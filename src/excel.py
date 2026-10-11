"""窗口识别、最近激活工作簿跟踪、目标判定。

`last_excel_hwnd` 归本模块持有，对外暴露 `target_hwnd()`。
"""

from __future__ import annotations

XLMAIN = "XLMAIN"
XLDESK = "XLDESK"
EXCEL_PROCESS = "EXCEL.EXE"


class ExcelTracker:
    """识别 Excel 工作簿窗口，跟踪最近激活的工作簿，并按优先级判定快捷键目标。"""

    def __init__(self, win32):
        self._win32 = win32
        self.last_excel_hwnd: int | None = None

    # -- 识别 ---------------------------------------------------------------

    def is_xlmain(self, hwnd: int) -> bool:
        """仅按类名判定（快路径，用于事件回调）。"""
        return bool(hwnd) and self._win32.get_class_name(hwnd) == XLMAIN

    def is_excel_window(self, hwnd: int) -> bool:
        """完整判定：类名 XLMAIN 且进程 EXCEL.EXE（用于枚举，排除 XLDESK 等壳窗口）。"""
        if not self.is_xlmain(hwnd):
            return False
        return self._win32.get_process_name(hwnd) == EXCEL_PROCESS

    def is_alive(self, hwnd: int) -> bool:
        """句柄仍存活且类名仍为 XLMAIN（防句柄复用）。"""
        return bool(hwnd) and self._win32.is_window(hwnd) and self.is_xlmain(hwnd)

    def enumerate_windows(self) -> list[int]:
        return [h for h in self._win32.enum_windows() if self.is_excel_window(h)]

    # -- 事件跟踪 -----------------------------------------------------------

    def on_foreground(self, hwnd: int, event: int, id_object: int, id_child: int) -> None:
        """EVENT_SYSTEM_FOREGROUND 回调：直接读事件 hwnd（正在成为前台的窗口）。"""
        if self.is_xlmain(hwnd):
            self.last_excel_hwnd = hwnd

    def on_destroy(self, hwnd: int, event: int, id_object: int, id_child: int) -> None:
        """EVENT_OBJECT_DESTROY 回调：窗口销毁时清掉最近激活记录（集合由 pinner 负责）。"""
        if hwnd and hwnd == self.last_excel_hwnd:
            self.last_excel_hwnd = None

    # -- 目标判定 -----------------------------------------------------------

    def target_hwnd(self, pinner) -> int | None:
        """按优先级判定快捷键目标：

        1. 前台窗口若是 Excel 工作簿 → 用它；
        2. 否则 → 置顶中排在最前面的工作簿；
        3. 否则 → 最近激活过的工作簿。
        """
        foreground = self._win32.get_foreground_window()
        if self.is_xlmain(foreground):
            return foreground

        frontmost = pinner.frontmost_pinned()
        if frontmost is not None:
            return frontmost

        if self.last_excel_hwnd is not None and self.is_alive(self.last_excel_hwnd):
            return self.last_excel_hwnd

        return None
