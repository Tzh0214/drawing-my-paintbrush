# drawing_utils.py

"""
Drawing utilities for rasterization and shape conversion in DrawingApp.
"""
import math
from raster import SimpleRasterization
from PIL import Image, ImageDraw
from pixel_buffer import PixelBuffer


def create_rasterized_image(app, state):
    """
    根据图形的状态字典，使用选定的光栅化算法创建一个PIL图像。
    'state' 字典必须包含:
    - tool: 'line', 'rectangle', 'circle', 'polygon', 'pencil'
    - start_xy, end_xy: (用于直线、矩形、圆形)
    - points: (用于多边形)
    - line_segments: (用于画笔)
    - outline_color, fill_color, brush_size
    """
    tool = state.get('tool')
    outline_color = state.get('outline_color')
    fill_color = state.get('fill_color')
    brush_size = state.get('brush_size', 1)
    
    # 1. 根据不同工具类型，确定图形的边界框 (Bounding Box)
    padding = brush_size
    if tool in ['line', 'rectangle', 'circle']:
        (start_x, start_y) = state['start_xy']
        (end_x, end_y) = state['end_xy']
        x1, y1 = min(start_x, end_x) - padding, min(start_y, end_y) - padding
        x2, y2 = max(start_x, end_x) + padding, max(start_y, end_y) + padding
    elif tool == 'polygon':
        points = state['points']
        if not points: return None, None
        x_coords, y_coords = zip(*points)
        x1, y1 = min(x_coords) - padding, min(y_coords) - padding
        x2, y2 = max(x_coords) + padding, max(y_coords) + padding
    elif tool == 'pencil':
        all_x, all_y = [], []
        for seg in state['line_segments']:
            all_x.extend([seg[0], seg[2]])
            all_y.extend([seg[1], seg[3]])
        if not all_x or not all_y: return None, None
        x1, y1 = min(all_x) - padding, min(all_y) - padding
        x2, y2 = max(all_x) + padding, max(all_y) + padding
    else:
        return None, None

    w, h = int(x2 - x1), int(y2 - y1)
    if w <= 1 or h <= 1: return None, None

    # 2. 创建PIL图像和Draw上下文
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    outline_rgba = PixelBuffer.hex_to_rgba(outline_color)
    fill_rgba = PixelBuffer.hex_to_rgba(fill_color) if fill_color else None

    # 3. 使用选择的光栅化算法获取所有像素点
    outline_points, fill_points = [], []
    
    line_algo = (SimpleRasterization.bresenham_line 
                 if app.rasterization_algorithm in ["Bresenham", "Midpoint"] 
                 else SimpleRasterization.dda_line)

    if tool == 'line':
        outline_points = line_algo(int(state['start_xy'][0]), int(state['start_xy'][1]), int(state['end_xy'][0]), int(state['end_xy'][1]))
    
    elif tool == 'rectangle':
        sx, sy = int(state['start_xy'][0]), int(state['start_xy'][1])
        ex, ey = int(state['end_xy'][0]), int(state['end_xy'][1])
        vertex_points = [(sx, sy), (ex, sy), (ex, ey), (sx, ey)]
        if fill_rgba:
            fill_points = SimpleRasterization.scanline_fill(vertex_points)
        outline_points.extend(line_algo(sx, sy, ex, sy))
        outline_points.extend(line_algo(ex, sy, ex, ey))
        outline_points.extend(line_algo(ex, ey, sx, ey))
        outline_points.extend(line_algo(sx, ey, sx, sy))
        
    elif tool == 'circle':
        sx, sy = int(state['start_xy'][0]), int(state['start_xy'][1])
        ex, ey = int(state['end_xy'][0]), int(state['end_xy'][1])
        cx, cy = (sx + ex) // 2, (sy + ey) // 2
        rx = abs(ex - sx) // 2
        ry = abs(ey - sy) // 2
        
        # --- BUG FIX START: Handle Ellipse Drawing ---
        # For non-circle shapes, default to Midpoint Ellipse algorithm for a clean outline.
        if rx != ry or app.rasterization_algorithm not in ["Bresenham", "DDA"]:
             outline_points = SimpleRasterization.midpoint_ellipse(cx, cy, rx, ry)
        elif app.rasterization_algorithm == "Bresenham":
            outline_points = SimpleRasterization.bresenham_circle(cx, cy, rx) # rx == ry here
        else: # DDA
            outline_points = SimpleRasterization.dda_circle(cx, cy, rx) # rx == ry here
            
        # Use a more robust mathematical fill for ellipses and circles
        if fill_rgba and rx > 0 and ry > 0:
            rx_squared, ry_squared = rx * rx, ry * ry
            for y_offset in range(-ry, ry + 1):
                for x_offset in range(-rx, rx + 1):
                    # Check if point is inside ellipse using formula: (x/a)^2 + (y/b)^2 <= 1
                    if (x_offset**2 * ry_squared) + (y_offset**2 * rx_squared) <= rx_squared * ry_squared:
                        fill_points.append((cx + x_offset, cy + y_offset))
        # --- BUG FIX END ---

    elif tool == 'polygon':
        vertex_points = state['points']
        if fill_rgba:
            fill_points = SimpleRasterization.scanline_fill(vertex_points)
        for i in range(len(vertex_points)):
            p1 = vertex_points[i]
            p2 = vertex_points[(i + 1) % len(vertex_points)]
            outline_points.extend(line_algo(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1])))

    elif tool == 'pencil':
        for seg in state['line_segments']:
             outline_points.extend(line_algo(int(seg[0]), int(seg[1]), int(seg[2]), int(seg[3])))
    
    # 4. 将计算出的像素点绘制到PIL图像上
    if fill_points:
        for p in fill_points:
            draw.point((p[0] - x1, p[1] - y1), fill=fill_rgba)

    if outline_points:
        r_brush = (brush_size -1) // 2
        for p in outline_points:
            px, py = p[0] - x1, p[1] - y1
            if brush_size > 1:
                draw.ellipse([px-r_brush, py-r_brush, px+r_brush, py+r_brush], fill=outline_rgba)
            else:
                draw.point((px,py), fill=outline_rgba)
    
    # 5. 应用旋转（如果有angle字段）
    angle = state.get('angle', 0)
    if angle != 0:
        img = img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
        # 旋转后重新计算位置（expand=True会改变图像尺寸）
        # 旋转中心是原图像中心
        orig_cx, orig_cy = (x1 + x2) / 2, (y1 + y2) / 2
        # 新图像的左上角位置
        x1 = orig_cx - img.width / 2
        y1 = orig_cy - img.height / 2
    
    return img, (x1, y1)


