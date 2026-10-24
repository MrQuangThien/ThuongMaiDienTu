from django.urls import path
from .views.admin import products as admin_products
from .views import auth
from .views import public
from . import views
from store.views.admin import dashboard
app_name = "store"

urlpatterns = [
    path('admin/products/import-excel/', admin_products.import_san_pham_excel, name='import_san_pham_excel'),
    path("chon-dia-chi/", public.location_picker, name="location_picker"),
    path("", views.home, name="home"),
    path("set-delivery-location/", public.set_delivery_location, name="set_delivery_location"),
    path('gioi-thieu/', public.about_view, name='about'),
    path("products/", views.product_list, name="product_list"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),

    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:pk>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_history, name="order_history"),
    path('dat-hang-thanh-cong/', views.order_success, name='order_success'),
    path("lich-su-giao-dich/", views.order_history, name="order_history_legacy"),
    path("huy-don-hang/<int:order_id>/", views.cancel_order, name="cancel_order"),

    path("login/", views.login_view, name="login"),
    path("login/email/", views.login_email_view, name="login_email"),
    path("login/phone/", views.login_phone_view, name="login_phone"),
    path("logout/", views.logout_view, name="logout"),

    path("register/", views.register_view, name="register"),
    path("register/email/", views.register_email_view, name="register_email"),
    path("register/phone/", views.register_phone_view, name="register_phone"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("resend-otp/", views.resend_otp_view, name="resend_otp"),
    path('quen-mat-khau/', views.forgot_password_view, name='forgot_password'),
    path('dat-lai-mat-khau/', views.reset_password_view, name='reset_password'),

    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/products/", views.admin_product_list, name="admin_product_list"),
    path("admin/products/create/", views.admin_product_create, name="admin_product_create"),
    path("admin/products/<int:pk>/edit/", views.admin_product_edit, name="admin_product_edit"),
    path("admin/products/<int:pk>/delete/", views.admin_product_delete, name="admin_product_delete"),
    path("admin/customers/", views.admin_customer_list, name="admin_customer_list"),
    path("admin/customers/create/", views.admin_customer_create, name="admin_customer_create"),
    path("admin/customers/<int:pk>/edit/", views.admin_customer_edit, name="admin_customer_edit"),
    path("admin/customers/<int:pk>/delete/", views.admin_customer_delete, name="admin_customer_delete"),
    path("admin/accounts/", views.admin_account_list, name="admin_account_list"),
    path("admin/accounts/create/", views.admin_account_create, name="admin_account_create"),
    path("admin/accounts/<int:pk>/edit/", views.admin_account_edit, name="admin_account_edit"),
    path("admin/accounts/<int:pk>/delete/", views.admin_account_delete, name="admin_account_delete"),
    path("admin/branches/", views.admin_branch_list, name="admin_branch_list"),
    path("admin/branches/create/", views.admin_branch_create, name="admin_branch_create"),
    path("admin/branches/<int:pk>/edit/", views.admin_branch_edit, name="admin_branch_edit"),
    path("admin/branches/<int:pk>/delete/", views.admin_branch_delete, name="admin_branch_delete"),
    path("admin/employees/", views.admin_employee_list, name="admin_employee_list"),
    path("admin/employees/create/", views.admin_employee_create, name="admin_employee_create"),
    path("admin/employees/<int:pk>/edit/", views.admin_employee_edit, name="admin_employee_edit"),
    path("admin/employees/<int:pk>/delete/", views.admin_employee_delete, name="admin_employee_delete"),
    path("admin/orders/", views.admin_order_list, name="admin_order_list"),
    path("admin/orders/create/", views.admin_order_create, name="admin_order_create"),
    path("admin/orders/<int:pk>/edit/", views.admin_order_edit, name="admin_order_edit"),
    path("admin/orders/<int:pk>/delete/", views.admin_order_delete, name="admin_order_delete"),

    path("pos/checkout/", views.pos_checkout_view, name="pos_checkout"),
    path("pos/add/<int:pk>/", views.pos_add_item, name="pos_add_item"),
    path("pos/update/<int:pk>/", views.pos_update_item, name="pos_update_item"),
    path("pos/remove/<int:pk>/", views.pos_remove_item, name="pos_remove_item"),
    path("pos/confirm/", views.pos_confirm_checkout, name="pos_confirm_checkout"),
    path("pos/invoice/", views.pos_invoice_view, name="pos_invoice"),
    path("cart/update/<int:pk>/", views.update_cart_quantity, name="update_cart_quantity"),
    path("cart/save-options/", views.save_checkout_options, name="save_checkout_options"),

    path("comments/<int:pk>/edit/", views.edit_product_comment, name="edit_product_comment"),
    path("comments/<int:pk>/delete/", views.delete_product_comment, name="delete_product_comment"),
    
    path("admin/inventory/", views.inventory_management, name="inventory_management"),
    path("staff/inventory/", views.staff_inventory, name="staff_inventory"),

    path("staff/inventory/<int:pk>/update/", views.inventory_update, name="inventory_update"),
    path('admin/export-excel/', dashboard.export_dashboard_excel, name='export_excel'),
]
