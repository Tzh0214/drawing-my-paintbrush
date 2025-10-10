import math

def rotate_point(x, y, angle_rad, center_x, center_y):
    """旋转点坐标的工具函数"""
    new_x = center_x + (x - center_x) * math.cos(angle_rad) - (y - center_y) * math.sin(angle_rad)
    new_y = center_y + (x - center_x) * math.sin(angle_rad) + (y - center_y) * math.cos(angle_rad)
    return new_x, new_y