"""Win32 调用的薄封装层。

这是整个项目里**唯一**直接 import win32* / ctypes 的地方。业务模块只依赖本模块，
测试时用 pytest 的 monkeypatch 替换本模块的函数即可，无需真实 Windows / Excel 环境。

约定：业务模块一律通过模块引用调用（`win32.set_window_pos(...)`），
不要 `from .win32 import xxx`，否则 monkeypatch 会失效。
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

import win32api
import win32con
import win32event
import win32gui
import win32process
import winerror

# ---------------------------------------------------------------------------
# 常量（re-export，供业务模块统一从本模块取值）
# ---------------------------------------------------------------------------

# 置顶 / 层级
HWND_TOPMOST = win32con.HWND_TOPMOST
HWND_NOTOPMOST = win32con.HWND_NOTOPMOST
SWP_NOMOVE = win32con.SWP_NOMOVE
SWP_NOSIZE = win32con.SWP_NOSIZE
SWP_NOACTIVATE = win32con.SWP_NOACTIVATE

# 扩展样式
GWL_EXSTYLE = win32con.GWL_EXSTYLE
WS_EX_TOPMOST = win32con.WS_EX_TOPMOST

# 窗口遍历
GW_HWNDNEXT = win32con.GW_HWNDNEXT

# 热键修饰键 / 虚拟键
MOD_CONTROL = win32con.MOD_CONTROL
MOD_WIN = win32con.MOD_WIN
MOD_NOREPEAT = win32con.MOD_NOREPEAT
VK_T = 0x54  # ord('T')；win32con 未暴露字母键虚拟键码

# 窗口消息
WM_HOTKEY = win32con.WM_HOTKEY
WM_COMMAND = win32con.WM_COMMAND
WM_DESTROY = win32con.WM_DESTROY
WM_CLOSE = win32con.WM_CLOSE
WM_QUIT = win32con.WM_QUIT
WM_RBUTTONUP = win32con.WM_RBUTTONUP
WM_LBUTTONUP = win32con.WM_LBUTTONUP
WM_LBUTTONDOWN = win32con.WM_LBUTTONDOWN
WM_LBUTTONDBLCLK = win32con.WM_LBUTTONDBLCLK
WM_CONTEXTMENU = win32con.WM_CONTEXTMENU
WM_USER = win32con.WM_USER
WM_APP = win32con.WM_APP

# 窗口类 / 样式
CS_HREDRAW = win32con.CS_HREDRAW
CS_VREDRAW = win32con.CS_VREDRAW
WS_OVERLAPPED = win32con.WS_OVERLAPPED
WS_POPUP = win32con.WS_POPUP
COLOR_WINDOW = win32con.COLOR_WINDOW
IDC_ARROW = win32con.IDC_ARROW
IDI_APPLICATION = win32con.IDI_APPLICATION
SW_HIDE = win32con.SW_HIDE

# 菜单
MF_STRING = win32con.MF_STRING
MF_SEPARATOR = win32con.MF_SEPARATOR
MF_GRAYED = win32con.MF_GRAYED
MF_DISABLED = win32con.MF_DISABLED
TPM_RETURNCMD = win32con.TPM_RETURNCMD
TPM_NONOTIFY = win32con.TPM_NONOTIFY
TPM_RIGHTBUTTON = win32con.TPM_RIGHTBUTTON
TPM_BOTTOMALIGN = win32con.TPM_BOTTOMALIGN
TPM_LEFTALIGN = win32con.TPM_LEFTALIGN

# 进程
PROCESS_QUERY_LIMITED_INFORMATION = win32con.PROCESS_QUERY_LIMITED_INFORMATION

# 托盘（win32gui 暴露）
NIM_ADD = win32gui.NIM_ADD
NIM_MODIFY = win32gui.NIM_MODIFY
NIM_DELETE = win32gui.NIM_DELETE
NIF_ICON = win32gui.NIF_ICON
NIF_MESSAGE = win32gui.NIF_MESSAGE
NIF_TIP = win32gui.NIF_TIP

# WinEvent（pywin32 未暴露，经 ctypes 直调 user32）
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002
EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_DESTROY = 0x8001
OBJID_WINDOW = 0x00000000

# 单实例 / 托盘气泡
ERROR_ALREADY_EXISTS = winerror.ERROR_ALREADY_EXISTS  # 183
NIF_INFO = 0x10
NIIF_INFO = 0x1


# ---------------------------------------------------------------------------
# 窗口操作
# ---------------------------------------------------------------------------

def set_window_pos(hwnd: int, insert_after: int, flags: int) -> None:
    win32gui.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)


def set_topmost(hwnd: int) -> None:
    set_window_pos(hwnd, HWND_TOPMOST, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def set_notopmost(hwnd: int) -> None:
    set_window_pos(hwnd, HWND_NOTOPMOST, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def is_topmost(hwnd: int) -> bool:
    return bool(win32api.GetWindowLong(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST)


def is_window(hwnd: int) -> bool:
    return bool(win32gui.IsWindow(hwnd))


def get_class_name(hwnd: int) -> str:
    return win32gui.GetClassName(hwnd)


def enum_windows() -> list[int]:
    return list(win32gui.EnumWindows())


def get_foreground_window() -> int:
    return win32gui.GetForegroundWindow()


def set_foreground_window(hwnd: int) -> None:
    win32gui.SetForegroundWindow(hwnd)


def get_top_window(hwnd: int | None) -> int:
    return win32gui.GetTopWindow(hwnd)


def get_window(hwnd: int, cmd: int) -> int:
    return win32gui.GetWindow(hwnd, cmd)


# ---------------------------------------------------------------------------
# 进程名（用于识别 EXCEL.EXE）
# ---------------------------------------------------------------------------

def get_process_name(hwnd: int) -> str | None:
    """返回窗口所属进程的可执行文件名（如 'EXCEL.EXE'），失败返回 None。"""
    try:
        _tid, pid = win32process.GetWindowThreadProcessId(hwnd)  # pywin32 返回 (threadId, processId)
        handle = win32api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            path = win32process.GetModuleFileNameEx(handle, 0)
            return os.path.basename(path).upper()
        finally:
            win32api.CloseHandle(handle)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 全局热键
# ---------------------------------------------------------------------------

def register_hot_key(hwnd: int | None, hotkey_id: int, modifiers: int, vk: int) -> bool:
    """注册全局热键，成功返回 True，冲突（被占用）返回 False。"""
    try:
        win32gui.RegisterHotKey(hwnd, hotkey_id, modifiers, vk)
        return True
    except Exception:
        return False


def unregister_hot_key(hwnd: int | None, hotkey_id: int) -> None:
    try:
        win32gui.UnregisterHotKey(hwnd, hotkey_id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# WinEvent 钩子（pywin32 未暴露，ctypes 直调 user32）
# ---------------------------------------------------------------------------

_user32 = ctypes.WinDLL("user32", use_last_error=True)

_WinEventProc = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,   # hWinEventHook
    wintypes.DWORD,    # event
    wintypes.HWND,     # hwnd
    wintypes.LONG,     # idObject
    wintypes.LONG,     # idChild
    wintypes.DWORD,    # dwEventThread
    wintypes.DWORD,    # dwmsEventTime
)

_user32.SetWinEventHook.argtypes = [
    wintypes.DWORD, wintypes.DWORD, wintypes.HMODULE,
    _WinEventProc, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
]
_user32.SetWinEventHook.restype = wintypes.HANDLE
_user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
_user32.UnhookWinEvent.restype = wintypes.BOOL

# 持有 ctypes 回调引用，防止被 GC 回收导致崩溃（key: 钩子句柄）
_event_hooks: dict[int, "_WinEventProc"] = {}


def set_win_event_hook(event_min: int, event_max: int, callback) -> int:
    """注册 WinEvent 钩子。callback(hwnd, event, id_object, id_child) 在注册线程
    的消息循环里被调用（WINEVENT_OUTOFCONTEXT）。返回钩子句柄，0 表示失败。"""
    def _cb(hook, event, hwnd, id_object, id_child, thread, time):
        callback(int(hwnd), int(event), int(id_object), int(id_child))

    proc = _WinEventProc(_cb)
    handle = _user32.SetWinEventHook(
        event_min, event_max, None, proc, 0, 0,
        WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
    )
    if not handle:
        return 0
    _event_hooks[int(handle)] = proc
    return int(handle)


def unhook_win_event(handle: int) -> None:
    if handle:
        _user32.UnhookWinEvent(wintypes.HANDLE(handle))
        _event_hooks.pop(int(handle), None)


# ---------------------------------------------------------------------------
# 隐藏消息窗口
# ---------------------------------------------------------------------------

def register_class(class_name: str, message_map: dict) -> int:
    wc = win32gui.WNDCLASS()
    wc.style = CS_HREDRAW | CS_VREDRAW
    wc.lpfnWndProc = message_map
    wc.hInstance = win32api.GetModuleHandle(None)
    wc.hCursor = win32gui.LoadCursor(0, IDC_ARROW)
    wc.hbrBackground = COLOR_WINDOW
    wc.lpszClassName = class_name
    return win32gui.RegisterClass(wc)


def create_window(class_name: str, window_name: str = "") -> int:
    return win32gui.CreateWindow(
        class_name, window_name, WS_OVERLAPPED,
        0, 0, 0, 0,
        0, 0, win32api.GetModuleHandle(None), None,
    )


def pump_messages() -> None:
    win32gui.PumpMessages()


def post_message(hwnd: int, msg: int, wparam: int, lparam: int) -> None:
    win32gui.PostMessage(hwnd, msg, wparam, lparam)


def post_quit_message() -> None:
    win32gui.PostQuitMessage(0)


# ---------------------------------------------------------------------------
# 托盘图标
# ---------------------------------------------------------------------------

def _notify_data(hwnd: int, callback_message: int, icon: int, tip: str):
    return (
        hwnd,                       # hWnd
        1,                          # uID
        NIF_ICON | NIF_MESSAGE | NIF_TIP,  # uFlags
        callback_message,           # uCallbackMessage
        icon,                       # hIcon
        tip,                        # szTip
    )


def shell_notify_icon_add(hwnd: int, callback_message: int, tip: str) -> bool:
    try:
        icon = win32gui.LoadIcon(0, IDI_APPLICATION)
        win32gui.Shell_NotifyIcon(NIM_ADD, _notify_data(hwnd, callback_message, icon, tip))
        return True
    except Exception:
        return False


def shell_notify_icon_modify(hwnd: int, callback_message: int, tip: str) -> None:
    icon = win32gui.LoadIcon(0, IDI_APPLICATION)
    win32gui.Shell_NotifyIcon(NIM_MODIFY, _notify_data(hwnd, callback_message, icon, tip))


def shell_notify_icon_delete(hwnd: int) -> None:
    try:
        win32gui.Shell_NotifyIcon(NIM_DELETE, (hwnd, 1))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 弹出菜单
# ---------------------------------------------------------------------------

def create_popup_menu() -> int:
    return win32gui.CreatePopupMenu()


def append_menu_item(menu: int, flags: int, item_id: int, text: str) -> None:
    win32gui.AppendMenu(menu, flags, item_id, text)


def get_cursor_pos() -> tuple[int, int]:
    return win32api.GetCursorPos()


def track_popup_menu(menu: int, flags: int, x: int, y: int, hwnd: int) -> int:
    """返回选中的命令 id；未选中返回 0。"""
    return win32gui.TrackPopupMenu(menu, flags, x, y, 0, hwnd, None)


def destroy_menu(menu: int) -> None:
    win32gui.DestroyMenu(menu)


# ---------------------------------------------------------------------------
# 单实例 / 提示框 / 托盘气泡
# ---------------------------------------------------------------------------

_mutex_handles: dict[str, object] = {}


def create_mutex(name: str) -> bool:
    """创建命名互斥体用于单实例检测。返回 True 表示已存在（即本进程非首个实例）。

    句柄保存在模块级，进程存活期间不释放，从而保证互斥体一直有效。
    """
    handle = win32event.CreateMutex(None, False, name)
    _mutex_handles[name] = handle
    return win32api.GetLastError() == ERROR_ALREADY_EXISTS


def message_box(text: str, title: str) -> int:
    return win32gui.MessageBox(0, text, title, win32con.MB_OK | win32con.MB_ICONINFORMATION)


# --- 托盘气泡（ctypes 直调 Shell_NotifyIconW，pywin32 的 tuple 接口不带标题字段） ---

_shell32 = ctypes.WinDLL("shell32", use_last_error=True)


class _NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeout", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
    ]


_shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(_NOTIFYICONDATAW)]
_shell32.Shell_NotifyIconW.restype = wintypes.BOOL


def show_balloon(hwnd: int, title: str, text: str) -> bool:
    """在托盘图标上弹一个气泡提示（NIM_MODIFY + NIF_INFO）。"""
    nid = _NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(_NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_INFO
    nid.szInfo = text
    nid.szInfoTitle = title
    nid.uTimeout = 5000
    nid.dwInfoFlags = NIIF_INFO
    return bool(_shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid)))
