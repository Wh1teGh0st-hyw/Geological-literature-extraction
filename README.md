# GeoChemExtractor · 地质文献PDF表格提取与地球化学数据管理软件

<p align="center">
  <b>📊 从 PDF 中自动提取地质化学数据 ｜ 🔬 I/S/A/M 型花岗岩自动分类 ｜ 📈 地球化学图解数据导出</b>
</p>

---

## 简介

GeoChemExtractor 是一款面向地质学研究人员的 Windows 桌面应用。它能够**自动从学术论文 PDF 中提取地球化学数据表格**，在 94 列标准化 Excel 模板中管理数据，并**根据地球化学判别规则自动分类花岗岩类型**（I型/S型/A型/M型）。

设计理念：**简洁 · 学术风 · Claude 橙 + 深色主题 · 离线可用**

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 🔍 **PDF 表格自动提取** | 支持中外文学术论文，基于 pdfplumber + PyMuPDF 的混合提取策略，批量处理 |
| 🧪 **地球化学数据解析** | 自动识别 94 列元素/氧化物表头，智能清洗数值（LOD、误差、异常值），单位转换 |
| 🏷️ **花岗岩类型自动分类** | 6 步决策树 (ASI/FeMgI/Ga/Al/Zr)，A1/A2、SG/SC/HFI 亚型，置信度评估 |
| ✅ **数据质量验证** | 主量元素总量检查、REE 配分平滑性、Th/U 比值等交叉校验 |
| 📊 **Excel 导出** | 94 列标准模板，按花岗岩类型分 Sheet，分类着色行，UTF-8 BOM CSV |
| 📈 **图解数据导出** | TAS 分类图、REE 球粒陨石标准化、花岗岩判别图数据 (CSV) |
| 📂 **项目持久化** | `.gce` 单文件格式（SQLite），便携可分享，支持打开/保存/另存为 |

---

## 快速开始

### 方式一：下载 .exe（推荐，无需 Python）

从 [Releases](https://github.com/your-username/Geological-literature-extraction/releases) 下载最新版 `GeoChemExtractor.exe`，双击运行。

### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/Geological-literature-extraction.git
cd Geological-literature-extraction/GeoChemExtractor

# 2. 创建虚拟环境并安装依赖
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt

# 3. 启动应用
export PYTHONPATH=".:geochem_extractor"
python geochem_extractor/app.py
```

### 已有 Excel 数据导入

```bash
# 将现有 Excel 迁移到 .gce 项目
python scripts/migrate_existing_data.py 松潘甘孜花岗岩统计.xlsx -o 数据导出.gce -s "SPGZ ALL"
```

---

## 项目结构

```
GeoChemExtractor/
├── geochem_extractor/          # 主 Python 包
│   ├── app.py                  # 应用入口
│   ├── data/                   # 数据层 (SQLite + Pydantic)
│   ├── ui/                     # UI 层 (PySide6 + Claude 主题)
│   ├── engine/                 # 引擎层 (PDF提取 + 分类 + 导出)
│   ├── services/               # 服务层 (QThread 异步任务)
│   └── geochem/                # 地球化学计算 (指数 + 图解)
├── scripts/                    # 工具脚本
├── docs/                       # 项目文档
├── DEVLOG.md                   # 开发者日志
├── requirements.txt            # Python 依赖
└── pyproject.toml              # 项目元数据
```

---

## 技术栈

| 类别 | 库 | 用途 |
|------|----|------|
| UI | PySide6 (Qt6) | 桌面界面框架 |
| PDF | pdfplumber + PyMuPDF | 表格提取与检测 |
| 数据 | pandas + openpyxl | DataFrame + Excel 读写 |
| 模型 | pydantic | 94列数据验证 |
| 图表 | matplotlib | TAS/REE/判别图 |
| 日志 | loguru | 滚动日志 |
| 存储 | SQLite | 零配置数据持久化 |
| 打包 | PyInstaller | Windows .exe 生成 |

---

## 花岗岩分类方法

采用多步骤地球化学判定流程：

1. **A型** — Ga/Al > 2.6 且 Zr > 250 且 FeMgI > 0.85（高温、无水、碱性）
2. **M型** — K₂O < 0.8 且 Na₂O > K₂O 且 SiO₂ > 63（岛弧玄武质分异）
3. **S型** — ASI > 1.1（过铝质，源自沉积岩部分熔融）
4. **I型** — ASI < 1.0（准铝质，源自火成岩部分熔融）
5. **过渡区** — ASI 1.0-1.1 综合 Na₂O 和 FeMgI 辅助判定

详细说明见 [docs/03-设计规范.md](docs/03-设计规范.md)

---

## 开发路线图

| 阶段 | 状态 |
|------|------|
| Phase 1 · 核心功能 | ✅ 已完成 — PDF提取 + 解析 + 分类 + 导出 + 图解 |
| Phase 2 · 增强功能 | 📋 规划中 — 分类UI、筛选面板、OCR、使用手册 |

详见 [docs/04-执行步骤.md](docs/04-执行步骤.md)

---

## 系统要求

- **操作系统**：Windows 10 / 11（64位）
- **Python**：3.10+（如从源码运行）
- **内存**：≥ 4 GB
- **磁盘**：≥ 500 MB（含依赖）

---

## 贡献与反馈

欢迎通过 GitHub Issues 提交 bug、功能请求或改进建议。

---

**GeoChemExtractor** · 让地质数据收集不再枯燥 ✨
