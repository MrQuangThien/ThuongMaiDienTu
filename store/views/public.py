from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import IntegrityError

from ..models import (
    LoaiSanPham, SanPham, ChiNhanh, TonKhoChiNhanh, SanPhamImage, TaiKhoan,
    BinhLuanSanPham, DanhGiaSanPham
)

from .common import paginate_queryset

from ..forms import DanhGiaSanPhamForm, BinhLuanSanPhamForm
def home(request):
    san_phams = SanPham.objects.all()[:20] 
    products_new = SanPham.objects.all().order_by('-id')[:10] # Đổi tên biến ở đây
    products_km = SanPham.objects.filter(gia_goc__isnull=False)[:10] # Đổi tên biến ở đây
    
    if not products_km: 
        products_km = products_new

    stores = ChiNhanh.objects.all().order_by("ten_chi_nhanh")

    selected_store_id = request.session.get("selected_store_id")
    selected_store_name = request.session.get("selected_store_name", "")
    delivery_address = request.session.get("dia_chi_giao_hang", "") 

    # Map Tồn kho
    for ds_sp in [san_phams, products_new, products_km]:
        if selected_store_id:
            ton_khos = TonKhoChiNhanh.objects.filter(chi_nhanh_id=selected_store_id)
            dict_ton_kho = {tk.san_pham_id: tk.so_luong_ton for tk in ton_khos}
            for sp in ds_sp:
                sp.ton_kho_hien_tai = dict_ton_kho.get(sp.id, 0) 
                sp.da_chon_cua_hang = True
        else:
            for sp in ds_sp:
                sp.ton_kho_hien_tai = sp.so_luong 
                sp.da_chon_cua_hang = False

    return render(request, 'store/home.html', {
        'san_phams': san_phams,
        'products_new': products_new, # Truyền ra ngoài bằng tên mới
        'products_km': products_km,   # Truyền ra ngoài bằng tên mới
        'stores': stores,
        'selected_store_id': selected_store_id,
        'selected_store_name': selected_store_name,
        'delivery_address': delivery_address
    })

# 2. HÀM XỬ LÝ LƯU ĐỊA CHỈ TỪ TRANG CHỦ -> GIỎ HÀNG
def set_delivery_location(request):
    if request.method == "POST":
        address = request.POST.get("address", "").strip()
        store_id = request.POST.get("store_id", "").strip()
        store_name = request.POST.get("store_name", "").strip()

        # Lưu địa chỉ giao hàng vào Session để Giỏ Hàng dùng luôn
        if address:
            request.session["dia_chi_giao_hang"] = address
        
        # Cập nhật chi nhánh gần nhất
        if store_id:
            request.session["selected_store_id"] = store_id
            request.session["selected_store_name"] = store_name
            
        request.session.modified = True
    return redirect(request.META.get("HTTP_REFERER", "/"))

# ========================================================
# 3. TRANG GIỚI THIỆU
# ========================================================
def about_view(request):
    return render(request, 'store/about.html')


def product_list(request):
    q = request.GET.get("q", "")
    category_id = request.GET.get("category", "")
    selected_price = request.GET.get("price", "")

    products = SanPham.objects.prefetch_related("images").all().order_by("id")
    categories = LoaiSanPham.objects.all().order_by("ten_loai")

    if q:
        products = products.filter(ten_san_pham__icontains=q)
    if category_id:
        products = products.filter(loai_id=category_id)

    # Lọc giá trị (Dựa vào cột gia_hien_tai chứ không phải don_gia)
    if selected_price == 'under_50':
        products = products.filter(gia_hien_tai__lt=50000)
    elif selected_price == '50_100':
        products = products.filter(gia_hien_tai__gte=50000, gia_hien_tai__lte=100000)
    elif selected_price == 'over_100':
        products = products.filter(gia_hien_tai__gt=100000)

    # 👇 ĐOẠN MỚI: Bổ sung load tồn kho cửa hàng cho trang product_list 👇
    selected_store_id = request.session.get("selected_store_id")
    selected_store_name = request.session.get("selected_store_name")
    
    # Note: Lấy data ra list() trước để có thể gán thuộc tính động (ton_kho_hien_tai)
    # Lát nữa dùng paginate_queryset thì truyền cái list này vào
    products_list = list(products) 
    
    if selected_store_id:
        ton_khos = TonKhoChiNhanh.objects.filter(chi_nhanh_id=selected_store_id)
        dict_ton_kho = {tk.san_pham_id: tk.so_luong_ton for tk in ton_khos}
        for sp in products_list:
            sp.ton_kho_hien_tai = dict_ton_kho.get(sp.id, 0) 
            sp.da_chon_cua_hang = True
    else:
        for sp in products_list:
            sp.ton_kho_hien_tai = sp.so_luong 
            sp.da_chon_cua_hang = False
    # 👆 ======================================================== 👆

    page_obj = paginate_queryset(request, products_list, 8)

    return render(
        request,
        "store/product_list.html",
        {
            "page_obj": page_obj,
            "products": page_obj,
            "categories": categories,
            "query": q,
            "selected_category": category_id,
            "selected_price": selected_price,
            "selected_store_name": selected_store_name, # Truyền ra HTML
        },
    )

