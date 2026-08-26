"""液态玻璃 Liquid Glass 样式表(暗色底 + 半透明玻璃层 + 高光描边)。

依据《液态玻璃UI 风格.md》v2.0 设计 Token:
  背景渐变  #141B4D -> #2A1E5C -> #4B3A8F(光斑由 BackgroundWidget 自绘)
  玻璃基底  glass-1 rgba(255,255,255,10) / glass-2 rgba(255,255,255,14) / glass-3 rgba(255,255,255,20)
  高光描边  rgba(255,255,255,90) 1px;强调 rgba(255,255,255,160)
  文字      主 rgba(255,255,255,230) / 次 rgba(255,255,255,150) / 弱 rgba(255,255,255,90)
  语义色    成功 #43A047 / 警告 #FB8C00 / 危险 #E53935 / 焦点琥珀 #FFD54F
  选中底色  rgba(63,81,181,90)
  圆角      输入 6px / 按钮 8px / 卡片 12px / 弹窗 16px
"""

QSS = """
/* ============ 全局 ============ */
QMainWindow, QDialog {
    background: transparent;
}
QWidget {
    font-family: "Microsoft YaHei UI", "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
    color: rgba(255,255,255,230);
}

/* ============ 顶部应用栏 ============ */
#HeaderBar {
    background: rgba(255,255,255,10);
    border-bottom: 1px solid rgba(255,255,255,30);
}
#AppLogo {
    background: rgba(255,255,255,20);
    color: #FFD54F;
    border: 1px solid rgba(255,255,255,45);
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
}
#AppTitle {
    font-size: 15px;
    font-weight: 600;
    color: rgba(255,255,255,230);
}
#AppSubtitle {
    font-size: 11px;
    color: rgba(255,255,255,90);
}
#WindowBtn {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: rgba(255,255,255,160);
    font-size: 13px;
    padding: 4px 10px;
}
#WindowBtn:hover {
    background: rgba(255,255,255,16);
}
#WindowBtnClose {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: rgba(255,255,255,160);
    font-size: 13px;
    padding: 4px 10px;
}
#WindowBtnClose:hover {
    background: #E53935;
    color: #FFFFFF;
}

/* ============ 按钮(四态) ============ */
QPushButton {
    background: rgba(255,255,255,26);
    border: 1px solid rgba(255,255,255,120);
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 12px;
    color: rgba(255,255,255,230);
}
QPushButton:hover {
    background: rgba(255,255,255,40);
    border-color: rgba(255,255,255,170);
}
QPushButton:pressed {
    background: rgba(255,255,255,18);
}
QPushButton:disabled {
    color: rgba(255,255,255,80);
    background: rgba(255,255,255,10);
    border-color: rgba(255,255,255,30);
}
QPushButton#PrimaryButton {
    background: rgba(255,213,79,225);
    color: #1A1400;
    border: none;
    font-weight: 500;
}
QPushButton#PrimaryButton:hover {
    background: rgba(255,213,79,255);
}
QPushButton#PrimaryButton:pressed {
    background: rgba(255,213,79,180);
}
QPushButton#PrimaryButton:disabled {
    background: rgba(255,213,79,90);
    color: rgba(26,20,0,120);
}
QPushButton#GhostButton {
    background: transparent;
    border: 1px solid rgba(255,255,255,80);
    color: rgba(255,255,255,180);
}
QPushButton#GhostButton:hover {
    background: rgba(255,255,255,14);
    border-color: rgba(255,255,255,130);
}

/* ============ 玻璃卡片 ============ */
#Card {
    background: rgba(255,255,255,14);
    border: 1px solid rgba(255,255,255,90);
    border-radius: 12px;
}
#CardTitle {
    font-size: 13px;
    font-weight: 600;
    color: rgba(255,255,255,230);
}
#CardCount {
    background: rgba(255,213,79,40);
    color: #FFD54F;
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 500;
}

/* ============ 输入框 / 下拉 ============ */
QLineEdit, QDoubleSpinBox, QComboBox {
    background: rgba(255,255,255,10);
    border: 1px solid rgba(255,255,255,70);
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    color: rgba(255,255,255,230);
    selection-background-color: rgba(63,81,181,120);
}
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid rgba(255,213,79,170);
    background: rgba(255,255,255,16);
}
QLineEdit#KeyEdit {
    color: rgba(255,255,255,90);
    letter-spacing: 1px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: rgba(52,46,84,240);
    border: 1px solid rgba(255,255,255,60);
    border-radius: 8px;
    color: rgba(255,255,255,230);
    selection-background-color: rgba(63,81,181,120);
    outline: none;
}

/* ============ 复选框 ============ */
QCheckBox {
    font-size: 12px;
    color: rgba(255,255,255,170);
    spacing: 8px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid rgba(255,255,255,70);
    border-radius: 4px;
    background: rgba(255,255,255,10);
}
QCheckBox::indicator:checked {
    background: #FFD54F;
    border-color: #FFD54F;
}

/* ============ 文件列表 ============ */
#FileList {
    background: rgba(255,255,255,8);
    border: 1px solid rgba(255,255,255,25);
    border-radius: 8px;
    outline: none;
}
#FileList::item {
    padding: 6px 8px;
    margin: 2px 4px;
    border-radius: 6px;
    color: rgba(255,255,255,230);
}
#FileList::item:selected {
    background: rgba(63,81,181,90);
}
#FileList::item:hover {
    background: rgba(255,255,255,8);
}

/* ============ 进度条 ============ */
QProgressBar {
    background: rgba(255,255,255,16);
    border: none;
    border-radius: 3px;
    text-align: center;
}
QProgressBar::chunk {
    background: rgba(255,213,79,210);
    border-radius: 3px;
}

/* ============ 选项卡 ============ */
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    padding: 9px 14px;
    font-size: 12px;
    color: rgba(255,255,255,120);
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #FFD54F;
    font-weight: 500;
    border-bottom: 2px solid #FFD54F;
}
QTabBar::tab:hover:!selected {
    color: rgba(255,255,255,200);
}

/* ============ 表格 ============ */
QTableWidget {
    background: rgba(255,255,255,8);
    border: 1px solid rgba(255,255,255,25);
    border-radius: 8px;
    gridline-color: transparent;
    font-size: 12px;
}
QTableWidget::item {
    padding: 4px 6px;
    color: rgba(255,255,255,230);
}
QTableWidget::item:selected {
    background: rgba(63,81,181,90);
    color: rgba(255,255,255,255);
}
QHeaderView::section {
    background: rgba(255,255,255,10);
    border: none;
    border-bottom: 1px solid rgba(255,255,255,25);
    padding: 7px 6px;
    font-size: 11px;
    font-weight: 500;
    color: rgba(255,255,255,150);
}
QTableCornerButton::section {
    background: rgba(255,255,255,10);
    border: none;
}

/* ============ 只读文本 ============ */
QPlainTextEdit {
    background: rgba(255,255,255,8);
    border: 1px solid rgba(255,255,255,25);
    border-radius: 8px;
    font-size: 12px;
    color: rgba(255,255,255,230);
    selection-background-color: rgba(63,81,181,120);
}

/* ============ 状态栏 ============ */
QStatusBar {
    background: rgba(255,255,255,8);
    border-top: 1px solid rgba(255,255,255,25);
    font-size: 12px;
    color: rgba(255,255,255,90);
}
QStatusBar::item {
    border: none;
}

/* ============ 滚动条 ============ */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,30);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255,255,255,50);
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,30);
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
