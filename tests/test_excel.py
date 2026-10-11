"""test_excel：窗口筛选 / 目标判定优先级。"""

from __future__ import annotations

from src.excel import ExcelTracker
from src.pinner import Pinner

XLMAIN = "XLMAIN"


def make_pair(win32):
    def is_alive(hwnd):
        return win32.is_window(hwnd) and win32.get_class_name(hwnd) == XLMAIN
    excel = ExcelTracker(win32)
    pinner = Pinner(win32, is_alive)
    return excel, pinner


# -- 窗口筛选 ---------------------------------------------------------------

def test_enumerate_filters_only_xlmain_excel_process(win32):
    win32.add_window(1, class_name="XLMAIN", process="EXCEL.EXE")
    win32.add_window(2, class_name="XLDESK", process="EXCEL.EXE")   # 壳窗口
    win32.add_window(3, class_name="XLMAIN", process="CHROME.EXE")  # 伪造进程
    win32.add_window(4, class_name="Notepad", process="EXCEL.EXE")  # 其他类名

    excel, _ = make_pair(win32)

    assert excel.enumerate_windows() == [1]


def test_is_xlmain_matches_class_only(win32):
    win32.add_window(1, class_name="XLMAIN")
    win32.add_window(2, class_name="XLDESK")
    excel, _ = make_pair(win32)

    assert excel.is_xlmain(1)
    assert not excel.is_xlmain(2)
    assert not excel.is_xlmain(0)


def test_is_excel_window_requires_excel_process(win32):
    win32.add_window(1, class_name="XLMAIN", process="EXCEL.EXE")
    win32.add_window(2, class_name="XLMAIN", process="OTHER.EXE")
    excel, _ = make_pair(win32)

    assert excel.is_excel_window(1)
    assert not excel.is_excel_window(2)


# -- 事件跟踪 ---------------------------------------------------------------

def test_on_foreground_records_only_xlmain(win32):
    excel, _ = make_pair(win32)
    win32.add_window(1, class_name="XLMAIN")
    win32.add_window(2, class_name="Notepad")

    excel.on_foreground(2, 0, 0, 0)
    assert excel.last_excel_hwnd is None

    excel.on_foreground(1, 0, 0, 0)
    assert excel.last_excel_hwnd == 1


def test_on_destroy_clears_last_excel_hwnd(win32):
    excel, _ = make_pair(win32)
    win32.add_window(1, class_name="XLMAIN")
    excel.on_foreground(1, 0, 0, 0)

    excel.on_destroy(1, 0, 0, 0)

    assert excel.last_excel_hwnd is None


# -- 目标判定优先级 ---------------------------------------------------------

def test_target_foreground_xlmain_wins(win32):
    excel, pinner = make_pair(win32)
    win32.add_window(1, class_name="XLMAIN")
    win32.add_window(2, class_name="XLMAIN")
    win32.foreground = 1
    pinner.pinned = {2}

    assert excel.target_hwnd(pinner) == 1


def test_target_frontmost_pinned_when_foreground_not_excel(win32):
    excel, pinner = make_pair(win32)
    win32.add_window(9, class_name="Notepad")     # 前台是别的软件
    win32.foreground = 9
    win32.add_window(2, class_name="XLMAIN")
    win32.zorder = [2]
    pinner.pinned = {2}

    assert excel.target_hwnd(pinner) == 2


def test_target_last_excel_when_nothing_pinned(win32):
    excel, pinner = make_pair(win32)
    win32.add_window(9, class_name="Notepad")
    win32.foreground = 9
    win32.add_window(3, class_name="XLMAIN")
    excel.last_excel_hwnd = 3

    assert excel.target_hwnd(pinner) == 3


def test_target_none_when_no_excel_at_all(win32):
    excel, pinner = make_pair(win32)
    win32.add_window(9, class_name="Notepad")
    win32.foreground = 9

    assert excel.target_hwnd(pinner) is None


def test_target_last_excel_ignores_dead_handle(win32):
    excel, pinner = make_pair(win32)
    win32.add_window(9, class_name="Notepad")
    win32.foreground = 9
    win32.add_window(3, class_name="XLMAIN", valid=True)
    excel.last_excel_hwnd = 3
    win32.valid.discard(3)  # 已销毁

    assert excel.target_hwnd(pinner) is None
