"""
History and undo/redo management for DrawingApp.
"""
import copy


def capture_and_save_state(app):
    """Capture the current canvas state and save it to the history stack."""
    state = app._get_canvas_state()
    if len(app.history_stack) >= app.history_limit:
        app.history_stack.pop(0)
    state['object_states'] = copy.deepcopy(state['object_states'])
    app.history_stack.append(state)


def restore_state_from_history(app, state):
    """从历史记录中恢复画布状态"""
    # 1. 清空当前所有元素和控制柄
    app._clear_resize_handles()
    app.selection_group.clear()
    app.canvas.delete("all")

    # 2. 恢复关键颜色状态
    # 修复核心：Canvas控件的背景色应保持为Viewport颜色，而不是画布颜色
    app.canvas_bg_color = state["bg_color"]
    viewport_color = getattr(app, "viewport_bg_color", "#202020")
    app.canvas.config(bg=viewport_color) 

    # 3. 恢复视图参数（缩放和平移）
    app.zoom_level = state.get("zoom_level", 1.0)
    app.pan_offset_x = state.get("pan_offset_x", 0)
    app.pan_offset_y = state.get("pan_offset_y", 0)

    # 4. 恢复图层元数据
    app.layers = copy.deepcopy(state["layers"])
    app.active_layer_id = state["active_layer_id"]
    app.layer_counter = state.get("layer_counter", app.layer_counter)

    # 5. 【关键点】重绘背景区域和网格
    # 这会重新在逻辑坐标 (0,0) 到 (Width, Height) 创建那个矩形
    app.draw_canvas_background() 
    if app.grid_visible:
        app.draw_grid()

    # 6. 恢复对象数据
    app.object_states = copy.deepcopy(state["object_states"])
    
    # 重建图像对象 (Base64 -> PIL)
    import base64, io
    from PIL import Image, ImageTk
    for tag, st in app.object_states.items():
        if 'original_pil_image_b64' in st:
            try:
                data = base64.b64decode(st.pop('original_pil_image_b64'))
                st['original_pil_image'] = Image.open(io.BytesIO(data)).convert('RGBA')
            except:
                pass

    # 7. 重新创建 Canvas 项
    for item_info in state["items"]:
        if not item_info["coords"]: continue
        
        creator_func = getattr(app.canvas, f"create_{item_info['type']}", None)
        if creator_func:
            options = dict(item_info["options"])
            
            # 特殊处理图像，因为 Tkinter 的 image 句柄不能序列化
            if item_info["type"] == "image":
                tags = options.get('tags', '')
                tag_list = tags if isinstance(tags, (list, tuple)) else tags.split()
                unique_tag = next((t for t in tag_list if t.startswith(('shape_', 'stroke_', 'erase_', 'surface_', 'curve_'))), None)
                
                pil_img = None
                if unique_tag and unique_tag in app.object_states:
                    pil_img = app.object_states[unique_tag].get('original_pil_image')
                
                if pil_img:
                    tk_img = ImageTk.PhotoImage(pil_img)
                    options['image'] = tk_img
                    new_item = creator_func(item_info["coords"], **options)
                    app._image_references[new_item] = tk_img
                else: continue
            else:
                new_item = creator_func(item_info["coords"], **options)

            # 保持图层可见性状态
            for tag in app.canvas.gettags(new_item):
                if tag.startswith("layer_"):
                    layer = app.get_layer_by_id(tag)
                    if layer and not layer['visible']:
                        app.canvas.itemconfig(new_item, state='hidden')
                    break

    # 8. 强制坐标同步（同步当前 zoom 和 pan 到所有物体）
    from coordinate_system import sync_all_objects_to_screen
    sync_all_objects_to_screen(app)
    
    # 9. 更新UI
    app.update_layer_list_ui()
    app.update_layer_stacking()
    if hasattr(app, 'zoom_label'):
        app.zoom_label.configure(text=f"{int(app.zoom_level * 100)}%")
    if hasattr(app, 'zoom_slider'):
        app.zoom_slider.set(app.zoom_level * 100)
    
    app._rebuild_stroke_maps_after_restore()


def undo_last_action(app):
    """Undo the last drawing action."""
    if len(app.history_stack) > 1:
        app.history_stack.pop()
        restore_state_from_history(app, app.history_stack[-1])
