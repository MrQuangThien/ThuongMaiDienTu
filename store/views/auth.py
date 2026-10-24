from datetime import timedelta
import email
import random
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from ..models import EmailOTP, TaiKhoan
from .common import generate_otp, send_otp_email, send_reset_password_email


SESSION_USER_KEYS = ("tai_khoan_id", "ho_ten", "role")


def _set_login_session(request, tai_khoan):
    request.session["tai_khoan_id"] = tai_khoan.id
    request.session["ho_ten"] = tai_khoan.ho_ten
    request.session["role"] = tai_khoan.role


def _validate_passwords(password, confirm_password):
    if not password or not confirm_password:
        return "Vui lòng nhập đầy đủ thông tin."
    if password != confirm_password:
        return "Mật khẩu nhập lại không khớp."
    return ""


def _validate_email_value(email):
    if not email:
        return "Vui lòng nhập email."
    try:
        validate_email(email)
    except ValidationError:
        return "Email không hợp lệ."
    return ""


def _validate_phone_value(phone):
    if not phone:
        return "Vui lòng nhập số điện thoại."
    if not phone.isdigit() or len(phone) < 9 or len(phone) > 11:
        return "Số điện thoại không hợp lệ."
    return ""


def _create_email_otp(tai_khoan, email):
    otp_code = generate_otp()
    EmailOTP.objects.create(
        tai_khoan=tai_khoan,
        email=email,
        otp_code=otp_code,
        expires_at=timezone.now() + timedelta(minutes=5),
        is_used=False,
    )
    send_otp_email(email, otp_code)


def register_view(request):
    return redirect("store:register_phone")


def login_view(request):
    # Template store/login.html không tồn tại -> dùng trang đăng nhập bằng email
    return redirect("store:login_email")


def logout_view(request):
    request.session.flush()
    return redirect("store:home")


