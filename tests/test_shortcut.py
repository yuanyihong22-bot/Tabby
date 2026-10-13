from src import shortcut


def test_exe_path_returns_dist_exe_in_dev():
    p = shortcut.exe_path()
    assert p is None or p.endswith("tabby.exe")


def test_ps_quote():
    assert shortcut._ps_quote("a'b") == "a''b"


def test_create_desktop_shortcut(tmp_path):
    # 在临时目录创建快捷方式，验证 .lnk 落盘（依赖本机 PowerShell）
    ok = shortcut.create_desktop_shortcut(desktop_dir=str(tmp_path))
    assert ok is True
    assert (tmp_path / shortcut.SHORTCUT_NAME).exists()
