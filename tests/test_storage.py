from src.storage import Storage, TableData, WindowPos


def test_roundtrip(tmp_path):
    p = tmp_path / "table.json"
    s = Storage(p)
    data = TableData(rows=[["a", "b"], ["1", "2"]], window=WindowPos(x=12, y=34))
    s.save(data)
    loaded = s.load()
    assert loaded.rows == [["a", "b"], ["1", "2"]]
    assert loaded.window.x == 12
    assert loaded.window.y == 34


def test_load_missing_returns_empty(tmp_path):
    s = Storage(tmp_path / "nope.json")
    data = s.load()
    assert data.rows == []
    assert data.window.x == 100
    assert data.window.y == 100


def test_load_corrupt_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not valid json", encoding="utf-8")
    s = Storage(p)
    data = s.load()
    assert data.rows == []


def test_save_creates_parent_dirs(tmp_path):
    p = tmp_path / "a" / "b" / "table.json"
    s = Storage(p)
    s.save(TableData(rows=[["x"]]))
    assert p.exists()


def test_non_string_cells_coerced(tmp_path):
    p = tmp_path / "table.json"
    p.write_text('{"rows": [[1, 2.5]], "window": {"x": 3, "y": 4}}', encoding="utf-8")
    s = Storage(p)
    data = s.load()
    assert data.rows == [["1", "2.5"]]
