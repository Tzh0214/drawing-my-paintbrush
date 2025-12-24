from tkinter import simpledialog, font
import customtkinter as ctk

class TextToolDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("文本工具")
        
        ctk.CTkLabel(master, text="文本内容:").grid(row=0, sticky="w", padx=5, pady=5)
        self.text_entry = ctk.CTkEntry(master, width=250)
        self.text_entry.grid(row=1, padx=5, pady=5)
        self.text_entry.focus_set()

        ctk.CTkLabel(master, text="字体:").grid(row=2, sticky="w", padx=5, pady=5)
        available_fonts = sorted([f for f in font.families() if not f.startswith('@')])
        self.font_var = ctk.StringVar(value="Arial")
        self.font_menu = ctk.CTkOptionMenu(master, variable=self.font_var, values=available_fonts)
        self.font_menu.grid(row=3, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(master, text="字号:").grid(row=4, sticky="w", padx=5, pady=5)
        self.size_var = ctk.StringVar(value="24")
        self.size_entry = ctk.CTkEntry(master, textvariable=self.size_var, width=80)
        self.size_entry.grid(row=5, padx=5, pady=5, sticky="w")
        
        return self.text_entry

    def apply(self):
        text = self.text_entry.get()
        font_family = self.font_var.get()
        try:
            font_size = int(self.size_var.get())
        except ValueError:
            font_size = 24
        
        if text:
            self.result = (text, font_family, font_size)