# shape_handlers.py

"""
Shape handling, filling, and text creation utilities for DrawingApp.
"""
import time
from tkinter import messagebox
from PIL import Image, ImageTk
from drawing_utils import create_rasterized_image
from tools import TextToolDialog


def _redraw_fill(app, unique_tag, outline_points=None):
    # This function is for vector shapes, raster shapes handle fill internally.
    pass


def fill_shape(app, event):
    ids = app.canvas.find_closest(event.x, event.y)
    if not ids: return
    item_tags = app.canvas.gettags(ids[0])
    unique_tag = next((t for t in item_tags if t.startswith('shape_')), None)
    
    if not unique_tag: return

    items_to_modify = app.canvas.find_withtag(unique_tag)
    if not items_to_modify: return
    item_id = items_to_modify[0]
    
    item_type = app.canvas.type(item_id)
    color_to_use = app.current_fill_color or ""
    modified = False

    # Branch 1: Rasterized Image Objects
    if item_type == "image":
        state = app.object_states.get(unique_tag)
        if not state or state.get('tool') in ['pencil', 'line']: return

        state['fill_color'] = color_to_use
        img, (x1, y1) = create_rasterized_image(app, state)
        
        if img:
            # Update the original PIL image in memory for future transforms
            state['original_pil_image'] = img
            
            # 根据当前 zoom 级别缩放图像
            zoom_ref = state.get('zoom_ref', 1.0)
            scale_factor = app.zoom_level / max(zoom_ref, 1e-9)
            
            if abs(scale_factor - 1.0) > 0.01:  # 如果缩放因子不是 1.0
                new_width = max(int(img.width * scale_factor), 1)
                new_height = max(int(img.height * scale_factor), 1)
                scaled_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(scaled_img)
            else:
                tk_img = ImageTk.PhotoImage(img)
            
            app.canvas.itemconfig(item_id, image=tk_img)
            app._image_references[item_id] = tk_img
            
            # 将逻辑坐标转换为屏幕坐标后再设置位置
            from coordinate_system import logical_to_screen
            app.canvas.update_idletasks()
            canvas_width = max(app.canvas.winfo_width(), 1)
            canvas_height = max(app.canvas.winfo_height(), 1)
            
            # x1, y1 是逻辑坐标，需要转换为屏幕坐标
            screen_coords = logical_to_screen(
                [x1, y1],
                app.zoom_level,
                app.pan_offset_x,
                app.pan_offset_y,
                canvas_width,
                canvas_height
            )
            app.canvas.coords(item_id, screen_coords[0], screen_coords[1])
            modified = True

    # Branch 2: Vector Objects
    elif item_type in ["rectangle", "oval", "polygon"]:
        try:
            app.canvas.itemconfig(item_id, fill=color_to_use)
            modified = True
        except Exception: pass
    
    if modified:
        app.update_layer_stacking()
        app._capture_and_save_state()


def finalize_polygon(app):
    if len(app.polygon_points) < 3:
        messagebox.showwarning("警告", "多边形至少需要3个点")
        app.reset_polygon_drawing()
        return
    
    from coordinate_system import screen_to_logical, logical_to_screen
    app.canvas.update_idletasks()
    canvas_width = max(app.canvas.winfo_width(), 1)
    canvas_height = max(app.canvas.winfo_height(), 1)

    logical_points = []
    for x, y in app.polygon_points:
        logical_xy = screen_to_logical(
            [x, y],
            app.zoom_level,
            app.pan_offset_x,
            app.pan_offset_y,
            canvas_width,
            canvas_height
        )
        logical_points.append((logical_xy[0], logical_xy[1]))

    unique_tag, tags = f"shape_{time.time()}", (f"shape_{time.time()}", app.active_layer_id)
    
    if app.use_rasterization:
        state = {
            'tool': 'polygon', 'points': list(logical_points),
            'outline_color': app.current_color, 'fill_color': app.current_fill_color,
            'brush_size': app.brush_size, 'angle': 0,
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
            
            # 将光栅化图像的位置转换为逻辑坐标
            state['original_coords'] = [x1, y1]
            state['original_pil_image'] = img
            app.object_states[tags[0]] = state
    else:
        logical_coords_flat = [c for p in logical_points for c in p]
        screen_coords = logical_to_screen(
            logical_coords_flat,
            app.zoom_level,
            app.pan_offset_x,
            app.pan_offset_y,
            canvas_width,
            canvas_height
        )
        item_id = app.canvas.create_polygon(screen_coords, outline=app.current_color, width=app.brush_size,
                                   fill=app.current_fill_color, tags=tags)
        app.object_states[tags[0]] = {'angle': 0, 'original_coords': logical_coords_flat}
    
    app.reset_polygon_drawing()
    app._capture_and_save_state()


def create_text_object(app, x, y):
    dialog = TextToolDialog(app, title="输入文本")
    app.wait_window(dialog)
    
    if hasattr(dialog, 'result') and dialog.result:
        text, font_family, font_size = dialog.result
        
        # 根据缩放调整显示字号，但保存逻辑字号
        logical_font_size = font_size
        display_font_size = max(1, int(font_size * app.zoom_level))
        font_info = f"{font_family} {display_font_size}"
        unique_tag, tags = f"shape_{time.time()}", (f"shape_{time.time()}", app.active_layer_id)
        
        text_item = app.canvas.create_text(x, y, text=text, fill=app.current_color, font=font_info, tags=tags)
        
        # 将屏幕坐标转换为逻辑坐标后保存
        from coordinate_system import screen_to_logical
        app.canvas.update_idletasks()
        canvas_width = max(app.canvas.winfo_width(), 1)
        canvas_height = max(app.canvas.winfo_height(), 1)
        
        logical_coords = screen_to_logical(
            [x, y],
            app.zoom_level,
            app.pan_offset_x,
            app.pan_offset_y,
            canvas_width,
            canvas_height
        )
        
        app.object_states[unique_tag] = {
            'angle': 0,
            'original_coords': logical_coords,
            'tool': 'text',
            'text': text,
            'font': f"{font_family} {logical_font_size}",
            'fill_color': app.current_color,
            'logical_font_size': logical_font_size,
            'zoom_ref': app.zoom_level,
            'pan_ref_x': app.pan_offset_x,
            'pan_ref_y': app.pan_offset_y
        }
        app._capture_and_save_state()