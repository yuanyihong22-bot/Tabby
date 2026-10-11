from src.model import TableModel
from src.widget import Widget, _col_letter, _is_number


def test_col_letter():
    assert _col_letter(0) == "A"
    assert _col_letter(25) == "Z"
    assert _col_letter(26) == "AA"
    assert _col_letter(27) == "AB"


def test_is_number():
    assert _is_number("3.5")
    assert _is_number("-2")
    assert _is_number(" 100 ")
    assert not _is_number("")
    assert not _is_number("苹果")
    assert not _is_number("3.5元")


def test_normalize():
    assert Widget._normalize((0, 0), (2, 3)) == (0, 0, 2, 3)
    assert Widget._normalize((2, 3), (0, 0)) == (0, 0, 2, 3)  # 反向拖动
    assert Widget._normalize((1, 1), (1, 1)) == (1, 1, 1, 1)


def _make_widget(rows):
    # 不经过 __init__，避免创建 Tk 窗口
    w = Widget.__new__(Widget)
    w.model = TableModel(rows)
    w._selection = None
    return w


def test_selection_text():
    w = _make_widget([["a", "b", "c"], ["1", "2", "3"], ["x", "y", "z"]])
    w._selection = (0, 1, 1, 2)  # 第1-2行、第2-3列
    assert w._selection_text() == "b\tc\n2\t3"


def test_selection_text_none():
    w = _make_widget([["a"]])
    assert w._selection_text() == ""
