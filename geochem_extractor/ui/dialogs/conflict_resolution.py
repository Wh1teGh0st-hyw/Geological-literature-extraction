"""合并冲突解决对话框 — 可视化新旧数据差异。

当从不同PDF源导入的样本与已有数据库中的样本发生重叠时，
提供逐字段差异对比和用户决策界面。
"""

from typing import Dict, List, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QRadioButton, QGroupBox,
    QButtonGroup, QMessageBox, QHeaderView,
)
from PySide6.QtCore import Qt
from ..theme import Colors


class MergeConflictDialog(QDialog):
    """合并冲突解决对话框。

    UI 布局:
      - 冲突样本选择下拉
      - 差异对比表格（字段 | 已有值 | 新值 | 差异）
      - 批量选择策略（全部保留已有 / 全部使用新值 / 逐字段选择）
    """

    def __init__(self, parent=None,
                 conflicts: List[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("数据合并冲突解决")
        self.setMinimumSize(700, 450)
        self._conflicts = conflicts or []  # [{"sample_no": ..., "fields": [...], "existing": {...}, "new": {...}}]
        self._resolutions: Dict[str, str] = {}  # sample_no -> "keep_existing" | "use_new"
        self._setup_ui()

        if self._conflicts:
            self._load_conflict(0)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 12)

        # 标题
        title = QLabel(f"发现 {len(self._conflicts)} 个样本存在数据冲突")
        title.setStyleSheet(f"color: {Colors.TEXT_ACCENT}; font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(
            "以下样本在数据库中存在旧值，与即将导入的数据存在差异。"
            "请逐样本确认保留策略。"
        )
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 当前冲突样本标识
        self._sample_label = QLabel("")
        self._sample_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 10pt; font-weight: bold;"
        )
        layout.addWidget(self._sample_label)

        # 差异对比表格
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["字段", "已有值", "新值", "差异"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        layout.addWidget(self._table, 1)

        # 策略选择
        strategy_group = QGroupBox("保留策略")
        strategy_layout = QHBoxLayout(strategy_group)

        self._strategy_group = QButtonGroup(self)

        self._keep_existing_radio = QRadioButton("保留已有值（覆盖策略）")
        self._keep_existing_radio.setChecked(True)
        self._strategy_group.addButton(self._keep_existing_radio, 0)

        self._use_new_radio = QRadioButton("使用新值")
        self._strategy_group.addButton(self._use_new_radio, 1)

        self._custom_radio = QRadioButton("自定义（表格中逐字段选择）")
        self._strategy_group.addButton(self._custom_radio, 2)

        strategy_layout.addWidget(self._keep_existing_radio)
        strategy_layout.addWidget(self._use_new_radio)
        strategy_layout.addWidget(self._custom_radio)
        strategy_layout.addStretch()
        layout.addWidget(strategy_group)

        # 按钮区
        prev_layout = QHBoxLayout()

        self._prev_btn = QPushButton("← 上一个")
        self._prev_btn.setProperty("secondary", True)
        self._prev_btn.clicked.connect(self._on_prev)
        prev_layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("下一个 →")
        self._next_btn.setProperty("secondary", True)
        self._next_btn.clicked.connect(self._on_next)
        prev_layout.addWidget(self._next_btn)

        prev_layout.addStretch()

        self._apply_btn = QPushButton("应用到全部")
        self._apply_btn.clicked.connect(self._on_apply_to_all)
        prev_layout.addWidget(self._apply_btn)

        layout.addLayout(prev_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        skip_btn = QPushButton("跳过全部冲突")
        skip_btn.setProperty("secondary", True)
        skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(skip_btn)

        accept_btn = QPushButton("确认并合并")
        accept_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(accept_btn)

        layout.addLayout(btn_layout)

        self._current_idx = 0

    def _load_conflict(self, idx: int):
        """加载指定索引的冲突。"""
        if idx < 0 or idx >= len(self._conflicts):
            return

        self._current_idx = idx
        conflict = self._conflicts[idx]

        sample_no = conflict.get("sample_no", "?")
        existing_source = conflict.get("existing_source", "")
        new_source = conflict.get("new_source", "")

        self._sample_label.setText(
            f"样本: {sample_no} ｜ 已有来源: {existing_source[:30]} ｜ 新来源: {new_source[:30]}"
        )

        fields = conflict.get("fields", [])
        self._table.setRowCount(len(fields))

        for row, field_info in enumerate(fields):
            field_name = field_info.get("field_name", "")
            existing_val = field_info.get("existing_value", "")
            new_val = field_info.get("new_value", "")

            self._table.setItem(row, 0, QTableWidgetItem(str(field_name)))

            existing_item = QTableWidgetItem(str(existing_val))
            existing_item.setForeground(Qt.gray if hasattr(Qt, 'gray') else Qt.GlobalColor.gray)
            self._table.setItem(row, 1, existing_item if existing_val is not None else QTableWidgetItem("—"))

            new_item = QTableWidgetItem(str(new_val))
            self._table.setItem(row, 2, new_item)

            # 计算差异
            try:
                ev = float(existing_val)
                nv = float(new_val)
                diff = abs(nv - ev)
                diff_str = f"{diff:.4f}"
                if ev != 0:
                    pct = diff / abs(ev) * 100
                    diff_str += f" ({pct:.1f}%)"
            except (ValueError, TypeError):
                diff_str = "—"

            diff_item = QTableWidgetItem(diff_str)
            if any(c in diff_str for c in ["%"]):
                try:
                    pct_val = float(diff_str.split("(")[1].replace("%)", ""))
                    if pct_val > 10:
                        diff_item.setForeground(
                            Qt.red if hasattr(Qt, 'red') else Qt.GlobalColor.red
                        )
                except (ValueError, IndexError):
                    pass
            self._table.setItem(row, 3, diff_item)

        # 按钮状态
        self._prev_btn.setEnabled(idx > 0)
        self._next_btn.setEnabled(idx < len(self._conflicts) - 1)

    def _on_prev(self):
        if self._current_idx > 0:
            self._load_conflict(self._current_idx - 1)

    def _on_next(self):
        if self._current_idx < len(self._conflicts) - 1:
            self._load_conflict(self._current_idx + 1)

    def _on_apply_to_all(self):
        """将当前策略应用到全部冲突。"""
        strategy = self._strategy_group.checkedId()
        strategy_name = {0: "keep_existing", 1: "use_new", 2: "custom"}

        reply = QMessageBox.question(
            self, "确认",
            f"确定将所有 {len(self._conflicts)} 个冲突的解决策略设置为"
            f"""{self._strategy_group.checkedButton().text()}吗？""",
        )
        if reply == QMessageBox.Yes:
            for conflict in self._conflicts:
                sample_no = conflict.get("sample_no")
                self._resolutions[sample_no] = strategy_name.get(strategy, "keep_existing")

    def _on_accept(self):
        """确认合并。"""
        # 对当前冲突应用策略
        strategy = self._strategy_group.checkedId()
        strategy_name = {0: "keep_existing", 1: "use_new", 2: "custom"}
        if self._current_idx < len(self._conflicts):
            sample_no = self._conflicts[self._current_idx].get("sample_no")
            self._resolutions[sample_no] = strategy_name.get(strategy, "keep_existing")

        self.accept()

    def get_resolutions(self) -> Dict[str, str]:
        """获取解决方法。"""
        return self._resolutions
