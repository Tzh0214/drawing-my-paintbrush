import customtkinter as ctk
from tkinter import Canvas, BOTH, YES
from tooltip import Tooltip


def setup_ui(app):
    """把 DrawingApp.__init__ 中的 UI 创建与布局代码抽离到这里。

    注意：这个函数不会修改应用逻辑，只负责把布局部件绑定到传入的 `app` 实例上。
    """
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(1, weight=1)

    # --- 左侧工具栏 ---
    app.toolbar_container = ctk.CTkFrame(app, width=150, corner_radius=0)
    app.toolbar_container.grid(row=0, column=0, sticky="ns")
    app.toolbar_container.grid_propagate(False)
    
    # 工具栏使用可滚动框架
    app.toolbar = ctk.CTkScrollableFrame(app.toolbar_container, corner_radius=0, fg_color="transparent")
    app.toolbar.pack(fill="both", expand=True, side="top")
    
    ui_font = ("Microsoft YaHei", 15)
    button_kwargs = { "font": ui_font, "anchor": "w", "fg_color": "transparent", "hover_color": ("gray70", "gray30"), "height": 40, "corner_radius": 8 }
    app.select_button = ctk.CTkButton(app.toolbar, text="🖐️ 选择", command=lambda: app.select_tool("select"), **button_kwargs)
    app.select_button.pack(pady=(20, 5), padx=10, fill="x")
    app.pencil_button = ctk.CTkButton(app.toolbar, text="✏️ 画笔", command=lambda: app.select_tool("pencil"), **button_kwargs)
    app.pencil_button.pack(pady=5, padx=10, fill="x")
    app.eraser_button = ctk.CTkButton(app.toolbar, text="🧽 橡皮擦", command=lambda: app.select_tool("eraser"), **button_kwargs)
    app.eraser_button.pack(pady=5, padx=10, fill="x")
    app.fill_button = ctk.CTkButton(app.toolbar, text="🎨 油漆桶", command=lambda: app.select_tool("fill"), **button_kwargs)
    app.fill_button.pack(pady=5, padx=10, fill="x")
    ctk.CTkFrame(app.toolbar, height=2, fg_color="gray40").pack(pady=10, padx=15, fill="x")
    app.line_button = ctk.CTkButton(app.toolbar, text="📏 直线", command=lambda: app.select_tool("line"), **button_kwargs)
    app.line_button.pack(pady=5, padx=10, fill="x")
    app.rect_button = ctk.CTkButton(app.toolbar, text="⬜ 矩形", command=lambda: app.select_tool("rectangle"), **button_kwargs)
    app.rect_button.pack(pady=5, padx=10, fill="x")
    app.circle_button = ctk.CTkButton(app.toolbar, text="⚪ 圆形", command=lambda: app.select_tool("circle"), **button_kwargs)
    app.circle_button.pack(pady=5, padx=10, fill="x")
    app.polygon_button = ctk.CTkButton(app.toolbar, text="⬢ 多边形", command=lambda: app.select_tool("polygon"), **button_kwargs)
    app.polygon_button.pack(pady=5, padx=10, fill="x")
    app.text_button = ctk.CTkButton(app.toolbar, text="T  文本", command=lambda: app.select_tool("text"), **button_kwargs)
    app.text_button.pack(pady=5, padx=10, fill="x")
    
    # --- 曲线与曲面工具分组 ---
    ctk.CTkFrame(app.toolbar, height=2, fg_color="gray40").pack(pady=10, padx=15, fill="x")
    ctk.CTkLabel(app.toolbar, text="曲线工具", font=(ui_font[0], 12, "bold"), text_color="#00BFFF").pack(pady=5)
    
    app.bezier_button = ctk.CTkButton(app.toolbar, text="📐 Bézier曲线", command=lambda: app.select_tool("bezier"), **button_kwargs)
    app.bezier_button.pack(pady=5, padx=10, fill="x")
    app.bspline_button = ctk.CTkButton(app.toolbar, text="🌊 B样条曲线", command=lambda: app.select_tool("bspline"), **button_kwargs)
    app.bspline_button.pack(pady=5, padx=10, fill="x")
    
    ctk.CTkLabel(app.toolbar, text="曲面工具", font=(ui_font[0], 12, "bold"), text_color="#FFD700").pack(pady=(10, 5))
    app.surface_button = ctk.CTkButton(app.toolbar, text="🏔️ Bézier曲面", command=lambda: app.select_tool("bezier_surface"), **button_kwargs)
    app.surface_button.pack(pady=5, padx=10, fill="x")
    
    app.tool_buttons = { 
        "select": app.select_button, "pencil": app.pencil_button, "eraser": app.eraser_button, 
        "fill": app.fill_button, "line": app.line_button, "rectangle": app.rect_button, 
        "circle": app.circle_button, "polygon": app.polygon_button, "text": app.text_button,
        "bezier": app.bezier_button, "bspline": app.bspline_button, 
        "bezier_surface": app.surface_button
    }
    app.active_fg_color = ("#3B8ED0", "#1F6AA5")
    app.active_hover_color = ("#36719F", "#144870")
    
    # 初始化时设置选择工具为高亮状态
    app.select_button.configure(fg_color=app.active_fg_color, hover_color=app.active_hover_color)

    # --- 中间画布 ---
    app.canvas_frame = ctk.CTkFrame(app, corner_radius=0)
    app.canvas_frame.grid(row=0, column=1, sticky="nsew")
    app.canvas_bg_color = getattr(app, "canvas_bg_color", "#1a1a1a")
    
    # 添加带边框的画布容器，使边缘更清晰
    app.canvas_border_frame = ctk.CTkFrame(app.canvas_frame, fg_color="#0a0a0a", corner_radius=0)
    app.canvas_border_frame.pack(fill=BOTH, expand=YES, padx=2, pady=2)
    
    # 修改：将 Canvas 背景色设为深色，以区分画布区域
    app.canvas_bg_color = getattr(app, "canvas_bg_color", "#333333") # 這是画布区域的颜色
    app.viewport_bg_color = "#202020" # 这是画布外的颜色
    
    app.canvas = Canvas(app.canvas_border_frame, bg=app.viewport_bg_color, highlightthickness=0)
    app.canvas.pack(fill=BOTH, expand=YES)

    app.canvas.bind("<B1-Motion>", app.draw)
    app.canvas.bind("<ButtonPress-1>", app.start_drawing)
    app.canvas.bind("<ButtonRelease-1>", app.stop_drawing)
    app.canvas.bind("<Motion>", app.on_mouse_move)
    app.canvas.bind("<Double-Button-1>", app.handle_double_click)
    app.canvas.bind("<MouseWheel>", app.on_canvas_mousewheel)  # Windows 滚轮
    app.canvas.bind("<Button-4>", app.on_canvas_mousewheel)    # Linux 滚轮上
    app.canvas.bind("<Button-5>", app.on_canvas_mousewheel)    # Linux 滚轮下
    
    # 空格+左键拖动画布的事件绑定
    app.bind("<KeyPress-space>", app.on_space_press)
    app.bind("<KeyRelease-space>", app.on_space_release)
    app.bind("<Delete>", app.delete_selection)

    # --- 画布下方的缩放工具条 ---
    app.zoom_toolbar = ctk.CTkFrame(app.canvas_frame, fg_color="transparent", height=40)
    app.zoom_toolbar.pack(side="bottom", fill="x", padx=5, pady=5)
    app.zoom_toolbar.grid_propagate(False)
    
    # 缩小按钮
    ctk.CTkButton(app.zoom_toolbar, text="−", width=35, command=app.zoom_out).pack(side="left", padx=2)
    
    # 缩放百分比标签
    app.zoom_label = ctk.CTkLabel(app.zoom_toolbar, text="100%", width=60, fg_color=("gray80", "gray20"))
    app.zoom_label.pack(side="left", padx=5)
    
    # 缩放滑块
    app.zoom_slider = ctk.CTkSlider(
        app.zoom_toolbar, 
        from_=10, 
        to=500, 
        number_of_steps=98,
        command=app.on_zoom_slider_change
    )
    app.zoom_slider.set(100)
    app.zoom_slider.pack(side="left", fill="x", expand=True, padx=5)
    
    # 放大按钮
    ctk.CTkButton(app.zoom_toolbar, text="＋", width=35, command=app.zoom_in).pack(side="left", padx=2)
    
    # 重置缩放按钮
    ctk.CTkButton(app.zoom_toolbar, text="重置", width=60, command=app.reset_zoom).pack(side="left", padx=2)

    # --- 右侧面板Tab视图 ---
    app.right_panel_container = ctk.CTkFrame(app, width=250, corner_radius=0)
    app.right_panel_container.grid(row=0, column=2, sticky="ns")
    app.right_panel_container.grid_rowconfigure(0, weight=1)
    app.right_panel_container.grid_columnconfigure(0, weight=1)

    app.tab_view = ctk.CTkTabview(app.right_panel_container)
    app.tab_view.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    app.options_tab = app.tab_view.add("工具选项")
    app.layers_tab = app.tab_view.add("图层")

    # --- 工具选项Tab ---
    app.options_panel = ctk.CTkScrollableFrame(app.options_tab, corner_radius=0)
    app.options_panel.pack(fill="both", expand=True)

    # 为每个功能模块创建容器框架，便于动态调整顺序
    
    # 颜色选择模块
    app.color_section = ctk.CTkFrame(app.options_panel, fg_color="transparent")
    color_label = ctk.CTkLabel(app.color_section, text="颜色", font=ui_font)
    color_label.pack(pady=(20, 0))
    app.color_frame = ctk.CTkFrame(app.color_section, fg_color="transparent")
    app.color_frame.pack(pady=5, padx=10)
    app.stroke_color_button = ctk.CTkButton(app.color_frame, text="边框", command=app.choose_stroke_color, font=ui_font, width=90)
    app.stroke_color_button.grid(row=0, column=0, padx=5)
    app.stroke_color_preview = ctk.CTkFrame(app.color_frame, width=30, height=30, fg_color=getattr(app, "current_color", "#FFFFFF"), corner_radius=5)
    app.stroke_color_preview.grid(row=0, column=1)
    app.fill_color_button = ctk.CTkButton(app.color_frame, text="填充", command=app.choose_fill_color, font=ui_font, width=90)
    app.fill_color_button.grid(row=1, column=0, padx=5, pady=5)
    app.fill_color_preview = ctk.CTkFrame(app.color_frame, width=30, height=30, fg_color=getattr(app, "current_fill_color", None) or app.canvas_bg_color, corner_radius=5, border_width=1, border_color="gray50")
    app.fill_color_preview.grid(row=1, column=1)
    app.color_section.pack(fill="x", padx=10)

    # 笔刷大小模块
    app.brush_section = ctk.CTkFrame(app.options_panel, fg_color="transparent")
    brush_label = ctk.CTkLabel(app.brush_section, text="画笔/边框大小", font=ui_font)
    brush_label.pack(pady=(20, 0))
    app.brush_size_slider = ctk.CTkSlider(app.brush_section, from_=1, to=100, command=app.set_brush_size)
    app.brush_size_slider.set(getattr(app, "brush_size", 5))
    app.brush_size_slider.pack(pady=10, padx=20, fill="x")
    app.brush_preview_canvas = Canvas(app.brush_section, width=60, height=60, bg=app.options_panel.cget("fg_color")[1], highlightthickness=0)
    app.brush_preview_canvas.pack(pady=5)
    try:
        app.update_brush_preview()
    except Exception:
        pass
    app.brush_section.pack(fill="x", padx=10)

    # 橡皮擦模式模块
    app.eraser_section = ctk.CTkFrame(app.options_panel, fg_color="transparent")
    app.eraser_mode_label = ctk.CTkLabel(app.eraser_section, text="橡皮擦模式", font=ui_font)
    app.eraser_mode_label.pack(pady=(20, 0))
    app.eraser_mode_switch = ctk.CTkSegmentedButton(app.eraser_section, values=["局部", "对象"], command=app.set_eraser_mode, font=ui_font)
    try:
        app.eraser_mode_switch.set(getattr(app, "eraser_mode", "局部"))
    except Exception:
        pass
    app.eraser_mode_switch.pack(pady=10, padx=20, fill="x")
    app.eraser_section.pack(fill="x", padx=10)
    app.eraser_section.pack_forget()  # 默认隐藏

    # 分隔线
    app.separator1 = ctk.CTkFrame(app.options_panel, height=2, fg_color="gray40")
    app.separator1.pack(pady=20, padx=15, fill="x")

    # 绘图模式模块
    app.drawing_mode_section = ctk.CTkFrame(app.options_panel, fg_color="transparent")
    mode_label = ctk.CTkLabel(app.drawing_mode_section, text="绘图模式", font=ui_font)
    mode_label.pack(pady=(20, 0))
    app.drawing_mode_switch = ctk.CTkSegmentedButton(
        app.drawing_mode_section,
        values=["系统函数库", "光栅化算法"],
        command=app.set_drawing_mode,
        font=ui_font
    )
    app.drawing_mode_switch.set(getattr(app, "drawing_mode", "系统函数库"))
    app.drawing_mode_switch.pack(pady=10, padx=20, fill="x")

    app.mode_info_label = ctk.CTkLabel(
        app.drawing_mode_section,
        text="当前：使用Canvas内置函数\n(直线、圆形、矩形)",
        text_color="gray70",
        font=(ui_font[0], 10)
    )
    app.mode_info_label.pack(pady=(0, 10), padx=10)

    # 算法选择器（仅在光栅化模式可见）
    app.algo_label = ctk.CTkLabel(app.drawing_mode_section, text="光栅化算法选择", font=ui_font)
    app.algo_label.pack(pady=(15, 5), padx=10)
    app.algorithm_selector = ctk.CTkOptionMenu(
        app.drawing_mode_section,
        values=["Bresenham", "Midpoint", "DDA"],
        command=app.set_rasterization_algorithm,
        font=ui_font
    )
    app.algorithm_selector.set(getattr(app, "rasterization_algorithm", "Bresenham"))
    app.algorithm_selector.pack(pady=5, padx=10, fill="x")
    app.algorithm_selector.pack_forget()
    app.algo_label.pack_forget()  # 默认隐藏标签
    app.drawing_mode_section.pack(fill="x", padx=10)

    # 分隔线
    app.separator2 = ctk.CTkFrame(app.options_panel, height=2, fg_color="gray40")
    app.separator2.pack(pady=20, padx=15, fill="x")
    
    # 曲线和曲面工具选项模块
    app.curve_surface_section = ctk.CTkFrame(app.options_panel, fg_color="transparent")
    curve_label = ctk.CTkLabel(app.curve_surface_section, text="曲线/曲面选项", font=ui_font)
    curve_label.pack(pady=(10, 5))
    
    # 完成曲线按钮
    app.finish_curve_button = ctk.CTkButton(
        app.curve_surface_section,
        text="✓ 完成曲线",
        command=lambda: app.finish_curve() if app.current_tool in ["bezier", "bspline"] else None,
        font=ui_font,
        fg_color="#27AE60",
        hover_color="#229954"
    )
    app.finish_curve_button.pack(pady=5, padx=10, fill="x")
    
    # 切换曲面显示模式按钮
    app.toggle_surface_mode_button = ctk.CTkButton(
        app.curve_surface_section,
        text="切换显示模式",
        command=app.toggle_surface_display_mode,
        font=ui_font,
        fg_color="#3498DB",
        hover_color="#2E86C1"
    )
    app.toggle_surface_mode_button.pack(pady=5, padx=10, fill="x")
    
    # 完成曲面按钮
    app.finish_surface_button = ctk.CTkButton(
        app.curve_surface_section,
        text="✓ 完成曲面",
        command=app.finish_surface,
        font=ui_font,
        fg_color="#27AE60",
        hover_color="#229954"
    )
    app.finish_surface_button.pack(pady=5, padx=10, fill="x")
    
    # 曲线/曲面提示标签
    app.curve_hint_label = ctk.CTkLabel(
        app.curve_surface_section,
        text="",
        text_color="gray70",
        font=(ui_font[0], 10),
        wraplength=200
    )
    app.curve_hint_label.pack(pady=5, padx=10)
    app.curve_surface_section.pack(fill="x", padx=10)
    app.curve_surface_section.pack_forget()  # 默认隐藏

    # 分隔线
    app.separator3 = ctk.CTkFrame(app.options_panel, height=2, fg_color="gray40")
    app.separator3.pack(pady=20, padx=15, fill="x")
    
    # 操作按钮模块
    app.action_section = ctk.CTkFrame(app.options_panel, fg_color="transparent")
    app.undo_button = ctk.CTkButton(app.action_section, text="撤销 (Ctrl+Z)", command=app.undo_last_action, font=ui_font)
    app.undo_button.pack(pady=10, fill="x", padx=10)
    app.clear_button = ctk.CTkButton(app.action_section, text="清空画布", command=app.clear_canvas, font=ui_font, fg_color="#C0392B", hover_color="#E74C3C")
    app.clear_button.pack(pady=10, fill="x", padx=10)
    app.save_button = ctk.CTkButton(app.action_section, text="导出为图片", command=app.export_as_image, font=ui_font)
    app.save_button.pack(pady=10, fill="x", padx=10)
    app.action_section.pack(fill="x", padx=10)

    # --- 图层Tab ---
    app.layer_panel = ctk.CTkFrame(app.layers_tab, corner_radius=0, fg_color="transparent")
    app.layer_panel.pack(fill="both", expand=True)
    app.layer_panel.grid_columnconfigure(0, weight=1)
    app.layer_panel.grid_rowconfigure(1, weight=1)

    ctk.CTkLabel(app.layer_panel, text="图层", font=(ui_font[0], 18, "bold")).grid(row=0, column=0, pady=10, sticky="w", padx=10)
    app.layer_list_frame = ctk.CTkScrollableFrame(app.layer_panel, label_text="")
    app.layer_list_frame.grid(row=1, column=0, sticky="nsew", padx=5)

    layer_controls_frame = ctk.CTkFrame(app.layer_panel)
    layer_controls_frame.grid(row=2, column=0, sticky="ew", pady=5, padx=5)
    layer_controls_frame.grid_columnconfigure((0,1,2,3,4), weight=1)
    btn_font = (ui_font[0], 18)
    app.add_layer_btn = ctk.CTkButton(layer_controls_frame, text="➕", command=app.add_new_layer, font=btn_font, width=40)
    app.add_layer_btn.grid(row=0, column=0, padx=2, pady=5)
    app.dup_layer_btn = ctk.CTkButton(layer_controls_frame, text="📋", command=app.duplicate_selected_layer, font=btn_font, width=40)
    app.dup_layer_btn.grid(row=0, column=1, padx=2, pady=5)
    app.del_layer_btn = ctk.CTkButton(layer_controls_frame, text="🗑️", command=app.delete_selected_layer, font=btn_font, width=40)
    app.del_layer_btn.grid(row=0, column=2, padx=2, pady=5)
    app.move_up_btn = ctk.CTkButton(layer_controls_frame, text="▲", command=app.move_layer_up, font=btn_font, width=40)
    app.move_up_btn.grid(row=0, column=3, padx=2, pady=5)
    app.move_down_btn = ctk.CTkButton(layer_controls_frame, text="▼", command=app.move_layer_down, font=btn_font, width=40)
    app.move_down_btn.grid(row=0, column=4, padx=2, pady=5)
    Tooltip(app.add_layer_btn, "新建图层", delay=3000)
    Tooltip(app.dup_layer_btn, "复制图层", delay=3000)
    Tooltip(app.del_layer_btn, "删除图层", delay=3000)
    Tooltip(app.move_up_btn, "上移图层", delay=3000)
    Tooltip(app.move_down_btn, "下移图层", delay=3000)

    # 绑定快捷键等初始化操作应由 app 本身执行。
    return