# locations/models.py
from django.db import models
from store.models import TaiKhoan
class CuaHang(models.Model):
    ten_cua_hang = models.CharField(max_length=200, verbose_name="Tên cửa hàng")
    dia_chi = models.CharField(max_length=255, verbose_name="Địa chỉ")
    so_dien_thoai = models.CharField(max_length=20, verbose_name="Hotline")
    
    # Lưu tọa độ để vẽ lên bản đồ
    vi_do = models.FloatField(verbose_name="Latitude (Vĩ độ)")   # Ví dụ: 10.7769
    kinh_do = models.FloatField(verbose_name="Longitude (Kinh độ)") # Ví dụ: 106.7009
    
    hinh_anh = models.ImageField(upload_to='store_images/', blank=True, null=True)

    def __str__(self):
        return self.ten_cua_hang
    
    