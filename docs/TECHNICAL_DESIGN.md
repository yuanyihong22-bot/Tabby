# 桌面表格便签 · 技术方案

> 版本：v0.1（MVP）　|　对应产品设计：`../PRODUCT_DESIGN.md`

## 1. 概述与目标

实现一个 Tkinter 桌面小组件：把粘贴进来的表格数据显示成便签式表格，点击单元格复制内容，数据本地持久化。本方案覆盖 v0.1 的五个功能点：无边框可拖动小组件、粘贴/录入数据、点选复制、持久化、右键菜单。

## 2. 技术选型

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 语言 | Python 3.14 | 本机已装 |
| GUI | Tkinter（标准库） | 零额外依赖，支持无边框窗口、拖动、剪贴板 |
| 剪贴板 | Tkinter `clipboard_clear` / `clipboard_append` | 标准库，无需 pyperclip |
| 持久化 | JSON 文件 | 简单可靠、可读 |
| 测试 | pytest | 对纯逻辑（解析、序列化）做单元测试 |

> 与「置顶」方案相比：技术栈换为 Tkinter，**不再依赖 pywin32**，无第三方安装、无 Win32 句柄/进程等平台细节，风险显著降低。

## 3. 整体架构

单进程、单线程，Tkinter `mainloop` 事件循环统一处理所有交互。

```
┌──────────────────────────────────────────────┐
│ main.py  入口：装配 model/storage/widget，启动循环│
│   ├─ widget.py  小组件窗口（渲染 + 拖柄 + 点选 + 菜单）│
│   ├─ editor.py  编辑窗口（粘贴文本 → 解析 → 回写）│
│   ├─ model.py   表格数据模型 + 粘贴文本解析       │
│   └─ storage.py JSON 持久化（保存 / 加载）        │
└──────────────────────────────────────────────┘
```

**状态归属**（避免隐式共享）：

- 表格数据归 `model.py` 持有（`rows: list[list[str]]`），对外暴露 `rows` / `cell(r, c)` / `apply_text(text)`。
- 窗口位置归 `storage.py` 随数据一起读写。
- `widget.py` 只做渲染与事件转发；`editor.py` 只做「读文本 → `model.apply_text` → 回写重绘」。不直接改数据，走公开接口。
- `main.py` 负责装配（把 model / storage 实例经构造器注入 widget、editor）。

## 4. 核心机制设计

### 4.1 数据模型与粘贴解析

- 内部表示：`rows: list[list[str]]`。
- **解析规则**：整段文本按 `\n` 分行、每行按 `\t` 分列。Excel 复制出的单元格天然是「Tab 分列 + 换行分行」，直接兼容；也接受 CSV 风格（逗号分隔，`csv` 模块解析）作为补充。
- 列数不一致：以最长行为准，短行用空串补齐，保证表格矩形完整。
- `apply_text(text)` 返回解析后的 rows，供 editor 调用。

### 4.2 小组件窗口

- `overrideredirect(True)` 去边框，无标题栏。
- **拖柄**：顶部一条细横条绑定 `<Button-1>` / `<B1-Motion>`，拖动更新 `geometry('+x+y')`；单元格区不响应拖动，避免「点复制」与「拖动」冲突。
- **非置顶**：默认普通 z-order，会被其他窗口盖住（符合「像便签」需求）。
- 位置持久化：坐标随数据存入 JSON；启动加载时夹取到屏幕可见范围内。

### 4.3 表格渲染与点选复制

- 用单个 `Canvas` 自绘网格线与文本，按内容尺寸自适应窗口大小。
- **点选复制**：绑定单元格区 `<Button-1>`，由点击坐标反算行列 → 取 `model.cell(r, c)` → 写剪贴板 → 短暂高亮该格作为反馈。
- 长文本：v0.1 按列宽截断显示，完整内容仍可复制。

### 4.4 编辑

- 右键菜单「编辑」打开 `Toplevel` 编辑窗，内含多行 `Text` 控件（用户粘贴）。
- 「应用」：读 `Text` 内容 → `model.apply_text` → 重绘 widget → `storage.save`。
- 「取消」：丢弃改动，不改 model、不落盘。

### 4.5 持久化

- 存储路径：`%APPDATA%\TableStickyNote\table.json`（`storage` 接受可注入路径，测试用 `tmp_path`）。
- 结构：`{"rows": [...], "window": {"x": ..., "y": ...}}`。
- 启动加载；编辑应用后自动保存；文件缺失用空表默认值；JSON 损坏时回退空表并提示。

## 5. 目录结构

```
E:\AI_Tools\EXCEL_desktop\
├── AGENTS.md
├── PRODUCT_DESIGN.md
├── README.md                # 使用说明（实现时补）
├── docs/
│   └── TECHNICAL_DESIGN.md  # 本文档
├── src/
│   ├── __init__.py
│   ├── main.py              # 入口：装配并启动 mainloop
│   ├── widget.py            # 小组件窗口（渲染/拖柄/点选/菜单）
│   ├── editor.py            # 编辑窗口
│   ├── model.py             # 数据模型 + 粘贴文本解析
│   └── storage.py           # JSON 持久化
├── tests/
│   ├── test_model.py        # 解析 / 列补齐 / 取值
│   └── test_storage.py      # JSON round-trip / 缺省 / 损坏回退
├── pyproject.toml
└── .gitignore
```

## 6. 关键状态与数据

| 状态 | 类型 | 说明 |
| --- | --- | --- |
| `rows` | `list[list[str]]` | 表格内容（model 持有） |
| `window.x / window.y` | `int` | 窗口位置（随 JSON 持久化） |

## 7. 边界情况与处理

| 边界情况 | 处理 |
| --- | --- |
| 粘贴数据列数不一致 | 以最长行为准补空串 |
| 空单元格 / 空行 | 保留为 `""`，渲染为空格，可复制空串 |
| 超长文本 | 截断显示，完整内容仍可复制 |
| 窗口拖出屏幕 | 启动加载时夹取坐标到可见区域 |
| 剪贴板写入失败 | 捕获异常，不中断程序 |
| 数据文件损坏 / 缺失 | 捕获解析异常，回退空表并提示 |

## 8. 测试方案

纯逻辑层（model / storage）与 GUI 层（widget / editor）分离，前者可单测，后者手工验收：

- **test_model**：粘贴文本解析（Tab/换行）、CSV 解析、列数补齐、取单元格值、空输入、含空行空列。
- **test_storage**：保存→加载 round-trip、文件缺失返回空表、JSON 损坏回退空表。

**手工验收清单**：
1. 打开工具 → 桌面出现空表格便签。
2. 从 Excel 复制一块区域 → 右键「编辑」粘贴 → 应用 → 表格正确渲染。
3. 点任意单元格 → 到别处 Ctrl+V，内容一致。
4. 拖动拖柄换位置 → 重启 → 位置与数据都恢复。

## 9. 运行与打包

- 开发运行：`python src/main.py`。
- 发布（后续）：`pyinstaller --onefile --noconsole src/main.py`（Tkinter 打包用 `--windowed`，注意图标资源路径）。

## 10. 风险与待确认项

1. `overrideredirect` 无边框窗口的右键菜单需手动 `Menu.tk_popup` 弹出（实现时用菜单绑定解决）。
2. 点选命中精度：Canvas 需按字体实际像素计算行列，v0.1 用统一等宽字体（如 Consolas）简化。
3. 剪贴板内容为纯文本，不带格式（v0.1 足够，复杂格式留迭代）。
4. 拖柄与单元格的交互分区（拖柄拖动 / 单元格复制）需在实现时验证手感。
