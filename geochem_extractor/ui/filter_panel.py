"""动态筛选面板 — 多条件组合筛选控件。

支持:
- 文本筛选: 矿区(含)、岩体(含)、样品号
- 分类筛选: 花岗岩类型下拉
- 范围筛选: SiO2 范围、Age 范围
- 快速筛选: 已分类/未分类
"""

from typing import Optional, Callable, Dict, Any, List
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QPushButton, QLabel, QCheckBox, QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal

from .theme import Colors


class FilterPanel(QWidget):
    """动态筛选面板 — 多条件组合筛选。"""

    filter_changed = Signal(dict)   # 发送筛选条件
    filter_cleared = Signal()       # 清空筛选

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = {}
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 可滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)

        # ── 矿区筛选 ──
        layout.addWidget(self._make_section_label("矿区"))
        self._area_combo = QComboBox()
        self._area_combo.setEditable(True)
        self._area_combo.setPlaceholderText("全部矿区 — 输入筛选...")
        self._area_combo.currentTextChanged.connect(self._emit_filter)
        layout.addWidget(self._area_combo)

        # ── 岩体筛选 ──
        layout.addWidget(self._make_section_label("岩体"))
        self._rock_body_input = QLineEdit()
        self._rock_body_input.setPlaceholderText("输入岩体名称（支持模糊匹配）")
        self._rock_body_input.textChanged.connect(self._emit_filter)
        layout.addWidget(self._rock_body_input)

        # ── 花岗岩类型 ──
        layout.addWidget(self._make_section_label("花岗岩类型"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(["全部", "I-type", "S-type", "A-type", "M-type", "未分类"])
        self._type_combo.currentTextChanged.connect(self._emit_filter)
        layout.addWidget(self._type_combo)

        # ── SiO2 范围 ──
        layout.addWidget(self._make_section_label("SiO₂ 范围 (wt%)"))
        sio2_layout = QHBoxLayout()
        self._sio2_min = QDoubleSpinBox()
        self._sio2_min.setRange(30, 85)
        self._sio2_min.setValue(30)
        self._sio2_min.setSuffix("%")
        self._sio2_min.valueChanged.connect(self._emit_filter)
        sio2_layout.addWidget(self._sio2_min)

        sio2_layout.addWidget(QLabel("—"))

        self._sio2_max = QDoubleSpinBox()
        self._sio2_max.setRange(30, 85)
        self._sio2_max.setValue(85)
        self._sio2_max.setSuffix("%")
        self._sio2_max.valueChanged.connect(self._emit_filter)
        sio2_layout.addWidget(self._sio2_max)
        layout.addLayout(sio2_layout)

        # ── 成岩年龄范围 ──
        layout.addWidget(self._make_section_label("成岩年龄 (Ma)"))
        age_layout = QHBoxLayout()
        self._age_min = QDoubleSpinBox()
        self._age_min.setRange(0, 4000)
        self._age_min.setValue(0)
        self._age_min.setSuffix(" Ma")
        self._age_min.valueChanged.connect(self._emit_filter)
        age_layout.addWidget(self._age_min)

        age_layout.addWidget(QLabel("—"))

        self._age_max = QDoubleSpinBox()
        self._age_max.setRange(0, 4000)
        self._age_max.setValue(4000)
        self._age_max.setSuffix(" Ma")
        self._age_max.valueChanged.connect(self._emit_filter)
        age_layout.addWidget(self._age_max)
        layout.addLayout(age_layout)

        # ── 样品号 ──
        layout.addWidget(self._make_section_label("样品号"))
        self._sample_input = QLineEdit()
        self._sample_input.setPlaceholderText("输入样品号（支持模糊匹配）")
        self._sample_input.textChanged.connect(self._emit_filter)
        layout.addWidget(self._sample_input)

        # ── 快速筛选 ──
        layout.addWidget(self._make_section_label("快速筛选"))
        self._only_classified = QCheckBox("仅显示已分类样本")
        self._only_classified.toggled.connect(self._emit_filter)
        layout.addWidget(self._only_classified)

        self._only_valid = QCheckBox("仅显示验证通过的样本")
        self._only_valid.toggled.connect(self._emit_filter)
        layout.addWidget(self._only_valid)

        # ── 结果计数 ──
        self._result_label = QLabel("匹配: — 条")
        self._result_label.setStyleSheet(f"color: {Colors.TEXT_ACCENT}; font-size: 9pt; font-weight: bold;")
        layout.addWidget(self._result_label)

        # ── 按钮 ──
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清除筛选")
        clear_btn.setProperty("secondary", True)
        clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _make_section_label(self, text: str) -> QLabel:
        """创建分组标题。"""
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 8pt; "
            f"font-weight: bold; padding-top: 4px;"
        )
        return label

    def _emit_filter(self, *_):
        """发送筛选条件变更信号。"""
        self.filter_changed.emit(self.get_filters())

    def _on_clear(self):
        """清除所有筛选条件。"""
        self._area_combo.setCurrentText("")
        self._rock_body_input.clear()
        self._type_combo.setCurrentIndex(0)
        self._sio2_min.setValue(30)
        self._sio2_max.setValue(85)
        self._age_min.setValue(0)
        self._age_max.setValue(4000)
        self._sample_input.clear()
        self._only_classified.setChecked(False)
        self._only_valid.setChecked(False)
        self.filter_cleared.emit()

    def get_filters(self) -> dict:
        """获取当前筛选条件。"""
        filters = {}

        if self._area_combo.currentText():
            filters["mining_area"] = self._area_combo.currentText()

        if self._rock_body_input.text():
            filters["rock_body"] = self._rock_body_input.text()

        if self._type_combo.currentIndex() > 0:
            filters["granite_type"] = self._type_combo.currentText()

        if self._sio2_min.value() > 30 or self._sio2_max.value() < 85:
            filters["sio2_min"] = self._sio2_min.value()
            filters["sio2_max"] = self._sio2_max.value()

        if self._age_min.value() > 0 or self._age_max.value() < 4000:
            filters["age_min"] = self._age_min.value()
            filters["age_max"] = self._age_max.value()

        if self._sample_input.text():
            filters["sample_no"] = self._sample_input.text()

        if self._only_classified.isChecked():
            filters["only_classified"] = True

        if self._only_valid.isChecked():
            filters["only_valid"] = True

        return filters

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """对 DataFrame 应用筛选条件，返回筛选后的 DataFrame。"""
        result = df.copy()
        filters = self.get_filters()

        # 矿区筛选
        if "mining_area" in filters:
            keyword = filters["mining_area"]
            if "矿区" in result.columns:
                result = result[result["矿区"].astype(str).str.contains(keyword, na=False)]

        # 岩体筛选
        if "rock_body" in filters:
            keyword = filters["rock_body"]
            if "岩体" in result.columns:
                result = result[result["岩体"].astype(str).str.contains(keyword, na=False)]

        # 类型筛选
        if "granite_type" in filters:
            type_val = filters["granite_type"]
            type_col = None
            for col in ["Granite type", "花岗岩类型", "Giranite type"]:
                if col in result.columns:
                    type_col = col
                    break
            if type_col:
                if type_val == "未分类":
                    result = result[
                        (result[type_col].isna()) |
                        (result[type_col].astype(str).str.strip() == "") |
                        (result[type_col].astype(str).str.strip() == "—")
                    ]
                else:
                    result = result[
                        result[type_col].astype(str).str.upper().str.contains(
                            type_val.replace("-type", "").strip(), na=False
                        )
                    ]

        # SiO2范围
        if "sio2_min" in filters and "SiO2" in result.columns:
            result = result[
                (result["SiO2"].fillna(0) >= filters["sio2_min"]) &
                (result["SiO2"].fillna(0) <= filters["sio2_max"])
            ]

        # 年龄范围
        if "age_min" in filters and "成岩年龄" in result.columns:
            result = result[
                (result["成岩年龄"].fillna(0) >= filters["age_min"]) &
                (result["成岩年龄"].fillna(0) <= filters["age_max"])
            ]

        # 样品号筛选
        if "sample_no" in filters:
            keyword = filters["sample_no"]
            if "Sample.No" in result.columns:
                result = result[
                    result["Sample.No"].astype(str).str.contains(keyword, na=False)
                ]

        # 仅已分类
        if filters.get("only_classified"):
            type_col = None
            for col in ["Granite type", "花岗岩类型"]:
                if col in result.columns:
                    type_col = col
                    break
            if type_col:
                result = result[
                    result[type_col].notna() &
                    (result[type_col].astype(str).str.strip() != "") &
                    (result[type_col].astype(str).str.strip() != "—")
                ]

        # 更新计数
        count = len(result)
        self._result_label.setText(f"匹配: {count} 条")
        return result

    def set_available_values(self, df: pd.DataFrame):
        """从 DataFrame 填充下拉框的可选项。"""
        if "矿区" in df.columns:
            areas = df["矿区"].dropna().unique()
            current = self._area_combo.currentText()
            self._area_combo.blockSignals(True)
            self._area_combo.clear()
            self._area_combo.addItem("")
            for a in sorted(areas):
                if str(a).strip():
                    self._area_combo.addItem(str(a).strip())
            self._area_combo.blockSignals(False)
