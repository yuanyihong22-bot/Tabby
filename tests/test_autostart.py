from src import autostart


def test_exe_command_is_none_when_not_frozen():
    # pytest 运行在非打包环境，exe_command 应为 None
    assert autostart.exe_command() is None


def test_is_enabled_returns_false_when_not_frozen():
    assert autostart.is_enabled() is False


def test_set_enabled_noop_when_not_frozen():
    assert autostart.set_enabled(True) is False
