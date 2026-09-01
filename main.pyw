import os
import sys
import json
import time
import random
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, colorchooser
from tkinter import ttk
from datetime import datetime
import re

try:
    import winreg
except ImportError:
    winreg = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "data.json")

DEFAULT_SETTINGS = {
    "ignore_indent": True,
    "search_mode": "smart_tolerate",
    "replace_mode": "add_below",
    "startup_mode": "recent_file",
    "theme_mode": "system",
    "custom_colors": {
        "bg": "#FFFFFF",
        "fg": "#000000",
        "button_bg": "#E0E0E0",
        "button_fg": "#000000",
        "entry_bg": "#FFFFFF",
        "entry_fg": "#000000",
        "listbox_bg": "#FFFFFF",
        "listbox_fg": "#000000",
    }
}

def get_system_theme():
    if winreg:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value == 1 else "dark"
        except:
            pass
    return "light"

def load_data():
    data = {
        "settings": DEFAULT_SETTINGS.copy(),
        "last_manual_file": "",
        "history": []
    }
    if not os.path.exists(DATA_FILE):
        return data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            return data
        try:
            data = json.loads(raw)
            if "settings" not in data:
                data["settings"] = DEFAULT_SETTINGS.copy()
            else:
                for key in DEFAULT_SETTINGS:
                    if key not in data["settings"]:
                        data["settings"][key] = DEFAULT_SETTINGS[key]
            if "last_manual_file" not in data:
                data["last_manual_file"] = ""
            if "history" not in data:
                data["history"] = []
            return data
        except json.JSONDecodeError:
            history = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    history.append(rec)
                except:
                    continue
            data["history"] = history
            save_data(data)
            messagebox.showwarning("数据已迁移", "检测到旧版数据格式，已自动迁移为新的 JSON 格式。")
            return data
    except Exception as e:
        messagebox.showerror("数据加载失败", f"无法读取 data.json：{e}\n将使用默认设置。")
        return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def apply_theme(root, settings):
    theme_mode = settings["theme_mode"]
    if theme_mode == "system":
        sys_theme = get_system_theme()
        if sys_theme == "dark":
            colors = {
                "bg": "#1E1E1E", "fg": "#FFFFFF",
                "button_bg": "#333333", "button_fg": "#FFFFFF",
                "entry_bg": "#2D2D2D", "entry_fg": "#FFFFFF",
                "listbox_bg": "#2D2D2D", "listbox_fg": "#FFFFFF",
            }
        else:
            colors = {
                "bg": "#FFFFFF", "fg": "#000000",
                "button_bg": "#E0E0E0", "button_fg": "#000000",
                "entry_bg": "#FFFFFF", "entry_fg": "#000000",
                "listbox_bg": "#FFFFFF", "listbox_fg": "#000000",
            }
    elif theme_mode == "light":
        colors = {
            "bg": "#FFFFFF", "fg": "#000000",
            "button_bg": "#E0E0E0", "button_fg": "#000000",
            "entry_bg": "#FFFFFF", "entry_fg": "#000000",
            "listbox_bg": "#FFFFFF", "listbox_fg": "#000000",
        }
    elif theme_mode == "dark":
        colors = {
            "bg": "#1E1E1E", "fg": "#FFFFFF",
            "button_bg": "#333333", "button_fg": "#FFFFFF",
            "entry_bg": "#2D2D2D", "entry_fg": "#FFFFFF",
            "listbox_bg": "#2D2D2D", "listbox_fg": "#FFFFFF",
        }
    else:  # custom
        colors = settings["custom_colors"]

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure(".", background=colors["bg"], foreground=colors["fg"])
    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
    style.configure("TButton", background=colors["button_bg"], foreground=colors["button_fg"])
    style.map("TButton",
              background=[("active", colors["button_bg"])],
              foreground=[("active", colors["button_fg"])])
    style.configure("TEntry", fieldbackground=colors["entry_bg"], foreground=colors["entry_fg"])
    style.configure("TCheckbutton", background=colors["bg"], foreground=colors["fg"])
    style.configure("TRadiobutton", background=colors["bg"], foreground=colors["fg"])
    style.configure("TLabelFrame", background=colors["bg"], foreground=colors["fg"])
    style.configure("TScrollbar", background=colors["button_bg"], troughcolor=colors["bg"])

    def configure_widget(widget):
        widget_class = widget.winfo_class()
        if widget_class in ('Text', 'Listbox', 'Entry', 'Label', 'Button', 'Checkbutton', 'Radiobutton'):
            if widget_class == 'Text' or widget_class == 'Listbox' or widget_class == 'Entry':
                widget.config(bg=colors["entry_bg"], fg=colors["entry_fg"])
            elif widget_class == 'Label' or widget_class == 'Checkbutton' or widget_class == 'Radiobutton':
                widget.config(bg=colors["bg"], fg=colors["fg"])
            elif widget_class == 'Button':
                widget.config(bg=colors["button_bg"], fg=colors["button_fg"],
                              activebackground=colors["button_bg"], activeforeground=colors["button_fg"])
        for child in widget.winfo_children():
            configure_widget(child)

    configure_widget(root)

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, data, on_save_callback):
        super().__init__(parent)
        self.parent = parent
        self.data = data
        self.on_save_callback = on_save_callback
        self.title("设置")
        self.geometry("600x700")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # 先应用主题，然后获取背景色用于 Canvas
        apply_theme(self, self.data["settings"])
        self._mousewheel_binding = None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.create_widgets()

    def close(self):
        if self._mousewheel_binding:
            try:
                self.unbind_all("<MouseWheel>", self._mousewheel_binding)
            except:
                pass
        self.destroy()

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建 Canvas，背景色与主题一致
        canvas = tk.Canvas(main_frame, highlightthickness=0, bg=self.cget("bg"))
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 内部框架，所有控件都放在这里
        inner_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor=tk.NW)

        # 鼠标滚轮绑定
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._mousewheel_binding = canvas.bind_all("<MouseWheel>", on_mousewheel)

        # 当内部框架大小改变时更新滚动区域和宽度
        def update_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=canvas.winfo_width())
        inner_frame.bind("<Configure>", update_scrollregion)

        # 当 Canvas 大小改变时也更新内部框架宽度
        def on_canvas_configure(event):
            canvas.itemconfigure(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)

        # ---- 以下为原所有设置控件，放在 inner_frame 中 ----
        basic_frame = ttk.LabelFrame(inner_frame, text="搜索选项", padding=10)
        basic_frame.pack(fill=tk.X, padx=10, pady=5)

        self.ignore_indent_var = tk.BooleanVar(value=self.data["settings"]["ignore_indent"])
        ttk.Checkbutton(basic_frame, text="忽略整体缩进差异（推荐用于代码）",
                        variable=self.ignore_indent_var).pack(anchor=tk.W)

        ttk.Label(basic_frame, text="搜索匹配模式：", font=('', 9, 'bold')).pack(anchor=tk.W, pady=(10,0))
        self.search_mode_var = tk.StringVar(value=self.data["settings"]["search_mode"])
        modes = [
            ("严格匹配", "strict"),
            ("智能容忍注释缺失（默认）", "smart_tolerate"),
            ("完全忽略注释", "ignore_all_comments"),
            ("忽略普通注释但保留文档字符串", "keep_docstrings")
        ]
        for text, value in modes:
            ttk.Radiobutton(basic_frame, text=text, variable=self.search_mode_var, value=value).pack(anchor=tk.W, padx=20)

        ttk.Label(basic_frame, text="替换注释处理模式：", font=('', 9, 'bold')).pack(anchor=tk.W, pady=(10,0))
        self.replace_mode_var = tk.StringVar(value=self.data["settings"]["replace_mode"])
        rmodes = [
            ("添加在其他注释下方（默认）", "add_below"),
            ("随机位置", "random_place"),
            ("替换注释（整体替换）", "replace_all")
        ]
        for text, value in rmodes:
            ttk.Radiobutton(basic_frame, text=text, variable=self.replace_mode_var, value=value).pack(anchor=tk.W, padx=20)

        startup_frame = ttk.LabelFrame(inner_frame, text="启动时文件恢复", padding=10)
        startup_frame.pack(fill=tk.X, padx=10, pady=5)
        self.startup_mode_var = tk.StringVar(value=self.data["settings"]["startup_mode"])
        ttk.Radiobutton(startup_frame, text="优先恢复最近一次操作的文件（默认）",
                        variable=self.startup_mode_var, value="recent_file").pack(anchor=tk.W)
        ttk.Radiobutton(startup_frame, text="始终恢复上次手动选择的文件",
                        variable=self.startup_mode_var, value="last_manual").pack(anchor=tk.W)

        self.personalize_frame = ttk.LabelFrame(inner_frame, text="个性化", padding=10)
        self.personalize_frame.pack(fill=tk.X, padx=10, pady=5)
        self.personalize_visible = False
        self.personalize_button = ttk.Button(self.personalize_frame, text="▼ 展开个性化设置",
                                            command=self.toggle_personalize)
        self.personalize_button.pack(anchor=tk.W)
        self.personalize_content = ttk.Frame(self.personalize_frame)

        ttk.Button(inner_frame, text="保存", command=self.save).pack(pady=10)

        # 强制刷新 Canvas，确保内容立即显示
        self.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(canvas_window, width=canvas.winfo_width())

    def toggle_personalize(self):
        if self.personalize_visible:
            self.personalize_content.pack_forget()
            self.personalize_button.config(text="▼ 展开个性化设置")
            self.personalize_visible = False
        else:
            self._build_personalize_content()
            self.personalize_content.pack(fill=tk.X, pady=5)
            self.personalize_button.config(text="▲ 收起个性化设置")
            self.personalize_visible = True

    def _build_personalize_content(self):
        for child in self.personalize_content.winfo_children():
            child.destroy()

        ttk.Label(self.personalize_content, text="主题模式：", font=('', 9, 'bold')).pack(anchor=tk.W, pady=(5,0))
        self.theme_mode_var = tk.StringVar(value=self.data["settings"]["theme_mode"])
        theme_modes = [
            ("跟随系统", "system"),
            ("浅色模式", "light"),
            ("深色模式", "dark"),
            ("自定义模式", "custom")
        ]
        for text, value in theme_modes:
            ttk.Radiobutton(self.personalize_content, text=text, variable=self.theme_mode_var, value=value,
                            command=self.on_theme_mode_change).pack(anchor=tk.W, padx=20)

        self.custom_color_visible = False
        self.custom_color_button = ttk.Button(self.personalize_content, text="▼ 展开自定义颜色",
                                             command=self.toggle_custom_color)
        self.custom_color_button.pack(anchor=tk.W, pady=5)
        self.custom_color_content = ttk.Frame(self.personalize_content)
        self.on_theme_mode_change()

    def on_theme_mode_change(self):
        if self.theme_mode_var.get() == "custom":
            self.custom_color_button.config(state=tk.NORMAL)
        else:
            self.custom_color_button.config(state=tk.DISABLED)
            if self.custom_color_visible:
                self.toggle_custom_color()

    def toggle_custom_color(self):
        if self.custom_color_visible:
            self.custom_color_content.pack_forget()
            self.custom_color_button.config(text="▼ 展开自定义颜色")
            self.custom_color_visible = False
        else:
            self._build_custom_color_content()
            self.custom_color_content.pack(fill=tk.X, pady=5)
            self.custom_color_button.config(text="▲ 收起自定义颜色")
            self.custom_color_visible = True

    def _build_custom_color_content(self):
        for child in self.custom_color_content.winfo_children():
            child.destroy()

        color_options = [
            ("窗口背景色", "bg"),
            ("文字颜色", "fg"),
            ("按钮背景色", "button_bg"),
            ("按钮文字颜色", "button_fg"),
            ("输入框背景色", "entry_bg"),
            ("输入框文字颜色", "entry_fg"),
            ("列表框背景色", "listbox_bg"),
            ("列表框文字颜色", "listbox_fg"),
        ]

        self.color_vars = {}
        for label, key in color_options:
            row = ttk.Frame(self.custom_color_content)
            row.pack(fill=tk.X, padx=10, pady=2)
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            var = tk.StringVar(value=self.data["settings"]["custom_colors"].get(key, "#FFFFFF"))
            self.color_vars[key] = var
            entry = ttk.Entry(row, textvariable=var, width=12)
            entry.pack(side=tk.LEFT, padx=5)
            ttk.Button(row, text="选择", command=lambda k=key: self.choose_color(k)).pack(side=tk.LEFT)

    def choose_color(self, key):
        initial = self.color_vars[key].get()
        color = colorchooser.askcolor(initial, title="选择颜色")
        if color and color[1]:
            self.color_vars[key].set(color[1])

    def save(self):
        self.data["settings"]["ignore_indent"] = self.ignore_indent_var.get()
        self.data["settings"]["search_mode"] = self.search_mode_var.get()
        self.data["settings"]["replace_mode"] = self.replace_mode_var.get()
        self.data["settings"]["startup_mode"] = self.startup_mode_var.get()
        if hasattr(self, "theme_mode_var"):
            self.data["settings"]["theme_mode"] = self.theme_mode_var.get()
        if hasattr(self, "color_vars"):
            for key, var in self.color_vars.items():
                self.data["settings"]["custom_colors"][key] = var.get()
        save_data(self.data)
        self.on_save_callback()
        self.close()


