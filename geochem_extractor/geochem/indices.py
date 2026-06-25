"""地球化学指数计算模块。

用于花岗岩分类的关键地球化学指数:
- ASI (铝饱和指数): molar Al₂O₃/(CaO+Na₂O+K₂O)
- FeMgI (铁镁指数): molar FeOt/(FeOt+MgO)
- Ga/Al 比率: Ga/Al × 10⁴
- MALI (碱钙指数): Na₂O+K₂O-CaO (wt%)
- TZr (锆石饱和温度): Watson & Harrison (1983)
"""

import math
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class GeochemIndices:
    """地球化学指数结果。"""
    asi: Optional[float] = None           # 铝饱和指数
    femgi: Optional[float] = None         # 铁镁指数
    ga_al_ratio: Optional[float] = None   # Ga/Al × 10⁴
    mali: Optional[float] = None          # 碱钙指数
    t_zr: Optional[float] = None          # 锆石饱和温度 (°C)
    a_cnk: Optional[float] = None         # A/CNK (同ASI)
    a_nk: Optional[float] = None          # A/NK
    k2o_na2o: Optional[float] = None     # K₂O/Na₂O
    feot: Optional[float] = None          # 总Fe换算
    si_k_classification: str = ""         # 高钾钙碱性系列分类


class IndexCalculator:
    """地球化学指数计算器。

    所有输入值需为 wt% (主量元素) 和 ppm (微量元素)。
    """

    # 摩尔质量 (g/mol)
    MOLAR_MASS = {
        "sio2": 60.08, "tio2": 79.87, "al2o3": 101.96,
        "fe2o3": 159.69, "feo": 71.84, "mno": 70.94,
        "mgo": 40.30, "cao": 56.08, "na2o": 61.98,
        "k2o": 94.20, "p2o5": 141.94,
        "ga": 69.72, "al": 26.98, "zr": 91.22,
        "si": 28.09,
    }

    @staticmethod
    def calc_asi(al2o3: float, cao: float, na2o: float, k2o: float) -> Optional[float]:
        """计算铝饱和指数 ASI = Al₂O₃/(CaO+Na₂O+K₂O) (摩尔比)。

        判别:
          ASI < 1.0 → 准铝质 (metaluminous) → I型
          ASI > 1.1 → 过铝质 (peraluminous) → S型
          1.0 < ASI < 1.1 → 过渡
        """
        if not all(v is not None and v > 0 for v in [al2o3, cao, na2o, k2o]):
            return None

        try:
            mol_al2o3 = al2o3 / IndexCalculator.MOLAR_MASS["al2o3"]
            mol_cao = cao / IndexCalculator.MOLAR_MASS["cao"]
            mol_na2o = na2o / IndexCalculator.MOLAR_MASS["na2o"]
            mol_k2o = k2o / IndexCalculator.MOLAR_MASS["k2o"]

            denominator = mol_cao + mol_na2o + mol_k2o
            if denominator == 0:
                return None

            return mol_al2o3 / denominator
        except (ZeroDivisionError, TypeError):
            return None

    @staticmethod
    def calc_a_cnk(al2o3: float, cao: float, na2o: float, k2o: float) -> Optional[float]:
        """A/CNK = 同 ASI。"""
        return IndexCalculator.calc_asi(al2o3, cao, na2o, k2o)

    @staticmethod
    def calc_a_nk(al2o3: float, na2o: float, k2o: float) -> Optional[float]:
        """A/NK = Al₂O₃/(Na₂O+K₂O) (摩尔比)。"""
        if not all(v is not None and v > 0 for v in [al2o3, na2o, k2o]):
            return None
        try:
            mol_al2o3 = al2o3 / IndexCalculator.MOLAR_MASS["al2o3"]
            mol_na2o = na2o / IndexCalculator.MOLAR_MASS["na2o"]
            mol_k2o = k2o / IndexCalculator.MOLAR_MASS["k2o"]
            denominator = mol_na2o + mol_k2o
            if denominator == 0:
                return None
            return mol_al2o3 / denominator
        except (ZeroDivisionError, TypeError):
            return None

    @staticmethod
    def calc_femgi(feot: float, mgo: float) -> Optional[float]:
        """计算铁镁指数 FeOt/(FeOt+MgO) (wt%)。

        需要先通过 _calc_feot() 将 Fe₂O₃ 换算为 FeOt。
        判别:
          高FeMgI (>0.85) + Ga/Al > 2.6 → A型特征
        """
        if not all(v is not None and v > 0 for v in [feot, mgo]):
            return None
        denominator = feot + mgo
        if denominator == 0:
            return None
        return feot / denominator

    @staticmethod
    def _calc_feot(fe2o3: Optional[float], feo: Optional[float]) -> Optional[float]:
        """将Fe₂O₃和FeO统一换算为FeOt (总铁以FeO形式)。

        换算: Fe₂O₃ → FeO = Fe₂O₃ × 0.8998
        """
        total = 0.0
        has_data = False
        if fe2o3 is not None and fe2o3 > 0:
            total += fe2o3 * 0.8998
            has_data = True
        if feo is not None and feo > 0:
            total += feo
            has_data = True
        return total if has_data else None

    @staticmethod
    def calc_ga_al(ga_ppm: float, al2o3_wt: float) -> Optional[float]:
        """计算 Ga/Al × 10⁴ 比率。

        Ga 输入为 ppm，Al₂O₃ 为 wt%。
        需要先将 Ga(ppm) 换算为 Ga(ppm)中的Ga元素质量，
        再将 Al₂O₃(wt%) 换算为 Al 元素含量 (wt%)
        最后比值 × 10⁴。

        判别:
          Ga/Al×10⁴ > 2.6 → 可能为A型
        """
        if not all(v is not None and v > 0 for v in [ga_ppm, al2o3_wt]):
            return None

        try:
            # Al₂O₃(wt%) → Al(wt%)
            al_wt = al2o3_wt * (2 * IndexCalculator.MOLAR_MASS["al"] / IndexCalculator.MOLAR_MASS["al2o3"])

            # Ga(ppm) → Ga(ppm中的wt%即 1ppm = 0.0001 wt%)
            ga_wt = ga_ppm * 0.0001

            if al_wt == 0:
                return None

            return (ga_wt / al_wt) * 10000
        except (ZeroDivisionError, TypeError):
            return None

    @staticmethod
    def calc_mali(na2o: float, k2o: float, cao: float) -> Optional[float]:
        """计算碱钙指数 MALI = Na₂O + K₂O - CaO (wt%)。

        用于区分钙碱性/碱钙性/碱性系列。
        """
        if not all(v is not None for v in [na2o, k2o, cao]):
            return None
        return na2o + k2o - cao

    @staticmethod
    def calc_t_zr(zr_ppm: float, m: float = 1.3) -> Optional[float]:
        """计算锆石饱和温度 TZr (°C)。

        Watson & Harrison (1983):
          TZr = 12900 / (ln(DZr) + 0.85*M + 2.95) - 273.15

        M = (Na+K+2Ca)/(Al×Si) (阳离子比率)
        DZr = Zr(ppm) / 锆石中Zr含量(496000 ppm) ≈ Zr_ppm / 496000

        简化公式 (Miller et al., 2003):
          TZr = 12900 / (2.95 + 0.85*M + ln(496000/Zr_ppm)) - 273.15

        判别:
          TZr > 800°C → 高温花岗岩 (可能A型/高分异I型)
          TZr < 800°C → 低温花岗岩 (S型或普通I型)
        """
        if zr_ppm is None or zr_ppm <= 0 or m is None:
            return None

        try:
            dzr = 496000 / zr_ppm
            denominator = 2.95 + 0.85 * m + math.log(dzr)
            if denominator == 0:
                return None
            return 12900 / denominator - 273.15
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    @staticmethod
    def calc_m_value(sio2: float, al2o3: float, fe2o3: float, feo: float,
                     mgo: float, cao: float, na2o: float, k2o: float) -> Optional[float]:
        """计算 M 值 (阳离子比率参数)，用于 TZr 计算。

        M = (Na + K + 2Ca) / (Al × Si)  阳离子比率
        """
        if not all(v is not None and v > 0 for v in [sio2, al2o3]):
            return None

        try:
            # 各氧化物 → 阳离子摩尔数
            mol_na = (na2o or 0) * 2 / IndexCalculator.MOLAR_MASS["na2o"]
            mol_k = (k2o or 0) * 2 / IndexCalculator.MOLAR_MASS["k2o"]
            mol_ca = (cao or 0) / IndexCalculator.MOLAR_MASS["cao"]
            mol_al = (al2o3 or 0) * 2 / IndexCalculator.MOLAR_MASS["al2o3"]
            mol_si = (sio2 or 0) / IndexCalculator.MOLAR_MASS["sio2"]

            numerator = mol_na + mol_k + 2 * mol_ca
            denominator = mol_al * mol_si

            if denominator == 0:
                return None

            return numerator / denominator
        except (ZeroDivisionError, TypeError):
            return None

    def calculate_all(self,
                      sio2: Optional[float], tio2: Optional[float],
                      al2o3: Optional[float], fe2o3: Optional[float],
                      feo: Optional[float], mno: Optional[float],
                      mgo: Optional[float], cao: Optional[float],
                      na2o: Optional[float], k2o: Optional[float],
                      p2o5: Optional[float],
                      ga_ppm: Optional[float] = None,
                      zr_ppm: Optional[float] = None) -> GeochemIndices:
        """一次性计算所有相关地球化学指数。

        Args:
            主量元素 (wt%), Ga(ppm), Zr(ppm)
        Returns:
            GeochemIndices 对象
        """
        result = GeochemIndices()

        # FeOt 换算
        feot = self._calc_feot(fe2o3, feo)
        result.feot = feot

        # ASI / A/CNK
        if all(v is not None for v in [al2o3, cao, na2o, k2o]):
            result.asi = self.calc_asi(al2o3, cao, na2o, k2o)
            result.a_cnk = result.asi
            result.a_nk = self.calc_a_nk(al2o3, na2o, k2o)

        # FeMgI
        if feot is not None and mgo is not None:
            result.femgi = self.calc_femgi(feot, mgo)

        # Ga/Al
        if ga_ppm is not None and al2o3 is not None:
            result.ga_al_ratio = self.calc_ga_al(ga_ppm, al2o3)

        # MALI
        if all(v is not None for v in [na2o, k2o, cao]):
            result.mali = self.calc_mali(na2o, k2o, cao)

        # K₂O/Na₂O
        if k2o is not None and na2o is not None and na2o > 0:
            result.k2o_na2o = k2o / na2o

        # TZr
        if zr_ppm is not None and all(v is not None for v in [sio2, al2o3, cao, na2o, k2o]):
            m_val = self.calc_m_value(sio2, al2o3, fe2o3, feo, mgo, cao, na2o, k2o)
            if m_val is not None:
                result.t_zr = self.calc_t_zr(zr_ppm, m_val)

        # SiO₂-K₂O 分类系列
        if sio2 is not None and k2o is not None:
            if 48 <= sio2 <= 80:
                if sio2 < 52:
                    expected = 0.4
                elif sio2 < 57:
                    expected = 0.7
                elif sio2 < 63:
                    expected = 1.4
                elif sio2 < 70:
                    expected = 2.5
                else:
                    expected = 3.5

                if k2o > expected * 1.5:
                    result.si_k_classification = "钾玄岩系列"
                elif k2o > expected:
                    result.si_k_classification = "高钾钙碱性系列"
                elif k2o > expected * 0.5:
                    result.si_k_classification = "中钾钙碱性系列"
                else:
                    result.si_k_classification = "低钾拉斑系列"

        return result
