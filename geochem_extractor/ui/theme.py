"""Claude 主题色 + Qt 样式表。

定义应用的完整颜色方案和 QSS 样式，在主窗口初始化时加载。
"""

# ── 颜色常量 (可被 Python 代码引用) ───────────────────

class Colors:
    """Claude 主题色板"""

    # 背景
    BG_PRIMARY = "#1A1A2E"
    BG_SECONDARY = "#16213E"
    BG_TERTIARY = "#0F3460"
    BG_INPUT = "#1C2A4A"
    BG_HOVER = "#2A3F6A"

    # 强调色 (Claude 橙)
    ACCENT_ORANGE = "#D97706"
    ACCENT_LIGHT = "#F59E0B"
    ACCENT_DARK = "#B45309"
    ACCENT_MUTED = "#92400E"

    # 文字
    TEXT_PRIMARY = "#E8E8E8"
    TEXT_SECONDARY = "#A0A0B0"
    TEXT_MUTED = "#6B7280"
    TEXT_ACCENT = "#D97706"

    # 状态
    STATUS_ERROR = "#EF4444"
    STATUS_WARNING = "#F59E0B"
    STATUS_SUCCESS = "#10B981"
    STATUS_INFO = "#3B82F6"

    # 花岗岩分类颜色
    ITYPE = "#3B82F6"       # I型 - 蓝色
    STYPE = "#EF4444"       # S型 - 红色
    ATYPE = "#10B981"       # A型 - 绿色
    MTYPE = "#8B5CF6"       # M型 - 紫色
    UNCLASSIFIED = "#6B7280"  # 未分类 - 灰色

    # 数据网格
    GRID_HEADER_BG = "#0F3460"
    GRID_ROW_EVEN = "#1A1A2E"
    GRID_ROW_ODD = "#1E2746"
    GRID_ROW_SELECTED = "#2A3F6A"
    GRID_BORDER = "#2A3F6A"
    GRID_TEXT = "#E8E8E8"

    @classmethod
    def classification_color(cls, granite_type: str) -> str:
        """根据花岗岩类型返回对应颜色。"""
        if not granite_type:
            return cls.UNCLASSIFIED
        t = granite_type.strip().upper()
        if "I" in t or "Ⅰ" in t:
            return cls.ITYPE
        if "S" in t:
            return cls.STYPE
        if "A" in t:
            return cls.ATYPE
        if "M" in t:
            return cls.MTYPE
        return cls.UNCLASSIFIED


# ── 完整 QSS 样式表 ────────────────────────────────────

