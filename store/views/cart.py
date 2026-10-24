from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from collections import OrderedDict
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..stock import HetHangError, reserve_stock
from django.utils.dateparse import parse_date

from ..models import (
    ChiNhanh,
    ChiTietHoaDon,
    HoaDon,
    KhachHang,
    NhanVien,
    SanPham,
    TaiKhoan,
    TonKhoChiNhanh,
)

try:
    from locations.models import CuaHang
except Exception:
    CuaHang = None


TIME_SLOTS = [
    "7H-8H",
    "8H-9H",
    "9H-10H",
    "10H-11H",
    "13H-14H",
    "14H-15H",
    "15H-16H",
    "16H-17H",
]


# =========================================================
# HELPER
# =========================================================
def _get_cart(request):
    return request.session.get("cart", {})


def _save_cart(request, cart):
    request.session["cart"] = cart
    request.session.modified = True


def _clear_cart(request):
    request.session["cart"] = {}
    request.session.modified = True


def _get_checkout_state(request):
    return {
        "delivery_method": request.session.get("delivery_method", "delivery"),
        "payment_method": request.session.get("payment_method", "BANK"),
        "delivery_time_slot": request.session.get("delivery_time_slot", ""),
        "address_type": request.session.get("address_type", "current_location"),
        "dia_chi_giao_hang": request.session.get("dia_chi_giao_hang", ""),
        "ten_nguoi_nhan": request.session.get("ten_nguoi_nhan", ""),
        "sdt_nguoi_nhan": request.session.get("sdt_nguoi_nhan", ""),
        "selected_store_id": request.session.get("selected_store_id", ""),
        "selected_store_name": request.session.get("selected_store_name", ""),
        "selected_store_address": request.session.get("selected_store_address", ""),
    }


def _get_current_account(request):
    tai_khoan_id = (
        request.session.get("tai_khoan_id")
        or request.session.get("user_id")
        or request.session.get("account_id")
    )
    if not tai_khoan_id:
        return None
    return TaiKhoan.objects.filter(id=tai_khoan_id).first()


def _get_current_customer(request):
    tai_khoan = _get_current_account(request)
    if not tai_khoan:
        return None
    return KhachHang.objects.filter(tai_khoan=tai_khoan).first()


def _get_current_staff(request):
    tai_khoan = _get_current_account(request)
    if not tai_khoan:
        return None
    return NhanVien.objects.select_related("chi_nhanh").filter(tai_khoan=tai_khoan).first()


def _get_user_role(request):
    raw_role = request.session.get("role") or request.session.get("vai_tro") or "USER"
    raw_role = str(raw_role).upper().strip()

    if raw_role in ["ADMIN", "QUAN_TRI", "QUANTRIVIEN"]:
        return "ADMIN"
    if raw_role in ["STAFF", "NHAN_VIEN", "NHANVIEN"]:
        return "STAFF"
    return "USER"


def _format_payment_method(value):
    mapping = {
        "BANK": "Chuyển khoản",
        "CASH": "Tiền mặt",
        "CHUYEN_KHOAN": "Chuyển khoản",
        "TIEN_MAT": "Tiền mặt",
    }
    return mapping.get(value, value or "Chưa cập nhật")


def _normalize_payment_method(value):
    mapping = {
        "BANK": "CHUYEN_KHOAN",
        "CASH": "TIEN_MAT",
        "CHUYEN_KHOAN": "CHUYEN_KHOAN",
        "TIEN_MAT": "TIEN_MAT",
    }
    return mapping.get(value, "CHUYEN_KHOAN")


