#!/usr/bin/env bash
# GeoChemExtractor — 一键打包脚本 (Windows)
# 使用: cd GeoChemExtractor && bash scripts/build_exe.bat
# 或: cd GeoChemExtractor && source venv/Scripts/activate && bash scripts/build_exe.sh

set -e

echo "🔨 GeoChemExtractor PyInstaller 打包脚本"
echo "========================================="

# 检查环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到虚拟环境，请先创建: python -m venv venv"
    exit 1
fi

source venv/Scripts/activate

# 确保 pyinstaller 已安装
pip install pyinstaller --quiet

# 清理旧构建
echo "🧹 清理旧构建..."
rm -rf build dist *.spec

# 构建 spec 文件（动态生成以包含所有隐藏导入）
echo "📦 分析依赖..."

HIDDEN_IMPORTS=(
    "PySide6.QtCore" "PySide6.QtGui" "PySide6.QtWidgets" "PySide6.QtSql"
    "pandas._libs" "pandas.io.sql"
    "numpy._core" "numpy.random"
    "pdfminer" "pdfminer.pdfparser" "pdfminer.pdfdocument"
    "pdfplumber._version"
    "fitz"
    "openpyxl.styles" "openpyxl.utils"
    "loguru._better_exceptions"
    "pydantic" "pydantic.deprecated"
    "pydantic_core"
    "matplotlib" "matplotlib.backends.backend_qtagg" "matplotlib.backends.backend_agg"
    "matplotlib.backends.backend_qt5agg"
    "PIL" "PIL._imaging" "PIL.Image"
    "scipy.sparse" "scipy.spatial" "scipy.optimize"
    "skimage" "skimage.filters"
)

EXCLUDES=(
    "tkinter" "test" "unittest" "pdb" "profile" "cProfile"
    "email" "http" "html" "xml" "xmlrpc" "urllib3"
    "IPython" "jupyter" "notebook" "ipykernel" "debugpy"
    "pip" "setuptools" "wheel" "pkg_resources"
)

# 构建命令行参数
HIDDEN_ARGS=""
for imp in "${HIDDEN_IMPORTS[@]}"; do
    HIDDEN_ARGS="$HIDDEN_ARGS --hidden-import $imp"
done

EXCLUDE_ARGS=""
for exc in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude-module $exc"
done

echo "🔧 开始打包..."
pyinstaller \
    --name="GeoChemExtractor" \
    --noconsole \
    --onefile \
    --clean \
    --add-data "geochem_extractor:geochem_extractor" \
    --icon=NONE \
    $HIDDEN_ARGS \
    $EXCLUDE_ARGS \
    geochem_extractor/app.py 2>&1 | tail -20

echo ""
echo "========================================="
echo "✅ 打包完成!"
echo "输出文件: dist/GeoChemExtractor.exe"
echo "========================================="
