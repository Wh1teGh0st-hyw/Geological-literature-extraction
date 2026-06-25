"""数据库连接管理、Schema 创建与迁移。

使用 SQLite3（Python标准库），单文件 .gce 格式存储项目数据。
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from loguru import logger

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- 项目元数据
CREATE TABLE IF NOT EXISTS project_meta (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT
);

-- PDF 文献来源
CREATE TABLE IF NOT EXISTS pdf_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    file_hash TEXT,
    title TEXT,
    authors TEXT,
    year INTEGER,
    journal TEXT,
    page_count INTEGER,
    text_page_count INTEGER DEFAULT 0,
    image_page_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    extracted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 提取的表格（中间产物，未解析）
CREATE TABLE IF NOT EXISTS extracted_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_source_id INTEGER REFERENCES pdf_sources(id) ON DELETE CASCADE,
    page_number INTEGER,
    table_index INTEGER DEFAULT 0,
    extraction_method TEXT DEFAULT 'pdfplumber',
    confidence REAL DEFAULT 1.0,
    raw_json TEXT NOT NULL,
    header_row_indices TEXT,
    is_image_based INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 解析后的地球化学样本数据（核心数据表）
CREATE TABLE IF NOT EXISTS geochem_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extracted_table_id INTEGER REFERENCES extracted_tables(id) ON DELETE SET NULL,
    pdf_source_id INTEGER REFERENCES pdf_sources(id) ON DELETE SET NULL,

    -- 身份信息
    mining_area TEXT,
    rock_body TEXT,
    data_source TEXT,
    sample_no TEXT,
    granite_type TEXT,
    rock_type TEXT,

    -- 年代学
    formation_age REAL,
    age_error REAL,
    age_method TEXT,
    mineralization_age REAL,
    min_age_error REAL,
    min_age_method TEXT,

    -- 空间坐标
    longitude REAL,
    latitude REAL,
    elevation REAL,

    -- 主量元素 (wt%)
    sio2 REAL, tio2 REAL, al2o3 REAL, fe2o3 REAL, feo REAL,
    mno REAL, mgo REAL, cao REAL, na2o REAL, k2o REAL, p2o5 REAL,
    loi REAL, total REAL,

    -- 微量元素 (ppm)
    li REAL, be REAL, sc REAL, v REAL, cr REAL, co REAL, ni REAL,
    cu REAL, zn REAL, ga REAL, rb REAL, sr REAL, y REAL, zr REAL,
    nb REAL, cs REAL, ba REAL, hf REAL, ta REAL, pb REAL, th REAL,
    u REAL, w REAL, sn REAL, mo REAL,

    -- 稀土元素 REE (ppm)
    la REAL, ce REAL, pr REAL, nd REAL, sm REAL, eu REAL,
    gd REAL, tb REAL, dy REAL, ho REAL, er REAL, tm REAL, yb REAL, lu REAL,

    -- Sr-Nd 同位素
    sr87_sr86_i REAL, sr87_sr86_err REAL,
    nd143_nd144_i REAL, nd143_nd144_err REAL,
    epsilon_nd_t REAL, epsilon_nd_err REAL,
    t_dm2_nd REAL, t_dm1_nd REAL,

    -- Hf 同位素
    hf176_hf177_i REAL, hf176_hf177_err REAL,
    epsilon_hf_t REAL, epsilon_hf_err REAL,
    t_dm2_hf REAL, t_dm1_hf REAL,

    -- 计算指数（分类用）
    asi REAL,
    femgi REAL,
    ga_al_ratio REAL,
    mali REAL,
    t_zr REAL,

    -- 分类
    auto_classification TEXT,
    auto_confidence TEXT,
    manual_classification TEXT,
    classification_source TEXT DEFAULT 'auto',

    -- 验证
    validation_status TEXT DEFAULT 'pending',
    validation_notes TEXT,

    -- 原始值备份
    raw_values_json TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 编辑历史（审计追溯）
CREATE TABLE IF NOT EXISTS edit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER REFERENCES geochem_samples(id) ON DELETE CASCADE,
    column_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    edit_reason TEXT,
    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 批量处理任务日志
CREATE TABLE IF NOT EXISTS batch_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,
    total_items INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_summary TEXT
);

-- 导出模板
CREATE TABLE IF NOT EXISTS export_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    column_mapping_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 应用配置
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_samples_mining_area ON geochem_samples(mining_area);
CREATE INDEX IF NOT EXISTS idx_samples_rock_body ON geochem_samples(rock_body);
CREATE INDEX IF NOT EXISTS idx_samples_granite_type ON geochem_samples(granite_type);
CREATE INDEX IF NOT EXISTS idx_samples_rock_type ON geochem_samples(rock_type);
CREATE INDEX IF NOT EXISTS idx_samples_sio2 ON geochem_samples(sio2);
CREATE INDEX IF NOT EXISTS idx_extracted_pdf ON extracted_tables(pdf_source_id);
CREATE INDEX IF NOT EXISTS idx_extracted_status ON extracted_tables(status);
CREATE INDEX IF NOT EXISTS idx_samples_sample_no ON geochem_samples(sample_no);
CREATE INDEX IF NOT EXISTS idx_samples_data_source ON geochem_samples(data_source);
"""


class DatabaseManager:
    """SQLite 数据库连接管理器。"""

    def __init__(self, db_path: str = ":memory:"):
        """
        Args:
            db_path: 数据库文件路径，默认使用内存数据库
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("数据库未连接。请使用 connect() 或上下文管理器。")
        return self._conn

    def connect(self) -> sqlite3.Connection:
        """建立数据库连接并初始化 schema。"""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._set_meta("schema_version", str(SCHEMA_VERSION))
        logger.debug(f"数据库已连接: {self.db_path}")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("数据库已关闭")

    def _init_schema(self):
        """执行 schema SQL 创建表结构。"""
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def _set_meta(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO project_meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        self._conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM project_meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def get_sample_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM geochem_samples"
        ).fetchone()
        return row["cnt"] if row else 0

    def get_pdf_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM pdf_sources"
        ).fetchone()
        return row["cnt"] if row else 0

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def create_database(db_path: str) -> DatabaseManager:
    """创建/打开数据库并返回管理器。"""
    db = DatabaseManager(db_path)
    db.connect()
    return db
