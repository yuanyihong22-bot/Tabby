"""桌面表格便签入口：管理多个便签窗口。"""

from __future__ import annotations

import tkinter as tk

from . import model as model_mod
from . import storage as storage_mod
from .widget import Widget


class WidgetManager:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.widgets: dict[int, Widget] = {}

    def start(self) -> None:
        storage_mod.Storage.migrate_legacy()
        ids = storage_mod.Storage.list_ids()
        if not ids:
            self._create(storage_mod.Storage.next_id())
            return
        for wid in ids:
            self._create(wid)

    def _create(self, wid: int) -> Widget:
        store = storage_mod.Storage(wid)
        data = store.load()
        table = model_mod.TableModel(data.rows)
        win = tk.Toplevel(self.root)
        w = Widget(
            win,
            table,
            store,
            data,
            widget_id=wid,
            on_close=lambda wid=wid: self._close(wid),
            on_new=self._new,
            on_quit_all=self._quit_all,
        )
        self.widgets[wid] = w
        return w

    def _new(self) -> None:
        existing = set(storage_mod.Storage.list_ids()) | set(self.widgets.keys())
        wid = (max(existing) + 1) if existing else 1
        self._create(wid)

    def _close(self, wid: int) -> None:
        w = self.widgets.pop(wid, None)
        if w is not None:
            w.storage.delete_file()
            w.root.destroy()
        if not self.widgets:
            self.root.quit()

    def _quit_all(self) -> None:
        for w in list(self.widgets.values()):
            w.storage.save(w.data)
            w.root.destroy()
        self.widgets.clear()
        self.root.quit()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    manager = WidgetManager(root)
    manager.start()
    root.mainloop()


if __name__ == "__main__":
    main()
