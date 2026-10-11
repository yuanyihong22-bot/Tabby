"""test_wnd：消息路由（热键 → 目标判定 → 切换）与状态文案。"""

from __future__ import annotations

from src.excel import ExcelTracker
from src.hotkey import Hotkey
from src.pinner import Pinner
from src.wnd import Window

XLMAIN = "XLMAIN"


class _FakeTray:
    def __init__(self):
        self.tips = []

    def add(self, hwnd, callback_message):
        pass

    def modify(self, tip):
        self.tips.append(tip)


def make_window(win32):
    excel = ExcelTracker(win32)
    pinner = Pinner(win32, is_alive=excel.is_alive)
    hotkey = Hotkey(win32)
    tray = _FakeTray()
    wnd = Window(win32, pinner, excel, tray, hotkey)
    return wnd, pinner, excel, tray


def test_handle_hotkey_toggles_target(win32):
    wnd, pinner, excel, _ = make_window(win32)
    win32.add_window(1, class_name=XLMAIN)
    win32.foreground = 1

    wnd.handle_hotkey()

    assert pinner.is_pinned(1)
    assert 1 in win32.topmost_set


def test_handle_hotkey_noop_when_no_target(win32):
    wnd, pinner, excel, _ = make_window(win32)
    win32.foreground = 0  # 无前台窗口、无置顶、无最近激活

    wnd.handle_hotkey()

    assert pinner.count == 0
    assert win32.topmost_set == []


def test_status_text_reflects_count(win32):
    wnd, pinner, excel, _ = make_window(win32)
    wnd._hotkey.hotkey_registered = True

    assert wnd._status_text() == "未置顶"
    win32.add_window(1, class_name=XLMAIN)
    win32.add_window(2, class_name=XLMAIN)
    pinner.pin(1)
    pinner.pin(2)
    assert wnd._status_text() == "已置顶 2 个窗口"


def test_status_text_when_hotkey_not_registered(win32):
    wnd, pinner, excel, _ = make_window(win32)
    wnd._hotkey.hotkey_registered = False

    assert wnd._status_text() == "热键未注册"


def test_startup_balloon_when_registered(win32):
    wnd, pinner, excel, _ = make_window(win32)
    wnd.hwnd = 0x1234
    wnd._hotkey.hotkey_registered = True
    wnd._hotkey.current_key = "T"

    wnd._show_startup_balloon()

    assert len(win32.balloons) == 1
    hwnd, title, text = win32.balloons[0]
    assert hwnd == 0x1234
    assert title == "Excel 置顶已启动"
    assert "Win+Ctrl+T" in text


def test_startup_balloon_when_not_registered(win32):
    wnd, pinner, excel, _ = make_window(win32)
    wnd.hwnd = 0x1234
    wnd._hotkey.hotkey_registered = False

    wnd._show_startup_balloon()

    assert len(win32.balloons) == 1
    assert "热键未注册" in win32.balloons[0][1]
