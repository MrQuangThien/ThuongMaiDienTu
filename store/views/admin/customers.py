from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect

from ...forms import KhachHangForm
from ...models import KhachHang
from ..common import admin_required, paginate_queryset, render_admin_delete, render_admin_form


@admin_required
def admin_customer_list(request):
    q = request.GET.get("q", "").strip()
    customers = KhachHang.objects.all().order_by("-id")

    if q:
        customers = customers.filter(ten_khach_hang__icontains=q)

    page_obj = paginate_queryset(request, customers, 8)

    return render(
        request,
        "store/admin/customer_list.html",
        {
            "page_obj": page_obj,
            "q": q,
        },
    )


@admin_required
def admin_customer_create(request):
    return render_admin_form(
        request,
        KhachHangForm,
        title="Thêm khách hàng",
        success_url="store:admin_customer_list",
    )


@admin_required
def admin_customer_edit(request, pk):
    customer = get_object_or_404(KhachHang, pk=pk)
    return render_admin_form(
        request,
        KhachHangForm,
        instance=customer,
        title=f"Sửa khách hàng: {customer.ten_khach_hang}",
        success_url="store:admin_customer_list",
    )


@admin_required
def admin_customer_delete(request, pk):
    customer = get_object_or_404(KhachHang, pk=pk)

    if request.method == "POST":
        ten_khach_hang = customer.ten_khach_hang
        customer.delete()
        messages.success(request, f"Đã xóa khách hàng: {ten_khach_hang}")
        return redirect("store:admin_customer_list")

    return render(
        request,
        "store/admin/confirm_delete.html",
        {
            "title": "Xóa khách hàng",
            "object": customer,
            "cancel_url": "store:admin_customer_list",
        },
    )
