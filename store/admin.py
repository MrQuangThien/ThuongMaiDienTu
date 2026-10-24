from django.contrib import admin
from import_export.admin import ImportExportModelAdmin  # <-- THÊM DÒNG NÀY ĐỂ CÓ NÚT IMPORT
from .models import (
    NhanVien, KhachHang, LoaiSanPham, SanPham,
    NhaCungCap, NhapHang, ChiTietNhapHang, SanPhamImage,
    HoaDon, ChiTietHoaDon, TaiKhoan, ChiNhanh, EmailOTP,
    ChiNhanhImage  
)

# Đổi giao diện Admin
admin.site.site_header = "Quản trị BHX"
admin.site.site_title = "BHX Admin"
admin.site.index_title = "Hệ thống quản lý Bách Hóa Xanh"

# ========================================================
# 1. CẤU HÌNH IMPORT/EXPORT BẰNG EXCEL CHO SẢN PHẨM
# ========================================================
@admin.register(SanPham)
class SanPhamAdmin(ImportExportModelAdmin): 
    list_display = ('ten_san_pham', 'gia_hien_tai', 'so_luong')
    search_fields = ('ten_san_pham',)

# ========================================================
# 2. CẤU HÌNH UP NHIỀU ẢNH CHO CỬA HÀNG (CHI NHÁNH)
# ========================================================
class ChiNhanhImageInline(admin.TabularInline):
    model = ChiNhanhImage
    extra = 3 # Hiển thị sẵn 3 ô up ảnh trống

@admin.register(ChiNhanh)
class ChiNhanhAdmin(admin.ModelAdmin):
    list_display = ('ten_chi_nhanh', 'dia_chi', 'dien_thoai')
    inlines = [ChiNhanhImageInline]

# ========================================================
# 3. ĐĂNG KÝ CÁC BẢNG CÒN LẠI 
# ========================================================
admin.site.register(NhanVien)
admin.site.register(KhachHang)
admin.site.register(LoaiSanPham)
# Đã XÓA dòng admin.site.register(SanPham) ở đây vì đã đăng ký ở mục 1
admin.site.register(SanPhamImage)
admin.site.register(NhaCungCap)
admin.site.register(NhapHang)
admin.site.register(ChiTietNhapHang)
admin.site.register(HoaDon)
admin.site.register(ChiTietHoaDon)
admin.site.register(TaiKhoan)
admin.site.register(EmailOTP)

# Nếu sếp muốn quản lý cả Bình Luận trong Admin thì mở thêm các dòng này:
# from .models import BinhLuanChiNhanh, BinhLuanChiNhanhImage
# admin.site.register(BinhLuanChiNhanh)
# admin.site.register(BinhLuanChiNhanhImage)