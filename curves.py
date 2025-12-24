# curves.py
"""
参数曲线算法实现 - 完全手工实现，不使用现成库
包括：
1. Bézier曲线（二次、三次及任意次）
2. B样条曲线（二次、三次）
"""

import math


def factorial(n):
    """计算阶乘"""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def binomial_coefficient(n, i):
    """计算二项式系数 C(n, i)"""
    if i < 0 or i > n:
        return 0
    return factorial(n) // (factorial(i) * factorial(n - i))


def bernstein_polynomial(n, i, t):
    """
    Bernstein基函数
    B_{i,n}(t) = C(n,i) * t^i * (1-t)^(n-i)
    """
    return binomial_coefficient(n, i) * (t ** i) * ((1 - t) ** (n - i))


class BezierCurve:
    """Bézier曲线实现 - 支持任意次数"""
    
    def __init__(self, control_points):
        """
        初始化Bézier曲线
        control_points: 控制点列表 [(x0,y0), (x1,y1), ..., (xn,yn)]
        """
        self.control_points = control_points
        self.degree = len(control_points) - 1  # n次Bézier曲线需要n+1个控制点
    
    def evaluate(self, t):
        """
        计算曲线上参数为t的点
        使用Bernstein基函数
        P(t) = Σ(i=0 to n) B_{i,n}(t) * P_i
        """
        if not 0 <= t <= 1:
            t = max(0, min(1, t))
        
        n = self.degree
        x = 0
        y = 0
        
        for i, (px, py) in enumerate(self.control_points):
            basis = bernstein_polynomial(n, i, t)
            x += basis * px
            y += basis * py
        
        return (x, y)
    
    def generate_points(self, num_segments=100):
        """
        生成曲线上的离散点
        num_segments: 分段数量，越大曲线越光滑
        """
        points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            points.append(self.evaluate(t))
        return points
    
    def de_casteljau(self, t):
        """
        De Casteljau算法 - 递归细分法
        数值稳定性更好的Bézier曲线计算方法
        """
        if not 0 <= t <= 1:
            t = max(0, min(1, t))
        
        # 复制控制点
        points = [list(p) for p in self.control_points]
        n = len(points)
        
        # 递归细分
        for r in range(1, n):
            for i in range(n - r):
                points[i][0] = (1 - t) * points[i][0] + t * points[i + 1][0]
                points[i][1] = (1 - t) * points[i][1] + t * points[i + 1][1]
        
        return tuple(points[0])


class BSplineCurve:
    """B样条曲线实现"""
    
    def __init__(self, control_points, degree=3):
        """
        初始化B样条曲线
        control_points: 控制点列表
        degree: B样条的次数（2=二次，3=三次）
        """
        self.control_points = control_points
        self.degree = min(degree, len(control_points) - 1)
        self.n = len(control_points) - 1
        
        # 生成节点向量（均匀B样条）
        self.knots = self._generate_uniform_knots()
    
    def _generate_uniform_knots(self):
        """生成均匀节点向量（钳位B样条）"""
        # 钳位B样条：前后各有degree+1个重复节点
        # 总节点数 = n + p + 2，其中n是控制点数-1，p是次数
        knots = []
        
        # 前degree+1个节点为0（钳位起点）
        for i in range(self.degree + 1):
            knots.append(0.0)
        
        # 中间的内部节点
        num_internal = self.n - self.degree
        if num_internal > 0:
            for i in range(1, num_internal + 1):
                knots.append(i / (num_internal + 1))
        
        # 后degree+1个节点为1（钳位终点）
        for i in range(self.degree + 1):
            knots.append(1.0)
        
        return knots
    
    def _basis_function(self, i, p, t):
        """
        Cox-de Boor递归公式计算B样条基函数
        N_{i,p}(t)
        """
        # 检查索引是否有效
        if i < 0 or i + p + 1 >= len(self.knots):
            return 0.0
        
        if p == 0:
            # 零次基函数
            if i + 1 >= len(self.knots):
                return 0.0
            # 处理最后一个区间
            if i == len(self.knots) - 2 and abs(t - self.knots[-1]) < 1e-10:
                return 1.0
            return 1.0 if self.knots[i] <= t < self.knots[i + 1] else 0.0
        
        # 递归计算
        term1 = 0.0
        term2 = 0.0
        
        # 第一项
        if i + p < len(self.knots):
            denominator1 = self.knots[i + p] - self.knots[i]
            if abs(denominator1) > 1e-10:
                term1 = ((t - self.knots[i]) / denominator1) * self._basis_function(i, p - 1, t)
        
        # 第二项
        if i + p + 1 < len(self.knots):
            denominator2 = self.knots[i + p + 1] - self.knots[i + 1]
            if abs(denominator2) > 1e-10:
                term2 = ((self.knots[i + p + 1] - t) / denominator2) * self._basis_function(i + 1, p - 1, t)
        
        return term1 + term2
    
    def evaluate(self, t):
        """
        计算曲线上参数为t的点
        C(t) = Σ(i=0 to n) N_{i,p}(t) * P_i
        """
        if not 0 <= t <= 1:
            t = max(0, min(1, t))
        
        # 处理边界情况
        if t == 1.0:
            t = 1.0 - 1e-10
        
        x = 0
        y = 0
        
        for i in range(len(self.control_points)):
            basis = self._basis_function(i, self.degree, t)
            x += basis * self.control_points[i][0]
            y += basis * self.control_points[i][1]
        
        return (x, y)
    
    def generate_points(self, num_segments=100):
        """生成曲线上的离散点"""
        points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            if t > 0.999:  # 避免边界问题
                t = 0.999
            points.append(self.evaluate(t))
        return points


class CatmullRomSpline:
    """Catmull-Rom样条曲线 - 经典参数曲线"""
    
    def __init__(self, control_points, tension=0.5):
        """
        初始化Catmull-Rom样条
        control_points: 控制点列表
        tension: 张力参数（0-1），默认0.5
        """
        self.control_points = control_points
        self.tension = tension
    
    def evaluate_segment(self, p0, p1, p2, p3, t):
        """
        计算单个曲线段
        使用Catmull-Rom矩阵
        """
        t2 = t * t
        t3 = t2 * t
        
        # Catmull-Rom基矩阵系数
        c = self.tension
        
        x = (
            p1[0] +
            c * (-p0[0] + p2[0]) * t +
            c * (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
            c * (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
        )
        
        y = (
            p1[1] +
            c * (-p0[1] + p2[1]) * t +
            c * (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
            c * (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
        )
        
        return (x, y)
    
    def generate_points(self, num_segments_per_span=30):
        """生成曲线上的离散点"""
        if len(self.control_points) < 4:
            return self.control_points
        
        points = []
        n = len(self.control_points)
        
        # 对每个曲线段进行插值
        for i in range(n - 3):
            p0 = self.control_points[i]
            p1 = self.control_points[i + 1]
            p2 = self.control_points[i + 2]
            p3 = self.control_points[i + 3]
            
            for j in range(num_segments_per_span):
                t = j / num_segments_per_span
                point = self.evaluate_segment(p0, p1, p2, p3, t)
                points.append(point)
        
        # 添加最后一个点
        points.append(self.control_points[-2])
        
        return points
