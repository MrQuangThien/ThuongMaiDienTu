# locations/admin.py
from django.contrib import admin
from .models import CuaHang

# Cách 1: Đăng ký cơ bản (Nhanh gọn)
# admin.site.register(CuaHang)

# Cách 2: Đăng ký nâng cao (Có hiện cột, ô tìm kiếm - Nên dùng cách này)
@admin.register(CuaHang)
class CuaHangAdmin(admin.ModelAdmin):
    # Hiển thị các cột này ra ngoài danh sách
    list_display = ('ten_cua_hang', 'dia_chi', 'so_dien_thoai', 'vi_do', 'kinh_do')
    
    # Cho phép tìm kiếm theo tên và địa chỉ
    search_fields = ('ten_cua_hang', 'dia_chi')