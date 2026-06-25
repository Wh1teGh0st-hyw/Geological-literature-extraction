"""样本速查面板 — 选中行时快速预览关键信息。"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt

from .theme import Colors


class SampleInspector(QWidget):
    """样本信息速查面板，显示于左侧栏底部。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题
        title = QLabel("样本速查")
        title.setProperty("heading", True)
        title.setStyleSheet(f"color: {Colors.TEXT_ACCENT}; font-size: 10pt; font-weight: bold;")
        layout.addWidget(title)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Colors.GRID_BORDER}; max-height: 1px;")
        layout.addWidget(line)

        # 表单布局
        self._form = QFormLayout()
        self._form.setSpacing(4)

        fields = [
            ("样品号", "sample_no"),
            ("矿区", "mining_area"),
            ("岩体", "rock_body"),
            ("花岗岩类型", "granite_type"),
            ("岩石类型", "rock_type"),
            ("成岩年龄 (Ma)", "formation_age"),
            ("SiO2 (%)", "sio2"),
            ("ASI", "asi"),
        ]

        self._labels = {}
        for label_text, key in fields:
            value_label = QLabel("—")
            value_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 9pt;")
            value_label.setWordWrap(True)
            self._labels[key] = value_label

            name_label = QLabel(label_text)
            name_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 8pt;")
            self._form.addRow(name_label, value_label)

        layout.addLayout(self._form)
        layout.addStretch()

    def update_sample(self, sample_data: dict):
        """更新显示的样本信息。

        Args:
            sample_data: 包含样本字段的字典
        """
        for key, label in self._labels.items():
            value = sample_data.get(key)
            if value is not None and value != "":
                if isinstance(value, float):
                    label.setText(f"{value:.2f}")
                else:
                    label.setText(str(value))
            else:
                label.setText("—")

    def clear(self):
        """清空显示。"""
        for label in self._labels.values():
            label.setText("—")
