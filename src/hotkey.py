"""全局热键注册 / 注销。"""

from __future__ import annotations

HOTKEY_ID = 1
DEFAULT_KEY = "T"
FALLBACK_KEYS = ["Y", "U", "I", "O"]


class Hotkey:
    """注册全局热键，冲突时依次尝试备用键。"""

    def __init__(self, win32):
        self._win32 = win32
        self.hotkey_registered = False
        self.current_key: str | None = None
        self._hwnd: int | None = None

    def register(self, hwnd: int | None) -> bool:
        """依次尝试默认键与备用键；任一成功即返回 True。"""
        self._hwnd = hwnd
        mods = self._win32.MOD_CONTROL | self._win32.MOD_WIN | self._win32.MOD_NOREPEAT
        for key in [DEFAULT_KEY, *FALLBACK_KEYS]:
            if self._win32.register_hot_key(hwnd, HOTKEY_ID, mods, ord(key)):
                self.hotkey_registered = True
                self.current_key = key
                return True
        self.hotkey_registered = False
        self.current_key = None
        return False

    def unregister(self) -> None:
        if self.hotkey_registered and self._hwnd is not None:
            self._win32.unregister_hot_key(self._hwnd, HOTKEY_ID)
        self.hotkey_registered = False
        self.current_key = None
