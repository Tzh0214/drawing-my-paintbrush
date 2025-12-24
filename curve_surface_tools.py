# curve_surface_tools.py
"""
曲线与曲面绘制工具的集成模块
提供交互式控制点编辑和实时预览功能
"""

import math
from curves import BezierCurve, BSplineCurve, CatmullRomSpline
from surfaces import BezierSurface, TriangularBezierSurface
from raster import SimpleRasterization


class CurveTool:
    """曲线工具基类"""
    
    def __init__(self, canvas, app, color='#FFFFFF'):
        self.canvas = canvas
        self.app = app  # 保存app引用以访问坐标转换
        self.control_points = []  # 存储逻辑坐标
        self.control_point_ids = []
        self.curve_id = None
        self.preview_lines = []
        self.is_editing = False
        self.curve_tag = None
        self.curve_color = color  # 曲线颜色
        
    def add_control_point(self, screen_x, screen_y):
        """添加控制点（输入为屏幕坐标）"""
        from coordinate_system import screen_to_logical
        
        # 将屏幕坐标转换为逻辑坐标存储
        self.canvas.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        
        logical_coords = screen_to_logical(
            [screen_x, screen_y],
            self.app.zoom_level,
            self.app.pan_offset_x,
            self.app.pan_offset_y,
            canvas_width,
            canvas_height
        )
        
        logical_x, logical_y = logical_coords[0], logical_coords[1]
        self.control_points.append((logical_x, logical_y))
        
        # 使用屏幕坐标绘制控制点（小圆圈）
        point_id = self.canvas.create_oval(
            screen_x - 4, screen_y - 4, screen_x + 4, screen_y + 4,
            fill='red', outline='white', width=2,
            tags=(self.curve_tag, 'control_point')
        )
        self.control_point_ids.append(point_id)
        
    def update_curve_preview(self):
        """更新曲线预览"""
        pass  # 由子类实现
        
    def clear(self):
        """清除所有元素"""
        for pid in self.control_point_ids:
            self.canvas.delete(pid)
        if self.curve_id:
            self.canvas.delete(self.curve_id)
        for line_id in self.preview_lines:
            self.canvas.delete(line_id)
        
        self.control_points = []
        self.control_point_ids = []
        self.curve_id = None
        self.preview_lines = []


class BezierCurveTool(CurveTool):
    """Bézier曲线工具"""
    
    def __init__(self, canvas, app, curve_type='cubic', color='#FFFFFF'):
        super().__init__(canvas, app, color)
        self.curve_type = curve_type  # 'quadratic' or 'cubic' or 'any'
        self.required_points = {
            'quadratic': 3,
            'cubic': 4,
            'any': -1  # 任意数量
        }
        
    def update_curve_preview(self):
        """更新Bézier曲线预览"""
        if len(self.control_points) < 2:
            return
        
        # 删除旧曲线
        if self.curve_id:
            self.canvas.delete(self.curve_id)
        
        # 绘制控制多边形（虚线）
        for line_id in self.preview_lines:
            self.canvas.delete(line_id)
        self.preview_lines = []
        
        for i in range(len(self.control_points) - 1):
            x0, y0 = self.control_points[i]
            x1, y1 = self.control_points[i + 1]
            line_id = self.canvas.create_line(
                x0, y0, x1, y1,
                fill='gray', dash=(4, 4), width=1,
                tags=(self.curve_tag, 'control_polygon')
            )
            self.preview_lines.append(line_id)
        
        # 生成并绘制Bézier曲线
        required = self.required_points[self.curve_type]
        if required == -1 or len(self.control_points) == required:
            bezier = BezierCurve(self.control_points)
            curve_points = bezier.generate_points(num_segments=100)
            
            # 使用光栅化算法绘制曲线
            flat_points = []
            for x, y in curve_points:
                flat_points.extend([x, y])
            
            self.curve_id = self.canvas.create_line(
                flat_points,
                fill=self.curve_color, width=2, smooth=True,
                tags=(self.curve_tag, 'bezier_curve')
            )
    
    def can_finish(self):
        """检查是否可以完成曲线"""
        required = self.required_points[self.curve_type]
        if required == -1:
            return len(self.control_points) >= 2
        return len(self.control_points) == required


