from functools import wraps
import random

from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils.html import strip_tags
from ..models import TaiKhoan

def ensure_admin_account():
    admin_acc, created = TaiKhoan.objects.get_or_create(
        email="admin@bhx.local",
        defaults={
            "password_hash": make_password("admin123"),
            "ho_ten": "Quản trị viên",
            "dien_thoai": "0909000000",
            "role": "ADMIN",
            "trang_thai": "ACTIVE",
        },
    )

    if created:
        return

    updated = False

    if admin_acc.ho_ten != "Quản trị viên":
        admin_acc.ho_ten = "Quản trị viên"
        updated = True

    if admin_acc.dien_thoai != "0909000000":
        admin_acc.dien_thoai = "0909000000"
        updated = True

    if admin_acc.role != "ADMIN":
        admin_acc.role = "ADMIN"
        updated = True

    if admin_acc.trang_thai != "ACTIVE":
        admin_acc.trang_thai = "ACTIVE"
        updated = True

    if not check_password("admin123", admin_acc.password_hash):
        admin_acc.password_hash = make_password("admin123")
        updated = True

    if updated:
        admin_acc.save()


def paginate_queryset(request, queryset, per_page=8):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)


def generate_otp():
    return f"{random.randint(100000, 999999)}"

def send_otp_email(email, otp_code):
    subject = "Mã OTP xác thực tài khoản Bách Hóa Xanh"
    
    # 1. Giao diện HTML chuẩn chỉnh với tông xanh lá
    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; border: 1px solid #e5e7eb; border-radius: 12px; padding: 30px; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #008a37; margin: 0; font-size: 28px;">BÁCH HÓA XANH</h2>
            <p style="color: #64748b; margin-top: 5px; font-size: 14px;">Hệ thống mua sắm trực tuyến</p>
        </div>
        
        <p style="color: #333; font-size: 16px; line-height: 1.5;">Xin chào,</p>
        <p style="color: #333; font-size: 16px; line-height: 1.5;">Bạn vừa yêu cầu mã OTP để xác thực tài khoản. Vui lòng sử dụng mã dưới đây để tiếp tục:</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <span style="display: inline-block; font-size: 34px; font-weight: bold; color: #008a37; letter-spacing: 8px; background: #eef8f2; padding: 15px 30px; border-radius: 10px; border: 2px dashed #008a37;">
                {otp_code}
            </span>
        </div>
        
        <p style="color: #d8232a; font-size: 14px; font-weight: bold; text-align: center;">
            ⏳ Mã OTP này có hiệu lực trong vòng 5 phút!
        </p>
        <p style="color: #64748b; font-size: 14px; line-height: 1.6; text-align: center; margin-top: 20px;">
            Tuyệt đối <strong style="color: #d8232a;">KHÔNG CHIA SẺ</strong> mã OTP cho bất kỳ ai, kể cả nhân viên Bách Hóa Xanh để bảo vệ tài khoản của bạn.
        </p>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">
        <p style="color: #94a3b8; font-size: 12px; text-align: center; margin: 0;">
            Email này được tạo tự động. Vui lòng không trả lời email này.<br>
            &copy; 2026 Bách Hóa Xanh. Trân trọng cảm ơn.
        </p>
    </div>
    """
    
    # 2. Tạo bản text thường (phòng khi thiết bị của khách không hỗ trợ hiển thị HTML)
    plain_message = strip_tags(html_message)

    # 3. Bắn mail đi
    send_mail(
        subject,
        plain_message,
        'no-reply@bachhoaxanh.local',
        [email],
        html_message=html_message,
        fail_silently=False,
    )

def send_reset_password_email(email, otp_code):
    subject = "Mã OTP khôi phục mật khẩu Bách Hóa Xanh"
    
    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; border: 1px solid #e5e7eb; border-radius: 12px; padding: 30px; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #d8232a; margin: 0; font-size: 28px;">BÁCH HÓA XANH</h2>
            <p style="color: #64748b; margin-top: 5px; font-size: 14px;">Yêu cầu đặt lại mật khẩu</p>
        </div>
        
        <p style="color: #333; font-size: 16px; line-height: 1.5;">Xin chào,</p>
        <p style="color: #333; font-size: 16px; line-height: 1.5;">Hệ thống vừa nhận được yêu cầu <strong>Khôi phục mật khẩu</strong> cho tài khoản liên kết với email này. Vui lòng sử dụng mã dưới đây để tạo mật khẩu mới:</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <span style="display: inline-block; font-size: 34px; font-weight: bold; color: #d8232a; letter-spacing: 8px; background: #fef2f2; padding: 15px 30px; border-radius: 10px; border: 2px dashed #d8232a;">
                {otp_code}
            </span>
        </div>
        
        <p style="color: #64748b; font-size: 14px; line-height: 1.6; text-align: center;">
            ⚠️ Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email. Tuyệt đối không chia sẻ mã này cho người khác.
        </p>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">
        <p style="color: #94a3b8; font-size: 12px; text-align: center; margin: 0;">
            Email này được tạo tự động. Vui lòng không trả lời email này.<br>
            &copy; 2026 Bách Hóa Xanh. Trân trọng cảm ơn.
        </p>
    </div>
    """
    
    plain_message = f"Mã OTP khôi phục mật khẩu của bạn là: {otp_code}. Mã có hiệu lực 5 phút. Nếu không phải bạn yêu cầu, vui lòng bỏ qua."

    send_mail(
        subject,
        plain_message,
        'no-reply@bachhoaxanh.local',
        [email],
        html_message=html_message,
        fail_silently=False,
    )
def _current_role(request):
    """Lấy role từ DB (không tin session cũ); tài khoản bị khóa/xóa sẽ bị đăng xuất."""
    tai_khoan_id = request.session.get("tai_khoan_id")
    if not tai_khoan_id:
        return None
    tai_khoan = TaiKhoan.objects.filter(id=tai_khoan_id, trang_thai="ACTIVE").first()
    if not tai_khoan:
        request.session.flush()
        return None
    request.session["role"] = tai_khoan.role
    return tai_khoan.role


def _role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            role = _current_role(request)
            if role is None:
                return redirect("store:login")
            if role not in allowed_roles:
                return redirect("store:home")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ADMIN + STAFF
admin_required = _role_required(("ADMIN", "STAFF"))
# Chỉ ADMIN (quản lý tài khoản, nhân viên, nhập sản phẩm bằng Excel...)
admin_only = _role_required(("ADMIN",))


def render_admin_form(request, form_class, title, success_url, instance=None):
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)

            if isinstance(obj, TaiKhoan):
                raw_password = form.cleaned_data.get("password_hash")
                
                if raw_password: 
                    if not str(raw_password).startswith("pbkdf2_"):
                        obj.password_hash = make_password(raw_password)
                else:
                    if instance and instance.pk:
                        old_obj = TaiKhoan.objects.get(pk=instance.pk)
                        obj.password_hash = old_obj.password_hash

            obj.save()
            return redirect(success_url)
    else:
        form = form_class(instance=instance)

    return render(
        request,
        "store/admin/form.html",
        {
            "form": form,
            "title": title,
        },
    )


def render_admin_delete(request, obj, title, success_url):
    if request.method == "POST":
        obj.delete()
        return redirect(success_url)

    return render(
        request,
        "store/admin/confirm_delete.html",
        {
            "object": obj,
            "title": title,
        },
    )