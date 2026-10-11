# Excel 置顶工具 · 技术方案

> 版本：v0.1（MVP）　|　对应产品设计：`../PRODUCT_DESIGN.md`

## 1. 概述与目标

实现一个 Windows 托盘小工具：全局快捷键一键切换 Excel 工作簿窗口的置顶状态，方便临时对照与复制粘贴。本方案只覆盖 v0.1 的四个功能点：全局快捷键切换、全局生效、托盘状态、退出自动还原。

## 2. 技术选型

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 语言 | Python 3.14 | 本机已装，无需额外环境 |
| Win32 封装 | pywin32 | 内置 `RegisterHotKey` / `SetWindowPos` / `Shell_NotifyIcon`，免写 ctypes |
| 依赖管理 | uv | 本机已有，快速建 venv |
| 测试 | pytest | 对纯逻辑（状态机、窗口筛选）做单元测试 |
| 打包（后续） | PyInstaller | 单文件 exe，`--noconsole` |

> **待确认风险**：需在开工时先验证 pywin32 是否提供 Python 3.14（cp314）的 wheel；若无，改用纯 `ctypes` 直调 user32/shell32，方案其余部分不变。

## 3. 整体架构

单进程、单主线程模型：主线程创建**隐藏窗口 + WndProc**，跑一个 Windows 消息循环。全局热键（`WM_HOTKEY`）与托盘回调（`WM_APP+1`）都投递到这个 WndProc 统一处理，避免多线程加锁。

```
┌─────────────────────────────────────────────┐
│ main.py（入口：装配并进入消息循环）              │
│   ├─ wnd.py    隐藏窗口 + WndProc（消息路由）    │
│   ├─ excel.py  识别 / 跟踪 Excel 工作簿窗口     │
│   ├─ pinner.py 置顶 / 取消置顶 + 状态集合        │
│   ├─ hotkey.py RegisterHotKey 全局热键         │
│   └─ tray.py   Shell_NotifyIcon 托盘 + 菜单    │
└─────────────────────────────────────────────┘
        │ user32 / shell32（经 pywin32）
        ▼
      Windows（EXCEL.EXE 的 XLMAIN 窗口）
```

## 4. 核心机制设计

### 4.1 窗口识别与跟踪

- **识别**：`EnumWindows` 遍历顶层窗口，仅取窗口类名为 `XLMAIN` 且进程为 `EXCEL.EXE` 的窗口（`GetWindowThreadProcessId` 取 PID，再比对进程名）。排除隐藏的桌面壳窗口 `XLDESK` 及其他类名。
- **跟踪「最近激活」**：`SetWinEventHook(EVENT_SYSTEM_FOREGROUND, WINEVENT_OUTOFCONTEXT)`，回调里取 `GetForegroundWindow`，若类名为 `XLMAIN` 则记下其 HWND 为 `last_excel_hwnd`。
- **热键触发时的目标判定**：前台窗口若是 Excel 工作簿 → 用它；否则回退用 `last_excel_hwnd`。这样在别的软件里按快捷键也能命中「刚才那个表格」。

### 4.2 置顶 / 取消置顶

```
SetWindowPos(hwnd, HWND_TOPMOST,    0,0,0,0, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE)  # 置顶
SetWindowPos(hwnd, HWND_NOTOPMOST,  0,0,0,0, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE)  # 取消
```

- 当前是否已置顶：`GetWindowLong(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST`。
- 状态用集合 `pinned: set[int]` 记录「由本程序置顶」的 HWND，支持多个工作簿同时置顶。
- **切换语义**：目标已在 `pinned` 中 → 取消并移除；否则 → 置顶并加入。

### 4.3 全局热键

```
RegisterHotKey(hwnd, HOTKEY_ID, MOD_CONTROL|MOD_WIN|MOD_NOREPEAT, VK_T)
```

- `MOD_NOREPEAT`（0x4000）避免按住键时重复触发。
- `WM_HOTKEY` 到达 WndProc 后执行切换逻辑。
- 注册失败（快捷键被占用）→ 托盘弹提示，并尝试去掉 `MOD_NOREPEAT` 或用备用键重试，仍失败则告知用户换键。

### 4.4 托盘图标

- `Shell_NotifyIcon(NIM_ADD, ...)`，`NIF_ICON|NIF_MESSAGE|NIF_TIP`，回调消息号 `WM_APP+1`。
- 右键菜单：`CreatePopupMenu` + `TrackPopupMenu`，含「当前状态（只读）」「退出」。
- 状态反馈：用 `NIM_MODIFY` 更新 tooltip 文案（「已置顶 N 个窗口」/「未置顶」）或图标。

