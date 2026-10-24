from django.urls import path
from . import views

# BẮT BUỘC PHẢI CÓ DÒNG NÀY ĐỂ HTML NHẬN DIỆN ĐƯỢC CHỮ 'locations:'
app_name = 'locations' 

urlpatterns = [
    path('ban-do/', views.map_search, name='map_search'),
    path('danh-sach/', views.danh_sach_cua_hang, name='store_list'),
    path('chi-tiet/<int:pk>/', views.store_detail, name='store_detail'),
    path('comment/<int:comment_id>/edit/', views.edit_store_comment, name='edit_store_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_store_comment, name='delete_store_comment'),
]