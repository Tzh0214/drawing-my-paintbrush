# coordinate_system.py
"""
统一的坐标系统管理模块
核心原则：
1. 所有对象的逻辑坐标存储在 object_states 的 'original_coords' 中（基于 zoom=1.0, pan=0,0）
2. Canvas 上的屏幕坐标（screen_coords）是逻辑坐标通过当前 zoom 和 pan 的投影
3. 转换流程：logical_coords -> (zoom + pan) -> screen_coords
"""


def logical_to_screen(logical_coords, zoom_level, pan_x, pan_y, canvas_width, canvas_height):
    """
    将逻辑坐标转换为屏幕坐标
    
    Args:
        logical_coords: 列表，格式为 [x1, y1, x2, y2, ...] (逻辑坐标)
        zoom_level: 缩放倍数（1.0 = 100%）
        pan_x, pan_y: 平移量（逻辑坐标单位）
        canvas_width, canvas_height: 画布尺寸
    
    Returns:
        屏幕坐标列表
    """
    if not logical_coords:
        return []
    
    canvas_center_x = canvas_width / 2.0
    canvas_center_y = canvas_height / 2.0
    
    screen_coords = []
    for i, coord in enumerate(logical_coords):
        if i % 2 == 0:  # x 坐标
            # 逻辑坐标 + 平移 -> 相对坐标 -> 缩放 -> 屏幕坐标
            screen_x = canvas_center_x + (coord + pan_x - canvas_center_x) * zoom_level
            screen_coords.append(screen_x)
        else:  # y 坐标
            screen_y = canvas_center_y + (coord + pan_y - canvas_center_y) * zoom_level
            screen_coords.append(screen_y)
    
    return screen_coords


def screen_to_logical(screen_coords, zoom_level, pan_x, pan_y, canvas_width, canvas_height):
    """
    将屏幕坐标转换为逻辑坐标
    
    Args:
        screen_coords: 屏幕坐标列表
        zoom_level: 缩放倍数
        pan_x, pan_y: 平移量
        canvas_width, canvas_height: 画布尺寸
    
    Returns:
        逻辑坐标列表
    """
    if not screen_coords:
        return []
    
    canvas_center_x = canvas_width / 2.0
    canvas_center_y = canvas_height / 2.0
    
    logical_coords = []
    for i, coord in enumerate(screen_coords):
        if i % 2 == 0:  # x 坐标
            # 屏幕坐标 -> 反缩放 -> 减去平移 -> 逻辑坐标
            logical_x = (coord - canvas_center_x) / max(zoom_level, 1e-9) + canvas_center_x - pan_x
            logical_coords.append(logical_x)
        else:  # y 坐标
            logical_y = (coord - canvas_center_y) / max(zoom_level, 1e-9) + canvas_center_y - pan_y
            logical_coords.append(logical_y)
    
    return logical_coords


def sync_object_to_screen(app, tag):
    """
    将存储在 object_states 的逻辑坐标同步到 Canvas 屏幕坐标
    
    Args:
        app: DrawingApp 实例
        tag: 对象标签
    """
    if tag not in app.object_states:
        return
    
    state = app.object_states[tag]
    if 'original_coords' not in state:
        return
    
    logical_coords = state['original_coords']
    
    app.canvas.update_idletasks()
    canvas_width = max(app.canvas.winfo_width(), 1)
    canvas_height = max(app.canvas.winfo_height(), 1)
    
    screen_coords = logical_to_screen(
        logical_coords, 
        app.zoom_level, 
        app.pan_offset_x, 
        app.pan_offset_y,
        canvas_width, 
        canvas_height
    )
    
    for item_id in app.canvas.find_withtag(tag):
        app.canvas.coords(item_id, *screen_coords)