def _build_cart_items(cart, selected_store_id=None):
    cart_items = []
    tong_tien = Decimal("0")

    product_ids = [int(pid) for pid in cart.keys() if str(pid).isdigit()]
    ton_kho_map = {}

    if selected_store_id and product_ids:
        ton_khos = TonKhoChiNhanh.objects.filter(
            chi_nhanh_id=selected_store_id,
            san_pham_id__in=product_ids,
            is_hien_thi=True,
        )
        ton_kho_map = {tk.san_pham_id: tk for tk in ton_khos}

    for product_id, item in cart.items():
        san_pham = (
            SanPham.objects.filter(pk=product_id)
            .prefetch_related("images")
            .first()
        )
        if not san_pham:
            continue

        don_gia = Decimal(str(item.get("don_gia", 0)))
        so_luong = int(item.get("so_luong", 1))
        thanh_tien = don_gia * so_luong
        tong_tien += thanh_tien

        anh_chinh = getattr(san_pham, "anh_chinh", None)
        hinh_anh_url = ""
        if anh_chinh and getattr(anh_chinh, "image", None):
            try:
                hinh_anh_url = anh_chinh.image.url
            except Exception:
                hinh_anh_url = ""

        ton_kho = ton_kho_map.get(san_pham.id)
        so_luong_ton = ton_kho.so_luong_ton if ton_kho else 0
        du_hang = so_luong_ton >= so_luong

        cart_items.append(
            {
                "product_id": str(product_id),
                "ten_san_pham": san_pham.ten_san_pham,
                "don_gia": don_gia,
                "so_luong": so_luong,
                "thanh_tien": thanh_tien,
                "gia_goc": getattr(san_pham, "gia_goc", None),
                "anh_chinh": anh_chinh,
                "hinh_anh_url": hinh_anh_url,
                "so_luong_ton_chi_nhanh": so_luong_ton,
                "du_hang": du_hang,
            }
        )

    return cart_items, tong_tien
def _get_or_create_customer(ten_nguoi_nhan, sdt_nguoi_nhan, dia_chi_giao_hang, tai_khoan=None):
    if tai_khoan:
        khach_hang = KhachHang.objects.filter(tai_khoan=tai_khoan).first()

        if not khach_hang:
            khach_hang = KhachHang.objects.create(
                tai_khoan=tai_khoan,
                ten_khach_hang=ten_nguoi_nhan or getattr(tai_khoan, "ho_ten", "Khách hàng"),
                dien_thoai=sdt_nguoi_nhan or "",
                dia_chi=dia_chi_giao_hang or "",
            )
        else:
            if ten_nguoi_nhan:
                khach_hang.ten_khach_hang = ten_nguoi_nhan
            if sdt_nguoi_nhan:
                khach_hang.dien_thoai = sdt_nguoi_nhan
            if dia_chi_giao_hang:
                khach_hang.dia_chi = dia_chi_giao_hang
            khach_hang.save()

        return khach_hang

    # Không dùng get_or_create theo số điện thoại vì dữ liệu cũ có thể bị trùng
    khach_hangs = KhachHang.objects.filter(dien_thoai=sdt_nguoi_nhan).order_by("id")
    khach_hang = khach_hangs.first()

    if khach_hang:
        if ten_nguoi_nhan:
            khach_hang.ten_khach_hang = ten_nguoi_nhan
        if dia_chi_giao_hang:
            khach_hang.dia_chi = dia_chi_giao_hang
        khach_hang.save()
        return khach_hang

    return KhachHang.objects.create(
        ten_khach_hang=ten_nguoi_nhan or "Khách hàng",
        dien_thoai=sdt_nguoi_nhan,
        dia_chi=dia_chi_giao_hang,
    )


def _normalize_order_data(orders, role):
    grouped_orders = OrderedDict()

    for order in orders:
        tong_tien = Decimal("0")
        tong_so_luong = 0
        preview_images = []

        for index, ct in enumerate(order.chi_tiets.all()):
            ct.thanh_tien = (ct.so_luong or 0) * (ct.don_gia or 0)
            tong_tien += ct.thanh_tien
            tong_so_luong += ct.so_luong or 0

            image_url = ""
            san_pham = ct.san_pham
            anh_chinh = getattr(san_pham, "anh_chinh", None)
            if anh_chinh and getattr(anh_chinh, "image", None):
                try:
                    image_url = anh_chinh.image.url
                except Exception:
                    image_url = ""

            if index < 4:
                preview_images.append(
                    {
                        "ten_san_pham": getattr(san_pham, "ten_san_pham", "Sản phẩm"),
                        "image_url": image_url,
                    }
                )

        order.tong_tien = tong_tien
        order.tong_so_luong = tong_so_luong
        order.preview_images = preview_images
        order.more_items_count = max(order.chi_tiets.count() - 4, 0)

        order.branch_name = ""
        if getattr(order, "nhan_vien", None) and getattr(order.nhan_vien, "chi_nhanh", None):
            order.branch_name = order.nhan_vien.chi_nhanh.ten_chi_nhanh

        order.customer_name = ""
        if getattr(order, "khach_hang", None):
            order.customer_name = order.khach_hang.ten_khach_hang or "Khách lẻ"

        order.customer_phone = ""
        if getattr(order, "khach_hang", None):
            order.customer_phone = order.khach_hang.dien_thoai or order.sdt_nguoi_nhan or ""

        order.is_guest = not bool(getattr(order.khach_hang, "tai_khoan_id", None))
        order.payment_display = _format_payment_method(order.phuong_thuc_thanh_toan)
        order.can_cancel = role not in ["ADMIN", "STAFF"] and order.trang_thai == "CHO_XU_LY"

        ngay_key = order.ngay_lap.date()
        if ngay_key not in grouped_orders:
            grouped_orders[ngay_key] = {
                "date": ngay_key,
                "orders": [],
            }

        grouped_orders[ngay_key]["orders"].append(order)

    return list(grouped_orders.values())


