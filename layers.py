import time
import copy
from tkinter import messagebox, simpledialog
import customtkinter as ctk
from PIL import ImageTk

# layers utilities extracted from app_core

def add_new_layer(app, name=None, insert_index=None):
    app.layer_counter += 1
    layer_name = name or f"图层 {app.layer_counter}"
    layer_id = f"layer_{time.time()}_{app.layer_counter}"
    new_layer = {'id': layer_id, 'name': layer_name, 'visible': True, 'opacity': 1.0}

    if insert_index is not None:
        app.layers.insert(insert_index, new_layer)
    else:
        app.layers.append(new_layer)

    app.active_layer_id = layer_id
    update_layer_list_ui(app)
    update_layer_stacking(app)
    return new_layer


def _get_selected_layer_index(app):
    for i, layer in enumerate(app.layers):
        if layer['id'] == app.active_layer_id:
            return i
    return None


def delete_selected_layer(app):
    if len(app.layers) <= 1:
        messagebox.showwarning("警告", "无法删除最后一个图层。")
        return
    selected_index = _get_selected_layer_index(app)
    if selected_index is not None:
        layer_to_delete = app.layers.pop(selected_index)
        tags_to_remove = set()
        for tag in app.selection_group:
            first_item = app.canvas.find_withtag(tag)
            if first_item and layer_to_delete['id'] in app.canvas.gettags(first_item[0]):
                tags_to_remove.add(tag)
        if tags_to_remove:
            app.selection_group -= tags_to_remove
            app._clear_resize_handles()
        app.canvas.delete(layer_to_delete['id'])
        if selected_index >= len(app.layers):
            selected_index = len(app.layers) - 1
        app.active_layer_id = app.layers[selected_index]['id']
        update_layer_list_ui(app)
        app._capture_and_save_state()


def duplicate_selected_layer(app):
    selected_index = _get_selected_layer_index(app)
    if selected_index is None: return
    source_layer = app.layers[selected_index]
    new_layer_data = add_new_layer(app, name=f"{source_layer['name']} 副本", insert_index=selected_index + 1)
    new_layer_id = new_layer_data['id']
    new_layer = get_layer_by_id(app, new_layer_id)
    new_layer['opacity'] = source_layer['opacity']

    tag_mapping = {}  # old unique_tag -> new unique_tag
    part_mapping = {} # old unique_tag -> list of (old_part_id, new_part_id)
    state_cache = {}  # old unique_tag -> original state copy

    items_to_copy = app.canvas.find_withtag(source_layer['id'])
    for item_id in items_to_copy:
        item_type = app.canvas.type(item_id)
        coords = app.canvas.coords(item_id)
        cleaned_options = {}
        copy_keys = ['tags', 'width', 'fill', 'outline', 'capstyle', 'smooth', 'joinstyle', 'dash', 'text', 'font', 'anchor']
        for key in copy_keys:
            try:
                cleaned_options[key] = app.canvas.itemcget(item_id, key)
            except: pass
        original_tags = list(app.canvas.gettags(item_id))
        new_tags = [t for t in original_tags if t != source_layer['id']]
        new_tags.append(new_layer_id)
        unique_tag = next((t for t in original_tags if t.startswith(('shape_', 'stroke_', 'erase_stroke_'))), None)
        new_unique_tag = None
        if unique_tag:
            if unique_tag not in tag_mapping:
                tag_mapping[unique_tag] = f"{unique_tag.split('_')[0]}_{time.time()}"
            new_unique_tag = tag_mapping[unique_tag]
            new_tags = [t if t != unique_tag else new_unique_tag for t in new_tags]

        if item_type == "image":
            state = app.object_states.get(unique_tag or "")
            pil_img = state.get('original_pil_image') if state else None
            if not pil_img: continue

            from coordinate_system import logical_to_screen
            app.canvas.update_idletasks()
            canvas_width = max(app.canvas.winfo_width(), 1)
            canvas_height = max(app.canvas.winfo_height(), 1)

            if state and 'start_xy' in state:
                logical_pos = state['start_xy']
            elif state and 'original_coords' in state and len(state['original_coords']) >= 2:
                logical_pos = (state['original_coords'][0], state['original_coords'][1])
            else:
                continue

            screen_pos = logical_to_screen(
                list(logical_pos),
                app.zoom_level,
                app.pan_offset_x,
                app.pan_offset_y,
                canvas_width,
                canvas_height
            )

            pil_img_copy = pil_img.copy()
            tk_img = ImageTk.PhotoImage(pil_img_copy)

            cleaned_options['tags'] = new_tags
            new_item_id = app.canvas.create_image(screen_pos[0], screen_pos[1], image=tk_img, anchor='nw', tags=tuple(new_tags))
            app._image_references[new_item_id] = tk_img

            if new_unique_tag and state:
                state_copy = copy.deepcopy(state)
                state_copy['original_pil_image'] = pil_img_copy
                app.object_states[new_unique_tag] = state_copy
            continue

        cleaned_options['tags'] = new_tags
        creator_func = getattr(app.canvas, f"create_{item_type}", None)
        if creator_func:
            new_item_id = creator_func(coords, **cleaned_options)
            if unique_tag and new_unique_tag:
                if unique_tag not in part_mapping:
                    part_mapping[unique_tag] = []
                part_mapping[unique_tag].append((item_id, new_item_id))
                if unique_tag not in state_cache and unique_tag in app.object_states:
                    state_cache[unique_tag] = copy.deepcopy(app.object_states[unique_tag])

    # 复制矢量对象的状态数据
    for old_tag, new_tag in tag_mapping.items():
        state = state_cache.get(old_tag) or app.object_states.get(old_tag)
        if not state:
            continue
        new_state = copy.deepcopy(state)

        if 'original_coords_map' in new_state and isinstance(new_state['original_coords_map'], dict):
            new_map = {}
            for old_id, new_id in part_mapping.get(old_tag, []):
                if old_id in new_state['original_coords_map']:
                    new_map[new_id] = new_state['original_coords_map'][old_id]
            new_state['original_coords_map'] = new_map

        app.object_states[new_tag] = new_state
    update_layer_list_ui(app)
    update_layer_stacking(app)
    app._capture_and_save_state()


