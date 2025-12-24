# surfaces.py
"""
参数曲面算法实现 - 完全手工实现
包括：
1. Bézier曲面（张量积，基于矩形控制网格）
2. 三边Bézier曲面（基于三角域Bernstein基）
"""

import math
from curves import binomial_coefficient, bernstein_polynomial


class BezierSurface:
    """Bézier曲面（张量积形式） - 基于矩形控制网格"""
    
    def __init__(self, control_grid):
        """
        初始化Bézier曲面
        control_grid: 控制点网格，形式为 [[(x,y,z), ...], ...]
                     外层列表表示u方向，内层列表表示v方向
        例如：3x3网格表示二次x二次Bézier曲面
        """
        self.control_grid = control_grid
        self.m = len(control_grid) - 1  # u方向次数
        self.n = len(control_grid[0]) - 1  # v方向次数
    
    def evaluate(self, u, v):
        """
        计算曲面上参数为(u,v)的点
        S(u,v) = Σ Σ B_{i,m}(u) * B_{j,n}(v) * P_{i,j}
        """
        u = max(0, min(1, u))
        v = max(0, min(1, v))
        
        x = 0
        y = 0
        z = 0
        
        for i in range(self.m + 1):
            for j in range(self.n + 1):
                # 计算Bernstein基函数的乘积
                basis = (bernstein_polynomial(self.m, i, u) * 
                        bernstein_polynomial(self.n, j, v))
                
                px, py, pz = self.control_grid[i][j]
                x += basis * px
                y += basis * py
                z += basis * pz
        
        return (x, y, z)
    
    def generate_mesh(self, u_segments=20, v_segments=20):
        """
        生成曲面网格
        返回：(点列表, 面片列表)
        """
        points = []
        faces = []
        
        # 生成网格点
        for i in range(u_segments + 1):
            u = i / u_segments
            for j in range(v_segments + 1):
                v = j / v_segments
                point = self.evaluate(u, v)
                points.append(point)
        
        # 生成面片（四边形或三角形）
        for i in range(u_segments):
            for j in range(v_segments):
                # 当前四边形的四个顶点索引
                p0 = i * (v_segments + 1) + j
                p1 = p0 + 1
                p2 = (i + 1) * (v_segments + 1) + j + 1
                p3 = p2 - 1
                
                # 将四边形分为两个三角形
                faces.append((p0, p1, p2))
                faces.append((p0, p2, p3))
        
        return points, faces
    
    def get_isocurves(self, num_u_curves=5, num_v_curves=5, segments_per_curve=30):
        """
        获取等参曲线（用于网格线显示）
        返回：(u方向曲线列表, v方向曲线列表)
        """
        u_curves = []
        v_curves = []
        
        # u方向等参曲线（固定u，改变v）
        for i in range(num_u_curves):
            u = i / (num_u_curves - 1)
            curve = []
            for j in range(segments_per_curve + 1):
                v = j / segments_per_curve
                point = self.evaluate(u, v)
                curve.append(point)
            u_curves.append(curve)
        
        # v方向等参曲线（固定v，改变u）
        for j in range(num_v_curves):
            v = j / (num_v_curves - 1)
            curve = []
            for i in range(segments_per_curve + 1):
                u = i / segments_per_curve
                point = self.evaluate(u, v)
                curve.append(point)
            v_curves.append(curve)
        
        return u_curves, v_curves


class TriangularBezierSurface:
    """三边Bézier曲面 - 基于三角域Bernstein基"""
    
    def __init__(self, control_points, degree=2):
        """
        初始化三边Bézier曲面
        control_points: 控制点字典 {(i,j,k): (x,y,z), ...}
                       其中 i+j+k=n (n为曲面次数)
        degree: 曲面次数
        
        例如，二次三边Bézier曲面需要6个控制点：
        (2,0,0), (1,1,0), (1,0,1), (0,2,0), (0,1,1), (0,0,2)
        """
        self.control_points = control_points
        self.degree = degree
        self._validate_control_points()
    
    def _validate_control_points(self):
        """验证控制点配置是否正确"""
        expected_count = (self.degree + 1) * (self.degree + 2) // 2
        if len(self.control_points) != expected_count:
            raise ValueError(f"For degree {self.degree}, need {expected_count} control points")
    
    def _triangular_bernstein(self, i, j, k, u, v, w):
        """
        三角域Bernstein基函数
        B_{i,j,k}^n(u,v,w) = (n!/(i!j!k!)) * u^i * v^j * w^k
        其中 i+j+k=n, u+v+w=1
        """
        n = self.degree
        coeff = (factorial(n) // 
                (factorial(i) * factorial(j) * factorial(k)))
        return coeff * (u ** i) * (v ** j) * (w ** k)
    
    def evaluate(self, u, v):
        """
        计算曲面上参数为(u,v)的点
        重心坐标：w = 1-u-v
        """
        u = max(0, min(1, u))
        v = max(0, min(1, v))
        
        # 确保在三角形域内
        if u + v > 1:
            total = u + v
            u = u / total
            v = v / total
        
        w = 1 - u - v
        
        x = 0
        y = 0
        z = 0
        
        # 遍历所有控制点
        for (i, j, k), (px, py, pz) in self.control_points.items():
            basis = self._triangular_bernstein(i, j, k, u, v, w)
            x += basis * px
            y += basis * py
            z += basis * pz
        
        return (x, y, z)
    
    def generate_mesh(self, segments=20):
        """
        生成三角形曲面网格
        """
        points = []
        faces = []
        
        # 在三角形域内均匀采样
        point_map = {}
        idx = 0
        
        for i in range(segments + 1):
            u = i / segments
            for j in range(segments + 1 - i):
                v = j / segments
                if u + v <= 1.0 + 1e-10:
                    point = self.evaluate(u, v)
                    points.append(point)
                    point_map[(i, j)] = idx
                    idx += 1
        
        # 生成三角形面片
        for i in range(segments):
            for j in range(segments - i):
                # 当前三角形的三个顶点
                if (i, j) in point_map and (i+1, j) in point_map and (i, j+1) in point_map:
                    p0 = point_map[(i, j)]
                    p1 = point_map[(i+1, j)]
                    p2 = point_map[(i, j+1)]
                    faces.append((p0, p1, p2))
                
                # 如果存在第二个三角形
                if j < segments - i - 1:
                    if (i+1, j) in point_map and (i+1, j+1) in point_map and (i, j+1) in point_map:
                        p0 = point_map[(i+1, j)]
                        p1 = point_map[(i+1, j+1)]
                        p2 = point_map[(i, j+1)]
                        faces.append((p0, p1, p2))
        
        return points, faces


def factorial(n):
    """计算阶乘"""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
