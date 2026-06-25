"""主窗口 — GeoChemExtractor 应用程序主体。

包含菜单栏、工具栏、左右分栏布局（导航+检查器｜数据网格/预览/图表）。
"""

import os
from typing import Optional
from loguru import logger

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QToolBar, QStatusBar, QTabWidget, QFileDialog,
    QMessageBox, QLabel, QApplication,
)
from PySide6.QtCore import Qt, QSize, QTimer, QThread
from PySide6.QtGui import QAction, QKeySequence, QIcon

from .theme import Colors, APP_STYLESHEET
from .project_navigator import ProjectNavigator
from .sample_inspector import SampleInspector
from .data_grid.view import GeochemTableView
from .table_preview import TablePreviewPanel
from .filter_panel import FilterPanel
from .charts.canvas import ChartCanvas
from .dialogs.batch_progress import BatchProgressDialog

# 延迟加载数据层 / 服务层（避免启动时的导入依赖）
from data.project import ProjectManager
from data.database import DatabaseManager
from data.repository import SampleRepository
from scripts.migrate_existing_data import import_excel_to_db


class MainWindow(QMainWindow):
    """GeoChemExtractor 主窗口。"""

    def __init__(self):
        super().__init__()
        self._project = ProjectManager()
        self._setup_window()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._apply_theme()
        self._connect_signals()
        self._update_ui_state()

        # 启动后静默检测更新
        self._check_for_updates()

    # ── 窗口初始化 ──────────────────────────────────

    def _setup_window(self):
        """配置主窗口属性。"""
        self.setWindowTitle("GeoChemExtractor — PDF地质文献表格提取与数据管理")
        self.setMinimumSize(1200, 720)
        self.resize(1400, 850)
        # 居中显示
        screen = QApplication.primaryScreen().availableGeometry()
        center_x = (screen.width() - self.width()) // 2
        center_y = (screen.height() - self.height()) // 2
        self.move(center_x, center_y)

    def _apply_theme(self):
        """应用 Claude 主题样式表。"""
        self.setStyleSheet(APP_STYLESHEET)

    # ── 菜单栏 ─────────────────────────────────────

    def _setup_menu_bar(self):
        """构建菜单栏。"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件(&F)")

        self._new_action = QAction("新建项目(&N)", self)
        self._new_action.setShortcut(QKeySequence.New)
        self._new_action.triggered.connect(self._on_new_project)
        # 工具栏
        self._classify_action = QAction("自动分类(&C)", self)
        self._classify_action = QAction("自动分类(&C)", self)
        self._classify_action.triggered.connect(self._on_classify)
        self._export_action = QAction("导出数据(&E)", self)
        self._export_action.triggered.connect(self._on_export_data)
        self._refresh_action = QAction("刷新数据(&R)", self)
        self._refresh_action.setShortcut(QKeySequence("F5"))
        self._refresh_action.triggered.connect(self._on_refresh)

        self._open_action = QAction("打开项目(&O)", self)
        self._open_action.setShortcut(QKeySequence.Open)
        self._open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(self._open_action)

        self._save_action = QAction("保存项目(&S)", self)
        self._save_action.setShortcut(QKeySequence.Save)
        self._save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(self._save_action)

        self._save_as_action = QAction("另存为(&A)...", self)
        self._save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._save_as_action.triggered.connect(self._on_save_as_project)
        file_menu.addAction(self._save_as_action)

        file_menu.addSeparator()

        self._import_excel_action = QAction("导入Excel数据(&I)...", self)
        self._import_excel_action.setShortcut(QKeySequence("Ctrl+I"))
        self._import_excel_action.triggered.connect(self._on_import_excel)
        file_menu.addAction(self._import_excel_action)

        self._import_pdf_action = QAction("导入PDF文献(&P)...", self)
        self._import_pdf_action.setShortcut(QKeySequence("Ctrl+Shift+I"))
        self._import_pdf_action.triggered.connect(self._on_import_pdf)
        self._import_pdf_action.setEnabled(True)  # 第2阶段已启用
        file_menu.addAction(self._import_pdf_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menu_bar.addMenu("编辑(&E)")

        copy_action = QAction("复制选中行(&C)", self)
        copy_action.setShortcut(QKeySequence.Copy)
        edit_menu.addAction(copy_action)

        delete_action = QAction("删除选中行(&D)", self)
        delete_action.setShortcut(QKeySequence.Delete)
        edit_menu.addAction(delete_action)

        # 视图菜单
        view_menu = menu_bar.addMenu("视图(&V)")
        view_menu.addAction(self._refresh_action)

        # 分类菜单
        classify_menu = menu_bar.addMenu("分类(&C)")
        classify_menu.addAction(self._classify_action)

        batch_classify = QAction("批量重分类(&B)", self)
        batch_classify.triggered.connect(self._on_batch_reclassify)
        classify_menu.addAction(batch_classify)

        # 工具菜单
        tools_menu = menu_bar.addMenu("工具(&T)")
        tools_menu.addAction(self._export_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ── 工具栏 ─────────────────────────────────────

    def _setup_toolbar(self):
        """构建工具栏。"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 项目操作
        toolbar.addAction(self._new_action)
        toolbar.addAction(self._open_action)
        toolbar.addAction(self._save_action)
        toolbar.addSeparator()

        # 导入
        toolbar.addAction(self._import_excel_action)
        toolbar.addAction(self._import_pdf_action)
        toolbar.addSeparator()

        # 分类与导出（Phase 2 已启用）
        self._classify_action = QAction("自动分类(&C)", self)
        self._classify_action.triggered.connect(self._on_classify)
        toolbar.addAction(self._classify_action)

        self._export_action = QAction("导出数据(&E)", self)
        self._export_action.setShortcut(QKeySequence("Ctrl+E"))
        self._export_action.triggered.connect(self._on_export_data)
        toolbar.addAction(self._export_action)

    # ── 中央区域 ───────────────────────────────────

    def _setup_central_widget(self):
        """构建左右分栏布局。"""
        central = QWidget()
        self.setCentralWidget(central)

        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(4, 0, 4, 4)
        h_layout.setSpacing(0)

        # 水平分割器
        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧栏 ──
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        # 项目导航器
        self._navigator = ProjectNavigator()
        left_layout.addWidget(self._navigator, 3)

        # 筛选面板
        self._filter_panel = FilterPanel()
        left_layout.addWidget(self._filter_panel, 2)

        # 样本速查面板
        self._inspector = SampleInspector()
        left_layout.addWidget(self._inspector, 1)

        splitter.addWidget(left_panel)

        # ── 右侧主内容区 ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(4)

        # 标签页
        self._tab_widget = QTabWidget()

        # 数据网格标签页
        self._data_grid = GeochemTableView()
        self._tab_widget.addTab(self._data_grid, "📊 数据网格")

        # 表格预览标签页
        self._table_preview = TablePreviewPanel()
        self._tab_widget.addTab(self._table_preview, "📋 表格预览")

        # 图表标签页
        self._chart_canvas = ChartCanvas()
        self._tab_widget.addTab(self._chart_canvas, "📈 图表")

        right_layout.addWidget(self._tab_widget)
        splitter.addWidget(right_panel)

        # 设置分割比例 (左:右 = 1:4)
        splitter.setSizes([250, 950])
        h_layout.addWidget(splitter)

    # ── 状态栏 ─────────────────────────────────────

    def _setup_status_bar(self):
        """构建状态栏。"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._status_project = QLabel("无项目")
        self._status_project.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self._status_project)

        self._status_samples = QLabel("")
        self._status_samples.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self._status_samples)

        self._status_modified = QLabel("")
        self._status_modified.setStyleSheet(f"color: {Colors.STATUS_WARNING}; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self._status_modified)

    # ── 信号连接 ───────────────────────────────────

    def _connect_signals(self):
        """连接各种 UI 信号。"""
        self._data_grid.row_selected.connect(self._on_row_selected)
        self._data_grid.sample_count_changed.connect(self._on_sample_count_changed)
        self._filter_panel.filter_changed.connect(self._on_filter_changed)
        self._filter_panel.filter_cleared.connect(self._on_filter_cleared)
        self._chart_canvas.sample_selected.connect(self._on_chart_sample_selected)
        self._chart_canvas.refresh_requested.connect(self._on_chart_refresh)

    # ── 菜单/工具栏 回调 ────────────────────────────

    def _on_new_project(self):
        """新建项目。"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "新建项目", "", "GeoChemExtractor Project (*.gce)"
        )
        if not file_path:
            return
        if not file_path.endswith(".gce"):
            file_path += ".gce"

        try:
            self._project.new_project(file_path)
            self._update_ui_state()
            self.status_bar.showMessage(f"新项目已创建: {file_path}", 3000)
            logger.info(f"新建项目: {file_path}")
        except FileExistsError:
            QMessageBox.warning(self, "文件已存在", f"项目文件已存在:\n{file_path}")

    def _on_open_project(self):
        """打开项目。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "GeoChemExtractor Project (*.gce)"
        )
        if not file_path:
            return

        try:
            self._project.open_project(file_path)
            self._load_project_data()
            self._update_ui_state()
            self.status_bar.showMessage(f"项目已打开: {file_path}", 3000)
            logger.info(f"打开项目: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", str(e))
            logger.error(f"打开项目失败: {e}")

    def _on_save_project(self):
        """保存项目。"""
        try:
            if self._project.project_path:
                self._project.save_project()
                self._update_ui_state()
                self.status_bar.showMessage("项目已保存", 2000)
            else:
                self._on_save_as_project()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_save_as_project(self):
        """另存为项目。"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "另存为", "", "GeoChemExtractor Project (*.gce)"
        )
        if not file_path:
            return
        if not file_path.endswith(".gce"):
            file_path += ".gce"

        try:
            self._project.save_as_project(file_path)
            self._update_ui_state()
            self.status_bar.showMessage(f"项目已另存为: {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "另存为失败", str(e))

    def _on_import_excel(self):
        """导入 Excel 数据到当前项目。"""
        if not self._project.has_project:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入Excel数据", "",
            "Excel文件 (*.xlsx *.xls)"
        )
        if not file_path:
            return

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
            sheets = wb.sheetnames
            wb.close()

            # 简单选择第一个 Sheet（后续可用对话框选择）
            sheet_name = "SPGZ ALL" if "SPGZ ALL" in sheets else sheets[0]

            count = import_excel_to_db(
                excel_path=file_path,
                db=self._project.db,
                sheet_name=sheet_name,
            )

            self._load_project_data()
            self._update_ui_state()
            self.status_bar.showMessage(
                f"导入完成: {count} 条样本 (Sheet: {sheet_name})", 5000
            )
            logger.info(f"Excel导入: {file_path} → {count} 条")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入 Excel 数据时出错:\n{str(e)}")
            logger.error(f"Excel导入失败: {e}")

    def _on_import_pdf(self):
        """导入 PDF 文献 — 打开 PDF 文件或文件夹，执行表格提取。"""
        if not self._project.has_project:
            QMessageBox.information(self, "提示", "请先新建或打开一个项目。")
            return

        # 让用户选择：单个PDF or 文件夹
        choice = QMessageBox.question(
            self, "导入 PDF",
            "请选择导入方式:\n\n"
            "• 点击「是」— 选择单个 PDF 文件\n"
            "• 点击「否」— 选择一个文件夹（递归扫描所有 PDF）\n"
            "• 点击「取消」— 放弃操作",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )

        pdf_paths = []
        if choice == QMessageBox.Yes:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择 PDF 文件", "", "PDF 文件 (*.pdf)"
            )
            if file_path:
                pdf_paths.append(file_path)
        elif choice == QMessageBox.No:
            folder = QFileDialog.getExistingDirectory(self, "选择包含 PDF 的文件夹")
            if folder:
                from pathlib import Path
                pdf_paths = [str(p) for p in Path(folder).rglob("*.pdf")]
        else:
            return

        if not pdf_paths:
            return

        # 创建并显示进度对话框
        progress = BatchProgressDialog(self, title=f"正在处理 {len(pdf_paths)} 个 PDF...")
        progress.setModal(True)

        from services.batch_service import BatchProcessingService
        service = BatchProcessingService()

        # 在线程中执行
        from services.task_runner import TaskRunner

        all_tables = []  # 捕获所有表格

        def batch_task(progress_callback=None, cancel_check=None):
            nonlocal all_tables
            total = len(pdf_paths)
            for i, pdf_path in enumerate(pdf_paths):
                if cancel_check and cancel_check():
                    break
                progress_callback(i, total, f"正在处理: {os.path.basename(pdf_path)}")
                result = service.process_single_pdf(
                    pdf_path,
                    progress_callback=None,
                    cancel_check=cancel_check,
                )
                if result.get("tables"):
                    all_tables.extend(result["tables"])
                    progress_callback(i + 1, total,
                        f"完成 {i + 1}/{total}: {os.path.basename(pdf_path)} → {len(result['tables'])} 个表格")
                else:
                    progress_callback(i + 1, total,
                        f"完成 {i + 1}/{total}: {os.path.basename(pdf_path)} → 0 个表格")
            return len(all_tables)

        def on_progress(current, total, message):
            progress.update_progress(current, total, message)

        def on_finished(count):
            progress.set_complete(f"处理完成: 共提取 {count} 个表格")
            self._tab_widget.setCurrentWidget(self._table_preview)
            if all_tables:
                self._table_preview.load_tables(all_tables)
                self._save_tables_to_db(all_tables)
                self.status_bar.showMessage(
                    f"PDF导入完成: {len(pdf_paths)} 个文件 → {count} 个表格", 8000
                )
            else:
                QMessageBox.information(self, "提示", "未在所选 PDF 中发现表格。")

        def on_error(err):
            progress.set_error(err)
            logger.error(f"PDF 批量处理失败: {err}")

        runner = TaskRunner(batch_task)
        runner.signals.progress.connect(on_progress)
        runner.signals.finished.connect(on_finished)
        runner.signals.error.connect(on_error)

        # 进度对话框取消时，取消任务
        progress.cancelled.connect(runner.cancel)

        runner.start()
        progress.exec()
        runner.wait()

    def _save_tables_to_db(self, tables):
        """将提取的表格保存到数据库的 extracted_tables 表。"""
        if not self._project.has_project or not tables:
            return

        import json
        repo = self._project.repo
        for table in tables:
            try:
                self._project.db.conn.execute(
                    """INSERT INTO extracted_tables
                       (page_number, table_index, extraction_method, confidence,
                        raw_json, is_image_based, status)
                       VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                    (
                        table.pdf_page,
                        table.table_index,
                        table.method,
                        table.confidence,
                        table.raw_json[:10000] if table.raw_json else "[]",
                        1 if table.is_image_based else 0,
                    ),
                )
            except Exception as e:
                logger.warning(f"保存表格到数据库失败: {e}")
        self._project.db.conn.commit()
        logger.info(f"{len(tables)} 个表格已保存到数据库")

    def _on_classify(self):
        """打开分类对话框。"""
        if not self._project.has_project:
            QMessageBox.information(self, "提示", "请先打开一个包含数据的项目。")
            return

        # 获取当前数据网格中的样本
        df = self._data_grid.get_dataframe()
        if len(df) == 0:
            QMessageBox.information(self, "提示", "没有数据可供分类。请先导入 Excel 数据。")
            return

        samples = df.to_dict(orient="records")

        from .dialogs.classification import ClassificationDialog
        dialog = ClassificationDialog(self, samples=samples)

        def on_applied(changes):
            """应用分类变更到数据库。"""
            if not changes:
                return

            # 更新数据网格中的花岗岩类型列
            for idx, new_type, confidence, subtype in changes:
                if idx < len(df):
                    # 找到 Granite type 列
                    type_col = None
                    for col_name in ["Granite type", "花岗岩类型", "Giranite type"]:
                        if col_name in df.columns:
                            type_col = col_name
                            break
                    if type_col:
                        df.at[idx, type_col] = new_type

            self._data_grid.load_dataframe(df)
            self._data_grid.refresh()

            # 更新数据库
            if self._project.has_project:
                try:
                    repo = self._project.repo
                    for idx, new_type, confidence, subtype in changes:
                        sample_no = str(df.iloc[idx]["Sample.No"]) if idx < len(df) else None
                        if sample_no:
                            self._project.db.conn.execute(
                                "UPDATE geochem_samples SET granite_type=?, auto_classification=? WHERE sample_no=?",
                                (new_type, new_type, sample_no),
                            )
                    self._project.db.conn.commit()
                except Exception as e:
                    logger.warning(f"数据库分类更新失败: {e}")

            self._update_ui_state()
            self.status_bar.showMessage(f"分类完成: {len(changes)} 项变更", 5000)

        dialog.classification_applied.connect(on_applied)
        dialog.exec()

    def _on_export_data(self):
        """打开导出对话框。"""
        if not self._project.has_project:
            QMessageBox.information(self, "提示", "请先打开一个包含数据的项目。")
            return

        df = self._data_grid.get_dataframe()
        if len(df) == 0:
            QMessageBox.information(self, "提示", "没有数据可供导出。请先导入 Excel 数据。")
            return

        samples = df.to_dict(orient="records")

        from .dialogs.export import ExportDialog
        dialog = ExportDialog(self, samples=samples, sample_count=len(samples))

        def on_exported(config):
            self.status_bar.showMessage(
                f"导出完成: {os.path.basename(config['output_path'])}", 5000
            )

        dialog.export_requested.connect(on_exported)
        dialog.exec()

    def _on_batch_reclassify(self):
        """批量重分类。"""
        self._on_classify()

    def _on_refresh(self):
        """刷新数据视图。"""
        if self._project.has_project:
            self._load_project_data()
            self.status_bar.showMessage("数据已刷新", 2000)

    def _on_about(self):
        """关于对话框。"""
        QMessageBox.about(
            self, "关于 GeoChemExtractor",
            """<h3>GeoChemExtractor v0.1.0</h3>
            <p>PDF地质文献表格提取与地球化学数据管理软件</p>
            <p>专为花岗岩岩石地球化学研究设计</p>
            <p style='color: #D97706;'><b>Claude 主题 · 学术风格</b></p>
            <p style='color: #A0A0B0;'>Windows 10/11 · Python 3.13</p>"""
        )

    # ── UI 信号回调 ────────────────────────────────

    def _on_row_selected(self, row: int):
        """数据网格行选中回调 — 更新速查面板。"""
        df = self._data_grid.get_dataframe()
        if 0 <= row < len(df):
            row_data = df.iloc[row].to_dict()
            # 翻译列名为模型字段名
            sample_data = {
                "sample_no": row_data.get("Sample.No"),
                "mining_area": row_data.get("矿区"),
                "rock_body": row_data.get("岩体"),
                "granite_type": row_data.get("Granite type"),
                "rock_type": row_data.get("Rock type"),
                "formation_age": row_data.get("成岩年龄"),
                "sio2": row_data.get("SiO2"),
                "asi": row_data.get("ASI"),
            }
            self._inspector.update_sample(sample_data)

    def _on_sample_count_changed(self, count: int):
        """样本数量变化回调。"""
        self._status_samples.setText(f"样本: {count} 行")

    def _on_filter_changed(self, filters: dict):
        """筛选条件变更 — 对数据网格应用筛选。"""
        if not self._project.has_project:
            return
        df = self._data_grid._model.get_dataframe()
        if len(df) == 0:
            return
        filtered = self._filter_panel.apply(df)
        self._data_grid.load_dataframe(filtered)

    def _on_filter_cleared(self):
        """筛选清空 — 恢复全部数据。"""
        self._load_project_data()

    def _on_chart_sample_selected(self, indices: list):
        """图表中选中样本 — 在数据网格中高亮对应行。"""
        if indices:
            self._data_grid.selectRow(indices[0])
            self._tab_widget.setCurrentWidget(self._data_grid)

    def _on_chart_refresh(self):
        """刷新图表数据。"""
        df = self._data_grid.get_dataframe()
        if len(df) > 0:
            samples_list = df.to_dict(orient="records")
            self._chart_canvas.load_samples(samples_list)

    # ── 内部方法 ────────────────────────────────────

    def _load_project_data(self):
        """从数据库加载数据到视图。"""
        if not self._project.has_project:
            return

        import pandas as pd
        from data.repository import SampleRepository
        from data.database import DatabaseManager

        repo = self._project.repo
        samples = repo.get_all_samples()

        if not samples:
            self._data_grid.load_dataframe(pd.DataFrame())
            self._update_navigator_counts()
            return

        # 构建 DataFrame，使用 94列格式
        rows = [s.to_flat_dict() for s in samples]
        df = pd.DataFrame(rows)

        # 调整列顺序为94列标准顺序
        from data_grid.model import COLUMN_LABELS
        ordered_cols = [c for c in COLUMN_LABELS if c in df.columns]
        remaining = [c for c in df.columns if c not in COLUMN_LABELS]
        df = df[ordered_cols + remaining]

        self._data_grid.load_dataframe(df)
        self._update_navigator_counts()

        # 更新筛选面板的可选项
        self._filter_panel.set_available_values(df)

        # 加载图表数据
        samples_list = df.to_dict(orient="records")
        self._chart_canvas.load_samples(samples_list)

    def _update_navigator_counts(self):
        """更新导航器中的计数信息。"""
        if not self._project.has_project:
            return

        summary = self._project.get_summary()
        self._navigator.update_counts(
            samples=summary["samples"],
            classified=summary["classified"],
            pdfs=summary["pdfs"],
        )

    def _check_for_updates(self):
        """启动后 3 秒静默检测更新。"""
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._do_update_check)
        self._update_timer.start(3000)

    def _do_update_check(self):
        """实际执行更新检测（在后台线程中）。"""
        from services.update_checker import UpdateChecker

        class UpdateThread(QThread):
            result_ready = Signal(object)

            def run(self):
                checker = UpdateChecker()
                self.result_ready.emit(checker.check())

        self._update_thread = UpdateThread()
        self._update_thread.result_ready.connect(self._on_update_result)
        self._update_thread.start()

    def _on_update_result(self, result):
        """处理更新检测结果。"""
        if result:
            from services.update_checker import UpdateChecker
            UpdateChecker.show_update_dialog(
                self, result["version"], result["url"]
            )

    def _update_ui_state(self):
        """根据当前项目状态更新 UI 元素。"""
        has_project = self._project.has_project
        is_modified = self._project.is_modified

        # 菜单/工具栏启用状态
        self._save_action.setEnabled(has_project)
        self._save_as_action.setEnabled(has_project)
        self._import_excel_action.setEnabled(has_project)

        # 状态栏
        if has_project:
            self._status_project.setText(f"项目: {self._project.project_name}")
            if is_modified:
                self._status_modified.setText("● 已修改")
            else:
                self._status_modified.setText("")
            self._update_navigator_counts()
        else:
            self._status_project.setText("无项目")
            self._status_modified.setText("")
            self._navigator.update_counts(0, 0, 0, 0, 0)

    def closeEvent(self, event):
        """窗口关闭事件 — 询问保存。"""
        if self._project.is_modified:
            reply = QMessageBox.question(
                self, "保存更改",
                "当前项目有未保存的更改，是否保存后退出？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                try:
                    self._project.save_project()
                except Exception as e:
                    QMessageBox.critical(self, "保存失败", str(e))
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return

        self._project.close_project()
        event.accept()
