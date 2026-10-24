"""Quản lý tồn kho theo chi nhánh (TonKhoChiNhanh).

Các hàm reserve_stock / restore_stock PHẢI được gọi bên trong transaction.atomic()
vì dùng select_for_update để tránh bán vượt tồn khi nhiều người đặt cùng lúc.
"""
from collections import defaultdict

from .models import SanPham, TonKhoChiNhanh


class HetHangError(Exception):
    """Không đủ tồn kho tại chi nhánh."""


def get_branch_stock_map(chi_nhanh_id, product_ids):
    """Trả về {san_pham_id: so_luong_ton} của chi nhánh (không có dòng = 0)."""
    if not chi_nhanh_id:
        return {}
    rows = TonKhoChiNhanh.objects.filter(
        chi_nhanh_id=chi_nhanh_id, san_pham_id__in=list(product_ids)
    ).values_list("san_pham_id", "so_luong_ton")
    return dict(rows)


def _merge(items):
    merged = defaultdict(int)
    for product_id, qty in items:
        merged[int(product_id)] += int(qty)
    return merged


def reserve_stock(chi_nhanh_id, items):
    """Kiểm tra và trừ tồn của chi nhánh. items = [(san_pham_id, so_luong), ...]."""
    merged = _merge(items)
    if not chi_nhanh_id:
        raise HetHangError("Chưa xác định được chi nhánh để trừ tồn kho.")

    ton_khos = {
        tk.san_pham_id: tk
        for tk in TonKhoChiNhanh.objects.select_for_update()
        .select_related("san_pham")
        .filter(chi_nhanh_id=chi_nhanh_id, san_pham_id__in=list(merged))
    }

    # Kiểm tra toàn bộ trước, rồi mới trừ
    for product_id, qty in merged.items():
        tk = ton_khos.get(product_id)
        if tk is None:
            ten = SanPham.objects.filter(pk=product_id).values_list("ten_san_pham", flat=True).first()
            raise HetHangError(f"Sản phẩm '{ten or product_id}' hiện không có hàng tại chi nhánh này.")
        if qty > tk.so_luong_ton:
            raise HetHangError(
                f"Sản phẩm '{tk.san_pham.ten_san_pham}' chỉ còn {tk.so_luong_ton} tại chi nhánh này."
            )

    for product_id, qty in merged.items():
        tk = ton_khos[product_id]
        tk.so_luong_ton -= qty
        tk.save(update_fields=["so_luong_ton", "updated_at"])

    _adjust_global(merged, sign=-1)


def restore_stock(chi_nhanh_id, items):
    """Hoàn tồn về chi nhánh (khi hủy đơn)."""
    if not chi_nhanh_id:
        return
    merged = _merge(items)
    for product_id, qty in merged.items():
        tk = (
            TonKhoChiNhanh.objects.select_for_update()
            .filter(chi_nhanh_id=chi_nhanh_id, san_pham_id=product_id)
            .first()
        )
        if tk:
            tk.so_luong_ton += qty
            tk.save(update_fields=["so_luong_ton", "updated_at"])
    _adjust_global(merged, sign=+1)


def _adjust_global(merged, sign):
    """Giữ SanPham.so_luong (tổng toàn hệ thống) đồng bộ để dashboard admin đúng."""
    for sp in SanPham.objects.select_for_update().filter(pk__in=list(merged)):
        sp.so_luong = max(0, sp.so_luong + sign * merged[sp.pk])
        sp.save(update_fields=["so_luong"])
