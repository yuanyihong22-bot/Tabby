# 桌面表格便签 · 技术方案

> 版本：v0.1（MVP）　|　对应产品设计：`../PRODUCT_DESIGN.md`

## 1. 概述与目标

实现一个 Tkinter 桌面小组件：把粘贴进来的表格数据显示成 Excel 样式的便签表格，点击单元格复制内容，数据本地持久化。覆盖 v0.1 功能：无边框可拖动小组件、直接粘贴（Ctrl+V）、点选复制、Excel 样式渲染、持久化、右键菜单。

## 2. 技术选型

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 语言 | Python 3.14 | 本机已装 |
| GUI | Tkinter（标准库） | 零第三方运行时依赖 |
| 剪贴板 | Tkinter `clipboard_get` / `clear` / `append` | 标准库 |
| 持久化 | JSON 文件 | 简单可靠 |
| 测试 | pytest | 纯逻辑单测 |
| 打包 | PyInstaller | `--onefile --noconsole` |

## 3. 整体架构

单进程、单线程，Tkinter `mainloop` 事件循环统一处理交互。

```
main.py      入口：装配 model/storage/widget，启动循环
widget.py    小组件窗口（Excel 样式渲染 + 拖柄 + 点选复制 + 直接粘贴 + 右键菜单）
model.py     数据模型 + 粘贴解析（原地替换，与持久化共享引用）
storage.py   JSON 持久化（数据 + 窗口位置）
launcher.py  打包入口（from src.main import main）
```

**状态归属**：`model` 持有 `rows`，`apply_text` / `clear` 用切片赋值原地替换，与 `storage` 读出的 `data.rows` 保持同一列表引用，保存无需手动同步。

## 4. 核心机制设计

### 4.1 数据模型与粘贴解析

- 内部表示：`rows: list[list[str]]`。
- 解析：按 `\n` 分行、按 `\t` 分列；列数不一致以最长行补空串；去末尾空行。**不做 CSV 逗号回退**（单列表格按「每行一个单元格」处理）。
- `apply_text` / `clear` / `append_text` 用原地操作保持与 `data.rows` 的共享引用；`append_text` 把新内容追加到表格下方并重新补齐列宽。

### 4.2 小组件窗口

- `overrideredirect(True)` 无边框、非置顶。
- 顶部细拖柄（`DRAG_H`）拖动；`ButtonRelease` 时保存位置。
- 位置夹取到屏幕可见范围内。

### 4.3 Excel 样式渲染

- 左上角角格 + 列标题 A/B/C…（`_col_letter`）+ 行号 1/2/3…，表头灰底。
- 数据格白底 + 浅灰网格线。
- 数字右对齐（`_is_number` 判断 float 可解析）、文本左对齐。
- 超长文本按列宽截断加省略号。
- 点选：坐标反算行列（扣除表头偏移）→ 点击复制 → 高亮 300ms。

### 4.4 直接粘贴

- Ctrl+V（root 绑定）或右键 → 粘贴：`clipboard_get()` 读剪贴板 → `append_text`（追加到下方，列宽自动补齐）→ 重绘 → 保存。
- 剪贴板为空 / 非文本时忽略（捕获 `TclError`）。

### 4.5 持久化

- 路径：`%APPDATA%\TableStickyNote\table.json`；结构 `{"rows": [...], "window": {"x": .., "y": ..}}`。
- 启动加载；粘贴 / 清空 / 拖动结束 / 退出时保存；JSON 损坏回退空表。

## 5. 目录结构

```
E:\AI_Tools\EXCEL_desktop\
├── AGENTS.md / PRODUCT_DESIGN.md / README.md
├── pyproject.toml / uv.lock / launcher.py
├── docs/TECHNICAL_DESIGN.md
├── src/{__init__, main, widget, model, storage}.py
└── tests/{conftest, test_model, test_storage}.py
```

## 6. 边界情况与处理

| 边界情况 | 处理 |
| --- | --- |
| 粘贴列数不一致 | 以最长行补空串 |
| 空单元格 / 空行 | 保留 `""`，渲染为空格 |
| 超长文本 | 截断显示，复制时取完整内容 |
| 窗口拖出屏幕 | 启动夹取坐标到可见区 |
| 剪贴板写入失败 | 捕获异常，不中断 |
| 数据文件损坏 / 缺失 | 回退空表 |

## 7. 测试方案

- **test_model**：解析（Tab/换行、单列无 Tab、列补齐、空输入、CRLF）、`clear`、原地替换共享。
- **test_storage**：round-trip、缺省、损坏回退、父目录创建、类型强转。

**手工验收清单**：粘贴 → 渲染；点击 → 复制；拖动 → 位置保持；重启 → 恢复。

## 8. 运行与打包

- 开发：`uv run python -m src.main`（或 `uv run python launcher.py`）
- 打包：`uv run pyinstaller --onefile --noconsole --name table-note launcher.py` → `dist/table-note.exe`

## 9. 风险与待确认项

1. `overrideredirect` 窗口的 Ctrl+V 依赖窗口获焦；右键 → 粘贴为无焦点兜底。
2. 点选命中依赖字体像素测量，用统一字体简化。
3. 剪贴板内容为纯文本，不带格式。
