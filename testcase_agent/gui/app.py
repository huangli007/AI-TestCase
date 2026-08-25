"""主窗口:按 v2 稿图实现的跨平台桌面界面。

布局:
  顶部工具栏(Logo / 标题 / 状态 / 保存配置 / 开始生成)
  左列:输入素材卡片
  右列:模型配置卡片 + 运行选项卡片 + 运行状态卡片
  底部:结果选项卡(产品分析 / 测试点清单 / 测试用例 / 评审报告)
  状态栏
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFrame, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QStatusBar, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout,
    QWidget,
)

# 国内主流 OpenAI 兼容厂家(联动 base_url / 文本模型 / 视觉模型)
PROVIDERS = [
    {"name": "DeepSeek",
     "base_url": "https://api.deepseek.com/v1",
     "text_models": ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
     "vision_models": ["deepseek-vl"]},
    {"name": "通义千问 Qwen",
     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "text_models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
     "vision_models": ["qwen-vl-max", "qwen-vl-plus"]},
    {"name": "智谱 GLM",
     "base_url": "https://open.bigmodel.cn/api/paas/v4",
     "text_models": ["glm-4-plus", "glm-4-flash", "glm-4-air", "glm-4-long"],
     "vision_models": ["glm-4v-plus", "glm-4v"]},
    {"name": "月之暗面 Kimi",
     "base_url": "https://api.moonshot.cn/v1",
     "text_models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
     "vision_models": ["moonshot-v1-8k-vision-preview"]},
    {"name": "百川",
     "base_url": "https://api.baichuan-ai.com/v1",
     "text_models": ["Baichuan4-Turbo", "Baichuan4-Air"],
     "vision_models": []},
    {"name": "豆包 Doubao",
     "base_url": "https://ark.cn-beijing.volces.com/api/v3",
     "text_models": ["doubao-pro-32k", "doubao-lite-32k", "doubao-pro-128k"],
     "vision_models": ["doubao-vision-pro-32k"]},
    {"name": "腾讯混元",
     "base_url": "https://api.hunyuan.tencent.com/v1",
     "text_models": ["hunyuan-turbo", "hunyuan-pro"],
     "vision_models": ["hunyuan-vision"]},
    {"name": "OpenAI",
     "base_url": "https://api.openai.com/v1",
     "text_models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
     "vision_models": ["gpt-4o", "gpt-4o-mini"]},
    {"name": "自定义…", "base_url": "", "text_models": [], "vision_models": []},
]
_PROVIDER_INDEX = {p["name"]: i for i, p in enumerate(PROVIDERS)}

from .. import models
from ..config import AppConfig
from ..exporters import export_all
from . import platform
from .ui import QSS
from .worker import AgentWorker, ModelFetchWorker, filter_vision_models

# 文件类型图标配色(TXT / IMG / VID)
TYPE_STYLE = {
    "TXT": "#4A7BDD", "MD": "#4A7BDD", "DOCX": "#4A7BDD", "PDF": "#4A7BDD", "CSV": "#4A7BDD",
    "IMG": "#0F8A6B", "PNG": "#0F8A6B", "JPG": "#0F8A6B",
    "VID": "#C25E3A", "MP4": "#C25E3A", "MOV": "#C25E3A",
}
TEXT_EXTS = {".txt", ".md", ".markdown", ".csv", ".json", ".log", ".yaml", ".yml", ".html", ".docx", ".pdf"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}
VID_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}

PRIORITY_COLORS = {
    "P0": ("#FDECEC", "#C0392B"),
    "P1": ("#FEF3E2", "#B7791F"),
    "P2": ("#EAF0FE", "#2F4FC4"),
    "P3": ("#F1F3F5", "#6B7280"),
}


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


class FileItemWidget(QWidget):
    """素材列表的自定义条目:类型徽标 + 文件名 + 大小 + 移除按钮。"""

    remove_clicked = Signal(object)

    def __init__(self, path: str, parent_item: "QListWidgetItem", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(10)

        is_url = path.strip().startswith(("http://", "https://"))
        if is_url:
            t, color = "URL", "#7C5CE0"
        else:
            t = _type_label(path)
            color = TYPE_STYLE.get(t, "#888780")
        badge = QLabel(t)
        badge.setFixedSize(36, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background:{color};color:#FFFFFF;border-radius:5px;"
            f"font-size:11px;font-weight:500;"
        )
        lay.addWidget(badge)

        # 链接显示域名,文件显示文件名
        if is_url:
            display = path.split("//")[-1][:48]
        else:
            display = os.path.basename(path)
        name = QLabel(display)
        name.setStyleSheet("color:#1F2329;font-size:13px;")
        name.setMinimumWidth(120)
        name.setToolTip(path)
        lay.addWidget(name, 1)

        if is_url:
            sz = "在线原型"
        else:
            try:
                sz = _human_size(os.path.getsize(path))
            except OSError:
                sz = ""
        size_lbl = QLabel(sz)
        size_lbl.setStyleSheet("color:#9AA1AC;font-size:11px;")
        size_lbl.setMinimumWidth(60)
        size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(size_lbl)

        self._parent_item = parent_item
        btn = QPushButton("×")
        btn.setFixedSize(20, 20)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#B4BAC3;font-size:14px;}"
            "QPushButton:hover{color:#C0392B;}"
        )
        btn.clicked.connect(lambda: self.remove_clicked.emit(self._parent_item))
        lay.addWidget(btn)

    def sizeHint(self):  # noqa: D102
        return QSize(super().sizeHint().width(), 40)

    def minimumSizeHint(self):  # noqa: N802
        return self.sizeHint()


def _type_label(path: str) -> str:
    ext = Path(path).suffix[1:].upper() or "FILE"
    if ext in ("JPG", "JPEG"):
        return "IMG"
    if ext == "MARKDOWN":
        return "MD"
    return ext if ext in TYPE_STYLE else "FILE"


class FileListWidget(QListWidget):
    """支持拖拽文件的素材列表(只接受外部文件 URL,禁用内部拖拽重排)。"""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("FileList")
        self.setSpacing(2)
        # 禁用 QListWidget 内置 drag/drop(避免与外部文件 drop 冲突)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.setDefaultDropAction(Qt.DropAction.IgnoreAction)
        self.setMovement(QListWidget.Movement.Static)
        self.setUniformItemSizes(True)

    def _is_file_url(self, mime) -> bool:
        return mime.hasUrls() and any(u.isLocalFile() for u in mime.urls())

    def dragEnterEvent(self, event):  # noqa: N802
        if self._is_file_url(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # noqa: N802
        if self._is_file_url(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # noqa: N802
        event.accept()

    def dropEvent(self, event):  # noqa: N802
        if not self._is_file_url(event.mimeData()):
            event.ignore()
            return
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()


class StepIndicator(QWidget):
    """阶段步骤指示器:分析 ✓ 生成 ✓ 评审(当前)。"""

    STEPS = ["分析", "生成", "评审"]

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._dots: list[QLabel] = []
        for i, name in enumerate(self.STEPS):
            if i:
                sep = QLabel("—")
                sep.setStyleSheet("color:#D5DAE1;font-size:11px;")
                lay.addWidget(sep)
            dot = QLabel("✓")
            dot.setFixedSize(18, 18)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setStyleSheet("color:#9AA1AC;background:#E5E7EB;border-radius:9px;font-size:10px;font-weight:500;")
            lay.addWidget(dot)
            lbl = QLabel(name)
            lbl.setStyleSheet("color:#8A919E;font-size:12px;")
            lay.addWidget(lbl)
            self._dots.append((dot, lbl))
        self.set_current(0)

    def set_current(self, idx: int):
        """idx: 0-based 当前阶段;已完成阶段显示对勾。"""
        for i, (dot, lbl) in enumerate(self._dots):
            if i < idx:
                dot.setText("✓")
                dot.setStyleSheet("color:#FFFFFF;background:#0F8A6B;border-radius:9px;font-size:10px;font-weight:500;")
                lbl.setStyleSheet("color:#5A6270;font-size:12px;")
            elif i == idx:
                dot.setText(str(i + 1))
                dot.setStyleSheet("color:#FFFFFF;background:#2F4FC4;border-radius:9px;font-size:10px;font-weight:500;")
                lbl.setStyleSheet("color:#2F4FC4;font-size:12px;font-weight:500;")
            else:
                dot.setText(str(i + 1))
                dot.setStyleSheet("color:#9AA1AC;background:#E5E7EB;border-radius:9px;font-size:10px;font-weight:500;")
                lbl.setStyleSheet("color:#8A919E;font-size:12px;")

    def reset(self):
        for i, (dot, lbl) in enumerate(self._dots):
            dot.setText(str(i + 1))
            dot.setStyleSheet("color:#9AA1AC;background:#E5E7EB;border-radius:9px;font-size:10px;font-weight:500;")
            lbl.setStyleSheet("color:#8A919E;font-size:12px;")


def _card(title: str) -> tuple[QWidget, QVBoxLayout]:
    w = QWidget()
    w.setObjectName("Card")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(14, 10, 14, 10)
    lay.setSpacing(7)
    t = QLabel(title)
    t.setObjectName("CardTitle")
    t.setStyleSheet("font-size:14px;font-weight:600;color:#1F2329;margin-bottom:2px;")
    t.setMinimumWidth(80)  # 防标题被压缩显示成单字
    lay.addWidget(t)
    return w, lay


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "formlabel")
    lbl.setStyleSheet("font-size:12px;color:#5A6270;")
    lbl.setMinimumWidth(60)  # 防 label 被压缩显示成单字
    return lbl


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TestCase Agent — AI 测试用例生成器")
        self.resize(1320, 920)
        self.setMinimumSize(1100, 780)
        self.setAcceptDrops(True)   # 主窗口接收外部文件拖入(简化为统一入口)

        self._result: Optional[models.GenerationResult] = None
        self._worker: Optional[AgentWorker] = None
        self._output_dir: str = "output"

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 8)
        body_lay.setSpacing(16)
        body_lay.addWidget(self._build_left_panel(), 5)
        body_lay.addWidget(self._build_right_panel(), 8)
        # 配置区(body)优先占高度,结果区(tabs)生成前较小
        root.addWidget(body, 8)
        root.addWidget(self._build_tabs(), 3)
        self.setStatusBar(QStatusBar())

        self.setStyleSheet(QSS)
        self._apply_status("就绪", ok=True)
        self._refresh_export_buttons()

    # ------------------------------------------------------------------ #
    # 构建
    # ------------------------------------------------------------------ #
    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("HeaderBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(10)

        logo = QLabel("TC")
        logo.setObjectName("AppLogo")
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("TestCase Agent")
        title.setObjectName("AppTitle")
        sub = QLabel("AI 测试用例生成器")
        sub.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        lay.addLayout(title_box)

        lay.addStretch(1)

        self._status_dot = QLabel()
        self._status_dot.setFixedSize(8, 8)
        self._status_dot.setStyleSheet("background:#0F8A6B;border-radius:4px;")
        self._status_text = QLabel("就绪")
        self._status_text.setObjectName("StatusText")
        lay.addWidget(self._status_dot)
        lay.addWidget(self._status_text)
        lay.addSpacing(12)

        btn_save = QPushButton("保存配置")
        btn_save.clicked.connect(self._save_config)
        lay.addWidget(btn_save)
        btn_load = QPushButton("加载配置")
        btn_load.clicked.connect(self._load_config)
        lay.addWidget(btn_load)

        self._btn_run = QPushButton("开始生成")
        self._btn_run.setObjectName("PrimaryButton")
        self._btn_run.clicked.connect(self._on_run)
        lay.addWidget(self._btn_run)
        return bar

    def _build_left_panel(self) -> QWidget:
        card, lay = _card("素材")

        self._count_lbl = QLabel("0")
        self._count_lbl.setObjectName("CardCount")
        card_title_row = QHBoxLayout()
        card_title_row.addWidget(QLabel("素材"))
        card_title_row.addWidget(self._count_lbl)
        card_title_row.addStretch(1)
        lay.removeWidget(lay.itemAt(0).widget())
        lay.insertLayout(0, card_title_row)

        self.file_list = FileListWidget()
        self.file_list.files_dropped.connect(self._add_files)
        lay.addWidget(self.file_list, 1)

        btns = QHBoxLayout()
        b_add = QPushButton("+ 添加文件")
        b_add.clicked.connect(self._on_add_files)
        b_link = QPushButton("🔗 链接")
        b_link.setToolTip("添加 Figma / MasterGo 原型图分享链接,自动读取页面截图")
        b_link.clicked.connect(self._on_add_link)
        b_rm = QPushButton("移除")
        b_rm.clicked.connect(self._on_remove_selected)
        b_clr = QPushButton("清空")
        b_clr.clicked.connect(self.file_list.clear)
        for b in (b_add, b_link, b_rm, b_clr):
            btns.addWidget(b)
        lay.addLayout(btns)

        hint = QLabel("拖拽文件到列表,或点击添加")
        hint.setStyleSheet("color:#8A919E;font-size:12px;border:1px dashed #CDD3DB;border-radius:8px;padding:10px;background:#FBFBFC;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)

        fmt = QLabel("支持 txt / md / docx / pdf / csv · png / jpg · mp4 / mov")
        fmt.setStyleSheet("color:#9AA1AC;font-size:11px;")
        fmt.setWordWrap(True)
        lay.addWidget(fmt)
        return card

    def _build_right_panel(self) -> QWidget:
        # 外层滚动容器:内容超出窗口高度时可滚动,保证任何屏幕尺寸都不遮挡
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(400)

        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # ---- 模型配置卡片(不内置任何 API 配置,全部由用户选择/填写) ----
        m_card, m_lay = _card("模型配置")

        # 厂家下拉(初始未选中)
        self._in_provider = QComboBox()
        self._in_provider.setEditable(False)
        self._in_provider.setMinimumHeight(32)
        for p in PROVIDERS:
            self._in_provider.addItem(p["name"])
        self._in_provider.setCurrentIndex(-1)
        self._in_provider.setPlaceholderText("请选择厂家(自动填 Base URL)")
        self._in_provider.currentIndexChanged.connect(self._on_provider_changed)

        self._btn_fetch_models = QPushButton("⟳ 拉取")
        self._btn_fetch_models.setObjectName("GhostButton")
        self._btn_fetch_models.setToolTip("从 /models 接口实时拉取该厂家可用模型")
        self._btn_fetch_models.setMinimumHeight(32)
        self._btn_fetch_models.clicked.connect(self._on_fetch_models)

        # 模型下拉(可编辑,初始为空)
        self._in_text_model = QComboBox()
        self._in_text_model.setEditable(True)
        self._in_text_model.setMinimumHeight(32)
        self._in_text_model.setCurrentText("")
        self._in_text_model.currentTextChanged.connect(self._on_text_model_changed)

        self._in_vision_model = QComboBox()
        self._in_vision_model.setEditable(True)
        self._in_vision_model.setMinimumHeight(32)
        self._in_vision_model.setCurrentText("")
        self._in_vision_model.currentTextChanged.connect(self._on_vision_model_changed)

        self._in_base = QLineEdit("")
        self._in_base.setMinimumHeight(32)
        self._in_base.setPlaceholderText("https://... 选择厂家后自动填充")
        self._in_key = QLineEdit()
        self._in_key.setObjectName("KeyEdit")
        self._in_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._in_key.setPlaceholderText("sk-...")
        self._in_key.setMinimumHeight(32)
        self._in_temp = QDoubleSpinBox()
        self._in_temp.setRange(0.0, 1.5)
        self._in_temp.setSingleStep(0.1)
        self._in_temp.setValue(0.6)
        self._in_temp.setMinimumHeight(32)

        # 厂家行(下拉 + 拉取按钮)
        m_lay.addWidget(_label("厂家"))
        prov_row = QHBoxLayout()
        prov_row.setSpacing(8)
        prov_row.addWidget(self._in_provider, 1)
        prov_row.addWidget(self._btn_fetch_models)
        m_lay.addLayout(prov_row)

        m_lay.addWidget(_label("Base URL(OpenAI 兼容)"))
        m_lay.addWidget(self._in_base)
        m_lay.addWidget(_label("API Key"))
        m_lay.addWidget(self._in_key)

        # 双模型一行
        r2 = QHBoxLayout()
        r2.setSpacing(10)
        for lbl, w in (("文本模型", self._in_text_model), ("视觉模型", self._in_vision_model)):
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(_label(lbl))
            col.addWidget(w)
            r2.addLayout(col)
        m_lay.addLayout(r2)

        # 拉取状态提示(只显示运行时状态,不显示静态提示文字,避免冗余)
        self._fetch_hint = QLabel(" ")
        self._fetch_hint.setStyleSheet("color:#9AA1AC;font-size:11px;")
        self._fetch_hint.setWordWrap(True)
        self._fetch_hint.setMinimumWidth(0)

        # 温度 + 拉取提示合并一行(节省垂直空间)
        temp_row = QHBoxLayout()
        temp_row.setSpacing(8)
        temp_row.addWidget(_label("温度"))
        temp_row.addWidget(self._in_temp)
        temp_row.addSpacing(10)
        temp_row.addWidget(self._fetch_hint, 1)
        m_lay.addLayout(temp_row)
        lay.addWidget(m_card)

        # ---- 运行选项卡片 ----
        o_card, o_lay = _card("运行选项")
        self._in_outdir = QLineEdit("output")
        b_browse = QPushButton("浏览")
        b_browse.setObjectName("GhostButton")
        b_browse.clicked.connect(self._on_browse_outdir)
        out_row = QHBoxLayout()
        out_row.addWidget(self._in_outdir, 1)
        out_row.addWidget(b_browse)
        o_lay.addWidget(_label("输出目录"))
        o_lay.addLayout(out_row)

        self._chk_review = QCheckBox("质量评审(补漏 / 去重 / 修正)")
        self._chk_review.setChecked(True)
        self._chk_mock = QCheckBox("离线演示模式(Mock,免 Key)")
        # 复选框并排一行
        chk_row = QHBoxLayout()
        chk_row.setSpacing(16)
        chk_row.addWidget(self._chk_review)
        chk_row.addWidget(self._chk_mock)
        chk_row.addStretch(1)
        o_lay.addLayout(chk_row)

        # 原型图平台 Token(可选,并排一列,用于读取 Figma/MasterGo 链接截图)
        self._in_figma_token = QLineEdit()
        self._in_figma_token.setPlaceholderText("Figma 个人访问令牌(可选)")
        self._in_figma_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._in_mastergo_token = QLineEdit()
        self._in_mastergo_token.setPlaceholderText("MasterGo 令牌(可选)")
        self._in_mastergo_token.setEchoMode(QLineEdit.EchoMode.Password)
        tok_row = QHBoxLayout()
        tok_row.setSpacing(10)
        for lbl, w in (("Figma Token", self._in_figma_token), ("MasterGo Token", self._in_mastergo_token)):
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(_label(lbl))
            col.addWidget(w)
            tok_row.addLayout(col)
        o_lay.addLayout(tok_row)
        lay.addWidget(o_card)

        # ---- 运行状态卡片 ----
        s_card, s_lay = _card("运行状态")
        self._steps = StepIndicator()
        s_lay.addWidget(self._steps)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        s_lay.addWidget(self._progress)
        self._stage_text = QLabel("等待开始…")
        self._stage_text.setStyleSheet("color:#8A919E;font-size:12px;")
        s_lay.addWidget(self._stage_text)
        lay.addWidget(s_card)

        lay.addStretch(1)
        scroll.setWidget(panel)
        return scroll

    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()

        self._txt_analysis = QPlainTextEdit()
        self._txt_analysis.setReadOnly(True)
        self.tabs.addTab(self._txt_analysis, "产品分析")

        self._tbl_points = QTableWidget(0, 6)
        self._tbl_points.setHorizontalHeaderLabels(["编号", "模块", "测试点", "类型", "优先级", "描述"])
        self._setup_table(self._tbl_points, [70, 90, 150, 70, 60, 300])
        self.tabs.addTab(self._tbl_points, "测试点清单")

        self._tbl_cases = QTableWidget(0, 6)
        self._tbl_cases.setHorizontalHeaderLabels(["编号", "模块", "测试点", "用例标题", "优先级", "类型"])
        self._setup_table(self._tbl_cases, [70, 80, 130, 300, 60, 60])
        self.tabs.addTab(self._tbl_cases, "测试用例")

        self._txt_review = QPlainTextEdit()
        self._txt_review.setReadOnly(True)
        self.tabs.addTab(self._txt_review, "评审报告")

        return self.tabs

    @staticmethod
    def _setup_table(tbl: QTableWidget, widths: List[int]):
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = tbl.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i, w in enumerate(widths):
            tbl.setColumnWidth(i, w)

    # ------------------------------------------------------------------ #
    # 主窗口拖拽支持(整窗口接收外部文件)
    # ------------------------------------------------------------------ #
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # noqa: N802
        if not (event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls())):
            event.ignore()
            return
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self._add_files(paths)
            self.file_list.setFocus()
            event.acceptProposedAction()

    # ------------------------------------------------------------------ #
    # 厂家联动
    # ------------------------------------------------------------------ #
    def _on_provider_changed(self, idx: int):
        if idx < 0 or idx >= len(PROVIDERS):
            return
        p = PROVIDERS[idx]
        # 厂家改变:刷新 Base URL 与模型下拉
        if p["base_url"]:
            self._in_base.setText(p["base_url"])
        self._in_text_model.blockSignals(True)
        self._in_text_model.clear()
        self._in_text_model.addItems(p["text_models"] or [])
        self._in_text_model.setCurrentText((p["text_models"] or [""])[0])
        self._in_text_model.blockSignals(False)

        self._in_vision_model.blockSignals(True)
        self._in_vision_model.clear()
        self._in_vision_model.addItems(p["vision_models"] or [""])
        self._in_vision_model.setCurrentText((p["vision_models"] or [""])[0])
        self._in_vision_model.blockSignals(False)

    def _on_text_model_changed(self, _t: str):
        # 视觉模型暂不强联动,留给用户自行选择
        pass

    def _on_vision_model_changed(self, _t: str):
        pass

    # ------------------------------------------------------------------ #
    # 拉取厂家模型
    # ------------------------------------------------------------------ #
    def _on_fetch_models(self):
        base_url = self._in_base.text().strip()
        api_key = self._in_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先填写 API Key,再拉取该厂家的模型列表。")
            return
        if not base_url:
            QMessageBox.warning(self, "提示", "请先填写 Base URL。")
            return

        self._btn_fetch_models.setEnabled(False)
        self._btn_fetch_models.setText("拉取中…")
        self._fetch_hint.setText(f"正在请求 {base_url}/models …")

        self._fetch_worker = ModelFetchWorker(base_url, api_key)
        self._fetch_worker.fetched.connect(self._on_models_fetched)
        self._fetch_worker.failed.connect(self._on_models_fetch_failed)
        self._fetch_worker.start()

    def _on_models_fetched(self, model_ids: list):
        self._btn_fetch_models.setEnabled(True)
        self._btn_fetch_models.setText("⟳ 拉取厂家模型")

        # 保留用户当前已选值(若存在于新列表中)
        cur_text = self._in_text_model.currentText().strip()
        cur_vision = self._in_vision_model.currentText().strip()

        vision_ids = filter_vision_models(model_ids)
        self._in_text_model.blockSignals(True)
        self._in_text_model.clear()
        self._in_text_model.addItems(model_ids)
        if cur_text in model_ids:
            self._in_text_model.setCurrentText(cur_text)
        self._in_text_model.blockSignals(False)

        self._in_vision_model.blockSignals(True)
        self._in_vision_model.clear()
        self._in_vision_model.addItems(vision_ids if vision_ids else model_ids)
        if cur_vision in (vision_ids or model_ids):
            self._in_vision_model.setCurrentText(cur_vision)
        self._in_vision_model.blockSignals(False)

        self._fetch_hint.setText(f"已拉取 {len(model_ids)} 个模型,视觉候选 {len(vision_ids)} 个")
        self.statusBar().showMessage(f"模型拉取成功:共 {len(model_ids)} 个,视觉 {len(vision_ids)} 个")

    def _on_models_fetch_failed(self, err: str):
        self._btn_fetch_models.setEnabled(True)
        self._btn_fetch_models.setText("⟳ 拉取厂家模型")
        self._fetch_hint.setText("拉取失败,请检查 Base URL 与 API Key")
        QMessageBox.critical(self, "拉取模型失败",
                             f"无法从该厂家获取模型列表:\n{err}\n\n"
                             "请检查 Base URL 是否正确(需支持 OpenAI 兼容 /models 接口)、"
                             "API Key 是否有效,或手动在模型下拉框中输入。")

    # ------------------------------------------------------------------ #
    # 素材管理
    # ------------------------------------------------------------------ #
    def _add_files(self, paths: List[str]):
        existing = {self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.file_list.count())}
        for p in paths:
            is_url = p.strip().startswith(("http://", "https://"))
            if p in existing or (not is_url and not os.path.exists(p)):
                continue
            item = QListWidgetItem(self.file_list)
            item.setData(Qt.ItemDataRole.UserRole, p)
            # 自定义 widget 承载徽标/文件名/大小/移除
            widget = FileItemWidget(p, item)
            widget.remove_clicked.connect(self._on_remove_item)
            item.setSizeHint(widget.sizeHint())
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, widget)
        self._count_lbl.setText(str(self.file_list.count()))
        self.file_list.updateGeometry()

    def _on_remove_item(self, item):
        if item is not None:
            self.file_list.takeItem(self.file_list.row(item))
            self._count_lbl.setText(str(self.file_list.count()))

    def _on_add_link(self):
        """弹出输入框粘贴原型图链接(Figma / MasterGo)。"""
        url, ok = QInputDialog.getText(
            self, "添加原型图链接",
            "粘贴 Figma / MasterGo 原型图分享链接:\n(读取页面截图作为素材,提高测试用例准确度)")
        if ok and url.strip():
            self._add_files([url.strip()])

    def _on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择素材文件",
            "",
            "素材文件 (*.txt *.md *.docx *.pdf *.csv *.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.mp4 *.mov *.avi *.mkv *.webm *.flv *.wmv *.m4v);;所有文件 (*)")
        if paths:
            self._add_files(paths)

    def _on_remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self._count_lbl.setText(str(self.file_list.count()))

    def _on_browse_outdir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", self._in_outdir.text() or ".")
        if d:
            self._in_outdir.setText(d)

    def _collect_files(self) -> List[str]:
        return [self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.file_list.count())]

    # ------------------------------------------------------------------ #
    # 运行
    # ------------------------------------------------------------------ #
    def _build_config(self) -> AppConfig:
        cfg = AppConfig.load()
        cfg.llm.base_url = self._in_base.text().strip() or cfg.llm.base_url
        cfg.llm.api_key = self._in_key.text().strip()
        cfg.llm.model = self._in_text_model.currentText().strip() or cfg.llm.model
        cfg.llm.vision_model = self._in_vision_model.currentText().strip()
        cfg.llm.temperature = self._in_temp.value()
        cfg.pipeline.review_enabled = self._chk_review.isChecked()
        cfg.pipeline.mock_mode = self._chk_mock.isChecked()
        cfg.prototype.figma_token = self._in_figma_token.text().strip()
        cfg.prototype.mastergo_token = self._in_mastergo_token.text().strip()
        self._output_dir = self._in_outdir.text().strip() or "output"
        return cfg

    def _on_run(self):
        if self._worker and self._worker.isRunning():
            return
        files = self._collect_files()
        if not files:
            QMessageBox.warning(self, "提示", "请先添加素材文件(文本 / 图片 / 视频)。")
            return
        cfg = self._build_config()
        if not cfg.pipeline.mock_mode and not cfg.llm.api_key:
            QMessageBox.warning(
                self, "提示",
                "未配置 API Key。\n\n请在右侧填写 API Key,或勾选「离线演示模式(Mock)」体验完整流程。")
            return

        self._set_running(True)
        self._progress.setValue(0)
        self._steps.reset()
        self._stage_text.setText("正在解析素材…")
        self.statusBar().showMessage("开始生成…")

        self._worker = AgentWorker(files, self._output_dir, cfg,
                                   review=None if cfg.pipeline.review_enabled else False)
        self._worker.stage.connect(self._on_stage)
        self._worker.progress.connect(lambda msg: self.statusBar().showMessage(msg))
        self._worker.stage_done.connect(self._on_stage_done)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_stage(self, cur: int, total: int, name: str):
        self._steps.set_current(cur - 1)
        self._progress.setValue(int(cur * 100 / total))
        self._stage_text.setText(f"阶段 {cur}/{total}: {name}…")

    def _on_stage_done(self, stage: str, payload):
        """分阶段实时填充 UI:分析完成→产品分析/测试点 tab,生成完成→用例 tab,评审完成→评审 + 最终用例。"""
        if stage == "analysis":
            analysis = payload
            self._populate_analysis(analysis)
            self._populate_test_points(analysis.test_points)
            self.tabs.setCurrentIndex(0)
            self.statusBar().showMessage("阶段 1 完成:产品分析已生成")
        elif stage == "cases":
            analysis, cases = payload
            self._populate_test_points(analysis.test_points)
            self._populate_cases(cases)
            self.tabs.setCurrentIndex(2)
            self.statusBar().showMessage(f"阶段 2 完成:已生成 {len(cases)} 条用例")
        elif stage == "review":
            review = payload
            self._populate_cases(review.cases)
            self._populate_review(review)
            self.tabs.setCurrentIndex(3)
            self.statusBar().showMessage(
                f"阶段 3 完成:补充 {len(review.gaps)} 遗漏点, 修正 {len(review.issues)} 问题")

    def _on_finished(self, result: models.GenerationResult):
        self._result = result
        self._set_running(False)
        self._progress.setValue(100)
        self._steps.set_current(len(StepIndicator.STEPS))
        self._stage_text.setText("全部完成 ✓")
        self._apply_status("完成", ok=True)
        self._enable_export_buttons(True)
        # 兜底再填一次(评审或 fallback 路径下可能 stage_done 没覆盖)
        self._populate_result(result)
        self.statusBar().showMessage(
            f"产品「{result.product_name}」共 {len(result.cases)} 条用例,已导出至 {self._output_dir}")

    def _on_failed(self, err: str):
        self._set_running(False)
        self._progress.setValue(0)
        self._apply_status("失败", ok=False)
        self._stage_text.setText("生成失败")
        self.statusBar().showMessage("生成失败")
        hint = ""
        if "python-docx" in err or "pypdf" in err or "imageio-ffmpeg" in err:
            hint = ("\n\n可能你用了未安装依赖的 Python。请使用本项目的 venv 启动:\n"
                    "  C:/Users/TianManyi/.workbuddy/binaries/python/envs/default/Scripts/python.exe run_gui.py\n"
                    "或在当前 Python 中安装缺失依赖后重启。")
        QMessageBox.critical(self, "生成失败", err + hint)

    def _set_running(self, running: bool):
        self._btn_run.setEnabled(not running)
        self._btn_run.setText("生成中…" if running else "开始生成")
        self.file_list.setEnabled(not running)

    def _apply_status(self, text: str, ok: bool):
        color = "#0F8A6B" if ok else "#C0392B"
        self._status_dot.setStyleSheet(f"background:{color};border-radius:4px;")
        self._status_text.setStyleSheet(f"font-size:12px;color:{color};")
        self._status_text.setText(text)

    # ------------------------------------------------------------------ #
    # 结果展示(分阶段实时填充)
    # ------------------------------------------------------------------ #
    def _populate_result(self, r: models.GenerationResult):
        """三阶段全部完成后的兜底填充。"""
        self._populate_analysis(r.analysis)
        self._populate_test_points(r.analysis.test_points)
        self._populate_cases(r.cases)
        if r.review:
            self._populate_review(r.review)
        else:
            self._txt_review.setPlainText("(未启用质量评审)")

    def _populate_analysis(self, a: models.ProductAnalysis):
        """阶段一完成后立即填充产品分析 tab。"""
        lines = [
            f"产品名称: {a.product_name}",
            f"产品类型: {a.product_type}",
            f"目标用户: {a.target_users}",
            f"核心价值: {a.core_value}",
            "",
            "【功能模块】",
        ]
        for m in a.modules:
            lines.append(f"- {m.module} / {m.feature}")
            for rule in m.rules:
                lines.append(f"    · {rule}")
        if a.business_flows:
            lines.append("")
            lines.append("【关键业务流程】")
            for b in a.business_flows:
                lines.append(f"- {b.name}: {b.description}")
        if a.risk_points:
            lines.append("")
            lines.append("【风险点】")
            for rp in a.risk_points:
                lines.append(f"- {rp}")
        self._txt_analysis.setPlainText("\n".join(lines))
        from PySide6.QtGui import QTextCursor
        self._txt_analysis.moveCursor(QTextCursor.MoveOperation.Start)
        self.tabs.setTabText(0, "产品分析")

    def _populate_test_points(self, test_points):
        """阶段一完成后立即填充测试点清单 tab。"""
        self._tbl_points.setRowCount(0)
        for tp in test_points:
            row = self._tbl_points.rowCount()
            self._tbl_points.insertRow(row)
            for col, val in enumerate([tp.id, tp.module, tp.name, tp.type, tp.priority, tp.description]):
                item = QTableWidgetItem(val)
                if col == 4:
                    self._paint_priority(item, tp.priority)
                self._tbl_points.setItem(row, col, item)
        self.tabs.setTabText(1, f"测试点清单({len(test_points)})")

    def _populate_cases(self, cases):
        """阶段二/三完成后填充测试用例 tab。"""
        self._tbl_cases.setRowCount(0)
        for c in cases:
            row = self._tbl_cases.rowCount()
            self._tbl_cases.insertRow(row)
            for col, val in enumerate([c.case_id, c.module, c.test_point, c.title, c.priority, c.case_type]):
                item = QTableWidgetItem(val)
                if col == 4:
                    self._paint_priority(item, c.priority)
                self._tbl_cases.setItem(row, col, item)
        self.tabs.setTabText(2, f"测试用例({len(cases)})")

    def _populate_review(self, rev: models.ReviewResult):
        parts = [f"【评审总结】{rev.summary}"]
        if rev.gaps:
            parts.append("\n【补充的遗漏点】")
            parts += [f"- {g}" for g in rev.gaps]
        if rev.issues:
            parts.append("\n【修正的问题】")
            parts += [f"- {i}" for i in rev.issues]
        self._txt_review.setPlainText("\n".join(parts))
        self.tabs.setTabText(3, "评审报告")

    @staticmethod
    def _paint_priority(item: QTableWidgetItem, priority: str):
        bg, fg = PRIORITY_COLORS.get(priority, ("#FFFFFF", "#1F2329"))
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))
        font = QFont()
        font.setBold(True)
        item.setFont(font)

    # ------------------------------------------------------------------ #
    # 导出(只创建一次按钮,后续只更新启用状态,避免累积)
    # ------------------------------------------------------------------ #
    def _refresh_export_buttons(self):
        """构建导出按钮一次,默认禁用,运行完成后启用。"""
        self._export_buttons = {}
        for label, fmt in (("导出 Excel", "xlsx"), ("导出 MD", "md"), ("导出 JSON", "json")):
            b = QPushButton(label)
            b.setObjectName("GhostButton")
            b.setEnabled(False)
            b.clicked.connect(lambda _=False, f=fmt: self._on_export(f))
            self._export_buttons[fmt] = b
            self.statusBar().addPermanentWidget(b)

    def _enable_export_buttons(self, enabled: bool):
        for b in getattr(self, "_export_buttons", {}).values():
            b.setEnabled(enabled)

    def _on_export(self, fmt: str):
        if not self._result:
            return
        try:
            paths = export_all(self._result, self._output_dir, formats=[fmt])
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(e))
            return
        if paths:
            platform.open_in_file_manager(self._output_dir)
            self.statusBar().showMessage(f"已导出: {os.path.basename(paths[0])}")

    # ------------------------------------------------------------------ #
    # 配置持久化
    # ------------------------------------------------------------------ #
    def _save_config(self):
        cfg = self._build_config()
        # 注意:API Key 不写入配置文件(密钥仅本次会话使用,不落盘、不随配置分享)
        data = {
            "base_url": cfg.llm.base_url,
            "model": cfg.llm.model,
            "vision_model": cfg.llm.vision_model,
            "temperature": cfg.llm.temperature,
            "review": cfg.pipeline.review_enabled,
            "output_dir": self._output_dir,
        }
        path = platform.config_file_path()
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "保存失败", str(e))
            return
        self.statusBar().showMessage("配置已保存(API Key 不写入配置文件,下次启动需重新填写)")

    def _load_config(self):
        path = platform.config_file_path()
        if not path.exists():
            QMessageBox.information(self, "加载配置", f"未找到配置文件:\n{path}")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "加载失败", str(e))
            return
        self._in_base.setText(data.get("base_url", ""))
        # 不恢复 API Key(配置文件不含密钥)
        self._in_text_model.setCurrentText(data.get("model", ""))
        self._in_vision_model.setCurrentText(data.get("vision_model", ""))
        self._in_temp.setValue(float(data.get("temperature", 0.6)))
        self._chk_review.setChecked(bool(data.get("review", True)))
        if data.get("output_dir"):
            self._in_outdir.setText(data["output_dir"])
        self.statusBar().showMessage("配置已加载(API Key 需重新填写)")


def run_app() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(platform.APP_NAME)
    app.setOrganizationName(platform.ORG_NAME)
    platform.apply_default_font()
    win = MainWindow()
    win.show()
    return app.exec()
