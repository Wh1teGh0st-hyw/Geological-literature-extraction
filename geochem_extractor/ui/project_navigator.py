"""项目导航器 — QTreeView 展示项目结构。

树形结构:
  + PDF 源文件 (N)
  + 已提取表格 (N)
  + 已解析样本 (N)
  + 已分类 (N)
"""

from PySide6.QtWidgets import QTreeView, QApplication
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont, QColor

from .theme import Colors


class ProjectNavigator(QTreeView):
    """左侧项目导航树。"""

    item_clicked = Signal(str, int)  # 发送 (节点类型, id) 信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = QStandardItemModel()
        self.setModel(self._model)
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(True)

        # 根节点
        self._root = self._model.invisibleRootItem()

        # 创建分组节点
        self._pdfs_node = self._create_group("📄 PDF 源文件 (0)")
        self._tables_node = self._create_group("📋 已提取表格 (0)")
        self._samples_node = self._create_group("🧪 已解析样本 (0)")
        self._classified_node = self._create_group("✅ 已分类 (0)")
        self._export_node = self._create_group("📊 可导出 (0)")

        self._root.appendRows([
            self._pdfs_node, self._tables_node,
            self._samples_node, self._classified_node,
            self._export_node,
        ])

        self.expandAll()
        self.clicked.connect(self._on_clicked)

    def _create_group(self, text: str) -> QStandardItem:
        """创建分组标题节点。"""
        item = QStandardItem(text)
        item.setSelectable(True)
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        item.setEditable(False)
        return item

    def _on_clicked(self, index: QModelIndex):
        """处理点击。"""
        item = self._model.itemFromIndex(index)
        if item and item.data(Qt.UserRole):
            self.item_clicked.emit(
                item.data(Qt.UserRole + 1),
                item.data(Qt.UserRole),
            )

    def update_counts(self, samples: int, classified: int, pdfs: int, tables: int = 0, export_ready: int = 0):
        """更新各分组节点计数。"""
        self._pdfs_node.setText(f"📄 PDF 源文件 ({pdfs})")
        self._tables_node.setText(f"📋 已提取表格 ({tables})")
        self._samples_node.setText(f"🧪 已解析样本 ({samples})")
        self._classified_node.setText(f"✅ 已分类 ({classified})")
        self._export_node.setText(f"📊 可导出 ({export_ready})")

    def clear(self):
        """清空所有子节点。"""
        for node in [self._pdfs_node, self._tables_node, self._samples_node,
                      self._classified_node, self._export_node]:
            node.removeRows(0, node.rowCount())
        self.update_counts(0, 0, 0, 0, 0)
