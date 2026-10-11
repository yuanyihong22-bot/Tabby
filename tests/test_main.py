"""test_main：单实例守卫（第二个实例直接退出并提示）。"""

from __future__ import annotations

from src import main as main_mod


def test_main_exits_when_already_running(monkeypatch):
    shown = {}

    monkeypatch.setattr(main_mod.win32, "create_mutex", lambda name: True)

    def _msg(text, title):
        shown["text"] = text
        shown["title"] = title
        return 1

    monkeypatch.setattr(main_mod.win32, "message_box", _msg)

    assert main_mod.main() == 0
    assert "已在运行" in shown["text"]
    assert shown["title"] == "Excel 置顶"


def test_main_creates_mutex_with_expected_name(monkeypatch):
    names = []

    monkeypatch.setattr(main_mod.win32, "create_mutex", lambda name: names.append(name) or True)
    monkeypatch.setattr(main_mod.win32, "message_box", lambda text, title: 1)

    main_mod.main()

    assert names == ["ExcelPinTool.SingleInstance"]
