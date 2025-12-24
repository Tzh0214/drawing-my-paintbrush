# event_handlers.py

"""
Event handlers for drawing, selection, and transformation in DrawingApp.
"""
import time
import math
from utils import rotate_point
from PIL import ImageTk, Image
from drawing_utils import create_rasterized_image


def on_mouse_move_canvas(app, event):
    """
    在曲线/曲面编辑时，悬停在控制点上时改变光标为手形
    """
    if app.current_tool in ["bezier", "bspline", "bezier_surface"]:
        # 检查是否悬停在控制点上
        items = app.canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
        is_over_control_point = False
        
        for item in items:
            tags = app.canvas.gettags(item)
            if "control_point" in tags:
                is_over_control_point = True
                break
        
        # 根据是否悬停在控制点改变光标
        if is_over_control_point:
            app.canvas.config(cursor="hand2")  # 手形光标
        else:
            app.canvas.config(cursor="crosshair")  # 十字光标


def start_drawing(app, event):
    # 如果按住空格键，进入画布拖动模式
    if app.space_pressed:
        app.pan_start_x = event.x
        app.pan_start_y = event.y
        return
    
    if app.current_tool == "select":
        item_tuple = app.canvas.find_withtag("current")
        item_id = item_tuple[0] if item_tuple else None

        if item_id and "handle" in app.canvas.gettags(item_id) and app.selection_group:
            app.original_bbox = app._get_selection_bbox()
            if not app.original_bbox: return

            if "rotate" in app.canvas.gettags(item_id):
                app.drag_mode = "rotate"
                app.shape_center = ((app.original_bbox[0] + app.original_bbox[2]) / 2, (app.original_bbox[1] + app.original_bbox[3]) / 2)
                app.drag_start_angle = math.atan2(event.y - app.shape_center[1], event.x - app.shape_center[0])
            else:
                app.drag_mode = "resize"
                app.drag_handle_type = next((t for t in app.canvas.gettags(item_id) if t not in ["handle", "rotate"]), None)

            app.original_group_states.clear()
            # 新增：保存原始逻辑状态，用于 Resize 时计算 control_grid 等
            if not hasattr(app, 'original_logical_states'): app.original_logical_states = {}
            app.original_logical_states.clear()

            for tag in app.selection_group:
                if app.drag_mode == 'rotate': app._convert_to_polygon(tag)

                # 保存逻辑状态副本
                if tag in app.object_states:
                    import copy
                    app.original_logical_states[tag] = copy.deepcopy(app.object_states[tag])

                items = list(app.canvas.find_withtag(tag))
                if not items:
                    app.original_group_states[tag] = {}
                    continue
                
                if app.canvas.type(items[0]) == "image":
                    # For raster images, we need the logical state, not just canvas coords
                    app.original_group_states[tag] = app.object_states.get(tag, {}).copy()
                elif len(items) > 1:
                     app.original_group_states[tag] = {item_id: app.canvas.coords(item_id) for item_id in items}
                else:
                    app.original_group_states[tag] = app.canvas.coords(items[0])
            return

        clicked_tag = None
        if item_id:
            item_tags = app.canvas.gettags(item_id)
            if app.active_layer_id not in item_tags and "grid_line" not in item_tags: 
                layer_tag = next((t for t in item_tags if t.startswith("layer_")), None)
                if layer_tag: app.select_layer(layer_tag)
            
            if app.active_layer_id in item_tags:
                # 首先检查是否点击了曲线或曲面
                clicked_tag = next((t for t in item_tags if t.startswith(("curve_", "surface_"))), None)
                # 如果没有点击曲线/曲面，检查其他形状
                if not clicked_tag:
                    clicked_tag = next((t for t in item_tags if t.startswith(("stroke_", "shape_"))), None)
        
        shift_pressed = (event.state & 1)
        if not shift_pressed:
            if clicked_tag not in app.selection_group:
                app._clear_resize_handles()
                app.selection_group.clear()
                if clicked_tag: app.selection_group.add(clicked_tag)
        else:
            if clicked_tag:
                if clicked_tag in app.selection_group: app.selection_group.remove(clicked_tag)
                else: app.selection_group.add(clicked_tag)
        
        app._draw_resize_handles()

        if clicked_tag and clicked_tag in app.selection_group:
            app.drag_mode = "move"
            app.last_x, app.last_y = event.x, event.y
        else:
            app.drag_mode = None
    
    elif app.current_tool == "text": app.create_text_object(event.x, event.y)
    elif app.current_tool == "polygon": app.handle_polygon_click(event)
    elif app.current_tool == "fill": app.fill_shape(event)
    elif app.current_tool in ["bezier", "bspline"]:
        # 曲线工具：优先检查是否点击了现有的控制点来拖动它
        if app.curve_tool:
            items = app.canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
            clicked_control_point = None
            for item in items:
                tags = app.canvas.gettags(item)
                if 'control_point' in tags and app.curve_tool.curve_tag in tags:
                    clicked_control_point = item
                    break
            
            if clicked_control_point:
                # 点击了控制点，进入拖动模式
                app.dragging_control_point = clicked_control_point
            else:
                # 没有点击控制点，添加新的控制点
                app.add_curve_control_point(event.x, event.y)
        else:
            app.add_curve_control_point(event.x, event.y)
    elif app.current_tool == "bezier_surface":
        # 曲面工具：检查是否点击了控制点来拖动它
        if app.surface_tool:
            items = app.canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
            for item in items:
                tags = app.canvas.gettags(item)
                if 'control_point' in tags and app.surface_tool.surface_tag in tags:
                    app.dragging_control_point = item
                    break
    elif app.current_tool == "eraser":
        app.erased_in_drag = False
        app.current_stroke_tag = f"erase_stroke_{time.time()}"
        app.draw(event)
    else:
        app.start_x, app.start_y = event.x, event.y
        if app.current_tool == "pencil":
            app.current_stroke_tag = f"stroke_{time.time()}"


