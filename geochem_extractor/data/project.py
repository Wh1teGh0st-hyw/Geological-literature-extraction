"""项目文件管理 — .gce 文件（即 SQLite 数据库）的打开/保存/另存。"""

import os
import shutil
from pathlib import Path
from typing import Optional
from loguru import logger

from .database import DatabaseManager, create_database
from .repository import SampleRepository


GCE_EXTENSION = ".gce"
GCE_FILTER = "GeoChemExtractor Project (*.gce)"


class ProjectManager:
    """项目文件管理器，封装 .gce（SQLite）文件的操作。"""

    def __init__(self):
        self._db: Optional[DatabaseManager] = None
        self._repo: Optional[SampleRepository] = None
        self._project_path: Optional[str] = None
        self._project_name: str = "未命名项目"
        self._modified: bool = False

    # ── 属性 ─────────────────────────────────────────────

    @property
    def db(self) -> DatabaseManager:
        if self._db is None:
            raise RuntimeError("没有打开的项目。请使用 new_project() 或 open_project()。")
        return self._db

    @property
    def repo(self) -> SampleRepository:
        if self._repo is None:
            raise RuntimeError("没有打开的项目。")
        return self._repo

    @property
    def project_path(self) -> Optional[str]:
        return self._project_path

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def is_modified(self) -> bool:
        return self._modified

    @property
    def has_project(self) -> bool:
        return self._db is not None

    # ── 项目操作 ─────────────────────────────────────────

    def new_project(self, save_path: str) -> DatabaseManager:
        """创建新项目。如果文件已存在则询问是否覆盖。"""
        if os.path.exists(save_path):
            raise FileExistsError(f"项目文件已存在: {save_path}")

        self._close_current()

        self._db = create_database(save_path)
        self._db._set_meta("project_name", os.path.splitext(os.path.basename(save_path))[0])
        self._db._set_meta("created_at", __import__("datetime").datetime.now().isoformat())

        self._repo = SampleRepository(self._db)
        self._project_path = save_path
        self._project_name = self._db.get_meta("project_name") or "未命名项目"
        self._modified = True

        logger.info(f"新项目已创建: {save_path}")
        return self._db

    def open_project(self, file_path: str) -> DatabaseManager:
        """打开已有项目文件。"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"项目文件不存在: {file_path}")

        self._close_current()

        self._db = create_database(file_path)
        self._repo = SampleRepository(self._db)
        self._project_path = file_path
        self._project_name = self._db.get_meta("project_name") or os.path.splitext(os.path.basename(file_path))[0]
        self._modified = False

        sample_count = self._repo.get_sample_count()
        pdf_count = self._repo.get_pdf_count()
        logger.info(f"项目已打开: {file_path} ({sample_count} 样本, {pdf_count} PDF)")
        return self._db

    def save_project(self) -> str:
        """保存当前项目（提交数据库事务）。"""
        if self._db is None:
            raise RuntimeError("没有打开的项目。")
        self._db.conn.commit()
        self._modified = False
        logger.info(f"项目已保存: {self._project_path}")
        return self._project_path

    def save_as_project(self, new_path: str) -> str:
        """另存为新文件。"""
        if self._db is None:
            raise RuntimeError("没有打开的项目。")
        old_path = self._project_path
        self._db.conn.commit()
        self._db.close()

        if old_path and old_path != new_path:
            shutil.copy2(old_path, new_path)

        self._db = create_database(new_path)
        self._repo = SampleRepository(self._db)
        self._project_path = new_path
        self._project_name = os.path.splitext(os.path.basename(new_path))[0]
        self._db._set_meta("project_name", self._project_name)
        self._modified = False

        logger.info(f"项目已另存为: {new_path}")
        return new_path

    def close_project(self):
        """关闭当前项目。"""
        if self._db:
            self._db.close()
        self._db = None
        self._repo = None
        self._project_path = None
        self._project_name = "未命名项目"
        self._modified = False
        logger.info("项目已关闭")

    def _close_current(self):
        """关闭当前打开的项目（内部使用）。"""
        if self._db:
            self._db.close()
            self._db = None
            self._repo = None
            self._project_path = None
            self._project_name = "未命名项目"
            self._modified = False

    def get_summary(self) -> dict:
        """获取项目概要信息。"""
        if self._db is None or self._repo is None:
            return {"samples": 0, "pdfs": 0, "classified": 0, "name": "无"}

        samples = self._repo.get_sample_count()
        pdfs = self._repo.get_pdf_count()
        classified = 0
        try:
            row = self._db.conn.execute(
                "SELECT COUNT(*) as cnt FROM geochem_samples WHERE granite_type IS NOT NULL AND granite_type != ''"
            ).fetchone()
            if row:
                classified = row["cnt"]
        except Exception:
            pass

        return {
            "name": self._project_name,
            "path": self._project_path,
            "samples": samples,
            "pdfs": pdfs,
            "classified": classified,
            "modified": self._modified,
        }
