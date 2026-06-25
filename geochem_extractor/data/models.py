"""Pydantic 数据模型 — 地球化学样本的完整94列定义。

所有模型字段与 SQLite geochem_samples 表及目标 Excel 模板列一一对应。
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# ── 主量元素组 ──────────────────────────────────────────

class MajorElements(BaseModel):
    """主量元素 (wt%)"""
    sio2: Optional[float] = Field(default=None, description="SiO2 wt%")
    tio2: Optional[float] = Field(default=None)
    al2o3: Optional[float] = Field(default=None)
    fe2o3: Optional[float] = Field(default=None)
    feo: Optional[float] = Field(default=None)
    mno: Optional[float] = Field(default=None)
    mgo: Optional[float] = Field(default=None)
    cao: Optional[float] = Field(default=None)
    na2o: Optional[float] = Field(default=None)
    k2o: Optional[float] = Field(default=None)
    p2o5: Optional[float] = Field(default=None)
    loi: Optional[float] = Field(default=None, description="烧失量")
    total: Optional[float] = Field(default=None, description="主量元素总和")

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ── 微量元素组 ──────────────────────────────────────────

class TraceElements(BaseModel):
    """微量元素 (ppm)"""
    li: Optional[float] = None
    be: Optional[float] = None
    sc: Optional[float] = None
    v: Optional[float] = None
    cr: Optional[float] = None
    co: Optional[float] = None
    ni: Optional[float] = None
    cu: Optional[float] = None
    zn: Optional[float] = None
    ga: Optional[float] = None
    rb: Optional[float] = None
    sr: Optional[float] = None
    y: Optional[float] = None
    zr: Optional[float] = None
    nb: Optional[float] = None
    cs: Optional[float] = None
    ba: Optional[float] = None
    hf: Optional[float] = None
    ta: Optional[float] = None
    pb: Optional[float] = None
    th: Optional[float] = None
    u: Optional[float] = None
    w: Optional[float] = None
    sn: Optional[float] = None
    mo: Optional[float] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ── 稀土元素组 ──────────────────────────────────────────

class REEElements(BaseModel):
    """稀土元素 (ppm)"""
    la: Optional[float] = Field(default=None, ge=0)
    ce: Optional[float] = Field(default=None, ge=0)
    pr: Optional[float] = Field(default=None, ge=0)
    nd: Optional[float] = Field(default=None, ge=0)
    sm: Optional[float] = Field(default=None, ge=0)
    eu: Optional[float] = Field(default=None, ge=0)
    gd: Optional[float] = Field(default=None, ge=0)
    tb: Optional[float] = Field(default=None, ge=0)
    dy: Optional[float] = Field(default=None, ge=0)
    ho: Optional[float] = Field(default=None, ge=0)
    er: Optional[float] = Field(default=None, ge=0)
    tm: Optional[float] = Field(default=None, ge=0)
    yb: Optional[float] = Field(default=None, ge=0)
    lu: Optional[float] = Field(default=None, ge=0)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ── 同位素组 ────────────────────────────────────────────

class Isotopes(BaseModel):
    """Sr-Nd-Hf 同位素数据"""
    # Sr
    sr87_sr86_i: Optional[float] = None
    sr87_sr86_err: Optional[float] = None
    # Nd
    nd143_nd144_i: Optional[float] = None
    nd143_nd144_err: Optional[float] = None
    epsilon_nd_t: Optional[float] = None
    epsilon_nd_err: Optional[float] = None
    t_dm2_nd: Optional[float] = None
    t_dm1_nd: Optional[float] = None
    # Hf
    hf176_hf177_i: Optional[float] = None
    hf176_hf177_err: Optional[float] = None
    epsilon_hf_t: Optional[float] = None
    epsilon_hf_err: Optional[float] = None
    t_dm2_hf: Optional[float] = None
    t_dm1_hf: Optional[float] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ── 计算指数 ────────────────────────────────────────────

class ComputedIndices(BaseModel):
    """地球化学计算指数"""
    asi: Optional[float] = Field(default=None, description="铝饱和指数 ASI = Al2O3/(CaO+Na2O+K2O)")
    femgi: Optional[float] = Field(default=None, description="铁镁指数 FeOt/(FeOt+MgO)")
    ga_al_ratio: Optional[float] = Field(default=None, description="Ga/Al × 10^4")
    mali: Optional[float] = Field(default=None, description="碱钙指数 Na2O+K2O-CaO")
    t_zr: Optional[float] = Field(default=None, description="锆石饱和温度(°C)")

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ── 完整样本模型 ────────────────────────────────────────

class GeochemSample(BaseModel):
    """完整地球化学样本数据模型 (94列对应)"""

    # ── 标识信息 ──
    id: Optional[int] = None
    extracted_table_id: Optional[int] = None
    pdf_source_id: Optional[int] = None

    mining_area: Optional[str] = None          # 矿区
    rock_body: Optional[str] = None            # 岩体
    data_source: Optional[str] = None          # Data source / 文献来源
    sample_no: Optional[str] = None            # Sample.No / 样品号
    granite_type: Optional[str] = None         # 花岗岩类型
    rock_type: Optional[str] = None            # 岩石类型

    # ── 年代学 ──
    formation_age: Optional[float] = None      # 成岩年龄 (Ma)
    age_error: Optional[float] = None
    age_method: Optional[str] = None
    mineralization_age: Optional[float] = None  # 成矿年龄
    min_age_error: Optional[float] = None
    min_age_method: Optional[str] = None

    # ── 空间坐标 ──
    longitude: Optional[float] = None          # X
    latitude: Optional[float] = None           # Y
    elevation: Optional[float] = None          # Hight

    # ── 主量元素 ──
    major: MajorElements = Field(default_factory=MajorElements)

    # ── 微量元素 ──
    trace: TraceElements = Field(default_factory=TraceElements)

    # ── 稀土元素 ──
    ree: REEElements = Field(default_factory=REEElements)

    # ── 同位素 ──
    isotopes: Isotopes = Field(default_factory=Isotopes)

    # ── 计算指数 ──
    indices: ComputedIndices = Field(default_factory=ComputedIndices)

    # ── 分类 ──
    auto_classification: Optional[str] = None   # I/S/A/M-type
    auto_confidence: Optional[str] = None       # high/medium/low
    manual_classification: Optional[str] = None
    classification_source: Optional[str] = "auto"

    # ── 验证 ──
    validation_status: Optional[str] = "pending"
    validation_notes: Optional[str] = None

    # ── 时间戳 ──
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    class Config:
        validate_assignment = True

    def to_flat_dict(self) -> dict:
        """将嵌套模型展平为单层字典（94列格式）。"""
        result = {}
        # 标识
        result["矿区"] = self.mining_area
        result["岩体"] = self.rock_body
        result["Data source"] = self.data_source
        result["Sample.No"] = self.sample_no
        result["Granite type"] = self.granite_type
        result["Rock type"] = self.rock_type
        # 年代学
        result["成岩年龄"] = self.formation_age
        result["age_error"] = self.age_error
        result["age_method"] = self.age_method
        result["成矿年龄"] = self.mineralization_age
        result["min_age_error"] = self.min_age_error
        result["min_age_method"] = self.min_age_method
        # 空间
        result["X"] = self.longitude
        result["Y"] = self.latitude
        result["Hight"] = self.elevation
        # 主量
        result["SiO2"] = self.major.sio2
        result["TiO2"] = self.major.tio2
        result["Al2O3"] = self.major.al2o3
        result["Fe2O3"] = self.major.fe2o3
        result["FeO"] = self.major.feo
        result["MnO"] = self.major.mno
        result["MgO"] = self.major.mgo
        result["CaO"] = self.major.cao
        result["Na2O"] = self.major.na2o
        result["K2O"] = self.major.k2o
        result["P2O5"] = self.major.p2o5
        result["L.O.I"] = self.major.loi
        result["Total"] = self.major.total
        # 微量
        for name in ["li","be","sc","v","cr","co","ni","cu","zn","ga",
                      "rb","sr","y","zr","nb","cs","ba","hf","ta","pb","th","u","w","sn","mo"]:
            result[name.capitalize()] = getattr(self.trace, name, None)
        # REE
        for name in ["la","ce","pr","nd","sm","eu","gd","tb","dy","ho","er","tm","yb","lu"]:
            result[name.capitalize()] = getattr(self.ree, name, None)
        # 同位素 Sr
        result["87Sr/86Sr(i)"] = self.isotopes.sr87_sr86_i
        result["87Sr/86Sr_err"] = self.isotopes.sr87_sr86_err
        # 同位素 Nd
        result["143Nd/144Nd(i)"] = self.isotopes.nd143_nd144_i
        result["143Nd/144Nd_err"] = self.isotopes.nd143_nd144_err
        result["εNd(t)"] = self.isotopes.epsilon_nd_t
        result["εNd_err"] = self.isotopes.epsilon_nd_err
        result["TDM2(Nd)"] = self.isotopes.t_dm2_nd
        result["TDM1(Nd)"] = self.isotopes.t_dm1_nd
        # 同位素 Hf
        result["176Hf/177Hf(i)"] = self.isotopes.hf176_hf177_i
        result["176Hf/177Hf_err"] = self.isotopes.hf176_hf177_err
        result["εHf(t)"] = self.isotopes.epsilon_hf_t
        result["εHf_err"] = self.isotopes.epsilon_hf_err
        result["TDM2(Hf)"] = self.isotopes.t_dm2_hf
        result["TDM1(Hf)"] = self.isotopes.t_dm1_hf
        # 指数
        result["ASI"] = self.indices.asi
        result["Ga/Al*10⁴"] = self.indices.ga_al_ratio
        result["FeOt/(FeOt+MgO)"] = self.indices.femgi
        result["TZr(°C)"] = self.indices.t_zr
        return result


# ── Excel列名映射 ──────────────────────────────────────
# 此常量定义了数据库中对应字段名到 Excel 列名的一一映射
# 用于导入导出时做精确对应

EXCEL_COLUMN_MAP = {
    "矿区": "mining_area",
    "岩体": "rock_body",
    "Data source": "data_source",
    "Sample.No": "sample_no",
    "Granite type": "granite_type",
    "Rock type": "rock_type",
    "成岩年龄": "formation_age",
    "error": "age_error",
    "Method": "age_method",
    "成矿年龄": "mineralization_age",
    "成矿error": "min_age_error",
    "成矿Method": "min_age_method",
    "X": "longitude",
    "Y": "latitude",
    "Hight": "elevation",
    "SiO2": "major.sio2",
    "TiO2": "major.tio2",
    "Al2O3": "major.al2o3",
    "Fe2O3": "major.fe2o3",
    "FeO": "major.feo",
    "MnO": "major.mno",
    "MgO": "major.mgo",
    "CaO": "major.cao",
    "Na2O": "major.na2o",
    "K2O": "major.k2o",
    "P2O5": "major.p2o5",
    "L.O.I": "major.loi",
    "Total": "major.total",
    "Li": "trace.li",
    "Be": "trace.be",
    "Sc": "trace.sc",
    "V": "trace.v",
    "Cr": "trace.cr",
    "Co": "trace.co",
    "Ni": "trace.ni",
    "Cu": "trace.cu",
    "Zn": "trace.zn",
    "Ga": "trace.ga",
    "Rb": "trace.rb",
    "Sr": "trace.sr",
    "Y": "trace.y",
    "Zr": "trace.zr",
    "Nb": "trace.nb",
    "Cs": "trace.cs",
    "Ba": "trace.ba",
    "Hf": "trace.hf",
    "Ta": "trace.ta",
    "Pb": "trace.pb",
    "Th": "trace.th",
    "U": "trace.u",
    "W": "trace.w",
    "Sn": "trace.sn",
    "Mo": "trace.mo",
    "La": "ree.la",
    "Ce": "ree.ce",
    "Pr": "ree.pr",
    "Nd": "ree.nd",
    "Sm": "ree.sm",
    "Eu": "ree.eu",
    "Gd": "ree.gd",
    "Tb": "ree.tb",
    "Dy": "ree.dy",
    "Ho": "ree.ho",
    "Er": "ree.er",
    "Tm": "ree.tm",
    "Yb": "ree.yb",
    "Lu": "ree.lu",
    "87Sr/86Sr(i)": "isotopes.sr87_sr86_i",
    "143Nd/144Nd(i)": "isotopes.nd143_nd144_i",
    "εNd(t)": "isotopes.epsilon_nd_t",
    "176Hf/177Hf(i)": "isotopes.hf176_hf177_i",
    "εHf(t)": "isotopes.epsilon_hf_t",
}
