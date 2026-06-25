# GeoChemExtractor · 开发者日志

**项目**: PDF地质文献表格爬取与数据管理软件  
**起始日期**: 2026-06-25

---

## [2026-06-25 14:47] 第1步 · 基础框架

### 已完成
- ✅ 创建 `pyproject.toml` — 项目元数据、依赖声明、构建配置、可选依赖分组
- ✅ 数据层：`database.py` — SQLite 连接管理、完整 Schema（8表）、预建索引、WAL 模式
- ✅ 数据层：`models.py` — Pydantic 模型：MajorElements、TraceElements、REEElements、Isotopes、ComputedIndices、GeochemSample（含 `to_flat_dict()` 展平方法）+ EXCEL_COLUMN_MAP
- ✅ 数据层：`repository.py` — SampleRepository（CRUD、批量导入、按类型/产区筛选）+ PDFSourceRepository
- ✅ 数据层：`project.py` — ProjectManager（.gce 项目文件的 新建/打开/保存/另存为/关闭）
- ✅ 数据层：`migrate_existing_data.py` — 支持从现有 Excel 导入到 .gce，含 65 列自动映射、值清洗
- ✅ UI：`theme.py` — Claude 颜色常量 + 完整 QSS 样式表（~300行，覆盖所有 Qt 组件）
- ✅ UI：`data_grid/model.py` — GeochemTableModel（QAbstractTableModel，94列标签，数值/文本格式）
- ✅ UI：`data_grid/view.py` — GeochemTableView（QTableView 子类，行选择，交替色，列宽预设）
- ✅ UI：`project_navigator.py` — 项目导航树（PDF/表格/样本/已分类/可导出 5组）
- ✅ UI：`sample_inspector.py` — 样本速查面板（8个关键字段）
- ✅ UI：`main_window.py` — 主窗口全功能（菜单栏/工具栏/左右分栏/标签页/状态栏）+ 所有交互逻辑
- ✅ `app.py` + `__main__.py` — 启动入口、日志配置、全局主题
- ✅ 集成测试：Excel 导入 .gce **通过**（SPGZ ALL → 935条样本，935条验证）
- ✅ 启动测试：应用正常启动，主窗口显示

### 关键数据
- 模型映射: 65/94 Excel列 → 数据库字段
- 导入性能: 953行 Excel → 935条有效样本 (98%有效率)
- 数据覆盖率: SiO2 876/935, Age 385/935, Type 600/935

### 遇到的问题
1. `migrate_existing_data.py` 导入路径问题 → 改用 `PYTHONPATH` 环境变量
2. Pydantic `field_validator` 在嵌套模型上不匹配 → 移除顶层校验器
3. Pydantic `ge=` 约束过于严格（MnO真实值可达5.14） → 移除严格范围约束
4. Qt6 `AA_UseHighDpiPixmaps` 已弃用 → try/except 包装

### 下一步
- 第2步：PDF 提取流水线（pdfplumber + PyMuPDF + OCR 准备）

---

## [2026-06-25 15:30] 第2步 · PDF 提取流水线

### 已完成
- ✅ `engine/pdf_ingestion.py` — PDFIngestionEngine：元数据提取（标题/作者/DOI/年份）、文本/图片页分类、表格候选页标记、SHA256哈希
- ✅ `engine/table_detection.py` — TableDetectionEngine：3策略检测（pdfplumber find_tables + pdfplumber text_blocks + 启发式数字对齐行），IoU去重，置信度评分
- ✅ `engine/table_extraction.py` — TableExtractionEngine：混合提取（pdfplumber + PyMuPDF + 启发式），bbox裁剪防越界，多策略兜底，脚注检测，表头估算
- ✅ `services/task_runner.py` — QThread异步任务基础框架 + BatchTaskRunner
- ✅ `services/batch_service.py` — BatchProcessingService：编排摄入→检测→提取的完整流水线
- ✅ `ui/dialogs/batch_progress.py` — BatchProgressDialog：双进度条+实时日志+取消
- ✅ `ui/table_preview.py` — TablePreviewPanel：表格选择下拉+QTableView预览+元信息
- ✅ 主窗口集成：PDF导入按钮+文件夹递归扫描+进度对话+表格预览标签页+数据库存储
- ✅ 集成测试：5篇真实地质PDF测试

