"""JSON 持久化：表格数据与窗口位置。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List


@dataclass
class WindowPos:
    x: int = 100
    y: int = 100


@dataclass
class TableData:
    rows: List[List[str]] = field(default_factory=list)
    window: WindowPos = field(default_factory=WindowPos)


def default_path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "TableStickyNote" / "table.json"
    return Path.home() / ".table_sticky_note" / "table.json"


class Storage:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else default_path()

    def load(self) -> TableData:
        if not self.path.exists():
            return TableData()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return TableData()
        if not isinstance(raw, dict):
            return TableData()

        rows = raw.get("rows", [])
        if not isinstance(rows, list):
            rows = []
        rows = [
            [str(c) for c in (row if isinstance(row, list) else [])]
            for row in rows
        ]

        win = raw.get("window", {})
        if not isinstance(win, dict):
            win = {}
        try:
            pos = WindowPos(x=int(win.get("x", 100)), y=int(win.get("y", 100)))
        except (ValueError, TypeError):
            pos = WindowPos()

        return TableData(rows=rows, window=pos)

    def save(self, data: TableData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"rows": data.rows, "window": asdict(data.window)}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
