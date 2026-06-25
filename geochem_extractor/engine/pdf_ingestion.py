"""PDF 摄入引擎 — 加载 PDF、提取元数据、检测文字页/图片页。

使用 PyMuPDF 进行元数据提取和文本密度检测，为后续表格检测做准备。
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from loguru import logger

import fitz  # PyMuPDF


@dataclass
class PageInfo:
    """单页信息。"""
    page_number: int          # 页码 (0-based)
    text_length: int          # 可提取文本字符数
    text_density: float       # 文本密度 (字符/页面积)
    is_image_based: bool      # 是否为图片型页面
    image_count: int = 0      # 页内图片数量
    has_table_candidates: bool = False  # 是否包含疑似表格区域


@dataclass
class PDFDocument:
    """PDF 文档完整信息。"""
    file_path: str
    file_name: str
    file_size: int
    file_hash: str

    # 元数据
    title: str = ""
    authors: str = ""
    year: Optional[int] = None
    journal: str = ""
    doi: str = ""
    abstract: str = ""

    # 页面信息
    page_count: int = 0
    text_pages: int = 0
    image_pages: int = 0
    pages: List[PageInfo] = field(default_factory=list)

    # 表格候选区域（后续阶段填充）
    table_candidate_pages: List[int] = field(default_factory=list)


class PDFIngestionEngine:
    """PDF 摄入引擎。

    负责：
    1. 打开 PDF 文件，提取元数据
    2. 逐页检测文本密度，分类为文字页/图片页
    3. 计算文件哈希用于变更检测
    4. 提取 DOI、标题、作者等文献信息
    """

    # 文本密度阈值：低于此值视为图片型页面
    TEXT_DENSITY_THRESHOLD = 0.005  # 字符/平方点
    # 最小文本长度阈值：低于此值视为图片型页面
    MIN_TEXT_LENGTH = 100

    def ingest(self, file_path: str) -> PDFDocument:
        """分析一个 PDF 文件，返回完整文档信息。"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF 文件不存在: {file_path}")

        logger.info(f"正在分析 PDF: {file_path}")

        # 计算文件哈希
        file_size = os.path.getsize(file_path)
        file_hash = self._compute_hash(file_path)
        file_name = os.path.basename(file_path)

        doc = PDFDocument(
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            file_hash=file_hash,
        )

        # 用 PyMuPDF 打开分析
        try:
            pdf = fitz.open(file_path)
            doc.page_count = pdf.page_count

            # 提取元数据
            self._extract_metadata(pdf, doc)

            # 逐页分析
            for page_num in range(pdf.page_count):
                page_info = self._analyze_page(pdf, page_num)
                doc.pages.append(page_info)

                if page_info.is_image_based:
                    doc.image_pages += 1
                else:
                    doc.text_pages += 1

                if page_info.has_table_candidates:
                    doc.table_candidate_pages.append(page_num)

            pdf.close()

        except Exception as e:
            logger.error(f"PDF 分析失败: {e}")
            raise

        logger.info(
            f"PDF 分析完成: {doc.file_name} "
            f"({doc.page_count} 页, {doc.text_pages} 文字页, "
            f"{doc.image_pages} 图片页, {len(doc.table_candidate_pages)} 疑似含表页)"
        )

        return doc

    def _compute_hash(self, file_path: str) -> str:
        """计算文件的 SHA-256 哈希。"""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def _extract_metadata(self, pdf: fitz.Document, doc: PDFDocument):
        """从 PDF 元数据和首段文本中提取文献信息。"""
        meta = pdf.metadata or {}

        doc.title = meta.get("title", "")
        doc.authors = meta.get("author", "")

        # 尝试从首段文本解析标题和作者（针对中文论文）
        if not doc.title or len(doc.title) < 5:
            first_page_text = pdf[0].get_text()
            lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]

            # 取前几行作为标题候选
            for line in lines[:5]:
                if len(line) > 10 and not line.startswith("DOI") and not line.startswith("http"):
                    doc.title = line[:200]
                    break

            # 尝试提取 DOI
            for line in lines[:10]:
                if "DOI" in line.upper() or "doi" in line:
                    doc.doi = line.replace("DOI:", "").replace("doi:", "").strip()
                    break

            # 尝试提取期刊名（通常在页眉）
            if lines:
                for line in lines[:3]:
                    if any(kw in line for kw in ["学报", "地质", "Journal", "Geology"]):
                        doc.journal = line.strip()
                        break

        # 尝试提取年份
        if not doc.year:
            import re
            text_200 = pdf[0].get_text()[:500]
            year_match = re.search(r"(19|20)\d{2}", text_200)
            if year_match:
                doc.year = int(year_match.group())

        # 提取摘要
        first_page_text = pdf[0].get_text()
        if "摘" in first_page_text and "要" in first_page_text:
            abs_start = first_page_text.find("摘要") if "摘要" in first_page_text else first_page_text.find("摘　要")
            if abs_start >= 0:
                abs_end = first_page_text.find("关键词", abs_start)
                if abs_end < 0:
                    abs_end = first_page_text.find("关键", abs_start)
                if abs_end < 0:
                    abs_end = min(len(first_page_text), abs_start + 1000)
                doc.abstract = first_page_text[abs_start:abs_end].strip()[:500]

    def _analyze_page(self, pdf: fitz.Document, page_num: int) -> PageInfo:
        """分析单页，判断文字/图片属性。"""
        page = pdf[page_num]
        text = page.get_text()
        text_length = len(text.strip())

        # 计算页面面积
        rect = page.rect
        area = rect.width * rect.height

        # 文本密度 = 字符数 / 面积（平方点）
        text_density = text_length / area if area > 0 else 0

        # 统计图片数量
        image_count = len(page.get_images())

        # 判断是否为图片型页面
        is_image = (
            text_length < self.MIN_TEXT_LENGTH and
            text_density < self.TEXT_DENSITY_THRESHOLD and
            image_count > 0
        )

        # 简单启发式：检测疑似表格
        has_table = self._detect_table_candidates(text, page)

        return PageInfo(
            page_number=page_num,
            text_length=text_length,
            text_density=text_density,
            is_image_based=is_image,
            image_count=image_count,
            has_table_candidates=has_table,
        )

    def _detect_table_candidates(self, text: str, page: fitz.Page) -> bool:
        """检测页面是否可能包含表格。

        启发式规则：
        1. 包含"表"或"Table"关键词
        2. 存在重复的制表符或对齐的数字列
        3. 多个用空格对齐的数字行
        """
        # 关键词检测
        table_keywords = ["表", "Table", "TABLE", "table"]
        has_keyword = any(kw in text for kw in table_keywords)

        # 数字行检测（至少3行含多个数值）
        lines = text.split("\n")
        numeric_lines = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # 统计这一行的数字片段
            import re
            numbers = re.findall(r"\d+\.?\d*", stripped)
            if len(numbers) >= 3:
                numeric_lines += 1

        return has_keyword or numeric_lines >= 3


def ingest_pdf(file_path: str) -> PDFDocument:
    """快捷函数：摄入单个 PDF。"""
    engine = PDFIngestionEngine()
    return engine.ingest(file_path)


def batch_ingest_pdfs(directory: str, recursive: bool = True) -> List[PDFDocument]:
    """批量摄入目录中的 PDF 文件。

    Args:
        directory: 目录路径
        recursive: 是否递归扫描子目录
    Returns:
        PDFDocument 列表
    """
    engine = PDFIngestionEngine()
    docs = []

    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdf_dir = Path(directory)
    pdf_files = list(pdf_dir.glob(pattern))

    logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")

    for pdf_path in pdf_files:
        try:
            doc = engine.ingest(str(pdf_path))
            docs.append(doc)
        except Exception as e:
            logger.error(f"跳过 {pdf_path.name}: {e}")

    logger.info(f"批量摄入完成: {len(docs)}/{len(pdf_files)} 个 PDF 成功")
    return docs