def move_layer_up(app):
    idx = _get_selected_layer_index(app)
    if idx is not None and idx < len(app.layers) - 1:
        app.layers[idx], app.layers[idx+1] = app.layers[idx+1], app.layers[idx]
        update_layer_list_ui(app)
        update_layer_stacking(app)
        app._capture_and_save_state()


def move_layer_down(app):
    idx = _get_selected_layer_index(app)
    if idx is not None and idx > 0:
        app.layers[idx], app.layers[idx-1] = app.layers[idx-1], app.layers[idx]
        update_layer_list_ui(app)
        update_layer_stacking(app)
        app._capture_and_save_state()


def select_layer(app, layer_id):
    if app.active_layer_id != layer_id:
        app.active_layer_id = layer_id
        update_layer_list_ui(app)
        if app.selection_group:
            app._clear_resize_handles()
            app.selection_group.clear()


def toggle_layer_visibility(app, layer_id):
    layer = get_layer_by_id(app, layer_id)
    if layer:
        layer['visible'] = not layer['visible']
        new_state = "normal" if layer['visible'] else "hidden"
        app.canvas.itemconfig(layer_id, state=new_state)
        update_layer_list_ui(app)


def set_layer_opacity(app, layer_id, opacity_value):
    layer = get_layer_by_id(app, layer_id)
    if layer:
        layer['opacity'] = float(opacity_value)
        stipple_pattern = ""
        opacity = float(opacity_value)
        if 0.75 <= opacity < 1.0: stipple_pattern = "gray75"
        elif 0.5 <= opacity < 0.75: stipple_pattern = "gray50"
        elif 0.25 <= opacity < 0.5: stipple_pattern = "gray25"
        elif 0 < opacity < 0.25: stipple_pattern = "gray12"
        for item_id in app.canvas.find_withtag(layer_id):
            try:
                app.canvas.itemconfig(item_id, stipple=stipple_pattern)
            except Exception:
                pass


def update_layer_list_ui(app):
    for widget_dict in list(app.layer_ui_widgets.values()):
        try:
            widget_dict['frame'].destroy()
        except Exception:
            pass
    app.layer_ui_widgets.clear()
    for layer in reversed(app.layers):
        layer_id = layer['id']
        frame = ctk.CTkFrame(app.layer_list_frame)
        frame.pack(fill="x", pady=2, padx=2)
        frame.grid_columnconfigure(1, weight=1)
        is_active = (layer_id == app.active_layer_id)
        fg_color = app.active_fg_color if is_active else "transparent"
        hover_color = app.active_hover_color if is_active else ("gray70", "gray30")
        vis_icon = "👁️" if layer['visible'] else "🙈"
        vis_button = ctk.CTkButton(frame, text=vis_icon, width=30, command=lambda l_id=layer_id: toggle_layer_visibility(app, l_id))
        vis_button.grid(row=0, column=0, padx=5, pady=2)
        name_button = ctk.CTkButton(frame, text=layer['name'], fg_color=fg_color, hover_color=hover_color,
                                   command=lambda l_id=layer_id: select_layer(app, l_id),
                                   anchor="w")
        name_button.grid(row=0, column=1, sticky="ew", pady=2, columnspan=2)
        name_button.bind("<Double-Button-1>", lambda event, l_id=layer_id: rename_layer(app, l_id))
        opacity_label = ctk.CTkLabel(frame, text="不透明度", font=("Microsoft YaHei", 10))
        opacity_label.grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")
        opacity_slider = ctk.CTkSlider(frame, from_=0.0, to=1.0, 
                                       command=lambda value, l_id=layer_id: set_layer_opacity(app, l_id, value))
        opacity_slider.set(layer.get('opacity', 1.0))
        opacity_slider.grid(row=1, column=1, columnspan=2, padx=(20, 5), pady=(0, 5), sticky="ew")
        app.layer_ui_widgets[layer_id] = {'frame': frame, 'vis_button': vis_button, 'name_button': name_button, 'opacity_slider': opacity_slider}


def rename_layer(app, layer_id):
    layer = get_layer_by_id(app, layer_id)
    if not layer: return
    new_name = simpledialog.askstring("重命名图层", "输入新的图层名称:", initialvalue=layer['name'])
    if new_name:
        layer['name'] = new_name
        update_layer_list_ui(app)


def update_layer_stacking(app):
    try:
        app.canvas.tag_lower("grid_line")
    except Exception:
        pass
    for layer in app.layers:
        try:
            app.canvas.tag_raise(layer['id'])
        except Exception:
            pass


def get_layer_by_id(app, layer_id):
    return next((l for l in app.layers if l['id'] == layer_id), None)
