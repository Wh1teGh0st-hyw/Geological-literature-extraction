"""地球化学图解模块 — TAS分类图 / REE球粒陨石配分曲线 / 花岗岩判别图。

支持:
- matplotlib 渲染 (推荐)
- 纯数据结构导出 (fallback, 用于外部绘图软件)
"""

from typing import List, Dict, Optional, Any, Tuple
import math
from loguru import logger


# ── 球粒陨石标准化值 ──────────────────────────────
# Sun & McDonough (1989)
CHONDRITE_VALUES = {
    "La": 0.237, "Ce": 0.613, "Pr": 0.0928, "Nd": 0.457,
    "Sm": 0.148, "Eu": 0.0563, "Gd": 0.199, "Tb": 0.0361,
    "Dy": 0.246, "Ho": 0.0546, "Er": 0.160, "Tm": 0.0247,
    "Yb": 0.161, "Lu": 0.0246,
}

# Boynton (1984) 备用
CHONDRITE_BOYNTON = {
    "La": 0.31, "Ce": 0.808, "Pr": 0.122, "Nd": 0.60,
    "Sm": 0.195, "Eu": 0.0735, "Gd": 0.259, "Tb": 0.0474,
    "Dy": 0.322, "Ho": 0.0718, "Er": 0.21, "Tm": 0.0324,
    "Yb": 0.209, "Lu": 0.0322,
}

# TAS 图分类边界
TAS_BOUNDARIES = {
    "F (似长岩)":        (35, 15, 41, 15),
    "U1 (碧玄岩/碱玄岩)": (41, 3, 45, 5),
    "U2 (响岩质碱玄岩)":  (45, 5, 49, 7),
    "U3 (碱玄质响岩)":    (49, 7, 52, 14),
    "Ph (响岩)":          (52, 9, 65, 18),
    "S1 (玄武岩)":        (45, 0, 52, 5),
    "S2 (玄武安山岩)":    (52, 0.5, 57, 5.5),
    "S3 (安山岩)":        (57, 2, 63, 7.5),
    "O1 (玄武粗安岩)":    (45, 3, 52, 7),
    "O2 (粗安岩)":        (52, 5, 57, 7.5),
    "O3 (粗安岩)":        (57, 5.5, 63, 9),
    "T (粗面岩/粗面英安岩)": (57, 7.5, 69, 16),
    "R (流纹岩)":         (69, 7, 80, 16),
    "B (粗面玄武岩)":     (45, 1.5, 52, 5),
    "Pc (苦榄玄武岩)":    (41, 0, 45, 3),
}


