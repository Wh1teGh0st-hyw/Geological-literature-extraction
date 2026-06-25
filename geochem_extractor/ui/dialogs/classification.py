"""分类对话框 — 展示自动分类结果，支持置信度查看、手动覆盖和批量重分类。"""

from typing import List, Dict, Optional, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLabel, QComboBox, QHeaderView, QMessageBox, QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QColor

from ..theme import Colors
from engine.classification import ClassificationEngine, ClassificationResult


# 分类结果表头
CLASS_COLUMNS = [
    "Sample.No", "Granite type (当前)", "自动分类结果", "置信度",
    "亚型", "ASI", "Ga/Al×10⁴", "FeMgI", "TZr(°C)",
]


class ClassificationTableModel(QAbstractTableModel):
    """分类结果表格模型。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples: List[Dict[str, Any]] = []
        self._results: List[ClassificationResult] = []
        self._headers = CLASS_COLUMNS

    def set_data(self, samples: List[Dict], results: List[ClassificationResult]):
        self.beginResetModel()
        self._samples = samples
        self._results = results
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._results)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        sample = self._samples[row]
        result = self._results[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return sample.get("Granite type", "")
            if col == 1:
                return sample.get("Granite type", "") or "未分类"
            if col == 2:
                return result.granite_type
            if col == 3:
                return result.confidence
            if col == 4:
                return result.subtype or "—"
            if col == 5:
                return f"{result.asi:.2f}" if result.asi else "—"
            if col == 6:
                return f"{result.ga_al_ratio:.2f}" if result.ga_al_ratio else "—"
            if col == 7:
                return f"{result.femgi:.2f}" if result.femgi else "—"
            if col == 8:
                return f"{result.t_zr:.0f}" if result.t_zr else "—"

        if role == Qt.BackgroundRole:
            gtype = (result.granite_type or "").strip()
            if "A-" in gtype:
                return QColor(Colors.ATYPE + "20")
            elif "S-" in gtype:
                return QColor(Colors.STYPE + "20")
            elif "M-" in gtype:
                return QColor(Colors.MTYPE + "20")
            elif "I-" in gtype:
                return QColor(Colors.ITYPE + "20")

        if role == Qt.ForegroundRole:
            if col == 3:  # confidence column
                conf = result.confidence
                if conf == "high":
                    return QColor(Colors.STATUS_SUCCESS)
                elif conf == "low":
                    return QColor(Colors.STATUS_ERROR)
                elif conf == "medium":
                    return QColor(Colors.STATUS_WARNING)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._headers[section]
            if orientation == Qt.Vertical:
                return str(section + 1)
        return None

    def get_sample_at(self, row: int) -> Optional[Dict]:
        if 0 <= row < len(self._samples):
            return self._samples[row]
        return None

    def get_result_at(self, row: int) -> Optional[ClassificationResult]:
        if 0 <= row < len(self._results):
            return self._results[row]
        return None


class ClassificationDialog(QDialog):
    """花岗岩类型分类对话框。

    功能：
    - 展示自动分类结果表格
    - 置信度颜色标记
    - 手动覆盖（下拉选择 + 自定义输入）
    - 批量重分类
    - 应用结果到数据库
    """

    # 信号：用户确认后的分类变更 (sample_index -> new_type)
    classification_applied = Signal(list)

    def __init__(self, parent=None, samples: List[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("花岗岩类型自动分类")
        self.setMinimumSize(800, 550)
        self._samples = samples or []
        self._results: List[ClassificationResult] = []
        self._manual_overrides: Dict[int, str] = {}
        self._setup_ui()

        if self._samples:
            self._run_classification()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 12)

        # 标题 + 统计
        header_layout = QHBoxLayout()
        self._title_label = QLabel("花岗岩类型自动分类")
        self._title_label.setStyleSheet(f"color: {Colors.TEXT_ACCENT}; font-size: 12pt; font-weight: bold;")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        header_layout.addWidget(self._stats_label)
        layout.addLayout(header_layout)

        # 分类结果表格
        self._table_model = ClassificationTableModel()
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSelectionBehavior(QTableView.SelectRows)
        self._table_view.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table_view, 1)

        # 操作区
        action_group = QGroupBox("手动操作")
        action_layout = QHBoxLayout(action_group)

        action_layout.addWidget(QLabel("修改为:"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(["", "I-type", "S-type", "A-type", "M-type", "未分类", "其他(手动输入)"])
        self._type_combo.currentTextChanged.connect(self._on_manual_type_changed)
        action_layout.addWidget(self._type_combo)

        self._manual_input = QComboBox()
        self._manual_input.setEditable(True)
        self._manual_input.setEnabled(False)
        self._manual_input.addItems(["A1", "A2", "SG", "SC", "HFI", "高分异I型", "埃达克质"])
        self._manual_input.setMinimumWidth(120)
        action_layout.addWidget(self._manual_input)

        apply_btn = QPushButton("应用覆盖")
        apply_btn.clicked.connect(self._apply_manual_override)
        action_layout.addWidget(apply_btn)

        action_layout.addStretch()
        layout.addWidget(action_group)

        # 底部按钮
        btn_layout = QHBoxLayout()

        # 批量操作
        batch_btn = QPushButton("批量重分类")
        batch_btn.setProperty("secondary", True)
        batch_btn.clicked.connect(self._on_batch_reclassify)
        btn_layout.addWidget(batch_btn)

        btn_layout.addStretch()

        # 确认 / 取消
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        accept_btn = QPushButton("确认并应用分类")
        accept_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(accept_btn)

        layout.addLayout(btn_layout)

    def _run_classification(self):
        """对当前样本列表运行自动分类。"""
        engine = ClassificationEngine()
        results = []

        for sample_dict in self._samples:
            result = engine.classify(
                sio2=sample_dict.get("SiO2"),
                al2o3=sample_dict.get("Al2O3"),
                fe2o3=sample_dict.get("Fe2O3"),
                feo=sample_dict.get("FeO"),
                mgo=sample_dict.get("MgO"),
                cao=sample_dict.get("CaO"),
                na2o=sample_dict.get("Na2O"),
                k2o=sample_dict.get("K2O"),
                p2o5=sample_dict.get("P2O5"),
                ga_ppm=sample_dict.get("Ga"),
                zr_ppm=sample_dict.get("Zr"),
                nb_ppm=sample_dict.get("Nb"),
                y_ppm=sample_dict.get("Y"),
            )
            results.append(result)

        self._results = results
        self._table_model.set_data(self._samples, results)

        # 统计
        types = {}
        for r in results:
            t = r.granite_type
            types[t] = types.get(t, 0) + 1
        stats = " ｜ ".join(f"{k}: {v}" for k, v in sorted(types.items()))
        self._stats_label.setText(f"共 {len(results)} 个样本 ｜ {stats}")

    def _on_manual_type_changed(self, text: str):
        """手动类型下拉变化。"""
        if text == "其他(手动输入)":
            self._manual_input.setEnabled(True)
            self._manual_input.setEditable(True)
        else:
            self._manual_input.setEnabled(False)

    def _apply_manual_override(self):
        """应用手动覆盖到选中行。"""
        indexes = self._table_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "提示", "请先选择要修改的行")
            return

        manual_type = self._type_combo.currentText()
        if manual_type == "其他(手动输入)":
            manual_type = self._manual_input.currentText().strip()
        if not manual_type:
            return

        for idx in indexes:
            row = idx.row()
            self._manual_overrides[row] = manual_type
            # 更新内存中的分类结果
            self._results[row].granite_type = manual_type
            self._results[row].confidence = "manual"
            self._results[row].subtype = ""
            self._results[row].basis = [f"手动覆盖: {manual_type}"]

        self._table_model.layoutChanged.emit()

    def _on_batch_reclassify(self):
        """批量重分类全部样本。"""
        reply = QMessageBox.question(
            self, "确认", "确定要对全部样本重新执行自动分类？\n这将覆盖所有手动修改。",
        )
        if reply == QMessageBox.Yes:
            self._manual_overrides.clear()
            self._run_classification()

    def _on_accept(self):
        """确认并应用分类结果。"""
        # 构建 (sample_index, new_type) 列表
        changes = []
        for i, result in enumerate(self._results):
            sample = self._samples[i]
            old_type = sample.get("Granite type", "")
            new_type = result.granite_type
            if old_type != new_type:
                changes.append((i, new_type, result.confidence, result.subtype))

        self.classification_applied.emit(changes)
        self.accept()

    def get_results(self) -> List[ClassificationResult]:
        return self._results
