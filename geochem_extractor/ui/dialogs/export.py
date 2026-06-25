"""导出对话框 — 列/Sheet/格式选择 + 主窗口集成。"""

import os
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QCheckBox, QComboBox, QGroupBox, QFileDialog, QMessageBox,
    QProgressBar, QRadioButton, QButtonGroup,
)
from PySide6.QtCore import Qt, Signal
from ..theme import Colors
from engine.export import ExportEngine


class ExportDialog(QDialog):
    """数据导出对话框。

    选项：
    - 导出格式：Excel (.xlsx) / CSV (.csv)
    - 分组方式：按花岗岩类型 / 按矿区 / 不分组
    - 包含列：全94列 / 仅主量+微量 / 自定义列
    - 包含计算指数
    - 输出路径
    """

    export_requested = Signal(dict)  # 发送导出配置

    def __init__(self, parent=None, samples: List[Dict] = None, sample_count: int = 0):
        super().__init__(parent)
        self.setWindowTitle("导出数据")
        self.setMinimumSize(500, 400)
        self._samples = samples or []
        self._count = sample_count or len(self._samples)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 12)

        # 标题
        title = QLabel(f"导出 {self._count} 条样本数据")
        title.setStyleSheet(f"color: {Colors.TEXT_ACCENT}; font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)

        # 格式选择
        fmt_group = QGroupBox("导出格式")
        fmt_layout = QHBoxLayout(fmt_group)

        self._xlsx_radio = QRadioButton("Excel (.xlsx) — 推荐")
        self._xlsx_radio.setChecked(True)
        self._csv_radio = QRadioButton("CSV (.csv) — 兼容其他软件")

        fmt_layout.addWidget(self._xlsx_radio)
        fmt_layout.addWidget(self._csv_radio)
        fmt_layout.addStretch()
        layout.addWidget(fmt_group)

        # 分组方式
        group_box = QGroupBox("分组方式（仅 Excel）")
        group_layout = QHBoxLayout(group_box)

        self._group_combo = QComboBox()
        self._group_combo.addItems(["不分组", "按花岗岩类型", "按矿区"])
        group_layout.addWidget(QLabel("按字段分组到不同 Sheet："))
        group_layout.addWidget(self._group_combo)
        group_layout.addStretch()
        layout.addWidget(group_box)

        # 列选择
        col_group = QGroupBox("包含内容")
        col_layout = QVBoxLayout(col_group)

        self._all_cols = QRadioButton("全94列标准模板")
        self._all_cols.setChecked(True)
        col_layout.addWidget(self._all_cols)

        self._basic_cols = QRadioButton("仅主量 + 微量 + REE（不含同位素）")
        col_layout.addWidget(self._basic_cols)

        self._include_indices = QCheckBox("包含计算指数列 (ASI/FeMgI/Ga/Al×10⁴/TZr)")
        self._include_indices.setChecked(True)
        col_layout.addWidget(self._include_indices)

        self._include_diagram = QCheckBox("同时导出图解数据 (TAS/REE/判别图)")
        self._include_diagram.setChecked(True)
        col_layout.addWidget(self._include_diagram)

        layout.addWidget(col_group)

        # 路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("输出路径:"))
        self._path_label = QLabel("(点击选择)")
        self._path_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 9pt;")
        self._path_label.setWordWrap(True)
        path_layout.addWidget(self._path_label, 1)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._on_browse)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        export_btn = QPushButton("开始导出")
        export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(export_btn)

        layout.addLayout(btn_layout)

        # 输出路径初始化
        self._output_path = ""

    def _on_browse(self):
        """选择输出路径。"""
        if self._xlsx_radio.isChecked():
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出 Excel", "geochem_export.xlsx",
                "Excel文件 (*.xlsx)"
            )
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出 CSV", "geochem_export.csv",
                "CSV文件 (*.csv)"
            )
        if file_path:
            self._output_path = file_path
            self._path_label.setText(file_path)

    def _on_export(self):
        """执行导出。"""
        if not self._output_path:
            self._output_path = "geochem_export.xlsx" if self._xlsx_radio.isChecked() else "geochem_export.csv"

        config = {
            "format": "xlsx" if self._xlsx_radio.isChecked() else "csv",
            "output_path": self._output_path,
            "group_by": None,
            "include_indices": self._include_indices.isChecked(),
            "include_diagram": self._include_diagram.isChecked(),
            "column_mode": "all" if self._all_cols.isChecked() else "basic",
        }

        if self._group_combo.currentIndex() == 1:
            config["group_by"] = "Granite type"
        elif self._group_combo.currentIndex() == 2:
            config["group_by"] = "矿区"

        # 执行导出
        try:
            exporter = ExportEngine()
            samples = self._samples

            if not samples:
                QMessageBox.warning(self, "无数据", "没有可导出的数据。")
                return

            output_dir = os.path.dirname(self._output_path) or "."

            if config["format"] == "xlsx":
                exporter.export_excel(
                    samples, config["output_path"],
                    group_by=config["group_by"],
                    include_indices=config["include_indices"],
                )
            else:
                exporter.export_csv(
                    samples, config["output_path"],
                    include_indices=config["include_indices"],
                )

            # 图解数据
            if config["include_diagram"]:
                exporter.export_diagram_data(samples, output_dir)

            QMessageBox.information(
                self, "导出完成",
                f"数据已成功导出:\n{config['output_path']}\n\n"
                f"共 {len(samples)} 条样本",
            )

            self.export_requested.emit(config)
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self, "导出失败",
                f"导出过程中出错:\n{str(e)}",
            )
