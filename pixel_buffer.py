from PIL import Image, ImageDraw, ImageTk, ImageEnhance

class PixelBuffer:
    """封装用于和 Canvas 同步的 PIL 像素缓冲。

    用法：在 DrawingApp 中创建：
        self.pixel_buffer = PixelBuffer(self.canvas, self.canvas_bg_color)
        self.pixel_buffer.ensure()

    然后使用：
        self.pixel_buffer.putpixel(x, y, rgba)
        self.pixel_buffer.draw_line(coords, rgba, width)
        self.pixel_buffer.composite_tmp(tmp_image)  # 把 tmp 合成到主缓冲并一次性绘回 Canvas
    """
    def __init__(self, canvas, canvas_bg_color="#333333"):
        self.canvas = canvas
        self.canvas_bg_color = canvas_bg_color
        self.image = None
        self.draw = None
        self._image_refs = []

    @staticmethod
    def hex_to_rgba(hex_color):
        if not hex_color or hex_color == "transparent":
            return (0, 0, 0, 0)
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r, g, b, 255)
        elif len(hex_color) == 8:
            r, g, b, a = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
            return (r, g, b, a)
        else:
            return (0, 0, 0, 255)

    def ensure(self):
        try:
            width = max(1, int(self.canvas.winfo_width() or 800))
            height = max(1, int(self.canvas.winfo_height() or 600))
        except Exception:
            width, height = 800, 600

        if self.image is None or self.image.size != (width, height):
            try:
                bg_rgba = self.hex_to_rgba(self.canvas_bg_color)
            except Exception:
                bg_rgba = (51, 51, 51, 255)
            img = Image.new("RGBA", (width, height), bg_rgba)
            self.image = img
            self.draw = ImageDraw.Draw(self.image)

    def putpixel(self, x, y, rgba):
        if self.image is None:
            self.ensure()
        try:
            self.image.putpixel((int(x), int(y)), rgba)
        except Exception:
            pass
    def draw_line(self, coords, rgba, width=1):
        if self.draw is None:
            self.ensure()
        try:
            self.draw.line(coords, fill=rgba, width=width)
        except Exception:
            pass

    def draw_rectangle(self, x1, y1, x2, y2, rgba):
        if self.draw is None:
            self.ensure()
        try:
            self.draw.rectangle([x1, y1, x2, y2], fill=rgba)
        except Exception:
            pass

    def composite_tmp(self, tmp_image, tags=None):
        """将 tmp_image 合成到主缓冲并一次性绘回 Canvas（保持引用避免 GC）。

        参数:
            tmp_image: PIL.Image (RGBA)
            tags: 可选的 Canvas 标签序列或单个标签，用于合成后的图像项
        返回:
            canvas image id 或 None
        """
        if self.image is None:
            self.ensure()
        try:
            try:
                self.image = Image.alpha_composite(self.image, tmp_image)
            except Exception:
                self.image.paste(tmp_image, (0, 0), tmp_image)
            self.draw = ImageDraw.Draw(self.image)

            tk_img = ImageTk.PhotoImage(self.image)
            image_tag = f"pixelbuffer_image"
            canvas_tags = ()
            if tags:
                if isinstance(tags, (list, tuple)):
                    canvas_tags = tuple(tags) + (image_tag,)
                else:
                    canvas_tags = (tags, image_tag)

            # 在 Canvas 原点绘制整张图像
            if canvas_tags:
                img_id = self.canvas.create_image(0, 0, image=tk_img, anchor='nw', tags=canvas_tags)
            else:
                img_id = self.canvas.create_image(0, 0, image=tk_img, anchor='nw', tags=(image_tag,))

            self._image_refs.append(tk_img)
            return img_id
        except Exception:
            return None

    def draw_item(self, item_type: str, coords: list, options: dict):
        # 提供给 app_core 使用的兼容封装
        fill = options.get('fill') or options.get('outline') or "#000000"
        outline = options.get('outline')
        try:
            width = int(float(options.get('width') or 1))
        except Exception:
            width = 1
        fill_rgba = self.hex_to_rgba(fill) if fill else None
        outline_rgba = self.hex_to_rgba(outline) if outline else None

        try:
            if item_type == 'line':
                self.draw_line(coords, fill_rgba or outline_rgba or (0,0,0,255), width=width)
            elif item_type == 'rectangle':
                if fill_rgba:
                    x1, y1, x2, y2 = coords[:4]
                    self.draw_rectangle(x1, y1, x2, y2, fill_rgba)
                elif outline_rgba:
                    x1, y1, x2, y2 = coords[:4]
                    self.draw_line([x1, y1, x2, y2], outline_rgba, width=width)
            elif item_type == 'oval':
                if fill_rgba:
                    x1, y1, x2, y2 = coords[:4]
                    self.draw.ellipse([x1, y1, x2, y2], fill=fill_rgba)
                elif outline_rgba:
                    x1, y1, x2, y2 = coords[:4]
                    self.draw.ellipse([x1, y1, x2, y2], outline=outline_rgba)
            elif item_type == 'polygon':
                if fill_rgba:
                    self.draw.polygon(coords, fill=fill_rgba)
                else:
                    self.draw.line(coords + coords[:2], fill=outline_rgba or fill_rgba or (0,0,0,255), width=width)
        except Exception:
            pass
