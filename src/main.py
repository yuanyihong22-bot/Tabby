"""桌面表格便签入口。"""

from __future__ import annotations

import tkinter as tk

from . import model as model_mod
from . import storage as storage_mod
from .widget import Widget


def main() -> None:
    store = storage_mod.Storage()
    data = store.load()
    table = model_mod.TableModel(data.rows)

    root = tk.Tk()
    Widget(root, table, store, data)
    root.mainloop()


if __name__ == "__main__":
    main()
