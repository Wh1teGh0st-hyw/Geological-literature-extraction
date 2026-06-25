"""元素/氧化物列识别引擎。

读取提取表格的表头和数据，匹配到94列目标字段。
支持:
- 中文别名（二氧化硅 / 硅 / SiO2 / SiO₂）
- 英文别名（Silica / Si / silicon dioxide）
- OCR 纠错（Si02 → SiO2, A1203 → Al2O3）
- 模糊匹配（编辑距离 < 2）
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from loguru import logger


# ── 94列目标定义 ──────────────────────────────────────

# 格式: (规范名, [别名列表], 分类)
TARGET_COLUMNS = [
    # 身份信息
    ("mining_area",     ["矿区", "采样区", "地区", "Location", "Area", "Mining area"], "identity"),
    ("rock_body",       ["岩体", "岩株", "深成岩体", "Pluton", "Rock body", "Intrusion"], "identity"),
    ("data_source",     ["Data source", "数据来源", "资料来源", "Source", "Reference", "文献"], "identity"),
    ("sample_no",       ["Sample.No", "样品号", "样品编号", "样号", "Sample", "Sample ID", "No."], "identity"),
    ("granite_type",    ["Granite type", "花岗岩类型", "类型", "Type", "岩石成因类型"], "identity"),
    ("rock_type",       ["Rock type", "岩石类型", "岩性", "Lithology", "岩相"], "identity"),

    # 年代学
    ("formation_age",   ["成岩年龄", "Age(Ma)", "年龄", "U-Pb年龄", "锆石年龄", "Formation age", "t(Ma)", "Age"], "chronology"),
    ("age_error",       ["error", "误差", "2σ", "±", "±1σ", "Error"], "chronology"),
    ("age_method",      ["Method", "方法", "测年方法", "Dating method"], "chronology"),
    ("mineralization_age", ["成矿年龄", "矿化年龄", "Mineralization age"], "chronology"),
    ("min_age_error",   ["成矿error", "成矿误差"], "chronology"),
    ("min_age_method",  ["成矿Method", "成矿方法"], "chronology"),

    # 空间
    ("longitude",       ["X", "Longitude", "经度", "东经", "E", "lon"], "spatial"),
    ("latitude",        ["纬度", "Latitude", "北纬", "N", "lat"], "spatial"),
    ("elevation",       ["Hight", "海拔", "高程", "Elevation", "Alt", "m"], "spatial"),

    # 主量元素 (wt%)
    ("sio2",  ["SiO2", "SiO₂", "二氧化硅", "Si02", "Sio2", "SiO2(wt%)", "SiO2%", "SiO₂(%)", "Silica"], "major"),
    ("tio2",  ["TiO2", "TiO₂", "二氧化钛", "Ti02", "Titanium"], "major"),
    ("al2o3", ["Al2O3", "Al₂O₃", "Al2O₃", "三氧化二铝", "氧化铝", "A1203", "Al2O3%", "Aluminum"], "major"),
    ("fe2o3", ["Fe2O3", "Fe₂O₃", "三氧化二铁", "Fe2O₃", "Fe2O3T", "Fe₂O₃T", "TFe₂O₃", "TFe2O3", "总铁", "全铁"], "major"),
    ("feo",   ["FeO", "氧化亚铁", "FeO(T)", "FeOt"], "major"),
    ("mno",   ["MnO", "氧化锰", "Mn0", "Manganese"], "major"),
    ("mgo",   ["MgO", "氧化镁", "Mg0", "Magnesium"], "major"),
    ("cao",   ["CaO", "氧化钙", "Ca0", "Calcium"], "major"),
    ("na2o",  ["Na2O", "Na₂O", "氧化钠", "Na2O%", "Sodium"], "major"),
    ("k2o",   ["K2O", "K₂O", "氧化钾", "K2O%", "Potassium"], "major"),
    ("p2o5",  ["P2O5", "P₂O₅", "五氧化二磷", "P2O5%", "Phosphorus"], "major"),
    ("loi",   ["L.O.I", "LOI", "烧失量", "烧失", "Loss on ignition", "L.O.I."], "major"),
    ("total", ["Total", "总和", "总量", "Sum"], "major"),

    # 微量元素 (ppm)
    ("li", ["Li", "锂", "Li(ppm)", "Lithium"], "trace"),
    ("be", ["Be", "铍", "Beryllium"], "trace"),
    ("sc", ["Sc", "钪", "Scandium"], "trace"),
    ("v",  ["V", "钒", "Vanadium"], "trace"),
    ("cr", ["Cr", "铬", "Chromium"], "trace"),
    ("co", ["Co", "钴", "Cobalt"], "trace"),
    ("ni", ["Ni", "镍", "Nickel"], "trace"),
    ("cu", ["Cu", "铜", "Copper"], "trace"),
    ("zn", ["Zn", "锌", "Zinc"], "trace"),
    ("ga", ["Ga", "镓", "Gallium"], "trace"),
    ("rb", ["Rb", "铷", "Rubidium"], "trace"),
    ("sr", ["Sr", "锶", "Strontium"], "trace"),
    ("y",  ["Y", "钇", "Yttrium", "Y element"], "trace"),
    ("zr", ["Zr", "锆", "Zirconium"], "trace"),
    ("nb", ["Nb", "铌", "Niobium"], "trace"),
    ("cs", ["Cs", "铯", "Cesium", "Caesium"], "trace"),
    ("ba", ["Ba", "钡", "Barium"], "trace"),
    ("hf", ["Hf", "铪", "Hafnium"], "trace"),
    ("ta", ["Ta", "钽", "Tantalum"], "trace"),
    ("pb", ["Pb", "铅", "Lead"], "trace"),
    ("th", ["Th", "钍", "Thorium"], "trace"),
    ("u",  ["U", "铀", "Uranium"], "trace"),
    ("w",  ["W", "钨", "Tungsten", "Wolfram"], "trace"),
    ("sn", ["Sn", "锡", "Tin"], "trace"),
    ("mo", ["Mo", "钼", "Molybdenum"], "trace"),

    # 稀土元素 REE (ppm)
    ("la", ["La", "镧", "Lanthanum"], "ree"),
    ("ce", ["Ce", "铈", "Cerium"], "ree"),
    ("pr", ["Pr", "镨", "Praseodymium"], "ree"),
    ("nd", ["Nd", "钕", "Neodymium"], "ree"),
    ("sm", ["Sm", "钐", "Samarium"], "ree"),
    ("eu", ["Eu", "铕", "Europium"], "ree"),
    ("gd", ["Gd", "钆", "Gadolinium"], "ree"),
    ("tb", ["Tb", "铽", "Terbium"], "ree"),
    ("dy", ["Dy", "镝", "Dysprosium"], "ree"),
    ("ho", ["Ho", "钬", "Holmium"], "ree"),
    ("er", ["Er", "铒", "Erbium"], "ree"),
    ("tm", ["Tm", "铥", "Thulium"], "ree"),
    ("yb", ["Yb", "镱", "Ytterbium"], "ree"),
    ("lu", ["Lu", "镥", "Lutetium"], "ree"),

    # 同位素
    ("sr87_sr86_i",     ["87Sr/86Sr", "87Sr/86Sr(i)", "ISr(t)", "(87Sr/86Sr)i", "87Sr/⁸⁶Sr", "Initial 87Sr/86Sr"], "isotope"),
    ("sr87_sr86_err",   ["87Sr/86Sr_err", "2σ(Sr)", "±87Sr/86Sr"], "isotope"),
    ("nd143_nd144_i",   ["143Nd/144Nd", "143Nd/144Nd(i)", "(143Nd/144Nd)i", "¹⁴³Nd/¹⁴⁴Nd"], "isotope"),
    ("nd143_nd144_err", ["143Nd/144Nd_err", "2σ(Nd)"], "isotope"),
    ("epsilon_nd_t",    ["εNd(t)", "eNd(t)", "εNd", "epsilon Nd", "epsilon_Nd", "ɛNd(t)"], "isotope"),
    ("epsilon_nd_err",  ["εNd_err", "2σ(εNd)"], "isotope"),
    ("t_dm2_nd",        ["TDM2(Nd)", "T2DM", "TDM2", "tDM2", "T_DM2", "Nd TDM2"], "isotope"),
    ("t_dm1_nd",        ["TDM1(Nd)", "TDM", "T1DM", "tDM", "T_DM"], "isotope"),
    ("hf176_hf177_i",   ["176Hf/177Hf", "176Hf/177Hf(i)", "(176Hf/177Hf)i", "176Hf/¹⁷⁷Hf"], "isotope"),
    ("hf176_hf177_err", ["176Hf/177Hf_err", "2σ(Hf)"], "isotope"),
    ("epsilon_hf_t",    ["εHf(t)", "eHf(t)", "εHf", "epsilon Hf", "ɛHf(t)"], "isotope"),
    ("epsilon_hf_err",  ["εHf_err", "2σ(εHf)"], "isotope"),
    ("t_dm2_hf",        ["TDM2(Hf)", "TDM2 Hf", "Hf TDM2", "tDM2(Hf)"], "isotope"),
    ("t_dm1_hf",        ["TDM1(Hf)", "TDM Hf", "Hf TDM"], "isotope"),
]


class ElementIdentifier:
    """元素/氧化物列识别器。"""

    # OCR 常见错误纠正表
    OCR_CORRECTIONS = {
        "si02": "SiO2", "si0z": "SiO2", "sio₂": "SiO2",
        "al20": "Al2O", "a1203": "Al2O3", "al₂o₃": "Al2O3",
        "feo": "FeO", "fe₂o₃": "Fe2O3", "fe203": "Fe2O3",
        "mn0": "MnO", "mg0": "MgO", "ca0": "CaO",
        "na20": "Na2O", "k20": "K2O", "na2o": "Na2O", "p205": "P2O5",
        "ti02": "TiO2", "a1203": "Al2O3",
    }

    def __init__(self):
        # 构建查找表: 别名 → (规范名, 分类)
        self._alias_map: Dict[str, Tuple[str, str]] = {}
        self._build_alias_map()

    def _build_alias_map(self):
        """构建别名查找表。"""
        for canonical, aliases, category in TARGET_COLUMNS:
            for alias in aliases:
                key = self._normalize(alias)
                if key not in self._alias_map:
                    self._alias_map[key] = (canonical, category)
                # 也添加 OCR 纠错版本
                corrected = self._ocr_correct(key)
                if corrected != key and corrected not in self._alias_map:
                    self._alias_map[corrected] = (canonical, category)

    def _normalize(self, text: str) -> str:
        """规范化学符串：去除空白、转小写、统一括号。"""
        t = text.strip()
        t = re.sub(r"\s+", "", t)
        t = t.lower()
        # 统一 Unicode 下标
        t = t.replace("₂", "2").replace("₃", "3").replace("₅", "5")
        t = t.replace("⁸", "8").replace("⁷", "7").replace("⁶", "6").replace("⁴", "4")
        t = t.replace("¹", "1").replace("³", "3")
        # 统一括号
        t = t.replace("(", "").replace(")", "")
        t = t.replace("（", "").replace("）", "")
        t = t.replace("ₓ", "t")
        t = t.replace("₀", "0")
        return t.lower()

    def _ocr_correct(self, text: str) -> str:
        """OCR 常见错误纠正。"""
        t = text.lower()
        if t in self.OCR_CORRECTIONS:
            return self.OCR_CORRECTIONS[t]
        # 通用规则
        t = t.replace("0", "o")  # 可能反过来用 - 待定
        return text

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离。"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                cost = 0 if c1 == c2 else 1
                curr_row.append(min(
                    curr_row[j] + 1,
                    prev_row[j + 1] + 1,
                    prev_row[j] + cost,
                ))
            prev_row = curr_row
        return prev_row[-1]

    def identify_column(self, header_text: str) -> Optional[Tuple[str, str, float]]:
        """识别单个表头文本对应的目标字段。

        Args:
            header_text: 表头单元格文本
        Returns:
            (规范字段名, 分类, 置信度) 或 None
        """
        if not header_text or not header_text.strip():
            return None

        # 精确匹配
        key = self._normalize(header_text)
        if key in self._alias_map:
            canonical, category = self._alias_map[key]
            return (canonical, category, 1.0)

        # OCR纠错后匹配
        corrected = self._ocr_correct(key)
        if corrected in self._alias_map:
            canonical, category = self._alias_map[corrected]
            return (canonical, category, 0.9)

        # 子串匹配（表头可能包含额外词如 (wt%)、(ppm) 等）
        for alias_key, (canonical, category) in self._alias_map.items():
            if alias_key in key or key in alias_key:
                return (canonical, category, 0.85)

        # 模糊匹配（编辑距离 < 2）
        for alias_key, (canonical, category) in self._alias_map.items():
            if len(alias_key) >= 3 and len(key) >= 3:
                if self._levenshtein_distance(key, alias_key) <= 1:
                    return (canonical, category, 0.7)

        return None

    def identify_columns_batch(self, headers: List[str]) -> Dict[int, Tuple[str, str, float]]:
        """批量识别所有表头列。

        Args:
            headers: 表头文本列表
        Returns:
            {列索引: (规范字段名, 分类, 置信度)}
        """
        result = {}
        for idx, header in enumerate(headers):
            match = self.identify_column(str(header))
            if match:
                result[idx] = match
        return result

    def get_category(self, canonical_name: str) -> Optional[str]:
        """获取规范字段名的分类（major/trace/ree/isotope等）。"""
        for canonical, aliases, category in TARGET_COLUMNS:
            if canonical == canonical_name:
                return category
        return None
