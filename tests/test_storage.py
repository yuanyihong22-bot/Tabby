from src.storage import Storage, TableData, WindowPos


def test_roundtrip(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    s = Storage(3)
    data = TableData(
        rows=[["a", "b"], ["1", "2"]],
        window=WindowPos(x=12, y=34),
        font_size=15,
        topmost=True,
    )
    s.save(data)
    loaded = s.load()
    assert loaded.rows == [["a", "b"], ["1", "2"]]
    assert loaded.window.x == 12
    assert loaded.window.y == 34
    assert loaded.font_size == 15
    assert loaded.topmost is True


def test_path_naming(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    s = Storage(7)
    assert s.path.name == "note_7.json"
    assert s.path.parent == tmp_path


def test_load_missing_returns_defaults(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    data = Storage(1).load()
    assert data.rows == []
    assert data.window.x == 100
    assert data.font_size == 12
    assert data.topmost is False


def test_load_corrupt_returns_empty(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    s = Storage(1)
    s.path.write_text("{ not valid json", encoding="utf-8")
    assert s.load().rows == []


def test_save_creates_parent_dirs(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path / "a" / "b")
    s = Storage(1)
    s.save(TableData(rows=[["x"]]))
    assert s.path.exists()


def test_non_string_cells_coerced(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    s = Storage(1)
    s.path.write_text('{"rows": [[1, 2.5]], "window": {"x": 3, "y": 4}}', encoding="utf-8")
    assert s.load().rows == [["1", "2.5"]]


def test_font_size_clamped_on_load(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    s = Storage(1)
    s.path.write_text('{"rows": [], "font_size": 999}', encoding="utf-8")
    assert s.load().font_size == 40


def test_list_ids_and_next_id(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    Storage(2).save(TableData())
    Storage(5).save(TableData())
    Storage(1).save(TableData())
    assert Storage.list_ids() == [1, 2, 5]
    assert Storage.next_id() == 6


def test_next_id_empty(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    assert Storage.list_ids() == []
    assert Storage.next_id() == 1


def test_migrate_legacy(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    legacy = tmp_path / "table.json"
    legacy.write_text('{"rows": [["旧数据"]]}', encoding="utf-8")
    assert Storage.migrate_legacy() is True
    assert (tmp_path / "note_1.json").exists()
    assert not legacy.exists()
    assert Storage(1).load().rows == [["旧数据"]]


def test_migrate_legacy_does_not_overwrite(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    (tmp_path / "table.json").write_text('{"rows": [["旧"]]}', encoding="utf-8")
    (tmp_path / "note_1.json").write_text('{"rows": [["新"]]}', encoding="utf-8")
    assert Storage.migrate_legacy() is False
    assert Storage(1).load().rows == [["新"]]


def test_delete_file(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setattr(sm, "base_dir", lambda: tmp_path)
    s = Storage(4)
    s.save(TableData(rows=[["a"]]))
    assert s.path.exists()
    s.delete_file()
    assert not s.path.exists()


def test_migrate_old_dir(tmp_path, monkeypatch):
    import src.storage as sm
    monkeypatch.setenv("APPDATA", str(tmp_path))
    old = tmp_path / "TableStickyNote"
    old.mkdir()
    (old / "note_1.json").write_text('{"rows": [["x"]]}', encoding="utf-8")
    assert sm.migrate_old_dir() is True
    assert (tmp_path / "Tabby" / "note_1.json").exists()
    assert not old.exists()
