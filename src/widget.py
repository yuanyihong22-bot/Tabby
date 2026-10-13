"""桌面小组件窗口：Excel 样式表格、框选/行列选中/删除、撤销、字号缩放、置顶、悬停提示、多便签。"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont

from . import autostart
from . import shortcut
from .model import TableModel
from .storage import Storage, TableData

# 布局
DRAG_H = 22          # 顶部拖柄高度
ROW_HDR_W = 46       # 行标题（1/2/3）列宽
CELL_PAD = 10
COL_MIN_W = 90
MAX_CELL_W = 260
EMPTY_MIN_W = 260    # 空表时数据区最小宽
EMPTY_MIN_H = 100    # 空表时数据区最小高

# 字号
FONT_FAMILY = "Microsoft YaHei"
DEFAULT_FONT_SIZE = 12
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 40

# 配色（Excel 风格）
DRAG_BG = "#e9e9e9"
DRAG_FG = "#7a7a7a"
HDR_BG = "#f0f0f0"
HDR_FG = "#404040"
GRID_COLOR = "#d4d4d4"
CELL_BG = "#ffffff"
TEXT_COLOR = "#1a1a1a"
HIGHLIGHT_COLOR = "#cce8ff"   # 选中浅蓝填充
SELECTION_BORDER = "#2f6fd6"  # 选中蓝色边框


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


def _clamp_font_size(n: int) -> int:
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, n))


class Widget:
    def __init__(
        self,
        root,
        model: TableModel,
        storage: Storage,
        data: TableData,
        widget_id: int,
        on_close,
        on_new,
        on_quit_all,
    ) -> None:
        self.root = root
        self.model = model
        self.storage = storage
        self.data = data
        self.widget_id = widget_id
        self.on_close = on_close
        self.on_new = on_new
        self.on_quit_all = on_quit_all

        self._font_size = data.font_size
        self._font = tkfont.Font(family=FONT_FAMILY, size=self._font_size)
        self._font_hdr = tkfont.Font(family=FONT_FAMILY, size=max(8, self._font_size - 2))

        self._col_widths: list[int] = []
        self._col_offsets: list[int] = []
        self._drag_off_x = 0
        self._drag_off_y = 0
        self._selection: tuple[int, int, int, int] | None = None  # 框选 (r1,c1,r2,c2)
        self._row_sel: int | None = None                          # 选中的整行
        self._col_sel: int | None = None                          # 选中的整列
        self._anchor: tuple[int, int] | None = None
        self._dragging = False
        self._topmost = data.topmost
        self._undo_stack: list[list[list[str]]] = []
        self._tooltip: tk.Toplevel | None = None
        self._hover: tuple[int, int] | None = None
        self._settings_win: tk.Toplevel | None = None
        self._feedback_id = None

        root.overrideredirect(True)
        root.attributes("-topmost", self._topmost)
        root.configure(bg=GRID_COLOR)

        x, y = self._clamp_position(data.window.x, data.window.y)
        root.geometry(f"+{x}+{y}")

        # 顶部拖柄 + 标题 + 右侧按钮
        self.header = tk.Frame(root, bg=DRAG_BG, height=DRAG_H, cursor="fleur")
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        self.title = tk.Label(
            self.header, text="表格便签", bg=DRAG_BG, fg=DRAG_FG,
            font=(FONT_FAMILY, 9), cursor="fleur",
        )
        self.title.pack(side="left", padx=8)

        self.btn_close = self._header_button("×", self.on_close)
        self.btn_settings = self._header_button("设置", self._open_settings)
        self.btn_new = self._header_button("＋", self.on_new)
        self.btn_pin = self._header_button("置顶", self._toggle_topmost)
        for b in (self.btn_close, self.btn_settings, self.btn_new, self.btn_pin):
            b.pack(side="right", padx=2)
        self._update_pin_button()

        # 表格画布
        self.canvas = tk.Canvas(root, highlightthickness=0, bg=CELL_BG)
        self.canvas.pack(fill="both", expand=True)

        # 右键菜单
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="复制", command=self._copy_selection)
        self.menu.add_command(label="粘贴", command=self._on_paste)
        self.menu.add_command(label="清空", command=self._on_clear)
        self.menu.add_separator()
        self.menu.add_command(label="新建便签", command=self.on_new)
        self.menu.add_command(label="退出全部", command=self.on_quit_all)

        # 拖柄：移动窗口
        for w in (self.header, self.title):
            w.bind("<Button-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._on_drag_end)
            w.bind("<Button-3>", self._on_right_click)

        # 表格区
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)

        # 快捷键
        root.bind("<Control-v>", self._on_paste)
        root.bind("<Control-V>", self._on_paste)
        root.bind("<Control-c>", self._copy_selection)
        root.bind("<Control-C>", self._copy_selection)
        root.bind("<Delete>", self._on_delete)
        root.bind("<Control-z>", self._undo)
        root.bind("<Control-Z>", self._undo)
        root.bind("<Control-MouseWheel>", self._on_zoom_wheel)
        root.bind("<Control-Button-4>", lambda e: self._zoom(1))
        root.bind("<Control-Button-5>", lambda e: self._zoom(-1))
        root.bind("<Control-equal>", self._on_zoom_in)
        root.bind("<Control-plus>", self._on_zoom_in)
        root.bind("<Control-minus>", self._on_zoom_out)
        root.bind("<Control-0>", self._on_zoom_reset)

        self._redraw()

    # ---- 尺寸 ----

    def _row_h(self) -> int:
        return self._font.metrics("linespace") + 14

    def _col_hdr_h(self) -> int:
        return self._font_hdr.metrics("linespace") + 12

    # ---- 渲染 ----

    def _redraw(self) -> None:
        self._hide_tooltip()
        self.canvas.delete("all")
        n_rows = self.model.num_rows
        n_cols = self.model.num_cols
        row_h = self._row_h()
        hdr_h = self._col_hdr_h()

        self._col_widths = []
        for c in range(n_cols):
            maxw = COL_MIN_W
            for r in range(n_rows):
                w = self._font.measure(self.model.cell(r, c))
                if w > maxw:
                    maxw = w
            self._col_widths.append(min(maxw, MAX_CELL_W) + 2 * CELL_PAD)

        data_w = sum(self._col_widths) if self._col_widths else COL_MIN_W
        data_h = n_rows * row_h if n_rows else row_h
        if n_cols == 0:
            data_w = max(data_w, EMPTY_MIN_W)
        if n_rows == 0:
            data_h = max(data_h, EMPTY_MIN_H)
        total_w = data_w + ROW_HDR_W
        total_h = data_h + hdr_h
        self.canvas.configure(width=total_w, height=total_h)

        self._col_offsets = []
        cx = 0
        for w in self._col_widths:
            self._col_offsets.append(cx)
            cx += w

        # 左上角
        self.canvas.create_rectangle(0, 0, ROW_HDR_W, hdr_h, fill=HDR_BG, outline=GRID_COLOR)

        # 列标题（A/B/C…）
        if n_cols == 0:
            self.canvas.create_rectangle(ROW_HDR_W, 0, total_w, hdr_h, fill=HDR_BG, outline=GRID_COLOR)
            self.canvas.create_text((ROW_HDR_W + total_w) // 2, hdr_h // 2, text="A", fill=HDR_FG, font=self._font_hdr)
        else:
            for c in range(n_cols):
                x0 = ROW_HDR_W + self._col_offsets[c]
                w = self._col_widths[c]
                self.canvas.create_rectangle(x0, 0, x0 + w, hdr_h, fill=HDR_BG, outline=GRID_COLOR)
                self.canvas.create_text(x0 + w // 2, hdr_h // 2, text=_col_letter(c), fill=HDR_FG, font=self._font_hdr)

        # 行标题（1/2/3…）
        if n_rows == 0:
            self.canvas.create_rectangle(0, hdr_h, ROW_HDR_W, total_h, fill=HDR_BG, outline=GRID_COLOR)
            self.canvas.create_text(ROW_HDR_W // 2, (hdr_h + total_h) // 2, text="1", fill=HDR_FG, font=self._font_hdr)
        else:
            for r in range(n_rows):
                y0 = hdr_h + r * row_h
                self.canvas.create_rectangle(0, y0, ROW_HDR_W, y0 + row_h, fill=HDR_BG, outline=GRID_COLOR)
                self.canvas.create_text(ROW_HDR_W // 2, y0 + row_h // 2, text=str(r + 1), fill=HDR_FG, font=self._font_hdr)

        if n_rows == 0 or n_cols == 0:
            self.canvas.create_text(
                (ROW_HDR_W + total_w) // 2, (hdr_h + total_h) // 2, anchor="center",
                text="在 Excel 复制表格后\nCtrl+V 粘贴（追加到下面）",
                fill="#999999", font=(FONT_FAMILY, 11), justify="center",
            )
            self.root.update_idletasks()
            return

        # 第一遍：单元格底色 + 网格
        for r in range(n_rows):
            y0 = hdr_h + r * row_h
            for c in range(n_cols):
                x0 = ROW_HDR_W + self._col_offsets[c]
                w = self._col_widths[c]
                self.canvas.create_rectangle(x0, y0, x0 + w, y0 + row_h, fill=CELL_BG, outline=GRID_COLOR)

        # 选中填充（框选 / 整行 / 整列）
        for rect in self._highlight_rects():
            pr = self._cell_rect(*rect)
            if pr is not None:
                x0, y0, x1, y1 = pr
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=HIGHLIGHT_COLOR, outline=GRID_COLOR)

        # 第二遍：文本
        for r in range(n_rows):
            y0 = hdr_h + r * row_h
            for c in range(n_cols):
                x0 = ROW_HDR_W + self._col_offsets[c]
                w = self._col_widths[c]
                raw = self.model.cell(r, c)
                text = self._truncate(raw, w - 2 * CELL_PAD)
                if _is_number(raw):
                    self.canvas.create_text(x0 + w - CELL_PAD, y0 + row_h // 2, anchor="e",
                                            text=text, fill=TEXT_COLOR, font=self._font)
                else:
                    self.canvas.create_text(x0 + CELL_PAD, y0 + row_h // 2, anchor="w",
                                            text=text, fill=TEXT_COLOR, font=self._font)

        # 选中边框
        for rect in self._highlight_rects():
            pr = self._cell_rect(*rect)
            if pr is not None:
                x0, y0, x1, y1 = pr
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=SELECTION_BORDER, width=2)

        self.root.update_idletasks()

    def _highlight_rects(self):
        n_rows = self.model.num_rows
        n_cols = self.model.num_cols
        rects = []
        if self._row_sel is not None and self._row_sel < n_rows and n_cols > 0:
            rects.append((self._row_sel, 0, self._row_sel, n_cols - 1))
        if self._col_sel is not None and self._col_sel < n_cols and n_rows > 0:
            rects.append((0, self._col_sel, n_rows - 1, self._col_sel))
        if self._selection is not None:
            rects.append(self._selection)
        return rects

    def _cell_rect(self, r1: int, c1: int, r2: int, c2: int):
        n_rows = self.model.num_rows
        n_cols = self.model.num_cols
        if n_rows == 0 or n_cols == 0:
            return None
        if r1 >= n_rows or c1 >= n_cols or r2 < 0 or c2 < 0:
            return None
        r1 = max(0, r1); c1 = max(0, c1)
        r2 = min(r2, n_rows - 1); c2 = min(c2, n_cols - 1)
        x0 = ROW_HDR_W + self._col_offsets[c1]
        y0 = self._col_hdr_h() + r1 * self._row_h()
        x1 = ROW_HDR_W + self._col_offsets[c2] + self._col_widths[c2]
        y1 = self._col_hdr_h() + (r2 + 1) * self._row_h()
        return (x0, y0, x1, y1)

    def _truncate(self, text: str, max_px: int) -> str:
        if max_px <= 0:
            return ""
        if self._font.measure(text) <= max_px:
            return text
        while text and self._font.measure(text + "…") > max_px:
            text = text[:-1]
        return text + "…"

    # ---- 点选 / 框选 / 行列选中 ----

    def _hit_header(self, x: int, y: int):
        hdr_h = self._col_hdr_h()
        if y < hdr_h:
            if x < ROW_HDR_W:
                return ("corner", None)
            for i in range(len(self._col_offsets)):
                x0 = ROW_HDR_W + self._col_offsets[i]
                if x0 <= x < x0 + self._col_widths[i]:
                    return ("col", i)
            return None
        if x < ROW_HDR_W:
            r = (y - hdr_h) // self._row_h()
            if 0 <= r < self.model.num_rows:
                return ("row", r)
            return None
        return None

    def _hit_test(self, x: int, y: int):
        if x < ROW_HDR_W or y < self._col_hdr_h():
            return None, None
        c = None
        for i in range(len(self._col_offsets)):
            x0 = ROW_HDR_W + self._col_offsets[i]
            if x0 <= x < x0 + self._col_widths[i]:
                c = i
                break
        r = (y - self._col_hdr_h()) // self._row_h()
        if r >= self.model.num_rows:
            r = None
        return r, c

    def _on_mouse_down(self, event) -> None:
        self._hide_tooltip()
        self.root.focus_force()
        hdr = self._hit_header(event.x, event.y)
        if hdr is not None:
            kind, idx = hdr
            self._anchor = None
            self._dragging = False
            if kind == "row" and idx is not None:
                self._row_sel = idx
                self._col_sel = None
                self._selection = None
                self._redraw()
            elif kind == "col" and idx is not None:
                self._col_sel = idx
                self._row_sel = None
                self._selection = None
                self._redraw()
            return
        r, c = self._hit_test(event.x, event.y)
        if r is None or c is None:
            self._anchor = None
            return
        self._anchor = (r, c)
        self._dragging = False
        self._row_sel = None
        self._col_sel = None

    def _on_mouse_move(self, event) -> None:
        if self._anchor is None:
            return
        r, c = self._hit_test(event.x, event.y)
        if r is None or c is None:
            return
        if (r, c) != self._anchor:
            self._dragging = True
            self._selection = self._normalize(self._anchor, (r, c))
            self._redraw()

    def _on_mouse_up(self, event) -> None:
        anchor = self._anchor
        self._anchor = None
        if anchor is None:
            return
        r, c = self._hit_test(event.x, event.y)
        if self._dragging:
            self._dragging = False
            if r is not None and c is not None:
                self._selection = self._normalize(anchor, (r, c))
                self._redraw()
            return
        if r is not None and c is not None and (r, c) == anchor:
            # 单击：选中该格（1×1）并复制；之后 Delete 可清除该格内容
            self._selection = (r, c, r, c)
            self._redraw()
            self._copy_to_clipboard(self.model.cell(r, c))

    @staticmethod
    def _normalize(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int, int, int]:
        r1, c1 = a
        r2, c2 = b
        return (min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2))

    def _selection_text(self) -> str:
        if self._row_sel is not None:
            r = self._row_sel
            if r < self.model.num_rows:
                return "\t".join(self.model.cell(r, c) for c in range(self.model.num_cols))
            return ""
        if self._col_sel is not None:
            c = self._col_sel
            if c < self.model.num_cols:
                return "\n".join(self.model.cell(r, c) for r in range(self.model.num_rows))
            return ""
        if self._selection is not None:
            r1, c1, r2, c2 = self._selection
            return "\n".join(
                "\t".join(self.model.cell(r, c) for c in range(c1, c2 + 1))
                for r in range(r1, r2 + 1)
            )
        return ""

    def _copy_selection(self, event=None) -> None:
        text = self._selection_text()
        if text:
            self._copy_to_clipboard(text)

    # ---- 删除 / 撤销 ----

    def _on_delete(self, event=None) -> None:
        if self._row_sel is not None:
            self._push_undo()
            self.model.delete_rows(self._row_sel, self._row_sel)
            self._row_sel = None
            self._redraw()
            self.storage.save(self.data)
        elif self._col_sel is not None:
            self._push_undo()
            self.model.delete_cols(self._col_sel, self._col_sel)
            self._col_sel = None
            self._redraw()
            self.storage.save(self.data)
        elif self._selection is not None:
            self._push_undo()
            r1, c1, r2, c2 = self._selection
            self.model.clear_range(r1, c1, r2, c2)
            self._selection = None
            self._redraw()
            self.storage.save(self.data)

    def _push_undo(self) -> None:
        self._undo_stack.append([row[:] for row in self.model.rows])
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def _undo(self, event=None) -> None:
        if not self._undo_stack:
            return
        self.model.rows[:] = self._undo_stack.pop()
        self._selection = None
        self._row_sel = None
        self._col_sel = None
        self._redraw()
        self.storage.save(self.data)

    # ---- 粘贴 / 清空 ----

    def _on_paste(self, event=None) -> None:
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return
        if text:
            self._push_undo()
            self._selection = None
            self._row_sel = None
            self._col_sel = None
            self.model.append_text(text)
            self._redraw()
            self.storage.save(self.data)

    def _on_clear(self) -> None:
        self._push_undo()
        self._selection = None
        self._row_sel = None
        self._col_sel = None
        self.model.clear()
        self._redraw()
        self.storage.save(self.data)

    # ---- 复制反馈 ----

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
            self._copied_feedback()
        except tk.TclError:
            pass

    def _copied_feedback(self) -> None:
        self.title.configure(text="已复制 ✓", fg="#1e8e3e")
        if self._feedback_id is not None:
            self.root.after_cancel(self._feedback_id)
        self._feedback_id = self.root.after(800, self._reset_title)

    def _reset_title(self) -> None:
        self.title.configure(text="表格便签", fg=DRAG_FG)
        self._feedback_id = None

    # ---- 字号缩放 ----

    def _zoom(self, delta: int) -> None:
        new_size = _clamp_font_size(self._font_size + delta)
        if new_size == self._font_size:
            return
        self._font_size = new_size
        self._font.configure(size=new_size)
        self._font_hdr.configure(size=max(8, new_size - 2))
        self.data.font_size = new_size
        self._redraw()
        self.storage.save(self.data)

    def _on_zoom_wheel(self, event) -> None:
        self._zoom(1 if event.delta > 0 else -1)

    def _on_zoom_in(self, event=None) -> None:
        self._zoom(1)

    def _on_zoom_out(self, event=None) -> None:
        self._zoom(-1)

    def _on_zoom_reset(self, event=None) -> None:
        self._zoom(DEFAULT_FONT_SIZE - self._font_size)

    # ---- 置顶 / 设置 ----

    def _toggle_topmost(self) -> None:
        self._topmost = not self._topmost
        self.data.topmost = self._topmost
        self.root.attributes("-topmost", self._topmost)
        self._update_pin_button()
        self.storage.save(self.data)

    def _update_pin_button(self) -> None:
        if self._topmost:
            self.btn_pin.configure(text="置顶✓", bg="#dbeafe", fg="#1d4ed8")
        else:
            self.btn_pin.configure(text="置顶", bg=DRAG_BG, fg=DRAG_FG)

    def _open_settings(self) -> None:
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("设置")
        win.geometry(f"+{self.root.winfo_x() + 40}+{self.root.winfo_y() + 40}")
        win.resizable(False, False)
        self._settings_win = win

        var = tk.BooleanVar(value=autostart.is_enabled())

        def on_toggle():
            autostart.set_enabled(var.get())

        cb = tk.Checkbutton(win, text="开机自动启动", variable=var, command=on_toggle,
                            font=(FONT_FAMILY, 11))
        cb.pack(padx=16, pady=(14, 4), anchor="w")

        tk.Label(win, text="下次开机自动打开所有便签", fg="#888888",
                 font=(FONT_FAMILY, 9)).pack(padx=16, pady=(0, 10), anchor="w")

        def make_shortcut():
            if shortcut.create_desktop_shortcut():
                btn_shortcut.configure(text="已创建 ✓")
            else:
                btn_shortcut.configure(text="创建失败")

        btn_shortcut = tk.Button(win, text="创建桌面快捷方式", command=make_shortcut,
                                 font=(FONT_FAMILY, 10))
        btn_shortcut.pack(pady=(0, 10))

        tk.Button(win, text="关闭", command=win.destroy, font=(FONT_FAMILY, 10)).pack(pady=(0, 12))

    # ---- 悬停提示 ----

    def _on_motion(self, event) -> None:
        r, c = self._hit_test(event.x, event.y)
        if (r, c) == self._hover:
            return
        self._hide_tooltip()
        if r is None or c is None:
            return
        self._hover = (r, c)
        raw = self.model.cell(r, c)
        if c < len(self._col_widths) and self._font.measure(raw) > self._col_widths[c] - 2 * CELL_PAD:
            self._show_tooltip(raw)

    def _on_leave(self, event) -> None:
        self._hide_tooltip()

    def _show_tooltip(self, text: str) -> None:
        if len(text) > 500:
            text = text[:500] + "…"
        tip = tk.Toplevel(self.root)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tk.Label(tip, text=text, bg="#ffffe0", fg="#333333", font=(FONT_FAMILY, 11),
                 justify="left", padx=6, pady=3, bd=1, relief="solid").pack()
        px = self.root.winfo_pointerx() + 14
        py = self.root.winfo_pointery() + 14
        tip.wm_geometry(f"+{px}+{py}")
        self._tooltip = tip

    def _hide_tooltip(self) -> None:
        if self._tooltip is not None:
            try:
                self._tooltip.destroy()
            except tk.TclError:
                pass
            self._tooltip = None
        self._hover = None

    # ---- 拖动窗口 ----

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

    def _header_button(self, text: str, command):
        lbl = tk.Label(self.header, text=text, bg=DRAG_BG, fg=DRAG_FG,
                       font=(FONT_FAMILY, 9), cursor="hand2", padx=6)
        lbl.bind("<Button-1>", lambda e: command())
        return lbl

    def _clamp_position(self, x: int, y: int):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        return (max(0, min(x, sw - 120)), max(0, min(y, sh - 80)))
