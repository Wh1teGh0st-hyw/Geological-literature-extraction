"""内嵌 matplotlib 图表画布 — 嵌入到 Qt 标签页中。

功能:
- TAS 分类图
- REE 球粒陨石标准化配分曲线
- 花岗岩判别图（4种子图）
- 图表联动：点击/悬停 → 发射样本索引信号
"""

from typing import List, Dict, Optional, Any
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, Signal

from ..theme import Colors
from geochem.diagrams import DiagramDataBuilder, ChartRenderer


class ChartCanvas(QWidget):
    """内嵌图表画布 — 管理 matplotlib 图表在 Qt 中的渲染。

    图表类型切换和样本数据联动。
    """

    # 信号：选中的样本序号列表（对应 data 中的 index）
    sample_selected = Signal(list)
    refresh_requested = Signal()

    CHART_TYPES = {
        "TAS 分类图": "tas",
        "REE 配分曲线": "ree",
        "ASI vs SiO₂": "asi_sio2",
        "FeMgI vs SiO₂": "femgi_sio2",
        "Ga/Al vs Zr": "ga_al_zr",
        "Rb vs Y+Nb": "rb_ynb",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples_data: List[Dict[str, Any]] = []
        self._available = ChartRenderer.is_available()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 4, 8, 4)

        # 顶部控制栏
        control = QHBoxLayout()

        control.addWidget(QLabel("图表类型:"))
        self._chart_selector = QComboBox()
        self._chart_selector.addItems(list(self.CHART_TYPES.keys()))
        self._chart_selector.currentTextChanged.connect(self._on_chart_changed)
        control.addWidget(self._chart_selector, 1)

        self._sample_count_label = QLabel("")
        self._sample_count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 9pt;")
        control.addWidget(self._sample_count_label)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        control.addWidget(refresh_btn)

        layout.addLayout(control)

        # matplotlib 画布区域
        if self._available:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(facecolor=Colors.BG_PRIMARY, dpi=100)
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setMinimumHeight(400)
            layout.addWidget(self._canvas, 1)

            # 点击事件
            self._canvas.mpl_connect("button_press_event", self._on_click)
        else:
            warning = QLabel("⚠ matplotlib 未安装，无法渲染图表\n\n"
                            "请运行: pip install matplotlib")
            warning.setAlignment(Qt.AlignCenter)
            warning.setStyleSheet(f"color: {Colors.STATUS_WARNING}; font-size: 10pt;")
            layout.addWidget(warning, 1)

        # 提示
        hint = QLabel("提示: 请先在数据网格中加载数据，然后切换到此标签页查看图表。")
        hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 8pt; padding: 4px;")
        layout.addWidget(hint)

    def load_samples(self, samples: List[Dict[str, Any]]):
        """从数据网格加载样本数据。"""
        self._samples_data = samples
        self._sample_count_label.setText(f"数据: {len(samples)} 个样本")
        self._render_current()

    def _render_current(self):
        """根据当前选择的图表类型渲染。"""
        if not self._available or not self._samples_data:
            return

        chart_key = self.CHART_TYPES[self._chart_selector.currentText()]
        self._figure.clear()

        builder = DiagramDataBuilder()

        if chart_key == "tas":
            data = builder.build_tas_data(self._samples_data)
            ax = self._figure.add_subplot(111)
            ChartRenderer.render_tas(data, ax)
            self._figure.tight_layout()

        elif chart_key == "ree":
            data = builder.build_ree_data(self._samples_data)
            ax = self._figure.add_subplot(111)
            ChartRenderer.render_ree(data, ax)
            self._figure.tight_layout()

        elif chart_key in ("asi_sio2", "femgi_sio2", "ga_al_zr", "rb_ynb"):
            data = builder.build_discrimination_data(self._samples_data)
            disc_data = data.get(chart_key, {})
            if disc_data.get("x"):
                ax = self._figure.add_subplot(111)
                ax.set_facecolor(Colors.BG_SECONDARY)
                ax.tick_params(colors=Colors.TEXT_SECONDARY)
                ax.scatter(disc_data["x"], disc_data["y"],
                          c=Colors.ACCENT_ORANGE, s=20, alpha=0.7)
                ax.set_title(self._chart_selector.currentText(),
                            color=Colors.TEXT_ACCENT, fontweight="bold")
                ax.grid(True, alpha=0.15, color=Colors.TEXT_PRIMARY)
                for spine in ax.spines.values():
                    spine.set_color(Colors.GRID_BORDER)
                self._figure.tight_layout()

        self._canvas.draw()

    def _on_chart_changed(self, *_):
        self._render_current()

    def _on_click(self, event):
        """图表点击事件 — 发射选中的样本信号。"""
        # matplotlib 的点击坐标对应图表数据点
        # 简化实现：查找最近的数据点
        if event.xdata is None or event.ydata is None:
            return

        chart_key = self.CHART_TYPES[self._chart_selector.currentText()]
        builder = DiagramDataBuilder()

        if chart_key == "tas":
            data = builder.build_tas_data(self._samples_data)
            if data["x"] and len(data["x"]) > 0:
                # 找最近的点
                import math
                best_idx = 0
                best_dist = float("inf")
                for i in range(len(data["x"])):
                    dx = data["x"][i] - event.xdata
                    dy = data["y"][i] - event.ydata
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i
                if best_dist < 5:  # 合理容差
                    self.sample_selected.emit([best_idx])

    def refresh(self):
        """刷新图表。"""
        if self._samples_data:
            self._render_current()
