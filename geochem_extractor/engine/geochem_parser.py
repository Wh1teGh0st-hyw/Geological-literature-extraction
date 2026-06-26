"""地球化学解析主引擎。

编排 列识别 → 值清洗 → 单位转换 → 映射为 GeochemSample 的完整流水线。
"""

import pandas as pd
from typing import List, Optional, Dict, Any
from loguru import logger

from .element_identifier import ElementIdentifier
from .value_cleaner import ValueCleaner, CleanedValue
from .unit_converter import UnitConverter

from data.models import (
    GeochemSample, MajorElements, TraceElements,
    REEElements, Isotopes, ComputedIndices,
)


class GeochemParserEngine:
    """地球化学解析主引擎。

    输入：提取后的表格 DataFrame + 列到字段的映射
    输出：GeochemSample 对象列表
    """

    def __init__(self):
        self.element_id = ElementIdentifier()
        self.cleaner = ValueCleaner()
        self.converter = UnitConverter()

    def parse_table(self, df: pd.DataFrame,
                    source_label: str = "",
                    pdf_source_id: Optional[int] = None,
                    table_id: Optional[int] = None) -> List[GeochemSample]:
        """解析整个提取表格为多个 GeochemSample。"""
        if df is None or len(df) < 2:
            return []

        # 步骤1: 列识别
        headers = [str(df.iloc[0, c]) if df.iloc[0, c] else f"Col_{c}" for c in range(len(df.columns))]
        column_mapping = self.element_id.identify_columns_batch(headers)

        if not column_mapping:
            logger.warning(f"无法识别任何列: {headers[:10]}")
            column_mapping = self._brute_force_column_detect(df)

        if not column_mapping:
            return []

        logger.debug(f"列映射: {len(column_mapping)}/{len(headers)} 列已识别")

        # 步骤2: 确定数据行起始位置
        data_start = 1
        for r in range(1, min(8, len(df))):
            row_vals = [df.iloc[r, c] for c in range(len(df.columns))]
            if self.cleaner.is_data_row(row_vals):
                data_start = r
                break

        # 步骤3: 检测脚注
        rows_list = [[df.iloc[r, c] for c in range(len(df.columns))]
                      for r in range(data_start, len(df))]
        footnote_start = self.cleaner.detect_footnote_start(rows_list)
        data_end = data_start + footnote_start if footnote_start >= 0 else len(df)

        # 步骤4: 逐行解析
        samples = []
        for row_idx in range(data_start, data_end):
            sample = self._parse_row(
                df, row_idx, column_mapping,
                source_label=source_label,
                pdf_source_id=pdf_source_id,
                table_id=table_id,
            )
            if sample is not None:
                samples.append(sample)

        logger.info(f"解析完成: {len(samples)} 个样本 (来源: {source_label})")
        return samples

    def _parse_row(self, df: pd.DataFrame, row_idx: int,
                   column_mapping: Dict[int, tuple],
                   **meta) -> Optional[GeochemSample]:
        """解析单行数据为 GeochemSample。"""
        sample = GeochemSample()
        has_data = False
        major_values = {}

        sample.extracted_table_id = meta.get("table_id")
        sample.pdf_source_id = meta.get("pdf_source_id")
        sample.data_source = meta.get("source_label", "")

        for col_idx, (field_name, category, confidence) in column_mapping.items():
            if col_idx >= len(df.columns):
                continue

            raw_value = df.iloc[row_idx, col_idx]
            cleaned = self.cleaner.clean(raw_value)
            if cleaned.value is None:
                continue

            value = self.converter.detect_and_convert(
                field_name, cleaned.value, cleaned.original_text
            )

            if category == "identity":
                val_str = str(raw_value).strip() if raw_value else None
                if field_name == "sample_no":
                    sample.sample_no = val_str
                elif field_name == "granite_type":
                    sample.granite_type = val_str
                elif field_name == "rock_type":
                    sample.rock_type = val_str
                elif field_name == "mining_area":
                    sample.mining_area = val_str
                elif field_name == "rock_body":
                    sample.rock_body = val_str
                elif field_name == "data_source":
                    sample.data_source = val_str
                elif field_name == "age_method":
                    sample.age_method = val_str
                has_data = True
                continue

            elif category == "chronology":
                for f in ["formation_age", "age_error", "mineralization_age", "min_age_error"]:
                    if field_name == f:
                        setattr(sample, f, value)
                        has_data = True
                continue

            elif category == "spatial":
                for f in ["longitude", "latitude", "elevation"]:
                    if field_name == f:
                        setattr(sample, f, value)
                        has_data = True
                continue

            elif category == "major":
                setattr(sample.major, field_name, value)
                major_values[field_name] = value
                has_data = True
                continue

            elif category == "trace":
                setattr(sample.trace, field_name, value)
                has_data = True
                continue

            elif category == "ree":
                setattr(sample.ree, field_name, value)
                has_data = True
                continue

            elif category == "isotope":
                setattr(sample.isotopes, field_name, value)
                has_data = True
                continue

        # 自动计算 Total
        if sample.major.total is None:
            total = self.converter.normalize_total(major_values)
            if total:
                sample.major.total = round(total, 2)

        if not has_data:
            return None

        if not sample.sample_no:
            sample.sample_no = f"auto_{meta.get('source_label', 'unknown')}_r{row_idx}"

        return sample

    def _brute_force_column_detect(self, df: pd.DataFrame) -> Dict[int, tuple]:
        """暴力检测列 — 基于数据行的特征反推列类型。"""
        if len(df) < 2:
            return {}
        result = {}
        for col_idx in range(len(df.columns)):
            values = []
            for r in range(1, min(len(df), 4)):
                cleaned = self.cleaner.clean(df.iloc[r, col_idx])
                if cleaned.value is not None:
                    values.append(cleaned.value)
            if not values:
                continue
            avg_val = sum(values) / len(values)
            if 30 <= avg_val <= 85 and any(v > 50 for v in values):
                result[col_idx] = ("sio2", "major", 0.5)
            elif 0 <= avg_val <= 10000:
                if avg_val > 500:
                    result[col_idx] = ("ba", "trace", 0.3)
                elif avg_val < 50:
                    result[col_idx] = ("la", "ree", 0.3)
        return result


def parse_extracted_table(df: pd.DataFrame, **kwargs) -> List[GeochemSample]:
    """快捷函数：解析单张提取表格。"""
    engine = GeochemParserEngine()
    return engine.parse_table(df, **kwargs)
