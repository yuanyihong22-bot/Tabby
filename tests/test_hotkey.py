"""test_hotkey：默认键 / 冲突回退 / 注销。"""

from __future__ import annotations

from src.hotkey import FALLBACK_KEYS, Hotkey


def _expected_mods(win32):
    return win32.MOD_CONTROL | win32.MOD_WIN | win32.MOD_NOREPEAT


def test_register_uses_default_key(win32):
    hotkey = Hotkey(win32)
    hwnd = 0x100

    assert hotkey.register(hwnd) is True
    assert hotkey.hotkey_registered is True
    assert hotkey.current_key == "T"
    assert win32.hotkey_registered == [(hwnd, 1, _expected_mods(win32), ord("T"))]


def test_register_falls_back_on_conflict(win32):
    hotkey = Hotkey(win32)
    # 前两个键被占用，第三个成功
    win32.hotkey_results = [False, False, True]

    assert hotkey.register(0x100) is True
    assert hotkey.current_key == FALLBACK_KEYS[1]


def test_register_fails_when_all_occupied(win32):
    hotkey = Hotkey(win32)
    win32.hotkey_results = [False] * (1 + len(FALLBACK_KEYS))

    assert hotkey.register(0x100) is False
    assert hotkey.hotkey_registered is False
    assert hotkey.current_key is None


def test_unregister_only_when_registered(win32):
    hotkey = Hotkey(win32)
    hotkey.register(0x100)
    win32.hotkey_unregistered.clear()

    hotkey.unregister()

    assert hotkey.hotkey_registered is False
    assert win32.hotkey_unregistered == [(0x100, 1)]


def test_unregister_noop_when_not_registered(win32):
    hotkey = Hotkey(win32)

    hotkey.unregister()

    assert win32.hotkey_unregistered == []
