"""数据网格视图 — QTableView 子类。

配置表头、选择行为、列宽等；集成 GeochemTableModel。
"""

from typing import Optional
import pandas as pd
from PySide6.QtWidgets import QTableView, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .model import GeochemTableModel
from ..theme import Colors


class GeochemTableView(QTableView):
    """地球化学数据表格视图。

    提供样式化的数据展示，支持排序、选择、分类着色。
    """

    row_selected = Signal(int)  # 发送选中行索引
    sample_count_changed = Signal(int)  # 发送样本总数

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = GeochemTableModel(self)
        self.setModel(self._model)
        self._setup_ui()

    def _setup_ui(self):
        """配置表格外观和行为。"""
        # 选择行为
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)

        # 表头配置
        h_header = self.horizontalHeader()
        h_header.setSectionsMovable(True)
        h_header.setStretchLastSection(False)
        h_header.setDefaultSectionSize(80)
        h_header.setMinimumSectionSize(50)

        v_header = self.verticalHeader()
        v_header.setDefaultSectionSize(28)
        v_header.setVisible(True)
        v_header.setMinimumWidth(40)

        # 列宽预设（关键列稍宽）
        h_header.resizeSection(0, 80)   # 矿区
        h_header.resizeSection(1, 120)  # 岩体
        h_header.resizeSection(2, 100)  # Data source
        h_header.resizeSection(3, 80)   # Sample.No
        h_header.resizeSection(4, 80)   # Granite type
        h_header.resizeSection(5, 100)  # Rock type

        # 编辑
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.EditKeyPressed
        )

        # 滚动
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # 连接选择信号
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self, selected, deselected):
        """行选择变化时发送信号。"""
        indexes = self.selectionModel().selectedRows()
        if indexes:
            self.row_selected.emit(indexes[0].row())

    # ── 公共 API ──────────────────────────────────────

    def load_dataframe(self, df: pd.DataFrame):
        """加载 DataFrame 到表格。"""
        self._model.set_dataframe(df)
        self.sample_count_changed.emit(len(df))

    def get_dataframe(self) -> pd.DataFrame:
        """获取当前表格数据。"""
        return self._model.get_dataframe()

    def get_row_count(self) -> int:
        return self._model.get_row_count()

    def get_selected_row(self) -> int:
        """获取当前选中行索引（-1 表示未选中）。"""
        indexes = self.selectionModel().selectedRows()
        return indexes[0].row() if indexes else -1

    def get_selected_rows(self) -> list:
        """获取所有选中行索引。"""
        return [idx.row() for idx in self.selectionModel().selectedRows()]

    def set_sample_value(self, row: int, col: int, value):
        """设置单元格值。"""
        model_index = self._model.index(row, col)
        self._model.setData(model_index, value, Qt.EditRole)

    def refresh(self):
        """刷新视图。"""
        self._model.layoutChanged.emit()
