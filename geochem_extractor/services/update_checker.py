"""自动更新检测 — 检查 GitHub Releases 中的新版本。"""

import json
import urllib.request
from typing import Optional, Dict, Any
from loguru import logger

from PySide6.QtWidgets import QMessageBox, QPushButton
from PySide6.QtCore import QObject, Signal

REPO_OWNER = "Wh1teGh0st-hyw"
REPO_NAME = "Geological-literature-extraction"
CURRENT_VERSION = "0.1.0"


class UpdateChecker(QObject):
    """GitHub Releases 更新检测器。"""

    update_available = Signal(str, str)  # (new_version, download_url)

    def __init__(self, parent=None):
        super().__init__(parent)

    def check(self) -> Optional[Dict[str, Any]]:
        """检查 GitHub 上的最新发布版本。

        如果网络不可用或 API 限制，静默地返回 None。
        """
        api_url = (
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
            f"/releases/latest"
        )

        try:
            req = urllib.request.Request(api_url)
            req.add_header("Accept", "application/vnd.github.v3+json")
            req.add_header("User-Agent", "GeoChemExtractor-UpdateChecker")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            latest_version = data.get("tag_name", "").lstrip("v")
            html_url = data.get("html_url", "")
            download_url = ""

            # 找 Windows exe 文件的下载链接
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".exe") and "windows" in name.lower():
                    download_url = asset.get("browser_download_url", "")
                    break
            if not download_url and data.get("assets"):
                # 取第一个 exe 文件
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".exe"):
                        download_url = asset.get("browser_download_url", "")
                        break

            if not latest_version:
                return None

            if self._is_newer(latest_version):
                logger.info(f"发现新版本: v{latest_version}")
                self.update_available.emit(latest_version, download_url or html_url)
                return {
                    "version": latest_version,
                    "url": download_url or html_url,
                    "current": CURRENT_VERSION,
                }

            logger.debug(f"已是最新版本: v{CURRENT_VERSION}")
            return None

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.debug("仓库尚无正式 Release")
                return None
            logger.debug(f"更新检测 HTTP {e.code}: {e.reason}")
            return None
        except Exception as e:
            logger.debug(f"更新检测不可用: {e}")
            return None

    def _is_newer(self, remote_version: str) -> bool:
        """比较版本号。"""

        def parse(v: str):
            parts = v.strip().lower().lstrip("v").split(".")
            result = []
            for p in parts:
                # 处理 pre-release 后缀
                try:
                    base = ""
                    for c in p:
                        if c.isdigit():
                            base += c
                        else:
                            break
                    result.append(int(base) if base else 0)
                except (ValueError, IndexError):
                    result.append(0)
            return tuple(result)

        try:
            return parse(remote_version) > parse(CURRENT_VERSION)
        except Exception:
            return False

    @staticmethod
    def show_update_dialog(parent, version: str, download_url: str):
        """显示更新提示对话框。"""
        msg = QMessageBox(parent)
        msg.setWindowTitle("发现新版本")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"GeoChemExtractor 新版本 v{version} 可用！")
        msg.setInformativeText(
            f"当前版本: v{CURRENT_VERSION}\n"
            f"新版本: v{version}\n\n"
            f"是否前往 GitHub 下载更新？"
        )

        download_btn = msg.addButton("前往下载", QMessageBox.AcceptRole)
        later_btn = msg.addButton("稍后提醒", QMessageBox.RejectRole)
        msg.setDefaultButton(download_btn)

        msg.exec()

        if msg.clickedButton() == download_btn:
            import webbrowser
            webbrowser.open(download_url)


def check_for_updates_silent() -> Optional[Dict[str, Any]]:
    """后台静默检测更新。"""
    checker = UpdateChecker()
    return checker.check()
