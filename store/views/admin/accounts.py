from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, render,redirect

from ...forms import TaiKhoanForm
from ...models import TaiKhoan
from ..common import admin_only, admin_required, paginate_queryset, render_admin_delete, render_admin_form


@admin_only
def admin_account_list(request):
    q = request.GET.get("q", "").strip()
    accounts = TaiKhoan.objects.all().order_by("-id")

    if q:
        accounts = accounts.filter(
            Q(ho_ten__icontains=q)
            | Q(email__icontains=q)
            | Q(dien_thoai__icontains=q)
        )

    page_obj = paginate_queryset(request, accounts, 8)

    return render(
        request,
        "store/admin/account_list.html",
        {
            "page_obj": page_obj,
            "q": q,
        },
    )


@admin_only
def admin_account_create(request):
    return render_admin_form(
        request,
        TaiKhoanForm,
        title="Thêm tài khoản",
        success_url="store:admin_account_list",
    )


@admin_only
def admin_account_edit(request, pk):
    account = get_object_or_404(TaiKhoan, pk=pk)
    display_name = account.ho_ten or account.email or account.dien_thoai or f"#{account.id}"
    return render_admin_form(
        request,
        TaiKhoanForm,
        instance=account,
        title=f"Sửa tài khoản: {display_name}",
        success_url="store:admin_account_list",
    )


@admin_only
def admin_account_delete(request, pk):
    account = get_object_or_404(TaiKhoan, pk=pk)

    if request.method == "POST":
        display_name = account.ho_ten or account.email or account.dien_thoai or f"#{account.id}"
        account.delete()
        messages.success(request, f"Đã xóa tài khoản: {display_name}")
        return redirect("store:admin_account_list")

    return render(
        request,
        "store/admin/confirm_delete.html",
        {
            "title": "Xóa tài khoản",
            "object": account,
            "cancel_url": "store:admin_account_list",
        },
    )