import customtkinter as ctk
from tkinter import colorchooser, filedialog, Canvas, BOTH, YES, simpledialog, messagebox, Menu, font
import math
import time
import copy
import json
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from tooltip import Tooltip  # 假设tooltip.py在当前目录
from tools import TextToolDialog
from utils import rotate_point

class DrawingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 基本窗口设置 ---
        self.title("My Paintbrush")
        self.geometry("1450x900")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- 状态变量 ---
        self.current_fill_color = ""
        self.grid_visible = False
        self.grid_spacing = 25

        # --- 文件菜单 ---
        self.setup_menu()

        # --- 原有初始化代码 ---
        self.current_tool = "pencil"
        self.current_color = "#FFFFFF"
        self.brush_size = 5
        self.start_x = None
        self.start_y = None
        self.temp_shape = None
        self.polygon_points = []
        self.preview_line = None
        self.CLOSING_TOLERANCE = 15
        self.current_polygon_tag = None
        self.selection_group = set()
        self.last_x = 0
        self.last_y = 0
        self.current_stroke_tag = None
        self.resize_handles = []
        self.drag_handle_type = None
        self.original_bbox = None
        self.drag_mode = None
        self.object_states = {}
        self.rotation_handle_id = None
        self.drag_start_angle = 0
        self.shape_center = (0, 0)
        self.initial_object_angle = 0
        self.erased_in_drag = False
        self.original_group_states = {}
        self.clipboard = None
        self.eraser_mode = "局部"
        self.history_stack = []
        self.history_limit = 50
        self.layers = []
        self.active_layer_id = None
        self.layer_counter = 0
        self.layer_ui_widgets = {}
        
        # --- 窗口布局 ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- 左侧工具栏 ---
        self.toolbar = ctk.CTkFrame(self, width=150, corner_radius=0)
        self.toolbar.grid(row=0, column=0, sticky="ns")
        self.toolbar.grid_propagate(False)
        ui_font = ("Microsoft YaHei", 15)
        button_kwargs = { "font": ui_font, "anchor": "w", "fg_color": "transparent", "hover_color": ("gray70", "gray30"), "height": 40, "corner_radius": 8 }
        self.select_button = ctk.CTkButton(self.toolbar, text="🖐️ 选择", command=lambda: self.select_tool("select"), **button_kwargs)
        self.select_button.pack(pady=(20, 5), padx=10, fill="x")
        self.pencil_button = ctk.CTkButton(self.toolbar, text="✏️ 画笔", command=lambda: self.select_tool("pencil"),** button_kwargs)
        self.pencil_button.pack(pady=5, padx=10, fill="x")
        self.eraser_button = ctk.CTkButton(self.toolbar, text="🧽 橡皮擦", command=lambda: self.select_tool("eraser"), **button_kwargs)
        self.eraser_button.pack(pady=5, padx=10, fill="x")
        self.fill_button = ctk.CTkButton(self.toolbar, text="🎨 油漆桶", command=lambda: self.select_tool("fill"),** button_kwargs)
        self.fill_button.pack(pady=5, padx=10, fill="x")
        ctk.CTkFrame(self.toolbar, height=2, fg_color="gray40").pack(pady=10, padx=15, fill="x")
        self.line_button = ctk.CTkButton(self.toolbar, text="📏 直线", command=lambda: self.select_tool("line"), **button_kwargs)
        self.line_button.pack(pady=5, padx=10, fill="x")
        self.rect_button = ctk.CTkButton(self.toolbar, text="⬜ 矩形", command=lambda: self.select_tool("rectangle"),** button_kwargs)
        self.rect_button.pack(pady=5, padx=10, fill="x")
        self.circle_button = ctk.CTkButton(self.toolbar, text="⚪ 圆形", command=lambda: self.select_tool("circle"), **button_kwargs)
        self.circle_button.pack(pady=5, padx=10, fill="x")
        self.polygon_button = ctk.CTkButton(self.toolbar, text="⬢ 多边形", command=lambda: self.select_tool("polygon"),** button_kwargs)
        self.polygon_button.pack(pady=5, padx=10, fill="x")
        self.text_button = ctk.CTkButton(self.toolbar, text="T  文本", command=lambda: self.select_tool("text"), **button_kwargs)
        self.text_button.pack(pady=5, padx=10, fill="x")
        self.tool_buttons = { "select": self.select_button, "pencil": self.pencil_button, "eraser": self.eraser_button, "fill": self.fill_button, "line": self.line_button, "rectangle": self.rect_button, "circle": self.circle_button, "polygon": self.polygon_button, "text": self.text_button }
        self.active_fg_color = ("#3B8ED0", "#1F6AA5")
        self.active_hover_color = ("#36719F", "#144870")
        
        # --- 中间画布 ---
        self.canvas_frame = ctk.CTkFrame(self, corner_radius=0)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_bg_color = "#333333"
        self.canvas = Canvas(self.canvas_frame, bg=self.canvas_bg_color, highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=YES)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonPress-1>", self.start_drawing)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Double-Button-1>", self.handle_double_click)
        
        # --- 右侧面板Tab视图 ---
        self.right_panel_container = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.right_panel_container.grid(row=0, column=2, sticky="ns")
        self.right_panel_container.grid_rowconfigure(0, weight=1)
        self.right_panel_container.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self.right_panel_container)
        self.tab_view.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.options_tab = self.tab_view.add("工具选项")
        self.layers_tab = self.tab_view.add("图层")
        
        # --- 工具选项Tab ---
        self.options_panel = ctk.CTkFrame(self.options_tab, corner_radius=0)
        self.options_panel.pack(fill="both", expand=True)

        ctk.CTkLabel(self.options_panel, text="颜色", font=ui_font).pack(pady=(20, 0))
        self.color_frame = ctk.CTkFrame(self.options_panel, fg_color="transparent")
        self.color_frame.pack(pady=5, padx=10)
        self.stroke_color_button = ctk.CTkButton(self.color_frame, text="边框", command=self.choose_stroke_color, font=ui_font, width=90)
        self.stroke_color_button.grid(row=0, column=0, padx=5)
        self.stroke_color_preview = ctk.CTkFrame(self.color_frame, width=30, height=30, fg_color=self.current_color, corner_radius=5)
        self.stroke_color_preview.grid(row=0, column=1)
        self.fill_color_button = ctk.CTkButton(self.color_frame, text="填充", command=self.choose_fill_color, font=ui_font, width=90)
        self.fill_color_button.grid(row=1, column=0, padx=5, pady=5)
        self.fill_color_preview = ctk.CTkFrame(self.color_frame, width=30, height=30, fg_color=self.current_fill_color or self.canvas_bg_color, corner_radius=5, border_width=1, border_color="gray50")
        self.fill_color_preview.grid(row=1, column=1)

        ctk.CTkLabel(self.options_panel, text="画笔/边框大小", font=ui_font).pack(pady=(20, 0))
        self.brush_size_slider = ctk.CTkSlider(self.options_panel, from_=1, to=100, command=self.set_brush_size)
        self.brush_size_slider.set(self.brush_size)
        self.brush_size_slider.pack(pady=10, padx=20, fill="x")
        self.brush_preview_canvas = Canvas(self.options_panel, width=60, height=60, bg=self.options_panel.cget("fg_color")[1], highlightthickness=0)
        self.brush_preview_canvas.pack(pady=5)
        self.update_brush_preview()

        # 橡皮擦模式
        self.eraser_mode_label = ctk.CTkLabel(self.options_panel, text="橡皮擦模式", font=ui_font)
        self.eraser_mode_switch = ctk.CTkSegmentedButton(self.options_panel, values=["局部", "对象"], command=self.set_eraser_mode, font=ui_font)
        self.eraser_mode_switch.set(self.eraser_mode)
        
        ctk.CTkFrame(self.options_panel, height=2, fg_color="gray40").pack(pady=20, padx=15, fill="x")
        self.undo_button = ctk.CTkButton(self.options_panel, text="撤销 (Ctrl+Z)", command=self.undo_last_action, font=ui_font)
        self.undo_button.pack(pady=10)
        self.clear_button = ctk.CTkButton(self.options_panel, text="清空画布", command=self.clear_canvas, font=ui_font, fg_color="#C0392B", hover_color="#E74C3C")
        self.clear_button.pack(pady=10)
        self.save_button = ctk.CTkButton(self.options_panel, text="导出为图片", command=self.export_as_image, font=ui_font)
        self.save_button.pack(pady=10)

        # --- 图层Tab ---
        self.layer_panel = ctk.CTkFrame(self.layers_tab, corner_radius=0, fg_color="transparent")
        self.layer_panel.pack(fill="both", expand=True)
        self.layer_panel.grid_columnconfigure(0, weight=1)
        self.layer_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.layer_panel, text="图层", font=(ui_font[0], 18, "bold")).grid(row=0, column=0, pady=10, sticky="w", padx=10)
        self.layer_list_frame = ctk.CTkScrollableFrame(self.layer_panel, label_text="")
        self.layer_list_frame.grid(row=1, column=0, sticky="nsew", padx=5)
        
        layer_controls_frame = ctk.CTkFrame(self.layer_panel)
        layer_controls_frame.grid(row=2, column=0, sticky="ew", pady=5, padx=5)
        layer_controls_frame.grid_columnconfigure((0,1,2,3,4), weight=1)
        btn_font = (ui_font[0], 18)
        self.add_layer_btn = ctk.CTkButton(layer_controls_frame, text="➕", command=self.add_new_layer, font=btn_font, width=40)
        self.add_layer_btn.grid(row=0, column=0, padx=2, pady=5)
        self.dup_layer_btn = ctk.CTkButton(layer_controls_frame, text="📋", command=self.duplicate_selected_layer, font=btn_font, width=40)
        self.dup_layer_btn.grid(row=0, column=1, padx=2, pady=5)
        self.del_layer_btn = ctk.CTkButton(layer_controls_frame, text="🗑️", command=self.delete_selected_layer, font=btn_font, width=40)
        self.del_layer_btn.grid(row=0, column=2, padx=2, pady=5)
        self.move_up_btn = ctk.CTkButton(layer_controls_frame, text="▲", command=self.move_layer_up, font=btn_font, width=40)
        self.move_up_btn.grid(row=0, column=3, padx=2, pady=5)
        self.move_down_btn = ctk.CTkButton(layer_controls_frame, text="▼", command=self.move_layer_down, font=btn_font, width=40)
        self.move_down_btn.grid(row=0, column=4, padx=2, pady=5)
        Tooltip(self.add_layer_btn, "新建图层", delay=3000)
        Tooltip(self.dup_layer_btn, "复制图层", delay=3000)
        Tooltip(self.del_layer_btn, "删除图层", delay=3000)
        Tooltip(self.move_up_btn, "上移图层", delay=3000)
        Tooltip(self.move_down_btn, "下移图层", delay=3000)

        # --- 初始化与绑定 ---
        self.bind("<Control-z>", lambda event: self.undo_last_action())
        self.bind("<Control-c>", self.copy_selection)
        self.bind("<Control-v>", self.paste_selection)
        self.bind("<Control-s>", lambda event: self.save_project())
        self.bind("<Control-o>", lambda event: self.open_project())
        self.add_new_layer(name="背景")
        self.select_tool("pencil")
        self._capture_and_save_state()

    # --- 所有原方法保持不变（仅修改旋转函数调用） ---
    def setup_menu(self):
        menubar = Menu(self)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="打开项目", command=self.open_project, accelerator="Ctrl+O")
        filemenu.add_command(label="保存项目", command=self.save_project, accelerator="Ctrl+S")
        filemenu.add_separator()
        filemenu.add_command(label="导出为图片...", command=self.export_as_image)
        filemenu.add_separator()
        filemenu.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="文件", menu=filemenu)
        
        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_checkbutton(label="显示网格", onvalue=1, offvalue=0, command=self.toggle_grid)
        menubar.add_cascade(label="视图", menu=viewmenu)

        self.config(menu=menubar)

    def _get_canvas_state(self):
        items_data = []
        for item_id in self.canvas.find_all():
            tags = self.canvas.gettags(item_id)
            if "handle" in tags or "grid_line" in tags: continue

            item_type = self.canvas.type(item_id)
            coords = self.canvas.coords(item_id)
            options = {}
            config_keys = ['tags', 'width', 'fill', 'outline', 'capstyle', 'smooth', 'joinstyle', 'dash', 'text', 'font', 'anchor']
            for key in config_keys:
                try:
                    options[key] = self.canvas.itemcget(item_id, key)
                except:
                    pass
            item_info = {"type": item_type, "coords": coords, "options": options}
            items_data.append(item_info)
        
        state = {
            "bg_color": self.canvas_bg_color,
            "items": items_data,
            "object_states": self.object_states,
            "layers": self.layers,
            "active_layer_id": self.active_layer_id,
            "layer_counter": self.layer_counter,
        }
        return state

    def save_project(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Gemini绘图板项目", "*.json"), ("所有文件", "*.*")],
            title="保存项目文件"
        )
        if not file_path: return
        try:
            canvas_state = self._get_canvas_state()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(canvas_state, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", f"项目已成功保存到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存项目时发生错误: \n{e}")

    def open_project(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Gemini绘图板项目", "*.json"), ("所有文件", "*.*")],
            title="打开项目文件"
        )
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_to_load = json.load(f)
            self._restore_state_from_history(state_to_load)
            self.history_stack.clear()
            self._capture_and_save_state()
        except Exception as e:
            messagebox.showerror("打开失败", f"打开项目时发生错误: \n{e}")

    def export_as_image(self):
        if self.selection_group:
            self._clear_resize_handles()
            self.selection_group.clear()
            self.canvas.update_idletasks()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("BMP 文件", "*.bmp")],
            title="导出为图片"
        )
        if not file_path: return

        try:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            
            final_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

            for layer in self.layers:
                if not layer['visible']: continue

                layer_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(layer_image)

                for item_id in self.canvas.find_withtag(layer['id']):
                    item_type = self.canvas.type(item_id)
                    coords = [float(c) for c in self.canvas.coords(item_id)]
                    
                    try:
                        outline = self.canvas.itemcget(item_id, "outline") or "transparent"
                        fill = self.canvas.itemcget(item_id, "fill") or "transparent"
                        item_width = int(float(self.canvas.itemcget(item_id, "width") or 0))
                    except: continue

                    outline_color = outline if outline != "transparent" and outline else None
                    fill_color = fill if fill != "transparent" and fill else None
                    
                    if item_type == "line":
                        draw.line(coords, fill=outline_color, width=item_width)
                    elif item_type == "rectangle":
                        draw.rectangle(coords, fill=fill_color, outline=outline_color, width=item_width)
                    elif item_type == "oval":
                        draw.ellipse(coords, fill=fill_color, outline=outline_color, width=item_width)
                    elif item_type == "polygon":
                        draw.polygon(coords, fill=fill_color, outline=outline_color, width=item_width)
                    elif item_type == "text":
                        text_content = self.canvas.itemcget(item_id, "text")
                        font_str = self.canvas.itemcget(item_id, "font")
                        try:
                            font_family, font_size, *font_styles = font_str.split()
                            font_size = int(font_size)
                            pil_font = ImageFont.truetype(f"{font_family.lower()}.ttf", font_size)
                        except Exception:
                            pil_font = ImageFont.load_default()
                        
                        draw.text(coords, text_content, font=pil_font, fill=fill_color)

                opacity = layer.get('opacity', 1.0)
                if opacity < 1.0:
                    alpha = layer_image.split()[3]
                    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
                    layer_image.putalpha(alpha)

                final_image = Image.alpha_composite(final_image, layer_image)

            bg_image = Image.new("RGB", (width, height), self.canvas_bg_color)
            bg_image.paste(final_image, (0, 0), final_image)
            
            file_ext = file_path.split('.')[-1].lower()
            if file_ext == 'jpg' or file_ext == 'jpeg':
                bg_image.convert('RGB').save(file_path)
            else:
                bg_image.save(file_path)
            
            messagebox.showinfo("成功", f"图片已成功导出到:\n{file_path}")
        
        except Exception as e:
            messagebox.showerror("导出失败", f"导出图片时发生错误: \n{str(e)}")

    def copy_selection(self, event=None):
        if not self.selection_group or self.current_tool != "select":
            return
        
        self.clipboard = []
        bbox = self._get_selection_bbox()
        if not bbox: return
        
        min_x, min_y = bbox[0], bbox[1]
        clipboard_data = {'origin': (min_x, min_y), 'items': []}

        for unique_tag in self.selection_group:
            item_group_data = {'unique_tag_prefix': unique_tag.split('_')[0], 'parts': []}
            for item_id in self.canvas.find_withtag(unique_tag):
                item_type = self.canvas.type(item_id)
                coords = self.canvas.coords(item_id)
                relative_coords = [(c - min_x) if i % 2 == 0 else (c - min_y) for i, c in enumerate(coords)]
                
                options = {}
                copy_keys = ['width', 'fill', 'outline', 'capstyle', 'smooth', 'joinstyle', 'dash', 'tags', 'text', 'font', 'anchor']
                for key in copy_keys:
                    try: options[key] = self.canvas.itemcget(item_id, key)
                    except: pass
                
                item_group_data['parts'].append({
                    'type': item_type,
                    'relative_coords': relative_coords,
                    'options': options
                })
            clipboard_data['items'].append(item_group_data)
        
        self.clipboard = clipboard_data

    def paste_selection(self, event=None):
        if not self.clipboard or self.current_tool != "select":
            return

        self._clear_resize_handles()
        self.selection_group.clear()

        paste_x, paste_y = self.clipboard['origin']
        offset_x, offset_y = 20, 20

        for item_group_data in self.clipboard['items']:
            new_unique_tag = f"{item_group_data['unique_tag_prefix']}_{time.time()}"
            self.selection_group.add(new_unique_tag)
            
            all_new_part_coords = {}
            for part_data in item_group_data['parts']:
                absolute_coords = [(c + paste_x + offset_x) if i % 2 == 0 else (c + paste_y + offset_y) for i, c in enumerate(part_data['relative_coords'])]
                
                creator_func = getattr(self.canvas, f"create_{part_data['type']}", None)
                if creator_func:
                    options = part_data['options']
                    original_tags = list(options.get('tags', []))
                    new_tags = [t for t in original_tags if not (t.startswith('shape_') or t.startswith('stroke_') or t.startswith('layer_'))]
                    new_tags.extend([new_unique_tag, self.active_layer_id])
                    options['tags'] = new_tags
                    
                    new_item_id = creator_func(absolute_coords, **options)
                    all_new_part_coords[new_item_id] = self.canvas.coords(new_item_id)

            is_stroke = new_unique_tag.startswith("stroke_") or new_unique_tag.startswith("erase_stroke_")
            if is_stroke:
                self.object_states[new_unique_tag] = {'angle': 0, 'original_coords': None, 'original_coords_map': all_new_part_coords}
            else:
                first_item_id = list(all_new_part_coords.keys())[0]
                self.object_states[new_unique_tag] = {'angle': 0, 'original_coords': self.canvas.coords(first_item_id), 'original_coords_map': None}
        
        self._draw_resize_handles()
        self.update_layer_stacking()
        self._capture_and_save_state()

    def add_new_layer(self, name=None, insert_index=None):
        self.layer_counter += 1
        layer_name = name or f"图层 {self.layer_counter}"
        layer_id = f"layer_{time.time()}_{self.layer_counter}"
        new_layer = {'id': layer_id, 'name': layer_name, 'visible': True, 'opacity': 1.0}

        if insert_index is not None:
            self.layers.insert(insert_index, new_layer)
        else:
            self.layers.append(new_layer)

        self.active_layer_id = layer_id
        self.update_layer_list_ui()
        self.update_layer_stacking()
        return new_layer

    def delete_selected_layer(self):
        if len(self.layers) <= 1:
            messagebox.showwarning("警告", "无法删除最后一个图层。")
            return
        
        selected_index = self._get_selected_layer_index()
        if selected_index is not None:
            layer_to_delete = self.layers.pop(selected_index)
            
            tags_to_remove = set()
            for tag in self.selection_group:
                first_item = self.canvas.find_withtag(tag)[0]
                if layer_to_delete['id'] in self.canvas.gettags(first_item):
                    tags_to_remove.add(tag)
            
            if tags_to_remove:
                self.selection_group -= tags_to_remove
                self._clear_resize_handles()

            self.canvas.delete(layer_to_delete['id'])

            if selected_index >= len(self.layers):
                selected_index = len(self.layers) - 1
            self.active_layer_id = self.layers[selected_index]['id']
            
            self.update_layer_list_ui()
            self._capture_and_save_state()

    def duplicate_selected_layer(self):
        selected_index = self._get_selected_layer_index()
        if selected_index is None: return

        source_layer = self.layers[selected_index]
        new_layer_data = self.add_new_layer(
            name=f"{source_layer['name']} 副本",
            insert_index=selected_index + 1
        )
        new_layer_id = new_layer_data['id']
        new_layer = self.get_layer_by_id(new_layer_id)
        new_layer['opacity'] = source_layer['opacity']

        items_to_copy = self.canvas.find_withtag(source_layer['id'])
        
        for item_id in items_to_copy:
            item_type = self.canvas.type(item_id)
            if item_type == "image": continue
            coords = self.canvas.coords(item_id)
            
            cleaned_options = {}
            copy_keys = ['tags', 'width', 'fill', 'outline', 'capstyle', 'smooth', 'joinstyle', 'dash', 'text', 'font', 'anchor']
            for key in copy_keys:
                try:
                    cleaned_options[key] = self.canvas.itemcget(item_id, key)
                except: pass

            original_tags = list(self.canvas.gettags(item_id))
            new_tags = [t for t in original_tags if t != source_layer['id']]
            new_tags.append(new_layer_id)
            
            unique_tag = next((t for t in original_tags if t.startswith(('shape_', 'stroke_', 'erase_stroke_'))), None)
            if unique_tag:
                new_unique_tag = f"{unique_tag.split('_')[0]}_{time.time()}"
                new_tags = [t if t != unique_tag else new_unique_tag for t in new_tags]
                if unique_tag in self.object_states:
                    self.object_states[new_unique_tag] = copy.deepcopy(self.object_states[unique_tag])

            cleaned_options['tags'] = new_tags
            
            creator_func = getattr(self.canvas, f"create_{item_type}", None)
            if creator_func:
                creator_func(coords, **cleaned_options)
        
        self.update_layer_list_ui()
        self.update_layer_stacking()
        self._capture_and_save_state()

    def move_layer_up(self):
        idx = self._get_selected_layer_index()
        if idx is not None and idx < len(self.layers) - 1:
            self.layers[idx], self.layers[idx+1] = self.layers[idx+1], self.layers[idx]
            self.update_layer_list_ui()
            self.update_layer_stacking()
            self._capture_and_save_state()

    def move_layer_down(self):
        idx = self._get_selected_layer_index()
        if idx is not None and idx > 0:
            self.layers[idx], self.layers[idx-1] = self.layers[idx-1], self.layers[idx]
            self.update_layer_list_ui()
            self.update_layer_stacking()
            self._capture_and_save_state()

    def select_layer(self, layer_id):
        if self.active_layer_id != layer_id:
            self.active_layer_id = layer_id
            self.update_layer_list_ui()
            if self.selection_group:
                self._clear_resize_handles()
                self.selection_group.clear()

    def toggle_layer_visibility(self, layer_id):
        layer = self.get_layer_by_id(layer_id)
        if layer:
            layer['visible'] = not layer['visible']
            new_state = "normal" if layer['visible'] else "hidden"
            self.canvas.itemconfig(layer_id, state=new_state)
            self.update_layer_list_ui()

    def set_layer_opacity(self, layer_id, opacity_value):
        layer = self.get_layer_by_id(layer_id)
        if layer:
            layer['opacity'] = float(opacity_value)
            stipple_pattern = ""
            opacity = float(opacity_value)
            if 0.75 <= opacity < 1.0: stipple_pattern = "gray75"
            elif 0.5 <= opacity < 0.75: stipple_pattern = "gray50"
            elif 0.25 <= opacity < 0.5: stipple_pattern = "gray25"
            elif 0 < opacity < 0.25: stipple_pattern = "gray12"
            
            for item_id in self.canvas.find_withtag(layer_id):
                try:
                    self.canvas.itemconfig(item_id, stipple=stipple_pattern)
                except Exception:
                    pass

    def update_layer_list_ui(self):
        for widget_dict in self.layer_ui_widgets.values():
            widget_dict['frame'].destroy()
        self.layer_ui_widgets.clear()
        
        for layer in reversed(self.layers):
            layer_id = layer['id']
            
            frame = ctk.CTkFrame(self.layer_list_frame)
            frame.pack(fill="x", pady=2, padx=2)
            frame.grid_columnconfigure(1, weight=1)

            is_active = (layer_id == self.active_layer_id)
            fg_color = self.active_fg_color if is_active else "transparent"
            hover_color = self.active_hover_color if is_active else ("gray70", "gray30")

            vis_icon = "👁️" if layer['visible'] else "🙈"
            vis_button = ctk.CTkButton(frame, text=vis_icon, width=30, command=lambda l_id=layer_id: self.toggle_layer_visibility(l_id))
            vis_button.grid(row=0, column=0, padx=5, pady=2)
            
            name_button = ctk.CTkButton(frame, text=layer['name'], fg_color=fg_color, hover_color=hover_color,
                                       command=lambda l_id=layer_id: self.select_layer(l_id),
                                       anchor="w")
            name_button.grid(row=0, column=1, sticky="ew", pady=2, columnspan=2)
            name_button.bind("<Double-Button-1>", lambda event, l_id=layer_id: self.rename_layer(l_id))
            
            opacity_label = ctk.CTkLabel(frame, text="不透明度", font=("Microsoft YaHei", 10))
            opacity_label.grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")
            
            opacity_slider = ctk.CTkSlider(frame, from_=0.0, to=1.0, 
                                           command=lambda value, l_id=layer_id: self.set_layer_opacity(l_id, value))
            opacity_slider.set(layer.get('opacity', 1.0))
            opacity_slider.grid(row=1, column=1, columnspan=2, padx=(20, 5), pady=(0, 5), sticky="ew")

            self.layer_ui_widgets[layer_id] = {'frame': frame, 'vis_button': vis_button, 'name_button': name_button, 'opacity_slider': opacity_slider}

    def rename_layer(self, layer_id):
        layer = self.get_layer_by_id(layer_id)
        if not layer: return

        new_name = simpledialog.askstring("重命名图层", "输入新的图层名称:", initialvalue=layer['name'])
        if new_name:
            layer['name'] = new_name
            self.update_layer_list_ui()

    def update_layer_stacking(self):
        self.canvas.tag_lower("grid_line")
        for layer in self.layers:
            self.canvas.tag_raise(layer['id'])

    def get_layer_by_id(self, layer_id):
        return next((l for l in self.layers if l['id'] == layer_id), None)

    def _get_selected_layer_index(self):
        for i, layer in enumerate(self.layers):
            if layer['id'] == self.active_layer_id:
                return i
        return None

    def _capture_and_save_state(self):
        state = self._get_canvas_state()
        if len(self.history_stack) >= self.history_limit:
            self.history_stack.pop(0)
        state['object_states'] = copy.deepcopy(state['object_states'])
        self.history_stack.append(state)

    def _restore_state_from_history(self, state):
        self._clear_resize_handles()
        self.selection_group.clear()
        self.canvas.delete("all")
        self.draw_grid()
        self.canvas.config(bg=state["bg_color"])
        self.canvas_bg_color = state["bg_color"]

        self.layers = copy.deepcopy(state["layers"])
        self.active_layer_id = state["active_layer_id"]
        self.layer_counter = state.get("layer_counter", self.layer_counter)
        self.object_states = copy.deepcopy(state["object_states"])
        
        for item_info in state["items"]:
            if not item_info["coords"]: continue
            creator_func = getattr(self.canvas, f"create_{item_info['type']}", None)
            if creator_func:
                new_item = creator_func(item_info["coords"], **item_info["options"])
                for tag in self.canvas.gettags(new_item):
                    if tag.startswith("layer_"):
                        layer = self.get_layer_by_id(tag)
                        if layer and not layer['visible']:
                            self.canvas.itemconfig(new_item, state='hidden')
                        break
        
        self.update_layer_list_ui()
        self.update_layer_stacking()
        self._rebuild_stroke_maps_after_restore()

    def undo_last_action(self):
        if len(self.history_stack) > 1:
            self.history_stack.pop()
            self._restore_state_from_history(self.history_stack[-1])

    def select_tool(self, tool):
        if self.current_tool == "polygon" and self.polygon_points: self.finalize_polygon()
        if self.selection_group: self._clear_resize_handles(); self.selection_group.clear(); self.original_group_states.clear()
        self.current_tool = tool
        for t, b in self.tool_buttons.items(): b.configure(fg_color=self.active_fg_color if t == tool else "transparent", hover_color=self.active_hover_color if t == tool else ("gray70", "gray30"))
        
        if tool == "eraser":
            self.eraser_mode_label.pack(pady=(10, 0))
            self.eraser_mode_switch.pack(pady=5, padx=20, fill="x")
        else:
            self.eraser_mode_label.pack_forget()
            self.eraser_mode_switch.pack_forget()
            
        if tool == "polygon": self.reset_polygon_drawing(); self.current_polygon_tag = f"poly_in_progress_{time.time()}"
        self.brush_size_slider.configure(state="disabled" if tool in ["fill", "select", "text"] else "normal")
        self.canvas.config(cursor="arrow" if tool == "select" else "dotbox" if tool == "eraser" else "xterm" if tool == "text" else "crosshair")

    def start_drawing(self, event):
        if self.current_tool == "select":
            item_tuple = self.canvas.find_withtag("current")
            item_id = item_tuple[0] if item_tuple else None

            if item_id and "handle" in self.canvas.gettags(item_id) and self.selection_group:
                self.original_bbox = self._get_selection_bbox() 

                if "rotate" in self.canvas.gettags(item_id):
                    self.drag_mode = "rotate"
                    self.shape_center = ((self.original_bbox[0] + self.original_bbox[2]) / 2, (self.original_bbox[1] + self.original_bbox[3]) / 2)
                    self.drag_start_angle = math.atan2(event.y - self.shape_center[1], event.x - self.shape_center[0])
                    self.initial_object_angle = 0
                else:
                    self.drag_mode = "resize"
                    self.drag_handle_type = next(t for t in self.canvas.gettags(item_id) if t not in ["handle", "rotate"])

                self.original_group_states.clear()
                for tag in self.selection_group:
                    if self.drag_mode == 'rotate':
                        first_item_id = self.canvas.find_withtag(tag)[0]
                        if self.canvas.type(first_item_id) in ["rectangle", "oval"]:
                            self._convert_to_polygon(tag)

                    is_stroke = tag.startswith("stroke_")
                    if is_stroke:
                        self.original_group_states[tag] = self.object_states[tag]['original_coords_map'].copy()
                    else:
                        self.original_group_states[tag] = self.object_states[tag]['original_coords'][:]
                return

            clicked_tag = None
            if item_id:
                item_tags = self.canvas.gettags(item_id)
                if self.active_layer_id not in item_tags and "grid_line" not in item_tags: 
                    layer_tag = next((t for t in item_tags if t.startswith("layer_")), None)
                    if layer_tag: self.select_layer(layer_tag)
                
                if self.active_layer_id in item_tags:
                    clicked_tag = next((t for t in item_tags if t.startswith("stroke_") or t.startswith("shape_")), None)
            
            shift_pressed = (event.state & 1)
            
            if not shift_pressed:
                if clicked_tag not in self.selection_group:
                    self._clear_resize_handles()
                    self.selection_group.clear()
                    if clicked_tag:
                        self.selection_group.add(clicked_tag)
            else:
                if clicked_tag:
                    if clicked_tag in self.selection_group: self.selection_group.remove(clicked_tag)
                    else: self.selection_group.add(clicked_tag)
            
            self._draw_resize_handles()

            if clicked_tag and clicked_tag in self.selection_group:
                self.drag_mode = "move"
                self.last_x, self.last_y = event.x, event.y
            else:
                self.drag_mode = None
        
        elif self.current_tool == "text":
            self.create_text_object(event.x, event.y)
        elif self.current_tool == "polygon": self.handle_polygon_click(event)
        elif self.current_tool == "fill": self.fill_shape(event)
        elif self.current_tool == "eraser":
             self.erased_in_drag = False
             self.current_stroke_tag = f"erase_stroke_{time.time()}"
             self.draw(event)
        else:
            self.start_x, self.start_y = event.x, event.y
            if self.current_tool == "pencil":
                self.current_stroke_tag = f"stroke_{time.time()}"

    def stop_drawing(self, event):
        action_completed = False
        if self.current_tool == "select" and self.drag_mode:
            action_completed = True
            if self.drag_mode in ["rotate", "resize"]:
                for tag in self.selection_group:
                    is_stroke = tag.startswith("stroke_")
                    if tag in self.object_states:
                        self.object_states[tag]['angle'] = 0 
                        if is_stroke:
                            self.object_states[tag]['original_coords_map'] = {item_id: self.canvas.coords(item_id) for item_id in self.canvas.find_withtag(tag)}
                        else:
                            item_id = self.canvas.find_withtag(tag)[0]
                            self.object_states[tag]['original_coords'] = self.canvas.coords(item_id)
            self.drag_mode = None
            self.original_group_states.clear()
        elif self.current_tool in ["line", "rectangle", "circle"] and self.start_x is not None:
            action_completed = True
            if self.temp_shape: self.canvas.delete(self.temp_shape); self.temp_shape = None
            if (self.start_x != event.x or self.start_y != event.y):
                unique_tag = f"shape_{time.time()}"
                tags = (unique_tag, self.active_layer_id)
                item_id = None
                if self.current_tool == "line": item_id = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill=self.current_color, width=self.brush_size, capstyle="round", tags=tags)
                elif self.current_tool == "rectangle": item_id = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline=self.current_color, width=self.brush_size, fill=self.current_fill_color, tags=tags)
                elif self.current_tool == "circle": item_id = self.canvas.create_oval(self.start_x, self.start_y, event.x, event.y, outline=self.current_color, width=self.brush_size, fill=self.current_fill_color, tags=tags)
                if item_id: self.object_states[unique_tag] = {'angle': 0, 'original_coords': self.canvas.coords(item_id), 'original_coords_map': None}
            self.start_x, self.start_y = None, None
        elif self.current_tool == "pencil" and self.current_stroke_tag:
            action_completed = True
            stroke_ids = self.canvas.find_withtag(self.current_stroke_tag)
            if stroke_ids: self.object_states[self.current_stroke_tag] = {'angle': 0, 'original_coords': None, 'original_coords_map': {item_id: self.canvas.coords(item_id) for item_id in stroke_ids}}
            self.current_stroke_tag = None
        elif self.current_tool == "eraser" and self.erased_in_drag:
            action_completed = True
            self.erased_in_drag = False; self.current_stroke_tag = None
            
        if action_completed:
            self.update_layer_stacking()
            self._capture_and_save_state()

    def draw(self, event):
        if self.current_tool == "select" and self.selection_group and self.drag_mode:
            if self.drag_mode == "move":
                dx, dy = event.x - self.last_x, event.y - self.last_y
                for tag in self.selection_group:
                    self.canvas.move(tag, dx, dy)
                self.canvas.move("handle", dx, dy) 
                self.last_x, self.last_y = event.x, event.y
            
            elif self.drag_mode == "resize" and self.original_bbox:
                is_text_object = False
                if len(self.selection_group) == 1:
                    tag = list(self.selection_group)[0]
                    item_id = self.canvas.find_withtag(tag)[0]
                    if self.canvas.type(item_id) == 'text':
                        is_text_object = True

                if is_text_object:
                    dx, dy = event.x - self.last_x, event.y - self.last_y
                    self.canvas.move(tag, dx, dy)
                    self.canvas.move("handle", dx, dy)
                    self.last_x, self.last_y = event.x, event.y
                else:
                    x1, y1, x2, y2 = self.original_bbox
                    origin_x, origin_y = (x1 + x2) / 2, (y1 + y2) / 2
                    if "left" in self.drag_handle_type: origin_x = x2
                    elif "right" in self.drag_handle_type: origin_x = x1
                    if "top" in self.drag_handle_type: origin_y = y2
                    elif "bottom" in self.drag_handle_type: origin_y = y1
                    
                    old_w, old_h = (x2 - x1) or 1, (y2 - y1) or 1
                    new_w, new_h = old_w, old_h
                    if "left" in self.drag_handle_type: new_w = origin_x - event.x
                    elif "right" in self.drag_handle_type: new_w = event.x - origin_x
                    if "top" in self.drag_handle_type: new_h = origin_y - event.y
                    elif "bottom" in self.drag_handle_type: new_h = event.y - origin_y
                    
                    scale_x = new_w / old_w if old_w != 0 else 1.0
                    scale_y = new_h / old_h if old_h != 0 else 1.0
                    if "center" in self.drag_handle_type: scale_x = 1.0
                    if "middle" in self.drag_handle_type: scale_y = 1.0

                    for tag in self.selection_group:
                        is_stroke = tag.startswith("stroke_")
                        original_state = self.original_group_states[tag]
                        if is_stroke:
                            for part_id, coords in original_state.items(): self.canvas.coords(part_id, *coords)
                        else:
                            self.canvas.coords(tag, *original_state)
                        self.canvas.scale(tag, origin_x, origin_y, scale_x, scale_y)
                    
                    self._draw_resize_handles()
            
            elif self.drag_mode == "rotate":
                current_angle = math.atan2(event.y - self.shape_center[1], event.x - self.shape_center[0])
                total_angle = self.initial_object_angle + (current_angle - self.drag_start_angle)
                
                for tag in self.selection_group:
                    item_id = self.canvas.find_withtag(tag)[0]
                    if self.canvas.type(item_id) == 'text':
                        self.canvas.itemconfig(item_id, angle=-math.degrees(total_angle))
                        continue
                    
                    is_stroke = tag.startswith("stroke_")
                    original_state = self.original_group_states[tag]

                    if is_stroke:
                        for item_id, original_segment_coords in original_state.items():
                            p1_x, p1_y, p2_x, p2_y = original_segment_coords
                            # 调用utils.py中的rotate_point函数
                            new_p1_x, new_p1_y = rotate_point(p1_x, p1_y, total_angle, self.shape_center[0], self.shape_center[1])
                            new_p2_x, new_p2_y = rotate_point(p2_x, p2_y, total_angle, self.shape_center[0], self.shape_center[1])
                            self.canvas.coords(item_id, new_p1_x, new_p1_y, new_p2_x, new_p2_y)
                    else:
                        new_coords = []
                        for i in range(0, len(original_state), 2):
                            px, py = original_state[i], original_state[i+1]
                            new_px, new_py = rotate_point(px, py, total_angle, self.shape_center[0], self.shape_center[1])
                            new_coords.extend([new_px, new_py])
                        self.canvas.coords(tag, *new_coords)
                
                self._draw_resize_handles()
        
        elif self.current_tool == "eraser":
            self.erased_in_drag = True
            if self.eraser_mode == "对象":
                items_under_cursor = self.canvas.find_overlapping(event.x - self.brush_size/2, event.y - self.brush_size/2, event.x + self.brush_size/2, event.y + self.brush_size/2)
                objects_to_delete = set()
                for item in items_under_cursor:
                    tags = self.canvas.gettags(item)
                    if self.active_layer_id not in tags or "handle" in tags: continue
                    parent_tag = next((t for t in tags if t.startswith("stroke_") or t.startswith("shape_") or t.startswith("erase_stroke_")), None)
                    if parent_tag: objects_to_delete.add(parent_tag)
                if objects_to_delete:
                    for tag in objects_to_delete:
                        self.canvas.delete(tag)
                        if tag in self.object_states: del self.object_states[tag]
                        if tag in self.selection_group: self.selection_group.remove(tag); self._draw_resize_handles()
            else: 
                r = self.brush_size / 2
                self.canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r,
                                        fill=self.canvas_bg_color, outline=self.canvas_bg_color,
                                        tags=("eraser_mark", self.current_stroke_tag, self.active_layer_id))
        elif self.current_tool not in ["polygon", "fill", "select", "text"]:
            if self.start_x is not None:
                if self.current_tool == "pencil":
                    tags = (self.current_stroke_tag, self.active_layer_id)
                    self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill=self.current_color, width=self.brush_size, capstyle="round", smooth=True, tags=tags)
                    self.start_x, self.start_y = event.x, event.y
                else:
                    if self.temp_shape: self.canvas.delete(self.temp_shape)
                    if self.current_tool == "line": self.temp_shape = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill=self.current_color, width=self.brush_size, capstyle="round")
                    elif self.current_tool == "rectangle": self.temp_shape = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline=self.current_color, width=self.brush_size, fill=self.current_fill_color)
                    elif self.current_tool == "circle": self.temp_shape = self.canvas.create_oval(self.start_x, self.start_y, event.x, event.y, outline=self.current_color, width=self.brush_size, fill=self.current_fill_color)

    def clear_canvas(self):
        if self.canvas.find_all(): self._capture_and_save_state()
        self.canvas.delete("all")
        self.draw_grid()
        self.canvas.config(bg="#333333")
        self.canvas_bg_color = "#333333"
        self.reset_polygon_drawing(); self.selection_group.clear(); self.start_x = None; self.start_y = None; self.temp_shape = None; self.current_stroke_tag = None
        self.object_states.clear()
        
        for widget_dict in self.layer_ui_widgets.values():
            if widget_dict.get('frame'):
                widget_dict['frame'].destroy()

        self.layers.clear()
        self.layer_ui_widgets.clear() 
        self.layer_counter = 0
        self.add_new_layer(name="背景")

        self._capture_and_save_state()

    def set_eraser_mode(self, mode): self.eraser_mode = mode

    def _rebuild_stroke_maps_after_restore(self):
        for tag, state_data in self.object_states.items():
            if tag.startswith("stroke_") and state_data.get('original_coords_map') is not None:
                new_coords_map = {segment_id: self.canvas.coords(segment_id) for segment_id in self.canvas.find_withtag(tag)}
                self.object_states[tag]['original_coords_map'] = new_coords_map

    def update_brush_preview(self):
        self.brush_preview_canvas.delete("all"); self.brush_preview_canvas.update_idletasks()
        center = self.brush_preview_canvas.winfo_width() / 2
        radius = min(self.brush_size / 2, center - 2)
        self.brush_preview_canvas.create_oval(center - radius, center - radius, center + radius, center + radius, fill=self.current_color, outline=self.current_color)

    def choose_stroke_color(self):
        color_code = colorchooser.askcolor(title="选择边框颜色")
        if color_code and color_code[1]: 
            self.current_color = color_code[1]
            self.stroke_color_preview.configure(fg_color=self.current_color)
            self.update_brush_preview()

    def choose_fill_color(self):
        color_code = colorchooser.askcolor(title="选择填充颜色")
        if color_code and color_code[1]: 
            self.current_fill_color = color_code[1]
            self.fill_color_preview.configure(fg_color=self.current_fill_color)
        else:
            self.current_fill_color = ""
            self.fill_color_preview.configure(fg_color=self.canvas_bg_color)
    
    def set_brush_size(self, value): self.brush_size = int(value); self.update_brush_preview()
    def reset_polygon_drawing(self):
        if self.preview_line: self.canvas.delete(self.preview_line); self.preview_line = None
        if self.current_polygon_tag: self.canvas.delete(self.current_polygon_tag)
        self.polygon_points = []; self.current_polygon_tag = None
    def handle_double_click(self, event):
        if self.current_tool == "polygon" and self.polygon_points: self.finalize_polygon()
    def handle_polygon_click(self, event):
        x, y = event.x, event.y
        if self.polygon_points:
            start_x, start_y = self.polygon_points[0]
            if math.sqrt((x - start_x)**2 + (y - start_y)** 2) < self.CLOSING_TOLERANCE: self.finalize_polygon(); return
        self.polygon_points.append((x, y))
        if len(self.polygon_points) > 1: self.canvas.create_line(self.polygon_points[-2], self.polygon_points[-1], fill=self.current_color, width=self.brush_size, capstyle="round", tags=(self.current_polygon_tag,))
    def on_mouse_move(self, event):
        if self.current_tool == "polygon" and self.polygon_points:
            if self.preview_line: self.canvas.delete(self.preview_line)
            self.preview_line = self.canvas.create_line(self.polygon_points[-1], (event.x, event.y), fill=self.current_color, width=self.brush_size, dash=(4, 4))

    def fill_shape(self, event):
        if self.selection_group: self._clear_resize_handles(); self.selection_group.clear()
        ids = self.canvas.find_closest(event.x, event.y)
        if not ids:
            if self.canvas_bg_color != self.current_fill_color and self.current_fill_color:
                self.canvas_bg_color = self.current_fill_color
                self.canvas.config(bg=self.canvas_bg_color)
                self._capture_and_save_state()
            return
        item_id = ids[0]
        if "handle" in self.canvas.gettags(item_id) or "eraser_mark" in self.canvas.gettags(item_id): return

        item_tags = self.canvas.gettags(item_id)
        if self.active_layer_id not in item_tags: return

        try:
            if self.canvas.itemcget(item_id, "fill").lower() != self.current_fill_color.lower(): 
                self.canvas.itemconfig(item_id, fill=self.current_fill_color)
                self._capture_and_save_state()
        except Exception: pass

    def _convert_to_polygon(self, unique_tag):
        item_ids = self.canvas.find_withtag(unique_tag)
        if not item_ids: return
        item_id = item_ids[0]
        
        item_type = self.canvas.type(item_id)
        if item_type == "text": return
        
        coords, tags = self.canvas.coords(item_id), self.canvas.gettags(item_id)
        new_coords = []
        if item_type == "rectangle": x1, y1, x2, y2 = coords; new_coords = [x1, y1, x2, y1, x2, y2, x1, y2]
        elif item_type == "oval":
            x1, y1, x2, y2 = coords; rx, ry, cx, cy = (x2 - x1) / 2, (y2 - y1) / 2, x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2
            for i in range(60): angle = (i / 60) * 2 * math.pi; new_coords.extend([cx + rx * math.cos(angle), cy + ry * math.sin(angle)])
        
        if new_coords:
            options = {'outline': self.canvas.itemcget(item_id, 'outline'), 'width': self.canvas.itemcget(item_id, 'width'), 'fill': self.canvas.itemcget(item_id, 'fill'), 'tags': tags}
            self.canvas.delete(item_id)
            self.canvas.create_polygon(new_coords, **options)
            if unique_tag in self.object_states: self.object_states[unique_tag]['original_coords'] = new_coords

    def _clear_resize_handles(self): self.canvas.delete("handle"); self.resize_handles.clear(); self.rotation_handle_id = None
    def _get_selection_bbox(self):
        if not self.selection_group: return None
        min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
        has_bbox = False
        for tag in self.selection_group:
            bbox = self.canvas.bbox(tag)
            if bbox:
                has_bbox = True
                min_x = min(min_x, bbox[0])
                min_y = min(min_y, bbox[1])
                max_x = max(max_x, bbox[2])
                max_y = max(max_y, bbox[3])
        return (min_x, min_y, max_x, max_y) if has_bbox else None
    def _draw_resize_handles(self):
        self._clear_resize_handles()
        bbox = self._get_selection_bbox()
        if not bbox: return
        x1, y1, x2, y2 = bbox; s = 5

        handle_positions = {"top-left": (x1, y1), "top-center": ((x1+x2)/2, y1), "top-right": (x2, y1), "middle-left": (x1, (y1+y2)/2), "middle-right": (x2, (y1+y2)/2), "bottom-left": (x1, y2), "bottom-center": ((x1+x2)/2, y2), "bottom-right": (x2, y2)}
        for name, (x, y) in handle_positions.items(): self.resize_handles.append(self.canvas.create_rectangle(x-s, y-s, x+s, y+s, fill="white", outline="blue", tags=("handle", name)))
        top_center_x, top_y = handle_positions["top-center"]
        handle_line_end_y = top_y - 25; self.canvas.create_line(top_center_x, top_y, top_center_x, handle_line_end_y, fill="white", tags="handle"); s_rot = 7
        self.rotation_handle_id = self.canvas.create_oval(top_center_x - s_rot, handle_line_end_y - s_rot, top_center_x + s_rot, handle_line_end_y + s_rot, fill="cyan", outline="blue", tags=("handle", "rotate"))
        self.resize_handles.append(self.rotation_handle_id)

    def finalize_polygon(self):
        if len(self.polygon_points) < 3:
            messagebox.showwarning("警告", "多边形至少需要3个点")
            self.reset_polygon_drawing()
            return
        unique_tag = f"shape_{time.time()}"
        tags = (unique_tag, self.active_layer_id)
        coords = [coord for point in self.polygon_points for coord in point]
        self.canvas.create_polygon(coords, outline=self.current_color, width=self.brush_size, fill=self.current_fill_color, tags=tags)
        self.object_states[unique_tag] = {'angle': 0, 'original_coords': coords, 'original_coords_map': None}
        self.reset_polygon_drawing()
        self._capture_and_save_state()

    def create_text_object(self, x, y):
        dialog = TextToolDialog(self, title="输入文本")
        if dialog.result:
            text, font_family, font_size = dialog.result
            unique_tag = f"shape_{time.time()}"
            tags = (unique_tag, self.active_layer_id, "text_object")
            
            item_id = self.canvas.create_text(
                x, y,
                text=text,
                font=(font_family, font_size),
                fill=self.current_fill_color or self.current_color,
                tags=tags,
                anchor="nw"
            )
            self.object_states[unique_tag] = {'angle': 0, 'original_coords': self.canvas.coords(item_id), 'original_coords_map': None}
            self.update_layer_stacking()
            self._capture_and_save_state()

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.draw_grid()

    def draw_grid(self):
        self.canvas.delete("grid_line")
        if self.grid_visible:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            for i in range(0, width, self.grid_spacing):
                self.canvas.create_line(i, 0, i, height, fill="#555555", tags="grid_line", dash=(2, 4))
            for i in range(0, height, self.grid_spacing):
                self.canvas.create_line(0, i, width, i, fill="#555555", tags="grid_line", dash=(2, 4))
            self.canvas.tag_lower("grid_line")