"""编辑窗口：粘贴文本，应用后回写模型。"""

from __future__ import annotations

import tkinter as tk

from .model import TableModel


class EditorDialog:
    def __init__(self, parent, model: TableModel, on_apply) -> None:
        self.model = model
        self.on_apply = on_apply

        self.win = tk.Toplevel(parent)
        self.win.title("编辑表格")
        self.win.geometry("560x380")
        self.win.transient(parent)

        tk.Label(
            self.win,
            text="从 Excel 复制表格后粘贴到下面（Tab 分列、换行分行）：",
            font=("Microsoft YaHei", 9), fg="#555555", anchor="w",
        ).pack(fill="x", padx=10, pady=(10, 4))

        self.text = tk.Text(self.win, font=("Consolas", 10), wrap="none", undo=True)
        self.text.pack(fill="both", expand=True, padx=10, pady=4)
        self.text.insert("1.0", self._rows_to_text(self.model.rows))

        bar = tk.Frame(self.win)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(bar, text="应用", command=self._apply, width=10).pack(side="right")
        tk.Button(bar, text="取消", command=self.win.destroy, width=10).pack(
            side="right", padx=6
        )

    @staticmethod
    def _rows_to_text(rows) -> str:
        return "\n".join("\t".join(row) for row in rows)

    def _apply(self) -> None:
        content = self.text.get("1.0", "end-1c")
        self.model.apply_text(content)
        self.on_apply()
        self.win.destroy()
