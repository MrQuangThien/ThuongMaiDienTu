import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0016_sanpham_bao_quan_sanpham_cach_su_dung_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='hoadon',
            name='chi_nhanh',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='hoa_dons',
                to='store.chinhanh',
            ),
        ),
    ]
