"""开机自启：把打包后的 exe 写入 Windows 注册表 Run 键。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "TableStickyNote"


def exe_command() -> Optional[str]:
    """返回要注册的命令：打包后是自身 exe；开发模式回退到 dist/table-note.exe。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    candidate = Path(__file__).resolve().parent.parent / "dist" / "table-note.exe"
    if candidate.exists():
        return str(candidate)
    return None


def is_enabled() -> bool:
    """当前 Run 键里是否已注册本程序。"""
    cmd = exe_command()
    if cmd is None or sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return val == cmd
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    """注册 / 取消开机自启。返回是否成功。"""
    cmd = exe_command()
    if cmd is None or sys.platform != "win32":
        return False
    import winreg

    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
    try:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except OSError:
                pass
    finally:
        winreg.CloseKey(key)
    return True
