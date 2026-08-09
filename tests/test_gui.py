"""GUI 冒烟测试(offscreen):窗口构建、添加文件、结果填充、拖放逻辑。"""

from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from testcase_agent.gui.app import FileListWidget, MainWindow, _type_label


class TestGuiSmoke:
    def test_mainwindow_builds(self, qapp):
        win = MainWindow()
        assert win.windowTitle().startswith("TestCase Agent")
        assert win.file_list.count() == 0
        assert win._tbl_cases.rowCount() == 0
        win.close()

    def test_add_files_and_remove(self, qapp, tmp_path):
        win = MainWindow()
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.png"
        f1.write_text("x", encoding="utf-8")
        f2.write_bytes(b"\x89PNG\r\n")
        win._add_files([str(f1), str(f2)])
        assert win.file_list.count() == 2
        assert win._count_lbl.text() == "2"
        # 重复添加去重
        win._add_files([str(f1)])
        assert win.file_list.count() == 2
        # 移除
        win._on_remove_item(win.file_list.item(0))
        assert win.file_list.count() == 1
        win.close()

    def test_populate_result(self, qapp, sample_result):
        win = MainWindow()
        win._populate_result(sample_result)
        assert win._tbl_points.rowCount() == len(sample_result.analysis.test_points)
        assert win._tbl_cases.rowCount() == len(sample_result.cases)
        assert "测试产品" in win._txt_analysis.toPlainText()
        assert "评审通过" in win._txt_review.toPlainText()
        win.close()

    def test_drop_file_emits_signal(self, qapp, tmp_path):
        w = FileListWidget()
        received = []
        w.files_dropped.connect(received.append)
        f = tmp_path / "c.md"
        f.write_text("hi", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(f))])
        ev = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        w.dropEvent(ev)
        assert received
        assert Path(received[0][0]) == f  # 规范化路径比较(正/反斜杠差异)

    def test_drop_non_file_ignored(self, qapp):
        w = FileListWidget()
        received = []
        w.files_dropped.connect(received.append)
        mime = QMimeData()
        mime.setText("纯文本拖入")
        ev = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        w.dropEvent(ev)
        assert received == []

    def test_mainwindow_drop_adds(self, qapp, tmp_path):
        win = MainWindow()
        f = tmp_path / "d.txt"
        f.write_text("x", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(f))])
        ev = QDropEvent(QPointF(100, 100), Qt.DropAction.CopyAction, mime,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        win.dropEvent(ev)
        assert win.file_list.count() == 1
        win.close()

    def test_type_label(self):
        assert _type_label("a.png") == "PNG"
        assert _type_label("a.jpg") == "IMG"
        assert _type_label("a.jpeg") == "IMG"
        assert _type_label("a.mp4") == "MP4"
        assert _type_label("a.md") == "MD"
        assert _type_label("a.docx") == "DOCX"

    def test_provider_switch_updates_models(self, qapp):
        """切换厂家应自动刷新 base_url、文本模型和视觉模型下拉。"""
        from testcase_agent.gui.app import _PROVIDER_INDEX
        win = MainWindow()
        # 初始未选中厂家,不内置任何 API 配置
        assert win._in_provider.currentIndex() == -1
        assert win._in_base.text() == ""
        assert win._in_text_model.currentText() == ""
        # 切到 通义千问
        idx = _PROVIDER_INDEX["通义千问 Qwen"]
        win._in_provider.setCurrentIndex(idx)
        assert "dashscope" in win._in_base.text()
        assert win._in_text_model.currentText() in ("qwen-plus", "qwen-turbo", "qwen-max", "qwen-long")
        assert "qwen-vl" in (win._in_vision_model.currentText() or "")
        # 切到 自定义…(允许 base_url 保留之前内容,模型下拉清空)
        win._in_provider.setCurrentIndex(_PROVIDER_INDEX["自定义…"])
        assert win._in_text_model.count() == 0  # 空厂家时模型列表为空
        win.close()

    def test_export_buttons_single_instance(self, qapp):
        """导出按钮只创建一次,多次调用不重复累积。"""
        win = MainWindow()
        # 初次 _refresh_export_buttons + 多次启用
        win._refresh_export_buttons()
        first = list(win._export_buttons.values())
        win._enable_export_buttons(True)
        win._enable_export_buttons(False)
        win._enable_export_buttons(True)
        # 不应有重复 widget
        ids = [id(b) for b in win._export_buttons.values()]
        assert len(ids) == len(set(ids))  # dict keys 唯一 → buttons 唯一
        assert len(win._export_buttons) == 3
        win.close()

    def test_stage_done_fills_tabs_progressively(self, qapp, sample_result):
        """stage_done 实时填充应让各 tab 增量更新。"""
        win = MainWindow()
        # 阶段一
        win._on_stage_done("analysis", sample_result.analysis)
        assert "测试产品" in win._txt_analysis.toPlainText()
        assert win._tbl_points.rowCount() == len(sample_result.analysis.test_points)
        # 阶段二:用例表应填充,但评审 tab 还为空
        win._on_stage_done("cases", (sample_result.analysis, sample_result.cases))
        assert win._tbl_cases.rowCount() == len(sample_result.cases)
        # 阶段三:评审 tab 填充
        win._on_stage_done("review", sample_result.review)
        assert "评审通过" in win._txt_review.toPlainText()
        win.close()

    def test_filter_vision_models(self):
        from testcase_agent.gui.worker import filter_vision_models
        ids = ["deepseek-chat", "deepseek-reasoner", "qwen-vl-max", "qwen-plus",
               "gpt-4o", "gpt-4o-mini", "glm-4v-plus", "glm-4-flash", "unknown-model"]
        vision = filter_vision_models(ids)
        assert "qwen-vl-max" in vision and "gpt-4o" in vision and "glm-4v-plus" in vision
        assert "deepseek-chat" not in vision and "unknown-model" not in vision

    def test_models_fetched_populates(self, qapp):
        """拉取成功后应填充文本/视觉模型下拉,并保留当前选择。"""
        win = MainWindow()
        win._in_text_model.setCurrentText("gpt-4o")  # 预设当前值(不存在于新列表,应被新列表覆盖)
        win._on_models_fetched(["deepseek-chat", "deepseek-reasoner", "deepseek-vl"])
        # 文本下拉含全部模型
        items = [win._in_text_model.itemText(i) for i in range(win._in_text_model.count())]
        assert "deepseek-chat" in items and "deepseek-vl" in items
        # 视觉下拉只含视觉候选(deepseek-vl 命中 "vl")
        vitems = [win._in_vision_model.itemText(i) for i in range(win._in_vision_model.count())]
        assert "deepseek-vl" in vitems and "deepseek-chat" not in vitems
        win.close()

    def test_fetch_models_requires_key(self, qapp, monkeypatch):
        """未填写 API Key 时点击拉取应提示且不发起请求。"""
        win = MainWindow()
        win._in_key.clear()
        warnings = []
        monkeypatch.setattr("testcase_agent.gui.app.QMessageBox.warning",
                            lambda *a, **k: warnings.append(a))
        win._on_fetch_models()
        assert warnings  # 弹了提示
        assert not hasattr(win, "_fetch_worker")  # 未启动 worker
        win.close()
