import math
from PIL import Image, ImageDraw

class SimpleRasterization:
    """简化的光栅化算法实现（已解耦出主文件）"""

    @staticmethod
    def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> list:
        """Bresenham直线算法 - 整数运算，高效率"""
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1

        if dx > dy:
            err = dx / 2.0
            y = y0
            for x in range(x0, x1 + sx, sx):
                points.append((x, y))
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
        else:
            err = dy / 2.0
            x = x0
            for y in range(y0, y1 + sy, sy):
                points.append((x, y))
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
        return points

    @staticmethod
    def dda_line(x0: int, y0: int, x1: int, y1: int) -> list:
        """DDA直线算法 - 数字微分分析法"""
        points = []
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy))

        if steps == 0:
            return [(x0, y0)]

        x_inc = dx / steps
        y_inc = dy / steps

        x = float(x0)
        y = float(y0)

        for _ in range(steps + 1):
            points.append((int(round(x)), int(round(y))))
            x += x_inc
            y += y_inc

        return points

    @staticmethod
    def bresenham_circle(xc: int, yc: int, r: int) -> list:
        """Bresenham圆形算法 - 返回按圆周顺序排列的点"""
        points = []
        if r <= 0:
            return points

        octant_points = [[] for _ in range(8)]

        x = 0
        y = r
        d = 3 - 2 * r

        while x <= y:
            octant_points[0].append((xc + x, yc + y))
            octant_points[1].append((xc + y, yc + x))
            octant_points[2].append((xc + y, yc - x))
            octant_points[3].append((xc + x, yc - y))
            octant_points[4].append((xc - x, yc - y))
            octant_points[5].append((xc - y, yc - x))
            octant_points[6].append((xc - y, yc + x))
            octant_points[7].append((xc - x, yc + y))

            if d < 0:
                d = d + 4 * x + 6
            else:
                d = d + 4 * (x - y) + 10
                y -= 1
            x += 1

        for octant in octant_points:
            points.extend(octant)

        unique_points = list(dict.fromkeys(points))
        unique_points.sort(key=lambda p: math.atan2(p[1] - yc, p[0] - xc))

        if unique_points and unique_points[0] != unique_points[-1]:
            unique_points.append(unique_points[0])

        return unique_points

    @staticmethod
    def dda_circle(xc: int, yc: int, r: int) -> list:
        """DDA圆形算法 - 基于角度采样"""
        points = []
        if r <= 0:
            return points

        steps = max(int(2 * math.pi * r / 1.0), 12)

        for i in range(steps):
            theta = 2 * math.pi * i / steps
            x = xc + int(round(r * math.cos(theta)))
            y = yc + int(round(r * math.sin(theta)))
            pt = (x, y)
            if not points or points[-1] != pt:
                points.append(pt)

        if points and points[0] != points[-1]:
            points.append(points[0])

        return points

    @staticmethod
    def midpoint_circle(xc: int, yc: int, r: int) -> list:
        """Midpoint圆形算法 - 8对称性，整数运算"""
        points = []
        if r <= 0:
            return points

        octant_points = [[] for _ in range(8)]

        x = 0
        y = r
        d = 1 - r

        while x <= y:
            octant_points[0].append((xc + x, yc + y))
            octant_points[1].append((xc + y, yc + x))
            octant_points[2].append((xc + y, yc - x))
            octant_points[3].append((xc + x, yc - y))
            octant_points[4].append((xc - x, yc - y))
            octant_points[5].append((xc - y, yc - x))
            octant_points[6].append((xc - y, yc + x))
            octant_points[7].append((xc - x, yc + y))

            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1

        for octant in octant_points:
            for p in octant:
                if not points or points[-1] != p:
                    points.append(p)

        if points and points[0] != points[-1]:
            points.append(points[0])

        return points

    @staticmethod
    def midpoint_ellipse(xc: int, yc: int, a: int, b: int) -> list:
        """Midpoint椭圆算法 - 4对称性，标准整数实现"""
        points = set()
        if a <= 0 or b <= 0:
            return []

        def add_ellipse_points(x, y):
            points.update([
                (xc + x, yc + y), (xc - x, yc + y),
                (xc + x, yc - y), (xc - x, yc - y),
            ])

        a2 = a * a
        b2 = b * b
        two_a2 = 2 * a2
        two_b2 = 2 * b2

        # Region 1
        x = 0
        y = b
        d1 = round(b2 - a2 * b + 0.25 * a2)
        px = 0
        py = two_a2 * y

        while px < py:
            add_ellipse_points(x, y)
            x += 1
            px += two_b2
            if d1 < 0:
                d1 += b2 + px
            else:
                y -= 1
                py -= two_a2
                d1 += b2 + px - py
        
        # Region 2
        d2 = round(b2 * (x + 0.5)**2 + a2 * (y - 1)**2 - a2 * b2)
        
        while y >= 0:
            add_ellipse_points(x, y)
            y -= 1
            py -= two_a2
            if d2 > 0:
                d2 += a2 - py
            else:
                x += 1
                px += two_b2
                d2 += a2 - py + px

        return list(points)

    @staticmethod
    def scanline_fill(outline_points: list) -> list:
        """
        扫描线填充算法 - 用于填充闭合多边形内部
        输入：outline_points - 闭合多边形的顶点列表或边界点列表 [(x1,y1), (x2,y2), ...]
        输出：fill_points - 内部所有像素点的列表
        """
        if not outline_points or len(outline_points) < 3:
            return []

        vertices = []
        if len(outline_points) > 50:
            simplified = [outline_points[0]]
            for i in range(1, len(outline_points) - 1):
                p_prev = outline_points[i - 1]
                p_curr = outline_points[i]
                p_next = outline_points[i + 1]

                dx1 = p_curr[0] - p_prev[0]
                dy1 = p_curr[1] - p_prev[1]
                dx2 = p_next[0] - p_curr[0]
                dy2 = p_next[1] - p_curr[1]

                cross = dx1 * dy2 - dy1 * dx2
                if abs(cross) > 0.1:
                    simplified.append(p_curr)

            if simplified[-1] != outline_points[-1]:
                simplified.append(outline_points[-1])

            if len(simplified) >= 3:
                vertices = simplified
            else:
                vertices = outline_points
        else:
            vertices = outline_points

        fill_points = []

        y_coords = [p[1] for p in vertices]
        y_min = int(min(y_coords))
        y_max = int(max(y_coords))

        for y in range(y_min, y_max + 1):
            intersections = []

            for i in range(len(vertices)):
                p1 = vertices[i]
                p2 = vertices[(i + 1) % len(vertices)]

                y1, y2 = p1[1], p2[1]
                x1, x2 = p1[0], p2[0]

                if (y1 <= y <= y2) or (y2 <= y <= y1):
                    if y1 != y2:
                        t = (y - y1) / (y2 - y1)
                        x_intersect = x1 + t * (x2 - x1)
                        intersections.append(x_intersect)

            intersections.sort()

            for j in range(0, len(intersections) - 1, 2):
                x_start = int(intersections[j])
                x_end = int(intersections[j + 1])

                for x in range(x_start, x_end + 1):
                    fill_points.append((x, y))

        return fill_points

    @staticmethod
    def flood_fill(canvas_data: list, start_x: int, start_y: int, fill_color, target_color) -> list:
        """
        洪水填充算法 - 从起始点开始填充相邻的相同颜色区域
        使用栈-based实现，避免递归深度限制
        canvas_data: 二维列表，表示画布的像素颜色数据
        start_x, start_y: 起始点的坐标
        fill_color: 填充颜色
        target_color: 目标颜色（要被填充的颜色）
        返回：填充的像素点列表 [(x1,y1), (x2,y2), ...]
        """
        if not canvas_data or not canvas_data[0]:
            return []

        height = len(canvas_data)
        width = len(canvas_data[0])

        if start_x < 0 or start_x >= width or start_y < 0 or start_y >= height:
            return []

        if canvas_data[start_y][start_x] != target_color:
            return []

        filled_points = []
        stack = [(start_x, start_y)]
        visited = set()

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue
            visited.add((x, y))

            if canvas_data[y][x] == target_color:
                canvas_data[y][x] = fill_color
                filled_points.append((x, y))

                if x > 0:
                    stack.append((x - 1, y))
                if x < width - 1:
                    stack.append((x + 1, y))
                if y > 0:
                    stack.append((x, y - 1))
                if y < height - 1:
                    stack.append((x, y + 1))

        return filled_points