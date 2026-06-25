"""数据质量验证引擎。

对解析后的地球化学数据进行检查:
1. 主量元素总和校验
2. 元素合理范围检查
3. REE配分模式平滑性检查
4. 交叉元素一致性检查
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class ValidationResult:
    """单条验证结果。"""
    is_valid: bool
    field_name: str = ""
    message: str = ""
    severity: str = "info"  # "error" / "warning" / "info"
    expected_range: tuple = None
    actual_value: Any = None


class DataValidator:
    """地球化学数据质量验证器。"""

    # 主量元素合理范围 (wt%)
    MAJOR_RANGES = {
        "sio2": (35, 80),
        "tio2": (0, 5),
        "al2o3": (5, 40),
        "fe2o3": (0, 20),
        "feo": (0, 20),
        "mno": (0, 5),
        "mgo": (0, 25),
        "cao": (0, 25),
        "na2o": (0, 15),
        "k2o": (0, 15),
        "p2o5": (0, 5),
        "loi": (-5, 20),
        "total": (85, 110),
    }

    # 微量元素合理范围 (ppm)
    TRACE_RANGES = {
        "li": (0, 10000), "be": (0, 500), "sc": (0, 100),
        "v": (0, 500), "cr": (0, 3000), "co": (0, 300),
        "ni": (0, 3000), "cu": (0, 500), "zn": (0, 500),
        "ga": (0, 50), "rb": (0, 2000), "sr": (0, 3000),
        "y": (0, 200), "zr": (0, 1500), "nb": (0, 200),
        "cs": (0, 100), "ba": (0, 3000), "hf": (0, 50),
        "ta": (0, 20), "pb": (0, 200), "th": (0, 100),
        "u": (0, 50), "w": (0, 200), "sn": (0, 100), "mo": (0, 20),
    }

    # REE 合理范围 (ppm)
    REE_RANGES = {
        "la": (0, 500), "ce": (0, 1000), "pr": (0, 100),
        "nd": (0, 500), "sm": (0, 100), "eu": (0, 20),
        "gd": (0, 50), "tb": (0, 10), "dy": (0, 50),
        "ho": (0, 10), "er": (0, 30), "tm": (0, 5),
        "yb": (0, 30), "lu": (0, 5),
    }

    def validate_sample(self, sample_dict: Dict[str, Any]) -> List[ValidationResult]:
        """对单个样本进行全面验证。

        Args:
            sample_dict: 样本字典 (to_flat_dict() 输出)
        Returns:
            ValidationResult 列表
        """
        results = []

        # 1. 主量元素范围校验
        for field, (lo, hi) in self.MAJOR_RANGES.items():
            val = sample_dict.get(field) or sample_dict.get(field.upper())
            if val is not None:
                if val < lo or val > hi:
                    results.append(ValidationResult(
                        is_valid=False,
                        field_name=field,
                        message=f"{field}={val} 超出合理范围 {lo}-{hi}",
                        severity="error",
                        expected_range=(lo, hi),
                        actual_value=val,
                    ))
                elif val < lo * 1.2 or val > hi * 0.8:
                    results.append(ValidationResult(
                        is_valid=False,
                        field_name=field,
                        message=f"{field}={val} 接近边界 {lo}-{hi}",
                        severity="warning",
                        expected_range=(lo, hi),
                        actual_value=val,
                    ))

        # 2. 总量校验
        total = sample_dict.get("total") or sample_dict.get("Total")
        if total is not None:
            if total < 85 or total > 110:
                results.append(ValidationResult(
                    is_valid=False,
                    field_name="total",
                    message=f"主量元素总和={total} 异常 (正常 98-102%)",
                    severity="warning",
                    actual_value=total,
                ))
        else:
            # 计算理论Total
            calc_total = 0.0
            for field in ["sio2", "tio2", "al2o3", "fe2o3", "feo",
                           "mno", "mgo", "cao", "na2o", "k2o", "p2o5"]:
                v = sample_dict.get(field) or sample_dict.get(field.upper())
                if v is not None and v > 0:
                    calc_total += v
            loi = sample_dict.get("loi") or sample_dict.get("L.O.I") or 0
            calc_total += loi if loi else 0
            if calc_total > 0:
                if calc_total < 90 or calc_total > 108:
                    results.append(ValidationResult(
                        is_valid=False,
                        field_name="total",
                        message=f"计算总和={calc_total:.1f} 异常",
                        severity="warning",
                        actual_value=calc_total,
                    ))

        # 3. REE 平滑性校验
        ree_fields = ["la", "ce", "pr", "nd", "sm", "eu",
                       "gd", "tb", "dy", "ho", "er", "tm", "yb", "lu"]
        ree_values = {}
        for f in ree_fields:
            v = sample_dict.get(f) or sample_dict.get(f.capitalize())
            if v is not None and v > 0:
                ree_values[f] = v

        if len(ree_values) >= 6:
            # 检查 Oddo-Harkins 效应 (奇数原子序数REE应低于相邻偶数)
            pairs = [
                ("la", "ce"), ("pr", "nd"), ("sm", "eu"),
                ("gd", "tb"), ("dy", "ho"), ("er", "tm"),
                ("yb", "lu"),
            ]
            violations = 0
            for low, high in pairs:
                if low in ree_values and high in ree_values:
                    if ree_values[low] > ree_values[high]:
                        violations += 1
            if violations >= 4:
                results.append(ValidationResult(
                    is_valid=False,
                    field_name="REE",
                    message=f"REE配分模式异常: {violations}/7对违反Oddo-Harkins效应",
                    severity="warning",
                ))

        # 4. 交叉元素一致性
        # Th/U 比值应在合理范围 (1-10)
        th = sample_dict.get("th") or sample_dict.get("Th")
        u_val = sample_dict.get("u") or sample_dict.get("U")
        if th is not None and u_val is not None and u_val > 0:
            th_u = th / u_val
            if th_u < 0.1 or th_u > 50:
                results.append(ValidationResult(
                    is_valid=False,
                    field_name="Th/U",
                    message=f"Th/U={th_u:.1f} 异常 (正常 1-10)",
                    severity="warning",
                    actual_value=th_u,
                ))

        # CaO 与 LOI 正相关检查
        cao = sample_dict.get("cao") or sample_dict.get("CaO")
        loi = sample_dict.get("loi") or sample_dict.get("L.O.I")
        if cao is not None and loi is not None:
            if cao > 5 and loi < 0.5 and cao < 15:
                results.append(ValidationResult(
                    is_valid=False,
                    field_name="CaO-LOI",
                    message=f"高CaO={cao}但低LOI={loi}，可能存在碳酸盐化",
                    severity="info",
                ))

        return results

    def validate_batch(self, samples: list) -> Dict[str, List[ValidationResult]]:
        """批量验证。

        Returns:
            {sample_id: [ValidationResult, ...]}
        """
        results = {}
        for i, sample in enumerate(samples):
            if hasattr(sample, 'to_flat_dict'):
                sample_dict = sample.to_flat_dict()
            else:
                sample_dict = sample

            sample_key = sample_dict.get("Sample.No") or f"sample_{i}"
            results[str(sample_key)] = self.validate_sample(sample_dict)

        # 汇总统计
        total_errors = sum(1 for v in results.values() for r in v if r.severity == "error")
        total_warnings = sum(1 for v in results.values() for r in v if r.severity == "warning")
        logger.info(f"批量验证完成: {len(results)} 样本, {total_errors} 错误, {total_warnings} 警告")

        return results
