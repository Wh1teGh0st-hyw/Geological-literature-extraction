# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 — GeoChemExtractor Windows .exe

使用方法:
    cd GeoChemExtractor
    PyInstaller build_windows.spec

输出:
    dist/GeoChemExtractor.exe
"""

import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(".").resolve()

a = Analysis(
    ["geochem_extractor/app.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # 日志目录 (运行时自动创建)
    ],
    hiddenimports=[
        # PySide6
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "PySide6.QtSql",
        # pandas / numpy
        "pandas._libs", "pandas.io.sql",
        "numpy._core", "numpy.random",
        # PDF 库
        "pdfminer", "pdfminer.pdfparser", "pdfminer.pdfdocument",
        "pdfplumber._version",
        "fitz",  # PyMuPDF
        # openpyxl
        "openpyxl.styles", "openpyxl.utils",
        # loguru / pydantic
        "loguru._better_exceptions",
        "pydantic", "pydantic.deprecated",
        # matplotlib
        "matplotlib", "matplotlib.backends.backend_qtagg",
        "matplotlib.backends.backend_agg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "test", "unittest",
        "email", "http", "html", "xml", "xmlrpc",
        "pdb", "profile", "cProfile",
    ],
    no_warn=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GeoChemExtractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 无控制台窗口（GUI 应用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # TODO: 添加应用图标
    version="0.1.0",
)
