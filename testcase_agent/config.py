"""配置加载:支持 YAML 文件 + 环境变量插值 + 命令行覆盖。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import yaml

_ENV_PATTERN = re.compile(r"^\$\{(\w+)(?::(.*))?\}$")


def _interpolate(value):
    """支持 ${ENV_NAME} 与 ${ENV_NAME:default} 两种环境变量插值。"""
    if isinstance(value, str):
        m = _ENV_PATTERN.match(value.strip())
        if m:
            name, default = m.group(1), m.group(2)
            if name in os.environ and os.environ[name] != "":
                return os.environ[name]
            return default or ""
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


@dataclass
class LLMConfig:
    """大模型配置(兼容任意 OpenAI 风格 API)。打包发布版不含任何预设 API 配置,由用户自行填写。"""

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    vision_model: str = ""          # 视觉模型,如 gpt-4o / qwen-vl-max / deepseek-vl;留空表示与 model 相同
    temperature: float = 0.6
    max_retries: int = 3
    timeout: int = 120

    @property
    def vision_enabled(self) -> bool:
        return bool(self.vision_model) or "vl" in self.model.lower() or "vision" in self.model.lower() or "gpt-4o" in self.model.lower()


@dataclass
class PipelineConfig:
    """管线参数。"""

    max_frames_per_video: int = 12      # 每个视频最多抽帧数
    frame_interval: float = 2.0         # 抽帧间隔(秒)
    max_image_size: int = 1280          # 图片最长边(发送给模型前压缩)
    review_enabled: bool = True         # 是否开启质量评审阶段
    mock_mode: bool = False             # 离线 Mock 模式(无需 API Key,用于演示/测试)
    max_cases: int = 80                 # 用例总数上限


@dataclass
class ExportConfig:
    """导出配置。"""

    formats: List[str] = field(default_factory=lambda: ["xlsx", "md", "json"])


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    export: ExportConfig = field(default_factory=ExportConfig)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        """加载配置:path 为空时使用默认值 + 环境变量。"""
        raw: dict = {}
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        raw = _interpolate(raw)

        llm_raw = raw.get("llm", {})
        pipe_raw = raw.get("pipeline", {})
        exp_raw = raw.get("export", {})

        llm = LLMConfig(
            base_url=llm_raw.get("base_url", os.environ.get("LLM_BASE_URL", LLMConfig.base_url)),
            api_key=llm_raw.get("api_key", os.environ.get("LLM_API_KEY", "")),
            model=llm_raw.get("model", os.environ.get("LLM_MODEL", LLMConfig.model)),
            vision_model=llm_raw.get("vision_model", os.environ.get("LLM_VISION_MODEL", "")),
            temperature=llm_raw.get("temperature", LLMConfig.temperature),
            max_retries=llm_raw.get("max_retries", LLMConfig.max_retries),
            timeout=llm_raw.get("timeout", LLMConfig.timeout),
        )

        pipeline = PipelineConfig(
            max_frames_per_video=pipe_raw.get("max_frames_per_video", PipelineConfig.max_frames_per_video),
            frame_interval=pipe_raw.get("frame_interval", PipelineConfig.frame_interval),
            max_image_size=pipe_raw.get("max_image_size", PipelineConfig.max_image_size),
            review_enabled=pipe_raw.get("review_enabled", PipelineConfig.review_enabled),
            mock_mode=pipe_raw.get("mock_mode", PipelineConfig.mock_mode),
            max_cases=pipe_raw.get("max_cases", PipelineConfig.max_cases),
        )

        export = ExportConfig(formats=exp_raw.get("formats") or ["xlsx", "md", "json"])

        return cls(llm=llm, pipeline=pipeline, export=export)