# =========================================================
# CART
# =========================================================
def add_to_cart(request, pk):
    product = get_object_or_404(SanPham, pk=pk)

    cart = _get_cart(request)
    product_id = str(product.id)
    don_gia = float(product.gia_hien_tai)

    if product_id in cart:
        cart[product_id]["so_luong"] += 1
    else:
        cart[product_id] = {
            "ten_san_pham": product.ten_san_pham,
            "don_gia": don_gia,
            "so_luong": 1,
        }

    _save_cart(request, cart)

    tong_sp = sum(item["so_luong"] for item in cart.values())

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "status": "success",
                "cart_count": tong_sp,
                "message": f"Đã thêm {product.ten_san_pham} vào giỏ!",
            }
        )

    trang_hien_tai = request.META.get("HTTP_REFERER")
    if trang_hien_tai:
        return redirect(trang_hien_tai)
    return redirect("store:product_list")


def cart_detail(request):
    cart = _get_cart(request)
    state = _get_checkout_state(request)

    # Đảm bảo selected_store_id là int hoặc None, không phải string rỗng
    raw_store_id = state.get("selected_store_id", "")
    try:
        selected_store_id = int(raw_store_id) if raw_store_id else None
    except (ValueError, TypeError):
        selected_store_id = None

    cart_items, tong_tien = _build_cart_items(cart, selected_store_id=selected_store_id)

    stores = ChiNhanh.objects.all().order_by("ten_chi_nhanh")

    return render(
        request,
        "store/cart.html",
        {
            "cart_items": cart_items,
            "tong_tien": tong_tien,
            "time_slots": TIME_SLOTS,
            "stores": stores,
            **state,
            # Override lại selected_store_id đã được chuẩn hóa
            "selected_store_id": selected_store_id,
        },
    )


def update_cart_quantity(request, pk):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=405)

    cart = _get_cart(request)
    product_id = str(pk)
    action = request.POST.get("action", "").strip()

    if product_id not in cart:
        return JsonResponse({"status": "error", "message": "Không tìm thấy sản phẩm"}, status=404)

    current_qty = int(cart[product_id].get("so_luong", 1))

    if action == "increase":
        selected_store_id = request.session.get("selected_store_id")
        if selected_store_id:
            ton_kho = TonKhoChiNhanh.objects.filter(
                chi_nhanh_id=selected_store_id,
                san_pham_id=pk,
                is_hien_thi=True,
            ).first()
            so_ton = ton_kho.so_luong_ton if ton_kho else 0
            if current_qty + 1 > so_ton:
                return JsonResponse({
                    "status": "error",
                    "message": f"Sản phẩm chỉ còn {so_ton} tại chi nhánh đã chọn."
                }, status=400)
        cart[product_id]["so_luong"] = current_qty + 1

    elif action == "decrease":
        new_qty = current_qty - 1
        if new_qty <= 0:
            del cart[product_id]
        else:
            cart[product_id]["so_luong"] = new_qty

    _save_cart(request, cart)
    return JsonResponse({"status": "ok"})