### 测试结果
```
PDFs: 5 篇 (spgz/ 目录)
含表页: 80%+ 检测到疑似表格页
提取结果: 中文论文提取较好（2-7个表格），英文期刊PDF提取受限

关键发现:
- 学术论文表格多为"内联文本表格"（无框线），pdfplumber find_tables() 依赖边线，检测率低
- 自研启发式检测能有效定位数字密集区域，但列分割准确度依赖原文排版
- 英文论文中存在化学式下标丢失（如 SiO₂ → SiO）的问题
- 第3步的列识别引擎将填补列匹配gap

修复的问题:
- Bounding box 越界 → _clip_bbox_to_page()
- 编码输出乱码 → Python -X utf8 + io.TextIOWrapper
```

### 遇到的问题
1. pdfplumber `find_tables()` 对无框线学术表格检测率为0（需要边线）
2. 英文PDF中文本行"SiO₂ 74.86 ..." 下标丢失为 "SiO 74.86 ..."
3. 多策略管道中 bbox 裁剪引发越界错误
4. 中文表头单字符拆分问题（汉字被空格拆成单字）

### 下一步
- 第3步：地球化学解析 — 列识别引擎 + 值清洗器 + 单位转换 + 合并去重

---

## [2026-06-25 15:40] 第3步 · 地球化学解析

### 已完成
- ✅ `engine/element_identifier.py` — ElementIdentifier：94列目标别名（中/英文+Unicode下标），OCR纠错表，编辑距离模糊匹配
- ✅ `engine/value_cleaner.py` — ValueCleaner：LOD/BDL/ND检测，误差分离（±），数值标准化（千位分隔/科学计数法/Unicode）
- ✅ `engine/unit_converter.py` — UnitConverter：ppm↔wt%检测转换，Fe2O3↔FeO换算，Total自动估算
- ✅ `engine/geochem_parser.py` — GeochemParserEngine：列识别→清洗→转换→映射为GeochemSample的完整流水线
- ✅ `engine/merger.py` — DataMerger：按(Sample.No, DataSource)去重，冲突检测（10%容差），缺失字段自动补全
- ✅ 集成测试：端到端验证通过

### 单元测试结果
```
列识别: 53/53 英文表头 100%匹配 ✅
      12/12 中文表头 100%匹配 ✅
       7/7 OCR纠错识别 ✅ (Si02→SiO2, A1203→Al2O3, Na20→Na2O, K20→K2O...)

值清洗: 10/10 测试通过 ✅
  - "72.5±2.3" → v=72.5, err=2.3
  - "<0.01" → v=0.01, lod=True
  - "0.282515±0.000013" → v=0.282515, err=1.3e-05

解析: 模拟表格 3/3 样本正确提取 ✅
  - SiO2=72.5, Al2O3=14.3, K2O=4.5 正确

但真实PDF表格提取后全是乱码文本（中文论文中字母被空格拆成单字），
导致列识别无法匹配。这是第2步表格提取的问题（key blocker）。
在第3步解析引擎本身功能正确。
```

### 遇到的问题
1. `Y` 元素与 `Y` 坐标冲突 → latitude 别名去掉 "Y"，y元素保留
2. OCR `Na20` 被误识别为 na2o（通过ocr_correct修复）
3. 真实PDF提取的表格数据质量差（文本碎片化），解析引擎本身正确但无法处理碎片化输入
4. 表格提取质量 → 第4步评估是否调整提取策略

### 下一步
- 第4步：分类与导出 — 指数计算 + I/S/A/M分类 + 数据网格着色

---

## [2026-06-25 15:50] 第4步 · 分类与导出

### 已完成
- ✅ `geochem/indices.py` — IndexCalculator：ASI、A/CNK、A/NK、FeMgI、FeOt换算、Ga/Al×10⁴、MALI、TZr（Watson & Harrison 1983）、M值、K₂O系列分类
- ✅ `engine/classification.py` — ClassificationEngine：6步决策树 (A型→M型→S型→I型→过渡区→未分类)，置信度评分，A1/A2和SG/SC/HFI亚型，中文标签映射
- ✅ `engine/validation.py` — DataValidator：主量元素范围、总量校验、REE Oddo-Harkins平滑性、Th/U比值、CaO-LOI相关性
- ✅ `engine/export.py` — ExportEngine：94列Excel导出（分组Sheet、分类着色、表头冻结、列宽），UTF-8 BOM CSV，图解数据导出 (TAS/REE/判别)
- ✅ 单元测试全部通过

### 测试结果
```
分类测试 (4/4 通过):
  I型: ASI=0.89, Na₂O>3.2% → I-type (high)      ✅
  S型: ASI=1.21, FeMgI=0.82 → S-type SG (high)   ✅
  A型: Ga/Al=3.8, Zr=350 → A-type (high)         ✅
  M型: K₂O=0.6, Na₂O/K₂O>1 → M-type (medium)    ✅

导出测试:
  Excel分组导出 → 按Granite type分4个Sheet     ✅
  CSV UTF-8 BOM → 兼容Excel中文                ✅
  图解数据 → TAS/REE/判别 3个CSV                ✅
```

