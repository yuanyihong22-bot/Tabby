"""隐藏消息窗口 + WndProc（消息路由）。

只做路由：收到 WM_HOTKEY 后调 excel.target_hwnd() 拿目标，再调 pinner.toggle(target)；
不直接读写 pinned / last_excel_hwnd，只走公开接口。
"""

from __future__ import annotations

from . import tray as tray_mod


class Window:
    """隐藏窗口：承载热键消息、托盘回调与事件钩子所在的消息循环。"""

    CLASS_NAME = "ExcelPinMessageWindow"

    def __init__(self, win32, pinner, excel, tray, hotkey):
        self._win32 = win32
        self._pinner = pinner
        self._excel = excel
        self._tray = tray
        self._hotkey = hotkey
        self.hwnd: int | None = None
        self._tray_msg = win32.WM_APP + 1
        self._hook_handles: list[int] = []

    # -- 生命周期 -----------------------------------------------------------

    def run(self) -> int:
        self.hwnd = self._create_hidden_window()
        self._tray.add(self.hwnd, self._tray_msg)
        self._hotkey.register(self.hwnd)
        self._install_event_hooks()
        self._update_tooltip()
        self._show_startup_balloon()
        self._win32.pump_messages()
        return 0

    def _show_startup_balloon(self) -> None:
        if self._hotkey.hotkey_registered:
            self._win32.show_balloon(
                self.hwnd, "Excel 置顶已启动",
                f"按 Win+Ctrl+{self._hotkey.current_key} 切换置顶，右键托盘退出",
            )
        else:
            self._win32.show_balloon(
                self.hwnd, "Excel 置顶已启动（热键未注册）",
                "快捷键被占用，请右键托盘查看",
            )

    def request_exit(self) -> None:
        self._win32.post_quit_message()

    def uninstall_event_hooks(self) -> None:
        for handle in self._hook_handles:
            self._win32.unhook_win_event(handle)
        self._hook_handles.clear()

    # -- 窗口创建 -----------------------------------------------------------

    def _create_hidden_window(self) -> int:
        self._win32.register_class(self.CLASS_NAME, self._message_map())
        return self._win32.create_window(self.CLASS_NAME, "ExcelPin")

    def _message_map(self) -> dict:
        return {
            self._win32.WM_HOTKEY: self._on_hotkey,
            self._tray_msg: self._on_tray,
            self._win32.WM_DESTROY: self._on_destroy,
        }

    # -- 事件钩子 -----------------------------------------------------------

    def _install_event_hooks(self) -> None:
        w = self._win32
        self._hook_handles.append(
            w.set_win_event_hook(
                w.EVENT_SYSTEM_FOREGROUND, w.EVENT_SYSTEM_FOREGROUND,
                self._excel.on_foreground,
            )
        )
        self._hook_handles.append(
            w.set_win_event_hook(
                w.EVENT_OBJECT_DESTROY, w.EVENT_OBJECT_DESTROY,
                self._on_object_destroy,
            )
        )

    def _on_object_destroy(self, hwnd: int, event: int, id_object: int, id_child: int) -> None:
        if id_object == self._win32.OBJID_WINDOW:
            self._excel.on_destroy(hwnd, event, id_object, id_child)
            self._pinner.drop_dead(hwnd)

    # -- 消息路由 -----------------------------------------------------------

    def _on_hotkey(self, hwnd, msg, wparam, lparam) -> int:
        self.handle_hotkey()
        return 0

    def handle_hotkey(self) -> None:
        """快捷键核心逻辑（独立出来便于单测）。"""
        target = self._excel.target_hwnd(self._pinner)
        if target is not None:
            self._pinner.toggle(target)
        self._update_tooltip()

    def _on_tray(self, hwnd, msg, wparam, lparam) -> int:
        if lparam in (self._win32.WM_RBUTTONUP, self._win32.WM_CONTEXTMENU):
            self.handle_tray_menu()
        return 0

    def handle_tray_menu(self) -> None:
        cmd = self._tray.show_menu(self._status_text())
        if cmd == tray_mod.ID_EXIT:
            self.request_exit()

    def _on_destroy(self, hwnd, msg, wparam, lparam) -> int:
        self._win32.post_quit_message()
        return 0

    # -- 状态提示 -----------------------------------------------------------

    def _status_text(self) -> str:
        if not self._hotkey.hotkey_registered:
            return "热键未注册"
        n = self._pinner.count
        return f"已置顶 {n} 个窗口" if n else "未置顶"

    def _update_tooltip(self) -> None:
        self._tray.modify(self._status_text())
