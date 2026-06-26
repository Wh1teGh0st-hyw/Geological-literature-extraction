"""单位转换器 — 地球化学数据的单位检测与转换。

功能:
- ppm ↔ wt% 转换（针对特定元素）
- Fe2O3 ↔ FeO 换算
- 百分号自动检测
- 主量元素总量标准化
"""

from typing import Optional, Dict, Any
from loguru import logger


class UnitConverter:
    """单位检测与转换器。"""

    FE2O3_TO_FEO = 0.8998
    FEO_TO_FE2O3 = 1.1113

    # 主量元素标准单位（wt%）范围
    MAJOR_WT_RANGES: Dict[str, tuple] = {
        "sio2": (30, 85), "tio2": (0, 5), "al2o3": (5, 40),
        "fe2o3": (0, 20), "feo": (0, 20), "mno": (0, 5),
        "mgo": (0, 25), "cao": (0, 25), "na2o": (0, 15),
        "k2o": (0, 15), "p2o5": (0, 5), "loi": (-5, 20),
        "total": (85, 110),
    }

    # 微量元素标准单位（ppm）范围
    TRACE_PPM_RANGES: Dict[str, tuple] = {
        "li": (0, 10000), "be": (0, 500), "sc": (0, 100),
        "v": (0, 500), "cr": (0, 2000), "co": (0, 200),
        "ni": (0, 2000), "cu": (0, 500), "zn": (0, 500),
        "ga": (0, 50), "rb": (0, 2000), "sr": (0, 2000),
        "y": (0, 200), "zr": (0, 1000), "nb": (0, 200),
        "cs": (0, 100), "ba": (0, 3000), "hf": (0, 50),
        "ta": (0, 20), "pb": (0, 200), "th": (0, 100),
        "u": (0, 50), "w": (0, 200), "sn": (0, 100), "mo": (0, 20),
    }

    # REE 标准范围 (ppm)
    REE_PPM_RANGES: Dict[str, tuple] = {
        "la": (0, 500), "ce": (0, 1000), "pr": (0, 100),
        "nd": (0, 500), "sm": (0, 100), "eu": (0, 20),
        "gd": (0, 50), "tb": (0, 10), "dy": (0, 50),
        "ho": (0, 10), "er": (0, 30), "tm": (0, 5),
        "yb": (0, 30), "lu": (0, 5),
    }

    def detect_and_convert(self, field_name: str, value: float,
                           original_text: str = "") -> Optional[float]:
        """根据字段名自动检测并转换单位。"""
        if value is None:
            return None

        category = self._get_category(field_name)

        # 主量元素：检查是否误写为 ppm
        if category == "major":
            ranges = self.MAJOR_WT_RANGES.get(field_name, (0, 110))
            if value > ranges[1] * 2:
                converted = value / 10000
                if ranges[0] <= converted <= ranges[1]:
                    logger.debug(f"{field_name}: {value} → {converted} (ppm→wt%)")
                    return converted

        # 微量元素/REE：检查是否误写为 wt%
        if category in ("trace", "ree"):
            if field_name in self.TRACE_PPM_RANGES:
                ranges = self.TRACE_PPM_RANGES[field_name]
            elif field_name in self.REE_PPM_RANGES:
                ranges = self.REE_PPM_RANGES[field_name]
            else:
                ranges = (0, 2000)

            if 0 < value <= 1.0:
                possible_ppm = value * 10000
                if ranges[0] <= possible_ppm <= ranges[1]:
                    logger.debug(f"{field_name}: {value} → {possible_ppm} (wt%→ppm)")
                    return possible_ppm

        return value

    def convert_fe2o3_to_feo(self, fe2o3: Optional[float]) -> Optional[float]:
        """Fe2O3 → FeO 换算。"""
        if fe2o3 is None:
            return None
        return fe2o3 * self.FE2O3_TO_FEO

    def convert_feo_to_fe2o3(self, feo: Optional[float]) -> Optional[float]:
        """FeO → Fe2O3 换算。"""
        if feo is None:
            return None
        return feo * self.FEO_TO_FE2O3

    def _get_category(self, field_name: str) -> Optional[str]:
        """根据字段名推断分类。"""
        major_fields = {"sio2", "tio2", "al2o3", "fe2o3", "feo", "mno",
                        "mgo", "cao", "na2o", "k2o", "p2o5", "loi", "total"}
        trace_fields = {"li", "be", "sc", "v", "cr", "co", "ni", "cu", "zn", "ga",
                        "rb", "sr", "y", "zr", "nb", "cs", "ba", "hf", "ta",
                        "pb", "th", "u", "w", "sn", "mo"}
        ree_fields = {"la", "ce", "pr", "nd", "sm", "eu", "gd", "tb",
                       "dy", "ho", "er", "tm", "yb", "lu"}
        if field_name in major_fields:
            return "major"
        if field_name in trace_fields:
            return "trace"
        if field_name in ree_fields:
            return "ree"
        return None

    def normalize_total(self, major_values: Dict[str, Any]) -> Optional[float]:
        """尝试从已有主量元素计算总和。"""
        total = major_values.get("total")
        if total is not None:
            return total
        total = 0.0
        for field in ["sio2", "tio2", "al2o3", "fe2o3", "feo", "mno",
                       "mgo", "cao", "na2o", "k2o", "p2o5", "loi"]:
            v = major_values.get(field)
            if v is not None and v > 0:
                total += v
        return total if total > 0 else None
