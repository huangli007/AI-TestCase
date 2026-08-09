"""OpenAI 兼容大模型客户端:可外接 DeepSeek / Qwen(通义) / OpenAI / 智谱 / Kimi 等任意 API。"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Any, List, Optional

from openai import OpenAI

from ..config import LLMConfig

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class LLMClient:
    """统一封装 OpenAI 兼容 Chat Completions 接口,支持文本 / 视觉 / JSON 结构化输出。"""

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        if not cfg.api_key:
            raise LLMError(
                "未配置 API Key。请在 config.yaml 中设置 llm.api_key(或环境变量 LLM_API_KEY),"
                "或使用 --mock 参数运行离线演示模式。"
            )
        self.client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, timeout=cfg.timeout)

    # ------------------------------------------------------------------ #
    # 基础能力
    # ------------------------------------------------------------------ #
    @property
    def vision_enabled(self) -> bool:
        return self.cfg.vision_enabled

    def complete(self, messages: List[dict], *, temperature: float = 0.6,
                 max_tokens: Optional[int] = None, model: Optional[str] = None,
                 json_mode: bool = False) -> str:
        """调用对话补全接口,返回文本。"""
        kwargs: dict[str, Any] = {
            "model": model or self.cfg.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_err: Exception | None = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                if content.strip():
                    return content
                raise LLMError("模型返回了空内容")
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt < self.cfg.max_retries:
                    wait = 2 ** attempt
                    logger.warning("LLM 调用失败(%s),%.1fs 后重试...", e, wait)
                    time.sleep(wait)
        raise LLMError(f"LLM 调用最终失败: {last_err}")

    def complete_json(self, messages: List[dict], *, temperature: float = 0.5,
                      max_tokens: Optional[int] = None, model: Optional[str] = None,
                      stage: str = "") -> dict:
        """调用接口并强制解析为 JSON 字典(含容错:代码块剥离、截断修复)。

        stage 仅用于离线 Mock 客户端路由,真实客户端忽略。
        """
        text = self.complete(messages, temperature=temperature, max_tokens=max_tokens,
                             model=model, json_mode=True)
        return parse_json(text)

    # ------------------------------------------------------------------ #
    # 视觉能力
    # ------------------------------------------------------------------ #
    def vision_analyze(self, text: str, image_data_uris: List[str],
                       *, temperature: float = 0.4) -> dict:
        """将文本指令 + 多张图片(base64 data URI)发送给视觉模型,返回 JSON 分析。"""
        if not image_data_uris:
            return {}
        model = self.cfg.vision_model or self.cfg.model
        content: list[dict] = [{"type": "text", "text": text}]
        content += [
            {"type": "image_url", "image_url": {"url": uri}} for uri in image_data_uris
        ]
        messages = [
            {"role": "system", "content": "你是一个严谨的多模态产品分析助手,只输出合法 JSON。"},
            {"role": "user", "content": content},
        ]
        text = self.complete(messages, temperature=temperature, model=model, json_mode=True)
        return parse_json(text)


def parse_json(text: str) -> dict:
    """容错解析模型输出中的 JSON(处理代码块、前后缀、截断等)。"""
    if not text:
        raise LLMError("模型返回空内容,无法解析 JSON")
    text = text.strip()
    # 剥离 ```json ... ``` 代码块
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 定位最外层 JSON 起点(首个 { 或 [)
    start = len(text)
    for ch in ("{", "["):
        idx = text.find(ch)
        if idx != -1 and idx < start:
            start = idx

    if start < len(text):
        # 尝试以最后一个闭合括号截断,并允许补尾括号(应对 max_tokens 截断)
        for end_char in ("}", "]"):
            end = text.rfind(end_char)
            if end > start:
                for tail in ("", "}", "]"):
                    candidate = text[start:end + 1] + tail
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        continue
    raise LLMError(f"无法从模型输出中解析 JSON。输出预览: {text[:200]}")


def encode_image_to_data_uri(image_path: str, fmt: str = "JPEG", mime: str = "image/jpeg") -> str:
    """将图片文件编码为 base64 data URI。"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"
