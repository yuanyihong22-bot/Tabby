from src.model import TableModel


def test_parse_tab_separated():
    rows = TableModel.parse_text("a\tb\tc\n1\t2\t3")
    assert rows == [["a", "b", "c"], ["1", "2", "3"]]


def test_parse_single_column_no_tab():
    rows = TableModel.parse_text("a\nb\nc")
    assert rows == [["a"], ["b"], ["c"]]


def test_parse_trailing_newline_removed():
    rows = TableModel.parse_text("a\tb\n1\t2\n")
    assert rows == [["a", "b"], ["1", "2"]]


def test_parse_pads_uneven_columns():
    rows = TableModel.parse_text("a\tb\tc\n1\t2")
    assert rows == [["a", "b", "c"], ["1", "2", ""]]


def test_parse_empty_text():
    assert TableModel.parse_text("") == []


def test_parse_crlf_normalized():
    rows = TableModel.parse_text("a\tb\r\n1\t2")
    assert rows == [["a", "b"], ["1", "2"]]


def test_empty_row_in_middle_preserved():
    rows = TableModel.parse_text("a\tb\n\nc\td")
    assert rows == [["a", "b"], ["", ""], ["c", "d"]]


def test_cell_access():
    m = TableModel([["a", "b"], ["c", "d"]])
    assert m.cell(0, 0) == "a"
    assert m.cell(1, 1) == "d"
    assert m.cell(5, 5) == ""


def test_num_rows_cols():
    m = TableModel([["a", "b", "c"], ["x"]])
    assert m.num_rows == 2
    assert m.num_cols == 3


def test_apply_text_replaces():
    m = TableModel([["old"]])
    m.apply_text("x\ty\n1\t2")
    assert m.rows == [["x", "y"], ["1", "2"]]


def test_clear():
    m = TableModel([["a", "b"], ["c", "d"]])
    m.clear()
    assert m.rows == []


def test_apply_text_mutates_in_place():
    # 外部持有同一列表引用时，apply_text 不应断开引用
    shared = [["old"]]
    m = TableModel(shared)
    m.apply_text("a\tb")
    assert shared == [["a", "b"]]
