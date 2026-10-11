"""置顶状态管理：SetWindowPos 封装 + pinned 集合 + frontmost_pinned()。

`pinned` 集合归本模块持有，记录「由本程序置顶」的窗口句柄。
"""

from __future__ import annotations

from typing import Callable


class Pinner:
    """置顶 / 取消置顶 + 置顶集合。

    依赖：
      - win32：薄封装层（可被测试 monkeypatch）。
      - is_alive：校验句柄仍指向存活且类名仍为 XLMAIN 的窗口（防句柄复用），
        由调用方（main.py 装配时）注入 excel 的校验函数。
    """

    def __init__(self, win32, is_alive: Callable[[int], bool]):
        self._win32 = win32
        self._is_alive = is_alive
        self.pinned: set[int] = set()

    # -- 查询 ---------------------------------------------------------------

    def is_pinned(self, hwnd: int) -> bool:
        return hwnd in self.pinned

    @property
    def count(self) -> int:
        return len(self.pinned)

    # -- 操作 ---------------------------------------------------------------

    def pin(self, hwnd: int) -> None:
        self._win32.set_topmost(hwnd)
        self.pinned.add(hwnd)

    def unpin(self, hwnd: int) -> None:
        self._win32.set_notopmost(hwnd)
        self.pinned.discard(hwnd)

    def toggle(self, hwnd: int | None) -> None:
        """目标已在置顶集合 → 取消；否则 → 置顶。忽略空句柄。"""
        if not hwnd:
            return
        if hwnd in self.pinned:
            self.unpin(hwnd)
        else:
            self.pin(hwnd)

    # -- 最前面的置顶窗口 ---------------------------------------------------

    def frontmost_pinned(self) -> int | None:
        """从 z 序最前遍历顶层窗口，返回第一个仍在 pinned 且类名仍为 XLMAIN 的窗口。"""
        hwnd = self._win32.get_top_window(None)
        while hwnd:
            if hwnd in self.pinned and self._is_alive(hwnd):
                return hwnd
            hwnd = self._win32.get_window(hwnd, self._win32.GW_HWNDNEXT)
        return None

    # -- 清理 ---------------------------------------------------------------

    def restore_all(self) -> None:
        """把 pinned 中所有仍存活且类名仍为 XLMAIN 的窗口还原为普通层级，并清空集合。

        句柄复用校验：`IsWindow` 通过不等于句柄仍指向 Excel 窗口，还必须校验类名。
        """
        for hwnd in list(self.pinned):
            if self._is_alive(hwnd):
                self._win32.set_notopmost(hwnd)
            self.pinned.discard(hwnd)

    def drop_dead(self, hwnd: int) -> None:
        """窗口销毁时及时从集合剔除（EVENT_OBJECT_DESTROY 回调调用）。"""
        self.pinned.discard(hwnd)