# ... (Các hàm bên dưới như product_detail, post_review... sếp giữ nguyên nhé)

def product_detail(request, pk):
    product = get_object_or_404(
        SanPham.objects.prefetch_related("images", "binh_luans__tai_khoan"),
        pk=pk
    )
    images = product.images.all()
    binh_luans = product.binh_luans.filter(hien_thi=True)
    selected_store_id = request.session.get("selected_store_id")
    selected_store_name = request.session.get("selected_store_name", "")

    if selected_store_id:
        ton_kho = TonKhoChiNhanh.objects.filter(chi_nhanh_id=selected_store_id, san_pham=product).first()
        product.ton_kho_hien_tai = ton_kho.so_luong_ton if ton_kho else 0
        product.da_chon_cua_hang = True
    else:
        product.ton_kho_hien_tai = product.so_luong
        product.da_chon_cua_hang = False
    tai_khoan_id = request.session.get("tai_khoan_id")
    tai_khoan = None
    my_comment = None

    if tai_khoan_id:
        tai_khoan = TaiKhoan.objects.filter(id=tai_khoan_id).first()
        if tai_khoan:
            my_comment = BinhLuanSanPham.objects.filter(
                san_pham=product,
                tai_khoan=tai_khoan
            ).first()

    if request.method == "POST":
        if not tai_khoan_id:
            messages.error(request, "Vui lòng đăng nhập để bình luận.")
            return redirect("store:login")

        if my_comment:
            messages.warning(request, "Bạn đã bình luận sản phẩm này rồi. Hãy sửa hoặc xóa bình luận cũ.")
            return redirect("store:product_detail", pk=product.pk)

        form = BinhLuanSanPhamForm(request.POST)
        if form.is_valid():
            binh_luan = form.save(commit=False)
            binh_luan.san_pham = product
            binh_luan.tai_khoan_id = tai_khoan_id
            if not binh_luan.so_sao:
                binh_luan.so_sao = 5

            try:
                binh_luan.save()
                messages.success(request, "Đã gửi bình luận của bạn.")
            except IntegrityError:
                messages.warning(request, "Bạn đã bình luận sản phẩm này rồi. Hãy sửa hoặc xóa bình luận cũ.")

            return redirect("store:product_detail", pk=product.pk)
    else:
        form = BinhLuanSanPhamForm(initial={"so_sao": 5})

    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "images": images,
            "binh_luans": binh_luans,
            "comment_form": form,
            "my_comment": my_comment,
        },
    )


def edit_product_comment(request, pk):
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        messages.error(request, "Vui lòng đăng nhập để sửa bình luận.")
        return redirect("store:login")

    comment = get_object_or_404(
        BinhLuanSanPham.objects.select_related("san_pham", "tai_khoan"),
        pk=pk,
        tai_khoan_id=tai_khoan_id,
    )

    if request.method != "POST":
        return redirect("store:product_detail", pk=comment.san_pham_id)

    form = BinhLuanSanPhamForm(request.POST, instance=comment)
    if form.is_valid():
        updated_comment = form.save(commit=False)
        if not updated_comment.so_sao:
            updated_comment.so_sao = 5
        updated_comment.save()
        messages.success(request, "Đã cập nhật bình luận của bạn.")
    else:
        messages.error(request, "Dữ liệu không hợp lệ. Vui lòng kiểm tra lại.")

    return redirect("store:product_detail", pk=comment.san_pham_id)


def delete_product_comment(request, pk):
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        messages.error(request, "Vui lòng đăng nhập để xóa bình luận.")
        return redirect("store:login")

    comment = get_object_or_404(
        BinhLuanSanPham.objects.select_related("san_pham", "tai_khoan"),
        pk=pk,
        tai_khoan_id=tai_khoan_id,
    )

    product_id = comment.san_pham_id

    if request.method == "POST":
        comment.delete()
        messages.success(request, "Đã xóa bình luận của bạn.")

    return redirect("store:product_detail", pk=product_id)

def location_picker(request):
    stores = ChiNhanh.objects.all()
    # Truyền danh sách cửa hàng ra để JS tính toán khoảng cách
    return render(request, 'store/location_picker.html', {'stores': stores})