class ReplaceSuccessDialog(tk.Toplevel):
    """替换成功提示对话框，包含“完成”和“取消”按钮"""
    def __init__(self, parent, has_remaining_matches, on_complete_callback):
        # 兼容传入 MainApp 或 Tk 实例
        if isinstance(parent, tk.Tk) or isinstance(parent, tk.Toplevel):
            actual_parent = parent
        else:
            actual_parent = parent.root  # 假设是 MainApp

        super().__init__(actual_parent)
        self.parent = actual_parent
        self.on_complete_callback = on_complete_callback
        self.title("替换成功")
        self.geometry("400x200")
        self.resizable(False, False)
        self.transient(actual_parent)
        self.grab_set()

        # 手动设置背景色
        bg = actual_parent.cget("bg")
        self.configure(bg=bg)

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="替换成功！", font=('', 11, 'bold')).pack(pady=(0, 10))

        if has_remaining_matches:
            detail = "还有剩余匹配项。\n点击“完成”将清空替换输入框，保留查找输入框。"
        else:
            detail = "没有剩余匹配项。\n点击“完成”将清空查找和替换输入框。"
        ttk.Label(main_frame, text=detail, justify=tk.CENTER).pack(pady=(0, 15))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack()
        ttk.Button(btn_frame, text="完成", command=self._on_complete).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.LEFT, padx=10)

    def _on_complete(self):
        self.on_complete_callback()
        self.destroy()

    def _on_cancel(self):
        self.destroy()


