"""测试夹具：FakeWin32 替代真实 Win32 层，记录调用并支持按需配置返回值。

业务模块通过构造器注入 win32 依赖，测试直接传 FakeWin32 实例，无需真实 Windows。
"""

from __future__ import annotations

import pytest


class FakeWin32:
    """可配置、记录调用的 win32 接缝替身。"""

    # ---- 常量（与 src/win32.py 对齐）----
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x2
    SWP_NOSIZE = 0x1
    SWP_NOACTIVATE = 0x10
    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x8
    GW_HWNDNEXT = 2
    MOD_CONTROL = 0x2
    MOD_WIN = 0x8
    MOD_NOREPEAT = 0x4000
    VK_T = 0x54
    WM_HOTKEY = 0x312
    WM_COMMAND = 0x111
    WM_DESTROY = 0x2
    WM_CLOSE = 0x10
    WM_QUIT = 0x12
    WM_RBUTTONUP = 0x205
    WM_LBUTTONUP = 0x202
    WM_LBUTTONDOWN = 0x201
    WM_LBUTTONDBLCLK = 0x203
    WM_CONTEXTMENU = 0x7B
    WM_USER = 0x400
    WM_APP = 0x8000
    NIM_ADD = 0
    NIM_MODIFY = 1
    NIM_DELETE = 2
    NIF_ICON = 0x2
    NIF_MESSAGE = 0x1
    NIF_TIP = 0x4
    MF_STRING = 0x0
    MF_SEPARATOR = 0x800
    MF_GRAYED = 0x1
    TPM_RETURNCMD = 0x100
    TPM_NONOTIFY = 0x80
    TPM_RIGHTBUTTON = 0x2
    WINEVENT_OUTOFCONTEXT = 0x0
    WINEVENT_SKIPOWNPROCESS = 0x2
    EVENT_SYSTEM_FOREGROUND = 0x3
    EVENT_OBJECT_DESTROY = 0x8001
    OBJID_WINDOW = 0x0

    def __init__(self):
        # 记录
        self.recorded: list[tuple] = []
        self.topmost_set: list[int] = []
        self.notopmost_set: list[int] = []
        self.hotkey_registered: list[tuple] = []   # (hwnd, id, mods, vk)
        self.hotkey_unregistered: list[tuple] = []
        self.notify_added: list[tuple] = []
        self.notify_modified: list[tuple] = []
        self.notify_deleted: list[tuple] = []
        self.win_event_hooks: list[tuple] = []
        self.unhooked: list[int] = []
        self.quit_posted = 0

        # 窗口数据
        self.class_names: dict[int, str] = {}
        self.process_names: dict[int, str] = {}
        self.valid: set[int] = set()      # is_window() 返回 True 的句柄
        self.topmost_flags: dict[int, bool] = {}
        self.zorder: list[int] = []       # 从前往后
        self.foreground = 0

        # 热键注册结果队列
        self.hotkey_results: list[bool] = []
        # 托盘菜单返回值
        self.menu_result = 0
        # 单实例互斥体返回值（True = 已存在）
        self.mutex_already_exists = False
        self.mutex_names: list[str] = []
        self.messages_shown: list[tuple] = []
        self.balloons: list[tuple] = []

    # ---- 记录辅助 ----
    def _rec(self, name, *args):
        self.recorded.append((name, args))

    def add_window(self, hwnd, class_name="XLMAIN", process="EXCEL.EXE", valid=True):
        self.class_names[hwnd] = class_name
        self.process_names[hwnd] = process
        if valid:
            self.valid.add(hwnd)

    # ---- 窗口操作 ----
    def set_window_pos(self, hwnd, insert_after, flags):
        self._rec("set_window_pos", hwnd, insert_after, flags)

    def set_topmost(self, hwnd):
        self._rec("set_topmost", hwnd)
        self.topmost_set.append(hwnd)
        self.topmost_flags[hwnd] = True

    def set_notopmost(self, hwnd):
        self._rec("set_notopmost", hwnd)
        self.notopmost_set.append(hwnd)
        self.topmost_flags[hwnd] = False

    def is_topmost(self, hwnd):
        return self.topmost_flags.get(hwnd, False)

    def is_window(self, hwnd):
        return hwnd in self.valid

    def get_class_name(self, hwnd):
        return self.class_names.get(hwnd, "")

    def get_process_name(self, hwnd):
        return self.process_names.get(hwnd)

    def enum_windows(self):
        return list(self.class_names.keys())

    def get_foreground_window(self):
        return self.foreground

    def set_foreground_window(self, hwnd):
        self.foreground = hwnd

    def get_top_window(self, hwnd):
        return self.zorder[0] if self.zorder else 0

    def get_window(self, hwnd, cmd):
        if cmd != self.GW_HWNDNEXT or hwnd not in self.zorder:
            return 0
        idx = self.zorder.index(hwnd)
        return self.zorder[idx + 1] if idx + 1 < len(self.zorder) else 0

    # ---- 热键 ----
    def register_hot_key(self, hwnd, hotkey_id, modifiers, vk):
        self._rec("register_hot_key", hwnd, hotkey_id, modifiers, vk)
        if self.hotkey_results:
            ok = self.hotkey_results.pop(0)
        else:
            ok = True
        if ok:
            self.hotkey_registered.append((hwnd, hotkey_id, modifiers, vk))
        return ok

    def unregister_hot_key(self, hwnd, hotkey_id):
        self._rec("unregister_hot_key", hwnd, hotkey_id)
        self.hotkey_unregistered.append((hwnd, hotkey_id))

    # ---- 事件钩子 ----
    def set_win_event_hook(self, event_min, event_max, callback):
        self._rec("set_win_event_hook", event_min, event_max)
        handle = len(self.win_event_hooks) + 1
        self.win_event_hooks.append((event_min, event_max, callback))
        return handle

    def unhook_win_event(self, handle):
        self._rec("unhook_win_event", handle)
        self.unhooked.append(handle)

    # ---- 托盘 / 菜单 ----
    def shell_notify_icon_add(self, hwnd, callback_message, tip):
        self._rec("shell_notify_icon_add", hwnd, callback_message, tip)
        self.notify_added.append((hwnd, callback_message, tip))
        return True

    def shell_notify_icon_modify(self, hwnd, callback_message, tip):
        self._rec("shell_notify_icon_modify", hwnd, callback_message, tip)
        self.notify_modified.append((hwnd, callback_message, tip))

    def shell_notify_icon_delete(self, hwnd):
        self._rec("shell_notify_icon_delete", hwnd)
        self.notify_deleted.append(hwnd)

    def create_popup_menu(self):
        return 100

    def append_menu_item(self, menu, flags, item_id, text):
        self._rec("append_menu_item", menu, flags, item_id, text)

    def get_cursor_pos(self):
        return (10, 10)

    def track_popup_menu(self, menu, flags, x, y, hwnd):
        self._rec("track_popup_menu", menu, flags, x, y, hwnd)
        return self.menu_result

    def destroy_menu(self, menu):
        self._rec("destroy_menu", menu)

    # ---- 单实例 / 提示 / 气泡 ----
    def create_mutex(self, name):
        self._rec("create_mutex", name)
        self.mutex_names.append(name)
        return self.mutex_already_exists

    def message_box(self, text, title):
        self._rec("message_box", text, title)
        self.messages_shown.append((text, title))
        return 1

    def show_balloon(self, hwnd, title, text):
        self._rec("show_balloon", hwnd, title, text)
        self.balloons.append((hwnd, title, text))
        return True

    # ---- 消息循环 ----
    def register_class(self, class_name, message_map):
        self._rec("register_class", class_name)
        return 1

    def create_window(self, class_name, window_name=""):
        self._rec("create_window", class_name, window_name)
        return 0x1234

    def pump_messages(self):
        self._rec("pump_messages")

    def post_quit_message(self):
        self._rec("post_quit_message")
        self.quit_posted += 1


@pytest.fixture
def win32():
    return FakeWin32()
