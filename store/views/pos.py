from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


from ..models import ChiTietHoaDon, HoaDon, KhachHang, NhanVien, SanPham
from ..stock import HetHangError, get_branch_stock_map, reserve_stock
from .common import admin_required


POS_CART_KEY = "pos_cart"
POS_LAST_INVOICE_KEY = "pos_last_invoice"


def _get_pos_cart(request):
    return request.session.get(POS_CART_KEY, {})


def _save_pos_cart(request, cart):
    request.session[POS_CART_KEY] = cart
    request.session.modified = True


def _clear_pos_cart(request):
    request.session.pop(POS_CART_KEY, None)
    request.session.modified = True


def _build_cart_items(cart, stock_map=None):
    if not cart:
        return [], Decimal("0")

    product_ids = [int(pk) for pk in cart.keys()]
    products = {
        product.id: product
        for product in SanPham.objects.select_related("loai").filter(id__in=product_ids)
    }

    items = []
    total = Decimal("0")

    for product_id_str, quantity in cart.items():
        product_id = int(product_id_str)
        product = products.get(product_id)
        if not product:
            continue

        qty = max(int(quantity), 1)
        unit_price = Decimal(str(product.don_gia))
        line_total = unit_price * qty
        total += line_total

        items.append(
            {
                "id": product.id,
                "ten_san_pham": product.ten_san_pham,
                "loai": product.loai.ten_loai if getattr(product, "loai", None) else "",
                "so_luong_ton": (stock_map or {}).get(product.id, 0),
                "don_gia": unit_price,
                "so_luong_mua": qty,
                "thanh_tien": line_total,
            }
        )

    return items, total


def _get_cashier(request):
    tai_khoan_id = request.session.get("tai_khoan_id")
    role = request.session.get("role")

    if not tai_khoan_id:
        return None, "Không xác định được tài khoản đang đăng nhập."

    if role not in ["STAFF", "ADMIN"]:
        return None, "Tài khoản hiện tại không có quyền thu ngân."

    nhan_vien = (
        NhanVien.objects.select_related("tai_khoan")
        .filter(tai_khoan_id=tai_khoan_id, tai_khoan__role__in=["STAFF", "ADMIN"])
        .first()
    )

    if not nhan_vien:
        return None, "Tài khoản hiện tại chưa được liên kết với nhân viên."

    return nhan_vien, ""


def _cashier_branch_id(request):
    nhan_vien, _ = _get_cashier(request)
    return nhan_vien.chi_nhanh_id if nhan_vien else None


@admin_required
def pos_checkout_view(request):
    q = request.GET.get("q", "").strip()
    products = SanPham.objects.select_related("loai").order_by("ten_san_pham")

    if q:
        products = products.filter(ten_san_pham__icontains=q)

    chi_nhanh_id = _cashier_branch_id(request)
    products = list(products[:100])
    stock_map = get_branch_stock_map(chi_nhanh_id, [p.id for p in products] + [int(k) for k in _get_pos_cart(request)])
    for p in products:
        p.so_luong_chi_nhanh = stock_map.get(p.id, 0)

    cart = _get_pos_cart(request)
    cart_items, cart_total = _build_cart_items(cart, stock_map)

    return render(
        request,
        "store/pos_checkout.html",
        {
            "products": products,
            "cart_items": cart_items,
            "cart_total": cart_total,
            "q": q,
        },
    )


@admin_required
def pos_add_item(request, pk):
    if request.method != "POST":
        return redirect("store:pos_checkout")

    product = get_object_or_404(SanPham, pk=pk)
    cart = _get_pos_cart(request)

    current_qty = int(cart.get(str(product.id), 0))
    new_qty = current_qty + 1

    ton_chi_nhanh = get_branch_stock_map(_cashier_branch_id(request), [product.id]).get(product.id, 0)
    if new_qty > ton_chi_nhanh:
        messages.error(request, f"Sản phẩm '{product.ten_san_pham}' không đủ tồn kho tại chi nhánh.")
        return redirect("store:pos_checkout")

    cart[str(product.id)] = new_qty
    _save_pos_cart(request, cart)

    return redirect("store:pos_checkout")


@admin_required
def pos_update_item(request, pk):
    if request.method != "POST":
        return redirect("store:pos_checkout")

    product = get_object_or_404(SanPham, pk=pk)
    action = request.POST.get("action", "").strip()

    cart = _get_pos_cart(request)
    current_qty = int(cart.get(str(product.id), 0))

    if action == "increase":
        new_qty = current_qty + 1
        ton_chi_nhanh = get_branch_stock_map(_cashier_branch_id(request), [product.id]).get(product.id, 0)
        if new_qty > ton_chi_nhanh:
            messages.error(request, f"Sản phẩm '{product.ten_san_pham}' chỉ còn {ton_chi_nhanh} tại chi nhánh.")
            return redirect("store:pos_checkout")
        cart[str(product.id)] = new_qty

    elif action == "decrease":
        new_qty = current_qty - 1
        if new_qty <= 0:
            cart.pop(str(product.id), None)
        else:
            cart[str(product.id)] = new_qty

    _save_pos_cart(request, cart)
    return redirect("store:pos_checkout")


