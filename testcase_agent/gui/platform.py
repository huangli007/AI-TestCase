"""跨平台适配层:路径、配置目录、字体、打开目录等平台差异收敛点。

Windows / macOS 双平台使用同一套代码,差异全部收敛在此模块。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices, QFont

APP_NAME = "TestCaseAgent"
ORG_NAME = "TestCaseAgent"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform == "win32"


def app_config_dir() -> Path:
    """应用配置目录:Windows=%APPDATA%/TestCaseAgent, macOS=~/Library/Application Support/TestCaseAgent。"""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    if not base:
        base = str(Path.home() / (".testcase-agent" if not is_windows() else "AppData/Roaming/TestCaseAgent"))
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file_path() -> Path:
    return app_config_dir() / "config.json"


def ui_font_family() -> str:
    """中文字体:Windows 用微软雅黑,macOS 用 PingFang SC,回退系统默认。"""
    if is_windows():
        return "Microsoft YaHei UI"
    if is_macos():
        return "PingFang SC"
    return ""


def apply_default_font(app=None):
    """设置默认字体(优先系统中文字体)。保证双平台中文渲染一致。"""
    from PySide6.QtWidgets import QApplication
    target = app or QApplication.instance()
    if target is None:
        return
    family = _resolve_cjk_family()
    font = QFont(family) if family else QFont()
    font.setPointSize(10)
    target.setFont(font)


def _resolve_cjk_family() -> str:
    """从系统中文字体候选中挑出实际可用的第一个。"""
    candidates = [
        "Microsoft YaHei UI", "Microsoft YaHei", "SimHei",
        "PingFang SC", "Hiragino Sans GB",
        "Noto Sans CJK SC", "Source Han Sans CN", "WenQuanYi Zen Hei",
        "Microsoft JhengHei", "Arial Unicode MS",
    ]
    try:
        from PySide6.QtGui import QFontDatabase
        available = set(QFontDatabase.families())
        for name in candidates:
            if name in available:
                return name
    except Exception:  # noqa: BLE001
        pass
    return is_windows() and "Microsoft YaHei" or (is_macos() and "PingFang SC" or "")


def open_in_file_manager(path: str | Path) -> None:
    """在系统文件管理器中打开目录(Windows=资源管理器, macOS=Finder)。"""
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
