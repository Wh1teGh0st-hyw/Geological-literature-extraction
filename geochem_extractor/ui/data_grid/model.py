"""数据网格模型 — QAbstractTableModel 包装 pandas DataFrame。

为94列地球化学数据提供高性能表格模型，支持：
- 行列数据的快速读写
- 表头（94列中英文标签）
- 数据类型感知（数值右对齐 / 文本左对齐）
"""

from typing import Optional, Any, List
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex


# ── 94列显示名称（中文） ────────────────────────────

COLUMN_LABELS = [
    "矿区", "岩体", "Data source", "Sample.No", "Granite type", "Rock type",
    "成岩年龄", "error", "Method", "成矿年龄", "error", "Method",
    "X", "Y", "Hight",
    "SiO2", "TiO2", "Al2O3", "Fe2O3", "FeO", "MnO", "MgO", "CaO", "Na2O", "K2O", "P2O5", "L.O.I", "Total",
    "Li", "Be", "Sc", "V", "Cr", "Co", "Ni", "Cu", "Zn", "Ga",
    "Rb", "Sr", "Y", "Zr", "Nb", "Cs", "Ba", "Hf", "Ta", "Pb", "Th", "U", "W", "Sn", "Mo",
    "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "87Sr/86Sr(i)", "87Sr/86Sr_err",
    "143Nd/144Nd(i)", "143Nd/144Nd_err", "εNd(t)", "εNd_err", "TDM2(Nd)", "TDM1(Nd)",
    "176Hf/177Hf(i)", "176Hf/177Hf_err", "εHf(t)", "εHf_err", "TDM2(Hf)", "TDM1(Hf)",
    "ASI", "Ga/Al×10⁴", "FeOt/(FeOt+MgO)", "TZr(°C)",
]


class GeochemTableModel(QAbstractTableModel):
    """地球化学数据表格模型。

    底层使用 pandas DataFrame，通过 Qt Model/View 框架展示。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame()  # 空 DataFrame
        self._column_labels = COLUMN_LABELS.copy()
        self._editable = True

    # ── 核心 QAbstractTableModel 方法 ──────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._df)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._column_labels)

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()

        if role == Qt.DisplayRole:
            value = self._df.iloc[row, col]
            if pd.isna(value) or value is None:
                return "—"
            if isinstance(value, float):
                # 小数值显示更多小数位（同位素）
                if abs(value) < 1 and value != 0:
                    return f"{value:.5f}"
                return f"{value:.2f}"
            return str(value)

        if role == Qt.TextAlignmentRole:
            if col >= 6:  # 数值列右对齐
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.ForegroundRole:
            # 未分类样本使用灰色字体标记
            if col == 4:  # Granite type 列
                value = self._df.iloc[row, col]
                if pd.isna(value) or str(value).strip() == "":
                    from .theme import Colors
                    return Colors.TEXT_MUTED

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section < len(self._column_labels):
                    return self._column_labels[section]
                return str(section + 1)
            if orientation == Qt.Vertical:
                return str(section + 1)
        return None

    def setData(self, index: QModelIndex, value: Any, role=Qt.EditRole) -> bool:
        if not self._editable:
            return False
        if index.isValid() and role == Qt.EditRole:
            self._df.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        if self._editable:
            flags |= Qt.ItemIsEditable
        return flags

    # ── DataFrame 操作 ────────────────────────────────

    def set_dataframe(self, df: pd.DataFrame):
        """替换整个 DataFrame。"""
        self.beginResetModel()
        self._df = df.copy() if df is not None else pd.DataFrame()
        self._ensure_column_count()
        self.endResetModel()

    def get_dataframe(self) -> pd.DataFrame:
        """获取当前 DataFrame 副本。"""
        return self._df.copy()

    def get_sample_value(self, row: int, col: int) -> Any:
        """获取指定单元格的原始值。"""
        if 0 <= row < len(self._df) and 0 <= col < len(self._df.columns):
            return self._df.iloc[row, col]
        return None

    def get_row_count(self) -> int:
        return len(self._df)

    def _ensure_column_count(self):
        """确保 DataFrame 列数与表头标签一致。"""
        target = len(self._column_labels)
        current = len(self._df.columns)
        if current < target:
            for i in range(current, target):
                col_name = self._column_labels[i] if i < len(self._column_labels) else f"Col_{i}"
                self._df[col_name] = None