def stop_drawing(app, event):
    action_completed = False
    
    # 如果空格键拖动结束，不需要做其他处理
    if app.space_pressed and app.pan_start_x is not None:
        app.pan_start_x = None
        app.pan_start_y = None
        return
    
    # 释放曲线/曲面控制点拖拽
    if app.current_tool in ["bezier", "bspline", "bezier_surface"]:
        app.release_control_point_drag(event)
        return
    
    if app.current_tool == "select" and app.drag_mode:
        action_completed = True
        
        # If there were temporary state updates from resizing, commit them now.
        if hasattr(app, '_temp_state_updates'):
            for tag, updates in app._temp_state_updates.items():
                if tag in app.object_states:
                    app.object_states[tag].update(updates)
            del app._temp_state_updates

        for tag in app.selection_group:
            if tag in app.object_states:
                state = app.object_states[tag]
                item_ids = app.canvas.find_withtag(tag)
                if not item_ids: continue
                
                # 图像变换结束时，不再将旋转/缩放后的临时位图“烘焙”回原图。
                # 这样可以：
                # 1) 保持 state['angle'] 的真实累积值，后续缩放基于对象自身轴向，不会被当作 0 度导致剪切；
                # 2) 避免重复对已旋转过的位图再次旋转，防止包围盒膨胀与画质劣化。
                if app.canvas.type(item_ids[0]) == 'image' and hasattr(app, '_temp_pil_image'):
                    # 仅清理临时缓存，保持 original_pil_image 为未叠加变换的基准图。
                    del app._temp_pil_image

                # For vector shapes, update their coords (convert screen to logical first)
                if app.canvas.type(item_ids[0]) != 'image':
                    from coordinate_system import screen_to_logical
                    app.canvas.update_idletasks()
                    canvas_width = max(app.canvas.winfo_width(), 1)
                    canvas_height = max(app.canvas.winfo_height(), 1)
                    
                    screen_coords = app.canvas.coords(item_ids[0])
                    logical_coords = screen_to_logical(
                        screen_coords,
                        app.zoom_level,
                        app.pan_offset_x,
                        app.pan_offset_y,
                        canvas_width,
                        canvas_height
                    )
                    state['original_coords'] = logical_coords

                # 更新参考变换状态，确保后续缩放使用最新的逻辑基准
                state['zoom_ref'] = app.zoom_level
                state['pan_ref_x'] = app.pan_offset_x
                state['pan_ref_y'] = app.pan_offset_y

                # 保留累积的角度信息，避免后续重绘时被强制“回正”

        app.drag_mode = None
        app.original_group_states.clear()
        
    elif app.current_tool in ["line", "rectangle", "circle"] and app.start_x is not None:
        if abs(app.start_x - event.x) < 2 and abs(app.start_y - event.y) < 2:
            if app.temp_shape: app.canvas.delete(app.temp_shape)
            app.temp_shape, app.start_x, app.start_y = None, None, None
            return

        unique_tag, tags = f"shape_{time.time()}", (f"shape_{time.time()}", app.active_layer_id)
        
        if app.use_rasterization:
            action_completed = True
            if app.temp_shape: app.canvas.delete(app.temp_shape)
            app.temp_shape = None
            from coordinate_system import screen_to_logical, logical_to_screen
            app.canvas.update_idletasks()
            canvas_width = max(app.canvas.winfo_width(), 1)
            canvas_height = max(app.canvas.winfo_height(), 1)

            logical_coords = screen_to_logical(
                [app.start_x, app.start_y, event.x, event.y],
                app.zoom_level,
                app.pan_offset_x,
                app.pan_offset_y,
                canvas_width,
                canvas_height
            )

            state = {
                'tool': app.current_tool,
                'start_xy': (logical_coords[0], logical_coords[1]),
                'end_xy': (logical_coords[2], logical_coords[3]),
                'outline_color': app.current_color, 'fill_color': app.current_fill_color, 'brush_size': app.brush_size,
                'angle': 0,
                'zoom_ref': app.zoom_level, 'pan_ref_x': app.pan_offset_x, 'pan_ref_y': app.pan_offset_y
            }
            img, (x1, y1) = create_rasterized_image(app, state)
            
            if img:
                # 根据缩放级别调整显示尺寸
                display_img = img
                if app.zoom_level != 1.0:
                    new_w = max(int(img.width * app.zoom_level), 1)
                    new_h = max(int(img.height * app.zoom_level), 1)
                    display_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                tk_img = ImageTk.PhotoImage(display_img)
                screen_xy = logical_to_screen(
                    [x1, y1],
                    app.zoom_level,
                    app.pan_offset_x,
                    app.pan_offset_y,
                    canvas_width,
                    canvas_height
                )
                img_id = app.canvas.create_image(screen_xy[0], screen_xy[1], image=tk_img, anchor='nw', tags=tags)
                app._image_references[img_id] = tk_img
                
                state['original_coords'] = logical_coords
                state['original_pil_image'] = img
                app.object_states[tags[0]] = state
        else:
            action_completed = True
            if app.temp_shape: app.canvas.delete(app.temp_shape)
            item_id = None
            if app.current_tool == "line": item_id = app.canvas.create_line(app.start_x, app.start_y, event.x, event.y, fill=app.current_color, width=app.brush_size, capstyle="round", tags=tags)
            elif app.current_tool == "rectangle": item_id = app.canvas.create_rectangle(app.start_x, app.start_y, event.x, event.y, outline=app.current_color, width=app.brush_size, fill=app.current_fill_color, tags=tags)
            elif app.current_tool == "circle": item_id = app.canvas.create_oval(app.start_x, app.start_y, event.x, event.y, outline=app.current_color, width=app.brush_size, fill=app.current_fill_color, tags=tags)
            if item_id:
                # 将屏幕坐标转换为逻辑坐标后保存
                from coordinate_system import screen_to_logical
                app.canvas.update_idletasks()
                canvas_width = max(app.canvas.winfo_width(), 1)
                canvas_height = max(app.canvas.winfo_height(), 1)
                
                screen_coords = app.canvas.coords(item_id)
                logical_coords = screen_to_logical(
                    screen_coords,
                    app.zoom_level,
                    app.pan_offset_x,
                    app.pan_offset_y,
                    canvas_width,
                    canvas_height
                )
                
                app.object_states[tags[0]] = {
                    'angle': 0,
                    'original_coords': logical_coords,
                    'zoom_ref': app.zoom_level, 'pan_ref_x': app.pan_offset_x, 'pan_ref_y': app.pan_offset_y
                }
        
        app.start_x, app.start_y = None, None
        
    elif app.current_tool == "pencil" and app.current_stroke_tag:
        stroke_ids = app.canvas.find_withtag(app.current_stroke_tag)
        tags = (app.current_stroke_tag, app.active_layer_id)
        if stroke_ids:
            if app.use_rasterization:
                action_completed = True
                all_coords = [app.canvas.coords(item_id) for item_id in stroke_ids]
                app.canvas.delete(app.current_stroke_tag)
                
                state = {
                    'tool': 'pencil', 'line_segments': all_coords,
                    'outline_color': app.current_color, 'brush_size': app.brush_size,
                    'angle': 0,
                    'zoom_ref': app.zoom_level, 'pan_ref_x': app.pan_offset_x, 'pan_ref_y': app.pan_offset_y
                }
                img, (x1, y1) = create_rasterized_image(app, state)
                
                if img:
                    # 根据缩放级别调整显示尺寸
                    from coordinate_system import screen_to_logical, logical_to_screen
                    app.canvas.update_idletasks()
                    canvas_width = max(app.canvas.winfo_width(), 1)
                    canvas_height = max(app.canvas.winfo_height(), 1)
                    
                    display_img = img
                    if app.zoom_level != 1.0:
                        new_w = max(int(img.width * app.zoom_level), 1)
                        new_h = max(int(img.height * app.zoom_level), 1)
                        display_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    tk_img = ImageTk.PhotoImage(display_img)
                    
                    # 转换逻辑坐标为屏幕坐标
                    screen_coords = [x1, y1]
                    logical_coords = screen_to_logical(
                        screen_coords,
                        app.zoom_level,
                        app.pan_offset_x,
                        app.pan_offset_y,
                        canvas_width,
                        canvas_height
                    )
                    screen_pos = logical_to_screen(
                        logical_coords[:2],
                        app.zoom_level,
                        app.pan_offset_x,
                        app.pan_offset_y,
                        canvas_width,
                        canvas_height
                    )
                    
                    img_id = app.canvas.create_image(screen_pos[0], screen_pos[1], image=tk_img, anchor='nw', tags=tags)
                    app._image_references[img_id] = tk_img
                    
                    state['original_coords'] = logical_coords
                    state['original_pil_image'] = img
                    app.object_states[tags[0]] = state
            else:
                action_completed = True
                
                # 将所有笔触行段的屏幕坐标转换为逻辑坐标
                from coordinate_system import screen_to_logical
                app.canvas.update_idletasks()
                canvas_width = max(app.canvas.winfo_width(), 1)
                canvas_height = max(app.canvas.winfo_height(), 1)
                
                logical_coords_map = {}
                for item_id in stroke_ids:
                    screen_coords = app.canvas.coords(item_id)
                    logical_coords = screen_to_logical(
                        screen_coords,
                        app.zoom_level,
                        app.pan_offset_x,
                        app.pan_offset_y,
                        canvas_width,
                        canvas_height
                    )
                    logical_coords_map[item_id] = logical_coords
                
                app.object_states[app.current_stroke_tag] = {
                    'angle': 0,
                    'original_coords_map': logical_coords_map,
                    'zoom_ref': app.zoom_level, 'pan_ref_x': app.pan_offset_x, 'pan_ref_y': app.pan_offset_y
                }
        app.current_stroke_tag = None
        
    elif app.current_tool == "eraser" and app.erased_in_drag:
        action_completed, app.erased_in_drag, app.current_stroke_tag = True, False, None
        
    if action_completed:
        app.update_layer_stacking()
        app._capture_and_save_state()


