# core_tools/gis_utils.py
from math import radians, cos, sin, asin, sqrt

def tinh_khoang_cach_km(lon1, lat1, lon2, lat2):
    """
    Công thức Haversine tính khoảng cách giữa 2 điểm GPS (đơn vị: km)
    """
    # Chuyển độ sang radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Công thức
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Bán kính trái đất (km)
    
    return round(c * r, 2)