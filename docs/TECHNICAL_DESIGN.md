# Excel 置顶工具 · 技术方案

> 版本：v0.1（MVP）　|　对应产品设计：`../PRODUCT_DESIGN.md`

## 1. 概述与目标

实现一个 Windows 托盘小工具：全局快捷键一键切换 Excel 工作簿窗口的置顶状态，方便临时对照与复制粘贴。本方案覆盖 v0.1 的功能点：**多窗口同时置顶、全局快捷键切换（含目标判定）、全局生效、托盘状态、退出自动还原**。

## 2. 技术选型

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 语言 | Python 3.14 | 本机已装，无需额外环境 |
| Win32 封装 | pywin32 | 内置 `RegisterHotKey` / `SetWindowPos` / `Shell_NotifyIcon`，免写 ctypes |
| 依赖管理 | uv | 本机已有，快速建 venv |
| 测试 | pytest | 对纯逻辑（状态机、窗口筛选、目标判定）做单元测试 |
| 打包（后续） | PyInstaller | 单文件 exe，`--noconsole` |

> **风险状态**：pywin32 已发布 `312` 版，带 `cp314-cp314-win32 / win_amd64 / win_arm64` 三个 wheel（已核实 PyPI），Python 3.14 直接可用。保留 ctypes 直调 user32/shell32 作为兜底方案以防环境异常。

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

**状态归属**（避免模块间隐式共享）：

- `pinned` 集合归 `pinner.py` 持有，对外暴露 `pin(hwnd)` / `unpin(hwnd)` / `frontmost_pinned()`。
- `last_excel_hwnd` 归 `excel.py` 持有，对外暴露 `target_hwnd()`。
- `wnd.py` 只做消息路由：收到 `WM_HOTKEY` 后调 `excel.target_hwnd()` 拿目标，再调 `pinner.toggle(target)`；不直接读写状态，只走公开接口。
- `main.py` 负责装配（把 pinner / excel 实例经构造器注入 wnd），不引入全局单例。

## 4. 核心机制设计

### 4.1 窗口识别与目标判定

- **识别**：`EnumWindows` 遍历顶层窗口，仅取窗口类名为 `XLMAIN` 且进程为 `EXCEL.EXE` 的窗口（`GetWindowThreadProcessId` 取 PID，再用 `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` + `QueryFullProcessImageNameW` 取进程名比对）。排除隐藏的桌面壳窗口 `XLDESK` 及其他类名。
- **跟踪「最近激活」**：`SetWinEventHook(EVENT_SYSTEM_FOREGROUND, WINEVENT_OUTOFCONTEXT)`。回调里**直接读取事件参数 `hwnd`**（正是「正在成为前台」的窗口），不再调 `GetForegroundWindow()`（后者在异步回调里可能已过期）。若该 `hwnd` 类名为 `XLMAIN` 则记下为 `last_excel_hwnd`。
  - pywin32 的 `SetWinEventHook` 回调是 Python 函数，**必须持有其引用**（存到模块级变量），否则被垃圾回收会导致崩溃。
  - `WINEVENT_OUTOFCONTEXT` 下回调经消息队列投递到注册线程（主线程），与 WndProc 天然串行，无数据竞争。
- **目标判定优先级**（`target_hwnd()`）：
  1. 前台窗口若是 Excel 工作簿（`XLMAIN`）→ 用它；
  2. 否则 → `pinner.frontmost_pinned()`（置顶中排在最前面的工作簿）；
  3. 否则 → `last_excel_hwnd`（最近激活过的工作簿）。
  这样既支持「点哪个表格、按快捷键就切哪个」，也支持「在别的软件里按快捷键，命中飘在最前面的那个置顶表格」。

### 4.2 置顶 / 取消置顶

```python
SetWindowPos(hwnd, HWND_TOPMOST,    0,0,0,0, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE)  # 置顶
SetWindowPos(hwnd, HWND_NOTOPMOST,  0,0,0,0, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE)  # 取消
```