def draw_on_canvas(app, event):
    # 如果按住空格键，拖动画布
    if app.space_pressed and app.pan_start_x is not None:
        dx = event.x - app.pan_start_x
        dy = event.y - app.pan_start_y
        
        # 物理移动所有对象
        app.canvas.move("all", dx, dy)
        
        # 核心修正：严格按照当前缩放倍率反推逻辑偏移量
        # 强制使用 max 防止 zoom 为 0 导致的崩溃
        zoom = max(app.zoom_level, 1e-9)
        app.pan_offset_x += dx / zoom
        app.pan_offset_y += dy / zoom
        
        app.pan_start_x = event.x
        app.pan_start_y = event.y
        
        # 重新绘制网格以保持同步
        if app.grid_visible:
            app.draw_grid()
        
        return
    
    # 处理曲线和曲面控制点拖拽
    if app.current_tool in ["bezier", "bspline", "bezier_surface"]:
        if app.dragging_control_point is not None:
            app.handle_curve_control_point_drag(event)
        return
    
    if app.current_tool == "select" and app.selection_group and app.drag_mode:
        if app.drag_mode == "move":
            dx, dy = event.x - app.last_x, event.y - app.last_y
            for tag in app.selection_group:
                app.canvas.move(tag, dx, dy)
                
                # 修复：同步更新 object_states 里的逻辑数据，防止曲面/曲线"传送回中心"
                state = app.object_states.get(tag)
                if state:
                    # 将屏幕像素位移转换为逻辑位移
                    zoom = max(app.zoom_level, 1e-9)
                    dlx, dly = dx / zoom, dy / zoom
                    
                    # 更新曲面的控制网格
                    if 'control_grid' in state:
                        state['control_grid'] = [
                            [(p[0] + dlx, p[1] + dly, p[2]) for p in row] 
                            for row in state['control_grid']
                        ]
                    
                    # 更新曲线的控制点
                    if 'control_points' in state:
                        state['control_points'] = [
                            (p[0] + dlx, p[1] + dly) for p in state['control_points']
                        ]
                    
                    # 更新普通图形的逻辑坐标（但不包括光栅图像，它们有特殊处理）
                    if 'original_coords' in state:
                        item_ids = app.canvas.find_withtag(tag)
                        if item_ids:
                            item_type = app.canvas.type(item_ids[0])
                            if item_type != 'image':
                                state['original_coords'] = [
                                    c + (dlx if i % 2 == 0 else dly) 
                                    for i, c in enumerate(state['original_coords'])
                                ]
                    
                    # 更新曲线的逻辑坐标（曲线对象同时有control_points和original_coords）
                    if 'original_coords' in state and tag.startswith("curve_"):
                        state['original_coords'] = [
                            c + (dlx if i % 2 == 0 else dly) 
                            for i, c in enumerate(state['original_coords'])
                        ]
                    
                    # 更新光栅图像的逻辑位置
                    if 'start_xy' in state:
                        state['start_xy'] = (state['start_xy'][0] + dlx, state['start_xy'][1] + dly)
                    if 'end_xy' in state:
                        state['end_xy'] = (state['end_xy'][0] + dlx, state['end_xy'][1] + dly)
                    
                    # 更新笔触的坐标映射
                    if 'original_coords_map' in state:
                        for seg_id in state['original_coords_map']:
                            state['original_coords_map'][seg_id] = [
                                c + (dlx if i % 2 == 0 else dly)
                                for i, c in enumerate(state['original_coords_map'][seg_id])
                            ]
            
            app.canvas.move("handle", dx, dy) 
            app.last_x, app.last_y = event.x, event.y
        elif app.drag_mode == "resize" and app.original_bbox: _handle_resize(app, event)
        elif app.drag_mode == "rotate": _handle_rotate(app, event)
    
    elif app.current_tool == "eraser":
        app.erased_in_drag = True
        if app.eraser_mode == "对象":
            items_under_cursor = app.canvas.find_overlapping(event.x - app.brush_size / 2, event.y - app.brush_size / 2, event.x + app.brush_size / 2, event.y + app.brush_size / 2)
            tags_to_delete = {t for item in items_under_cursor for t in app.canvas.gettags(item) if t.startswith(("stroke_", "shape_")) and app.active_layer_id in app.canvas.gettags(item)}
            if tags_to_delete:
                for tag in tags_to_delete:
                    app.canvas.delete(tag)
                    if tag in app.object_states: del app.object_states[tag]
                    if tag in app.selection_group: app.selection_group.remove(tag)
                app._draw_resize_handles()
        else: 
            r = app.brush_size / 2
            app.canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r, fill=app.canvas_bg_color, outline=app.canvas_bg_color, tags=("eraser_mark", app.current_stroke_tag, app.active_layer_id))
    
    elif app.current_tool not in ["polygon", "fill", "select", "text"] and app.start_x is not None:
        # 根据缩放调整预览线宽
        display_width = max(1, int(app.brush_size * app.zoom_level))
        
        if app.current_tool == "pencil":
            app.canvas.create_line(app.start_x, app.start_y, event.x, event.y, fill=app.current_color, width=display_width, capstyle="round", smooth=True, tags=(app.current_stroke_tag, app.active_layer_id))
            app.start_x, app.start_y = event.x, event.y
        else:
            if app.temp_shape: app.canvas.delete(app.temp_shape)
            if app.current_tool == "line": app.temp_shape = app.canvas.create_line(app.start_x, app.start_y, event.x, event.y, fill=app.current_color, width=display_width, capstyle="round")
            elif app.current_tool == "rectangle": app.temp_shape = app.canvas.create_rectangle(app.start_x, app.start_y, event.x, event.y, outline=app.current_color, width=display_width, fill=app.current_fill_color)
            elif app.current_tool == "circle": app.temp_shape = app.canvas.create_oval(app.start_x, app.start_y, event.x, event.y, outline=app.current_color, width=display_width, fill=app.current_fill_color)


