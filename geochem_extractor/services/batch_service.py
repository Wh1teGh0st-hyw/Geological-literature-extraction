"""批量处理服务 — 编排 PDF 摄入、表格检测、提取的流水线。

提供高层接口供 UI 调用，支持 QThread 异步执行。
"""

import os
from typing import List, Optional, Callable
from loguru import logger

from engine.pdf_ingestion import PDFIngestionEngine, PDFDocument
from engine.table_detection import TableDetectionEngine, TableCandidate
from engine.table_extraction import TableExtractionEngine, ExtractedTable


class BatchProcessingService:
    """批量处理编排服务。

    封装 PDF 摄入 → 表格检测 → 表格提取 的完整流水线。
    """

    def __init__(self):
        self.ingestion_engine = PDFIngestionEngine()
        self.detection_engine = TableDetectionEngine()
        self.extraction_engine = TableExtractionEngine()

    def process_single_pdf(self, pdf_path: str,
                           progress_callback: Callable = None,
                           cancel_check: Callable = None) -> dict:
        """处理单个 PDF 的完整流水线。

        Returns:
            dict with keys: pdf_doc, tables, errors
        """
        result = {"pdf_doc": None, "tables": [], "errors": []}

        if not os.path.exists(pdf_path):
            result["errors"].append(f"文件不存在: {pdf_path}")
            return result

        try:
            if progress_callback:
                progress_callback(0, 3, f"正在分析: {os.path.basename(pdf_path)}")

            # 阶段1: PDF 摄入
            pdf_doc = self.ingestion_engine.ingest(pdf_path)
            result["pdf_doc"] = pdf_doc

            if progress_callback:
                progress_callback(1, 3, f"检测表格区域 ({pdf_doc.page_count} 页)...")

            # 阶段2: 表格检测
            all_candidates = {}
            for page_num in range(pdf_doc.page_count):
                if cancel_check and cancel_check():
                    return result

                candidates = self.detection_engine.detect(pdf_path, page_num)
                if candidates:
                    all_candidates[page_num] = candidates

            if not all_candidates:
                logger.info(f"未检测到表格: {os.path.basename(pdf_path)}")
                return result

            if progress_callback:
                progress_callback(2, 3,
                    f"正在提取表格 ({len(all_candidates)} 页含表)...")

            # 阶段3: 表格提取
            all_tables = []
            for page_num, candidates in all_candidates.items():
                if cancel_check and cancel_check():
                    return result

                tables = self.extraction_engine.extract_from_page(
                    pdf_path, page_num, candidates
                )
                all_tables.extend(tables)

            result["tables"] = all_tables
            logger.info(
                f"处理完成: {os.path.basename(pdf_path)} "
                f"→ {len(all_tables)} 个表格"
            )

        except Exception as e:
            result["errors"].append(f"处理失败: {str(e)}")
            logger.error(f"PDF 处理异常: {pdf_path} - {e}")

        return result

    def process_directory(self, directory: str,
                          progress_callback: Callable = None,
                          cancel_check: Callable = None,
                          recursive: bool = True) -> list:
        """批量处理目录下的所有 PDF。

        Returns:
            list of dict: 每个 PDF 的处理结果
        """
        from pathlib import Path

        pdf_dir = Path(directory)
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(pdf_dir.glob(pattern))

        if not pdf_files:
            logger.warning(f"未找到 PDF 文件: {directory}")
            return []

        results = []
        total = len(pdf_files)
        logger.info(f"开始批量处理 {total} 个 PDF")

        for i, pdf_path in enumerate(pdf_files):
            if cancel_check and cancel_check():
                break

            if progress_callback:
                progress_callback(
                    i, total,
                    f"PDF {i + 1}/{total}: {pdf_path.name}"
                )

            result = self.process_single_pdf(
                str(pdf_path),
                cancel_check=cancel_check,
            )
            result["source"] = str(pdf_path)
            results.append(result)

        success_count = sum(1 for r in results if not r["errors"])
        table_count = sum(len(r["tables"]) for r in results)
        logger.info(
            f"批量处理完成: {success_count}/{total} PDF 成功, "
            f"共提取 {table_count} 个表格"
        )

        return results


# ── 快捷函数 ──────────────────────────────────────────

def quick_process_pdf(pdf_path: str) -> dict:
    """快速处理单个 PDF。"""
    service = BatchProcessingService()
    return service.process_single_pdf(pdf_path)
