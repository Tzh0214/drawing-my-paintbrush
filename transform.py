# transform.py

"""
Transform operations (flip, rotate, etc.) for selected objects in DrawingApp.
"""
from PIL import Image, ImageTk


def flip_horizontal(app):
    """水平翻转（左右翻转）所有选中对象"""
    if not app.selection_group:
        return
    
    bbox = _get_selection_bbox(app)
    if not bbox:
        return
    
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2
    
    for tag in app.selection_group:
        # 遍历这个 tag 对应的所有 item
        item_ids = list(app.canvas.find_withtag(tag))
        for item_id in item_ids:
            item_type = app.canvas.type(item_id)
            
            if item_type == "image":
                # 对于图片，使用 PIL 的翻转功能
                _flip_image_horizontal(app, item_id)
            else:
                # 对于矢量图形，翻转坐标
                _flip_coords_horizontal(app, item_id, center_x)
        
        # 翻转后更新逻辑坐标到 object_states
        _update_logical_coords_after_transform(app, tag)
    
    app._draw_resize_handles()
    app._capture_and_save_state()


def flip_vertical(app):
    """竖直翻转（上下翻转）所有选中对象"""
    if not app.selection_group:
        return
    
    bbox = _get_selection_bbox(app)
    if not bbox:
        return
    
    x1, y1, x2, y2 = bbox
    center_y = (y1 + y2) / 2
    
    for tag in app.selection_group:
        # 遍历这个 tag 对应的所有 item
        item_ids = list(app.canvas.find_withtag(tag))
        for item_id in item_ids:
            item_type = app.canvas.type(item_id)
            
            if item_type == "image":
                # 对于图片，使用 PIL 的翻转功能
                _flip_image_vertical(app, item_id)
            else:
                # 对于矢量图形，翻转坐标
                _flip_coords_vertical(app, item_id, center_y)        
        # 翻转后更新逻辑坐标到 object_states
        _update_logical_coords_after_transform(app, tag)    
    app._draw_resize_handles()
    app._capture_and_save_state()


def _get_selection_bbox(app):
    """获取选中对象的边界框"""
    if not app.selection_group:
        return None
    min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
    has_bbox = False
    for tag in app.selection_group:
        bbox = app.canvas.bbox(tag)
        if bbox:
            has_bbox = True
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])
    return (min_x, min_y, max_x, max_y) if has_bbox else None


def _flip_coords_horizontal(app, item_id, center_x):
    """水平翻转矢量图形的坐标"""
    coords = app.canvas.coords(item_id)
    if not coords:
        return
    
    # 翻转所有 x 坐标：新_x = center_x - (旧_x - center_x) = 2*center_x - 旧_x
    new_coords = []
    for i, coord in enumerate(coords):
        if i % 2 == 0:  # x 坐标
            new_coords.append(2 * center_x - coord)
        else:  # y 坐标
            new_coords.append(coord)
    
    app.canvas.coords(item_id, *new_coords)


def _flip_coords_vertical(app, item_id, center_y):
    """竖直翻转矢量图形的坐标"""
    coords = app.canvas.coords(item_id)
    if not coords:
        return
    
    # 翻转所有 y 坐标：新_y = center_y - (旧_y - center_y) = 2*center_y - 旧_y
    new_coords = []
    for i, coord in enumerate(coords):
        if i % 2 == 0:  # x 坐标
            new_coords.append(coord)
        else:  # y 坐标
            new_coords.append(2 * center_y - coord)
    
    app.canvas.coords(item_id, *new_coords)


def _flip_image_horizontal(app, item_id):
    """水平翻转图片对象"""
    # 获取图片当前的坐标和大小
    coords = app.canvas.coords(item_id)
    if not coords:
        return
    
    # 从 canvas 直接获取当前显示的图像
    try:
        # 尝试从 _image_references 中获取原始 PIL 图像
        # 由于 PhotoImage 是 Tkinter 对象，我们需要找到原始的 PIL 图像
        # 通过遍历 object_states 来找到对应的状态
        for tag in app.canvas.gettags(item_id):
            if tag.startswith(("stroke_", "shape_")) and tag in app.object_states:
                state = app.object_states[tag]
                if 'original_pil_image' in state:
                    original_img = state['original_pil_image']
                    flipped_img = original_img.transpose(Image.FLIP_LEFT_RIGHT)
                    state['original_pil_image'] = flipped_img
                    
                    # 应用缩放显示
                    display_img = flipped_img
                    if app.zoom_level != 1.0:
                        new_w = max(int(flipped_img.width * app.zoom_level), 1)
                        new_h = max(int(flipped_img.height * app.zoom_level), 1)
                        display_img = flipped_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    tk_img = ImageTk.PhotoImage(display_img)
                    app.canvas.itemconfig(item_id, image=tk_img)
                    
                    if item_id in app._image_references:
                        del app._image_references[item_id]
                    app._image_references[item_id] = tk_img
                    return
    except Exception:
        pass


