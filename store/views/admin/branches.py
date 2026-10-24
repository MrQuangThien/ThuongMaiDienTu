from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect

from ...forms import ChiNhanhForm
from ...models import ChiNhanh, ChiNhanhImage
from ..common import admin_required, paginate_queryset, render_admin_delete, render_admin_form


@admin_required
def admin_branch_list(request):
    q = request.GET.get("q", "").strip()
    branches = ChiNhanh.objects.all().order_by("-id")

    if q:
        branches = branches.filter(ten_chi_nhanh__icontains=q)

    page_obj = paginate_queryset(request, branches, 8)

    return render(
        request,
        "store/admin/branch_list.html",
        {
            "page_obj": page_obj,
            "q": q,
        },
    )


@admin_required
def admin_branch_create(request):
    response = render_admin_form(
        request,
        ChiNhanhForm,
        title="Thêm chi nhánh",
        success_url="store:admin_branch_list",
    )

    if request.method == "POST" and response.status_code == 302:
        new_branch = ChiNhanh.objects.latest('id')
        danh_sach_anh = request.FILES.getlist('hinh_anh_phu')
        for file_anh in danh_sach_anh:
            ChiNhanhImage.objects.create(chi_nhanh=new_branch, image=file_anh)

    return response

@admin_required
def admin_branch_edit(request, pk):
    branch = get_object_or_404(ChiNhanh, pk=pk)
    
    if request.method == "POST":
        if request.POST.get("hinh_anh-clear") == "on":
            if branch.hinh_anh:
                branch.hinh_anh.delete(save=False)
                branch.hinh_anh = None
                branch.save()

        danh_sach_xoa = request.POST.getlist("xoa_anh_phu")
        if danh_sach_xoa:
            for img in ChiNhanhImage.objects.filter(id__in=danh_sach_xoa, chi_nhanh=branch):
                img.image.delete(save=False)
                img.delete()

    response = render_admin_form(
        request,
        ChiNhanhForm,
        instance=branch,
        title=f"Sửa chi nhánh: {branch.ten_chi_nhanh}",
        success_url="store:admin_branch_list",
    )

    if request.method == "POST" and response.status_code == 302:
        danh_sach_anh = request.FILES.getlist('hinh_anh_phu')
        for file_anh in danh_sach_anh:
            ChiNhanhImage.objects.create(chi_nhanh=branch, image=file_anh)

    return response

@admin_required
def admin_branch_delete(request, pk):
    branch = get_object_or_404(ChiNhanh, pk=pk)
    return render_admin_delete(
        request,
        branch,
        title="Xóa chi nhánh",
        success_url="store:admin_branch_list",
    )