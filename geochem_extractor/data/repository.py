"""数据访问仓库（Repository Pattern）。

封装所有对 SQLite 的 CRUD 操作，提供统一的数据访问接口。
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from .database import DatabaseManager
from .models import GeochemSample, MajorElements, TraceElements, REEElements, Isotopes, ComputedIndices


class SampleRepository:
    """地球化学样本数据仓库。"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.conn

    # ── 样本 CRUD ─────────────────────────────────────────

    def insert_sample(self, sample: GeochemSample) -> int:
        """插入一条样本记录，返回自增 ID。"""
        fields = self._get_sample_fields()
        flat = self._flatten_sample(sample)
        placeholders = ",".join(["?" for _ in fields])
        columns = ",".join(fields)
        sql = f"INSERT INTO geochem_samples ({columns}) VALUES ({placeholders})"
        values = [flat.get(f) for f in fields]
        cursor = self.conn.execute(sql, values)
        self.conn.commit()
        sample_id = cursor.lastrowid
        logger.debug(f"样本已插入: id={sample_id}, sample_no={sample.sample_no}")
        return sample_id

    def update_sample(self, sample: GeochemSample) -> bool:
        """更新一条样本记录。"""
        if sample.id is None:
            raise ValueError("无法更新未持久化的样本（id=None）")
        fields = self._get_sample_fields()
        flat = self._flatten_sample(sample)
        flat["modified_at"] = datetime.now().isoformat()
        set_clause = ",".join([f"{f}=?" for f in fields if f != "id"])
        values = [flat.get(f) for f in fields if f != "id"]
        self.conn.execute(
            f"UPDATE geochem_samples SET {set_clause} WHERE id=?",
            values + [sample.id],
        )
        self.conn.commit()
        logger.debug(f"样本已更新: id={sample.id}")
        return True

    def delete_sample(self, sample_id: int) -> bool:
        """删除一条样本记录。"""
        self.conn.execute("DELETE FROM geochem_samples WHERE id=?", (sample_id,))
        self.conn.commit()
        return True

    def get_sample(self, sample_id: int) -> Optional[GeochemSample]:
        """获取单条样本。"""
        row = self.conn.execute(
            "SELECT * FROM geochem_samples WHERE id=?", (sample_id,)
        ).fetchone()
        return self._row_to_sample(row) if row else None

    def get_all_samples(self) -> List[GeochemSample]:
        """获取所有样本。"""
        rows = self.conn.execute("SELECT * FROM geochem_samples ORDER BY id").fetchall()
        return [self._row_to_sample(r) for r in rows]

    def get_sample_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM geochem_samples").fetchone()
        return row["cnt"] if row else 0

    def get_samples_by_type(self, granite_type: str) -> List[GeochemSample]:
        """按花岗岩类型筛选。"""
        rows = self.conn.execute(
            "SELECT * FROM geochem_samples WHERE granite_type=? ORDER BY id",
            (granite_type,),
        ).fetchall()
        return [self._row_to_sample(r) for r in rows]

    def get_samples_by_area(self, mining_area: str) -> List[GeochemSample]:
        """按矿区筛选。"""
        rows = self.conn.execute(
            "SELECT * FROM geochem_samples WHERE mining_area=? ORDER BY id",
            (mining_area,),
        ).fetchall()
        return [self._row_to_sample(r) for r in rows]

    def get_distinct_values(self, column: str) -> List[str]:
        """获取某列的唯一切换值（用于筛选下拉框）。"""
        valid_columns = [
            "mining_area", "rock_body", "granite_type", "rock_type",
            "data_source", "age_method", "auto_classification"
        ]
        if column not in valid_columns:
            raise ValueError(f"列 {column} 不支持获取唯一值")
        rows = self.conn.execute(
            f"SELECT DISTINCT {column} FROM geochem_samples WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
        ).fetchall()
        return [r[column] for r in rows]

    # ── PDF 来源 CRUD ────────────────────────────────────

    def insert_pdf_source(self, file_path: str, file_name: str,
                          file_size: int = 0, file_hash: str = "",
                          title: str = "", authors: str = "",
                          year: int = None, journal: str = "",
                          page_count: int = 0) -> int:
        """添加 PDF 来源记录。"""
        cursor = self.conn.execute(
            """INSERT INTO pdf_sources
               (file_path, file_name, file_size, file_hash, title, authors, year, journal, page_count)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (file_path, file_name, file_size, file_hash, title, authors, year, journal, page_count),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_pdf_sources(self) -> List[Dict[str, Any]]:
        """获取所有 PDF 来源。"""
        rows = self.conn.execute(
            "SELECT * FROM pdf_sources ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── 批量导入 ─────────────────────────────────────────

    def bulk_insert_samples(self, samples: List[GeochemSample]) -> int:
        """批量插入样本（单事务），返回成功插入数量。"""
        fields = self._get_sample_fields()
        columns = ",".join(fields)
        placeholders = ",".join(["?" for _ in fields])
        sql = f"INSERT OR IGNORE INTO geochem_samples ({columns}) VALUES ({placeholders})"
        count = 0
        try:
            self.conn.execute("BEGIN TRANSACTION")
            for sample in samples:
                flat = self._flatten_sample(sample)
                values = [flat.get(f) for f in fields]
                self.conn.execute(sql, values)
                count += 1
            self.conn.execute("COMMIT")
            logger.info(f"批量导入完成: {count} 条样本")
        except Exception as e:
            self.conn.execute("ROLLBACK")
            logger.error(f"批量导入失败: {e}")
            raise
        return count

    # ── 内部工具方法 ─────────────────────────────────────

    def _get_sample_fields(self) -> List[str]:
        """返回 geochem_samples 表的所有字段名（不含 id, created_at, modified_at）。"""
        return [
            "extracted_table_id", "pdf_source_id",
            "mining_area", "rock_body", "data_source", "sample_no", "granite_type", "rock_type",
            "formation_age", "age_error", "age_method",
            "mineralization_age", "min_age_error", "min_age_method",
            "longitude", "latitude", "elevation",
            "sio2", "tio2", "al2o3", "fe2o3", "feo", "mno", "mgo", "cao", "na2o", "k2o", "p2o5", "loi", "total",
            "li", "be", "sc", "v", "cr", "co", "ni", "cu", "zn", "ga",
            "rb", "sr", "y", "zr", "nb", "cs", "ba", "hf", "ta", "pb", "th", "u", "w", "sn", "mo",
            "la", "ce", "pr", "nd", "sm", "eu", "gd", "tb", "dy", "ho", "er", "tm", "yb", "lu",
            "sr87_sr86_i", "sr87_sr86_err",
            "nd143_nd144_i", "nd143_nd144_err", "epsilon_nd_t", "epsilon_nd_err", "t_dm2_nd", "t_dm1_nd",
            "hf176_hf177_i", "hf176_hf177_err", "epsilon_hf_t", "epsilon_hf_err", "t_dm2_hf", "t_dm1_hf",
            "asi", "femgi", "ga_al_ratio", "mali", "t_zr",
            "auto_classification", "auto_confidence", "manual_classification", "classification_source",
            "validation_status", "validation_notes", "raw_values_json",
        ]

    def _flatten_sample(self, sample: GeochemSample) -> Dict[str, Any]:
        """将 GeochemSample 对象展平为数据库行的 dict。"""
        return {
            "extracted_table_id": sample.extracted_table_id,
            "pdf_source_id": sample.pdf_source_id,
            "mining_area": sample.mining_area,
            "rock_body": sample.rock_body,
            "data_source": sample.data_source,
            "sample_no": sample.sample_no,
            "granite_type": sample.granite_type,
            "rock_type": sample.rock_type,
            "formation_age": sample.formation_age,
            "age_error": sample.age_error,
            "age_method": sample.age_method,
            "mineralization_age": sample.mineralization_age,
            "min_age_error": sample.min_age_error,
            "min_age_method": sample.min_age_method,
            "longitude": sample.longitude,
            "latitude": sample.latitude,
            "elevation": sample.elevation,
            "sio2": sample.major.sio2,
            "tio2": sample.major.tio2,
            "al2o3": sample.major.al2o3,
            "fe2o3": sample.major.fe2o3,
            "feo": sample.major.feo,
            "mno": sample.major.mno,
            "mgo": sample.major.mgo,
            "cao": sample.major.cao,
            "na2o": sample.major.na2o,
            "k2o": sample.major.k2o,
            "p2o5": sample.major.p2o5,
            "loi": sample.major.loi,
            "total": sample.major.total,
            "li": sample.trace.li, "be": sample.trace.be, "sc": sample.trace.sc,
            "v": sample.trace.v, "cr": sample.trace.cr, "co": sample.trace.co,
            "ni": sample.trace.ni, "cu": sample.trace.cu, "zn": sample.trace.zn,
            "ga": sample.trace.ga, "rb": sample.trace.rb, "sr": sample.trace.sr,
            "y": sample.trace.y, "zr": sample.trace.zr, "nb": sample.trace.nb,
            "cs": sample.trace.cs, "ba": sample.trace.ba, "hf": sample.trace.hf,
            "ta": sample.trace.ta, "pb": sample.trace.pb, "th": sample.trace.th,
            "u": sample.trace.u, "w": sample.trace.w, "sn": sample.trace.sn,
            "mo": sample.trace.mo,
            "la": sample.ree.la, "ce": sample.ree.ce, "pr": sample.ree.pr,
            "nd": sample.ree.nd, "sm": sample.ree.sm, "eu": sample.ree.eu,
            "gd": sample.ree.gd, "tb": sample.ree.tb, "dy": sample.ree.dy,
            "ho": sample.ree.ho, "er": sample.ree.er, "tm": sample.ree.tm,
            "yb": sample.ree.yb, "lu": sample.ree.lu,
            "sr87_sr86_i": sample.isotopes.sr87_sr86_i,
            "sr87_sr86_err": sample.isotopes.sr87_sr86_err,
            "nd143_nd144_i": sample.isotopes.nd143_nd144_i,
            "nd143_nd144_err": sample.isotopes.nd143_nd144_err,
            "epsilon_nd_t": sample.isotopes.epsilon_nd_t,
            "epsilon_nd_err": sample.isotopes.epsilon_nd_err,
            "t_dm2_nd": sample.isotopes.t_dm2_nd,
            "t_dm1_nd": sample.isotopes.t_dm1_nd,
            "hf176_hf177_i": sample.isotopes.hf176_hf177_i,
            "hf176_hf177_err": sample.isotopes.hf176_hf177_err,
            "epsilon_hf_t": sample.isotopes.epsilon_hf_t,
            "epsilon_hf_err": sample.isotopes.epsilon_hf_err,
            "t_dm2_hf": sample.isotopes.t_dm2_hf,
            "t_dm1_hf": sample.isotopes.t_dm1_hf,
            "asi": sample.indices.asi,
            "femgi": sample.indices.femgi,
            "ga_al_ratio": sample.indices.ga_al_ratio,
            "mali": sample.indices.mali,
            "t_zr": sample.indices.t_zr,
            "auto_classification": sample.auto_classification,
            "auto_confidence": sample.auto_confidence,
            "manual_classification": sample.manual_classification,
            "classification_source": sample.classification_source,
            "validation_status": sample.validation_status,
            "validation_notes": sample.validation_notes,
            "raw_values_json": json.dumps(sample.to_flat_dict(), ensure_ascii=False, default=str),
        }

    def _row_to_sample(self, row: sqlite3.Row) -> GeochemSample:
        """将 SQLite Row 对象转换为 GeochemSample。"""
        r = dict(row)
        return GeochemSample(
            id=r.get("id"),
            extracted_table_id=r.get("extracted_table_id"),
            pdf_source_id=r.get("pdf_source_id"),
            mining_area=r.get("mining_area"),
            rock_body=r.get("rock_body"),
            data_source=r.get("data_source"),
            sample_no=r.get("sample_no"),
            granite_type=r.get("granite_type"),
            rock_type=r.get("rock_type"),
            formation_age=r.get("formation_age"),
            age_error=r.get("age_error"),
            age_method=r.get("age_method"),
            mineralization_age=r.get("mineralization_age"),
            min_age_error=r.get("min_age_error"),
            min_age_method=r.get("min_age_method"),
            longitude=r.get("longitude"),
            latitude=r.get("latitude"),
            elevation=r.get("elevation"),
            major=MajorElements(
                sio2=r.get("sio2"), tio2=r.get("tio2"), al2o3=r.get("al2o3"),
                fe2o3=r.get("fe2o3"), feo=r.get("feo"), mno=r.get("mno"),
                mgo=r.get("mgo"), cao=r.get("cao"), na2o=r.get("na2o"),
                k2o=r.get("k2o"), p2o5=r.get("p2o5"), loi=r.get("loi"),
                total=r.get("total"),
            ),
            trace=TraceElements(
                li=r.get("li"), be=r.get("be"), sc=r.get("sc"),
                v=r.get("v"), cr=r.get("cr"), co=r.get("co"),
                ni=r.get("ni"), cu=r.get("cu"), zn=r.get("zn"),
                ga=r.get("ga"), rb=r.get("rb"), sr=r.get("sr"),
                y=r.get("y"), zr=r.get("zr"), nb=r.get("nb"),
                cs=r.get("cs"), ba=r.get("ba"), hf=r.get("hf"),
                ta=r.get("ta"), pb=r.get("pb"), th=r.get("th"),
                u=r.get("u"), w=r.get("w"), sn=r.get("sn"), mo=r.get("mo"),
            ),
            ree=REEElements(
                la=r.get("la"), ce=r.get("ce"), pr=r.get("pr"),
                nd=r.get("nd"), sm=r.get("sm"), eu=r.get("eu"),
                gd=r.get("gd"), tb=r.get("tb"), dy=r.get("dy"),
                ho=r.get("ho"), er=r.get("er"), tm=r.get("tm"),
                yb=r.get("yb"), lu=r.get("lu"),
            ),
            isotopes=Isotopes(
                sr87_sr86_i=r.get("sr87_sr86_i"),
                sr87_sr86_err=r.get("sr87_sr86_err"),
                nd143_nd144_i=r.get("nd143_nd144_i"),
                nd143_nd144_err=r.get("nd143_nd144_err"),
                epsilon_nd_t=r.get("epsilon_nd_t"),
                epsilon_nd_err=r.get("epsilon_nd_err"),
                t_dm2_nd=r.get("t_dm2_nd"),
                t_dm1_nd=r.get("t_dm1_nd"),
                hf176_hf177_i=r.get("hf176_hf177_i"),
                hf176_hf177_err=r.get("hf176_hf177_err"),
                epsilon_hf_t=r.get("epsilon_hf_t"),
                epsilon_hf_err=r.get("epsilon_hf_err"),
                t_dm2_hf=r.get("t_dm2_hf"),
                t_dm1_hf=r.get("t_dm1_hf"),
            ),
            indices=ComputedIndices(
                asi=r.get("asi"),
                femgi=r.get("femgi"),
                ga_al_ratio=r.get("ga_al_ratio"),
                mali=r.get("mali"),
                t_zr=r.get("t_zr"),
            ),
            auto_classification=r.get("auto_classification"),
            auto_confidence=r.get("auto_confidence"),
            manual_classification=r.get("manual_classification"),
            classification_source=r.get("classification_source") or "auto",
            validation_status=r.get("validation_status") or "pending",
            validation_notes=r.get("validation_notes"),
            created_at=r.get("created_at"),
            modified_at=r.get("modified_at"),
        )