def register_phone_view(request):
    error = ""

    if request.method == "POST":
        ho_ten = request.POST.get("ho_ten", "").strip()
        dien_thoai = request.POST.get("dien_thoai", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not ho_ten:
            error = "Vui lòng nhập đầy đủ thông tin."
        else:
            error = _validate_phone_value(dien_thoai) or _validate_passwords(password, confirm_password)

        if not error and TaiKhoan.objects.filter(dien_thoai=dien_thoai).exists():
            error = "Số điện thoại đã được sử dụng."

        if not error:
            TaiKhoan.objects.create(
                ho_ten=ho_ten,
                dien_thoai=dien_thoai,
                email=None,
                password_hash=make_password(password),
                role="USER",
                trang_thai="ACTIVE",
            )
            return redirect("store:login_phone")

    return render(request, "store/register_phone.html", {"error": error})


# ======================================================================
# ĐÃ SỬA HÀM NÀY: LIÊN KẾT VỚI LUỒNG GỬI OTP VÀ CHUYỂN HƯỚNG SANG TRANG NHẬP MÃ
# ======================================================================
def register_email_view(request):
    error = ""

    if request.method == "POST":
        ho_ten = request.POST.get("ho_ten", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not ho_ten or not email or not password or not confirm_password:
            error = "Vui lòng nhập đầy đủ thông tin."
        elif password != confirm_password:
            error = "Mật khẩu nhập lại không khớp."
        else:
            try:
                validate_email(email)
            except ValidationError:
                error = "Email không hợp lệ."

        if not error and TaiKhoan.objects.filter(email=email).exists():
            error = "Email đã được sử dụng."

        if not error:
            with transaction.atomic():
                # 1. Tạo tài khoản với trạng thái PENDING
                new_user = TaiKhoan.objects.create(
                    ho_ten=ho_ten,
                    email=email,
                    dien_thoai=None,
                    password_hash=make_password(password),
                    role="USER",
                    trang_thai="PENDING", # <-- Đổi từ ACTIVE sang PENDING
                )
                
                # 2. Gọi hàm sinh OTP và gửi mail sếp đã viết sẵn ở trên
                _create_email_otp(new_user, email)
                
                # 3. Ghi nhớ ID và Email vào session để hàm verify_otp_view biết mà kiểm tra
                request.session["pending_user_id"] = new_user.id
                request.session["pending_email"] = email
                
            # 4. Chuyển hướng qua trang nhập mã OTP
            return redirect("store:verify_otp")

    return render(request, "store/register_email.html", {"error": error})
# ======================================================================


def login_phone_view(request):
    error = ""

    if request.method == "POST":
        dien_thoai = request.POST.get("dien_thoai", "").strip()
        password = request.POST.get("password", "").strip()

        error = _validate_phone_value(dien_thoai)
        
        if not error and not password:
            error = "Vui lòng nhập đầy đủ thông tin."

        if not error:
            tai_khoan = TaiKhoan.objects.filter(
                dien_thoai=dien_thoai,
                trang_thai="ACTIVE",
            ).first()

            if not tai_khoan:
                error = "Tài khoản không tồn tại."
            elif not check_password(password, tai_khoan.password_hash):
                error = "Sai mật khẩu."
            else:
                _set_login_session(request, tai_khoan)
                return redirect("store:home")

    return render(request, "store/login_phone.html", {"error": error})


def login_email_view(request):
    error = ""

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        error = _validate_email_value(email)
        if not error and not password:
            error = "Vui lòng nhập đầy đủ thông tin."

        if not error:
            tai_khoan = TaiKhoan.objects.filter(
                email=email,
                trang_thai="ACTIVE",
            ).first()

            if not tai_khoan:
                error = "Tài khoản không tồn tại hoặc chưa xác thực email."
            elif not check_password(password, tai_khoan.password_hash):
                error = "Sai mật khẩu."
            else:
                _set_login_session(request, tai_khoan)
                return redirect("store:home")

    return render(request, "store/login_email.html", {"error": error})


def verify_otp_view(request):
    error = ""

    pending_user_id = request.session.get("pending_user_id")
    pending_email = request.session.get("pending_email")

    if not pending_user_id or not pending_email:
        return redirect("store:register_email")

    tai_khoan = TaiKhoan.objects.filter(id=pending_user_id, email=pending_email).first()
    if not tai_khoan:
        return redirect("store:register_email")

    if request.method == "POST":
        otp_code = request.POST.get("otp_code", "").strip()
        latest_otp = EmailOTP.objects.filter(
            tai_khoan=tai_khoan,
            email=pending_email,
            is_used=False,
        ).order_by("-created_at").first()

        if not otp_code:
            error = "Vui lòng nhập mã OTP."
        elif not latest_otp:
            error = "Không tìm thấy OTP hợp lệ."
        elif latest_otp.is_expired():
            error = "Mã OTP đã hết hạn."
        elif latest_otp.otp_code != otp_code:
            error = "Mã OTP không đúng."
        else:
            latest_otp.is_used = True
            latest_otp.save()

            tai_khoan.trang_thai = "ACTIVE"
            tai_khoan.save()

            request.session.pop("pending_user_id", None)
            request.session.pop("pending_email", None)
            return redirect("store:login_email")

    return render(
        request,
        "store/verify_otp.html",
        {
            "email": pending_email,
            "error": error,
        },
    )


def resend_otp_view(request):
    pending_user_id = request.session.get("pending_user_id")
    pending_email = request.session.get("pending_email")

    if not pending_user_id or not pending_email:
        return redirect("store:register_email")

    tai_khoan = TaiKhoan.objects.filter(id=pending_user_id, email=pending_email).first()
    if not tai_khoan:
        return redirect("store:register_email")

    EmailOTP.objects.filter(tai_khoan=tai_khoan, is_used=False).update(is_used=True)
    _create_email_otp(tai_khoan, pending_email)
    return redirect("store:verify_otp")

# 1. Trang nhập email để lấy lại mật khẩu
def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            # Kiểm tra xem email có trong hệ thống không
            tai_khoan = TaiKhoan.objects.get(email=email)
            
            # Tạo mã OTP 6 số
            otp_code = str(random.randint(100000, 999999))
            
            # Lưu tạm OTP và Email vào session để trang sau dùng
            request.session['reset_otp'] = otp_code
            request.session['reset_email'] = email
            
            try:
                send_reset_password_email(email, otp_code)
            except Exception as e:
                print(f"Lỗi gửi mail: {e}")
                return render(request, 'store/forgot_password.html', {
                    'error': 'Hệ thống đang bận gửi mail (Mailtrap limit), vui lòng thử lại sau 30 giây!'
                })
            
            return redirect('store:reset_password')
            
        except TaiKhoan.DoesNotExist:
            return render(request, 'store/forgot_password.html', {
                'error': 'Email này chưa được đăng ký trong hệ thống!'
            })
            return render(request, 'store/forgot_password.html')
            return redirect('store:reset_password')
            
        except TaiKhoan.DoesNotExist:
            return render(request, 'store/forgot_password.html', {'error': 'Email này chưa được đăng ký trong hệ thống!'})

    return render(request, 'store/forgot_password.html')

# 2. Trang nhập OTP và đổi mật khẩu mới
def reset_password_view(request):
    email = request.session.get('reset_email')
    
    # Nếu không có email trong session (vào lụi) thì đuổi về trang quên mật khẩu
    if not email:
        return redirect('store:forgot_password')

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if otp_code != request.session.get('reset_otp'):
            return render(request, 'store/reset_password.html', {'error': 'Mã OTP không chính xác!', 'email': email})
            
        if new_password != confirm_password:
            return render(request, 'store/reset_password.html', {'error': 'Mật khẩu xác nhận không khớp!', 'email': email})

        # Lưu mật khẩu mới vào Database (nhớ mã hóa)
        tai_khoan = TaiKhoan.objects.get(email=email)
        tai_khoan.password_hash = make_password(new_password)
        tai_khoan.save()

        # Dọn dẹp session cho sạch sẽ
        del request.session['reset_otp']
        del request.session['reset_email']

        # Xong xuôi thì đá về trang đăng nhập
        return redirect('store:login_email')

    return render(request, 'store/reset_password.html', {'email': email})