class BSplineCurveTool(CurveTool):
    """B样条曲线工具"""
    
    def __init__(self, canvas, app, degree=3, color='#FFFFFF'):
        super().__init__(canvas, app, color)
        self.degree = degree
        
    def update_curve_preview(self):
        """更新B样条曲线预览"""
        if len(self.control_points) < self.degree + 1:
            return
        
        from coordinate_system import logical_to_screen
        
        # 删除旧曲线
        if self.curve_id:
            self.canvas.delete(self.curve_id)
        
        # 绘制控制多边形
        for line_id in self.preview_lines:
            self.canvas.delete(line_id)
        self.preview_lines = []
        
        self.canvas.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        
        for i in range(len(self.control_points) - 1):
            # 将逻辑坐标转换为屏幕坐标
            logical_coords = [self.control_points[i][0], self.control_points[i][1],
                            self.control_points[i + 1][0], self.control_points[i + 1][1]]
            screen_coords = logical_to_screen(
                logical_coords,
                self.app.zoom_level,
                self.app.pan_offset_x,
                self.app.pan_offset_y,
                canvas_width,
                canvas_height
            )
            line_id = self.canvas.create_line(
                screen_coords,
                fill='gray', dash=(4, 4), width=1,
                tags=(self.curve_tag, 'control_polygon')
            )
            self.preview_lines.append(line_id)
        
        # 生成并绘制B样条曲线
        bspline = BSplineCurve(self.control_points, self.degree)
        curve_points = bspline.generate_points(num_segments=100)
        
        # 将曲线点转换为屏幕坐标
        logical_curve_coords = []
        for x, y in curve_points:
            logical_curve_coords.extend([x, y])
        
        screen_curve_coords = logical_to_screen(
            logical_curve_coords,
            self.app.zoom_level,
            self.app.pan_offset_x,
            self.app.pan_offset_y,
            canvas_width,
            canvas_height
        )
        
        self.curve_id = self.canvas.create_line(
            screen_curve_coords,
            fill=self.curve_color, width=2, smooth=True,
            tags=(self.curve_tag, 'bspline_curve')
        )
    
    def can_finish(self):
        """检查是否可以完成曲线"""
        return len(self.control_points) >= self.degree + 1


class SurfaceTool:
    """曲面工具基类"""
    
    def __init__(self, canvas, app, color='#FFFFFF'):
        self.canvas = canvas
        self.app = app  # 保存app引用以访问坐标转换
        self.control_grid = []
        self.control_point_ids = []
        self.surface_id = None
        self.grid_lines = []
        self.surface_tag = None
        self.display_mode = 'wireframe'  # 'wireframe' or 'filled'
        self.surface_color = color  # 曲面颜色
        
    def clear(self):
        """清除所有元素"""
        for pid in self.control_point_ids:
            self.canvas.delete(pid)
        if self.surface_id:
            self.canvas.delete(self.surface_id)
        for line_id in self.grid_lines:
            self.canvas.delete(line_id)
        
        self.control_grid = []
        self.control_point_ids = []
        self.surface_id = None
        self.grid_lines = []