@admin_required
def pos_remove_item(request, pk):
    if request.method != "POST":
        return redirect("store:pos_checkout")

    cart = _get_pos_cart(request)
    cart.pop(str(pk), None)
    _save_pos_cart(request, cart)
    return redirect("store:pos_checkout")


@admin_required
def pos_confirm_checkout(request):
    if request.method != "POST":
        return redirect("store:pos_checkout")

    cart = _get_pos_cart(request)
    cart_items, cart_total = _build_cart_items(cart)

    if not cart_items:
        messages.error(request, "Đơn tại quầy đang trống.")
        return redirect("store:pos_checkout")

    tien_khach_dua_raw = request.POST.get("tien_khach_dua", "").strip().replace(",", "")
    if not tien_khach_dua_raw:
        messages.error(request, "Vui lòng nhập tiền khách đưa.")
        return redirect("store:pos_checkout")

    try:
        tien_khach_dua = Decimal(tien_khach_dua_raw)
    except (InvalidOperation, TypeError):
        messages.error(request, "Tiền khách đưa không hợp lệ.")
        return redirect("store:pos_checkout")

    if tien_khach_dua < cart_total:
        messages.error(request, "Tiền khách đưa phải lớn hơn hoặc bằng tổng tiền.")
        return redirect("store:pos_checkout")

    tien_hoan_lai = tien_khach_dua - cart_total

    nhan_vien, cashier_error = _get_cashier(request)
    if not nhan_vien:
        messages.error(request, cashier_error)
        return redirect("store:pos_checkout")

    khach_hang, _ = KhachHang.objects.get_or_create(
        dien_thoai="0000000000",
        defaults={
            "ten_khach_hang": "Khách lẻ",
            "dia_chi": "Mua tại quầy",
        },
    )

    if not nhan_vien.chi_nhanh_id:
        messages.error(request, "Nhân viên thu ngân chưa được gán chi nhánh nên không thể trừ tồn kho.")
        return redirect("store:pos_checkout")

    try:
        with transaction.atomic():
            # Kiểm tra + trừ tồn kho của chi nhánh thu ngân (khóa dòng để tránh bán vượt)
            reserve_stock(
                nhan_vien.chi_nhanh_id,
                [(item["id"], item["so_luong_mua"]) for item in cart_items],
            )

            hoa_don = HoaDon.objects.create(
                ten_nguoi_nhan="Khách lẻ",
                sdt_nguoi_nhan="0000000000",
                khach_hang=khach_hang,
                nhan_vien=nhan_vien,
                chi_nhanh_id=nhan_vien.chi_nhanh_id,
                ngay_lap=timezone.now(),
                trang_thai="HOAN_TAT",
                phuong_thuc_thanh_toan="TIEN_MAT",
                dia_chi_giao_hang="Mua tại quầy",
            )

            for item in cart_items:
                ChiTietHoaDon.objects.create(
                    hoa_don=hoa_don,
                    san_pham_id=item["id"],
                    so_luong=item["so_luong_mua"],
                    don_gia=item["don_gia"],
                )

        request.session[POS_LAST_INVOICE_KEY] = {
            "hoa_don_id": hoa_don.id,
            "ngay_gio": timezone.localtime(hoa_don.ngay_lap).strftime("%d/%m/%Y %H:%M:%S"),
            "thu_ngan": nhan_vien.ten_nhan_vien,
            "tong_tien": str(cart_total),
            "tien_khach_dua": str(tien_khach_dua),
            "tien_hoan_lai": str(tien_hoan_lai),
            "items": [
                {
                    "ten_san_pham": item["ten_san_pham"],
                    "so_luong_mua": item["so_luong_mua"],
                    "don_gia": str(item["don_gia"]),
                    "thanh_tien": str(item["thanh_tien"]),
                }
                for item in cart_items
            ],
        }
        request.session.modified = True

        _clear_pos_cart(request)
        messages.success(request, "Thanh toán tại quầy thành công.")
        return redirect("store:pos_invoice")

    except HetHangError as exc:
        messages.error(request, str(exc))
        return redirect("store:pos_checkout")

    except Exception as exc:
        messages.error(request, f"Không thể thanh toán tại quầy: {exc}")
        return redirect("store:pos_checkout")


@admin_required
def pos_invoice_view(request):
    invoice = request.session.get(POS_LAST_INVOICE_KEY)

    if not invoice:
        messages.error(request, "Không tìm thấy dữ liệu hóa đơn để in.")
        return redirect("store:pos_checkout")

    return render(
        request,
        "store/pos_invoice.html",
        {
            "invoice": invoice,
        },
    )