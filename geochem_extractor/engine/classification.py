"""花岗岩类型自动分类引擎。

基于地球化学判别规则，自动判定 I型 / S型 / A型 / M型 花岗岩。
分类层级:
  1. A型判别: Ga/Al > 2.6 且 Zr > 250 且 FeMgI > 0.85
  2. M型判别: K₂O < 0.8 且 Na₂O > K₂O 且 SiO₂ > 63 (岛弧玄武质分异)
  3. S型判别: ASI > 1.1 (过铝质)
  4. I型判别: ASI < 1.0 (准铝质)
  5. 过渡区: ASI 1.0~1.1 综合判定

置信度: high / medium / low
"""

from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from loguru import logger

from geochem.indices import GeochemIndices


@dataclass
class ClassificationResult:
    """分类结果。"""
    granite_type: str = ""                       # "I-type" / "S-type" / "A-type" / "M-type"
    confidence: str = ""                          # "high" / "medium" / "low"
    subtype: str = ""                          # "SG" / "SC" (S型亚型) / "A1" / "A2"
    basis: list = None                         # 判定依据列表
    asi: Optional[float] = None
    femgi: Optional[float] = None
    ga_al_ratio: Optional[float] = None
    t_zr: Optional[float] = None


class ClassificationEngine:
    """花岗岩类型自动分类引擎。"""

    # ── 分类阈值常量 ──
    A_TYPE_GA_AL = 2.6               # Ga/Al×10⁴ 阈值
    A_TYPE_ZR = 250                  # Zr (ppm) 阈值
    A_TYPE_FEMGI = 0.85              # FeMgI 阈值
    S_TYPE_ASI = 1.1                 # ASI 上限
    I_TYPE_ASI = 1.0                 # ASI 下限
    M_TYPE_K2O = 0.8                 # K₂O 上限 (wt%)
    TRANSITIONAL_ASI_LOW = 1.0       # 过渡区下界
    TRANSITIONAL_ASI_HIGH = 1.1      # 过渡区上界

    def classify(self,
                 sio2: Optional[float],
                 al2o3: Optional[float],
                 fe2o3: Optional[float],
                 feo: Optional[float],
                 mgo: Optional[float],
                 cao: Optional[float],
                 na2o: Optional[float],
                 k2o: Optional[float],
                 p2o5: Optional[float] = None,
                 ga_ppm: Optional[float] = None,
                 zr_ppm: Optional[float] = None,
                 nb_ppm: Optional[float] = None,
                 y_ppm: Optional[float] = None,
                 ce_ppm: Optional[float] = None,
                 la_ppm: Optional[float] = None,
                 nd_ppm: Optional[float] = None,
                 manual_label: Optional[str] = None
                 ) -> ClassificationResult:
        """根据输入的地球化学数据自动判定花岗岩类型。

        主输入为 wt% 和 ppm，返回带置信度的分类结果。
        """
        from geochem.indices import IndexCalculator

        calc = IndexCalculator()
        indices = calc.calculate_all(
            sio2=sio2, tio2=None, al2o3=al2o3,
            fe2o3=fe2o3, feo=feo, mno=None,
            mgo=mgo, cao=cao, na2o=na2o, k2o=k2o,
            p2o5=p2o5, ga_ppm=ga_ppm, zr_ppm=zr_ppm,
        )

        result = ClassificationResult(
            asi=indices.asi,
            femgi=indices.femgi,
            ga_al_ratio=indices.ga_al_ratio,
            t_zr=indices.t_zr,
            basis=[],
        )

        # ── 优先级: 手动标签 > 自动判定 ──
        if manual_label:
            mapped = self._map_manual_label(manual_label)
            if mapped:
                result.granite_type = mapped
                result.confidence = "high"
                result.basis.append(f"手动标注: {manual_label}")
                return result

        # ── 步骤1: 检查数据充足性 ──
        required = [sio2, al2o3, cao, na2o, k2o]
        available = sum(1 for v in required if v is not None)
        if available < 4:
            result.granite_type = "未分类"
            result.confidence = "low"
            result.basis.append("数据不足")
            return result

        # ── 步骤2: A型判别 (Ga/Al优先) ──
        a_type_score = 0
        a_type_basis = []

        if indices.ga_al_ratio is not None and indices.ga_al_ratio > self.A_TYPE_GA_AL:
            a_type_score += 1
            a_type_basis.append(f"Ga/Al={indices.ga_al_ratio:.1f}>{self.A_TYPE_GA_AL}")

        if zr_ppm is not None and zr_ppm > self.A_TYPE_ZR:
            a_type_score += 1
            a_type_basis.append(f"Zr={zr_ppm:.0f}>{self.A_TYPE_ZR}")

        if indices.femgi is not None and indices.femgi > self.A_TYPE_FEMGI:
            a_type_score += 1
            a_type_basis.append(f"FeMgI={indices.femgi:.2f}>{self.A_TYPE_FEMGI}")

        if a_type_score >= 2:
            result.granite_type = "A-type"
            result.confidence = "high" if a_type_score >= 3 else "medium"
            result.basis = a_type_basis
            # 判断 A1/A2 亚型
            if nb_ppm is not None and y_ppm is not None:
                if nb_ppm > y_ppm * 2:
                    result.subtype = "A1"
                else:
                    result.subtype = "A2"
            return result

        # ── 步骤3: M型判别 ──
        if (sio2 is not None and sio2 > 63 and
            k2o is not None and k2o < self.M_TYPE_K2O and
            na2o is not None and k2o is not None and na2o > k2o):
            result.granite_type = "M-type"
            result.confidence = "medium"
            result.basis.append(f"低钾高钠: K₂O={k2o:.2f}<{self.M_TYPE_K2O}, Na₂O/K₂O>1")
            return result

        # ── 步骤4: S型判别 (过铝质) ──
        if indices.asi is not None and indices.asi > self.S_TYPE_ASI:
            result.granite_type = "S-type"
            result.basis.append(f"ASI={indices.asi:.2f}>{self.S_TYPE_ASI}")

            # S型亚型 (SG vs SC)
            if indices.femgi is not None:
                if indices.femgi > 0.8:
                    result.subtype = "SG"
                    result.basis.append(f"FeMgI={indices.femgi:.2f}>0.8 → SG亚型")
                else:
                    result.subtype = "SC"
                    result.basis.append(f"FeMgI={indices.femgi:.2f}≤0.8 → SC亚型")

            result.confidence = "high" if indices.a_cnk is not None and indices.a_cnk > 1.15 else "medium"
            return result

        # ── 步骤5: I型判别 (准铝质) ──
        if indices.asi is not None and indices.asi < self.I_TYPE_ASI:
            result.granite_type = "I-type"
            result.basis.append(f"ASI={indices.asi:.2f}<{self.I_TYPE_ASI}")

            # I型置信度
            if na2o is not None and na2o > 3.2:
                result.confidence = "high"
                result.basis.append("特征I型: Na₂O>3.2%")
            else:
                result.confidence = "medium"

            # 高分异I型检测 (SiO2高, Al2O3低)
            if sio2 is not None and sio2 > 70 and al2o3 is not None and al2o3 < 14:
                result.subtype = "HFI"
                result.basis.append("高分异特征: SiO₂>70%, Al₂O₃<14%")

            return result

        # ── 步骤6: 过渡区 (ASI 1.0~1.1) ──
        if indices.asi is not None and self.TRANSITIONAL_ASI_LOW <= indices.asi <= self.TRANSITIONAL_ASI_HIGH:
            # 综合 Na₂O、FeMgI 辅助判别
            if na2o is not None and na2o > 3.2:
                result.granite_type = "I-type"
                result.basis.append(f"过渡区 ASI={indices.asi:.2f}, 高Na₂O={na2o:.1f}% → I型")
                result.confidence = "low"
            elif indices.femgi is not None and indices.femgi > 0.8:
                result.granite_type = "S-type"
                result.basis.append(f"过渡区 ASI={indices.asi:.2f}, 高FeMgI={indices.femgi:.2f} → S型")
                result.confidence = "low"
            else:
                # 额外判别: 使用 A/NK 值
                if sio2 is not None and sio2 < 68:
                    result.granite_type = "I-type"
                else:
                    result.granite_type = "S-type"
                result.basis.append(f"过渡区 ASI={indices.asi:.2f}, 综合判定")
                result.confidence = "low"
            return result

        # ── 默认：无法分类 ──
        result.granite_type = "未分类"
        result.confidence = "low"
        result.basis.append("不满足任何分类条件")
        return result

    def _map_manual_label(self, label: str) -> Optional[str]:
        """将手动标注映射为标准分类名。"""
        label = label.strip().upper()
        mapping = {
            "I": "I-type", "I型": "I-type", "I-型": "I-type",
            "I TYPE": "I-type", "I型花岗岩": "I-type",
            "S": "S-type", "S型": "S-type", "S-型": "S-type",
            "S TYPE": "S-type", "S型花岗岩": "S-type",
            "A": "A-type", "A型": "A-type", "A-型": "A-type",
            "A TYPE": "A-type", "A型花岗岩": "A-type",
            "M": "M-type", "M型": "M-type",
            "高分异I型": "I-type",
        }
        for key, value in mapping.items():
            if key in label:
                return value
        return None

    def classify_sample(self, sample_dict: Dict[str, Any]) -> ClassificationResult:
        """从样本数据字典中分类。

        Args:
            sample_dict: 包含主量/微量元素的字典
        Returns:
            ClassificationResult
        """
        return self.classify(
            sio2=sample_dict.get("sio2") or sample_dict.get("SiO2"),
            al2o3=sample_dict.get("al2o3") or sample_dict.get("Al2O3"),
            fe2o3=sample_dict.get("fe2o3") or sample_dict.get("Fe2O3"),
            feo=sample_dict.get("feo") or sample_dict.get("FeO"),
            mgo=sample_dict.get("mgo") or sample_dict.get("MgO"),
            cao=sample_dict.get("cao") or sample_dict.get("CaO"),
            na2o=sample_dict.get("na2o") or sample_dict.get("Na2O"),
            k2o=sample_dict.get("k2o") or sample_dict.get("K2O"),
            p2o5=sample_dict.get("p2o5") or sample_dict.get("P2O5"),
            ga_ppm=sample_dict.get("ga") or sample_dict.get("Ga"),
            zr_ppm=sample_dict.get("zr") or sample_dict.get("Zr"),
            nb_ppm=sample_dict.get("nb") or sample_dict.get("Nb"),
            y_ppm=sample_dict.get("y") or sample_dict.get("Y"),
            manual_label=sample_dict.get("granite_type"),
        )

    def batch_classify(self, samples: list) -> list:
        """批量分类样本列表。

        Args:
            samples: GeochemSample 列表或 dict 列表
        Returns:
            [(sample, ClassificationResult), ...]
        """
        results = []
        for sample in samples:
            if hasattr(sample, 'to_flat_dict'):
                sample_dict = sample.to_flat_dict()
            else:
                sample_dict = sample
            result = self.classify_sample(sample_dict)
            results.append((sample, result))
        return results
