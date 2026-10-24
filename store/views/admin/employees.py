from django.db.models import F
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from ...forms import TaiKhoanForm, NhanVienForm
from ...models import TaiKhoan, NhanVien, TonKhoChiNhanh, ChiNhanh
from ..common import admin_only, admin_required, paginate_queryset, render_admin_delete, render_admin_form


@admin_only
def admin_employee_list(request):
    q = request.GET.get("q", "").strip()

    employees = (
        NhanVien.objects.select_related("chi_nhanh", "tai_khoan")
        .filter(
            Q(tai_khoan__role__in=["STAFF", "ADMIN"]) | Q(tai_khoan__isnull=True)
        )
        .order_by("-id")
    )

    if q:
        employees = employees.filter(
            Q(ten_nhan_vien__icontains=q)
            | Q(chuc_vu__icontains=q)
            | Q(tai_khoan__ho_ten__icontains=q)
            | Q(tai_khoan__email__icontains=q)
            | Q(tai_khoan__dien_thoai__icontains=q)
        )

    page_obj = paginate_queryset(request, employees, 8)

    return render(
        request,
        "store/admin/employee_list.html",
        {
            "page_obj": page_obj,
            "q": q,
        },
    )


@admin_only
def admin_employee_create(request):
    return render_admin_form(
        request,
        NhanVienForm,
        title="Thêm nhân viên",
        success_url="store:admin_employee_list",
    )


@admin_only
def admin_employee_edit(request, pk):
    employee = get_object_or_404(NhanVien, pk=pk)
    return render_admin_form(
        request,
        NhanVienForm,
        instance=employee,
        title=f"Sửa nhân viên: {employee.ten_nhan_vien}",
        success_url="store:admin_employee_list",
    )


@admin_only
def admin_employee_delete(request, pk):
    employee = get_object_or_404(NhanVien, pk=pk)

    if request.method == "POST":
        display_name = employee.ten_nhan_vien
        employee.delete()
        messages.success(request, f"Đã xóa nhân viên: {display_name}")
        return redirect("store:admin_employee_list")

    return render(
        request,
        "store/admin/confirm_delete.html",
        {
            "title": "Xóa nhân viên",
            "object": employee,
            "cancel_url": "store:admin_employee_list",
        },
    )

def inventory_management(request):
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        return redirect("store:login")

    try:
        tai_khoan = TaiKhoan.objects.get(id=tai_khoan_id)
    except TaiKhoan.DoesNotExist:
        return redirect("store:login")

    if tai_khoan.role != "ADMIN":
        return redirect("store:home")

    chi_nhanh_id = request.GET.get("chi_nhanh")
    keyword = request.GET.get("q", "").strip()
    trang_thai = request.GET.get("trang_thai", "").strip()

    ton_khos = TonKhoChiNhanh.objects.select_related(
        "chi_nhanh", "san_pham", "san_pham__loai"
    ).all()

    if chi_nhanh_id:
        ton_khos = ton_khos.filter(chi_nhanh_id=chi_nhanh_id)

    if keyword:
        ton_khos = ton_khos.filter(
            Q(san_pham__ten_san_pham__icontains=keyword) |
            Q(chi_nhanh__ten_chi_nhanh__icontains=keyword) |
            Q(san_pham__loai__ten_loai__icontains=keyword)
        )

    if trang_thai == "HET_HANG":
        ton_khos = ton_khos.filter(so_luong_ton__lte=0)
    elif trang_thai == "SAP_HET":
        ton_khos = ton_khos.filter(so_luong_ton__gt=0, so_luong_ton__lte=F("muc_can_canh_bao"))
    elif trang_thai == "CON_HANG":
        ton_khos = ton_khos.filter(so_luong_ton__gt=F("muc_can_canh_bao"))

    ds_chi_nhanh = ChiNhanh.objects.all().order_by("ten_chi_nhanh")

    context = {
        "ton_khos": ton_khos,
        "ds_chi_nhanh": ds_chi_nhanh,
        "tong_mat_hang": ton_khos.count(),
        "tong_het_hang": ton_khos.filter(so_luong_ton__lte=0).count(),
        "tong_sap_het": ton_khos.filter(so_luong_ton__gt=0, so_luong_ton__lte=F("muc_can_canh_bao")).count(),
        "tong_con_hang": ton_khos.filter(so_luong_ton__gt=F("muc_can_canh_bao")).count(),
        "selected_chi_nhanh": chi_nhanh_id,
        "keyword": keyword,
        "selected_trang_thai": trang_thai,
    }
    return render(request, "store/admin/inventory_management.html", context)
