"""入口：装配各模块，进入消息循环，负责退出清理。

退出清理顺序（§4.5）：
  1. 还原所有被置顶窗口为 HWND_NOTOPMOST（含句柄复用校验）；
  2. UnregisterHotKey；
  3. Shell_NotifyIcon(NIM_DELETE)。
正常退出（菜单「退出」）走 finally 主路径；atexit 兜底。
"""

from __future__ import annotations

import atexit

from . import win32
from .excel import ExcelTracker
from .hotkey import Hotkey
from .pinner import Pinner
from .tray import Tray
from .wnd import Window


def cleanup(pinner: Pinner, hotkey: Hotkey, tray: Tray, wnd: Window | None = None) -> None:
    """按顺序清理，幂等（可重复调用）。"""
    pinner.restore_all()
    hotkey.unregister()
    tray.delete()
    if wnd is not None:
        wnd.uninstall_event_hooks()


def main() -> int:
    if win32.create_mutex("ExcelPinTool.SingleInstance"):
        # 已有实例在运行：提示后直接退出，避免重复进程互相抢占热键
        win32.message_box("Excel 置顶已在运行。\n请查看右下角任务栏托盘图标。", "Excel 置顶")
        return 0

    excel = ExcelTracker(win32)
    pinner = Pinner(win32, is_alive=excel.is_alive)
    hotkey = Hotkey(win32)
    tray = Tray(win32)
    wnd = Window(win32, pinner, excel, tray, hotkey)

    atexit.register(cleanup, pinner, hotkey, tray, wnd)
    try:
        return wnd.run()
    finally:
        cleanup(pinner, hotkey, tray, wnd)


if __name__ == "__main__":
    raise SystemExit(main())