def _handle_resize(app, event):
    x1_orig_bbox, y1_orig_bbox, x2_orig_bbox, y2_orig_bbox = app.original_bbox
    origin_x, origin_y = (x1_orig_bbox + x2_orig_bbox) / 2, (y1_orig_bbox + y2_orig_bbox) / 2
    if "left" in app.drag_handle_type: origin_x = x2_orig_bbox
    elif "right" in app.drag_handle_type: origin_x = x1_orig_bbox
    if "top" in app.drag_handle_type: origin_y = y2_orig_bbox
    elif "bottom" in app.drag_handle_type: origin_y = y1_orig_bbox
    
    from coordinate_system import screen_to_logical, logical_to_screen
    app.canvas.update_idletasks()
    canvas_width = max(app.canvas.winfo_width(), 1)
    canvas_height = max(app.canvas.winfo_height(), 1)

    logical_bbox = screen_to_logical(
        [x1_orig_bbox, y1_orig_bbox, x2_orig_bbox, y2_orig_bbox],
        app.zoom_level,
        app.pan_offset_x,
        app.pan_offset_y,
        canvas_width,
        canvas_height
    )
    lx1, ly1, lx2, ly2 = logical_bbox
    origin_lx, origin_ly = (lx1 + lx2) / 2, (ly1 + ly2) / 2
    if "left" in app.drag_handle_type: origin_lx = lx2
    elif "right" in app.drag_handle_type: origin_lx = lx1
    if "top" in app.drag_handle_type: origin_ly = ly2
    elif "bottom" in app.drag_handle_type: origin_ly = ly1

    old_w_logical, old_h_logical = (lx2 - lx1) or 1, (ly2 - ly1) or 1
    event_logical = screen_to_logical(
        [event.x, event.y],
        app.zoom_level,
        app.pan_offset_x,
        app.pan_offset_y,
        canvas_width,
        canvas_height
    )
    ex_l, ey_l = event_logical[0], event_logical[1]

    new_w_logical, new_h_logical = old_w_logical, old_h_logical
    if "left" in app.drag_handle_type: new_w_logical = origin_lx - ex_l
    elif "right" in app.drag_handle_type: new_w_logical = ex_l - origin_lx
    if "top" in app.drag_handle_type: new_h_logical = origin_ly - ey_l
    elif "bottom" in app.drag_handle_type: new_h_logical = ey_l - origin_ly
    
    scale_x, scale_y = new_w_logical / old_w_logical if old_w_logical != 0 else 1.0, new_h_logical / old_h_logical if old_h_logical != 0 else 1.0
    if "center" in app.drag_handle_type: scale_x = 1.0
    if "middle" in app.drag_handle_type: scale_y = 1.0

    origin_screen = logical_to_screen(
        [origin_lx, origin_ly],
        app.zoom_level,
        app.pan_offset_x,
        app.pan_offset_y,
        canvas_width,
        canvas_height
    )
    origin_x, origin_y = origin_screen[0], origin_screen[1]

    # 定义局部坐标变换函数:全局->局部(逆旋转)->缩放->全局(正旋转)
    def transform_point_locally(px, py, anchor_x, anchor_y, angle_deg, sx, sy):
        angle_rad = math.radians(angle_deg)
        tx, ty = px - anchor_x, py - anchor_y
        rx, ry = rotate_point(tx, ty, -angle_rad, 0, 0)
        scaled_rx, scaled_ry = rx * sx, ry * sy
        fx, fy = rotate_point(scaled_rx, scaled_ry, angle_rad, 0, 0)
        return fx + anchor_x, fy + anchor_y

    for tag in app.selection_group:
        items = app.canvas.find_withtag(tag)
        if not items: continue
        item_id = items[0]
        
        if app.canvas.type(item_id) == 'image':
            # 使用对象的本地坐标系（考虑当前角度）计算缩放，避免旋转形状被“拉胖”或剪切
            state = app.object_states.get(tag, {})
            original_state = app.original_group_states.get(tag)
            if not original_state: continue

            # 角度（度 -> 弧度），默认 0
            angle_deg = state.get('angle', original_state.get('angle', 0))
            angle_rad = math.radians(angle_deg)

            # 从原始状态获取未旋转的几何包围盒（逻辑坐标）
            def _geometry_bbox(st):
                if 'start_xy' in st and 'end_xy' in st:
                    sx, sy = st['start_xy']
                    ex, ey = st['end_xy']
                    return min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)
                if 'points' in st and st['points']:
                    xs, ys = zip(*st['points'])
                    return min(xs), min(ys), max(xs), max(ys)
                if 'line_segments' in st and st['line_segments']:
                    xs, ys = [], []
                    for seg in st['line_segments']:
                        xs.extend([seg[0], seg[2]])
                        ys.extend([seg[1], seg[3]])
                    if xs and ys:
                        return min(xs), min(ys), max(xs), max(ys)
                return None

            geom_bbox = _geometry_bbox(original_state)
            if not geom_bbox: continue
            gx1, gy1, gx2, gy2 = geom_bbox
            center_lx, center_ly = (gx1 + gx2) / 2, (gy1 + gy2) / 2

            # 锚点（保持对侧不动）
            anchor_x = gx2 if "left" in app.drag_handle_type else gx1 if "right" in app.drag_handle_type else center_lx
            anchor_y = gy2 if "top" in app.drag_handle_type else gy1 if "bottom" in app.drag_handle_type else center_ly

            # 在全局逻辑空间中计算缩放比例（避免坐标系混淆）
            old_w_logical = (gx2 - gx1) or 1.0
            old_h_logical = (gy2 - gy1) or 1.0

            new_w_logical = old_w_logical
            new_h_logical = old_h_logical
            if "left" in app.drag_handle_type:
                new_w_logical = max(anchor_x - ex_l, 1e-3)
            elif "right" in app.drag_handle_type:
                new_w_logical = max(ex_l - anchor_x, 1e-3)
            if "top" in app.drag_handle_type:
                new_h_logical = max(anchor_y - ey_l, 1e-3)
            elif "bottom" in app.drag_handle_type:
                new_h_logical = max(ey_l - anchor_y, 1e-3)

            scale_x = new_w_logical / old_w_logical if "center" not in app.drag_handle_type else 1.0
            scale_y = new_h_logical / old_h_logical if "middle" not in app.drag_handle_type else 1.0

            temp_state = original_state.copy()
            temp_state['angle'] = angle_deg

            # 定义：局部坐标变换函数（仅供显式点使用）
            def transform_point_locally(px, py, center_x, center_y, angle_rad, sx, sy):
                tx, ty = px - center_x, py - center_y
                rx, ry = rotate_point(tx, ty, -angle_rad, 0, 0)
                scaled_rx, scaled_ry = rx * sx, ry * sy
                fx, fy = rotate_point(scaled_rx, scaled_ry, angle_rad, 0, 0)
                return fx + center_x, fy + center_y

            # 处理矩形/圆（参数化）：在全局空间中直接缩放，保留角度
            if 'start_xy' in original_state and 'end_xy' in original_state:
                sx, sy = original_state['start_xy']
                ex, ey = original_state['end_xy']
                # 全局空间中缩放，避免坐标系混淆
                new_sx = anchor_x + (sx - anchor_x) * scale_x
                new_sy = anchor_y + (sy - anchor_y) * scale_y
                new_ex = anchor_x + (ex - anchor_x) * scale_x
                new_ey = anchor_y + (ey - anchor_y) * scale_y
                temp_state['start_xy'] = (new_sx, new_sy)
                temp_state['end_xy'] = (new_ex, new_ey)

            if 'points' in original_state and original_state['points']:
                # 计算多边形几何中心作为缩放基准
                xs, ys = zip(*original_state['points'])
                geom_cx, geom_cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                # 在局部坐标系中缩放（正确处理旋转）
                scaled_points = []
                for px, py in original_state['points']:
                    nx, ny = transform_point_locally(px, py, geom_cx, geom_cy, angle_deg, scale_x, scale_y)
                    scaled_points.append((nx, ny))
                temp_state['points'] = scaled_points
                # 点已在最终位置,不需要 rasterizer 再旋转
                temp_state['angle'] = 0

            if 'line_segments' in original_state and original_state['line_segments']:
                # 计算笔迹几何中心
                xs, ys = [], []
                for seg in original_state['line_segments']:
                    xs.extend([seg[0], seg[2]])
                    ys.extend([seg[1], seg[3]])
                geom_cx, geom_cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                # 在局部坐标系中缩放线段端点
                scaled_segments = []
                for seg in original_state['line_segments']:
                    x1, y1 = transform_point_locally(seg[0], seg[1], geom_cx, geom_cy, angle_deg, scale_x, scale_y)
                    x2, y2 = transform_point_locally(seg[2], seg[3], geom_cx, geom_cy, angle_deg, scale_x, scale_y)
                    scaled_segments.append([x1, y1, x2, y2])
                temp_state['line_segments'] = scaled_segments
                # 点已在最终位置,不需要 rasterizer 再旋转
                temp_state['angle'] = 0

            resized_img, (img_x, img_y) = create_rasterized_image(app, temp_state)
            if not resized_img: continue

            app._temp_pil_image = resized_img
            if not hasattr(app, '_temp_state_updates'): app._temp_state_updates = {}
            updates = {'angle': angle_deg}
            if 'start_xy' in temp_state: updates['start_xy'] = temp_state['start_xy']
            if 'end_xy' in temp_state: updates['end_xy'] = temp_state['end_xy']
            if 'points' in temp_state: updates['points'] = temp_state['points']
            if 'line_segments' in temp_state: updates['line_segments'] = temp_state['line_segments']
            app._temp_state_updates[tag] = updates

            img_coords_screen = logical_to_screen(
                [img_x, img_y],
                app.zoom_level,
                app.pan_offset_x,
                app.pan_offset_y,
                canvas_width,
                canvas_height
            )

            display_img = resized_img
            if app.zoom_level != 1.0:
                new_w = max(int(resized_img.width * app.zoom_level), 1)
                new_h = max(int(resized_img.height * app.zoom_level), 1)
                display_img = resized_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            tk_img = ImageTk.PhotoImage(display_img)
            app.canvas.itemconfig(item_id, image=tk_img)
            app._image_references[item_id] = tk_img
            app.canvas.coords(item_id, img_coords_screen[0], img_coords_screen[1])
        else: # Vector objects can be scaled directly
            original_coords_or_map = app.original_group_states.get(tag)
            if isinstance(original_coords_or_map, dict):
                for part_id, original_coords in original_coords_or_map.items():
                    app.canvas.coords(part_id, *original_coords)
                    app.canvas.scale(part_id, origin_x, origin_y, scale_x, scale_y)
            else:
                app.canvas.coords(item_id, *original_coords_or_map)
                app.canvas.scale(item_id, origin_x, origin_y, scale_x, scale_y)
            
            # 新增：同步更新矢量对象的逻辑状态（control_grid, control_points 等）
            if hasattr(app, 'original_logical_states') and tag in app.original_logical_states:
                orig_logical_state = app.original_logical_states[tag]
                if not hasattr(app, '_temp_state_updates'): app._temp_state_updates = {}
                if tag not in app._temp_state_updates: app._temp_state_updates[tag] = {}
                
                # 更新 control_grid (曲面)
                if 'control_grid' in orig_logical_state:
                    new_grid = []
                    for row in orig_logical_state['control_grid']:
                        new_row = []
                        for pt in row:
                            # pt 是逻辑坐标 (x, y, z)
                            # 在逻辑空间中缩放
                            nx = origin_lx + (pt[0] - origin_lx) * scale_x
                            ny = origin_ly + (pt[1] - origin_ly) * scale_y
                            new_row.append((nx, ny, pt[2]))
                        new_grid.append(new_row)
                    app._temp_state_updates[tag]['control_grid'] = new_grid
                
                # 更新 control_points (曲线)
                if 'control_points' in orig_logical_state:
                    new_points = []
                    for pt in orig_logical_state['control_points']:
                        nx = origin_lx + (pt[0] - origin_lx) * scale_x
                        ny = origin_ly + (pt[1] - origin_ly) * scale_y
                        new_points.append((nx, ny))
                    app._temp_state_updates[tag]['control_points'] = new_points
    
    app._draw_resize_handles()