APP_STYLESHEET = r"""
/* ================================================================
   GeoChemExtractor · Claude 主题样式表
   ================================================================ */

/* ── 全局 ─────────────────────────────────────────────── */

QWidget {
    background-color: #1A1A2E;
    color: #E8E8E8;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 9pt;
}

/* ── 菜单栏 ───────────────────────────────────────────── */

QMenuBar {
    background-color: #16213E;
    color: #E8E8E8;
    border-bottom: 2px solid #D97706;
    padding: 2px;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #D97706;
    color: #FFFFFF;
}

QMenu {
    background-color: #16213E;
    color: #E8E8E8;
    border: 1px solid #2A3F6A;
    padding: 4px;
}

QMenu::item {
    padding: 6px 30px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #D97706;
}

QMenu::separator {
    height: 1px;
    background: #2A3F6A;
    margin: 4px 8px;
}

/* ── 工具栏 ───────────────────────────────────────────── */

QToolBar {
    background-color: #16213E;
    border-bottom: 1px solid #2A3F6A;
    spacing: 4px;
    padding: 4px;
}

QToolButton {
    background-color: transparent;
    color: #E8E8E8;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 12px;
}

QToolButton:hover {
    background-color: #2A3F6A;
    border-color: #D97706;
}

QToolButton:pressed {
    background-color: #D97706;
}

/* ── 主按钮 ───────────────────────────────────────────── */

QPushButton {
    background-color: #D97706;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #F59E0B;
}

QPushButton:pressed {
    background-color: #B45309;
}

QPushButton:disabled {
    background-color: #4B5563;
    color: #9CA3AF;
}

QPushButton[secondary="true"] {
    background-color: transparent;
    border: 1px solid #D97706;
    color: #D97706;
}

QPushButton[secondary="true"]:hover {
    background-color: #2A3F6A;
}

/* ── 输入控件 ─────────────────────────────────────────── */

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1C2A4A;
    color: #E8E8E8;
    border: 1px solid #2A3F6A;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #D97706;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #A0A0B0;
}

QComboBox QAbstractItemView {
    background-color: #16213E;
    color: #E8E8E8;
    selection-background-color: #D97706;
    border: 1px solid #2A3F6A;
}

/* ── 标签页 ───────────────────────────────────────────── */

QTabWidget::pane {
    border: 1px solid #2A3F6A;
    background-color: #1A1A2E;
}

QTabBar::tab {
    background-color: #16213E;
    color: #A0A0B0;
    padding: 8px 16px;
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
}

QTabBar::tab:selected {
    color: #D97706;
    border-bottom: 2px solid #D97706;
}

QTabBar::tab:hover {
    color: #F59E0B;
}

/* ── 数据表格 ─────────────────────────────────────────── */

QTableView {
    background-color: #1A1A2E;
    alternate-background-color: #1E2746;
    color: #E8E8E8;
    gridline-color: #2A3F6A;
    selection-background-color: #D97706;
    selection-color: #FFFFFF;
    border: 1px solid #2A3F6A;
    font-size: 9pt;
}

QTableView::item {
    padding: 4px;
}

QTableView::item:selected {
    background-color: #D97706;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #0F3460;
    color: #E8E8E8;
    padding: 6px 4px;
    border: 1px solid #2A3F6A;
    border-right: 1px solid #1A1A2E;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #1A4A80;
}

/* ── 树形视图 (导航器) ────────────────────────────────── */

QTreeView {
    background-color: #16213E;
    color: #E8E8E8;
    border: none;
    outline: none;
}

QTreeView::item {
    padding: 4px 8px;
    border-radius: 4px;
}

QTreeView::item:selected {
    background-color: #D97706;
    color: #FFFFFF;
}

QTreeView::item:hover {
    background-color: #2A3F6A;
}

QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
    border-image: none;
}

/* ── 滚动条 ───────────────────────────────────────────── */

QScrollBar:vertical {
    background-color: #16213E;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #2A3F6A;
    border-radius: 5px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #D97706;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #16213E;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #2A3F6A;
    border-radius: 5px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #D97706;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── 进度条 ───────────────────────────────────────────── */

QProgressBar {
    background-color: #1C2A4A;
    border: 1px solid #2A3F6A;
    border-radius: 4px;
    text-align: center;
    color: #E8E8E8;
    min-height: 20px;
}

QProgressBar::chunk {
    background-color: #D97706;
    border-radius: 3px;
}

/* ── 状态栏 ───────────────────────────────────────────── */

QStatusBar {
    background-color: #16213E;
    color: #A0A0B0;
    border-top: 1px solid #2A3F6A;
}

/* ── 分组框 ───────────────────────────────────────────── */

QGroupBox {
    background-color: #16213E;
    border: 1px solid #2A3F6A;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #D97706;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 8px;
}

/* ── 分隔线 ───────────────────────────────────────────── */

QSplitter::handle {
    background-color: #2A3F6A;
    width: 2px;
}

/* ── 对话框 ───────────────────────────────────────────── */

QDialog {
    background-color: #16213E;
    border: 1px solid #2A3F6A;
    border-radius: 6px;
}

/* ── 标签 ─────────────────────────────────────────────── */

QLabel {
    color: #E8E8E8;
    background-color: transparent;
}

QLabel[heading="true"] {
    font-size: 11pt;
    font-weight: bold;
    color: #D97706;
}

QLabel[subtitle="true"] {
    font-size: 9pt;
    color: #A0A0B0;
}

/* ── 文本编辑区 ───────────────────────────────────────── */

QTextEdit, QPlainTextEdit {
    background-color: #1C2A4A;
    color: #E8E8E8;
    border: 1px solid #2A3F6A;
    border-radius: 4px;
    padding: 4px;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #D97706;
}

/* ── 复选框/单选按钮 ───────────────────────────────────── */

QCheckBox, QRadioButton {
    background-color: transparent;
    color: #E8E8E8;
    spacing: 8px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #6B7280;
    border-radius: 3px;
    background-color: #1C2A4A;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    border-color: #D97706;
    background-color: #D97706;
}

/* ── 工具提示 ─────────────────────────────────────────── */

QToolTip {
    background-color: #16213E;
    color: #E8E8E8;
    border: 1px solid #D97706;
    padding: 4px 8px;
    border-radius: 4px;
}
"""