- 当前是否已置顶：`GetWindowLong(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST`。
- 状态用集合 `pinned: set[int]` 记录「由本程序置顶」的 HWND，支持多个工作簿同时置顶。
- **切换语义**：目标已在 `pinned` 中 → 取消并移除；否则 → 置顶并加入。
- **「最前面的置顶窗口」**（`frontmost_pinned()`）：从 `GetTopWindow(None)` 起沿 `GetWindow(hwnd, GW_HWNDNEXT)` 从前往后遍历 z 序，返回第一个**仍在 `pinned` 中且类名仍为 `XLMAIN`** 的窗口。新置顶的窗口自然排到置顶层最前，与产品设计「点击哪个哪个在前」一致（点击置顶窗口本就会把它提到最前，无需额外处理）。

### 4.3 全局热键

```python
RegisterHotKey(hwnd, HOTKEY_ID, MOD_CONTROL|MOD_WIN|MOD_NOREPEAT, VK_T)
```

- `MOD_NOREPEAT`（0x4000）避免按住键时重复触发（Win7+ 支持）。
- `WM_HOTKEY` 到达 WndProc 后执行切换逻辑。
- 注册失败（快捷键被占用）→ 依次尝试**备用键**；仍失败则托盘弹提示告知用户「热键被占用，请换键」。（去掉 `MOD_NOREPEAT` 无法解除「组合键被占用」的冲突，不作为回退手段。）

### 4.4 托盘图标

- `Shell_NotifyIcon(NIM_ADD, ...)`，`NIF_ICON|NIF_MESSAGE|NIF_TIP`，回调消息号 `WM_APP+1`。
- 右键菜单：`CreatePopupMenu` + `TrackPopupMenu`，含「当前状态（只读）」「退出」。
- 状态反馈：用 `NIM_MODIFY` 更新 tooltip 文案（「已置顶 N 个窗口」/「未置顶」/「热键未注册」）或图标。

### 4.5 退出清理

按顺序执行（`atexit` 兜底 + 菜单「退出」主路径）：

1. 遍历 `pinned`，对每个仍存活的 HWND 执行 `HWND_NOTOPMOST`。存活校验不能只靠 `IsWindow`：句柄值可能被 Windows **复用**给别的窗口，需再比对类名仍是 `XLMAIN` 才还原。
2. `UnregisterHotKey`。
3. `Shell_NotifyIcon(NIM_DELETE)`。
4. 结束消息循环、退出进程。

