# Excel 置顶工具

一键把 Excel 工作簿窗口临时置顶的 Windows 托盘小工具。解决「一边对照表格、一边在别的软件里复制粘贴」时表格被挡住的问题。

## 功能（v0.1）

- **多窗口同时置顶**：支持把多个工作簿同时置顶，各自独立切换。
- **全局快捷键**：默认 `Win+Ctrl+T`，在任意软件里按快捷键即可切换目标工作簿的置顶状态。
- **目标判定优先级**：
  1. 当前前台窗口就是某个 Excel 工作簿 → 作用于它；
  2. 否则 → 作用于「置顶中排在最前面的工作簿」；
  3. 两者都没有 → 作用于「最近激活过的工作簿」。
- **托盘图标**：显示当前置顶状态与数量，右键可退出程序。
- **退出自动还原**：程序正常退出时，把所有置顶窗口调回普通状态，不残留。

## 环境要求

- Windows
- Python 3.14+（配合 pywin32）

## 安装与运行

```bash
# 安装依赖
uv sync

# 运行（二选一）
uv run excel-pin            # 推荐：通过入口命令
uv run python -m src.main   # 等价：以包模块方式运行
```

> 若热键 `Win+Ctrl+T` 被其他程序占用，程序会依次尝试备用键；仍失败时托盘会提示换键。

## 打包为 exe

```bash
uv add --dev pyinstaller
uv run pyinstaller --onefile --noconsole --name excel-pin launcher.py
# 产物在 dist/excel-pin.exe，双击即可运行
```

> 代码使用相对导入，PyInstaller 不能直接打包 `src/main.py`，需经根目录 `launcher.py` 以包方式导入。

## 测试

```bash
uv run pytest -q
```

纯逻辑（置顶切换状态机、窗口筛选、目标判定、退出清理）通过 mock 掉 `src/win32.py` 接缝来测试，无需真实 Excel 环境。

## 目录结构

```
src/
├── win32.py     # Win32 调用的薄封装层（唯一直接 import win32 的地方）
├── main.py      # 入口：装配各模块，进入消息循环
├── wnd.py       # 隐藏窗口 + WndProc（路由 WM_HOTKEY / 托盘消息）
├── excel.py     # 窗口识别、last_excel_hwnd 跟踪、target_hwnd()
├── pinner.py    # SetWindowPos 封装 + pinned 集合 + frontmost_pinned()
├── hotkey.py    # RegisterHotKey / UnregisterHotKey
└── tray.py      # 托盘图标 + 右键菜单
tests/           # pytest 单元测试（mock win32）
```

## 已知限制

- 任务管理器强杀、崩溃、断电等异常退出无法执行清理，已置顶窗口会残留 `TOPMOST`（Excel 可能「卡死」在顶上）。v0.1 接受此限制；彻底解决需后续引入独立 watchdog 进程。
