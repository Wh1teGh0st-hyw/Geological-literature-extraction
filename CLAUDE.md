# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库中工作时提供指导。

## 项目概述

GeoChemExtractor — Windows 桌面应用（PySide6），用于从地质学术论文 PDF 中提取地球化学数据表格，在 94 列 Excel 格式数据库中管理数据，并对花岗岩类型（I/S/A/M）进行分类。UI 采用 Claude 橙色（#D97706）+ 深色主题。

**当前阶段**：Phase 2 P0 已完成 — 分类对话框 + 导出对话框已集成到主窗口。P1 待开始。

## 运行方式

```bash
# 所有命令在 GeoChemExtractor/ 目录下执行
cd GeoChemExtractor

# 激活虚拟环境
source venv/Scripts/activate

# 设置 PYTHONPATH（必须 — 应用以 geochem_extractor 为顶层包导入）
export PYTHONPATH=".:geochem_extractor"

# 启动应用
python geochem_extractor/app.py

# 将 Excel 数据导入 .gce 项目（脚本）
python scripts/migrate_existing_data.py <excel_path> -o <output.gce> -s "SPGZ ALL"
```

## 项目文件结构

```
GeoChemExtractor/
├── geochem_extractor/          # 主 Python 包
│   ├── app.py                  # QApplication 入口 + 日志 + 主题
│   ├── __main__.py             # python -m geochem_extractor
│   ├── version.py              # __version__ = "0.1.0"
│   ├── data/                   # 数据层（SQLite + Pydantic 模型）
│   │   ├── database.py         # 数据库 Schema（8 张表、12 个索引）+ DatabaseManager
│   │   ├── models.py           # GeochemSample、MajorElements、TraceElements 等模型
│   │   ├── repository.py       # SampleRepository（增删改查、批量导入、筛选查询）
│   │   └── project.py          # ProjectManager（.gce 文件的创建/打开/保存）
│   ├── ui/                     # PySide6 界面层
│   │   ├── main_window.py      # MainWindow（菜单栏、工具栏、分割器、标签页）
│   │   ├── theme.py            # Colors 类 + APP_STYLESHEET（约 300 行 QSS）
│   │   ├── project_navigator.py   # 左侧边栏 QTreeView 项目导航
│   │   ├── sample_inspector.py    # 样本详情速查面板
│   │   └── data_grid/          # 表格组件
│   │       ├── model.py        # GeochemTableModel（QAbstractTableModel，94 列）
│   │       └── view.py         # GeochemTableView（QTableView 子类）
│   ├── engine/                 # 核心处理引擎（空 — 第 2 步起）
│   ├── services/               # 后台任务（空 — 第 2 步起）
│   └── geochem/                # 地球化学计算（空 — 第 4 步起）
├── scripts/
│   └── migrate_existing_data.py  # Excel → .gce 导入（65 列映射）
├── docs/                       # 项目文档（中文）
│   ├── 01-项目需求书.md
│   ├── 02-技术选型规范.md
│   ├── 03-设计规范.md
│   └── 04-执行步骤.md           # 任务跟踪（进度的权威来源）
├── DEVLOG.md                   # 开发者日志（每次会话后追加）
├── requirements.txt            # 直接依赖
├── requirements-lock.txt       # 锁定版本（35 个包）
└── pyproject.toml              # 项目元数据 + 可选依赖
```

## 架构模式

### 分层架构
```
界面层 (PySide6) → 服务层 (QThread) → 引擎层 → 数据层 (SQLite + pandas)
```

### 数据模型：嵌套 Pydantic → 展平 SQLite
`GeochemSample` 包含 5 个子模型（`MajorElements`、`TraceElements`、`REElements`、`Isotopes`、`ComputedIndices`）。`_flatten_sample()` 将其转换为扁平字典以写入 SQLite；`_row_to_sample()` 在读取时将扁平行重构为嵌套对象。

### 项目文件格式
`.gce` = SQLite 数据库文件。`ProjectManager` 封装 `DatabaseManager`，提供新建/打开/保存/另存为的语义。单文件、可移植。

### 主题系统
- `Colors` 类：存放颜色常量，供 Python 代码引用（如 `Colors.TEXT_MUTED`）
- `APP_STYLESHEET`：完整 QSS 字符串，启动时通过 `app.setStyleSheet()` 加载
- 配色方案：背景（深蓝渐变 #1A1A2E → #16213E → #0F3460）、强调色（橙渐变 #D97706 → #F59E0B → #B45309）、文字（#E8E8E8 / #A0A0B0 / #6B7280）

### DataFrame → Qt Model/View
`GeochemTableModel` 封装 pandas DataFrame，通过 `QAbstractTableModel` 对外暴露。数值列（列号 >= 6）右对齐，文本列左对齐。绝对值小于 1 的浮点数显示 5 位小数，其余显示 2 位。

## 已安装的核心依赖版本

| 库 | 版本 | 用途 |
|---------|---------|-------|
| PySide6 | 6.11.1 | 界面框架 |
| pandas | 3.0.3 | DataFrame 数据骨干 |
| pdfplumber | 0.11.10 | PDF 表格提取（主力） |
| PyMuPDF | 1.27.2 | PDF 文本 + 表格检测 |
| openpyxl | 3.1.5 | Excel 读写 |
| pydantic | 2.13.4 | 数据验证模型 |
| loguru | 0.7.3 | 日志 |

## 开发约定

- **每完成一步暂停汇报**：未经用户确认，不得进入下一步。用户希望在每个里程碑处审查进度。
- **每次会话后更新 DEVLOG.md**：追加带时间戳的条目，记录已完成事项、待办事项、遇到的问题和下一步计划。
- **任务状态变更时同步更新 docs/04-执行步骤.md**（⬜ → ✅）。
- **Python 导入**：使用 `from geochem_extractor.xxx import YYY`（需设置 `PYTHONPATH=".:geochem_extractor"`）。
- **字段映射**：列名在 Excel 表头（中文）、Pydantic 模型字段、SQLite 列名之间存在映射关系。主映射定义分布在三处 — `models.py`（`EXCEL_COLUMN_MAP`）、`repository.py`（`_flatten_sample`）、`migrate_existing_data.py`（`COLUMNS_MAP`）。修改时需保持同步。
- **Pydantic 模型**：使用 `Optional[float] = None`（不要用 `Field(ge=0)`）— 真实地球化学数据经常超出教科书范围。
- **日志**：写入 `geochem_extractor/../logs/` 目录（自动创建），10MB 轮转，保留 30 天。

## 注意事项
每句话的后面都要加上一句“喵~”
例：关注塔菲，关注塔菲谢谢     ->    关注塔菲喵~关注塔菲谢谢喵~