"""桌面小组件窗口：Excel 样式表格、直接粘贴、点选复制、右键菜单。"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from .model import TableModel
from .storage import Storage, TableData

# 布局
DRAG_H = 22          # 顶部拖柄高度
COL_HDR_H = 26       # 列标题（A/B/C）行高
ROW_HDR_W = 46       # 行标题（1/2/3）列宽
ROW_H = 30           # 数据行高
CELL_PAD = 10
COL_MIN_W = 90
MAX_CELL_W = 260
EMPTY_MIN_W = 260    # 空表时数据区最小宽
EMPTY_MIN_H = 100    # 空表时数据区最小高

# 配色（Excel 风格）
FONT_FAMILY = "Microsoft YaHei"
FONT_SIZE = 12
HDR_FONT_SIZE = 10
DRAG_BG = "#e9e9e9"
DRAG_FG = "#7a7a7a"
HDR_BG = "#f0f0f0"
HDR_FG = "#404040"
GRID_COLOR = "#d4d4d4"
CELL_BG = "#ffffff"
TEXT_COLOR = "#1a1a1a"
HIGHLIGHT_COLOR = "#cce8ff"


def _col_letter(n: int) -> str:
    """0 基列号转 Excel 列标题（0→A，25→Z，26→AA）。"""
    s = ""
    n += 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        s = chr(ord("A") + rem) + s
    return s


def _is_number(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


class Widget:
    def __init__(self, root: tk.Tk, model: TableModel, storage: Storage, data: TableData) -> None:
        self.root = root
        self.model = model
        self.storage = storage
        self.data = data
        self._col_widths: list[int] = []
        self._col_offsets: list[int] = []
        self._drag_off_x = 0
        self._drag_off_y = 0
        self._font = tkfont.Font(family=FONT_FAMILY, size=FONT_SIZE)
        self._font_hdr = tkfont.Font(family=FONT_FAMILY, size=HDR_FONT_SIZE)

        root.overrideredirect(True)
        root.attributes("-topmost", False)
        root.configure(bg=GRID_COLOR)

        x, y = self._clamp_position(data.window.x, data.window.y)
        root.geometry(f"+{x}+{y}")

        # 顶部拖柄
        self.header = tk.Frame(root, bg=DRAG_BG, height=DRAG_H, cursor="fleur")
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)
        title = tk.Label(
            self.header, text="表格便签", bg=DRAG_BG, fg=DRAG_FG,
            font=(FONT_FAMILY, 9),
        )
        title.pack(side="left", padx=8)

        # 表格画布
        self.canvas = tk.Canvas(root, highlightthickness=0, bg=CELL_BG)
        self.canvas.pack(fill="both", expand=True)

        # 右键菜单
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="粘贴", command=self._on_paste)
        self.menu.add_command(label="清空", command=self._on_clear)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self._quit)

        # 事件
        self.header.bind("<Button-1>", self._on_drag_start)
        self.header.bind("<B1-Motion>", self._on_drag)
        self.header.bind("<ButtonRelease-1>", self._on_drag_end)
        self.header.bind("<Button-3>", self._on_right_click)
        title.bind("<Button-1>", self._on_drag_start)
        title.bind("<B1-Motion>", self._on_drag)
        title.bind("<ButtonRelease-1>", self._on_drag_end)
        title.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        root.bind("<Control-v>", self._on_paste)
        root.bind("<Control-V>", self._on_paste)

        self._redraw()

    # ---- 渲染 ----

    def _redraw(self) -> None:
        self.canvas.delete("all")
        n_rows = self.model.num_rows
        n_cols = self.model.num_cols

        self._col_widths = []
        for c in range(n_cols):
            maxw = COL_MIN_W
            for r in range(n_rows):
                w = self._font.measure(self.model.cell(r, c))
                if w > maxw:
                    maxw = w
            self._col_widths.append(min(maxw, MAX_CELL_W) + 2 * CELL_PAD)

        data_w = sum(self._col_widths) if self._col_widths else COL_MIN_W
        data_h = n_rows * ROW_H if n_rows else ROW_H
        if n_cols == 0:
            data_w = max(data_w, EMPTY_MIN_W)
        if n_rows == 0:
            data_h = max(data_h, EMPTY_MIN_H)
        total_w = data_w + ROW_HDR_W
        total_h = data_h + COL_HDR_H
        self.canvas.configure(width=total_w, height=total_h)

        self._col_offsets = []
        cx = 0
        for w in self._col_widths:
            self._col_offsets.append(cx)
            cx += w

        # 左上角
        self.canvas.create_rectangle(0, 0, ROW_HDR_W, COL_HDR_H, fill=HDR_BG, outline=GRID_COLOR)

        # 列标题（A/B/C…）
        if n_cols == 0:
            self.canvas.create_rectangle(ROW_HDR_W, 0, total_w, COL_HDR_H, fill=HDR_BG, outline=GRID_COLOR)
            self.canvas.create_text((ROW_HDR_W + total_w) // 2, COL_HDR_H // 2, text="A", fill=HDR_FG, font=self._font_hdr)
        else:
            for c in range(n_cols):
                x0 = ROW_HDR_W + self._col_offsets[c]
                w = self._col_widths[c]
                self.canvas.create_rectangle(x0, 0, x0 + w, COL_HDR_H, fill=HDR_BG, outline=GRID_COLOR)
                self.canvas.create_text(x0 + w // 2, COL_HDR_H // 2, text=_col_letter(c), fill=HDR_FG, font=self._font_hdr)

        # 行标题（1/2/3…）
        if n_rows == 0:
            self.canvas.create_rectangle(0, COL_HDR_H, ROW_HDR_W, total_h, fill=HDR_BG, outline=GRID_COLOR)
            self.canvas.create_text(ROW_HDR_W // 2, (COL_HDR_H + total_h) // 2, text="1", fill=HDR_FG, font=self._font_hdr)
        else:
            for r in range(n_rows):
                y0 = COL_HDR_H + r * ROW_H
                self.canvas.create_rectangle(0, y0, ROW_HDR_W, y0 + ROW_H, fill=HDR_BG, outline=GRID_COLOR)
                self.canvas.create_text(ROW_HDR_W // 2, y0 + ROW_H // 2, text=str(r + 1), fill=HDR_FG, font=self._font_hdr)

        if n_rows == 0 or n_cols == 0:
            self.canvas.create_text(
                (ROW_HDR_W + total_w) // 2, (COL_HDR_H + total_h) // 2, anchor="center",
                text="在 Excel 复制表格后\n点这里按 Ctrl+V 粘贴",
                fill="#999999", font=(FONT_FAMILY, 11), justify="center",
            )
            self.root.update_idletasks()
            return

        for r in range(n_rows):
            y0 = COL_HDR_H + r * ROW_H
            for c in range(n_cols):
                x0 = ROW_HDR_W + self._col_offsets[c]
                w = self._col_widths[c]
                raw = self.model.cell(r, c)
                text = self._truncate(raw, w - 2 * CELL_PAD)
                self.canvas.create_rectangle(x0, y0, x0 + w, y0 + ROW_H, fill=CELL_BG, outline=GRID_COLOR)
                if _is_number(raw):
                    self.canvas.create_text(x0 + w - CELL_PAD, y0 + ROW_H // 2, anchor="e",
                                            text=text, fill=TEXT_COLOR, font=self._font)
                else:
                    self.canvas.create_text(x0 + CELL_PAD, y0 + ROW_H // 2, anchor="w",
                                            text=text, fill=TEXT_COLOR, font=self._font)
        self.root.update_idletasks()

    def _truncate(self, text: str, max_px: int) -> str:
        if max_px <= 0:
            return ""
        if self._font.measure(text) <= max_px:
            return text
        while text and self._font.measure(text + "…") > max_px:
            text = text[:-1]
        return text + "…"

    # ---- 交互 ----

    def _on_click(self, event) -> None:
        self.root.focus_force()
        r, c = self._hit_test(event.x, event.y)
        if r is None or c is None:
            return
        self._copy_to_clipboard(self.model.cell(r, c))
        self._flash_cell(r, c)

    def _hit_test(self, x: int, y: int):
        if x < ROW_HDR_W or y < COL_HDR_H:
            return None, None
        c = None
        for i in range(len(self._col_offsets)):
            x0 = ROW_HDR_W + self._col_offsets[i]
            if x0 <= x < x0 + self._col_widths[i]:
                c = i
                break
        r = (y - COL_HDR_H) // ROW_H
        if r >= self.model.num_rows:
            r = None
        return r, c

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
        except tk.TclError:
            pass

    def _flash_cell(self, r: int, c: int) -> None:
        x0 = ROW_HDR_W + self._col_offsets[c]
        y0 = COL_HDR_H + r * ROW_H
        w = self._col_widths[c]
        raw = self.model.cell(r, c)
        text = self._truncate(raw, w - 2 * CELL_PAD)
        self.canvas.create_rectangle(x0, y0, x0 + w, y0 + ROW_H, fill=HIGHLIGHT_COLOR, outline=GRID_COLOR)
        if _is_number(raw):
            self.canvas.create_text(x0 + w - CELL_PAD, y0 + ROW_H // 2, anchor="e",
                                    text=text, fill=TEXT_COLOR, font=self._font)
        else:
            self.canvas.create_text(x0 + CELL_PAD, y0 + ROW_H // 2, anchor="w",
                                    text=text, fill=TEXT_COLOR, font=self._font)
        self.root.after(300, self._redraw)

    def _on_paste(self, event=None) -> None:
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return
        if text:
            self.model.apply_text(text)
            self._redraw()
            self.storage.save(self.data)

    def _on_clear(self) -> None:
        self.model.clear()
        self._redraw()
        self.storage.save(self.data)

    def _on_drag_start(self, event) -> None:
        self._drag_off_x = self.root.winfo_pointerx() - self.root.winfo_x()
        self._drag_off_y = self.root.winfo_pointery() - self.root.winfo_y()

    def _on_drag(self, event) -> None:
        x = self.root.winfo_pointerx() - self._drag_off_x
        y = self.root.winfo_pointery() - self._drag_off_y
        self.root.geometry(f"+{x}+{y}")
        self.data.window.x = x
        self.data.window.y = y

    def _on_drag_end(self, event) -> None:
        self.storage.save(self.data)

    def _on_right_click(self, event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _quit(self) -> None:
        self.storage.save(self.data)
        self.root.destroy()

    def _clamp_position(self, x: int, y: int):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        return (max(0, min(x, sw - 120)), max(0, min(y, sh - 80)))
