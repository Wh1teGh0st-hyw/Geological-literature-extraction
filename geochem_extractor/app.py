"""GeoChemExtractor 应用程序入口点。

启动 PySide6 QApplication，加载 Claude 主题，显示主窗口。
"""

import sys
import os
from pathlib import Path
from loguru import logger

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from geochem_extractor.ui.main_window import MainWindow
from geochem_extractor.ui.theme import APP_STYLESHEET, Colors
from geochem_extractor.version import __version__


def configure_logging():
    """配置日志系统。"""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    # 移除默认 handler
    logger.remove()

    # 控制台输出（彩色）
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
    )

    # 文件输出
    logger.add(
        log_dir / "geochem_extractor_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )

    logger.info(f"GeoChemExtractor v{__version__} 启动")


def main():
    """应用程序主入口。"""
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("GeoChemExtractor")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("GeochemResearch")

    # 全局字体设置
    font = QFont("Microsoft YaHei", 9)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    # 应用 Claude 主题
    app.setStyleSheet(APP_STYLESHEET)

    # 设置高DPI支持
    try:
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass  # Qt6 中已默认启用

    try:
        window = MainWindow()
        window.show()
        logger.info("主窗口已显示")

        exit_code = app.exec()
        logger.info(f"应用程序退出 (code={exit_code})")
        sys.exit(exit_code)

    except Exception as e:
        logger.exception(f"应用程序崩溃: {e}")
        QMessageBox.critical(
            None, "程序错误",
            f"GeoChemExtractor 遇到严重错误:\n\n{str(e)}\n\n"
            f"请查看日志文件获取详细信息。"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
