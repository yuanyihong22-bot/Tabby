"""表格数据模型与粘贴文本解析。"""

from __future__ import annotations

from typing import List


class TableModel:
    """持有表格数据的二维列表，提供解析与取值接口。"""

    def __init__(self, rows: List[List[str]] | None = None) -> None:
        self.rows: List[List[str]] = rows if rows is not None else []

    @property
    def num_rows(self) -> int:
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        return max((len(row) for row in self.rows), default=0)

    def cell(self, r: int, c: int) -> str:
        if 0 <= r < len(self.rows) and 0 <= c < len(self.rows[r]):
            return self.rows[r][c]
        return ""

    @staticmethod
    def parse_text(text: str) -> List[List[str]]:
        """把粘贴文本解析成二维列表。

        规则：按换行分行、每行按 Tab 分列（Excel 复制出的格式）；
        列数不一致时以最长行为准补空串；去掉末尾空行。
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        raw = [line.split("\t") for line in text.split("\n")]
        return _pad_rows(raw)

    def apply_text(self, text: str) -> None:
        """用解析结果替换当前数据（原地替换，保持与外部引用的共享）。"""
        self.rows[:] = self.parse_text(text)

    def clear(self) -> None:
        """清空表格。"""
        self.rows[:] = []

    def append_text(self, text: str) -> None:
        """解析新内容并追加到现有表格下方（原地，不丢旧数据）。"""
        new_rows = self.parse_text(text)
        if not new_rows:
            return
        self.rows.extend(new_rows)
        self._repad()

    def _repad(self) -> None:
        """把所有行补齐到一致列宽。"""
        if not self.rows:
            return
        max_cols = max(len(r) for r in self.rows)
        for i in range(len(self.rows)):
            if len(self.rows[i]) < max_cols:
                self.rows[i] = self.rows[i] + [""] * (max_cols - len(self.rows[i]))

    def delete_rows(self, r1: int, r2: int) -> None:
        """删除第 r1..r2 行（含两端）。"""
        if not self.rows or r1 >= len(self.rows):
            return
        del self.rows[r1:r2 + 1]
        self._repad()

    def delete_cols(self, c1: int, c2: int) -> None:
        """删除第 c1..c2 列（含两端）。"""
        for row in self.rows:
            del row[c1:c2 + 1]
        self._repad()

    def clear_range(self, r1: int, c1: int, r2: int, c2: int) -> None:
        """清空矩形范围内的内容（保留结构）。"""
        for r in range(r1, min(r2 + 1, len(self.rows))):
            for c in range(c1, min(c2 + 1, len(self.rows[r]))):
                self.rows[r][c] = ""


def _pad_rows(raw: List[List[str]]) -> List[List[str]]:
    # 去掉末尾完全为空的行（粘贴常带结尾换行）
    while raw and all(cell == "" for cell in raw[-1]):
        raw.pop()
    if not raw:
        return []
    max_cols = max(len(row) for row in raw)
    return [row + [""] * (max_cols - len(row)) for row in raw]
