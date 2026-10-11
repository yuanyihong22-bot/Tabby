"""托盘图标 + 右键菜单。"""

from __future__ import annotations

ID_STATUS = 1001
ID_EXIT = 1002


class Tray:
    """托盘图标：显示状态 tooltip，右键菜单含「当前状态」「退出」。"""

    def __init__(self, win32):
        self._win32 = win32
        self._hwnd: int | None = None
        self._callback_message: int = 0
        self._added = False

    def add(self, hwnd: int, callback_message: int) -> None:
        self._hwnd = hwnd
        self._callback_message = callback_message
        self._added = self._win32.shell_notify_icon_add(hwnd, callback_message, "未置顶")

    def modify(self, tip: str) -> None:
        if self._added and self._hwnd is not None:
            self._win32.shell_notify_icon_modify(self._hwnd, self._callback_message, tip)

    def delete(self) -> None:
        if self._added and self._hwnd is not None:
            self._win32.shell_notify_icon_delete(self._hwnd)
        self._added = False

    def show_menu(self, status_text: str) -> int | None:
        """弹出右键菜单，返回选中的命令 id（ID_EXIT / 未选中 None）。"""
        if self._hwnd is None:
            return None
        menu = self._win32.create_popup_menu()
        w = self._win32
        w.append_menu_item(menu, w.MF_STRING | w.MF_GRAYED, ID_STATUS, status_text)
        w.append_menu_item(menu, w.MF_SEPARATOR, 0, "")
        w.append_menu_item(menu, w.MF_STRING, ID_EXIT, "退出")
        x, y = w.get_cursor_pos()
        w.set_foreground_window(self._hwnd)  # 保证菜单点击后能正确关闭
        flags = w.TPM_RETURNCMD | w.TPM_NONOTIFY | w.TPM_RIGHTBUTTON
        cmd = w.track_popup_menu(menu, flags, x, y, self._hwnd)
        w.destroy_menu(menu)
        return cmd or None
