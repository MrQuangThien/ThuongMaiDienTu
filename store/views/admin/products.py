from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db import transaction

from ...forms import SanPhamForm
from ...models import LoaiSanPham, SanPham, SanPhamImage
from ..common import admin_only, admin_required, paginate_queryset
import openpyxl
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
@admin_only
@require_POST
@transaction.atomic
def import_san_pham_excel(request):
    file_excel = request.FILES.get('file_excel')
    if not file_excel:
        messages.error(request, "Vui lòng chọn file Excel.")
        return redirect('store:admin_product_list')

    try:
        wb = openpyxl.load_workbook(file_excel, read_only=True, data_only=True)
        ws = wb.active

        count = 0
        for line_no, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
            row = (list(row) + [None] * 5)[:5]
            ten, ten_loai, don_gia, so_luong, mo_ta = row
            if not ten:
                continue
            try:
                don_gia = Decimal(str(don_gia))
                so_luong = int(so_luong or 0)
            except (InvalidOperation, ValueError, TypeError):
                raise ValueError(f"Dòng {line_no}: đơn giá/số lượng không hợp lệ")

            loai, _ = LoaiSanPham.objects.get_or_create(ten_loai=str(ten_loai or "Khác").strip())
            SanPham.objects.update_or_create(
                ten_san_pham=str(ten).strip(),
                defaults={
                    "loai": loai,
                    "don_gia": don_gia,
                    "so_luong": so_luong,
                    "mo_ta": mo_ta or "",
                },
            )
            count += 1

        messages.success(request, f"Đã nhập thành công {count} sản phẩm.")
    except Exception as e:
        transaction.set_rollback(True)
        messages.error(request, f"Lỗi khi đọc file (không có dòng nào được lưu): {e}")

    return redirect('store:admin_product_list')

@admin_required
def admin_product_list(request):
    q = request.GET.get("q", "").strip()
    loai_id = request.GET.get("loai", "").strip()

    products = (
        SanPham.objects.select_related("loai")
        .prefetch_related("images")
        .order_by("-id")
    )
    categories = LoaiSanPham.objects.all().order_by("ten_loai")

    if q:
        products = products.filter(ten_san_pham__icontains=q)
    if loai_id:
        products = products.filter(loai_id=loai_id)

    page_obj = paginate_queryset(request, products, 8)

    return render(
        request,
        "store/admin/product_list.html",
        {
            "page_obj": page_obj,
            "categories": categories,
            "q": q,
            "loai_id": loai_id,
        },
    )


@admin_required
@transaction.atomic
def admin_product_create(request):
    if request.method == "POST":
        form = SanPhamForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save()

            uploaded_images = request.FILES.getlist("images")
            for index, image_file in enumerate(uploaded_images):
                SanPhamImage.objects.create(
                    san_pham=product,
                    image=image_file,
                    thu_tu=index + 1,
                    la_anh_chinh=(index == 0),
                )

            messages.success(request, f"Đã thêm sản phẩm: {product.ten_san_pham}")
            return redirect("store:admin_product_list")
        else:
            messages.error(request, f"Lỗi dữ liệu: {form.errors}")
    else:
        form = SanPhamForm()

    return render(
        request,
        "store/admin/product_form.html",
        {
            "form": form,
            "title": "Thêm sản phẩm",
            "existing_images": [],
        },
    )


@admin_required
@transaction.atomic
def admin_product_edit(request, pk):
    product = get_object_or_404(SanPham, pk=pk)

    if request.method == "POST":
        form = SanPhamForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            product = form.save()

            # Xóa ảnh được chọn
            delete_ids = request.POST.getlist("delete_images")
            if delete_ids:
                images_to_delete = SanPhamImage.objects.filter(
                    id__in=delete_ids,
                    san_pham=product,
                )
                for img in images_to_delete:
                    if img.image:
                        img.image.delete(save=False)
                    img.delete()

            # Cập nhật thứ tự ảnh
            for img in product.images.all():
                order_value = request.POST.get(f"order_{img.id}")
                if order_value not in [None, ""]:
                    try:
                        img.thu_tu = int(order_value)
                        img.save(update_fields=["thu_tu"])
                    except ValueError:
                        pass

            # Cập nhật ảnh chính
            main_image_id = request.POST.get("main_image")
            if main_image_id:
                product.images.update(la_anh_chinh=False)
                SanPhamImage.objects.filter(
                    id=main_image_id,
                    san_pham=product,
                ).update(la_anh_chinh=True)
            elif not product.images.filter(la_anh_chinh=True).exists():
                first_image = product.images.order_by("thu_tu", "id").first()
                if first_image:
                    first_image.la_anh_chinh = True
                    first_image.save(update_fields=["la_anh_chinh"])

            # Thêm nhiều ảnh mới từ 1 ô input
            uploaded_images = request.FILES.getlist("images")
            if uploaded_images:
                last_image = product.images.order_by("-thu_tu", "-id").first()
                next_order = (last_image.thu_tu + 1) if last_image else 1
                has_main = product.images.filter(la_anh_chinh=True).exists()

                for index, image_file in enumerate(uploaded_images):
                    SanPhamImage.objects.create(
                        san_pham=product,
                        image=image_file,
                        thu_tu=next_order + index,
                        la_anh_chinh=(not has_main and index == 0),
                    )

            messages.success(request, f"Đã cập nhật sản phẩm: {product.ten_san_pham}")
            return redirect("store:admin_product_list")
        else:
            messages.error(request, f"Lỗi dữ liệu: {form.errors}")
    else:
        form = SanPhamForm(instance=product)

    return render(
        request,
        "store/admin/product_form.html",
        {
            "form": form,
            "title": f"Sửa sản phẩm: {product.ten_san_pham}",
            "product": product,
            "existing_images": product.images.all().order_by("thu_tu", "id"),
        },
    )


@admin_required
def admin_product_delete(request, pk):
    product = get_object_or_404(SanPham, pk=pk)

    if request.method == "POST":
        ten_san_pham = product.ten_san_pham
        product.delete()
        messages.success(request, f"Đã xóa sản phẩm: {ten_san_pham}")
        return redirect("store:admin_product_list")

    return render(
        request,
        "store/admin/confirm_delete.html",
        {
            "title": "Xóa sản phẩm",
            "object": product,
            "cancel_url": "store:admin_product_list",
        },
    )