def remove_from_cart(request, pk):
    if request.method != "POST":
        return redirect("store:cart_detail")

    cart = _get_cart(request)
    product_id = str(pk)

    if product_id in cart:
        del cart[product_id]
        _save_cart(request, cart)

    return redirect("store:cart_detail")


def save_checkout_options(request):
    if request.method != "POST":
        return redirect("store:cart_detail")

    request.session["delivery_method"] = request.POST.get("delivery_method", "delivery")
    request.session["payment_method"] = request.POST.get("payment_method", "BANK")
    request.session["delivery_time_slot"] = request.POST.get("delivery_time_slot", "")
    request.session["address_type"] = request.POST.get("address_type", "current_location")
    request.session["dia_chi_giao_hang"] = request.POST.get("dia_chi_giao_hang", "").strip()
    request.session["ten_nguoi_nhan"] = request.POST.get("ten_nguoi_nhan", "").strip()
    request.session["sdt_nguoi_nhan"] = request.POST.get("sdt_nguoi_nhan", "").strip()
    request.session["selected_store_id"] = request.POST.get("selected_store_id", "").strip()
    request.session["selected_store_name"] = request.POST.get("selected_store_name", "").strip()
    request.session["selected_store_address"] = request.POST.get("selected_store_address", "").strip()
    request.session.modified = True

    return redirect("store:cart_detail")


