"""文本解析器测试(txt/md/csv/json/docx/pdf)。"""

from pathlib import Path

import pytest

from testcase_agent.parsers.text_parser import extract_text

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


class TestTextParser:
    def test_md(self):
        text = extract_text(str(SAMPLES / "sample_prd.md"))
        assert "智能待办清单 App" in text
        assert "任务管理" in text

    def test_txt(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("第一行\n第二行", encoding="utf-8")
        assert extract_text(str(f)) == "第一行\n第二行"

    def test_csv(self, tmp_path):
        f = tmp_path / "d.csv"
        f.write_text("id,name\n1,张三\n2,李四", encoding="utf-8")
        text = extract_text(str(f))
        assert "张三" in text and "id" in text

    def test_json(self, tmp_path):
        f = tmp_path / "d.json"
        f.write_text('{"module": "登录", "feature": "验证码"}', encoding="utf-8")
        text = extract_text(str(f))
        assert "验证码" in text

    def test_docx(self, tmp_path):
        import docx
        doc = docx.Document()
        doc.add_paragraph("文档段落内容")
        p = tmp_path / "d.docx"
        doc.save(str(p))
        text = extract_text(str(p))
        assert "文档段落内容" in text

    def test_pdf(self, tmp_path):
        from pypdf import PdfWriter
        w = PdfWriter()
        from pypdf.generic import DecodedStreamObject, NameObject
        page = w.add_blank_page(width=200, height=200)
        w.add_metadata({"/Title": "PDF 测试"})
        p = tmp_path / "d.pdf"
        with open(p, "wb") as fh:
            w.write(fh)
        text = extract_text(str(p))  # 空白 PDF 无文本,不应抛异常
        assert isinstance(text, str)

    def test_unsupported_raises(self, tmp_path):
        f = tmp_path / "a.exe"
        f.write_bytes(b"MZ")
        with pytest.raises(ValueError):
            extract_text(str(f))

    def test_docx_missing_dependency_hint(self, tmp_path, monkeypatch):
        """docx 解析缺依赖时,错误信息应包含 pip install 命令。"""
        import builtins
        from testcase_agent.parsers import text_parser

        # 模拟 import docx 失败
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "docx":
                raise ImportError("No module named 'docx'")
            return real_import(name, *args, **kwargs)

        f = tmp_path / "x.docx"
        f.write_bytes(b"")
        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(RuntimeError, match="pip install python-docx"):
            extract_text(str(f))

    def test_pdf_missing_dependency_hint(self, tmp_path, monkeypatch):
        from testcase_agent.parsers import text_parser
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("No module named 'pypdf'")
            return real_import(name, *args, **kwargs)

        f = tmp_path / "x.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(RuntimeError, match="pip install pypdf"):
            extract_text(str(f))
