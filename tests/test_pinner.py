"""test_pinner：切换语义、集合增删、frontmost 判定、句柄复用校验、清理顺序。"""

from __future__ import annotations

from src.pinner import Pinner

XLMAIN = "XLMAIN"


def make_pinner(win32):
    def is_alive(hwnd):
        return win32.is_window(hwnd) and win32.get_class_name(hwnd) == XLMAIN
    return Pinner(win32, is_alive)


# -- 切换语义 ---------------------------------------------------------------

def test_toggle_pins_when_not_pinned(win32):
    pinner = make_pinner(win32)
    win32.add_window(10)

    pinner.toggle(10)

    assert pinner.is_pinned(10)
    assert pinner.count == 1
    assert 10 in win32.topmost_set


def test_toggle_unpins_when_already_pinned(win32):
    pinner = make_pinner(win32)
    win32.add_window(10)

    pinner.toggle(10)
    pinner.toggle(10)

    assert not pinner.is_pinned(10)
    assert pinner.count == 0
    assert 10 in win32.notopmost_set


def test_toggle_ignores_empty_handle(win32):
    pinner = make_pinner(win32)

    pinner.toggle(None)
    pinner.toggle(0)

    assert pinner.count == 0
    assert win32.topmost_set == []


# -- 集合增删 ---------------------------------------------------------------

def test_multiple_windows_pin_independently(win32):
    pinner = make_pinner(win32)
    win32.add_window(1)
    win32.add_window(2)

    pinner.pin(1)
    pinner.pin(2)
    pinner.unpin(1)

    assert not pinner.is_pinned(1)
    assert pinner.is_pinned(2)
    assert pinner.count == 1


def test_drop_dead_removes_handle(win32):
    pinner = make_pinner(win32)
    win32.add_window(1)
    pinner.pin(1)

    pinner.drop_dead(1)

    assert pinner.count == 0


# -- frontmost 判定 ---------------------------------------------------------

def test_frontmost_pinned_returns_frontmost_pinned_xlmain(win32):
    pinner = make_pinner(win32)
    # z 序从前到后：5(普通) 4(置顶) 3(普通) 2(置顶但已变类名)
    win32.add_window(5)
    win32.add_window(4)
    win32.add_window(3)
    win32.add_window(2)
    win32.zorder = [5, 4, 3, 2]
    pinner.pinned = {4, 2}
    # 2 的类名已非 XLMAIN（句柄复用），应跳过
    win32.class_names[2] = "SomeOtherClass"

    assert pinner.frontmost_pinned() == 4


def test_frontmost_pinned_returns_none_when_nothing_pinned(win32):
    pinner = make_pinner(win32)
    win32.add_window(5)
    win32.zorder = [5]

    assert pinner.frontmost_pinned() is None


# -- 句柄复用校验 / 清理 -----------------------------------------------------

def test_restore_all_skips_reused_handle(win32):
    pinner = make_pinner(win32)
    win32.add_window(10, class_name=XLMAIN, valid=True)
    win32.add_window(11, class_name=XLMAIN, valid=True)
    pinner.pin(10)
    pinner.pin(11)

    # 句柄 11 被复用：IsWindow 仍 True，但类名已不是 XLMAIN
    win32.class_names[11] = "Chrome_WidgetWin_1"

    pinner.restore_all()

    # 10 被还原，11 不被还原（防误伤复用后的窗口）
    assert 10 in win32.notopmost_set
    assert 11 not in win32.notopmost_set
    # 集合都被清空
    assert pinner.count == 0


def test_restore_all_skips_dead_handle(win32):
    pinner = make_pinner(win32)
    win32.add_window(10, class_name=XLMAIN, valid=True)
    win32.add_window(11, class_name=XLMAIN, valid=True)
    pinner.pin(10)
    pinner.pin(11)
    # 11 已销毁
    win32.valid.discard(11)

    pinner.restore_all()

    assert 10 in win32.notopmost_set
    assert 11 not in win32.notopmost_set
    assert pinner.count == 0


def test_restore_all_restores_every_alive_pinned_window(win32):
    pinner = make_pinner(win32)
    for h in (1, 2, 3):
        win32.add_window(h)
        pinner.pin(h)

    pinner.restore_all()

    assert set(win32.notopmost_set) == {1, 2, 3}
    assert pinner.count == 0
