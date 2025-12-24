import customtkinter as ctk
from tkinter import colorchooser, filedialog, Canvas, BOTH, YES, simpledialog, messagebox, Menu, font
import math
import time
import copy
import json
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageTk
from tooltip import Tooltip
from tools import TextToolDialog
from utils import rotate_point
from raster import SimpleRasterization
from pixel_buffer import PixelBuffer
from ui_setup import setup_ui


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
        self.drawing_mode = "library"
        self.use_rasterization = False
        self.rasterization_algorithm = "Bresenham"

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
        self._image_references = {}
        
        # --- 曲线和曲面工具状态 ---
        self.curve_tool = None  # 当前曲线工具实例
        self.surface_tool = None  # 当前曲面工具实例
        self.curve_control_points = []  # 曲线控制点
        self.curve_editing_tag = None  # 正在编辑的曲线标签
        self.surface_display_mode = 'wireframe'  # 曲面显示模式：wireframe 或 filled
        self.dragging_control_point = None  # 正在拖动的控制点
        
        # --- 画布拖动状态 ---
        self.space_pressed = False
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.pan_start_x = None
        self.pan_start_y = None
        
        # --- 画布缩放状态 ---
        self.zoom_level = 1.0  # 1.0 = 100%
        self.zoom_min = 0.1
        self.zoom_max = 5.0
        
        # 定义默认画布逻辑尺寸 (2000x1500)
        self.logical_canvas_size = (2000, 1500)
        
        # UI 已从此文件抽取到 ui_setup.setup_ui
        setup_ui(self)
        
        # 保存初始背景颜色（用于清空画布时恢复）
        self._initial_canvas_bg_color = self.canvas_bg_color
        
        # 初始化绘图模式UI状态（根据初始模式设置亮度）
        # drawing_mode 为 "library" 时对应 "系统函数库"
        initial_mode = "系统函数库" if self.drawing_mode == "library" else "光栅化算法"
        self.set_drawing_mode(initial_mode)

        # --- Pixel buffer 初始化 (用于快速像素级绘制与合成) ---
        try:
            self.pixel_buffer = PixelBuffer(self.canvas, getattr(self, 'canvas_bg_color', '#333333'))
            self.pixel_buffer.ensure()
        except Exception:
            self.pixel_buffer = None

        # --- 初始化与绑定 ---
        self.bind("<Control-z>", lambda event: self.undo_last_action())
        self.bind("<Control-c>", self.copy_selection)
        self.bind("<Control-v>", self.paste_selection)
        self.bind("<Control-s>", lambda event: self.save_project())
        self.bind("<Control-o>", lambda event: self.open_project())
        self.bind("<Control-h>", lambda event: self.flip_horizontal_selection())
        self.bind("<Control-Shift-V>", lambda event: self.flip_vertical_selection())
        self.add_new_layer(name="背景")
        self.select_tool("pencil")
        
        # 初始绘制背景
        self.after(100, self.draw_canvas_background)
        
        self._capture_and_save_state()

    # --- 文件/历史记录/图层管理 (与上一版本保持一致) ---
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
        
        transformmenu = Menu(menubar, tearoff=0)
        transformmenu.add_command(label="左右翻转", command=self.flip_horizontal_selection, accelerator="Ctrl+H")
        transformmenu.add_command(label="上下翻转", command=self.flip_vertical_selection, accelerator="Ctrl+Shift+V")
        menubar.add_cascade(label="变换", menu=transformmenu)

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

    def get_serializable_state(self):
        """构建可安全写入JSON的项目状态（包含缩放/平移，图像转Base64）。"""
        import copy, base64, io

        # 收集画布项的基础信息（不包含不可序列化的Tk内部对象）
        items_data = []
        for item_id in self.canvas.find_all():
            tags = self.canvas.gettags(item_id)
            if "handle" in tags or "grid_line" in tags:
                continue

            item_type = self.canvas.type(item_id)
            coords = self.canvas.coords(item_id)
            options = {}
            config_keys = ['tags', 'width', 'fill', 'outline', 'capstyle', 'smooth', 'joinstyle', 'dash', 'text', 'font', 'anchor']
            for key in config_keys:
                try:
                    options[key] = self.canvas.itemcget(item_id, key)
                except Exception:
                    pass
            # 注意：不保存Tk的'image'句柄，恢复时根据object_states中的PIL数据重建
            items_data.append({"type": item_type, "coords": coords, "options": options})

        # 深拷贝object_states并将PIL图像转Base64字符串
        serializable_object_states = {}
        for tag, state in self.object_states.items():
            st_copy = copy.deepcopy(state)
            pil_img = st_copy.pop('original_pil_image', None)
            if pil_img is not None:
                try:
                    buf = io.BytesIO()
                    pil_img.save(buf, format='PNG')
                    st_copy['original_pil_image_b64'] = base64.b64encode(buf.getvalue()).decode('ascii')
                except Exception:
                    # 编码失败时忽略图像以确保可写
                    pass
            serializable_object_states[tag] = st_copy

        return {
            "bg_color": self.canvas_bg_color,
            "items": items_data,
            "object_states": serializable_object_states,
            "layers": self.layers,
            "active_layer_id": self.active_layer_id,
            "layer_counter": self.layer_counter,
            "zoom_level": self.zoom_level,
            "pan_offset_x": self.pan_offset_x,
            "pan_offset_y": self.pan_offset_y,
        }

    def save_project(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Gemini绘图板项目", "*.json"), ("所有文件", "*.*")],
            title="保存项目文件"
        )
        if not file_path: return
        try:
            canvas_state = self.get_serializable_state()
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
        """导出画布为图片，彻底修复曲面塌陷与分辨率问题"""
        if self.selection_group:
            self._clear_resize_handles()
            self.selection_group.clear()
            self.canvas.update_idletasks()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg")],
            title="导出为图片"
        )
        if not file_path: return

        try:
            from coordinate_system import get_logical_bounding_box
            from surfaces import BezierSurface
            from curves import BezierCurve, BSplineCurve
            
            # 1. 计算逻辑边界
            content_bbox = get_logical_bounding_box(self)
            
            # 定义标准画布边界 (0, 0, 2000, 1500)
            # 这样导出的图片至少是这个尺寸，且包含所有内容
            canvas_w, canvas_h = getattr(self, 'logical_canvas_size', (2000, 1500))
            canvas_x1, canvas_y1, canvas_x2, canvas_y2 = 0, 0, canvas_w, canvas_h

            if content_bbox is None:
                # 如果没有内容，导出空白的标准画布
                lx1, ly1, lx2, ly2 = canvas_x1, canvas_y1, canvas_x2, canvas_y2
            else:
                # 取并集：(内容包围盒) U (标准画布)
                bx1, by1, bx2, by2 = content_bbox
                lx1 = min(bx1, canvas_x1)
                ly1 = min(by1, canvas_y1)
                lx2 = max(bx2, canvas_x2)
                ly2 = max(by2, canvas_y2)

            margin = 50 # 逻辑边距
            export_lx, export_ly = lx1 - margin, ly1 - margin
            logical_w = (lx2 - lx1) + 2 * margin
            logical_h = (ly2 - ly1) + 2 * margin

            # 2. 【核心修复】：计算导出缩放比例
            # 目标：确保导出的图片长边至少为 2000 像素，以保证曲面网格不塌陷
            # 改进：基于长边计算，防止瘦高图形导致内存溢出
            max_dim = max(logical_w, logical_h, 1)
            export_scale = 2000.0 / max_dim
            export_scale = max(export_scale, 2.0) # 至少放大2倍，保证清晰度

            # 安全检查：防止生成过大的图片导致崩溃 (限制最大边长为 8000)
            final_w = logical_w * export_scale
            final_h = logical_h * export_scale
            max_side = max(final_w, final_h)
            
            MAX_SIDE_LIMIT = 8000
            if max_side > MAX_SIDE_LIMIT:
                reduction = MAX_SIDE_LIMIT / max_side
                export_scale *= reduction

            width = int(logical_w * export_scale)
            height = int(logical_h * export_scale)

            # 3. 创建高分辨率画布
            final_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

            for layer in self.layers:
                if not layer['visible']: continue
                layer_id = layer['id']
                layer_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(layer_image)

                for unique_tag, state in self.object_states.items():
                    # 图层过滤
                    items = list(self.canvas.find_withtag(unique_tag))
                    if not items or layer_id not in self.canvas.gettags(items[0]):
                        continue

                    # --- A. 处理曲面 (修复重点) ---
                    if 'control_grid' in state:
                        surface = BezierSurface(state['control_grid'])
                        color = state.get('color', '#FFFFFF')
                        if state.get('display_mode') == 'wireframe':
                            u_curves, v_curves = surface.get_isocurves(10, 10)
                            for curve in u_curves + v_curves:
                                pts = []
                                for p in curve:
                                    pts.append((p[0] - export_lx) * export_scale)
                                    pts.append((p[1] - export_ly) * export_scale)
                                if len(pts) >= 4:
                                    draw.line(pts, fill=color, width=max(1, int(export_scale/2)))
                        else:
                            mesh_pts, faces = surface.generate_mesh(20, 20)
                            for face in faces:
                                tri = [mesh_pts[i] for i in face]
                                pts = [((p[0]-export_lx)*export_scale, (p[1]-export_ly)*export_scale) for p in tri]
                                avg_z = (tri[0][2] + tri[1][2] + tri[2][2]) / 3
                                gray = int(max(0, min(255, (avg_z + 50) * 2.55)))
                                draw.polygon(pts, fill=f'#{gray:02x}{gray:02x}{gray:02x}')

                    # --- B. 处理光栅化图形 ---
                    elif 'original_pil_image' in state or 'original_pil_image_b64' in state:
                        pil_img = state.get('original_pil_image')
                        # 尝试从 Base64 恢复图片（针对刚加载的项目）
                        if pil_img is None and state.get('original_pil_image_b64'):
                            try:
                                import base64, io
                                data = base64.b64decode(state['original_pil_image_b64'])
                                pil_img = Image.open(io.BytesIO(data)).convert('RGBA')
                            except:
                                pil_img = None
                        
                        if pil_img:
                            pil_img = pil_img.copy()
                            # 旋转
                            angle = state.get('angle', 0)
                            if angle != 0:
                                pil_img = pil_img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
                            
                            # 获取逻辑位置和尺寸（兼容性修复）
                            lx, ly, lw, lh = 0, 0, 0, 0
                            if 'start_xy' in state and 'end_xy' in state:
                                lx, ly = state['start_xy']
                                lw = abs(state['end_xy'][0] - state['start_xy'][0])
                                lh = abs(state['end_xy'][1] - state['start_xy'][1])
                            elif 'original_coords' in state and len(state['original_coords']) >= 2:
                                lx, ly = state['original_coords'][0], state['original_coords'][1]
                                # 如果没有记录尺寸，默认使用图片原始尺寸
                                lw = pil_img.width
                                lh = pil_img.height
                            else:
                                continue # 无法确定位置，跳过

                            # 缩放至匹配 export_scale
                            target_w = int(lw * export_scale)
                            target_h = int(lh * export_scale)
                            pil_img = pil_img.resize((max(1, target_w), max(1, target_h)), Image.Resampling.LANCZOS)
                            
                            img_x = int((lx - export_lx) * export_scale)
                            img_y = int((ly - export_ly) * export_scale)
                            layer_image.paste(pil_img, (img_x, img_y), pil_img)

                    # --- C. 处理矢量形状 (直线、矩形等) ---
                    elif 'original_coords' in state:
                        l_coords = state['original_coords']
                        ex_pts = [(c - export_lx if i%2==0 else c - export_ly) * export_scale for i, c in enumerate(l_coords)]
                        
                        item_type = self.canvas.type(items[0])
                        # 获取颜色逻辑修复（详见之前的分析）
                        try:
                            f = self.canvas.itemcget(items[0], "fill")
                            o = self.canvas.itemcget(items[0], "outline") if item_type != "line" else f
                            w = int(float(self.canvas.itemcget(items[0], "width") or 1) * export_scale)
                        except: f, o, w = "#FFFFFF", "#FFFFFF", int(export_scale)

                        if item_type == "line": draw.line(ex_pts, fill=f, width=w)
                        elif item_type == "rectangle": draw.rectangle(ex_pts, fill=f or None, outline=o, width=w)
                        elif item_type == "oval": draw.ellipse(ex_pts, fill=f or None, outline=o, width=w)
                        elif item_type == "polygon": draw.polygon(ex_pts, fill=f or None, outline=o)

                # 合成图层
                opacity = layer.get('opacity', 1.0)
                if opacity < 1.0:
                    alpha = layer_image.split()[3]
                    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
                    layer_image.putalpha(alpha)
                final_image = Image.alpha_composite(final_image, layer_image)

            # 4. 加上背景色
            bg = Image.new("RGB", (width, height), self.canvas_bg_color)
            bg.paste(final_image, (0, 0), final_image)
            bg.save(file_path)
            messagebox.showinfo("成功", f"图片导出成功！分辨率: {width}x{height}")

        except Exception as e:
            messagebox.showerror("导出失败", f"错误详情: {str(e)}")

    def copy_selection(self, event=None):
        if not self.selection_group or self.current_tool != "select":
            return
        
        self.clipboard = []
        bbox = self._get_selection_bbox()
        if not bbox: return
        
        min_x, min_y = bbox[0], bbox[1]
        from coordinate_system import screen_to_logical
        self.canvas.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)

        origin_logical = screen_to_logical(
            [min_x, min_y],
            self.zoom_level,
            self.pan_offset_x,
            self.pan_offset_y,
            canvas_width,
            canvas_height
        )
        origin_logical = (origin_logical[0], origin_logical[1]) if isinstance(origin_logical, (list, tuple)) else (0, 0)

        clipboard_data = {
            'origin': (min_x, min_y),
            'origin_logical': origin_logical,
            'copy_zoom': self.zoom_level,
            'copy_pan': (self.pan_offset_x, self.pan_offset_y),
            'items': []
        }

        for unique_tag in self.selection_group:
            item_group_data = {'unique_tag_prefix': unique_tag.split('_')[0], 'parts': []}
            
            # 保存对象状态信息（如角度、工具类型、光栅 PIL 数据等）
            if unique_tag in self.object_states:
                state = copy.deepcopy(self.object_states[unique_tag])
                if state.get('original_pil_image') is not None:
                    state['original_pil_image'] = state['original_pil_image'].copy()
                item_group_data['angle'] = state.get('angle', 0)
                item_group_data['tool'] = state.get('tool', None)
                item_group_data['state'] = state
            
            for item_id in self.canvas.find_withtag(unique_tag):
                item_type = self.canvas.type(item_id)
                coords = self.canvas.coords(item_id)
                logical_coords = screen_to_logical(
                    coords,
                    self.zoom_level,
                    self.pan_offset_x,
                    self.pan_offset_y,
                    canvas_width,
                    canvas_height
                )
                relative_coords = [(lc - origin_logical[0]) if i % 2 == 0 else (lc - origin_logical[1]) for i, lc in enumerate(logical_coords)]
                
                options = {}
                copy_keys = ['width', 'fill', 'outline', 'capstyle', 'smooth', 'joinstyle', 'dash', 'tags', 'text', 'font', 'anchor']
                for key in copy_keys:
                    try: options[key] = self.canvas.itemcget(item_id, key)
                    except: pass
                
                item_group_data['parts'].append({
                    'type': item_type,
                    'relative_logical_coords': relative_coords,
                    'options': options
                })
            clipboard_data['items'].append(item_group_data)
        
        self.clipboard = clipboard_data

    def paste_selection(self, event=None):
        if not self.clipboard or self.current_tool != "select":
            return

        self._clear_resize_handles()
        self.selection_group.clear()

        from coordinate_system import logical_to_screen, screen_to_logical
        self.canvas.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)

        origin_logical = self.clipboard.get('origin_logical', (0, 0))
        offset_logical_x = 20 / self.zoom_level
        offset_logical_y = 20 / self.zoom_level

        for item_group_data in self.clipboard['items']:
            new_unique_tag = f"{item_group_data['unique_tag_prefix']}_{time.time()}"
            self.selection_group.add(new_unique_tag)
            state_copy = copy.deepcopy(item_group_data.get('state', {})) if item_group_data.get('state') else {}
            if state_copy.get('original_pil_image') is not None:
                state_copy['original_pil_image'] = state_copy['original_pil_image'].copy()
            
            all_new_part_coords = {}
            for part_data in item_group_data['parts']:
                if part_data.get('type') == 'image':
                    # 光栅图像在后面统一按照 state_copy 处理
                    continue

                rel_logical = part_data.get('relative_logical_coords')
                if rel_logical is None:
                    # 兼容旧剪贴板数据，退化为原来的屏幕系逻辑
                    rel_logical = part_data.get('relative_coords', [])
                    rel_logical = screen_to_logical(
                        rel_logical,
                        self.zoom_level,
                        self.pan_offset_x,
                        self.pan_offset_y,
                        canvas_width,
                        canvas_height
                    ) if rel_logical else []

                abs_logical = []
                for i, coord in enumerate(rel_logical):
                    base = origin_logical[0] if i % 2 == 0 else origin_logical[1]
                    offset = offset_logical_x if i % 2 == 0 else offset_logical_y
                    abs_logical.append(coord + base + offset)

                screen_coords = logical_to_screen(
                    abs_logical,
                    self.zoom_level,
                    self.pan_offset_x,
                    self.pan_offset_y,
                    canvas_width,
                    canvas_height
                )

                creator_func = getattr(self.canvas, f"create_{part_data['type']}", None)
                if creator_func:
                    options = part_data['options']
                    original_tags = list(options.get('tags', []))
                    new_tags = [t for t in original_tags if not (t.startswith('shape_') or t.startswith('stroke_') or t.startswith('layer_'))]
                    new_tags.extend([new_unique_tag, self.active_layer_id])
                    options['tags'] = new_tags
                    
                    new_item_id = creator_func(screen_coords, **options)
                    all_new_part_coords[new_item_id] = abs_logical

            # 如果是光栅图像对象，按 state_copy 重建 image
            if state_copy.get('original_pil_image') is not None:
                pil_img = state_copy['original_pil_image']
                pil_img_copy = pil_img.copy()

                # 调整逻辑坐标基于偏移
                def _shift_point(pt):
                    return (pt[0] + offset_logical_x, pt[1] + offset_logical_y)

                if 'start_xy' in state_copy:
                    state_copy['start_xy'] = _shift_point(state_copy['start_xy'])
                if 'end_xy' in state_copy:
                    state_copy['end_xy'] = _shift_point(state_copy['end_xy'])
                if 'original_coords' in state_copy and isinstance(state_copy['original_coords'], (list, tuple)):
                    shifted = []
                    for i, coord in enumerate(state_copy['original_coords']):
                        base = offset_logical_x if i % 2 == 0 else offset_logical_y
                        shifted.append(coord + base)
                    state_copy['original_coords'] = shifted

                logical_pos = None
                if 'start_xy' in state_copy:
                    logical_pos = state_copy['start_xy']
                elif 'original_coords' in state_copy and len(state_copy['original_coords']) >= 2:
                    logical_pos = (state_copy['original_coords'][0], state_copy['original_coords'][1])

                if logical_pos:
                    screen_pos = logical_to_screen(
                        list(logical_pos),
                        self.zoom_level,
                        self.pan_offset_x,
                        self.pan_offset_y,
                        canvas_width,
                        canvas_height
                    )

                    display_img = pil_img_copy
                    if self.zoom_level != 1.0:
                        new_w = max(int(pil_img_copy.width * self.zoom_level), 1)
                        new_h = max(int(pil_img_copy.height * self.zoom_level), 1)
                        display_img = pil_img_copy.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    tk_img = ImageTk.PhotoImage(display_img)
                    new_tags = [t for t in (item_group_data.get('parts')[0].get('options', {}).get('tags', []) if item_group_data.get('parts') else []) if not (t.startswith('shape_') or t.startswith('stroke_') or t.startswith('layer_'))]
                    new_tags.extend([new_unique_tag, self.active_layer_id])
                    img_id = self.canvas.create_image(screen_pos[0], screen_pos[1], image=tk_img, anchor='nw', tags=tuple(new_tags))
                    self._image_references[img_id] = tk_img

                    state_copy['angle'] = state_copy.get('angle', item_group_data.get('angle', 0))
                    state_copy['zoom_ref'] = self.zoom_level
                    state_copy['pan_ref_x'] = self.pan_offset_x
                    state_copy['pan_ref_y'] = self.pan_offset_y
                    self.object_states[new_unique_tag] = state_copy
                continue

            is_stroke = new_unique_tag.startswith("stroke_") or new_unique_tag.startswith("erase_stroke_")
            if is_stroke:
                state = state_copy or {}
                state['angle'] = state.get('angle', item_group_data.get('angle', 0))
                state['original_coords'] = None
                state['original_coords_map'] = all_new_part_coords
                state['zoom_ref'] = self.zoom_level
                state['pan_ref_x'] = self.pan_offset_x
                state['pan_ref_y'] = self.pan_offset_y
                self.object_states[new_unique_tag] = state
            else:
                first_item_ids = list(all_new_part_coords.keys())
                if first_item_ids:
                    logical_coords = all_new_part_coords[first_item_ids[0]]
                    state = state_copy or {}
                    state['angle'] = state.get('angle', item_group_data.get('angle', 0))
                    state['original_coords'] = logical_coords
                    state['original_coords_map'] = None
                    state['zoom_ref'] = self.zoom_level
                    state['pan_ref_x'] = self.pan_offset_x
                    state['pan_ref_y'] = self.pan_offset_y
                    self.object_states[new_unique_tag] = state
        
        self._draw_resize_handles()
        self.update_layer_stacking()
        self._capture_and_save_state()

    def delete_selection(self, event=None):
        """删除当前选中的对象（支持 Delete 键触发）"""
        if not self.selection_group:
            return

        # 删除选中对象对应的 Canvas 元素与状态
        for tag in list(self.selection_group):
            items = list(self.canvas.find_withtag(tag))
            for item_id in items:
                # 清理图像引用，防止内存泄漏
                if hasattr(self, "_image_references") and item_id in self._image_references:
                    del self._image_references[item_id]
                self.canvas.delete(item_id)

            # 清理对象状态
            if tag in self.object_states:
                self.object_states.pop(tag, None)

        # 清理选择与辅助控件
        self.selection_group.clear()
        self.original_group_states.clear()
        self._clear_resize_handles()

        # 记录历史以便撤销
        if hasattr(self, "_capture_and_save_state"):
            self._capture_and_save_state()

    def add_new_layer(self, name=None, insert_index=None):
        from layers import add_new_layer as _add_new_layer
        return _add_new_layer(self, name=name, insert_index=insert_index)

    def delete_selected_layer(self):
        from layers import delete_selected_layer as _delete_selected_layer
        return _delete_selected_layer(self)

    def duplicate_selected_layer(self):
        from layers import duplicate_selected_layer as _duplicate_selected_layer
        return _duplicate_selected_layer(self)

    def move_layer_up(self):
        from layers import move_layer_up as _move_layer_up
        return _move_layer_up(self)

    def move_layer_down(self):
        from layers import move_layer_down as _move_layer_down
        return _move_layer_down(self)

    def select_layer(self, layer_id):
        from layers import select_layer as _select_layer
        return _select_layer(self, layer_id)

    def toggle_layer_visibility(self, layer_id):
        from layers import toggle_layer_visibility as _toggle_layer_visibility
        return _toggle_layer_visibility(self, layer_id)

    def set_layer_opacity(self, layer_id, opacity_value):
        from layers import set_layer_opacity as _set_layer_opacity
        return _set_layer_opacity(self, layer_id, opacity_value)

    def update_layer_list_ui(self):
        from layers import update_layer_list_ui as _update_layer_list_ui
        return _update_layer_list_ui(self)

    def rename_layer(self, layer_id):
        from layers import rename_layer as _rename_layer
        return _rename_layer(self, layer_id)

    def update_layer_stacking(self):
        from layers import update_layer_stacking as _update_layer_stacking
        return _update_layer_stacking(self)

    def get_layer_by_id(self, layer_id):
        from layers import get_layer_by_id as _get_layer_by_id
        return _get_layer_by_id(self, layer_id)

    def _get_selected_layer_index(self):
        from layers import _get_selected_layer_index as _get_selected_layer_index_fn
        return _get_selected_layer_index_fn(self)

    def _capture_and_save_state(self):
        from history import capture_and_save_state as _capture_and_save_state
        return _capture_and_save_state(self)

    def _restore_state_from_history(self, state):
        from history import restore_state_from_history as _restore_state_from_history
        return _restore_state_from_history(self, state)

    def undo_last_action(self):
        from history import undo_last_action as _undo_last_action
        return _undo_last_action(self)

    # --- 工具选择与事件处理 (与上一版本保持一致) ---

    def select_tool(self, tool):
        if self.current_tool == "polygon" and self.polygon_points: self.finalize_polygon()
        
        # 完成曲线或曲面编辑
        if self.current_tool in ["bezier", "bspline"] and self.curve_tool:
            self.finish_curve()
        if self.current_tool == "bezier_surface" and self.surface_tool:
            self.finish_surface()
        
        if self.selection_group: self._clear_resize_handles(); self.selection_group.clear(); self.original_group_states.clear()
        self.current_tool = tool
        for t, b in self.tool_buttons.items(): b.configure(fg_color=self.active_fg_color if t == tool else "transparent", hover_color=self.active_hover_color if t == tool else ("gray70", "gray30"))
        
        # 根据选择的工具，动态重新排列右侧选项面板的模块顺序
        self._reorder_options_panel(tool)
        
        if tool == "polygon": self.reset_polygon_drawing(); self.current_polygon_tag = f"poly_in_progress_{time.time()}"
        
        # 初始化曲线工具
        if tool == "bezier":
            self.init_curve_tool("bezier")
        elif tool == "bspline":
            self.init_curve_tool("bspline")
        elif tool == "bezier_surface":
            self.init_surface_tool()
        
        self.brush_size_slider.configure(state="disabled" if tool in ["fill", "select", "text"] else "normal")
        self.canvas.config(cursor="arrow" if tool == "select" else "dotbox" if tool == "eraser" else "xterm" if tool == "text" else "crosshair")

    def _reorder_options_panel(self, tool):
        """根据选择的工具动态重新排列右侧选项面板的模块顺序"""
        # 首先隐藏所有模块
        self.color_section.pack_forget()
        self.brush_section.pack_forget()
        self.eraser_section.pack_forget()
        self.separator1.pack_forget()
        self.drawing_mode_section.pack_forget()
        self.separator2.pack_forget()
        self.curve_surface_section.pack_forget()
        self.separator3.pack_forget()
        self.action_section.pack_forget()
        
        # 根据工具类型，决定显示的模块和顺序
        if tool == "eraser":
            # 橡皮擦工具：橡皮擦模式提到最前
            self.eraser_section.pack(fill="x", padx=10)
            self.separator1.pack(pady=20, padx=15, fill="x")
            self.color_section.pack(fill="x", padx=10)
            self.brush_section.pack(fill="x", padx=10)
            self.separator2.pack(pady=20, padx=15, fill="x")
            self.drawing_mode_section.pack(fill="x", padx=10)
            self.separator3.pack(pady=20, padx=15, fill="x")
            self.action_section.pack(fill="x", padx=10)
            
        elif tool in ["bezier", "bspline", "bezier_surface"]:
            # 曲线/曲面工具：曲线/曲面选项提到最前
            self.curve_surface_section.pack(fill="x", padx=10)
            self.separator1.pack(pady=20, padx=15, fill="x")
            self.color_section.pack(fill="x", padx=10)
            self.brush_section.pack(fill="x", padx=10)
            self.separator2.pack(pady=20, padx=15, fill="x")
            self.drawing_mode_section.pack(fill="x", padx=10)
            self.separator3.pack(pady=20, padx=15, fill="x")
            self.action_section.pack(fill="x", padx=10)
            
            # 显示对应的曲线/曲面选项
            if tool in ["bezier", "bspline"]:
                self.finish_curve_button.pack(pady=5, padx=10, fill="x")
                self.curve_hint_label.pack(pady=5, padx=10)
                hint_text = "点击画布添加控制点\n" + (
                    "二次Bézier需要3个点\n三次Bézier需要4个点\n或任意多个点" if tool == "bezier"
                    else f"B样条需要至少4个控制点"
                )
                self.curve_hint_label.configure(text=hint_text)
                self.toggle_surface_mode_button.pack_forget()
                self.finish_surface_button.pack_forget()
            elif tool == "bezier_surface":
                self.finish_curve_button.pack_forget()
                self.curve_hint_label.pack(pady=5, padx=10)
                self.curve_hint_label.configure(text="拖动控制点调整曲面形状\n点击按钮切换显示模式")
                self.toggle_surface_mode_button.pack(pady=5, padx=10, fill="x")
                self.finish_surface_button.pack(pady=5, padx=10, fill="x")
                
        else:
            # 其他工具：默认顺序
            self.color_section.pack(fill="x", padx=10)
            self.brush_section.pack(fill="x", padx=10)
            self.separator1.pack(pady=20, padx=15, fill="x")
            self.drawing_mode_section.pack(fill="x", padx=10)
            self.separator2.pack(pady=20, padx=15, fill="x")
            self.separator3.pack(pady=20, padx=15, fill="x")
            self.action_section.pack(fill="x", padx=10)

    def _scroll_options_panel_to_top(self):
        """将右侧选项面板滚动到顶部"""
        try:
            self.options_panel._parent_canvas.yview_moveto(0)
        except:
            pass

    def start_drawing(self, event):
        from event_handlers import start_drawing as _start_drawing
        return _start_drawing(self, event)

    def stop_drawing(self, event):
        from event_handlers import stop_drawing as _stop_drawing
        return _stop_drawing(self, event)

    def draw(self, event):
        from event_handlers import draw_on_canvas as _draw_on_canvas
        return _draw_on_canvas(self, event)

    def clear_canvas(self):
        """清空画布（保存当前状态到历史记录）"""
        # 先保存当前状态到历史
        from history import capture_and_save_state
        capture_and_save_state(self)
        
        # 清空选择和控制柄
        self._clear_resize_handles()
        self.selection_group.clear()
        
        # 删除所有图形（保留网格线）
        self.canvas.delete("all")
        
        # 重绘背景
        self.draw_canvas_background()
        
        # 清空对象状态
        self.object_states.clear()
        self._image_references.clear()
        
        # 重置图层
        self.layers.clear()
        self.layer_counter = 0
        self.active_layer_id = None
        
        # 重置为初始图层
        self.add_new_layer(name="背景")
        
        # 重绘网格
        self.draw_grid()

    def set_drawing_mode(self, mode):
        """
        切换绘图模式
        """
        # 更新开关按钮的状态
        self.drawing_mode_switch.set(mode)
        
        if mode == "系统函数库":
            self.use_rasterization = False
            self.mode_info_label.configure(
                text="当前：使用Canvas内置函数\n(直线、圆形、矩形)"
            )
            self.algorithm_selector.pack_forget()
            self.algo_label.pack_forget()
        else:
            self.use_rasterization = True
            self.mode_info_label.configure(
                text="当前：使用光栅化算法\n(Bresenham/Midpoint/DDA)"
            )
            self.algo_label.pack(pady=(15, 5), padx=10)
            self.algorithm_selector.pack(pady=5, padx=10, fill="x")

    def set_eraser_mode(self, mode):
        """设置橡皮擦模式（局部/对象），供右侧分段控件回调使用"""
        # 记录当前模式
        self.eraser_mode = mode
        # 同步控件显示（若控件已初始化）
        try:
            self.eraser_mode_switch.set(mode)
        except Exception:
            pass
        # 如果当前正在使用橡皮擦，调整光标以保持一致
        if getattr(self, "current_tool", None) == "eraser":
            self.canvas.config(cursor="dotbox")

    def set_rasterization_algorithm(self, algorithm):
        """设置光栅化算法"""
        self.rasterization_algorithm = algorithm
        self.mode_info_label.configure(
            text=f"当前：光栅化算法 - {algorithm}"
        )

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
        if not self.current_polygon_tag:
            self.current_polygon_tag = f"poly_in_progress_{time.time()}"
        if len(self.polygon_points) > 1:
            line_tags = (self.current_polygon_tag,)
            self.canvas.create_line(self.polygon_points[-2], self.polygon_points[-1], fill=self.current_color, width=self.brush_size, capstyle="round", tags=line_tags)
    def on_mouse_move(self, event):
        if self.current_tool == "polygon" and self.polygon_points:
            if self.preview_line: self.canvas.delete(self.preview_line)
            self.preview_line = self.canvas.create_line(self.polygon_points[-1], (event.x, event.y), fill=self.current_color, width=self.brush_size, dash=(4, 4))
        
        # 在曲线/曲面编辑时，悬停在控制点上改变光标
        from event_handlers import on_mouse_move_canvas
        on_mouse_move_canvas(self, event)

    # --- 填充逻辑修正：解决空白填充和颜色覆盖问题 ---
    
    def _get_rasterization_outline(self, unique_tag):
        from drawing_utils import get_rasterization_outline as _get_rasterization_outline
        return _get_rasterization_outline(self, unique_tag)

    def fill_shape(self, event):
        from shape_handlers import fill_shape as _fill_shape
        return _fill_shape(self, event)

    # --- 其他辅助和几何方法 (与上一版本保持一致) ---

    def finalize_polygon(self):
        from shape_handlers import finalize_polygon as _finalize_polygon
        return _finalize_polygon(self)

    def create_text_object(self, x, y):
        from shape_handlers import create_text_object as _create_text_object
        return _create_text_object(self, x, y)

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.draw_grid()

    def draw_canvas_background(self):
        """绘制画布背景矩形"""
        self.canvas.delete("canvas_bg")
        
        from coordinate_system import logical_to_screen
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        
        # 计算画布矩形的屏幕坐标
        # 假设画布从 (0,0) 开始
        coords = logical_to_screen(
            [0, 0, self.logical_canvas_size[0], self.logical_canvas_size[1]],
            self.zoom_level,
            self.pan_offset_x,
            self.pan_offset_y,
            width,
            height
        )
        
        if len(coords) == 4:
            self.canvas.create_rectangle(
                coords[0], coords[1], coords[2], coords[3],
                fill=self.canvas_bg_color, outline="", tags="canvas_bg"
            )
            self.canvas.tag_lower("canvas_bg")

    def draw_grid(self):
        self.canvas.delete("grid_line")
        
        # 确保背景始终存在
        if not self.canvas.find_withtag("canvas_bg"):
            self.draw_canvas_background()
            
        if self.grid_visible:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            
            # 计算网格的屏幕坐标偏移，以同步平移
            # 将逻辑平移量转换为屏幕偏移
            from coordinate_system import logical_to_screen
            
            # 计算基准点 (0, 0) 在屏幕上的位置
            logical_origin = [0, 0]
            screen_origin = logical_to_screen(logical_origin, self.zoom_level, self.pan_offset_x, self.pan_offset_y, width, height)
            
            grid_offset_x = screen_origin[0] % self.grid_spacing
            grid_offset_y = screen_origin[1] % self.grid_spacing
            
            # 确保偏移在 [0, grid_spacing) 范围内
            if grid_offset_x < 0:
                grid_offset_x += self.grid_spacing
            if grid_offset_y < 0:
                grid_offset_y += self.grid_spacing
            
            # 绘制垂直线（沿 x 轴）
            x = grid_offset_x
            while x < width:
                self.canvas.create_line(x, 0, x, height, fill="#555555", tags="grid_line", dash=(2, 4))
                x += self.grid_spacing
            
            # 绘制水平线（沿 y 轴）
            y = grid_offset_y
            while y < height:
                self.canvas.create_line(0, y, width, y, fill="#555555", tags="grid_line", dash=(2, 4))
                y += self.grid_spacing
            
            self.canvas.tag_lower("grid_line")

    def _draw_rasterization_shape(self, tool, x0, y0, x1, y1, unique_tag, tags):
        from drawing_utils import draw_rasterization_shape as _draw_rasterization_shape
        return _draw_rasterization_shape(self, tool, x0, y0, x1, y1, unique_tag, tags)

    # --- 缩放/旋转/辅助 (与上一版本保持一致) ---
    def _convert_to_polygon(self, unique_tag):
        from drawing_utils import convert_to_polygon as _convert_to_polygon
        return _convert_to_polygon(self, unique_tag)

    def _clear_resize_handles(self):
        from selection import clear_resize_handles as _clear_resize_handles
        return _clear_resize_handles(self)

    # --- 画布拖动功能 ---
    def on_space_press(self, event):
        """当空格键被按下时，启用画布拖动模式"""
        self.space_pressed = True
        self.canvas.config(cursor="hand2")

    def on_space_release(self, event):
        """当空格键被释放时，禁用画布拖动模式"""
        self.space_pressed = False
        self.pan_start_x = None
        self.pan_start_y = None
        # 恢复正常光标
        tool_cursors = {
            "select": "arrow",
            "eraser": "dotbox",
            "text": "xterm",
            "default": "crosshair"
        }
        cursor = tool_cursors.get(self.current_tool, "crosshair")
        self.canvas.config(cursor=cursor)

    # --- 翻转变换功能 ---
    def flip_horizontal_selection(self):
        """水平翻转（左右翻转）选中的对象"""
        from transform import flip_horizontal
        flip_horizontal(self)

    def flip_vertical_selection(self):
        """竖直翻转（上下翻转）选中的对象"""
        from transform import flip_vertical
        flip_vertical(self)
    
    # --- 画布缩放功能 ---
    def zoom_in(self):
        """放大画布"""
        new_zoom = min(self.zoom_level * 1.2, self.zoom_max)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        """缩小画布"""
        new_zoom = max(self.zoom_level / 1.2, self.zoom_min)
        self.set_zoom(new_zoom)
    
    def reset_zoom(self):
        """重置缩放为 100%"""
        self.set_zoom(1.0)
    
    def set_zoom(self, zoom_level):
        """设置缩放级别"""
        from coordinate_system import sync_all_objects_to_screen
        
        self.zoom_level = max(self.zoom_min, min(zoom_level, self.zoom_max))

        # 使用统一的坐标转换系统同步所有对象
        sync_all_objects_to_screen(self)
        
        # 更新背景矩形
        self.draw_canvas_background()
        
        # 重新绘制网格以保持同步
        if self.grid_visible:
            self.draw_grid()
        
        # 重新绘制网格以保持同步
        if self.grid_visible:
            self.draw_grid()
        
        # 无副作用修复：强制 Canvas 更新内部拾取索引
        self.canvas.update_idletasks()
        
        # 更新 UI 显示
        zoom_percent = int(self.zoom_level * 100)
        self.zoom_label.configure(text=f"{zoom_percent}%")
        self.zoom_slider.set(zoom_percent)
    
    def on_zoom_slider_change(self, value):
        """当缩放滑块改变时"""
        zoom_level = float(value) / 100.0
        self.set_zoom(zoom_level)
    
    def on_canvas_mousewheel(self, event):
        """鼠标滚轮缩放"""
        # Windows 中 MouseWheel 事件 delta = 120/-120
        # Linux 中 Button-4 向上，Button-5 向下
        if event.num == 4 or event.delta > 0:
            self.zoom_in()
        elif event.num == 5 or event.delta < 0:
            self.zoom_out()
    
    def _get_selection_bbox(self):
        from selection import get_selection_bbox as _get_selection_bbox
        return _get_selection_bbox(self)

    def _draw_resize_handles(self):
        from selection import draw_resize_handles as _draw_resize_handles
        return _draw_resize_handles(self)
    
    # --- 曲线和曲面工具方法 ---
    def init_curve_tool(self, curve_type):
        """初始化曲线工具"""
        from curve_surface_tools import BezierCurveTool, BSplineCurveTool
        
        # 清除现有曲线工具
        if self.curve_tool:
            self.curve_tool.clear()
        
        # 创建新的曲线工具
        self.curve_editing_tag = f"curve_{curve_type}_{time.time()}"
        
        if curve_type == "bezier":
            self.curve_tool = BezierCurveTool(self.canvas, self, curve_type='any', color=self.current_color)
        elif curve_type == "bspline":
            self.curve_tool = BSplineCurveTool(self.canvas, self, degree=3, color=self.current_color)
        
        self.curve_tool.curve_tag = self.curve_editing_tag
        self.curve_control_points = []
    
    def add_curve_control_point(self, x, y):
        """添加曲线控制点"""
        if not self.curve_tool:
            return
        
        self.curve_tool.add_control_point(x, y)
        self.curve_control_points.append((x, y))
        self.curve_tool.update_curve_preview()
    
    def finish_curve(self):
        """完成曲线绘制"""
        if not self.curve_tool or not self.curve_tool.can_finish():
            return False
        
        # 获取曲线的逻辑坐标（已经在curve_tool.control_points中存储为逻辑坐标）
        # 生成曲线上的点（逻辑坐标）
        from curves import BezierCurve, BSplineCurve
        
        if self.current_tool == 'bezier':
            curve = BezierCurve(self.curve_tool.control_points)
        else:  # bspline
            curve = BSplineCurve(self.curve_tool.control_points, self.curve_tool.degree)
        
        curve_points = curve.generate_points(num_segments=100)
        
        # 将曲线点转换为平面坐标列表（逻辑坐标）
        logical_coords = []
        for x, y in curve_points:
            logical_coords.extend([x, y])
        
        # 保存曲线状态到object_states
        state = {
            'tool': self.current_tool,
            'control_points': self.curve_tool.control_points.copy(),  # 逻辑坐标
            'original_coords': logical_coords,  # 曲线上的点（逻辑坐标）
            'curve_type': 'bezier' if self.current_tool == 'bezier' else 'bspline',
            'color': self.current_color,
            'width': self.brush_size,
            'angle': 0,
            'zoom_ref': self.zoom_level,
            'pan_ref_x': self.pan_offset_x,
            'pan_ref_y': self.pan_offset_y
        }
        
        self.object_states[self.curve_editing_tag] = state
        
        # 添加图层标签
        items = self.canvas.find_withtag(self.curve_editing_tag)
        for item in items:
            current_tags = list(self.canvas.gettags(item))
            if self.active_layer_id not in current_tags:
                current_tags.append(self.active_layer_id)
                self.canvas.itemconfig(item, tags=tuple(current_tags))
        
        # 删除控制点和控制多边形，只保留曲线本身
        for pid in self.curve_tool.control_point_ids:
            self.canvas.delete(pid)
        for line_id in self.curve_tool.preview_lines:
            self.canvas.delete(line_id)
        
        # 清理工具状态
        self.curve_tool = None
        self.curve_control_points = []
        self.curve_editing_tag = None
        
        return True
    
    def init_surface_tool(self):
        """初始化曲面工具"""
        from curve_surface_tools import BezierSurfaceTool
        
        # 清除现有曲面工具
        if self.surface_tool:
            self.surface_tool.clear()
        
        surface_tag = f"surface_{time.time()}"
        self.surface_tool = BezierSurfaceTool(self.canvas, self, grid_size=(4, 4), color=self.current_color)
        self.surface_tool.surface_tag = surface_tag
        
        # 创建默认的4x4控制网格
        self._create_default_surface_grid()
    
    def _create_default_surface_grid(self):
        """创建默认的曲面控制网格（使用逻辑坐标）"""
        from coordinate_system import screen_to_logical
        
        # 在画布中心创建一个4x4的控制网格
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        grid_width = 300
        grid_height = 300
        
        rows, cols = 4, 4
        control_grid = []
        
        for i in range(rows):
            row = []
            for j in range(cols):
                # 计算屏幕坐标
                screen_x = center_x - grid_width // 2 + (grid_width / (cols - 1)) * j
                screen_y = center_y - grid_height // 2 + (grid_height / (rows - 1)) * i
                
                # 转换为逻辑坐标
                logical_coords = screen_to_logical(
                    [screen_x, screen_y],
                    self.zoom_level,
                    self.pan_offset_x,
                    self.pan_offset_y,
                    canvas_width,
                    canvas_height
                )
                logical_x, logical_y = logical_coords[0], logical_coords[1]
                
                # z值用于创建一个简单的波形曲面
                z = 20 * math.sin(i * math.pi / (rows - 1)) * math.cos(j * math.pi / (cols - 1))
                
                row.append((logical_x, logical_y, z))
            control_grid.append(row)
        
        self.surface_tool.set_control_grid(control_grid)
        self.surface_tool.update_surface(self.surface_display_mode)
    
    def toggle_surface_display_mode(self):
        """切换曲面显示模式"""
        if not self.surface_tool:
            return
        
        self.surface_display_mode = 'filled' if self.surface_display_mode == 'wireframe' else 'wireframe'
        self.surface_tool.update_surface(self.surface_display_mode)
    
    def finish_surface(self):
        """完成曲面绘制"""
        if not self.surface_tool:
            return False
        
        # 保存曲面状态（control_grid已经是逻辑坐标）
        state = {
            'tool': 'bezier_surface',
            'control_grid': self.surface_tool.control_grid,  # 逻辑坐标
            'display_mode': self.surface_display_mode,
            'color': self.current_color,
            'angle': 0,
            'zoom_ref': self.zoom_level,
            'pan_ref_x': self.pan_offset_x,
            'pan_ref_y': self.pan_offset_y,
            'layer_id': self.active_layer_id
        }
        
        self.object_states[self.surface_tool.surface_tag] = state
        
        # 添加图层标签
        items = self.canvas.find_withtag(self.surface_tool.surface_tag)
        for item in items:
            current_tags = list(self.canvas.gettags(item))
            if self.active_layer_id not in current_tags:
                current_tags.append(self.active_layer_id)
                self.canvas.itemconfig(item, tags=tuple(current_tags))
        
        # 删除控制点，只保留曲面
        for pid in self.surface_tool.control_point_ids:
            self.canvas.delete(pid)
        
        # 清理工具状态
        self.surface_tool = None
        
        return True
    
    def handle_curve_control_point_drag(self, event):
        """处理曲线控制点的拖拽"""
        from coordinate_system import screen_to_logical
        
        if self.dragging_control_point is None:
            # 查找是否点击了控制点
            items = self.canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
            for item in items:
                tags = self.canvas.gettags(item)
                if 'control_point' in tags:
                    self.dragging_control_point = item
                    break
        else:
            # 拖动控制点
            self.canvas.coords(
                self.dragging_control_point,
                event.x - 4, event.y - 4,
                event.x + 4, event.y + 4
            )
            
            # 将屏幕坐标转换为逻辑坐标
            self.canvas.update_idletasks()
            canvas_width = max(self.canvas.winfo_width(), 1)
            canvas_height = max(self.canvas.winfo_height(), 1)
            
            logical_coords = screen_to_logical(
                [event.x, event.y],
                self.zoom_level,
                self.pan_offset_x,
                self.pan_offset_y,
                canvas_width,
                canvas_height
            )
            logical_x, logical_y = logical_coords[0], logical_coords[1]
            
            # 更新对应的控制点坐标（使用逻辑坐标）
            if self.curve_tool:
                # 找到控制点索引
                idx = self.curve_tool.control_point_ids.index(self.dragging_control_point)
                self.curve_tool.control_points[idx] = (logical_x, logical_y)
                
                # 更新曲线预览
                self.curve_tool.update_curve_preview()
            elif self.surface_tool:
                # 曲面控制点拖动
                idx = self.surface_tool.control_point_ids.index(self.dragging_control_point)
                
                # 找到网格中的位置
                rows, cols = self.surface_tool.grid_size
                row = idx // cols
                col = idx % cols
                
                # 更新控制点（使用逻辑坐标）
                old_x, old_y, old_z = self.surface_tool.control_grid[row][col]
                self.surface_tool.control_grid[row][col] = (logical_x, logical_y, old_z)
                
                # 更新曲面显示
                self.surface_tool.update_surface(self.surface_display_mode)
    
    def release_control_point_drag(self, event):
        """释放控制点拖拽"""
        self.dragging_control_point = None