### 4.5 退出清理

按顺序执行（`atexit` 兜底 + 菜单「退出」主路径）：

1. 遍历 `pinned`，对每个仍存活的 HWND（`IsWindow` 校验）执行 `HWND_NOTOPMOST`。
2. `UnregisterHotKey`。
3. `Shell_NotifyIcon(NIM_DELETE)`。
4. 结束消息循环、退出进程。

> 关键点：`TOPMOST` 是窗口自身属性，程序退出不会自动还原，**必须先还原再退出**，否则 Excel 会「卡死」在顶上。

## 5. 模块划分与目录结构

```
E:\AI_Tools\EXCEL_desktop\
├── AGENTS.md
├── PRODUCT_DESIGN.md
├── README.md                # 使用说明（实现时补）
├── docs/
│   └── TECHNICAL_DESIGN.md  # 本文档
├── src/
│   ├── __init__.py
│   ├── main.py              # 入口：装配各模块，进入消息循环
│   ├── wnd.py               # 隐藏窗口 + WndProc（路由 WM_HOTKEY / 托盘消息）
│   ├── excel.py             # 窗口识别、last_excel_hwnd 跟踪
│   ├── pinner.py            # SetWindowPos 封装 + pinned 集合
│   ├── hotkey.py            # RegisterHotKey / UnregisterHotKey
│   └── tray.py              # 托盘图标 + 右键菜单
├── tests/
│   ├── test_pinner.py       # 切换状态机（mock win32 调用）
│   ├── test_excel.py        # 窗口筛选 / 目标判定逻辑
│   └── test_cleanup.py      # 退出清理顺序
├── pyproject.toml
└── .gitignore
```

## 6. 关键状态与数据

| 状态 | 类型 | 说明 |
| --- | --- | --- |
| `pinned` | `set[int]` | 当前被本程序置顶的 HWND |
| `last_excel_hwnd` | `int \| None` | 最近激活的 Excel 工作簿 HWND |
| `hotkey_registered` | `bool` | 热键是否注册成功 |

状态不落盘（v0.1 不记忆），进程生命周期内有效。

## 7. 边界情况与处理

| 边界情况 | 处理 |
| --- | --- |
| 程序退出残留置顶 | 退出前统一还原（见 4.5） |
| 工作簿关闭 / Excel 退出 | 每次操作与退出前用 `IsWindow` 校验，剔除失效 HWND；可加 `EVENT_OBJECT_DESTROY` 钩子及时清理 |
| 多个工作簿 | `pinned` 为集合，每个窗口独立切换；tooltip 显示数量 |
| 快捷键冲突 | 注册失败 → 重试 / 提示换键（见 4.3） |
| Excel 以管理员权限运行 | `SetWindowPos` 可能静默失效 → 检测失败并警告；普通权限场景无需处理 |
| 隐藏壳窗口 `XLDESK` | 按类名严格过滤，只认 `XLMAIN` |

## 8. 测试方案

纯逻辑与 Win32 调用分离，Win32 侧在测试中用 mock 替换，保证无 Excel 环境也能跑：

- **test_pinner**：切换语义（置顶↔取消）、集合增删、`IsWindow` 失效剔除、退出清理顺序。
- **test_excel**：给定 `(hwnd, class, pid)` 列表，验证只筛出 `XLMAIN`；目标判定（前台命中 / 回退 last）。
- **test_cleanup**：mock 后断言退出时对每个 pinned 窗口都调用了 NOTOPMOST、且先于进程退出。

**手工验收清单**（需真实 Excel）：
1. 打开工作簿，按 `Win+Ctrl+T` → 置顶；再按 → 取消。
2. 切到别的窗口按快捷键 → 仍能取消置顶。
3. 托盘 tooltip 随状态变化；右键「退出」→ Excel 恢复普通层叠。

## 9. 打包与运行

- 开发运行：`uv run python src/main.py`（先 `uv add pywin32 pytest`）。
- 发布（后续）：`pyinstaller --onefile --noconsole src/main.py`。

## 10. 风险与待确认项

1. pywin32 对 Python 3.14 的 wheel 可用性（开工第一步验证，失败则 ctypes 兜底）。
2. 全局快捷键 `Win+Ctrl+T` 是否被占用（运行时检测，失败提示换键）。
3. 托盘菜单「当前状态」的更新频率与交互细节，实现时再定。