def sync_all_objects_to_screen(app):
    """
    同步所有对象从逻辑坐标到屏幕坐标
    
    Args:
        app: DrawingApp 实例
    """
    from PIL import Image, ImageTk
    from drawing_utils import create_rasterized_image
    
    app.canvas.update_idletasks()
    canvas_width = max(app.canvas.winfo_width(), 1)
    canvas_height = max(app.canvas.winfo_height(), 1)
    
    for tag in list(app.object_states.keys()):
        if tag.startswith(("stroke_", "shape_")):
            state = app.object_states[tag]
            
            if 'original_coords' in state:
                logical_coords = state['original_coords']
                screen_coords = logical_to_screen(
                    logical_coords,
                    app.zoom_level,
                    app.pan_offset_x,
                    app.pan_offset_y,
                    canvas_width,
                    canvas_height
                )
                
                for item_id in app.canvas.find_withtag(tag):
                    item_type = app.canvas.type(item_id)
                    
                    # 对于 image 类型（光栅化对象），需要特殊处理
                    if item_type == 'image':
                        # 重新生成光栅化图像（使用当前的缩放级别）
                        if 'original_pil_image' in state:
                            # 根据当前 zoom 级别计算缩放后的大小
                            original_img = state['original_pil_image']
                            original_width, original_height = original_img.size
                            
                            # 计算缩放因子（基于当前缩放级别与参考缩放级别的比值）
                            zoom_ref = state.get('zoom_ref', 1.0)
                            scale_factor = app.zoom_level / max(zoom_ref, 1e-9)
                            
                            # 计算新的图像大小
                            new_width = max(int(original_width * scale_factor), 1)
                            new_height = max(int(original_height * scale_factor), 1)
                            
                            # 如果大小确实改变了，重新缩放图像
                            if (new_width, new_height) != (original_width, original_height):
                                scaled_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                tk_img = ImageTk.PhotoImage(scaled_img)
                                
                                # 更新 canvas 上的图像
                                app.canvas.itemconfig(item_id, image=tk_img)
                                app._image_references[item_id] = tk_img  # 保持对图像的引用
                        
                        # Image 对象的 coords 只需要 (x, y) 两个参数，表示锚点位置
                        img_x, img_y = screen_coords[0], screen_coords[1]
                        app.canvas.coords(item_id, img_x, img_y)
                    elif item_type == 'text':
                        # 文本需按缩放调整字号，保持空间感一致
                        font_spec = state.get('font', '') or ''
                        font_parts = font_spec.split()
                        font_family = font_parts[0] if font_parts else 'Arial'
                        logical_font_size = state.get('logical_font_size')
                        if logical_font_size is None:
                            try:
                                logical_font_size = int(font_parts[1]) if len(font_parts) > 1 else 16
                            except Exception:
                                logical_font_size = 16
                        zoom_ref = state.get('zoom_ref', 1.0)
                        scale_factor = app.zoom_level / max(zoom_ref, 1e-9)
                        display_font_size = max(1, int(logical_font_size * scale_factor))
                        app.canvas.itemconfig(item_id, font=f"{font_family} {display_font_size}")
                        app.canvas.coords(item_id, *screen_coords[:2])
                    else:
                        # 矢量图形（line, rectangle, oval, polygon 等）可以直接使用所有坐标
                        app.canvas.coords(item_id, *screen_coords)
            
            elif 'original_coords_map' in state:
                # 对于包含多个 item_id 的对象（如笔触）
                for item_id, logical_coords in state['original_coords_map'].items():
                    screen_coords = logical_to_screen(
                        logical_coords,
                        app.zoom_level,
                        app.pan_offset_x,
                        app.pan_offset_y,
                        canvas_width,
                        canvas_height
                    )
                    item_type = app.canvas.type(item_id)
                    
                    # 对于 image 类型，只使用前两个坐标
                    if item_type == 'image':
                        img_x, img_y = screen_coords[0], screen_coords[1]
                        app.canvas.coords(item_id, img_x, img_y)
                    else:
                        app.canvas.coords(item_id, *screen_coords)
        
        # 处理曲线对象
        elif tag.startswith("curve_"):
            state = app.object_states[tag]
            if 'original_coords' in state and 'control_points' in state:
                # 重新生成曲线
                from curves import BezierCurve, BSplineCurve
                
                # 获取逻辑坐标的控制点
                logical_control_points = state['control_points']
                
                # 生成曲线上的点（逻辑坐标）
                if state.get('curve_type') == 'bezier':
                    curve = BezierCurve(logical_control_points)
                else:  # bspline
                    degree = 3  # B样条默认度数为3
                    curve = BSplineCurve(logical_control_points, degree)
                
                curve_points = curve.generate_points(num_segments=100)
                
                # 将曲线点转换为屏幕坐标
                logical_curve_coords = []
                for x, y in curve_points:
                    logical_curve_coords.extend([x, y])
                
                screen_curve_coords = logical_to_screen(
                    logical_curve_coords,
                    app.zoom_level,
                    app.pan_offset_x,
                    app.pan_offset_y,
                    canvas_width,
                    canvas_height
                )
                
                # 更新canvas上的曲线
                curve_items = [item for item in app.canvas.find_withtag(tag) 
                              if 'bezier_curve' in app.canvas.gettags(item) 
                              or 'bspline_curve' in app.canvas.gettags(item)]
                
                if curve_items:
                    app.canvas.coords(curve_items[0], *screen_curve_coords)
                    
                    # 补充图层标签（如果状态中有保存）
                    saved_layer_id = state.get('layer_id')
                    if saved_layer_id:
                        current_tags = list(app.canvas.gettags(curve_items[0]))
                        if saved_layer_id not in current_tags:
                            current_tags.append(saved_layer_id)
                            app.canvas.itemconfig(curve_items[0], tags=tuple(current_tags))
        
        # 处理曲面对象
        elif tag.startswith("surface_"):
            state = app.object_states[tag]
            if 'control_grid' in state:
                from surfaces import BezierSurface
                from curve_surface_tools import BezierSurfaceTool
                
                # 获取状态
                logical_grid = state['control_grid']
                display_mode = state.get('display_mode', 'wireframe')
                color = state.get('color', '#FFFFFF')
                
                # 创建一个临时的工具包装来复用绘制逻辑，避免代码冗余
                # 这样可以确保缩放时的行为与初次绘制完全一致
                surface = BezierSurface(logical_grid)
                
                # 删除旧的曲面所有部件（包括线框和填充）
                old_items = app.canvas.find_withtag(tag)
                for item in old_items:
                    # 不要删除控制点标签，除非是在非编辑状态
                    if 'control_point' not in app.canvas.gettags(item):
                        app.canvas.delete(item)
                
                # 重新调用绘制逻辑
                # 我们模拟一个 Tool 实例来调用内部方法
                temp_tool = BezierSurfaceTool(app.canvas, app, color=color)
                temp_tool.surface_tag = tag
                temp_tool.control_grid = logical_grid
                
                # 根据保存的模式重绘
                if display_mode == 'wireframe':
                    temp_tool._draw_wireframe(surface)
                else:
                    temp_tool._draw_filled(surface)

                # 为重绘后的曲面元素补充图层标签
                layer_tag = state.get('layer_id')
                if layer_tag:
                    new_items = [item for item in app.canvas.find_withtag(tag)
                                 if ('surface_grid' in app.canvas.gettags(item)
                                     or 'surface_fill' in app.canvas.gettags(item))]
                    for item in new_items:
                        current_tags = list(app.canvas.gettags(item))
                        if layer_tag not in current_tags:
                            current_tags.append(layer_tag)
                            app.canvas.itemconfig(item, tags=tuple(current_tags))


