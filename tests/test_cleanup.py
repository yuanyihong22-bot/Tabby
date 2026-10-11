"""test_cleanup：退出清理顺序 + 句柄复用校验。"""

from __future__ import annotations

from src.excel import ExcelTracker
from src.hotkey import Hotkey
from src.main import cleanup
from src.pinner import Pinner
from src.tray import Tray

XLMAIN = "XLMAIN"


class _FakeWnd:
    def __init__(self):
        self.uninstalled = False

    def uninstall_event_hooks(self):
        self.uninstalled = True


def make_stack(win32):
    excel = ExcelTracker(win32)
    pinner = Pinner(win32, is_alive=excel.is_alive)
    hotkey = Hotkey(win32)
    tray = Tray(win32)
    return pinner, hotkey, tray


def _order(win32, *names):
    """返回各记录名在 recorded 里首次出现的索引（找不到返回 None）。"""
    seq = [n for n, _ in win32.recorded]
    return [seq.index(n) if n in seq else None for n in names]


def test_cleanup_restores_all_pinned_windows(win32):
    pinner, hotkey, tray = make_stack(win32)
    for h in (1, 2):
        win32.add_window(h, class_name=XLMAIN, valid=True)
        pinner.pin(h)
    hotkey.hotkey_registered = True
    hotkey._hwnd = 0x1234
    tray._added = True
    tray._hwnd = 0x1234

    cleanup(pinner, hotkey, tray)

    assert set(win32.notopmost_set) == {1, 2}


def test_cleanup_order_restore_then_unregister_then_delete(win32):
    pinner, hotkey, tray = make_stack(win32)
    win32.add_window(1, class_name=XLMAIN, valid=True)
    pinner.pin(1)
    hotkey.hotkey_registered = True
    hotkey._hwnd = 0x1234
    tray._added = True
    tray._hwnd = 0x1234

    cleanup(pinner, hotkey, tray)

    i_restore, i_unregister, i_delete = _order(
        win32, "set_notopmost", "unregister_hot_key", "shell_notify_icon_delete"
    )
    assert i_restore is not None
    assert i_unregister is not None
    assert i_delete is not None
    assert i_restore < i_unregister < i_delete


def test_cleanup_skips_reused_handle(win32):
    pinner, hotkey, tray = make_stack(win32)
    win32.add_window(1, class_name=XLMAIN, valid=True)
    pinner.pin(1)
    # 句柄复用：仍存活但类名已变
    win32.class_names[1] = "Chrome_WidgetWin_1"

    cleanup(pinner, hotkey, tray)

    assert 1 not in win32.notopmost_set
    assert pinner.count == 0


def test_cleanup_is_idempotent(win32):
    pinner, hotkey, tray = make_stack(win32)
    win32.add_window(1, class_name=XLMAIN, valid=True)
    pinner.pin(1)
    hotkey.hotkey_registered = True
    hotkey._hwnd = 0x1234
    tray._added = True
    tray._hwnd = 0x1234

    cleanup(pinner, hotkey, tray)
    cleanup(pinner, hotkey, tray)

    # 只还原一次（第二次集合已空）
    assert win32.notopmost_set == [1]
    # 只注销一次热键、删除一次图标
    assert len(win32.hotkey_unregistered) == 1
    assert len(win32.notify_deleted) == 1


def test_cleanup_unhooks_event_hooks_when_wnd_present(win32):
    pinner, hotkey, tray = make_stack(win32)
    wnd = _FakeWnd()

    cleanup(pinner, hotkey, tray, wnd)

    assert wnd.uninstalled is True