def _flip_image_vertical(app, item_id):
    """竖直翻转图片对象"""
    coords = app.canvas.coords(item_id)
    if not coords:
        return
    
    try:
        for tag in app.canvas.gettags(item_id):
            if tag.startswith(("stroke_", "shape_")) and tag in app.object_states:
                state = app.object_states[tag]
                if 'original_pil_image' in state:
                    original_img = state['original_pil_image']
                    flipped_img = original_img.transpose(Image.FLIP_TOP_BOTTOM)
                    state['original_pil_image'] = flipped_img
                    
                    # 翻转 points 数据（多边形）
                    if 'points' in state and state['points']:
                        if 'start_xy' in state and 'end_xy' in state:
                            sx, sy = state['start_xy']
                            ex, ey = state['end_xy']
                            center_y = (sy + ey) / 2
                            flipped_points = [(px, 2 * center_y - py) for px, py in state['points']]
                            state['points'] = flipped_points
                    
                    # 翻转 line_segments 数据（画笔）
                    if 'line_segments' in state and state['line_segments']:
                        if 'start_xy' in state and 'end_xy' in state:
                            sx, sy = state['start_xy']
                            ex, ey = state['end_xy']
                            center_y = (sy + ey) / 2
                            flipped_segments = [
                                [seg[0], 2 * center_y - seg[1], seg[2], 2 * center_y - seg[3]]
                                for seg in state['line_segments']
                            ]
                            state['line_segments'] = flipped_segments
                    
                    # 应用缩放显示
                    display_img = flipped_img
                    if app.zoom_level != 1.0:
                        new_w = max(int(flipped_img.width * app.zoom_level), 1)
                        new_h = max(int(flipped_img.height * app.zoom_level), 1)
                        display_img = flipped_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    tk_img = ImageTk.PhotoImage(display_img)
                    app.canvas.itemconfig(item_id, image=tk_img)
                    
                    if item_id in app._image_references:
                        del app._image_references[item_id]
                    app._image_references[item_id] = tk_img
                    return
    except Exception:
        pass


def _update_logical_coords_after_transform(app, tag):
    """翻转或变换后，将屏幕坐标转换回逻辑坐标并更新到 object_states"""
    if tag not in app.object_states:
        return
    
    from coordinate_system import screen_to_logical
    app.canvas.update_idletasks()
    canvas_width = max(app.canvas.winfo_width(), 1)
    canvas_height = max(app.canvas.winfo_height(), 1)
    
    state = app.object_states[tag]
    item_ids = list(app.canvas.find_withtag(tag))
    if not item_ids:
        return
    item_id = item_ids[0]
    item_type = app.canvas.type(item_id)

    # 处理单个对象的坐标
    if 'original_coords' in state and item_type != 'image':
        screen_coords = app.canvas.coords(item_id)
        logical_coords = screen_to_logical(
            screen_coords,
            app.zoom_level,
            app.pan_offset_x,
            app.pan_offset_y,
            canvas_width,
            canvas_height
        )
        state['original_coords'] = logical_coords

    # 处理多个对象的坐标映射（如笔触）
    elif 'original_coords_map' in state and item_type != 'image':
        for part_id in state['original_coords_map'].keys():
            screen_coords = app.canvas.coords(part_id)
            logical_coords = screen_to_logical(
                screen_coords,
                app.zoom_level,
                app.pan_offset_x,
                app.pan_offset_y,
                canvas_width,
                canvas_height
            )
            state['original_coords_map'][part_id] = logical_coords

    # 处理光栅对象的逻辑坐标
    elif item_type == 'image':
        screen_xy = app.canvas.coords(item_id)
        if not screen_xy:
            return

        img_w, img_h = 0, 0
        try:
            pil_img = state.get('original_pil_image')
            if pil_img:
                img_w, img_h = pil_img.size
        except Exception:
            img_w, img_h = 0, 0

        if img_w == 0 or img_h == 0:
            try:
                bbox = app.canvas.bbox(item_id)
                if bbox:
                    img_w = bbox[2] - bbox[0]
                    img_h = bbox[3] - bbox[1]
            except Exception:
                return

        screen_bbox = [screen_xy[0], screen_xy[1], screen_xy[0] + img_w, screen_xy[1] + img_h]
        logical_bbox = screen_to_logical(
            screen_bbox,
            app.zoom_level,
            app.pan_offset_x,
            app.pan_offset_y,
            canvas_width,
            canvas_height
        )

        if len(logical_bbox) >= 4:
            lx1, ly1, lx2, ly2 = logical_bbox
            state['start_xy'] = (lx1, ly1)
            state['end_xy'] = (lx2, ly2)
            state['original_coords'] = [lx1, ly1, lx2, ly2]
