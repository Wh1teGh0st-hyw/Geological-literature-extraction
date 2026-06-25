"""表格预览面板 — 在原主窗口的 PDF 导入后展示提取结果。

嵌入到主窗口的"表格预览"标签页中。
"""

from typing import List, Optional
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QLabel, QComboBox, QPushButton, QHeaderView,
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from ..theme import Colors
from engine.table_extraction import ExtractedTable


class TablePreviewModel(QAbstractTableModel):
    """用于预览提取表格的简单表格模型。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame()
        self._headers = []

    def set_table(self, table: ExtractedTable):
        """加载提取的表格数据。"""
        self.beginResetModel()
        if table.dataframe is not None:
            self._df = table.dataframe
            self._headers = list(self._df.columns)
        else:
            self._df = pd.DataFrame()
            self._headers = []
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._df = pd.DataFrame()
        self._headers = []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            val = self._df.iloc[index.row(), index.column()]
            if pd.isna(val):
                return "—"
            return str(val)
        if role == Qt.ForegroundRole:
            # 表头行（前几行可能是表头）用浅色
            if index.row() < 2:
                return QColor(Colors.TEXT_ACCENT)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._headers[section]) if section < len(self._headers) else str(section)
            if orientation == Qt.Vertical:
                return str(section + 1)
        return None


class TablePreviewPanel(QWidget):
    """表格预览面板 — 在标签页中展示提取的表格。

    功能:
    - 下拉选择提取的表格
    - 表格预览 (QTableView)
    - 基本信息展示 (来源 PDF、页码、行数/列数、提取方法、置信度)
    """

    table_approved = Signal(ExtractedTable)   # 用户确认保留此表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tables: List[ExtractedTable] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 顶部控制栏
        control_layout = QHBoxLayout()

        label = QLabel("选择表格:")
        label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        control_layout.addWidget(label)

        self._table_selector = QComboBox()
        self._table_selector.setMinimumWidth(300)
        self._table_selector.currentIndexChanged.connect(self._on_table_selected)
        control_layout.addWidget(self._table_selector)

        control_layout.addStretch()

        # 信息标签
        self._info_label = QLabel("")
        self._info_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 9pt;")
        control_layout.addWidget(self._info_label)

        layout.addLayout(control_layout)

        # 表格视图
        self._table_model = TablePreviewModel()
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.horizontalHeader().setStretchLastSection(False)
        self._table_view.setAlternatingRowColors(True)
        layout.addWidget(self._table_view, 1)

        # 底部提示
        hint = QLabel("提示: 此面板展示原始提取的表格，尚未进行地球化学列解析。数据将在第3步处理。")
        hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 8pt; padding: 4px;")
        hint.setAlignment(Qt.AlignLeft)
        layout.addWidget(hint)

    def load_tables(self, tables: List[ExtractedTable]):
        """加载提取的表格列表。"""
        self._tables = tables
        self._table_selector.clear()
        if not tables:
            self._table_selector.addItem("(无表格)")
            self._table_model.clear()
            self._info_label.setText("")
            return

        for i, t in enumerate(tables):
            label = f"表格 {i + 1}: 第{t.pdf_page + 1}页 [{t.method}] ({t.rows}行×{t.cols}列)"
            self._table_selector.addItem(label, userData=i)

        self._table_selector.setCurrentIndex(0)
        self._on_table_selected(0)

    def _on_table_selected(self, index: int):
        """切换选中表格。"""
        if index < 0 or index >= len(self._tables):
            self._table_model.clear()
            self._info_label.setText("")
            return

        table = self._tables[index]
        self._table_model.set_table(table)

        # 更新信息
        source = table.pdf_path.split("/")[-1].split("\\")[-1][:40]
        info = (
            f"来源: {source} | "
            f"第{table.pdf_page + 1}页 | "
            f"方法: {table.method} | "
            f"置信度: {table.confidence:.0%} | "
            f"{table.rows}行 × {table.cols}列"
        )
        self._info_label.setText(info)

    def get_current_table(self) -> Optional[ExtractedTable]:
        """获取当前选中的表格。"""
        idx = self._table_selector.currentIndex()
        if 0 <= idx < len(self._tables):
            return self._tables[idx]
        return None

    def clear(self):
        """清空预览。"""
        self._tables = []
        self._table_selector.clear()
        self._table_model.clear()
        self._info_label.setText("")
