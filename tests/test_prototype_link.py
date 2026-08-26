"""原型图链接解析测试:Figma/MasterGo 链接识别、截图拉取(带 mock)。"""

from pathlib import Path

import pytest

from testcase_agent.parsers.prototype_link import (
    fetch_figma_screenshots, fetch_prototype_screenshots, is_prototype_url,
    parse_prototype_url,
)


class TestParseUrl:
    def test_figma_design(self):
        assert parse_prototype_url("https://www.figma.com/design/AbC123XyZ/title?node-id=1-2") == ("figma", "AbC123XyZ")

    def test_figma_file(self):
        assert parse_prototype_url("https://www.figma.com/file/KlM456Qwe/App-UI") == ("figma", "KlM456Qwe")

    def test_mastergo(self):
        assert parse_prototype_url("https://mastergo.com/file/Mg987Abc?tab=one") == ("mastergo", "Mg987Abc")

    def test_unsupported(self):
        with pytest.raises(ValueError):
            parse_prototype_url("https://www.not-design-tool.com/file/abc")

    def test_is_prototype_url(self):
        assert is_prototype_url("https://www.figma.com/design/abc/tt")
        assert is_prototype_url("https://mastergo.com/file/abc")
        assert not is_prototype_url("https://example.com/x.png")


class TestFetchFigma:
    def test_network_error_returns_error(self, tmp_path, monkeypatch):
        """API 请求失败时返回错误而非抛出。"""
        import requests

        def fake_get(*args, **kwargs):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr(requests, "get", fake_get)
        paths, errors = fetch_figma_screenshots(
            "https://www.figma.com/design/AbC123XyZ/t", "tok", str(tmp_path))
        assert paths == []
        assert errors and "Figma" in errors[0]

    def test_no_token_graceful(self, tmp_path, monkeypatch):
        """无 Token 时降级浏览器截图;未装 playwright 时返回安装提示。"""
        monkeypatch.setattr(
            "testcase_agent.parsers.prototype_link.browser_screenshot",
            lambda *a, **k: (_ for _ in ()).throw(ImportError("no playwright")))
        paths, errors = fetch_prototype_screenshots(
            "https://www.figma.com/design/AbC123XyZ/t", str(tmp_path))
        assert paths == []
        assert any("playwright" in e or "Token" in e for e in errors)


class TestFetchMastergo:
    def test_no_playwright_hint(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "testcase_agent.parsers.prototype_link.browser_screenshot",
            lambda *a, **k: (_ for _ in ()).throw(ImportError("no playwright")))
        paths, errors = fetch_prototype_screenshots(
            "https://mastergo.com/file/Mg987Abc", str(tmp_path))
        assert paths == []
        assert any("playwright" in e for e in errors)

    def test_screenshot_success(self, tmp_path, monkeypatch):
        def fake_shot(url, out, timeout=45):
            Path(out).write_bytes(b"\x89PNG")
        monkeypatch.setattr(
            "testcase_agent.parsers.prototype_link.browser_screenshot", fake_shot)
        paths, errors = fetch_prototype_screenshots(
            "https://mastergo.com/file/Mg987Abc", str(tmp_path))
        assert len(paths) == 1 and Path(paths[0]).exists()
        assert errors == []


class TestWebUrl:
    def test_web_page_screenshot(self, tmp_path, monkeypatch):
        """任意网页原型链接(GitHub Pages / H5 原型)也应支持浏览器截图。"""
        def fake_shot(url, out, timeout=45):
            Path(out).write_bytes(b"\x89PNG")
        monkeypatch.setattr(
            "testcase_agent.parsers.prototype_link.browser_screenshot", fake_shot)
        paths, errors = fetch_prototype_screenshots(
            "https://malstromnaef-afk.github.io/agent-pc/index.html?prototype=large", str(tmp_path))
        assert len(paths) == 1 and Path(paths[0]).exists()
        assert errors == []

    def test_web_page_import_error_hint(self, tmp_path, monkeypatch):
        """未安装 playwright 时给出安装提示(而非'不支持的链接')。"""
        monkeypatch.setattr(
            "testcase_agent.parsers.prototype_link.browser_screenshot",
            lambda *a, **k: (_ for _ in ()).throw(ImportError("no playwright")))
        paths, errors = fetch_prototype_screenshots(
            "https://example.com/proto/index.html", str(tmp_path))
        assert paths == []
        assert any("playwright" in e for e in errors)