def staff_inventory(request):
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        return redirect("store:login")

    tai_khoan = TaiKhoan.objects.filter(id=tai_khoan_id).first()
    if not tai_khoan:
        return redirect("store:login")

    if tai_khoan.role not in ["STAFF", "ADMIN"]:
        return redirect("store:home")

    nhan_vien = NhanVien.objects.select_related("chi_nhanh").filter(tai_khoan=tai_khoan).first()

    if not nhan_vien or not nhan_vien.chi_nhanh:
        return render(request, "store/staff/inventory_staff.html", {
            "chi_nhanh": None,
            "ton_khos": [],
            "tong_mat_hang": 0,
            "tong_het_hang": 0,
            "tong_sap_het": 0,
            "tong_con_hang": 0,
            "keyword": "",
            "selected_trang_thai": "",
        })

    keyword = (request.GET.get("q") or "").strip()
    trang_thai = (request.GET.get("trang_thai") or "").strip()

    ton_khos = TonKhoChiNhanh.objects.select_related(
        "chi_nhanh", "san_pham", "san_pham__loai"
    ).filter(chi_nhanh=nhan_vien.chi_nhanh)

    if keyword:
        ton_khos = ton_khos.filter(
            Q(san_pham__ten_san_pham__icontains=keyword) |
            Q(san_pham__loai__ten_loai__icontains=keyword)
        )

    if trang_thai == "HET_HANG":
        ton_khos = ton_khos.filter(so_luong_ton__lte=0)
    elif trang_thai == "SAP_HET":
        ton_khos = ton_khos.filter(so_luong_ton__gt=0, so_luong_ton__lte=F("muc_can_canh_bao"))
    elif trang_thai == "CON_HANG":
        ton_khos = ton_khos.filter(so_luong_ton__gt=F("muc_can_canh_bao"))

    context = {
        "chi_nhanh": nhan_vien.chi_nhanh,
        "ton_khos": ton_khos,
        "tong_mat_hang": ton_khos.count(),
        "tong_het_hang": ton_khos.filter(so_luong_ton__lte=0).count(),
        "tong_sap_het": ton_khos.filter(so_luong_ton__gt=0, so_luong_ton__lte=F("muc_can_canh_bao")).count(),
        "tong_con_hang": ton_khos.filter(so_luong_ton__gt=F("muc_can_canh_bao")).count(),
        "keyword": keyword,
        "selected_trang_thai": trang_thai,
    }
    return render(request, "store/staff/inventory_staff.html", context)

def inventory_update(request, pk):
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        return redirect("store:login")

    tai_khoan = TaiKhoan.objects.filter(id=tai_khoan_id).first()
    if not tai_khoan:
        return redirect("store:login")

    ton_kho = get_object_or_404(
        TonKhoChiNhanh.objects.select_related("chi_nhanh", "san_pham", "san_pham__loai"),
        pk=pk
    )

    # ADMIN được sửa mọi chi nhánh
    # STAFF chỉ được sửa tồn kho thuộc chi nhánh của mình
    if tai_khoan.role == "STAFF":
        nhan_vien = NhanVien.objects.select_related("chi_nhanh").filter(tai_khoan=tai_khoan).first()
        if not nhan_vien or not nhan_vien.chi_nhanh or ton_kho.chi_nhanh_id != nhan_vien.chi_nhanh_id:
            messages.error(request, "Bạn không có quyền sửa tồn kho của chi nhánh này.")
            return redirect("store:staff_inventory")
    elif tai_khoan.role != "ADMIN":
        return redirect("store:home")

    if request.method == "POST":
        action_type = request.POST.get("action_type", "set")
        so_luong_nhap_them = request.POST.get("so_luong_nhap_them", "").strip()
        so_luong_ton = request.POST.get("so_luong_ton", "").strip()
        muc_can_canh_bao = request.POST.get("muc_can_canh_bao", "").strip()
        is_hien_thi = True if request.POST.get("is_hien_thi") == "on" else False

        try:
            muc_can_canh_bao = int(muc_can_canh_bao or 0)
            if muc_can_canh_bao < 0:
                raise ValueError

            if action_type == "add":
                so_luong_nhap_them = int(so_luong_nhap_them or 0)
                if so_luong_nhap_them < 0:
                    raise ValueError
                ton_kho.so_luong_ton += so_luong_nhap_them
            else:
                so_luong_ton = int(so_luong_ton or 0)
                if so_luong_ton < 0:
                    raise ValueError
                ton_kho.so_luong_ton = so_luong_ton

            ton_kho.muc_can_canh_bao = muc_can_canh_bao
            ton_kho.is_hien_thi = is_hien_thi
            ton_kho.save()

            messages.success(
                request,
                f"Đã cập nhật tồn kho cho sản phẩm: {ton_kho.san_pham.ten_san_pham}"
            )

            if tai_khoan.role == "ADMIN":
                return redirect("store:inventory_management")
            return redirect("store:staff_inventory")

        except ValueError:
            messages.error(request, "Dữ liệu không hợp lệ. Số lượng và ngưỡng cảnh báo phải là số nguyên >= 0.")

    return render(
        request,
        "store/staff/inventory_edit.html",
        {
            "ton_kho": ton_kho,
            "is_admin": tai_khoan.role == "ADMIN",
        },
    )