def convert_to_polygon(app, unique_tag):
    """
    将矢量矩形或圆形转换为多边形以便旋转。
    """
    item_ids = app.canvas.find_withtag(unique_tag)
    if not item_ids or app.canvas.type(item_ids[0]) == 'image': return
    item_id = item_ids[0]
    
    item_type = app.canvas.type(item_id)
    if item_type not in ["rectangle", "oval"]: return
    
    coords, tags = app.canvas.coords(item_id), app.canvas.gettags(item_id)
    new_coords = []
    
    if item_type == "rectangle":
        x1, y1, x2, y2 = coords
        new_coords = [x1, y1, x2, y1, x2, y2, x1, y2]
    elif item_type == "oval":
        x1, y1, x2, y2 = coords
        rx, ry = (x2 - x1) / 2, (y2 - y1) / 2
        cx, cy = x1 + rx, y1 + ry
        for i in range(60): # 用60个点近似圆形
            angle = (i / 60) * 2 * math.pi
            new_coords.extend([cx + rx * math.cos(angle), cy + ry * math.sin(angle)])
    
    if new_coords:
        options = {
            'outline': app.canvas.itemcget(item_id, 'outline'),
            'width': app.canvas.itemcget(item_id, 'width'),
            'fill': app.canvas.itemcget(item_id, 'fill'),
            'tags': tags
        }
        app.canvas.delete(item_id)
        app.canvas.create_polygon(new_coords, **options)
        if unique_tag in app.object_states:
            app.object_states[unique_tag]['original_coords'] = new_coords