from django import forms
from store.models import BinhLuanChiNhanh

class BinhLuanChiNhanhForm(forms.ModelForm):
    class Meta:
        model = BinhLuanChiNhanh
        fields = ['so_sao', 'noi_dung']
        widgets = {
            'so_sao': forms.HiddenInput(attrs={'id': 'id_so_sao'}),
            'noi_dung': forms.Textarea(attrs={
                'class': 'comment-box-input',
                'placeholder': 'Mời bạn chia sẻ trải nghiệm về cửa hàng...',
                'rows': 4
            })
        }