class BezierSurfaceTool(SurfaceTool):
    """Bézier曲面工具（矩形控制网格）"""
    
    def __init__(self, canvas, app, grid_size=(4, 4), color='#FFFFFF'):
        super().__init__(canvas, app, color)
        self.grid_size = grid_size  # (rows, cols)
        self.rows, self.cols = grid_size
        
    def set_control_grid(self, grid):
        """
        设置控制点网格（grid中的坐标为逻辑坐标）
        grid: 形式为 [[(x,y,z), ...], ...]
        对于2D显示，z坐标用于控制颜色深度
        """
        from coordinate_system import logical_to_screen
        
        self.control_grid = grid
        
        self.canvas.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        
        # 绘制控制点
        for row in grid:
            for logical_x, logical_y, z in row:
                # 将逻辑坐标转换为屏幕坐标
                screen_coords = logical_to_screen(
                    [logical_x, logical_y],
                    self.app.zoom_level,
                    self.app.pan_offset_x,
                    self.app.pan_offset_y,
                    canvas_width,
                    canvas_height
                )
                screen_x, screen_y = screen_coords[0], screen_coords[1]
                
                point_id = self.canvas.create_oval(
                    screen_x - 4, screen_y - 4,
                    screen_x + 4, screen_y + 4,
                    fill='red', outline='white', width=2,
                    tags=(self.surface_tag, 'control_point')
                )
                self.control_point_ids.append(point_id)
    
    def update_surface(self, display_mode='wireframe'):
        """更新曲面显示"""
        self.display_mode = display_mode
        
        # 清除旧的曲面显示
        for line_id in self.grid_lines:
            self.canvas.delete(line_id)
        self.grid_lines = []
        
        if not self.control_grid:
            return
        
        # 创建Bézier曲面
        surface = BezierSurface(self.control_grid)
        
        if display_mode == 'wireframe':
            self._draw_wireframe(surface)
        else:  # filled
            self._draw_filled(surface)
    
    def _draw_wireframe(self, surface):
        """绘制网格线模式（将逻辑坐标转换为屏幕坐标）"""
        from coordinate_system import logical_to_screen
        
        self.canvas.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        
        # 获取等参曲线
        u_curves, v_curves = surface.get_isocurves(num_u_curves=10, num_v_curves=10)
        
        # 绘制u方向曲线（使用主颜色）
        for curve in u_curves:
            # 将逻辑坐标转换为屏幕坐标
            logical_points = []
            for x, y, z in curve:
                logical_points.extend([x, y])
            
            screen_points = logical_to_screen(
                logical_points,
                self.app.zoom_level,
                self.app.pan_offset_x,
                self.app.pan_offset_y,
                canvas_width,
                canvas_height
            )
            
            line_id = self.canvas.create_line(
                screen_points,
                fill=self.surface_color, width=1,
                tags=(self.surface_tag, 'surface_grid')
            )
            self.grid_lines.append(line_id)
        
        # 绘制v方向曲线（使用稍浅的颜色）
        for curve in v_curves:
            # 将逻辑坐标转换为屏幕坐标
            logical_points = []
            for x, y, z in curve:
                logical_points.extend([x, y])
            
            screen_points = logical_to_screen(
                logical_points,
                self.app.zoom_level,
                self.app.pan_offset_x,
                self.app.pan_offset_y,
                canvas_width,
                canvas_height
            )
            
            line_id = self.canvas.create_line(
                screen_points,
                fill=self.surface_color, width=1,
                tags=(self.surface_tag, 'surface_grid')
            )
            self.grid_lines.append(line_id)
    
    def _draw_filled(self, surface):
        """绘制填充模式（使用投影后的坐标）"""
        from coordinate_system import logical_to_screen
        
        self.canvas.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        
        # 生成网格
        mesh_points, faces = surface.generate_mesh(u_segments=20, v_segments=20)
        
        for face in faces:
            p0, p1, p2 = [mesh_points[i] for i in face]
            
            # 提取逻辑坐标并投影到屏幕坐标
            # 注意：p0, p1, p2 是 (x, y, z)
            logical_pts = [p0[0], p0[1], p1[0], p1[1], p2[0], p2[1]]
            screen_pts = logical_to_screen(
                logical_pts,
                self.app.zoom_level,
                self.app.pan_offset_x,
                self.app.pan_offset_y,
                canvas_width,
                canvas_height
            )
            
            # 根据z值计算颜色（简单的深度着色）
            avg_z = (p0[2] + p1[2] + p2[2]) / 3
            gray = int(max(0, min(255, (avg_z + 50) * 2.55)))  # 稍微调整映射范围
            color = f'#{gray:02x}{gray:02x}{gray:02x}'
            
            # 使用投影后的屏幕坐标绘制
            poly_id = self.canvas.create_polygon(
                screen_pts,
                fill=color, outline='',
                tags=(self.surface_tag, 'surface_fill')
            )
            self.grid_lines.append(poly_id)


def interpolate_color(color1, color2, t):
    """
    在两个颜色之间插值
    color1, color2: 十六进制颜色字符串，如 '#RRGGBB'
    t: 插值参数 0-1
    """
    # 解析颜色
    r1 = int(color1[1:3], 16)
    g1 = int(color1[3:5], 16)
    b1 = int(color1[5:7], 16)
    
    r2 = int(color2[1:3], 16)
    g2 = int(color2[3:5], 16)
    b2 = int(color2[5:7], 16)
    
    # 插值
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    
    return f'#{r:02x}{g:02x}{b:02x}'


def rasterize_curve_with_color(canvas, curve_points, start_color, end_color, width=2):
    """
    使用光栅化算法绘制带颜色渐变的曲线
    """
    rasterized_points = []
    num_points = len(curve_points)
    
    for i in range(num_points - 1):
        x0, y0 = int(curve_points[i][0]), int(curve_points[i][1])
        x1, y1 = int(curve_points[i + 1][0]), int(curve_points[i + 1][1])
        
        # 使用Bresenham算法
        segment_points = SimpleRasterization.bresenham_line(x0, y0, x1, y1)
        
        # 计算颜色
        t = i / max(1, num_points - 1)
        color = interpolate_color(start_color, end_color, t)
        
        # 绘制线段
        if segment_points:
            flat_points = []
            for px, py in segment_points:
                flat_points.extend([px, py])
            
            if len(flat_points) >= 4:
                canvas.create_line(
                    flat_points,
                    fill=color, width=width,
                    capstyle='round', joinstyle='round'
                )
