from src import autostart


def test_exe_command_points_to_exe_in_dev():
    # 开发模式下回退到 dist/table-note.exe（若存在）
    cmd = autostart.exe_command()
    assert cmd is None or cmd.endswith("table-note.exe")


def test_is_enabled_false_when_no_command(monkeypatch):
    monkeypatch.setattr(autostart, "exe_command", lambda: None)
    assert autostart.is_enabled() is False


def test_set_enabled_noop_when_no_command(monkeypatch):
    monkeypatch.setattr(autostart, "exe_command", lambda: None)
    assert autostart.set_enabled(True) is False
