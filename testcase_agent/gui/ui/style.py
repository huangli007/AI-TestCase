"""GUI 样式表:对齐 v2 稿图的视觉设计(浅色主题,靛蓝主色)。

设计令牌:
  主色      #2F4FC4 / hover #2741A8 / 按下 #223B96
  背景      #F6F7F9(窗口)、#FFFFFF(卡片)
  边框      #E5E7EB、输入框 #D5DAE1
  文本      #1F2329(主)、#5A6270(次)、#8A919E(弱)
  成功      #0F8A6B
  危险      #C0392B
  文件图标  TXT #4A7BDD / IMG #0F8A6B / VID #C25E3A
"""

QSS = """
/* ---------- 全局 ---------- */
QMainWindow, QDialog {
    background: #F6F7F9;
}
QWidget {
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #1F2329;
}

/* ---------- 顶部工具栏 ---------- */
#HeaderBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
}
#AppLogo {
    background: #2F4FC4;
    color: #FFFFFF;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
}
#AppTitle {
    font-size: 15px;
    font-weight: 600;
    color: #1F2329;
}
#AppSubtitle {
    font-size: 11px;
    color: #8A919E;
}
#StatusDot {
    background: #0F8A6B;
    border-radius: 4px;
}
#StatusText {
    font-size: 12px;
    color: #0F8A6B;
}

/* ---------- 按钮 ---------- */
QPushButton {
    background: #FFFFFF;
    border: 1px solid #D5DAE1;
    border-radius: 7px;
    padding: 6px 16px;
    font-size: 12px;
    color: #4A5568;
}
QPushButton:hover {
    background: #F3F5F8;
    border-color: #B9C1CC;
}
QPushButton:pressed {
    background: #E9EDF2;
}
QPushButton:disabled {
    color: #B4BAC3;
    background: #F6F7F9;
    border-color: #E5E7EB;
}
QPushButton#PrimaryButton {
    background: #2F4FC4;
    color: #FFFFFF;
    border: 1px solid #2F4FC4;
    font-weight: 500;
    padding: 7px 22px;
}
QPushButton#PrimaryButton:hover {
    background: #2741A8;
}
QPushButton#PrimaryButton:pressed {
    background: #223B96;
}
QPushButton#PrimaryButton:disabled {
    background: #A9BCEB;
    border-color: #A9BCEB;
    color: #FFFFFF;
}
QPushButton#GhostButton {
    background: transparent;
    border: 1px solid #D5DAE1;
    color: #2F4FC4;
}
QPushButton#GhostButton:hover {
    background: #EEF2FD;
}

/* ---------- 卡片 ---------- */
#Card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
#CardTitle {
    font-size: 13px;
    font-weight: 600;
    color: #1F2329;
}
#CardCount {
    background: #EAF0FE;
    color: #2F4FC4;
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 500;
}

/* ---------- 输入框 ---------- */
QLineEdit, QDoubleSpinBox {
    background: #FFFFFF;
    border: 1px solid #D5DAE1;
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 12px;
    color: #1F2329;
    selection-background-color: #2F4FC4;
}
QLineEdit:focus, QDoubleSpinBox:focus {
    border: 1px solid #2F4FC4;
}
QLineEdit#KeyEdit {
    color: #8A919E;
    letter-spacing: 1px;
}
QFormLabel {
    font-size: 12px;
    color: #5A6270;
}

/* ---------- 复选框 ---------- */
QCheckBox {
    font-size: 12px;
    color: #3A4150;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #C3CAD3;
    border-radius: 4px;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #2F4FC4;
    border-color: #2F4FC4;
    image: none;
}

/* ---------- 文件列表 ---------- */
#FileList {
    background: #FBFBFC;
    border: 1px solid #EDF0F3;
    border-radius: 8px;
    outline: none;
}
#FileList::item {
    padding: 6px 8px;
    margin: 2px 4px;
    border-radius: 6px;
    color: #1F2329;
}
#FileList::item:selected {
    background: #EAF0FE;
    color: #2F4FC4;
}
#FileList::item:hover {
    background: #F0F3F8;
}

/* ---------- 进度条 ---------- */
QProgressBar {
    background: #EDF0F3;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2F4FC4;
    border-radius: 3px;
}

/* ---------- 选项卡 ---------- */
QTabWidget::pane {
    border: none;
    background: #FFFFFF;
}
QTabBar::tab {
    background: transparent;
    padding: 9px 14px;
    font-size: 12px;
    color: #6B7280;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #2F4FC4;
    font-weight: 500;
    border-bottom: 2px solid #2F4FC4;
}
QTabBar::tab:hover:!selected {
    color: #2F4FC4;
}

/* ---------- 表格 ---------- */
QTableWidget {
    background: #FFFFFF;
    border: 1px solid #EDF0F3;
    border-radius: 8px;
    gridline-color: #F0F2F5;
    font-size: 12px;
}
QTableWidget::item {
    padding: 4px 6px;
    color: #1F2329;
}
QTableWidget::item:selected {
    background: #EAF0FE;
    color: #1F2329;
}
QHeaderView::section {
    background: #F8F9FB;
    border: none;
    border-bottom: 1px solid #EDF0F3;
    padding: 7px 6px;
    font-size: 11px;
    font-weight: 500;
    color: #8A919E;
}
QTableCornerButton::section {
    background: #F8F9FB;
    border: none;
}

/* ---------- 只读文本 ---------- */
QPlainTextEdit {
    background: #FFFFFF;
    border: 1px solid #EDF0F3;
    border-radius: 8px;
    font-size: 12px;
    color: #1F2329;
    selection-background-color: #2F4FC4;
}

/* ---------- 状态栏 ---------- */
QStatusBar {
    background: #FFFFFF;
    border-top: 1px solid #E5E7EB;
    font-size: 12px;
    color: #8A919E;
}
QStatusBar::item {
    border: none;
}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #D3D8E0;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #B9C1CC;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #D3D8E0;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0; width: 0;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}
"""
