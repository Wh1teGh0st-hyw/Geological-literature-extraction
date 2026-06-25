# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['geochem_extractor\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('geochem_extractor', 'geochem_extractor')],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'pandas._libs', 'numpy._core', 'pdfplumber', 'pdfminer', 'fitz', 'openpyxl', 'loguru', 'pydantic', 'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_agg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'IPython', 'jupyter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GeoChemExtractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GeoChemExtractor',
)
