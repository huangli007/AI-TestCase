"""配置与 LLM JSON 容错测试。"""

import os

import pytest

from testcase_agent.config import AppConfig
from testcase_agent.llm.client import parse_json
from testcase_agent.llm.mock_client import MockLLMClient


class TestConfig:
    def test_default_values(self):
        # 打包发布版不内置任何 API 配置
        cfg = AppConfig.load(None)
        assert cfg.llm.base_url == ""
        assert cfg.llm.model == ""
        assert cfg.llm.api_key == ""
        assert cfg.pipeline.review_enabled is True
        assert cfg.pipeline.mock_mode is False
        assert cfg.export.formats == ["xlsx", "md", "json"]

    def test_env_interpolation(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "sk-test-123")
        monkeypatch.setenv("LLM_BASE_URL", "https://custom.example/v1")
        cfg = AppConfig.load(None)
        assert cfg.llm.api_key == "sk-test-123"
        assert cfg.llm.base_url == "https://custom.example/v1"

    def test_default_value_in_yaml(self, tmp_path, monkeypatch):
        # ${ENV:default} 语法:环境变量缺失时用默认值
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        yml = tmp_path / "c.yaml"
        yml.write_text(
            "llm:\n  base_url: ${LLM_BASE_URL:https://default.example/v1}\n", encoding="utf-8")
        cfg = AppConfig.load(str(yml))
        assert cfg.llm.base_url == "https://default.example/v1"

    def test_yaml_overrides(self, tmp_path):
        yml = tmp_path / "c.yaml"
        yml.write_text(
            "pipeline:\n  review_enabled: false\n  max_cases: 40\n"
            "export:\n  formats: [json]\n", encoding="utf-8")
        cfg = AppConfig.load(str(yml))
        assert cfg.pipeline.review_enabled is False
        assert cfg.pipeline.max_cases == 40
        assert cfg.export.formats == ["json"]


class TestParseJson:
    def test_plain_json(self):
        assert parse_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_with_prefix_suffix(self):
        text = '解释如下:\n{"cases": [{"case_id": "TC-001"}]}\n以上为结果'
        assert parse_json(text)["cases"][0]["case_id"] == "TC-001"

    def test_truncated_fix(self):
        # 末尾截断缺少闭合括号时,应回退到最后一个合法括号
        text = '{"a": 1, "b": [1, 2, 3]'
        assert parse_json(text)["b"] == [1, 2, 3]

    def test_invalid_raises(self):
        with pytest.raises(Exception):
            parse_json("完全不是 JSON 的内容")


class TestMockLLM:
    def test_stage_routing(self):
        mock = MockLLMClient()
        assert mock.complete_json([], stage="analyze")["test_points"]
        assert mock.complete_json([], stage="generate")["cases"]
        assert mock.complete_json([], stage="review")["cases"]
        assert mock.complete_json([], stage="review")["summary"]

    def test_vision_enabled(self):
        assert MockLLMClient().vision_enabled is True
