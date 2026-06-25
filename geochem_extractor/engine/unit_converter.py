"""单位转换器 — 地球化学数据的单位检测与转换。

功能:
- ppm ↔ wt% 转换（针对特定元素）
- Fe2O3 ↔ FeO 换算
- 百分号自动检测
- 主量元素总量标准化（检测是否列轴/行轴）
"""

from typing import Optional
from loguru import logger


class UnitConverter:
    """单位检测与转换器。"""

    # Fe2O3 / FeO 换算系数
    # Fe2O3 → FeO: × 0.8998
    # FeO → Fe2O3: × 1.1113
    FE2O3_TO_FEO = 0.8998
    FEO_TO_FE2O3 = 1.1113

    # 元素 → 氧化物换算系数
    ELEMENT_TO_OXIDE = {
        # 主量
        "si_sio2": 2.1393,   # Si → SiO2
        "ti_tio2": 1.6680,   # Ti → TiO2
        "al_al2o3": 1.8895,  # Al → Al2O3
        "fe_fe2o3": 1.4297,  # Fe → Fe2O3 (总铁)
        "fe_feo": 1.2865,    # Fe → FeO
        "mn_mno": 1.2912,    # Mn → MnO
        "mg_mgo": 1.6583,    # Mg → MgO
        "ca_cao": 1.3992,    # Ca → CaO
        "na_na2o": 1.3480,   # Na → Na2O
        "k_k2o": 1.2046,     # K → K2O
        "p_p2o5": 2.2914,    # P → P2O5
    }

    # 主量元素标准单位（wt%）范围
    MAJOR_WT_RANGES = {
        "sio2": (30, 85),
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

    # 微量元素标准单位（ppm）范围
    TRACE_PPM_RANGES = {
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
    REE_PPM_RANGES = {
        "la": (0, 500), "ce": (0, 1000), "pr": (0, 100),
        "nd": (0, 500), "sm": (0, 100), "eu": (0, 20),
        "gd": (0, 50), "tb": (0, 10), "dy": (0, 50),
        "ho": (0, 10), "er": (0, 30), "tm": (0, 5),
        "yb": (0, 30), "lu": (0, 5),
    }

    def detect_and_convert(self, field_name: str, value: float,
                           original_text: str = "") -> float:
        """根据字段名自动检测并转换单位。

        Args:
            field_name: 规范字段名（如 "sio2", "li", "na2o"）
            value: 清洗后的数值
            original_text: 原始文本（用于检测%符号等）
        Returns:
            转换后的数值
        """
        if value is None:
            return None

        category = self._get_category(field_name)

        # 主量元素：检查是否误写为 ppm（值 > 100%）
        if category == "major":
            ranges = self.MAJOR_WT_RANGES.get(field_name, (0, 110))
            if value > ranges[1] * 2:
                # 可能写了 ppm 而非 wt%
                # ppm → wt%: / 10000
                converted = value / 10000
                if ranges[0] <= converted <= ranges[1]:
                    logger.debug(f"{field_name}: {value} 疑似 ppm → wt% 转换为 {converted}")
                    return converted

        # 微量元素/REE：检查是否误写为 wt%
        if category in ("trace", "ree"):
            if field_name in self.TRACE_PPM_RANGES:
                ranges = self.TRACE_PPM_RANGES[field_name]
            elif field_name in self.REE_PPM_RANGES:
                ranges = self.REE_PPM_RANGES[field_name]
            else:
                ranges = (0, 2000)

            if value <= 1.0 and value > 0:
                # 微量元素 < 1 ppm 是可能的（但罕见）
                # 检查是否是 wt%（值 * 10000 = 合理的 ppm 值）
                possible_ppm = value * 10000
                if ranges[0] <= possible_ppm <= ranges[1]:
                    logger.debug(f"{field_name}: {value} 疑似 wt% → ppm 转换为 {possible_ppm}")
                    return possible_ppm

        return value

    def convert_fe2o3_to_feo(self, fe2o3: float) -> float:
        """Fe2O3 → FeO 换算。"""
        return fe2o3 * self.FE2O3_TO_FEO if fe2o3 is not None else None

    def convert_feo_to_fe2o3(self, feo: float) -> float:
        """FeO → Fe2O3 换算。"""
        return feo * self.FEO_TO_FE2O3 if feo is not None else None

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

    def normalize_total(self, major_values: dict) -> Optional[float]:
        """尝试标准化主量元素总和。

        如果未提供 Total 值，从已有主量元素计算。
        """
        total = major_values.get("total")
        if total is not None:
            return total

        # 从已有氧化物求和
        total = 0.0
        for field in ["sio2", "tio2", "al2o3", "fe2o3", "feo", "mno",
                       "mgo", "cao", "na2o", "k2o", "p2o5", "loi"]:
            v = major_values.get(field)
            if v is not None and v > 0:
                total += v
        return total if total > 0 else None
