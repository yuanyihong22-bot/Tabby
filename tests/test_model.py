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


def test_append_text():
    m = TableModel([["a", "b"], ["1", "2"]])
    m.append_text("x\ty\n3\t4")
    assert m.rows == [["a", "b"], ["1", "2"], ["x", "y"], ["3", "4"]]


def test_append_text_widens_existing():
    m = TableModel([["a", "b"]])
    m.append_text("x\ty\tz")
    assert m.rows == [["a", "b", ""], ["x", "y", "z"]]


def test_append_text_narrower_new():
    m = TableModel([["a", "b", "c"]])
    m.append_text("x")
    assert m.rows == [["a", "b", "c"], ["x", "", ""]]


def test_append_empty_text_noop():
    m = TableModel([["a"]])
    m.append_text("")
    assert m.rows == [["a"]]


def test_delete_rows():
    m = TableModel([["a", "b"], ["c", "d"], ["e", "f"]])
    m.delete_rows(1, 1)
    assert m.rows == [["a", "b"], ["e", "f"]]


def test_delete_rows_multiple():
    m = TableModel([["a"], ["b"], ["c"], ["d"]])
    m.delete_rows(0, 2)
    assert m.rows == [["d"]]


def test_delete_cols():
    m = TableModel([["a", "b", "c"], ["1", "2", "3"]])
    m.delete_cols(1, 1)
    assert m.rows == [["a", "c"], ["1", "3"]]


def test_delete_cols_multiple():
    m = TableModel([["a", "b", "c", "d"]])
    m.delete_cols(0, 2)
    assert m.rows == [["d"]]


def test_clear_range():
    m = TableModel([["a", "b", "c"], ["1", "2", "3"]])
    m.clear_range(0, 1, 1, 2)
    assert m.rows == [["a", "", ""], ["1", "", ""]]
