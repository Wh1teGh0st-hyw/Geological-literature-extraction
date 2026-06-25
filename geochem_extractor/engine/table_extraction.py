"""混合表格提取引擎。

编排 pdfplumber / Camelot / PaddleOCR 三种提取策略：
- pdfplumber: 主力，处理不规则表格和合并单元格
- Camelot: 适合有框线的规则表格（后备）
- PaddleOCR: 图片型页面（第3阶段接入）
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger

import pandas as pd
import pdfplumber

from .table_detection import TableCandidate, TableDetectionEngine


@dataclass
class ExtractedTable:
    """提取完成的表格。"""
    pdf_path: str
    pdf_page: int
    table_index: int = 0
    method: str = "pdfplumber"
    confidence: float = 1.0
    is_image_based: bool = False

    # 表格数据
    dataframe: Optional[pd.DataFrame] = None
    raw_json: str = ""             # 原始提取结果的 JSON
    raw_html: str = ""             # pdfplumber 提取的 HTML

    # 元数据
    rows: int = 0
    cols: int = 0
    header_row_count: int = 1      # 表头行数（估算）
    has_footnote: bool = False     # 是否包含注释行
    page_label: str = ""           # 页码标签 (如 "Table 3")

    # 状态
    extraction_errors: List[str] = field(default_factory=list)


class TableExtractionEngine:
    """混合表格提取引擎。

    编排多策略提取流程，输出统一的 ExtractedTable 结构。
    """

    def __init__(self):
        self.detection_engine = TableDetectionEngine()

    def extract_from_page(self, pdf_path: str, page_number: int,
                          candidates: List[TableCandidate] = None) -> List[ExtractedTable]:
        """从 PDF 单页提取所有表格。

        Args:
            pdf_path: PDF 文件路径
            page_number: 页码 (0-based)
            candidates: 预检测的表格候选区域（可选，内部自动检测）
        Returns:
            提取的表格列表
        """
        # 检测表格候选区域
        if candidates is None:
            candidates = self.detection_engine.detect(pdf_path, page_number)

        if not candidates:
            logger.debug(f"第 {page_number + 1} 页未检测到表格")
            return []

        results = []
        for i, candidate in enumerate(candidates):
            try:
                table = self._extract_single(pdf_path, page_number, candidate, i)
                if table and table.rows >= 2 and table.cols >= 2:
                    results.append(table)
            except Exception as e:
                logger.warning(f"表格提取失败 (page {page_number + 1}, candidate {i}): {e}")

        return results

    def extract_from_pdf(self, pdf_path: str,
                         page_numbers: List[int] = None) -> List[ExtractedTable]:
        """从整个 PDF 文件提取表格。

        Args:
            pdf_path: PDF 文件路径
            page_numbers: 指定页码列表（None 表示全部页面）
        Returns:
            提取的表格列表
        """
        # 先进行全局检测
        all_candidates = {}
        pages_to_check = page_numbers if page_numbers else self._get_all_pages(pdf_path)

        for page_num in pages_to_check:
            candidates = self.detection_engine.detect(pdf_path, page_num)
            if candidates:
                all_candidates[page_num] = candidates

        # 对每个含候选的页面进行提取
        all_tables = []
        for page_num, candidates in all_candidates.items():
            tables = self.extract_from_page(pdf_path, page_num, candidates)
            all_tables.extend(tables)

        logger.info(
            f"PDF 提取完成: {os.path.basename(pdf_path)} "
            f"→ {len(all_tables)} 个表格 ({len(all_candidates)} 页含表)"
        )
        return all_tables

    def _extract_single(self, pdf_path: str, page_number: int,
                        candidate: TableCandidate, index: int) -> Optional[ExtractedTable]:
        """提取单个候选区域的表格数据。"""
        method = candidate.method

        if "pdfplumber" in method:
            return self._extract_pdfplumber(pdf_path, page_number, candidate, index)
        elif method == "pymupdf":
            return self._extract_pymupdf(pdf_path, page_number, candidate, index)
        elif method == "heuristic":
            return self._extract_heuristic(pdf_path, page_number, candidate, index)
        elif method == "ocr":
            return self._extract_ocr(pdf_path, page_number, candidate, index)
        else:
            return self._extract_pdfplumber(pdf_path, page_number, candidate, index)

    def _clip_bbox_to_page(self, bbox: tuple, page) -> tuple:
        """将边界框裁剪到页面范围内。"""
        x0, top, x1, bottom = bbox
        pw, ph = page.width, page.height
        x0 = max(0, x0)
        top = max(0, top)
        x1 = min(pw - 0.01, x1)
        bottom = min(ph - 0.01, bottom)
        return (x0, top, x1, bottom)

    def _extract_pdfplumber(self, pdf_path: str, page_number: int,
                            candidate: TableCandidate, index: int) -> Optional[ExtractedTable]:
        """使用 pdfplumber 提取表格数据。"""
        with pdfplumber.open(pdf_path) as pdf:
            if page_number >= len(pdf.pages):
                return None
            page = pdf.pages[page_number]

            # 裁剪 bbox 到页面范围内（避免 pdfplumber 报错）
            bbox = self._clip_bbox_to_page(candidate.bbox, page)

            # 如果候选区域已有 raw_region（来自 find_tables）
            if candidate.raw_region is not None and hasattr(candidate.raw_region, 'extract'):
                try:
                    table_data = candidate.raw_region.extract()
                except Exception:
                    table_data = None

                if table_data:
                    df = self._clean_dataframe(table_data, candidate)
                    if df is not None and len(df) >= 2:
                        table = self._build_table_result(df, pdf_path, page_number, index, candidate)
                        # 也获取 HTML 格式
                        try:
                            table.raw_html = page.within_bbox(bbox).extract_text() or ""
                        except Exception:
                            pass
                        return table

            # 如果候选区域没有预提取数据，用 crop 区域提取
            if bbox != (0, 0, 0, 0):
                try:
                    cropped = page.within_bbox(bbox)
                    table_data = cropped.extract_table()
                except Exception:
                    table_data = None
            else:
                # 整页提取
                try:
                    tables = page.extract_tables()
                    table_data = tables[0] if tables else None
                except Exception:
                    table_data = None

            if table_data:
                df = self._clean_dataframe(table_data, candidate)
                if df is not None and len(df) >= 2:
                    return self._build_table_result(df, pdf_path, page_number, index, candidate)

            # 最后的尝试：提取文本并解析
            if bbox != (0, 0, 0, 0):
                text = page.within_bbox(bbox).extract_text()
            else:
                text = page.extract_text()

            if text:
                df = self._parse_text_table(text, candidate)
                if df is not None and len(df) >= 2:
                    return self._build_table_result(df, pdf_path, page_number, index, candidate)

        return None

    def _extract_pymupdf(self, pdf_path: str, page_number: int,
                         candidate: TableCandidate, index: int) -> Optional[ExtractedTable]:
        """使用 PyMuPDF 提取表格数据。"""
        import fitz
        pdf = fitz.open(pdf_path)
        if page_number >= pdf.page_count:
            pdf.close()
            return None

        page = pdf[page_number]

        try:
            tabs = page.find_tables()
            if tabs and tabs.tables and index < len(tabs.tables):
                table = tabs.tables[index]
                # PyMuPDF 表格直接提取为二维列表
                data = table.extract()
                if data:
                    df = self._clean_dataframe(data, candidate)
                    if df is not None and len(df) >= 2:
                        result = self._build_table_result(df, pdf_path, page_number, index, candidate)
                        result.method = "pymupdf"
                        pdf.close()
                        return result
        except Exception as e:
            logger.debug(f"PyMuPDF 提取失败: {e}")

        pdf.close()
        return None

    def _extract_heuristic(self, pdf_path: str, page_number: int,
                           candidate: TableCandidate, index: int) -> Optional[ExtractedTable]:
        """启发式提取 — 利用候选区域的文本行特征重建表格。

        当 pdfplumber 的 find_tables() 检测不到无框线表格时，
        用此方法基于数字密集行重建表格结构。
        """
        with pdfplumber.open(pdf_path) as pdf:
            if page_number >= len(pdf.pages):
                return None
            page = pdf.pages[page_number]

            # 裁剪 bbox
            bbox = self._clip_bbox_to_page(candidate.bbox, page) if candidate.bbox != (0, 0, 0, 0) else None

            # 获取该区域的文本行
            if bbox:
                text = page.within_bbox(bbox).extract_text()
            else:
                text = page.extract_text()

            if not text:
                return None

            lines = text.split("\n")
            num_pattern = re.compile(r"[\d.+\-±×eE,]+")

            # 收集候选数字行及其上下文
            numeric_rows = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    continue
                numbers = num_pattern.findall(stripped)
                valid_nums = [n for n in numbers
                              if len(n) > 1
                              and not n.endswith(".")
                              and n.count(".") <= 1]
                if len(valid_nums) >= 3 and len(stripped) > 20:
                    numeric_rows.append(i)

            if len(numeric_rows) < 2:
                return None

            # 找出连续的数值行组（允许间隔0-1行）
            groups = []
            current = [numeric_rows[0]]
            for idx in numeric_rows[1:]:
                if idx - current[-1] <= 2:
                    current.append(idx)
                else:
                    groups.append(current)
                    current = [idx]
            groups.append(current)

            # 只处理最大的组
            best_group = max(groups, key=len) if groups else numeric_rows

            # 查找表头：数据行之前的行（向前回溯2-3行）
            first_data = best_group[0]
            header_start = max(0, first_data - 4)

            # 收集表头候选行
            header_candidates = []
            for hi in range(header_start, first_data):
                if hi >= len(lines):
                    break
                line = lines[hi].strip()
                if not line:
                    continue
                if hi in [r for r in numeric_rows]:
                    continue
                # 表头可能包含元素名/单位等
                if any(c.isalpha() for c in line):
                    header_candidates.append(line)

            # 解析表头
            if header_candidates:
                # 合并多行表头
                all_header_text = " ".join(header_candidates)
                # 智能分割：考虑中英文混合、括号、下标等
                header_parts = re.split(r"\s{2,}", all_header_text)
                if len(header_parts) <= 1:
                    header_parts = re.split(r"(?<=[a-zA-Z])\s+(?=[A-Z])", all_header_text)
                if len(header_parts) <= 1:
                    header_parts = re.split(r"\s+", all_header_text)
                # 过滤纯数字/纯符号的"假表头"
                header_parts = [h for h in header_parts if not h.replace(".", "").replace("-", "").isdigit()]
            else:
                header_parts = []

            # 解析数据行
            table_rows = []
            for ri in best_group:
                if ri >= len(lines):
                    continue
                line = lines[ri].strip()
                if line.startswith("Table") or line.startswith("表"):
                    continue  # 跳过表格标题行
                cells = re.split(r"\s{2,}", line)
                # 合并单字符单元格（中文被拆字）
                merged = []
                buf = []
                for c in cells:
                    if len(c) <= 1 and c.strip():
                        buf.append(c)
                    else:
                        if buf:
                            merged.append("".join(buf))
                            buf = []
                        merged.append(c)
                if buf:
                    merged.append("".join(buf))
                if len(merged) >= 2:
                    table_rows.append(merged)

            if len(table_rows) < 2:
                return None

            # 构建完整表格：表头 + 数据
            max_cols = max(len(r) for r in table_rows)
            if header_parts:
                # 检查表头列数是否合理
                if len(header_parts) < max_cols - 2:
                    # 表头不够用，添加占位列
                    header_parts += [f"Col_{i}" for i in range(len(header_parts), max_cols)]
                table_rows.insert(0, header_parts[:max_cols])
            else:
                # 尝试用数据行第一行作为表头
                if len(table_rows) > 1:
                    first = table_rows[0]
                    # 如果第一行包含字母但数字较少，可能是表头
                    has_alpha = any(c.isalpha() for c in " ".join(first))
                    num_count = sum(len(num_pattern.findall(c)) for c in first)
                    if has_alpha and num_count < len(first) * 0.5:
                        pass  # 保留第一行为表头
                    else:
                        # 插入占位表头
                        table_rows.insert(0, [f"Col_{i}" for i in range(max_cols)])

            df = self._clean_dataframe(table_rows, candidate)

            if df is None or len(df) < 2:
                return None

            result = self._build_table_result(df, pdf_path, page_number, index, candidate)
            result.method = "heuristic_parsed"
            result.confidence = min(0.85, 0.5 + len(table_rows) * 0.03)
            return result

    def _clean_dataframe(self, raw_data: list, candidate: TableCandidate) -> Optional[pd.DataFrame]:
        """清洗提取的原始表格数据，返回整洁的 DataFrame。"""
        if not raw_data or len(raw_data) < 2:
            return None

        # 找到第一个有效数据列数最多的行作为表头候选
        max_cols = max(len(row) for row in raw_data if row)

        # 补齐列数
        cleaned = []
        for row in raw_data:
            if row is None:
                continue
            cleaned_row = []
            for cell in row:
                val = str(cell).strip() if cell is not None else ""
                cleaned_row.append(val)
            # 补齐
            while len(cleaned_row) < max_cols:
                cleaned_row.append("")
            cleaned.append(cleaned_row[:max_cols])

        if len(cleaned) < 2:
            return None

        try:
            df = pd.DataFrame(cleaned)
            # 移除完全空的行
            df = df.dropna(how="all")
            # 移除完全空的列
            df = df.dropna(axis=1, how="all")

            if len(df) < 2 or len(df.columns) < 2:
                return None

            return df
        except Exception as e:
            logger.debug(f"DataFrame 构建失败: {e}")
            return None

    def _parse_text_table(self, text: str, candidate: TableCandidate) -> Optional[pd.DataFrame]:
        """从自由文本中解析表格结构。"""
        if not text:
            return None

        lines = text.strip().split("\n")
        if len(lines) < 2:
            return None

        # 以制表符或连续空格分割
        rows = []
        for line in lines:
            # 尝试用连续空格分割（表格式对齐）
            cells = re.split(r"\s{2,}", line.strip())
            # 过滤空字符串
            cells = [c.strip() for c in cells if c.strip()]
            if len(cells) >= 2:
                rows.append(cells)

        if len(rows) < 2:
            return None

        return self._clean_dataframe(rows, candidate)

    def _build_table_result(self, df: pd.DataFrame, pdf_path: str, page_number: int,
                            index: int, candidate: TableCandidate) -> ExtractedTable:
        """构建 ExtractedTable 结果对象。"""
        # 检测脚注行
        has_footnote = self._detect_footnotes(df)

        # 估算表头行数
        header_count = self._estimate_header_rows(df)

        # 生成原始 JSON
        try:
            raw_json = df.to_json(orient="values", force_ascii=False)
        except Exception:
            raw_json = str(df.values.tolist())

        return ExtractedTable(
            pdf_path=pdf_path,
            pdf_page=page_number,
            table_index=index,
            method=candidate.method,
            confidence=candidate.confidence,
            dataframe=df,
            raw_json=raw_json,
            rows=len(df),
            cols=len(df.columns),
            header_row_count=header_count,
            has_footnote=has_footnote,
            page_label=f"p{page_number + 1}_t{index}",
        )

    def _detect_footnotes(self, df: pd.DataFrame) -> bool:
        """检测是否包含脚注行。"""
        if df is None or len(df) == 0:
            return False
        # 检查最后几行是否包含脚注关键词
        footnote_keywords = ["Note:", "注：", "注释：", "*", "†", "Abbreviation"]
        last_rows = df.tail(3)
        for _, row in last_rows.iterrows():
            row_text = " ".join(str(v) for v in row.values if pd.notna(v))
            if any(kw in row_text for kw in footnote_keywords):
                return True
        return False

    def _estimate_header_rows(self, df: pd.DataFrame) -> int:
        """估算表头行数。"""
        if df is None or len(df) == 0:
            return 1
        # 检查第一行：如果第一行全是文字、第二行有数值，表头为1行
        first_row = df.iloc[0].astype(str)
        all_text_first = all(
            re.search(r"[A-Za-z一-鿿]", str(v))
            for v in first_row if v and v != "None"
        )
        if all_text_first and len(df) > 1:
            return 1
        # 如果前两行都没有数值，可能是双行表头
        if len(df) > 2:
            second_row = df.iloc[1].astype(str)
            all_text_second = all(
                re.search(r"[A-Za-z一-鿿]", str(v))
                for v in second_row if v and v != "None"
            )
            if all_text_second:
                return 2
        return 1

    def _get_all_pages(self, pdf_path: str) -> List[int]:
        """获取 PDF 的所有页码。"""
        with pdfplumber.open(pdf_path) as pdf:
            return list(range(len(pdf.pages)))

    def _extract_ocr(self, pdf_path: str, page_number: int,
                     candidate: TableCandidate, index: int) -> Optional[ExtractedTable]:
        """使用 EasyOCR 处理图片型 PDF 页面的表格提取。

        流程:
        1. pdf2image 将页面转为图片（如果 PDF 本身是图片型）
        2. 裁剪到候选区域的 bbox
        3. EasyOCR 识别文字 + 位置
        4. 基于 y 坐标聚类行，x 坐标分割列
        5. 重建为 DataFrame
        """
        try:
            import easyocr
        except ImportError:
            logger.warning("EasyOCR 未安装。请运行: pip install easyocr")
            return None

        try:
            from pdf2image import convert_from_path
            import numpy as np
        except ImportError:
            logger.warning("pdf2image 未安装。请运行: pip install pdf2image")
            return None

        try:
            # 将 PDF 页面渲染为图片
            images = convert_from_path(
                pdf_path, first_page=page_number + 1,
                last_page=page_number + 1, dpi=200
            )
            if not images:
                return None

            image = images[0]

            # 裁剪到表格候选区域
            if candidate.bbox != (0, 0, 0, 0):
                pw, ph = 595, 842  # A4 标准点
                img_w, img_h = image.size
                x_scale, y_scale = img_w / pw, img_h / ph
                x0 = int(candidate.bbox[0] * x_scale)
                y0 = int(candidate.bbox[1] * y_scale)
                x1 = int(candidate.bbox[2] * x_scale)
                y1 = int(candidate.bbox[3] * y_scale)
                image = image.crop((x0, y0, x1, y1))

            # EasyOCR 识别
            reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
            results = reader.readtext(np.array(image))

            if not results:
                return None

            # 按 y 坐标聚类行（容差 10px）
            rows = {}
            y_tolerance = 10
            for (bbox, text, conf) in results:
                y_center = (bbox[0][1] + bbox[2][1]) / 2
                row_key = round(y_center / y_tolerance) * y_tolerance
                if row_key not in rows:
                    rows[row_key] = []
                rows[row_key].append((bbox[0][0], text, conf))

            # 按 y 坐标排序行
            sorted_rows = sorted(rows.items())

            # 提取每行的文本（按 x 坐标排序列）
            table_data = []
            for _, row_items in sorted_rows:
                row_items.sort(key=lambda r: r[0])  # 按 x 排序
                cells = [item[1] for item in row_items]
                table_data.append(cells)

            if len(table_data) < 2:
                return None

            df = self._clean_dataframe(table_data, candidate)
            if df is None or len(df) < 2:
                return None

            result = self._build_table_result(df, pdf_path, page_number, index, candidate)
            result.method = "easyocr"
            result.is_image_based = True
            result.confidence = min(0.8, candidate.confidence)
            return result

        except Exception as e:
            logger.warning(f"OCR 提取失败 (page {page_number + 1}): {e}")
            return None


# ── 快捷函数 ──────────────────────────────────────────

def extract_tables_from_pdf(pdf_path: str) -> List[ExtractedTable]:
    """从 PDF 提取所有表格。"""
    engine = TableExtractionEngine()
    return engine.extract_from_pdf(pdf_path)
