"""桌面小组件窗口：无边框、拖柄拖动、点选复制、右键菜单。"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from .model import TableModel
from .storage import Storage, TableData

PAD = 6
ROW_H = 26
COL_MIN_W = 60
CELL_PAD = 8
MAX_CELL_W = 220
HEADER_H = 24
FONT_FAMILY = "Microsoft YaHei"
FONT_SIZE = 10
HEADER_BG = "#3f6fb5"
HEADER_FG = "#ffffff"
GRID_COLOR = "#d8d8d8"
CELL_BG = "#ffffff"
TEXT_COLOR = "#1a1a1a"
HIGHLIGHT_COLOR = "#ffe08a"


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

        root.overrideredirect(True)
        root.attributes("-topmost", False)
        root.configure(bg=GRID_COLOR)

        x, y = self._clamp_position(data.window.x, data.window.y)
        root.geometry(f"+{x}+{y}")

        # 顶部拖柄
        self.header = tk.Frame(root, bg=HEADER_BG, height=HEADER_H, cursor="fleur")
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)
        title = tk.Label(
            self.header, text="表格便签", bg=HEADER_BG, fg=HEADER_FG,
            font=(FONT_FAMILY, 9, "bold"),
        )
        title.pack(side="left", padx=8)

        # 表格画布
        self.canvas = tk.Canvas(root, highlightthickness=0, bg=CELL_BG)
        self.canvas.pack(fill="both", expand=True)

        # 右键菜单
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="编辑", command=self._open_editor)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self._quit)

        # 事件绑定
        self.header.bind("<Button-1>", self._on_drag_start)
        self.header.bind("<B1-Motion>", self._on_drag)
        self.header.bind("<Button-3>", self._on_right_click)
        title.bind("<Button-1>", self._on_drag_start)
        title.bind("<B1-Motion>", self._on_drag)
        title.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

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

        total_w = sum(self._col_widths) if self._col_widths else COL_MIN_W
        total_h = n_rows * ROW_H if n_rows else ROW_H

        self.canvas.configure(width=total_w, height=total_h)

        self._col_offsets = []
        cx = 0
        for w in self._col_widths:
            self._col_offsets.append(cx)
            cx += w

        if n_rows == 0 or n_cols == 0:
            self.canvas.create_text(
                PAD, PAD, anchor="nw",
                text="右键 → 编辑，粘贴表格数据",
                fill="#999999", font=(FONT_FAMILY, 9),
            )
            self.root.update_idletasks()
            return

        for r in range(n_rows):
            y0 = r * ROW_H
            for c in range(n_cols):
                x0 = self._col_offsets[c]
                w = self._col_widths[c]
                text = self._truncate(self.model.cell(r, c), w - 2 * CELL_PAD)
                self.canvas.create_rectangle(
                    x0, y0, x0 + w, y0 + ROW_H, fill=CELL_BG, outline=GRID_COLOR
                )
                self.canvas.create_text(
                    x0 + CELL_PAD, y0 + ROW_H // 2, anchor="w",
                    text=text, fill=TEXT_COLOR, font=self._font,
                )
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
        r, c = self._hit_test(event.x, event.y)
        if r is None or c is None:
            return
        text = self.model.cell(r, c)
        self._copy_to_clipboard(text)
        self._flash_cell(r, c)

    def _hit_test(self, x: int, y: int):
        if x < 0 or y < 0:
            return None, None
        c = None
        for i in range(len(self._col_offsets)):
            x0 = self._col_offsets[i]
            if x0 <= x < x0 + self._col_widths[i]:
                c = i
                break
        r = y // ROW_H
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
        x0 = self._col_offsets[c]
        y0 = r * ROW_H
        w = self._col_widths[c]
        self.canvas.create_rectangle(
            x0, y0, x0 + w, y0 + ROW_H, fill=HIGHLIGHT_COLOR, outline=GRID_COLOR
        )
        text = self._truncate(self.model.cell(r, c), w - 2 * CELL_PAD)
        self.canvas.create_text(
            x0 + CELL_PAD, y0 + ROW_H // 2, anchor="w",
            text=text, fill=TEXT_COLOR, font=self._font,
        )
        self.root.after(300, self._redraw)

    def _on_drag_start(self, event) -> None:
        self._drag_off_x = self.root.winfo_pointerx() - self.root.winfo_x()
        self._drag_off_y = self.root.winfo_pointery() - self.root.winfo_y()

    def _on_drag(self, event) -> None:
        x = self.root.winfo_pointerx() - self._drag_off_x
        y = self.root.winfo_pointery() - self._drag_off_y
        self.root.geometry(f"+{x}+{y}")
        self.data.window.x = x
        self.data.window.y = y

    def _on_right_click(self, event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _open_editor(self) -> None:
        from .editor import EditorDialog
        EditorDialog(self.root, self.model, on_apply=self._after_edit)

    def _after_edit(self) -> None:
        self._redraw()
        self.storage.save(self.data)

    def _quit(self) -> None:
        self.storage.save(self.data)
        self.root.destroy()

    def _clamp_position(self, x: int, y: int):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        return (max(0, min(x, sw - 120)), max(0, min(y, sh - 80)))