class DiagramDataBuilder:
    """图解数据构建器 — 从样本数据生成 matplotlib 绘图所需的结构。"""

    @staticmethod
    def build_tas_data(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建 TAS 图解数据。

        Returns:
            {"x": [SiO2], "y": [Na2O+K2O], "labels": [...], "boundaries": [...]}
        """
        x, y, labels, rocks = [], [], [], []

        for s in samples:
            sio2 = s.get("SiO2")
            na2o = s.get("Na2O")
            k2o = s.get("K2O")
            if all(v is not None and v > 0 for v in [sio2, na2o, k2o]):
                x.append(sio2)
                y.append(na2o + k2o)
                labels.append(s.get("Sample.No", "") or s.get("Sample", ""))
                rocks.append(s.get("Rock type", "") or s.get("Granite type", ""))

        return {"x": x, "y": y, "labels": labels, "rocks": rocks,
                "boundaries": TAS_BOUNDARIES}

    @staticmethod
    def build_ree_data(samples: List[Dict[str, Any]],
                       chondrite: str = "Sun_McDonough_1989") -> Dict[str, Any]:
        """构建 REE 配分曲线数据。

        Returns:
            {"elements": [...], "samples": [{"name": ..., "y": [...]}, ...]}
        """
        ree_fields = ["La", "Ce", "Pr", "Nd", "Sm", "Eu",
                       "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu"]

        if chondrite == "Boynton_1984":
            chondrite_vals = CHONDRITE_BOYNTON
        else:
            chondrite_vals = CHONDRITE_VALUES

        series = []
        for s in samples:
            y_vals = []
            has_data = False
            for f in ree_fields:
                val = s.get(f)
                if val is not None and val > 0:
                    y_vals.append(val / chondrite_vals[f])
                    has_data = True
                else:
                    y_vals.append(None)

            if has_data:
                series.append({
                    "name": s.get("Sample.No", "") or s.get("Sample", "?"),
                    "y": y_vals,
                })

        return {"elements": ree_fields, "series": series}

    @staticmethod
    def build_discrimination_data(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建花岗岩判别图数据。

        Returns 4种常用判别图的数据:
        - ASI vs SiO2
        - FeOt/(FeOt+MgO) vs SiO2
        - Ga/Al×10⁴ vs Zr
        - Rb vs (Y+Nb) (Pearce 1984)
        """
        data = {"asi_sio2": {"x": [], "y": [], "labels": [], "types": []},
                "femgi_sio2": {"x": [], "y": [], "labels": [], "types": []},
                "ga_al_zr": {"x": [], "y": [], "labels": [], "types": []},
                "rb_ynb": {"x": [], "y": [], "labels": [], "types": []}}

        for s in samples:
            name = s.get("Sample.No", "") or s.get("Sample", "")
            gtype = s.get("Granite type", "")

            sio2 = s.get("SiO2")
            asi = s.get("ASI")
            femgi = s.get("FeOt/(FeOt+MgO)")
            ga_al = s.get("Ga/Al×10⁴")
            zr_val = s.get("Zr")
            rb_val = s.get("Rb")
            y_val = s.get("Y")
            nb_val = s.get("Nb")

            if sio2 and asi:
                data["asi_sio2"]["x"].append(sio2)
                data["asi_sio2"]["y"].append(asi)
                data["asi_sio2"]["labels"].append(name)
                data["asi_sio2"]["types"].append(gtype)

            if sio2 and femgi:
                data["femgi_sio2"]["x"].append(sio2)
                data["femgi_sio2"]["y"].append(femgi)
                data["femgi_sio2"]["labels"].append(name)
                data["femgi_sio2"]["types"].append(gtype)

            if ga_al and zr_val:
                data["ga_al_zr"]["x"].append(ga_al)
                data["ga_al_zr"]["y"].append(zr_val)
                data["ga_al_zr"]["labels"].append(name)
                data["ga_al_zr"]["types"].append(gtype)

            if rb_val and y_val is not None and nb_val is not None:
                data["rb_ynb"]["x"].append(y_val + nb_val)
                data["rb_ynb"]["y"].append(rb_val)
                data["rb_ynb"]["labels"].append(name)
                data["rb_ynb"]["types"].append(gtype)

        return data


class ChartRenderer:
    """图表渲染器 — 使用 matplotlib 绘制。

    pip install matplotlib (可选依赖)
    """

    _MATPLOTLIB_AVAILABLE = None

    @classmethod
    def is_available(cls) -> bool:
        if cls._MATPLOTLIB_AVAILABLE is None:
            try:
                import matplotlib
                matplotlib.use("Qt5Agg")
                cls._MATPLOTLIB_AVAILABLE = True
            except ImportError:
                cls._MATPLOTLIB_AVAILABLE = False
        return cls._MATPLOTLIB_AVAILABLE

    @classmethod
    def render_tas(cls, data: Dict[str, Any], ax=None):
        """渲染 TAS 分类图。"""
        if not cls.is_available():
            logger.warning("matplotlib 未安装，无法渲染图表")
            return None

        import matplotlib
        matplotlib.use("Qt5Agg")
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 7))

        x, y = data["x"], data["y"]
        rocks = data.get("rocks", [])

        # 颜色映射
        color_map = {"I-type": "#3B82F6", "S-type": "#EF4444",
                      "A-type": "#10B981", "M-type": "#8B5CF6"}

        colors = [color_map.get(r, "#6B7280") for r in rocks]
        if not colors:
            colors = "#D97706"

        ax.scatter(x, y, c=colors, s=30, alpha=0.7, edgecolors="#1A1A2E", linewidth=0.5)

        # 确保目录用黑色外观
        ax.set_facecolor("#16213E")
        ax.figure.set_facecolor("#1A1A2E")

        ax.set_xlabel("SiO₂ (wt%)", color="#E8E8E8", fontsize=11)
        ax.set_ylabel("Na₂O + K₂O (wt%)", color="#E8E8E8", fontsize=11)
        ax.set_title("TAS 分类图 (Middlemost 1994)", color="#D97706", fontsize=13, fontweight="bold")

        ax.set_xlim(35, 80)
        ax.set_ylim(0, 16)
        ax.tick_params(colors="#A0A0B0")
        ax.grid(True, alpha=0.15, color="#E8E8E8")

        for spine in ax.spines.values():
            spine.set_color("#2A3F6A")

        return ax

    @classmethod
    def render_ree(cls, data: Dict[str, Any], ax=None):
        """渲染 REE 球粒陨石标准化配分曲线。"""
        if not cls.is_available():
            return None

        import matplotlib
        matplotlib.use("Qt5Agg")
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))

        elements = data["elements"]
        x = list(range(1, len(elements) + 1))
        for series in data["series"]:
            y = [v if v else None for v in series["y"]]
            ax.plot(x, y, "-o", label=series["name"], markersize=3, linewidth=1.2, alpha=0.7)

        ax.set_facecolor("#16213E")
        ax.figure.set_facecolor("#1A1A2E")
        ax.set_xticks(x)
        ax.set_xticklabels(elements, color="#E8E8E8", fontsize=9)
        ax.set_ylabel("Sample / Chondrite", color="#E8E8E8", fontsize=11)
        ax.set_title("REE 球粒陨石标准化配分曲线", color="#D97706", fontsize=13, fontweight="bold")
        ax.set_yscale("log")
        ax.tick_params(colors="#A0A0B0")
        ax.grid(True, alpha=0.15, which="both", color="#E8E8E8")
        ax.legend(facecolor="#16213E", edgecolor="#2A3F6A", labelcolor="#E8E8E8", fontsize=8)

        for spine in ax.spines.values():
            spine.set_color("#2A3F6A")

        return ax


def export_diagram_csv(data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """导出图解数据为 CSV。"""
    import os, pandas as pd
    os.makedirs(output_dir, exist_ok=True)
    files = {}

    builder = DiagramDataBuilder()

    if "x" in data:  # TAS data
        df_tas = pd.DataFrame({"SiO2": data["x"], "Na2O_K2O": data["y"],
                                "Sample": data["labels"], "Rock": data.get("rocks", [])})
        path = os.path.join(output_dir, "tas_diagram.csv")
        df_tas.to_csv(path, index=False, encoding="utf-8-sig")
        files["tas"] = path

    if "series" in data:  # REE data
        rows = []
        for s in data["series"]:
            rows.append({"Sample": s["name"], **{e: v for e, v in zip(data["elements"], s["y"])}})
        path = os.path.join(output_dir, "ree_normalized.csv")
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
        files["ree"] = path

    return files
