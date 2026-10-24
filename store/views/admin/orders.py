from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect

from ...forms import HoaDonForm
from ...models import HoaDon
from ..common import admin_required, paginate_queryset, render_admin_delete, render_admin_form


@admin_required
def admin_order_list(request):
    q = request.GET.get("q", "").strip()
    orders = HoaDon.objects.select_related("khach_hang", "nhan_vien").order_by("-ngay_lap")

    if q:
        orders = orders.filter(ten_nguoi_nhan__icontains=q)

    page_obj = paginate_queryset(request, orders, 8)

    return render(
        request,
        "store/admin/order_list.html",
        {
            "page_obj": page_obj,
            "q": q,
        },
    )


@admin_required
def admin_order_create(request):
    return render_admin_form(
        request,
        HoaDonForm,
        title="Thêm đơn hàng",
        success_url="store:admin_order_list",
    )


@admin_required
def admin_order_edit(request, pk):
    order = get_object_or_404(HoaDon, pk=pk)
    return render_admin_form(
        request,
        HoaDonForm,
        instance=order,
        title=f"Sửa đơn hàng #{order.pk}",
        success_url="store:admin_order_list",
    )


@admin_required
def admin_order_delete(request, pk):
    order = get_object_or_404(HoaDon, pk=pk)

    if request.method == "POST":
        ma_don = order.pk
        order.delete()
        messages.success(request, f"Đã xóa đơn hàng #{ma_don}")
        return redirect("store:admin_order_list")

    return render(
        request,
        "store/admin/confirm_delete.html",
        {
            "title": "Xóa đơn hàng",
            "object": order,
            "cancel_url": "store:admin_order_list",
        },
    )