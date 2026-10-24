# File: quanly_bhx_core/urls.py
from django.contrib import admin
from django.urls import path, include # <--- Nhớ import include
from django.conf import settings             # <-- Thêm dòng này
from django.conf.urls.static import static   # <-- Thêm dòng này
from store import views as store_views
# <-- Thêm nguyên đoạn này vào cuối file -->
# Lệnh này giúp Django biết cách lấy ảnh từ thư mục media ra để hiển thị trên web

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Nối dây đến app locations
    path('locations/', include('locations.urls')), 
    
    # (Sau này làm store và dashboard thì thêm tiếp vào đây)
    path("", store_views.home, name="home"),
    path("store/", include("store.urls")),
]

handler404 = "quanly_bhx_core.views.custom_404"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)