> 关键点：`TOPMOST` 是窗口自身属性，程序退出不会自动还原，**必须先还原再退出**，否则 Excel 会「卡死」在顶上。
> 已知限制：上述兜底只覆盖**正常退出**。任务管理器强杀、崩溃、断电时进程不会执行清理，已置顶窗口会残留 `TOPMOST`。v0.1 接受此限制（见 §10）；若要彻底解决，后续需引入独立 watchdog 进程监控主进程存活。

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
│   ├── win32.py             # ★ Win32 调用的薄封装层（唯一直接 import win32 的地方）
│   ├── main.py              # 入口：装配各模块，进入消息循环
│   ├── wnd.py               # 隐藏窗口 + WndProc（路由 WM_HOTKEY / 托盘消息）
│   ├── excel.py             # 窗口识别、last_excel_hwnd 跟踪、target_hwnd()
│   ├── pinner.py            # SetWindowPos 封装 + pinned 集合 + frontmost_pinned()
│   ├── hotkey.py            # RegisterHotKey / UnregisterHotKey
│   └── tray.py              # 托盘图标 + 右键菜单
├── tests/
│   ├── test_pinner.py       # 切换状态机、集合增删、frontmost 判定（mock win32）
│   ├── test_excel.py        # 窗口筛选 / 目标判定优先级（mock win32）
│   └── test_cleanup.py      # 退出清理顺序 + 句柄复用校验（mock win32）
├── pyproject.toml
└── .gitignore
```

> **测试接缝（seam）**：所有 `win32*` API（`SetWindowPos` / `EnumWindows` / `GetForegroundWindow` / `GetWindow` / `SetWinEventHook` / `RegisterHotKey` / `Shell_NotifyIcon` …）一律收口到 `src/win32.py` 这一层。业务模块只 import `win32.py`，测试时用 pytest 的 `monkeypatch` 替换 `win32.py` 里的函数即可，不依赖真实 Windows / Excel 环境。

## 6. 关键状态与数据

| 状态 | 类型 | 说明 |
| --- | --- | --- |
| `pinned` | `set[int]` | 当前被本程序置顶的 HWND |
| `last_excel_hwnd` | `int \| None` | 最近激活的 Excel 工作簿 HWND |
| `hotkey_registered` | `bool` | 热键是否注册成功（供托盘显示「热键未注册」状态） |

状态不落盘（v0.1 不记忆），进程生命周期内有效。

## 7. 边界情况与处理

| 边界情况 | 处理 |
| --- | --- |
| 程序退出残留置顶 | 退出前统一还原（见 4.5）；异常退出强杀属已知限制 |
| 工作簿关闭 / Excel 退出 | 挂 `EVENT_OBJECT_DESTROY` 钩子**及时**从 `pinned` 剔除失效 HWND；每次操作与退出前再校验 `IsWindow` **且类名仍为 `XLMAIN`**（防句柄复用） |
| 句柄复用（HWND 被回收后另作他用） | 只存 HWND 不够，必须校验类名；`EVENT_OBJECT_DESTROY` 及时清理是正确性前提，非可选 |
| 多个工作簿 | `pinned` 为集合，每个窗口独立切换；`frontmost_pinned()` 定目标；tooltip 显示数量 |
| 点击非置顶窗口时置顶窗口仍浮在上面 | 置顶层天然高于普通层；点普通窗口它成为前台但置顶窗口仍覆盖其上 → 按快捷键时「前台工作簿」判定命中刚点的那个并置顶它（符合预期） |
| 快捷键冲突 | 注册失败 → 尝试备用键 / 提示换键（见 4.3） |
| Excel 以管理员权限运行 | `SetWindowPos` 可能静默失败 → 调用后重新 `GetWindowLong(GWL_EXSTYLE)` 校验 `WS_EX_TOPMOST` 是否真生效，失败则警告 |
| 隐藏壳窗口 `XLDESK` | 按类名严格过滤，只认 `XLMAIN` |

## 8. 测试方案

纯逻辑与 Win32 调用分离：Win32 调用统一走 `src/win32.py` 接缝，测试中用 pytest `monkeypatch` 替换，保证无 Excel 环境也能跑：

- **test_pinner**：切换语义（置顶↔取消）、集合增删、`frontmost_pinned()`（给定 mock 的 z 序，验证返回最前面的置顶窗口）、句柄复用校验（`IsWindow` 通过但类名不符时不还原）、退出清理顺序。
- **test_excel**：给定 `(hwnd, class, pid)` 列表，验证只筛出 `XLMAIN`；目标判定优先级（前台命中 → 最前置顶 → 最近激活回退）。
- **test_cleanup**：mock 后断言退出时对每个 pinned 窗口都调用了 NOTOPMOST、且先于进程退出；含句柄复用场景。

**手工验收清单**（需真实 Excel）：
1. 打开工作簿 A，按 `Win+Ctrl+T` → A 置顶；再按 → A 取消。
2. 置顶 A 后再打开 B，点 B、按快捷键 → B 也置顶（A、B 同时置顶，B 在最前）。
3. 切到别的窗口按快捷键 → 命中「最前面的置顶窗口」，取消它。
4. 点 A（提到最前）后切走再按快捷键 → 命中 A。
5. 托盘 tooltip 随状态与数量变化；右键「退出」→ 所有 Excel 恢复普通层叠。

## 9. 打包与运行

- 开发运行：`uv run python src/main.py`（先 `uv add pywin32 pytest`）。
- 发布（后续）：`pyinstaller --onefile --noconsole src/main.py`。

## 10. 风险与待确认项

1. ~~pywin32 对 Python 3.14 的 wheel 可用性~~ → **已解除**：pywin32 312 带 cp314 wheel（win32/amd64/arm64，已核实 PyPI）。保留 ctypes 兜底以防万一。
2. 全局快捷键 `Win+Ctrl+T` 是否被占用（运行时检测，失败提示换键）。
3. 托盘菜单「当前状态」的更新频率与交互细节，实现时再定。
4. **异常退出（强杀 / 崩溃）会残留置顶**：atexit 无法兜底，属已知限制。若必须解决，后续引入 watchdog 进程。
