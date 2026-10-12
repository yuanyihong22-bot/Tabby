"""JSON 持久化：每个便签一个文件（note_<id>.json），含数据、位置、字号、置顶状态。"""

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
    font_size: int = 12
    topmost: bool = False


def base_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "TableStickyNote"
    return Path.home() / ".table_sticky_note"


class Storage:
    """绑定到某个便签 id 的持久化（文件 note_<id>.json）。"""

    def __init__(self, widget_id: int = 1) -> None:
        self.widget_id = widget_id
        self.path = base_dir() / f"note_{widget_id}.json"

    @staticmethod
    def list_ids(dir_: Path | None = None) -> List[int]:
        d = dir_ if dir_ is not None else base_dir()
        if not d.exists():
            return []
        ids = []
        for p in d.glob("note_*.json"):
            try:
                ids.append(int(p.stem.split("_", 1)[1]))
            except (IndexError, ValueError):
                continue
        return sorted(ids)

    @staticmethod
    def next_id(dir_: Path | None = None) -> int:
        ids = Storage.list_ids(dir_)
        return (max(ids) + 1) if ids else 1

    @staticmethod
    def migrate_legacy(dir_: Path | None = None) -> bool:
        """把旧版单文件 table.json 迁到 note_1.json（仅当目标不存在时）。"""
        d = dir_ if dir_ is not None else base_dir()
        legacy = d / "table.json"
        target = d / "note_1.json"
        if legacy.exists() and not target.exists():
            legacy.replace(target)
            return True
        return False

    def delete_file(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass

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

        font_size = raw.get("font_size", 12)
        try:
            font_size = int(font_size)
        except (ValueError, TypeError):
            font_size = 12
        font_size = max(8, min(40, font_size))

        topmost = raw.get("topmost", False)
        if not isinstance(topmost, bool):
            topmost = False

        return TableData(rows=rows, window=pos, font_size=font_size, topmost=topmost)

    def save(self, data: TableData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "rows": data.rows,
            "window": asdict(data.window),
            "font_size": data.font_size,
            "topmost": data.topmost,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
