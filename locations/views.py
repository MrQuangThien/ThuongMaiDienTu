import json
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import IntegrityError

# SỬA LỖI 1: Nhớ import thêm BinhLuanChiNhanhImage vào đây
from store.models import ChiNhanh, TaiKhoan, BinhLuanChiNhanh, BinhLuanChiNhanhImage
from .forms import BinhLuanChiNhanhForm

# ==========================================
# 1. HÀM CHO TRANG BẢN ĐỒ
# ==========================================
def map_search(request):
    stores = ChiNhanh.objects.all()
    
    stores_data = []
    for st in stores:
        if st.latitude and st.longitude:
            stores_data.append({
                "id": st.id,
                "ten": st.ten_chi_nhanh, 
                "dia_chi": st.dia_chi,
                "lat": float(st.latitude),
                "lon": float(st.longitude),
                "dien_thoai": st.dien_thoai
            })
            
    stores_json = json.dumps(stores_data)
    danh_sach_ten = ChiNhanh.objects.values_list('ten_chi_nhanh', flat=True)

    return render(request, 'locations/map_search.html', {
        'stores_json': stores_json,
        'danh_sach_ten': danh_sach_ten,
    })

# ==========================================
# 2. HÀM CHO TRANG DANH SÁCH
# ==========================================
def danh_sach_cua_hang(request):
    stores = ChiNhanh.objects.all()
    quan_huyen = request.GET.get('quan')
    tu_khoa = request.GET.get('q')

    if quan_huyen and quan_huyen != 'all':
        stores = stores.filter(dia_chi__icontains=quan_huyen)

    if tu_khoa:
        stores = stores.filter(
            Q(ten_chi_nhanh__icontains=tu_khoa) | 
            Q(dia_chi__icontains=tu_khoa)
        )

    danh_sach_quan = ['Quận 1', 'Quận 3', 'Quận 4', 'Quận 5', 'Quận 7', 'Quận 10', 'Bình Thạnh', 'Thủ Đức', 'Tân Bình', 'Gò Vấp']

    return render(request, 'locations/store_list.html', {
        'stores': stores,
        'danh_sach_quan': danh_sach_quan,
        'dang_chon_quan': quan_huyen,
        'dang_tim_kiem': tu_khoa
    })

# ==========================================
# 3. HÀM CHI TIẾT & XỬ LÝ BÌNH LUẬN
# ==========================================
def store_detail(request, pk):
    store = get_object_or_404(ChiNhanh, pk=pk)
    store_comments = BinhLuanChiNhanh.objects.filter(chi_nhanh=store).select_related('tai_khoan').order_by("-created_at")

    tai_khoan_id = request.session.get("tai_khoan_id")
    tai_khoan = None
    my_store_comment = None

    if tai_khoan_id:
        tai_khoan = TaiKhoan.objects.filter(id=tai_khoan_id).first()
        if tai_khoan:
            # Kiểm tra xem khách này đã bình luận chưa
            my_store_comment = BinhLuanChiNhanh.objects.filter(chi_nhanh=store, tai_khoan=tai_khoan).first()

    if request.method == "POST":
        if not tai_khoan_id:
            messages.error(request, "Vui lòng đăng nhập để bình luận.")
            return redirect("store:login")

        if my_store_comment:
            messages.warning(request, "Sếp đã đánh giá cửa hàng này rồi. Vui lòng sửa cái cũ nhé!")
            return redirect("locations:store_detail", pk=store.pk) # SỬA LỖI 2: Thêm locations:

        form = BinhLuanChiNhanhForm(request.POST)
        if form.is_valid():
            binh_luan = form.save(commit=False)
            binh_luan.chi_nhanh = store
            binh_luan.tai_khoan_id = tai_khoan_id
            if not binh_luan.so_sao:
                binh_luan.so_sao = 5

            try:
                binh_luan.save()
                
                # ==== XỬ LÝ UP NHIỀU ẢNH TỪ KHÁCH HÀNG ====
                images = request.FILES.getlist('hinh_anh_danh_gia') # Lấy danh sách ảnh
                for img in images:
                    BinhLuanChiNhanhImage.objects.create(binh_luan=binh_luan, image=img)
                # =====================================================
                
                messages.success(request, "Cảm ơn sếp đã đánh giá cửa hàng!")
            except IntegrityError:
                messages.warning(request, "Mỗi tài khoản chỉ được đánh giá 1 lần thôi sếp ơi!")

            return redirect("locations:store_detail", pk=store.pk) # SỬA LỖI 2: Thêm locations:
    else:
        form = BinhLuanChiNhanhForm(initial={"so_sao": 5})

    return render(
        request,
        "locations/store_detail.html",
        {
            "store": store,
            "store_comments": store_comments,
            "comment_form": form,
            "my_store_comment": my_store_comment,
        },
    )

def edit_store_comment(request, comment_id):
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        return redirect("store:login")

    comment = get_object_or_404(BinhLuanChiNhanh, pk=comment_id, tai_khoan_id=tai_khoan_id)

    if request.method == "POST":
        form = BinhLuanChiNhanhForm(request.POST, instance=comment)
        if form.is_valid():
            updated_comment = form.save(commit=False)
            if not updated_comment.so_sao:
                updated_comment.so_sao = 5
            updated_comment.save()
            
            # Khách hàng có thể up thêm ảnh khi sửa bình luận
            images = request.FILES.getlist('hinh_anh_danh_gia')
            for img in images:
                BinhLuanChiNhanhImage.objects.create(binh_luan=updated_comment, image=img)
                
            messages.success(request, "Đã cập nhật đánh giá thành công!")

    return redirect("locations:store_detail", pk=comment.chi_nhanh_id) # SỬA LỖI 2: Thêm locations:

def delete_store_comment(request, comment_id):
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        return redirect("store:login")

    comment = get_object_or_404(BinhLuanChiNhanh, pk=comment_id, tai_khoan_id=tai_khoan_id)
    store_id = comment.chi_nhanh_id

    if request.method == "POST":
        comment.delete() # Sẽ tự động xóa luôn các ảnh nằm trong BinhLuanChiNhanhImage nhờ on_delete=CASCADE
        messages.success(request, "Đã xóa đánh giá của sếp.")

    return redirect("locations:store_detail", pk=store_id) # SỬA LỖI 2: Thêm locations: