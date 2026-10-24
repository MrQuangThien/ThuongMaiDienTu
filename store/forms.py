from django import forms
from .models import SanPham, KhachHang, NhanVien, TaiKhoan, ChiNhanh, HoaDon, DanhGiaSanPham, BinhLuanSanPham

class BaseStyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                continue

            if isinstance(widget, forms.ClearableFileInput):
                widget.attrs.update({"class": "form-control-file"})
            elif isinstance(widget, forms.Textarea):
                widget.attrs.update({"class": "form-control", "rows": 4})
            elif isinstance(widget, forms.Select):
                widget.attrs.update({"class": "form-select"})
            else:
                widget.attrs.update({"class": "form-control"})


class NhanVienForm(BaseStyledForm):
    class Meta:
        model = NhanVien
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = TaiKhoan.objects.filter(role__in=["STAFF", "ADMIN"]).order_by("ho_ten")

        if self.instance and self.instance.pk and self.instance.tai_khoan_id:
            qs = TaiKhoan.objects.filter(role__in=["STAFF", "ADMIN"]) | TaiKhoan.objects.filter(id=self.instance.tai_khoan_id)
            qs = qs.distinct().order_by("ho_ten")

        self.fields["tai_khoan"].queryset = qs

    def clean_tai_khoan(self):
        tai_khoan = self.cleaned_data.get("tai_khoan")
        if tai_khoan and tai_khoan.role not in ["STAFF", "ADMIN"]:
            raise forms.ValidationError("Chỉ tài khoản nhân viên hoặc quản lý mới được liên kết.")
        return tai_khoan


class SanPhamForm(BaseStyledForm):
    class Meta:
        model = SanPham
        fields = "__all__"


class KhachHangForm(BaseStyledForm):
    class Meta:
        model = KhachHang
        fields = "__all__"


# =========================================================
# ĐÃ SỬA: LÀM ĐẸP VÀ ẨN Ô MẬT KHẨU CHO FORM TÀI KHOẢN
# =========================================================
class TaiKhoanForm(BaseStyledForm):
    class Meta:
        model = TaiKhoan
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        # Gọi class cha (BaseStyledForm) trước để nó format CSS cho các ô
        super().__init__(*args, **kwargs)

        if 'password_hash' in self.fields:
            # Đổi widget thành ô nhập mật khẩu (dấu chấm đen)
            self.fields['password_hash'].widget = forms.PasswordInput(render_value=False)
            
            # Cập nhật lại class CSS (vì đổi widget ở trên làm mất class form-control)
            self.fields['password_hash'].widget.attrs.update({"class": "form-control"})
            
            self.fields['password_hash'].required = False
            self.fields['password_hash'].label = "Mật khẩu"
            self.fields['password_hash'].help_text = "💡 Để trống ô này nếu bạn KHÔNG muốn thay đổi mật khẩu cũ."

            # Nếu đang sửa tài khoản đã có, tự động xóa trắng ô mật khẩu
            if self.instance and self.instance.pk:
                self.initial['password_hash'] = ''
# =========================================================


class ChiNhanhForm(BaseStyledForm):
    class Meta:
        model = ChiNhanh
        fields = "__all__"


class HoaDonForm(BaseStyledForm):
    class Meta:
        model = HoaDon
        fields = "__all__"


class DanhGiaSanPhamForm(forms.ModelForm):
    class Meta:
        model = DanhGiaSanPham
        fields = ["ten_nguoi_dung", "email", "so_sao", "noi_dung"]
        widgets = {
            "ten_nguoi_dung": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên của bạn"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email của bạn"}),
            "so_sao": forms.Select(
                choices=[(5, "5 sao"), (4, "4 sao"), (3, "3 sao"), (2, "2 sao"), (1, "1 sao")],
                attrs={"class": "form-select"}
            ),
            "noi_dung": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Nhập đánh giá của bạn"}),
        }

class BinhLuanSanPhamForm(forms.ModelForm):
    class Meta:
        model = BinhLuanSanPham
        fields = ["noi_dung", "so_sao"]
        widgets = {
            "noi_dung": forms.Textarea(attrs={
                "class": "comment-box-input",
                "rows": 4,
                "placeholder": "Mời bạn bình luận hoặc đặt câu hỏi"
            }),
            "so_sao": forms.HiddenInput(),
        }