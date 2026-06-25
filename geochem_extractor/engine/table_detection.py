"""多策略表格区域检测引擎。

策略:
1. PyMuPDF find_tables() — 适合带框线的标准表格
2. pdfplumber — 适合无框线但结构规整的学术表格
3. 自研启发式 — 根据数字对齐行密度、制表符分布做后备检测
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

import fitz  # PyMuPDF
import pdfplumber


@dataclass
class TableCandidate:
    """表格候选区域。"""
    page_number: int
    method: str                # 'pymupdf' | 'pdfplumber' | 'heuristic'
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1) 归一化坐标
    confidence: float          # 0.0-1.0
    row_estimate: int = 0      # 估算行数
    col_estimate: int = 0      # 估算列数
    raw_region: Any = None     # 原始检测结果（库特定）


class TableDetectionEngine:
    """多策略表格区域检测引擎。

    按优先级依次尝试：
    1. pdfplumber（最擅长学术论文表格）
    2. PyMuPDF find_tables（快速，适合框线表格）
    3. 自研启发式（兜底）
    """

    def __init__(self):
        self.min_rows = 3       # 最少行数
        self.min_cols = 3       # 最少列数
        self.min_confidence = 0.3

    def detect(self, pdf_path: str, page_number: int,
               prefer_method: str = "pdfplumber") -> List[TableCandidate]:
        """在指定 PDF 页面上检测所有表格候选区域。

        Args:
            pdf_path: PDF 文件路径
            page_number: 页码 (0-based)
            prefer_method: 优先使用的方法
        Returns:
            按置信度降序排列的候选区域列表
        """
        candidates = []

        # 策略1: pdfplumber（主策略）
        try:
            pdf_candidates = self._detect_pdfplumber(pdf_path, page_number)
            candidates.extend(pdf_candidates)
        except Exception as e:
            logger.debug(f"pdfplumber 检测失败 (page {page_number}): {e}")

        # 策略2: PyMuPDF（如果 pdfplumber 结果不足）
        if len(candidates) < 2:
            try:
                mupdf_candidates = self._detect_pymupdf(pdf_path, page_number)
                # 避免与 pdfplumber 结果重叠
                for mc in mupdf_candidates:
                    if not self._overlaps_with_any(mc, candidates):
                        candidates.append(mc)
            except Exception as e:
                logger.debug(f"PyMuPDF 检测失败 (page {page_number}): {e}")

        # 策略3: 启发式兜底
        if not candidates:
            try:
                heuristic_candidates = self._detect_heuristic(pdf_path, page_number)
                candidates.extend(heuristic_candidates)
            except Exception as e:
                logger.debug(f"启发式检测失败 (page {page_number}): {e}")

        # 过滤低置信度候选
        candidates = [c for c in candidates if c.confidence >= self.min_confidence]
        candidates.sort(key=lambda c: c.confidence, reverse=True)

        return candidates

    def _detect_pdfplumber(self, pdf_path: str, page_number: int) -> List[TableCandidate]:
        """使用 pdfplumber 检测表格。"""
        candidates = []

        with pdfplumber.open(pdf_path) as pdf:
            if page_number >= len(pdf.pages):
                return candidates
            page = pdf.pages[page_number]

            # 方法A: find_tables()（自动检测）
            tables = page.find_tables()

            for i, table in enumerate(tables):
                bbox = table.bbox  # (x0, top, x1, bottom)
                cells = table.cells
                rows = len(set(c[1] for c in cells)) if cells else 0
                cols = len(set(c[0] for c in cells)) if cells else 0

                if rows < self.min_rows or cols < self.min_cols:
                    continue

                # 计算置信度
                confidence = self._estimate_confidence(rows, cols, cells)

                candidates.append(TableCandidate(
                    page_number=page_number,
                    method="pdfplumber",
                    bbox=tuple(bbox),
                    confidence=confidence,
                    row_estimate=rows,
                    col_estimate=cols,
                    raw_region=table,
                ))

            # 方法B: 自定义启发式（pdfplumber 漏掉的表）
            if not candidates:
                custom = self._detect_text_blocks(page, page_number)
                candidates.extend(custom)

        return candidates

    def _detect_text_blocks(self, page, page_number: int) -> List[TableCandidate]:
        """基于 pdfplumber 文本块对齐的检测。"""
        candidates = []
        chars = page.chars
        if not chars:
            return candidates

        # 按 y 坐标聚类成行
        rows = {}
        for char in chars:
            y_key = round(char["top"], 0)
            if y_key not in rows:
                rows[y_key] = []
            rows[y_key].append(char)

        # 筛选数字密集行（疑似表格行）
        numeric_rows = {}
        num_pattern = re.compile(r"[\d.+\-±×eE,]+")
        for y, row_chars in rows.items():
            row_text = "".join(c["text"] for c in row_chars)
            numbers = num_pattern.findall(row_text)
            valid_numbers = [n for n in numbers if len(n) > 1 and not n.endswith(".")]
            if len(valid_numbers) >= self.min_cols:
                numeric_rows[y] = len(valid_numbers)

        if len(numeric_rows) < self.min_rows:
            return candidates

        # 确定表格边界
        y_coords = sorted(numeric_rows.keys())
        min_y = min(y_coords) - 5
        max_y = max(y_coords) + 15
        x_coords = [c["x0"] for row in rows.values() for c in row]
        min_x = min(x_coords) if x_coords else 0
        max_x = max(x_coords) if x_coords else page.width

        avg_cols = sum(numeric_rows.values()) / len(numeric_rows)
        confidence = min(0.9, 0.4 + (len(numeric_rows) - self.min_rows) * 0.1)

        candidates.append(TableCandidate(
            page_number=page_number,
            method="pdfplumber_text_blocks",
            bbox=(min_x, min_y, max_x, max_y),
            confidence=confidence,
            row_estimate=len(numeric_rows),
            col_estimate=int(avg_cols),
        ))

        return candidates

    def _detect_pymupdf(self, pdf_path: str, page_number: int) -> List[TableCandidate]:
        """使用 PyMuPDF 的 find_tables() 检测表格。"""
        candidates = []

        pdf = fitz.open(pdf_path)
        if page_number >= pdf.page_count:
            pdf.close()
            return candidates

        page = pdf[page_number]

        # PyMuPDF find_tables()
        tabs = page.find_tables()
        if tabs and tabs.tables:
            for table in tabs.tables:
                bbox = table.bbox
                rows = table.row_count
                cols = table.col_count

                if rows < self.min_rows or cols < self.min_cols:
                    continue

                confidence = self._estimate_confidence(
                    rows, cols, table.cells if hasattr(table, 'cells') else []
                )

                candidates.append(TableCandidate(
                    page_number=page_number,
                    method="pymupdf",
                    bbox=tuple(bbox),
                    confidence=min(0.85, confidence),
                    row_estimate=rows,
                    col_estimate=cols,
                    raw_region=table,
                ))

        pdf.close()
        return candidates

    def _detect_heuristic(self, pdf_path: str, page_number: int) -> List[TableCandidate]:
        """自研启发式检测 — 基于数字对齐模式。"""
        candidates = []

        # 使用 pdfplumber 提取文本
        with pdfplumber.open(pdf_path) as pdf:
            if page_number >= len(pdf.pages):
                return candidates
            page = pdf.pages[page_number]
            text = page.extract_text()

        if not text:
            return candidates

        lines = text.split("\n")
        num_pattern = re.compile(r"[\d.+\-±×eE,]+")
        table_line_indices = []

        for i, line in enumerate(lines):
            numbers = num_pattern.findall(line)
            valid = [n for n in numbers if len(n) > 1]
            if len(valid) >= self.min_cols:
                table_line_indices.append(i)

        if len(table_line_indices) < self.min_rows:
            return candidates

        # 检查连续行
        consecutive_groups = []
        current_group = [table_line_indices[0]]
        for idx in table_line_indices[1:]:
            if idx - current_group[-1] <= 2:  # 允许间隔1行
                current_group.append(idx)
            else:
                if len(current_group) >= self.min_rows:
                    consecutive_groups.append(current_group)
                current_group = [idx]
        if len(current_group) >= self.min_rows:
            consecutive_groups.append(current_group)

        for group in consecutive_groups:
            avg_cols = sum(
                len([n for n in num_pattern.findall(lines[i]) if len(n) > 1])
                for i in group
            ) / len(group)
            confidence = min(0.7, 0.3 + len(group) * 0.05)

            candidates.append(TableCandidate(
                page_number=page_number,
                method="heuristic",
                bbox=(0, 0, 0, 0),  # 使用整页
                confidence=confidence,
                row_estimate=len(group),
                col_estimate=int(avg_cols),
            ))

        return candidates

    def _estimate_confidence(self, rows: int, cols: int, cells: list) -> float:
        """估算表格检测的置信度。"""
        # 基础分
        base = 0.5
        # 行数越多越可信
        row_bonus = min(0.2, (rows - self.min_rows) * 0.05)
        # 列数越多越可信
        col_bonus = min(0.15, (cols - self.min_cols) * 0.03)
        # 有单元格信息加分
        cell_bonus = 0.15 if cells else 0
        return min(0.95, base + row_bonus + col_bonus + cell_bonus)

    def _overlaps_with_any(self, candidate: TableCandidate,
                           existing: List[TableCandidate]) -> bool:
        """检查候选区域是否与已有区域重叠。"""
        for e in existing:
            if self._bbox_iou(candidate.bbox, e.bbox) > 0.3:
                return True
        return False

    def _bbox_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """计算两个边界框的 IoU。"""
        if bbox1 == (0, 0, 0, 0) or bbox2 == (0, 0, 0, 0):
            return 0

        x_overlap = max(0, min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0]))
        y_overlap = max(0, min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1]))
        intersection = x_overlap * y_overlap
        if intersection == 0:
            return 0

        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0
