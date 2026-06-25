"""多源数据合并与去重引擎。

功能:
- 按 (Sample.No, Data source) 自动去重
- 冲突检测：同一样品不同来源的数据差异
- 合并策略：覆盖/保留/手工
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from loguru import logger

from data.models import GeochemSample


@dataclass
class MergeConflict:
    """合并冲突记录。"""
    sample_no: str
    field_name: str
    existing_value: Any
    new_value: Any
    existing_source: str
    new_source: str
    resolved: bool = False
    resolved_value: Any = None
    resolution: str = ""  # 'keep_existing' | 'use_new' | 'manual' | 'auto'


@dataclass
class MergeResult:
    """合并结果。"""
    samples_added: int = 0
    samples_updated: int = 0
    samples_skipped: int = 0
    conflicts: List[MergeConflict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class DataMerger:
    """数据合并与去重引擎。"""

    # 合并时检查的数值字段（差异 > 容差 视为冲突）
    NUMERIC_TOLERANCE = {
        # 主量元素 (%): 允许 0.5% 的差异
        "sio2": 0.5, "tio2": 0.1, "al2o3": 0.3, "fe2o3": 0.3,
        "feo": 0.3, "mno": 0.05, "mgo": 0.2, "cao": 0.2,
        "na2o": 0.2, "k2o": 0.2, "p2o5": 0.05, "loi": 0.5,
        # 微量元素: 允许 10% 的相对差异
        # (在比较时动态判断)
    }

    def find_duplicate(self, new_sample: GeochemSample,
                       existing_samples: List[GeochemSample]) -> Optional[GeochemSample]:
        """在已有样本中查找重复的样本。

        匹配规则:
        1. 精确匹配 (Sample.No + Data source)
        2. 宽松匹配 (Sample.No 相同，Data source 未知或不同)
        """
        # 精确匹配
        for existing in existing_samples:
            if (new_sample.sample_no and existing.sample_no and
                new_sample.sample_no.strip().lower() == existing.sample_no.strip().lower()):
                if (new_sample.data_source and existing.data_source and
                    new_sample.data_source.strip().lower() == existing.data_source.strip().lower()):
                    return existing
                # 如果新样本无来源，也视为重复
                if not new_sample.data_source or not existing.data_source:
                    return existing

        return None

    def detect_conflicts(self, new_sample: GeochemSample,
                         existing_sample: GeochemSample) -> List[MergeConflict]:
        """检测两个样本间的字段冲突。"""
        conflicts = []
        existing_dict = existing_sample.to_flat_dict()
        new_dict = new_sample.to_flat_dict()

        for field, new_val in new_dict.items():
            if new_val is None:
                continue
            existing_val = existing_dict.get(field)
            if existing_val is None:
                continue

            # 跳过非数值字段
            if not isinstance(new_val, (int, float)) or not isinstance(existing_val, (int, float)):
                if str(new_val).strip() != str(existing_val).strip():
                    conflicts.append(MergeConflict(
                        sample_no=new_sample.sample_no or "?",
                        field_name=field,
                        existing_value=existing_val,
                        new_value=new_val,
                        existing_source=existing_sample.data_source or "",
                        new_source=new_sample.data_source or "",
                    ))
                continue

            # 数值字段：检查差异
            if abs(new_val - existing_val) > 0:
                tolerance = self.NUMERIC_TOLERANCE.get(field.lower(), None)
                if tolerance is None:
                    # 相对容差 10%
                    avg = (abs(new_val) + abs(existing_val)) / 2
                    tolerance = max(avg * 0.1, 0.0001)

                if abs(new_val - existing_val) > tolerance:
                    conflicts.append(MergeConflict(
                        sample_no=new_sample.sample_no or "?",
                        field_name=field,
                        existing_value=existing_val,
                        new_value=new_val,
                        existing_source=existing_sample.data_source or "",
                        new_source=new_sample.data_source or "",
                    ))

        return conflicts

    def auto_resolve_conflicts(self, conflicts: List[MergeConflict]) -> List[MergeConflict]:
        """自动解决冲突（保守策略：保留已有值）。"""
        for conflict in conflicts:
            conflict.resolved = True
            conflict.resolved_value = conflict.existing_value
            conflict.resolution = "auto_keep_existing"
        return conflicts

    def merge_samples(self, new_samples: List[GeochemSample],
                      existing_samples: List[GeochemSample],
                      auto_resolve: bool = True) -> Tuple[List[GeochemSample], MergeResult]:
        """合并新旧样本列表。

        Args:
            new_samples: 新解析的样本
            existing_samples: 已有样本
            auto_resolve: 是否自动解决冲突（保留已有值）
        Returns:
            (合并后的完整列表, 合并结果统计)
        """
        result = MergeResult()
        merged = list(existing_samples)  # 从已有样本开始

        for new_sample in new_samples:
            existing = self.find_duplicate(new_sample, existing_samples)

            if existing is None:
                # 新样本，直接添加
                merged.append(new_sample)
                result.samples_added += 1
                continue

            # 检测冲突
            conflicts = self.detect_conflicts(new_sample, existing)
            if not conflicts:
                # 无冲突：用新数据补充缺失字段
                self._fill_missing_fields(existing, new_sample)
                result.samples_updated += 1
                continue

            # 有冲突
            if auto_resolve:
                self.auto_resolve_conflicts(conflicts)
                # 保留已有值，但补充缺失字段
                self._fill_missing_fields(existing, new_sample)
                result.samples_updated += 1
            else:
                # 不自动解决，跳过并标记
                result.samples_skipped += 1

            result.conflicts.extend(conflicts)

        logger.info(
            f"合并完成: +{result.samples_added} 新增, "
            f"~{result.samples_updated} 更新, "
            f"-{result.samples_skipped} 跳过, "
            f"!{len(result.conflicts)} 冲突"
        )

        return merged, result

    def _fill_missing_fields(self, target: GeochemSample, source: GeochemSample):
        """用 source 的非空字段填充 target 的空字段。"""
        # 主量元素
        for field in ["sio2", "tio2", "al2o3", "fe2o3", "feo", "mno",
                       "mgo", "cao", "na2o", "k2o", "p2o5", "loi", "total"]:
            if getattr(target.major, field) is None:
                src_val = getattr(source.major, field)
                if src_val is not None:
                    setattr(target.major, field, src_val)

        # 微量元素
        for field in ["li", "be", "sc", "v", "cr", "co", "ni", "cu", "zn", "ga",
                       "rb", "sr", "y", "zr", "nb", "cs", "ba", "hf", "ta",
                       "pb", "th", "u", "w", "sn", "mo"]:
            if getattr(target.trace, field) is None:
                src_val = getattr(source.trace, field)
                if src_val is not None:
                    setattr(target.trace, field, src_val)

        # REE
        for field in ["la", "ce", "pr", "nd", "sm", "eu", "gd", "tb",
                       "dy", "ho", "er", "tm", "yb", "lu"]:
            if getattr(target.ree, field) is None:
                src_val = getattr(source.ree, field)
                if src_val is not None:
                    setattr(target.ree, field, src_val)

        # 同位素
        for field in ["sr87_sr86_i", "sr87_sr86_err", "nd143_nd144_i",
                       "nd143_nd144_err", "epsilon_nd_t", "epsilon_nd_err",
                       "t_dm2_nd", "t_dm1_nd", "hf176_hf177_i", "hf176_hf177_err",
                       "epsilon_hf_t", "epsilon_hf_err", "t_dm2_hf", "t_dm1_hf"]:
            if getattr(target.isotopes, field) is None:
                src_val = getattr(source.isotopes, field)
                if src_val is not None:
                    setattr(target.isotopes, field, src_val)

        # 标识字段
        for field in ["mining_area", "rock_body", "rock_type", "granite_type",
                       "formation_age", "age_error", "age_method",
                       "longitude", "latitude", "elevation"]:
            if getattr(target, field, None) is None:
                src_val = getattr(source, field, None)
                if src_val is not None:
                    setattr(target, field, src_val)
