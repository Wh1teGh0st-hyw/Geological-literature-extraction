"""批量处理进度对话框。

在 PDF 批量导入/提取过程中显示实时进度条和日志。
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QProgressBar,
    QLabel, QTextEdit, QPushButton, QWidget,
)
from PySide6.QtCore import Qt, Signal
from .theme import Colors


class BatchProgressDialog(QDialog):
    """批量处理进度对话框。

    显示:
    - 总体进度条
    - 当前文件进度条
    - 实时日志
    - 取消按钮
    """

    cancelled = Signal()

    def __init__(self, parent=None, title: str = "批量处理中..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 380)
        self.setModal(True)
        self._cancelled = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # 标题
        self._title_label = QLabel("正在处理 PDF 文件...")
        self._title_label.setStyleSheet(
            f"color: {Colors.TEXT_ACCENT}; font-size: 11pt; font-weight: bold;"
        )
        layout.addWidget(self._title_label)

        # 总体进度
        overall_layout = QHBoxLayout()
        overall_label = QLabel("总体进度:")
        overall_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        overall_layout.addWidget(overall_label)
        self._overall_progress = QProgressBar()
        self._overall_progress.setMinimum(0)
        self._overall_progress.setMaximum(100)
        overall_layout.addWidget(self._overall_progress)
        layout.addLayout(overall_layout)

        # 当前文件进度
        file_layout = QHBoxLayout()
        file_label = QLabel("当前文件:")
        file_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        file_layout.addWidget(file_label)
        self._file_progress = QProgressBar()
        self._file_progress.setMinimum(0)
        self._file_progress.setMaximum(100)
        file_layout.addWidget(self._file_progress)
        layout.addLayout(file_layout)

        # 状态文字
        self._status_label = QLabel("准备中...")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 9pt;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # 日志区
        log_label = QLabel("详细日志:")
        log_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        layout.addWidget(log_label)

        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setMaximumBlockCount(200)
        self._log_area.setStyleSheet(
            f"background-color: {Colors.BG_INPUT}; "
            f"color: {Colors.TEXT_SECONDARY}; "
            f"font-size: 8pt; "
            f"border: 1px solid {Colors.GRID_BORDER}; "
            f"font-family: Consolas, monospace;"
        )
        layout.addWidget(self._log_area, 1)

        # 取消按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setProperty("secondary", True)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)

    def _on_cancel(self):
        """取消按钮回调。"""
        self._cancelled = True
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText("正在取消...")
        self.append_log("[用户操作] 正在取消处理...")
        self.cancelled.emit()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    # ── 公共 API ───────────────────────────────────

    def set_title(self, text: str):
        self._title_label.setText(text)

    def update_progress(self, current: int, total: int, message: str = ""):
        """更新总体进度。

        Args:
            current: 当前进度值
            total: 总值
            message: 状态消息
        """
        pct = int(current / total * 100) if total > 0 else 0
        self._overall_progress.setValue(pct)
        if message:
            self._status_label.setText(message)
            self.append_log(message)

    def update_file_progress(self, current: int, total: int, message: str = ""):
        """更新当前文件进度。"""
        pct = int(current / total * 100) if total > 0 else 0
        self._file_progress.setValue(pct)
        if message:
            self.append_log(f"  {message}")

    def append_log(self, message: str):
        """追加日志行。"""
        self._log_area.append(message)

    def set_complete(self, message: str = ""):
        """标记为完成。"""
        self._overall_progress.setValue(100)
        self._file_progress.setValue(100)
        self._status_label.setText(message or "处理完成")
        self._cancel_btn.setText("关闭")
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setProperty("secondary", False)

    def set_error(self, message: str):
        """标记为错误状态。"""
        self._status_label.setText(f"❌ {message}")
        self._status_label.setStyleSheet(
            f"color: {Colors.STATUS_ERROR}; font-size: 9pt;"
        )
        self.append_log(f"[错误] {message}")
        self._cancel_btn.setText("关闭")
        self._cancel_btn.setEnabled(True)