def _handle_rotate(app, event):
    from coordinate_system import screen_to_logical, logical_to_screen
    app.canvas.update_idletasks()
    canvas_width = max(app.canvas.winfo_width(), 1)
    canvas_height = max(app.canvas.winfo_height(), 1)
    
    # 将屏幕旋转中心转换为逻辑坐标
    shape_center_logical = screen_to_logical(
        [app.shape_center[0], app.shape_center[1]],
        app.zoom_level,
        app.pan_offset_x,
        app.pan_offset_y,
        canvas_width,
        canvas_height
    )
    center_lx, center_ly = shape_center_logical[0], shape_center_logical[1]
    
    current_angle_rad = math.atan2(event.y - app.shape_center[1], event.x - app.shape_center[0])
    rotation_delta_rad = current_angle_rad - app.drag_start_angle
    
    for tag in app.selection_group:
        items = app.canvas.find_withtag(tag)
        if not items: continue
        item_id = items[0]

        if app.canvas.type(item_id) == 'image':
            state = app.object_states.get(tag, {})
            orig_state = app.original_group_states.get(tag, state)

            base_angle_deg = state.get('angle', orig_state.get('angle', 0))
            new_angle_deg = base_angle_deg + math.degrees(rotation_delta_rad)

            temp_state = state.copy()
            
            # 对于显式点集,需要更新点坐标而不是角度(防止二次旋转)
            if 'points' in orig_state and orig_state['points']:
                rotated_points = []
                for px, py in orig_state['points']:
                    nx, ny = rotate_point(px, py, rotation_delta_rad, center_lx, center_ly)
                    rotated_points.append((nx, ny))
                temp_state['points'] = rotated_points
                temp_state['angle'] = 0  # 点已转好,不需再旋转
            elif 'line_segments' in orig_state and orig_state['line_segments']:
                rotated_segments = []
                for seg in orig_state['line_segments']:
                    x1, y1 = rotate_point(seg[0], seg[1], rotation_delta_rad, center_lx, center_ly)
                    x2, y2 = rotate_point(seg[2], seg[3], rotation_delta_rad, center_lx, center_ly)
                    rotated_segments.append([x1, y1, x2, y2])
                temp_state['line_segments'] = rotated_segments
                temp_state['angle'] = 0  # 同上
            else:
                # 参数化形状(矩形/圆),只更新角度
                temp_state['angle'] = new_angle_deg

            rotated_img, (img_x, img_y) = create_rasterized_image(app, temp_state)
            if not rotated_img: continue

            app._temp_pil_image = rotated_img

            display_img = rotated_img
            if app.zoom_level != 1.0:
                new_w = max(int(rotated_img.width * app.zoom_level), 1)
                new_h = max(int(rotated_img.height * app.zoom_level), 1)
                display_img = rotated_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            tk_img = ImageTk.PhotoImage(display_img)
            app.canvas.itemconfig(item_id, image=tk_img)
            app._image_references[item_id] = tk_img

            screen_pos = logical_to_screen(
                [img_x, img_y],
                app.zoom_level,
                app.pan_offset_x,
                app.pan_offset_y,
                canvas_width,
                canvas_height
            )
            app.canvas.coords(item_id, screen_pos[0], screen_pos[1])

            if not hasattr(app, '_temp_state_updates'): app._temp_state_updates = {}
            app._temp_state_updates[tag] = {
                'angle': new_angle_deg
            }
        else:
            original_coords_or_map = app.original_group_states.get(tag)
            if isinstance(original_coords_or_map, dict):
                for part_id, original_coords in original_coords_or_map.items():
                    new_coords = [c for p in zip(original_coords[::2], original_coords[1::2]) for c in rotate_point(p[0], p[1], rotation_delta_rad, app.shape_center[0], app.shape_center[1])]
                    app.canvas.coords(part_id, *new_coords)
            else:
                new_coords = [c for p in zip(original_coords_or_map[::2], original_coords_or_map[1::2]) for c in rotate_point(p[0], p[1], rotation_delta_rad, app.shape_center[0], app.shape_center[1])]
                app.canvas.coords(item_id, *new_coords)
    
    app._draw_resize_handles()