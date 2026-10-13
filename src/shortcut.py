"""创建桌面快捷方式（指向打包后的 exe）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

SHORTCUT_NAME = "表格便签.lnk"


def exe_path() -> Optional[str]:
    """返回要指向的 exe：打包后是自身；开发模式回退到 dist/table-note.exe。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    candidate = Path(__file__).resolve().parent.parent / "dist" / "table-note.exe"
    if candidate.exists():
        return str(candidate)
    return None


def _ps_quote(s: str) -> str:
    """转义 PowerShell 单引号字符串。"""
    return s.replace("'", "''")


def create_desktop_shortcut(desktop_dir: str | None = None) -> bool:
    """在桌面（或指定目录）创建指向 exe 的快捷方式。返回是否成功。"""
    target = exe_path()
    if target is None:
        return False
    workdir = str(Path(target).parent)

    if desktop_dir is not None:
        desktop_cmd = f"$d = '{_ps_quote(desktop_dir)}'"
        lnk_path = Path(desktop_dir) / SHORTCUT_NAME
    else:
        desktop_cmd = "$d = [Environment]::GetFolderPath('Desktop')"
        lnk_path = None

    ps = (
        "$ws = New-Object -ComObject WScript.Shell;"
        + desktop_cmd
        + ";"
        + f"$sc = $ws.CreateShortcut((Join-Path $d '{_ps_quote(SHORTCUT_NAME)}'));"
        + f"$sc.TargetPath = '{_ps_quote(target)}';"
        + f"$sc.WorkingDirectory = '{_ps_quote(workdir)}';"
        + "$sc.Save()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            timeout=30,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return False

    if lnk_path is not None:
        return lnk_path.exists()
    return True