class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("片段替换工具")
        self.root.geometry("900x750")
        self.root.minsize(800, 600)

        self.current_file = None
        self.file_content = None
        self.line_offsets = []
        self.matches = []
        self.last_matches = []  # 新增备份
        self.selected_match_index = None
        self.has_find_result = False

        self.data = load_data()
        apply_theme(root, self.data["settings"])

        self.create_widgets()
        self.restore_last_file()
        self.refresh_status()

    def restore_last_file(self):
        mode = self.data["settings"]["startup_mode"]
        last_manual = self.data.get("last_manual_file", "")
        history = self.data.get("history", [])
        candidate = None
        if mode == "recent_file":
            for rec in reversed(history):
                if rec and rec.get("file_path"):
                    candidate = rec["file_path"]
                    break
            if not candidate or not os.path.isfile(candidate):
                candidate = last_manual
        else:
            candidate = last_manual
        if candidate and os.path.isfile(candidate):
            try:
                self.load_file(candidate, show_message=False)
            except:
                self.current_file = None
                self.file_content = None

    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="打开文件", command=self.open_file).pack(side=tk.LEFT, padx=5)
        self.file_label = ttk.Label(top_frame, text="未选择文件", foreground="blue")
        self.file_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="设置", command=self.open_settings).pack(side=tk.RIGHT, padx=5)

        mid_frame = ttk.Frame(self.root, padding=5)
        mid_frame.pack(fill=tk.BOTH, expand=True)
        mid_frame.grid_rowconfigure(1, weight=1)
        mid_frame.grid_rowconfigure(3, weight=1)
        mid_frame.grid_columnconfigure(0, weight=1)

        # 查找输入框行：标签 + 清空按钮
        find_label_frame = ttk.Frame(mid_frame)
        find_label_frame.grid(row=0, column=0, sticky=tk.W)
        ttk.Label(find_label_frame, text="查找片段（支持多行）：").pack(side=tk.LEFT)
        ttk.Button(find_label_frame, text="清空", command=lambda: self.find_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=10)

        self.find_text = scrolledtext.ScrolledText(mid_frame, width=80, height=5, wrap=tk.NONE)
        self.find_text.grid(row=1, column=0, padx=5, pady=5, sticky=tk.NSEW)

        # 替换输入框行：标签 + 清空按钮
        replace_label_frame = ttk.Frame(mid_frame)
        replace_label_frame.grid(row=2, column=0, sticky=tk.W)
        ttk.Label(replace_label_frame, text="替换为（支持多行，可为空）：").pack(side=tk.LEFT)
        ttk.Button(replace_label_frame, text="清空", command=lambda: self.replace_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=10)

        self.replace_text = scrolledtext.ScrolledText(mid_frame, width=80, height=5, wrap=tk.NONE)
        self.replace_text.grid(row=3, column=0, padx=5, pady=5, sticky=tk.NSEW)

        btn_frame = ttk.Frame(mid_frame)
        btn_frame.grid(row=4, column=0, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="查找", command=self.find_fragment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="替换选中", command=self.replace_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="替换全部", command=self.replace_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="撤回上次替换", command=self.undo_last).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="撤回指定文件", command=self.undo_specific_file).pack(side=tk.LEFT, padx=5)

        list_frame = ttk.LabelFrame(mid_frame, text="匹配结果", padding=5)
        list_frame.grid(row=5, column=0, padx=5, pady=5, sticky=tk.NSEW)
        self.match_listbox = tk.Listbox(list_frame, height=7, width=90)
        self.match_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.match_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.match_listbox.config(yscrollcommand=scrollbar.set)
        self.match_listbox.bind('<<ListboxSelect>>', self.on_match_select)

        clean_frame = ttk.LabelFrame(mid_frame, text="清理历史记录", padding=5)
        clean_frame.grid(row=6, column=0, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(clean_frame, text="按日期之前：").grid(row=0, column=0, sticky=tk.W)
        self.clean_date_entry = ttk.Entry(clean_frame, width=20)
        self.clean_date_entry.grid(row=0, column=1, padx=5)
        ttk.Button(clean_frame, text="执行", command=self.clean_by_date).grid(row=0, column=2, padx=5)

        ttk.Label(clean_frame, text="按文件路径（删除该文件及之前所有）：").grid(row=1, column=0, sticky=tk.W)
        self.clean_file_entry = ttk.Entry(clean_frame, width=40)
        self.clean_file_entry.grid(row=1, column=1, padx=5)
        ttk.Button(clean_frame, text="执行", command=self.clean_by_file).grid(row=1, column=2, padx=5)

        ttk.Label(clean_frame, text="按大小（如 10MB）：").grid(row=2, column=0, sticky=tk.W)
        self.clean_size_entry = ttk.Entry(clean_frame, width=20)
        self.clean_size_entry.grid(row=2, column=1, padx=5)
        ttk.Button(clean_frame, text="执行", command=self.clean_by_size).grid(row=2, column=2, padx=5)

        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        apply_theme(self.root, self.data["settings"])

    def open_settings(self):
        SettingsDialog(self.root, self.data, self.on_settings_saved)

    def on_settings_saved(self):
        apply_theme(self.root, self.data["settings"])

    def refresh_status(self):
        if self.current_file:
            self.file_label.config(text=self.current_file)
            self.status_var.set(f"当前文件: {os.path.basename(self.current_file)}")
        else:
            self.file_label.config(text="未选择文件")
            self.status_var.set("就绪")

    def load_file(self, file_path, show_message=True):
        try:
            self.file_content = self._get_file_content(file_path)
            self.current_file = file_path
            self._compute_line_offsets()
            self.matches = []
            self.last_matches = []
            self.match_listbox.delete(0, tk.END)
            self.has_find_result = False
            self.refresh_status()
            self.data["last_manual_file"] = file_path
            save_data(self.data)
            # 静默加载，不再弹出提示
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def open_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.load_file(file_path)

    def _get_file_content(self, file_path):
        encodings = ["utf-8-sig", "utf-8", "gbk", "big5", "latin-1"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc, newline="") as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise e
        raise UnicodeDecodeError(f"无法识别文件编码: {file_path}")

    def _write_file_content(self, file_path, content):
        try:
            with open(file_path, "rb") as f:
                raw = f.read(3)
            has_bom = raw == b'\xef\xbb\xbf'
            encoding = "utf-8-sig" if has_bom else "utf-8"
            with open(file_path, "w", encoding=encoding, newline="") as f:
                f.write(content)
        except PermissionError:
            raise PermissionError(f"没有权限写入文件: {file_path}")
        except Exception as e:
            raise e

    def _compute_line_offsets(self):
        self.line_offsets = [0]
        for i, ch in enumerate(self.file_content):
            if ch == '\n':
                self.line_offsets.append(i+1)

    # ----- 查找 -----
    def find_fragment(self):
        if not self.current_file:
            messagebox.showwarning("提示", "请先打开文件")
            return
        fragment = self.find_text.get("1.0", tk.END).rstrip("\n")
        if not fragment:
            messagebox.showwarning("提示", "查找片段不能为空")
            return

        self.matches = []
        self.last_matches = []  # 新增备份
        self.match_listbox.delete(0, tk.END)
        self.has_find_result = False

        ignore_indent = self.data["settings"]["ignore_indent"]
        search_mode = self.data["settings"]["search_mode"]
        file_ext = os.path.splitext(self.current_file)[1].lower()

        if search_mode == "strict":
            matches = self._find_strict(fragment, ignore_indent)
        elif search_mode == "smart_tolerate":
            matches = self._find_smart_tolerate(fragment, ignore_indent, file_ext)
        elif search_mode == "ignore_all_comments":
            matches = self._find_ignore_comments(fragment, ignore_indent, file_ext, keep_docstrings=False)
        elif search_mode == "keep_docstrings":
            matches = self._find_ignore_comments(fragment, ignore_indent, file_ext, keep_docstrings=True)
        else:
            matches = self._find_smart_tolerate(fragment, ignore_indent, file_ext)

        for idx, m in enumerate(matches):
            start, end, parent_path, indent_info = m
            if indent_info:
                first_indent = indent_info[0][0] if indent_info else 0
                indent_level = first_indent // 4
                indent_display = f"缩进 {first_indent}空格 (级别{indent_level})"
            else:
                indent_display = "精确匹配"
            display = f"[{idx+1}] {parent_path} | {indent_display}"
            self.match_listbox.insert(tk.END, display)

        if not matches:
            messagebox.showinfo("结果", "没有找到指定片段。")
            self.status_var.set("未找到匹配")
        else:
            # 去重：基于起始偏移，避免重复匹配同一位置
            seen_starts = set()
            unique_matches = []
            for m in matches:
                if m[0] not in seen_starts:
                    unique_matches.append(m)
                    seen_starts.add(m[0])
            matches = unique_matches

            self.matches = matches.copy()  # 将匹配结果赋值给 self.matches
            self.has_find_result = True
            self.last_matches = self.matches.copy()  # 备份匹配数据
            self.status_var.set(f"找到 {len(self.matches)} 处匹配，请选择一项后替换")
            if len(self.matches) == 1:
                self.match_listbox.selection_set(0)
                self.selected_match_index = 0
            else:
                self.selected_match_index = None

    def _find_strict(self, fragment, ignore_indent):
        if ignore_indent:
            return self._find_relative_indent(fragment, skip_comments=False, keep_docstrings=True)
        else:
            return self._find_exact(fragment)

    def _find_exact(self, fragment):
        matches = []
        content = self.file_content
        start = 0
        while True:
            idx = content.find(fragment, start)
            if idx == -1:
                break
            end = idx + len(fragment)
            parent_path = self._get_parent_path(idx)
            matches.append((idx, end, parent_path, None))
            start = end
        return matches

    def _find_relative_indent(self, fragment, skip_comments=False, keep_docstrings=True):
        file_lines = self.file_content.split('\n')
        if file_lines and file_lines[-1] == '':
            file_lines.pop()
        frag_lines = fragment.split('\n')
        file_ext = os.path.splitext(self.current_file)[1].lower()

        if skip_comments:
            filtered_file_lines = []
            filtered_file_indices = []
            for i, line in enumerate(file_lines):
                ltype = self._classify_line(line, file_ext)
                if ltype == 'comment' or (ltype == 'docstring' and not keep_docstrings):
                    continue
                filtered_file_lines.append(line)
                filtered_file_indices.append(i)
            filtered_frag_lines = []
            for line in frag_lines:
                ltype = self._classify_line(line, file_ext)
                if ltype == 'comment' or (ltype == 'docstring' and not keep_docstrings):
                    continue
                filtered_frag_lines.append(line)
        else:
            filtered_file_lines = file_lines
            filtered_file_indices = list(range(len(file_lines)))
            filtered_frag_lines = frag_lines

        if not filtered_frag_lines:
            return []

        frag_info = []
        non_empty_indents = []
        for line in filtered_frag_lines:
            stripped = line.lstrip(' \t')
            indent = len(line) - len(stripped)
            frag_info.append((indent, stripped))
            if stripped:
                non_empty_indents.append(indent)
        if not non_empty_indents:
            return []
        min_frag_indent = min(non_empty_indents)

        matches = []
        max_start = len(filtered_file_lines) - len(filtered_frag_lines)
        if max_start < 0:
            return []

        for line_start in range(max_start + 1):
            text_match = True
            window_info = []
            for j in range(len(filtered_frag_lines)):
                file_line = filtered_file_lines[line_start + j]
                stripped = file_line.lstrip(' \t')
                indent = len(file_line) - len(stripped)
                window_info.append((indent, stripped))
                if stripped != frag_info[j][1]:
                    text_match = False
                    break
            if not text_match:
                continue

            non_empty_window = [ind for ind, txt in window_info if txt]
            min_window_indent = min(non_empty_window) if non_empty_window else 0

            rel_match = True
            for j in range(len(frag_info)):
                if frag_info[j][1] == '':
                    if window_info[j][1] != '':
                        rel_match = False
                        break
                else:
                    frag_rel = frag_info[j][0] - min_frag_indent
                    win_rel = window_info[j][0] - min_window_indent
                    if frag_rel != win_rel:
                        rel_match = False
                        break
            if not rel_match:
                continue

            first_file_idx = filtered_file_indices[line_start]
            last_file_idx = filtered_file_indices[line_start + len(filtered_frag_lines) - 1]
            start = self.line_offsets[first_file_idx]
            end = self.line_offsets[last_file_idx] + len(file_lines[last_file_idx])
            parent_path = self._get_parent_path(start)
            indent_info = [(ind, txt) for ind, txt in window_info]
            matches.append((start, end, parent_path, indent_info))

        return matches

    def _find_smart_tolerate(self, fragment, ignore_indent, file_ext):
        file_lines = self.file_content.split('\n')
        if file_lines and file_lines[-1] == '':
            file_lines.pop()
        frag_lines = fragment.split('\n')

        frag_info = []
        for line in frag_lines:
            stripped = line.lstrip(' \t')
            indent = len(line) - len(stripped)
            ltype = self._classify_line(stripped, file_ext)
            frag_info.append((indent, stripped, ltype))

        matches = []
        for start_line in range(len(file_lines)):
            f_idx = start_line
            p_idx = 0
            matched_file_indices = []
            code_frag_info = []
            code_file_info = []

            while p_idx < len(frag_info) and f_idx < len(file_lines):
                f_line = file_lines[f_idx]
                f_stripped = f_line.lstrip(' \t')
                f_indent = len(f_line) - len(f_stripped)
                f_type = self._classify_line(f_stripped, file_ext)
                frag_indent, frag_stripped, frag_type = frag_info[p_idx]

                if frag_type == 'comment':
                    # 片段要求注释，文件必须匹配
                    if f_type != 'comment' or f_stripped != frag_stripped:
                        break
                    matched_file_indices.append(f_idx)
                    f_idx += 1
                    p_idx += 1
                elif frag_type in ('code', 'docstring'):
                    if f_type == 'comment':
                        # 文件中的额外注释，跳过
                        f_idx += 1
                        continue
                    if f_type != frag_type or f_stripped != frag_stripped:
                        break
                    if ignore_indent and frag_type == 'code':
                        code_frag_info.append((p_idx, frag_indent))
                        code_file_info.append((f_idx, f_indent))
                    elif not ignore_indent and frag_indent != f_indent:
                        break
                    matched_file_indices.append(f_idx)
                    f_idx += 1
                    p_idx += 1
                else:  # blank
                    # 片段要求空行，文件可以是空行或额外的注释
                    if f_type == 'comment':
                        # 跳过文件中的额外注释
                        f_idx += 1
                        continue
                    if f_stripped != frag_stripped:
                        break
                    matched_file_indices.append(f_idx)
                    f_idx += 1
                    p_idx += 1

            if p_idx == len(frag_info):
                # 匹配完成，检查相对缩进
                if ignore_indent and code_frag_info:
                    min_frag_code = min([ind for _, ind in code_frag_info])
                    min_file_code = min([ind for _, ind in code_file_info])
                    if any((frag_ind - min_frag_code) != (file_ind - min_file_code)
                           for (_, frag_ind), (_, file_ind) in zip(code_frag_info, code_file_info)):
                        continue
                first_idx = matched_file_indices[0]
                last_idx = matched_file_indices[-1]
                start = self.line_offsets[first_idx]
                end = self.line_offsets[last_idx] + len(file_lines[last_idx])
                parent_path = self._get_parent_path(start)
                indent_info = []
                for idx in matched_file_indices:
                    line = file_lines[idx]
                    stripped = line.lstrip(' \t')
                    indent = len(line) - len(stripped)
                    indent_info.append((indent, stripped))
                matches.append((start, end, parent_path, indent_info))

        return matches

    def _find_ignore_comments(self, fragment, ignore_indent, file_ext, keep_docstrings):
        file_lines = self.file_content.split('\n')
        if file_lines and file_lines[-1] == '':
            file_lines.pop()
        frag_lines = fragment.split('\n')

        def filter_lines(lines):
            filtered = []
            for line in lines:
                ltype = self._classify_line(line, file_ext)
                if ltype == 'comment':
                    continue
                if ltype == 'docstring' and not keep_docstrings:
                    continue
                filtered.append(line)
            return filtered

        filtered_file_lines = filter_lines(file_lines)
        filtered_frag_lines = filter_lines(frag_lines)

        if not filtered_frag_lines:
            return []

        file_indices = []
        for i, line in enumerate(file_lines):
            ltype = self._classify_line(line, file_ext)
            if ltype == 'comment':
                continue
            if ltype == 'docstring' and not keep_docstrings:
                continue
            file_indices.append(i)

        frag_info = []
        non_empty_indents = []
        for line in filtered_frag_lines:
            stripped = line.lstrip(' \t')
            indent = len(line) - len(stripped)
            frag_info.append((indent, stripped))
            if stripped:
                non_empty_indents.append(indent)
        if not non_empty_indents:
            return []
        min_frag_indent = min(non_empty_indents)

        matches = []
        max_start = len(filtered_file_lines) - len(filtered_frag_lines)
        if max_start < 0:
            return []

        for line_start in range(max_start + 1):
            text_match = True
            window_info = []
            for j in range(len(filtered_frag_lines)):
                file_line = filtered_file_lines[line_start + j]
                stripped = file_line.lstrip(' \t')
                indent = len(file_line) - len(stripped)
                window_info.append((indent, stripped))
                if stripped != frag_info[j][1]:
                    text_match = False
                    break
            if not text_match:
                continue

            if ignore_indent:
                non_empty_window = [ind for ind, txt in window_info if txt]
                min_window_indent = min(non_empty_window) if non_empty_window else 0
                rel_match = all((frag_info[j][0] - min_frag_indent) == (window_info[j][0] - min_window_indent)
                                for j in range(len(frag_info)) if frag_info[j][1])
                if not rel_match:
                    continue
            else:
                if any(frag_info[j][0] != window_info[j][0] for j in range(len(frag_info))):
                    continue

            first_file_idx = file_indices[line_start]
            last_file_idx = file_indices[line_start + len(filtered_frag_lines) - 1]
            start = self.line_offsets[first_file_idx]
            end = self.line_offsets[last_file_idx] + len(file_lines[last_file_idx])
            parent_path = self._get_parent_path(start)
            indent_info = [(ind, txt) for ind, txt in window_info]
            matches.append((start, end, parent_path, indent_info))

        return matches

    def _classify_line(self, line, file_ext):
        stripped = line.lstrip(' \t')
        if not stripped:
            return 'blank'
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('--'):
            return 'comment'
        if stripped.startswith('"""') or stripped.startswith("'''"):
            rest = stripped[3:].strip()
            if not rest or rest.endswith('"""') or rest.endswith("'''"):
                return 'docstring'
        return 'code'

    def _get_parent_path(self, match_start):
        file_ext = os.path.splitext(self.current_file)[1].lower()
        prefix = self.file_content[:match_start]
        line_num = prefix.count('\n') + 1
        if file_ext in ['.xml', '.html', '.htm', '.svg']:
            tags = re.findall(r'<([A-Za-z_][\w\-]*)\b[^>]*>', prefix)
            path = " > ".join(tags[-3:]) if tags else ""
            return f"XML: {path} (行{line_num})"
        elif file_ext == '.json':
            keys = re.findall(r'"(?:[^"\\]|\\.)*"\s*:', prefix)
            key_names = [k.strip().strip('"').strip(':') for k in keys[-3:]]
            path = " > ".join(key_names) if key_names else ""
            return f"JSON: {path} (行{line_num})"
        elif file_ext in ['.md', '.markdown']:
            titles = re.findall(r'^(#{1,6})\s+(.*)$', prefix, re.MULTILINE)
            if titles:
                last = titles[-1]
                return f"Markdown: {'#' * len(last[0])} {last[1]} (行{line_num})"
            return f"文本 (行{line_num})"
        elif file_ext in ['.ini', '.cfg', '.conf']:
            sections = re.findall(r'^\[([^\]]+)\]', prefix, re.MULTILINE)
            if sections:
                return f"INI: [{sections[-1]}] (行{line_num})"
            return f"文本 (行{line_num})"
        else:
            return f"文本 (行{line_num})"

    def on_match_select(self, event):
        selection = self.match_listbox.curselection()
        if selection:
            self.selected_match_index = selection[0]
            self.status_var.set(f"已选择第 {selection[0]+1} 项")

    # ----- 替换 -----
    def replace_selected(self):
        # 如果 matches 意外为空但存在备份，则恢复
        if not self.matches and hasattr(self, 'last_matches') and self.last_matches:
            self.matches = self.last_matches.copy()
        if not self.matches:
            messagebox.showwarning("提示", "请先执行查找")
            return
        if self.selected_match_index is None:
            # 尝试从当前选中项获取索引
            selection = self.match_listbox.curselection()
            if selection:
                self.selected_match_index = selection[0]
            else:
                messagebox.showwarning("提示", "请先在结果列表中选择要替换的匹配项")
                return

        new_text = self.replace_text.get("1.0", tk.END).rstrip("\n")
        match = self.matches[self.selected_match_index]
        start, end, parent_path, indent_info = match

        try:
            adjusted_new_text = self._process_replacement(new_text, start, end, indent_info)
        except Exception as e:
            messagebox.showerror("错误", str(e))
            return

        record = {
            "op_id": int(time.time() * 1000) + random.randint(0, 999),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_path": self.current_file,
            "offset": start,
            "old_text": self.file_content[start:end],
            "new_text": adjusted_new_text,
            "parent_path": parent_path,
            "context_before": self.file_content[max(0, start-80):start],
            "context_after": self.file_content[end:end+80]
        }

        try:
            new_content = self.file_content[:start] + adjusted_new_text + self.file_content[end:]
            self._write_file_content(self.current_file, new_content)
            self.file_content = new_content
            self._compute_line_offsets()
            self.data["history"].append(record)
            save_data(self.data)
            self.status_var.set("替换成功，已记录历史")
            self.has_find_result = False
            # 计算剩余匹配数
            remaining = len(self.matches) - 1
            self.matches = []
            self.last_matches = []
            self.match_listbox.delete(0, tk.END)
            self.selected_match_index = None
            # 显示自定义对话框
            self._show_replace_success(remaining > 0)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def replace_all(self):
        if not self.matches and hasattr(self, 'last_matches') and self.last_matches:
            self.matches = self.last_matches.copy()
        if not self.matches:
            messagebox.showwarning("提示", "请先执行查找")
            return
        new_text = self.replace_text.get("1.0", tk.END).rstrip("\n")

        records = []
        content = self.file_content
        for match in reversed(self.matches):
            start, end, parent_path, indent_info = match
            try:
                adjusted = self._process_replacement(new_text, start, end, indent_info)
            except Exception as e:
                messagebox.showerror("错误", f"替换全部时出错：{e}")
                return
            record = {
                "op_id": int(time.time() * 1000) + random.randint(0, 999),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_path": self.current_file,
                "offset": start,
                "old_text": content[start:end],
                "new_text": adjusted,
                "parent_path": parent_path,
                "context_before": content[max(0, start-80):start],
                "context_after": content[end:end+80]
            }
            records.append(record)
            content = content[:start] + adjusted + content[end:]

        try:
            self._write_file_content(self.current_file, content)
            self.file_content = content
            self._compute_line_offsets()
            for rec in reversed(records):
                self.data["history"].append(rec)
            save_data(self.data)
            self.status_var.set(f"已替换所有 {len(self.matches)} 处")
            self.has_find_result = False
            self.matches = []
            self.last_matches = []
            self.match_listbox.delete(0, tk.END)
            self.selected_match_index = None
            # 替换全部后没有剩余匹配
            self._show_replace_success(False)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _show_replace_success(self, has_remaining_matches):
        """替换成功后显示提示对话框"""
        def on_complete():
            if has_remaining_matches:
                # 有剩余匹配：保留查找框，清空替换框
                self.replace_text.delete("1.0", tk.END)
            else:
                # 无剩余匹配：清空查找框和替换框
                self.find_text.delete("1.0", tk.END)
                self.replace_text.delete("1.0", tk.END)
        ReplaceSuccessDialog(self, has_remaining_matches, on_complete)

    def _process_replacement(self, new_text, start, end, indent_info):
        replace_mode = self.data["settings"]["replace_mode"]
        if replace_mode == "replace_all":
            return new_text

        file_ext = os.path.splitext(self.current_file)[1].lower()
        original_block = self.file_content[start:end]
        original_lines = original_block.split('\n')
        if original_lines and original_lines[-1] == '':
            original_lines.pop()

        original_comment_lines = [line for line in original_lines if self._classify_line(line, file_ext) == 'comment']
        new_lines = new_text.split('\n')
        new_comment_lines = [line for line in new_lines if self._classify_line(line, file_ext) == 'comment']

        adjusted_new_text = self._adjust_new_text_indent(new_text, indent_info)

        if not new_comment_lines:
            return adjusted_new_text

        if replace_mode == "add_below":
            adjusted_lines = adjusted_new_text.split('\n')
            first_code_idx = 0
            for i, line in enumerate(adjusted_lines):
                if line.strip() and self._classify_line(line, file_ext) != 'comment':
                    first_code_idx = i
                    break
            if original_comment_lines:
                final_lines = adjusted_lines[:first_code_idx] + original_comment_lines + new_comment_lines + adjusted_lines[first_code_idx:]
            else:
                final_lines = adjusted_lines[:first_code_idx] + new_comment_lines + adjusted_lines[first_code_idx:]
            return '\n'.join(final_lines)

        elif replace_mode == "random_place":
            if original_comment_lines:
                comment_indices = [i for i, line in enumerate(original_lines) if self._classify_line(line, file_ext) == 'comment']
                chosen_idx = random.choice(comment_indices)
                direction = random.choice([0, 1])
                insert_pos = chosen_idx if direction == 0 else chosen_idx + 1
                combined_comments = original_comment_lines + new_comment_lines
                random.shuffle(combined_comments)
                adjusted_lines = adjusted_new_text.split('\n')
                first_code_idx = 0
                for i, line in enumerate(adjusted_lines):
                    if line.strip() and self._classify_line(line, file_ext) != 'comment':
                        first_code_idx = i
                        break
                final_lines = adjusted_lines[:first_code_idx] + combined_comments + adjusted_lines[first_code_idx:]
                return '\n'.join(final_lines)
            else:
                return self._process_replacement_add_below(new_text, original_comment_lines, new_comment_lines, adjusted_new_text, file_ext)

        return adjusted_new_text

    def _process_replacement_add_below(self, new_text, original_comment_lines, new_comment_lines, adjusted_new_text, file_ext):
        adjusted_lines = adjusted_new_text.split('\n')
        first_code_idx = 0
        for i, line in enumerate(adjusted_lines):
            if line.strip() and self._classify_line(line, file_ext) != 'comment':
                first_code_idx = i
                break
        if original_comment_lines:
            final_lines = adjusted_lines[:first_code_idx] + original_comment_lines + new_comment_lines + adjusted_lines[first_code_idx:]
        else:
            final_lines = adjusted_lines[:first_code_idx] + new_comment_lines + adjusted_lines[first_code_idx:]
        return '\n'.join(final_lines)

    def _adjust_new_text_indent(self, new_text, indent_info):
        if not indent_info:
            return new_text
        base_indent = None
        for ind, txt in indent_info:
            if txt.strip() and not txt.startswith('#'):
                base_indent = ind
                break
        if base_indent is None:
            base_indent = 0

        new_lines = new_text.split('\n')
        min_indent = None
        for line in new_lines:
            stripped = line.lstrip(' \t')
            if stripped:
                indent = len(line) - len(stripped)
                if min_indent is None or indent < min_indent:
                    min_indent = indent
        if min_indent is None:
            min_indent = 0

        adjusted = []
        for line in new_lines:
            stripped = line.lstrip(' \t')
            if stripped:
                indent = len(line) - len(stripped)
                rel_indent = indent - min_indent
                adjusted.append(' ' * (base_indent + rel_indent) + stripped)
            else:
                adjusted.append('')
        return '\n'.join(adjusted)

    # ----- 撤回 -----
    def undo_last(self):
        self.perform_undo(None)

    def undo_specific_file(self):
        file_path = filedialog.askopenfilename(title="选择要撤回操作的文件")
        if file_path:
            self.perform_undo(file_path)

    def perform_undo(self, target_file=None):
        history = self.data["history"]
        if not history:
            messagebox.showinfo("提示", "没有可撤回的操作")
            return

        for i in range(len(history)-1, -1, -1):
            rec = history[i]
            if rec is None:
                del history[i]
                save_data(self.data)
                messagebox.showwarning("撤回失败", f"第 {i+1} 条历史记录已损坏，已删除。请再次尝试撤回。")
                return
            if target_file and rec["file_path"] != target_file:
                continue
            break
        else:
            if target_file:
                messagebox.showinfo("提示", f"没有找到文件 {target_file} 的可撤回操作")
            else:
                messagebox.showinfo("提示", "没有可撤回的操作")
            return

        try:
            current_content = self._get_file_content(rec["file_path"])
        except Exception as e:
            messagebox.showerror("错误", f"无法读取文件 {rec['file_path']}：{e}")
            return

        start = rec["offset"]
        end = start + len(rec["new_text"])
        if current_content[start:end] != rec["new_text"]:
            if not messagebox.askyesno("内容不一致", "文件当前内容与操作记录不一致，可能已被其他程序修改。\n是否仍然强制撤回（使用旧片段替换当前位置）？"):
                return
            idx = current_content.find(rec["new_text"])
            if idx == -1:
                messagebox.showerror("错误", "无法找到替换后的片段，撤回失败。")
                return
            start = idx
            end = idx + len(rec["new_text"])

        new_content = current_content[:start] + rec["old_text"] + current_content[end:]
        try:
            self._write_file_content(rec["file_path"], new_content)
            del history[i]
            save_data(self.data)
            self.status_var.set("撤回成功")
            if self.current_file == rec["file_path"]:
                self.file_content = new_content
                self._compute_line_offsets()
                self.has_find_result = False
                self.matches = []
                self.match_listbox.delete(0, tk.END)
                self.find_fragment()
            else:
                messagebox.showinfo("提示", f"已撤回文件 {rec['file_path']} 的最近一次操作")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ----- 清理 -----
    def clean_by_date(self):
        date_str = self.clean_date_entry.get().strip()
        try:
            cutoff = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("错误", "日期格式应为 YYYY-MM-DD")
            return
        history = self.data["history"]
        new_history = []
        removed = 0
        for rec in history:
            if rec is None:
                continue
            try:
                rec_time = datetime.strptime(rec["timestamp"], "%Y-%m-%d %H:%M:%S")
            except:
                rec_time = datetime.min
            if rec_time < cutoff:
                removed += 1
            else:
                new_history.append(rec)
        self.data["history"] = new_history
        save_data(self.data)
        messagebox.showinfo("完成", f"已删除 {removed} 条早于 {date_str} 的记录")

    def clean_by_file(self):
        file_path = self.clean_file_entry.get().strip()
        if not file_path:
            messagebox.showerror("错误", "请输入文件完整路径")
            return
        history = self.data["history"]
        new_history = []
        removed = 0
        last_idx = -1
        for i, rec in enumerate(history):
            if rec is not None and rec["file_path"] == file_path:
                last_idx = i
        if last_idx == -1:
            messagebox.showinfo("提示", "该文件没有任何历史记录")
            return
        for i, rec in enumerate(history):
            if i <= last_idx:
                removed += 1
                continue
            new_history.append(rec)
        self.data["history"] = new_history
        save_data(self.data)
        messagebox.showinfo("完成", f"已删除 {removed} 条记录（包含该文件及其之前的所有记录）")

    def clean_by_size(self):
        size_str = self.clean_size_entry.get().strip().upper()
        if not size_str:
            messagebox.showerror("错误", "请输入大小，例如 10MB")
            return
        match = re.match(r'^([\d.]+)\s*(B|KB|MB|GB)?$', size_str)
        if not match:
            messagebox.showerror("错误", "格式不正确，例如 10MB、500KB、1GB")
            return
        value = float(match.group(1))
        unit = match.group(2) or 'B'
        multipliers = {'B':1, 'KB':1024, 'MB':1024**2, 'GB':1024**3}
        target_size = value * multipliers[unit]
        history = self.data["history"]
        current_size = os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
        if current_size <= target_size:
            messagebox.showinfo("提示", "当前文件已经小于目标大小，无需清理")
            return
        removed = 0
        while current_size > target_size and history:
            if history[0] is None:
                history.pop(0)
            else:
                history.pop(0)
                removed += 1
            save_data(self.data)
            current_size = os.path.getsize(DATA_FILE)
        messagebox.showinfo("完成", f"已删除 {removed} 条记录，当前文件大小约 {current_size/1024:.2f} KB")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()