def get_logical_bounding_box(app):
    """
    获取所有对象的逻辑坐标包围盒
    
    Args:
        app: DrawingApp 实例
        
    Returns:
        (x1, y1, x2, y2) 或 None（如果没有对象）
    """
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    has_object = False
    for tag, state in app.object_states.items():
        # 获取额外的 padding（线宽的一半）
        padding = 0
        try:
            padding = float(state.get('width', 1.0)) / 2.0
        except:
            padding = 0.5

        # 检查是否为文字对象，给予额外 padding
        # 注意：这需要查询 canvas，可能会有轻微性能影响，但在导出时可忽略
        items = app.canvas.find_withtag(tag)
        if items:
            if app.canvas.type(items[0]) == 'text':
                # 粗略估算文字尺寸，给予较大 padding 防止被切
                # 假设每个字符平均宽 40 像素（覆盖大字体情况），取一半作为单侧 padding
                text_content = app.canvas.itemcget(items[0], 'text')
                text_padding = len(text_content) * 20.0
                padding = max(padding, text_padding, 100.0)

        if 'original_coords' in state:
            coords = state['original_coords']
            if coords:
                has_object = True
                for i, coord in enumerate(coords):
                    if i % 2 == 0:  # x
                        min_x = min(min_x, coord - padding)
                        max_x = max(max_x, coord + padding)
                    else:  # y
                        min_y = min(min_y, coord - padding)
                        max_y = max(max_y, coord + padding)
        
        elif 'original_coords_map' in state:
            for coords in state['original_coords_map'].values():
                if coords:
                    has_object = True
                    for i, coord in enumerate(coords):
                        if i % 2 == 0:  # x
                            min_x = min(min_x, coord - padding)
                            max_x = max(max_x, coord + padding)
                        else:  # y
                            min_y = min(min_y, coord - padding)
                            max_y = max(max_y, coord + padding)
        
        # 处理曲线的控制点
        elif 'control_points' in state:
            points = state['control_points']
            if points:
                has_object = True
                for pt in points:
                    if len(pt) >= 2:
                        min_x = min(min_x, pt[0] - padding)
                        max_x = max(max_x, pt[0] + padding)
                        min_y = min(min_y, pt[1] - padding)
                        max_y = max(max_y, pt[1] + padding)
        
        # 处理曲面的控制网格
        elif 'control_grid' in state:
            grid = state['control_grid']
            if grid:
                has_object = True
                for row in grid:
                    for pt in row:
                        if len(pt) >= 2:
                            min_x = min(min_x, pt[0] - padding)
                            max_x = max(max_x, pt[0] + padding)
                            min_y = min(min_y, pt[1] - padding)
                            max_y = max(max_y, pt[1] + padding)
        
        # 处理光栅化图像的边界
        elif 'start_xy' in state and 'end_xy' in state:
            has_object = True
            sx, sy = state['start_xy']
            ex, ey = state['end_xy']
            
            # 处理旋转后的边界
            angle = state.get('angle', 0)
            if angle != 0:
                # 计算中心点和半径（外接圆）
                w = abs(ex - sx)
                h = abs(ey - sy)
                cx, cy = (sx + ex) / 2, (sy + ey) / 2
                radius = (w**2 + h**2)**0.5 / 2
                # 使用外接圆作为保守边界
                min_x = min(min_x, cx - radius)
                max_x = max(max_x, cx + radius)
                min_y = min(min_y, cy - radius)
                max_y = max(max_y, cy + radius)
            else:
                min_x = min(min_x, sx, ex)
                max_x = max(max_x, sx, ex)
                min_y = min(min_y, sy, ey)
                max_y = max(max_y, sy, ey)
    
    if not has_object:
        return None
    
    return (min_x, min_y, max_x, max_y)


def get_grid_offset_for_render(pan_x, pan_y, grid_spacing):
    """
    计算网格的起始偏移，用于同步网格和平移
    
    Args:
        pan_x, pan_y: 逻辑坐标中的平移量
        grid_spacing: 网格间距（像素）
    
    Returns:
        (offset_x, offset_y) 适用于网格绘制
    """
    offset_x = (pan_x * 1) % grid_spacing  # 基本的网格偏移
    offset_y = (pan_y * 1) % grid_spacing
    return (offset_x, offset_y)