# =========================================================
# CHECKOUT
# =========================================================
def checkout(request):
    cart = _get_cart(request)
    cart_items, tong_tien = _build_cart_items(cart)

    if not cart_items:
        return redirect("store:product_list")

    state = _get_checkout_state(request)

    if request.method == "POST":
        ten_nguoi_nhan = (request.POST.get("ten_nguoi_nhan") or state.get("ten_nguoi_nhan", "")).strip()
        sdt_nguoi_nhan = (request.POST.get("sdt_nguoi_nhan") or state.get("sdt_nguoi_nhan", "")).strip()
        dia_chi_giao_hang = (request.POST.get("dia_chi_giao_hang") or state.get("dia_chi_giao_hang", "")).strip()
        delivery_method = request.POST.get("delivery_method") or state.get("delivery_method", "delivery")
        payment_method_raw = request.POST.get("phuong_thuc_thanh_toan") or state.get("payment_method", "BANK")
        delivery_time_slot = request.POST.get("delivery_time_slot") or state.get("delivery_time_slot", "")
        selected_store_id = (request.POST.get("selected_store_id") or state.get("selected_store_id", "")).strip()

        phuong_thuc_thanh_toan = _normalize_payment_method(payment_method_raw)

        if delivery_method == "pickup":
            ten_cua_hang = (request.POST.get("selected_store_name") or state.get("selected_store_name", "")).strip()
            dia_chi_cua_hang = (request.POST.get("selected_store_address") or state.get("selected_store_address", "")).strip()
            dia_chi_giao_hang = f"Nhận tại cửa hàng: {ten_cua_hang} - {dia_chi_cua_hang}".strip(" -")

        # --- Validation ---
        if not ten_nguoi_nhan or not sdt_nguoi_nhan:
            messages.error(request, "Vui lòng nhập đầy đủ tên người nhận và số điện thoại.")
            return redirect("store:cart_detail")

        if delivery_method != "pickup" and not dia_chi_giao_hang:
            messages.error(request, "Vui lòng nhập địa chỉ giao hàng.")
            return redirect("store:cart_detail")

        if delivery_method != "pickup" and not delivery_time_slot:
            messages.error(request, "Vui lòng chọn thời gian giao hàng.")
            return redirect("store:cart_detail")

        nhan_vien = None
        if selected_store_id:
            nhan_vien = (
                NhanVien.objects
                .select_related("chi_nhanh", "tai_khoan")
                .filter(
                    chi_nhanh_id=selected_store_id,
                    tai_khoan__role="STAFF",
                )
                .first()
            )
            if not nhan_vien:
                nhan_vien = (
                    NhanVien.objects
                    .select_related("chi_nhanh", "tai_khoan")
                    .filter(chi_nhanh_id=selected_store_id)
                    .first()
                )

        if not nhan_vien:
            nhan_vien = NhanVien.objects.first()

        if not nhan_vien:
            messages.error(request, "Hiện chưa có nhân viên phụ trách để xử lý đơn hàng. Vui lòng thử lại sau.")
            return redirect("store:cart_detail")

        # Chi nhánh bị trừ tồn kho: cửa hàng khách đã chọn (hoặc chi nhánh của nhân viên phụ trách)
        chi_nhanh_id = int(selected_store_id) if selected_store_id.isdigit() else nhan_vien.chi_nhanh_id
        if not chi_nhanh_id:
            messages.error(request, "Vui lòng chọn cửa hàng để đặt hàng.")
            return redirect("store:cart_detail")

        tai_khoan = _get_current_account(request)
        try:
            with transaction.atomic():
                reserve_stock(
                    chi_nhanh_id,
                    [(item["product_id"], item["so_luong"]) for item in cart_items],
                )

                khach_hang = _get_or_create_customer(
                    ten_nguoi_nhan=ten_nguoi_nhan,
                    sdt_nguoi_nhan=sdt_nguoi_nhan,
                    dia_chi_giao_hang=dia_chi_giao_hang,
                    tai_khoan=tai_khoan,
                )

                hoa_don = HoaDon.objects.create(
                    ngay_lap=timezone.now(),
                    khach_hang=khach_hang,
                    nhan_vien=nhan_vien,
                    chi_nhanh_id=chi_nhanh_id,
                    dia_chi_giao_hang=dia_chi_giao_hang,
                    sdt_nguoi_nhan=sdt_nguoi_nhan,
                    ten_nguoi_nhan=ten_nguoi_nhan,
                    trang_thai="CHO_XU_LY",
                    phuong_thuc_thanh_toan=phuong_thuc_thanh_toan,
                )

                for item in cart_items:
                    san_pham = SanPham.objects.get(pk=item["product_id"])
                    ChiTietHoaDon.objects.create(
                        hoa_don=hoa_don,
                        san_pham=san_pham,
                        so_luong=item["so_luong"],
                        don_gia=item["don_gia"],
                    )
        except HetHangError as exc:
            messages.error(request, str(exc))
            return redirect("store:cart_detail")

        # 👇 ĐOẠN GỬI MAIL ĐÃ ĐƯỢC CHÈN ĐÚNG VỊ TRÍ 👇
        try:
            email_khach_hang = getattr(tai_khoan, 'email', None)

            if email_khach_hang:
                subject = f'Xác nhận đơn hàng #{hoa_don.id} từ Bách Hóa Xanh'
                
                html_message = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px;">
                    <h2 style="color: #008a37; text-align: center;">CẢM ƠN BẠN ĐÃ ĐẶT HÀNG! 🎉</h2>
                    <p>Chào bạn,</p>
                    <p>Đơn hàng <strong>#{hoa_don.id}</strong> của bạn đã được đặt thành công.</p>
                    
                    <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h4 style="margin-top: 0; color: #166534;">Thông tin giao hàng:</h4>
                        <p>📍 Địa chỉ: {hoa_don.dia_chi_giao_hang}</p>
                        <p>📞 Số điện thoại: {hoa_don.sdt_nguoi_nhan}</p>
                        <p>💰 Tổng tiền: <strong style="color: #d8232a;">{tong_tien:,.0f} VNĐ</strong></p>
                    </div>
                    
                    <p>Chúng tôi sẽ sớm chuẩn bị hàng và giao đến bạn.</p>
                    <p>Trân trọng,<br><strong>Đội ngũ Bách Hóa Xanh</strong></p>
                </div>
                """
                
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject,
                    plain_message,
                    'no-reply@bachhoaxanh.local',
                    [email_khach_hang],
                    html_message=html_message,
                    fail_silently=False,
                )
        except Exception as e:
            print(f"Lỗi gửi mail: {e}")
        # 👆 KẾT THÚC ĐOẠN GỬI MAIL 👆

        _clear_cart(request)
        request.session["last_order_id"] = hoa_don.id
        request.session.modified = True

        return redirect("store:order_success")

    # Form thanh toán nằm trong cart.html
    return redirect("store:cart_detail")

def order_success(request):
    last_order_id = request.session.get("last_order_id")
    order = None

    if last_order_id:
        order = (
            HoaDon.objects.select_related("khach_hang")
            .prefetch_related(
                Prefetch(
                    "chi_tiets",
                    queryset=ChiTietHoaDon.objects.select_related("san_pham").prefetch_related("san_pham__images"),
                )
            )
            .filter(id=last_order_id)
            .first()
        )

    tong_tien = Decimal("0")
    tong_so_luong = 0

    if order:
        for ct in order.chi_tiets.all():
            ct.thanh_tien = (ct.so_luong or 0) * (ct.don_gia or 0)
            tong_tien += ct.thanh_tien
            tong_so_luong += ct.so_luong or 0

    return render(
        request,
        "store/order_success.html",
        {
            "last_order_id": last_order_id,
            "order": order,
            "tong_tien": tong_tien,
            "tong_so_luong": tong_so_luong,
        },
    )


# =========================================================
# ORDER HISTORY
# =========================================================
def order_history(request):
    role = _get_user_role(request)

    selected_date_from = request.GET.get("date_from", "").strip()
    selected_date_to = request.GET.get("date_to", "").strip()
    selected_branch = request.GET.get("branch", "").strip()

    date_from = parse_date(selected_date_from) if selected_date_from else None
    date_to = parse_date(selected_date_to) if selected_date_to else None

    chi_tiet_queryset = ChiTietHoaDon.objects.select_related("san_pham").prefetch_related("san_pham__images")
    orders = (
        HoaDon.objects.select_related(
            "khach_hang",
            "khach_hang__tai_khoan",
            "nhan_vien",
            "nhan_vien__tai_khoan",
            "nhan_vien__chi_nhanh",
        )
        .prefetch_related(Prefetch("chi_tiets", queryset=chi_tiet_queryset))
        .order_by("-ngay_lap", "-id")
    )

    branches = ChiNhanh.objects.all().order_by("ten_chi_nhanh")
    current_staff = None

    if role == "ADMIN":
        if selected_branch:
            orders = orders.filter(nhan_vien__chi_nhanh_id=selected_branch)

    elif role == "STAFF":
        current_staff = _get_current_staff(request)
        if current_staff and current_staff.chi_nhanh_id:
            orders = orders.filter(nhan_vien__chi_nhanh_id=current_staff.chi_nhanh_id)
        else:
            orders = HoaDon.objects.none()

    else:
        current_account = _get_current_account(request)
        current_customer = _get_current_customer(request)

        if current_account:
            orders = orders.filter(khach_hang__tai_khoan=current_account).distinct()
        elif current_customer:
            orders = orders.filter(khach_hang=current_customer).distinct()
        else:
            orders = HoaDon.objects.none()

    if date_from:
        orders = orders.filter(ngay_lap__date__gte=date_from)

    if date_to:
        orders = orders.filter(ngay_lap__date__lte=date_to)

    grouped_orders = _normalize_order_data(orders, role)

    return render(
        request,
        "store/order_history.html",
        {
            "grouped_orders": grouped_orders,
            "role": role,
            "branches": branches,
            "selected_branch": selected_branch,
            "selected_date_from": selected_date_from,
            "selected_date_to": selected_date_to,
            "current_staff": current_staff,
        },
    )


def cancel_order(request, order_id):
    if request.method != "POST":
        return redirect("store:order_history")

    current_customer = _get_current_customer(request)
    if not current_customer:
        messages.error(request, "Bạn cần đăng nhập để hủy đơn hàng.")
        return redirect("store:order_history")

    hoa_don = get_object_or_404(
        HoaDon.objects.select_related("khach_hang"),
        id=order_id,
        khach_hang=current_customer,
    )

    with transaction.atomic():
        # Khóa hóa đơn để tránh hủy 2 lần (hoàn tồn 2 lần)
        hoa_don = HoaDon.objects.select_for_update().get(pk=hoa_don.pk)

        if hoa_don.trang_thai != "CHO_XU_LY":
            messages.error(request, f"Đơn hàng #{hoa_don.id} không thể hủy.")
            return redirect("store:order_history")

        hoa_don.trang_thai = "HUY"
        hoa_don.save(update_fields=["trang_thai"])
        # Tồn kho được hoàn tự động bởi signal trên HoaDon khi trạng thái chuyển sang HUY

    messages.success(request, f"Đã hủy đơn hàng #{hoa_don.id} thành công.")
    return redirect("store:order_history")