### 遇到的问题
1. Dataclass 默认值问题 → `granite_type`/`confidence` 设置 `=""` 默认值
2. 包间导入路径 → `engine/classification.py` 内 `from geochem.indices` 而非 `.indices`
3. `calc_asi()` 参数名笔误 `na2o2` → `na2o`

### 下一步
- 第5步：图表与打磨 — 内嵌图表 + 图解数据导出 + 性能优化 + 打包

---

## [2026-06-25 16:00] 第5步 · 图表与打磨

### 已完成
- ✅ `geochem/diagrams.py` — DiagramDataBuilder + ChartRenderer (Claude主题matplotlib) + CSV导出
- ✅ matplotlib 3.11 安装成功（清华镜像）
- ✅ TAS/REE球粒陨石标准化/花岗岩判别图 数据构建
- ✅ `scripts/test_step5.py` — 端到端集成测试全部通过

### 端到端测试结果
```
4样本全流程: 计算→分类→验证→图解→导出 全部 ✅
分类准确率: 4/4 (100%)
验证: 0 errors
导出: Excel 11.7KB + CSV 1.4KB + 图解数据3文件
```

### 当前项目规模
- 25个Python源文件 + 4份中文文档 + 5个脚本
- 核心引擎7模块 + 数据层4模块 + UI层6模块
- 依赖: 41个Python包

### 遇到的问题
1. PyPI SSL连接失败 → 清华镜像 (`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`)
2. matplotlib 作为可选依赖 → ChartRenderer 加 `is_available()` 检测

### 下一步
- Phase 2 · P0 核心补强：表格质量优化 + 分类对话框 + 导出对话框

---

## [2026-06-25 17:00] Phase 2 · P0 核心补强

### 已完成
- ✅ P2-01：表格提取质量优化 — 化学式碎片化修复模块（`merge_fragmented_chemicals`, `normalize_chemical_header`）
- ✅ P2-02：数据网格分类着色 — QTableView 行按 I/S/A/M型 着色（10%透明度分类色），`GeochemTableModel.data()` 新增 `Qt.BackgroundRole` 支持

### 待完成
- ✅ P2-03：分类对话框（ClassificationDialog + ClassificationTableModel）
- ✅ P2-04：导出对话框（ExportDialog 列/Sheet/格式选择）
- ✅ 集成测试：10样本分类+导出测试全部通过

### 下一步
- Phase 2 · P2：OCR 图片表格提取 + PyInstaller 一键打包脚本 + 中文使用手册

---

## [2026-06-25 17:30] Phase 2 · P1 交互增强

### 已完成
- ✅ P2-05：动态筛选面板 — FilterPanel（矿区/岩体/类型/年龄/SiO2范围等多条件组合，实时筛选+计数+清除）
- ✅ P2-06：合并冲突解决对话框 — MergeConflictDialog（差异对比表格+逐字段选择+批量应用策略）
- ✅ P2-07：内嵌图表 Qt 画布 — ChartCanvas（TAS/REE/判别图 matplotlib 嵌入，图表类型切换）
- ✅ P2-08：图表联动 — 点击TAS图数据点 → 在数据网格中高亮对应行
- ✅ 主窗口集成：筛选面板嵌入左侧栏 + 图表标签页替换占位符 + Toolbar新增分类/导出按钮

### 集成测试
```
筛选面板: SiO2 70-80% → 12/20 行 ✅
合并对话框: 1个冲突样本，4个差异字段 ✅
图表数据: TAS=5点, REE=5条曲线, 判别=5点 ✅
图表联动: click(65.1,5.6) → nearest idx=0 (dist=0.14) ✅
```

### 下一步
- Phase 2 P2：OCR + 打包脚本 + 中文使用手册

### 待完成
- ✅ 生成 `requirements-lock.txt`（41个包版本锁定）

### 遇到的问题
- 无

### 关键决策
- 确认 pdfplumber 为主提取引擎，PyMuPDF 为辅，Camelot 为备选
- PaddleOCR 标记为第2阶段可选依赖（避免初期安装复杂度）
- pyrolite/matplotlib 标记为后续阶段依赖

### 下一步
- 第1步：基础框架 — 创建 SQLite schema、Pydantic模型、Claude主题UI、数据网格

---

_日志格式说明：每次操作后添加新条目，包含[日期 时间]、已完成事项、待办事项、遇到的问题和下一步计划。_
