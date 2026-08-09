"""阶段一:产品分析器 —— 从素材生成结构化产品分析与测试点清单。"""

from __future__ import annotations

import json
import logging
from typing import List

from .. import models
from ..llm import LLMError
from ..llm.normalize import normalize_analysis
from ..prompts import build_analyze_messages

logger = logging.getLogger(__name__)


class Analyzer:
    def __init__(self, llm):
        self.llm = llm

    def analyze(self, materials: List[str]) -> models.ProductAnalysis:
        """输入素材文本列表,输出产品分析。"""
        content = "\n\n".join(f"### 素材 {i + 1}\n{m}" for i, m in enumerate(materials))
        messages = build_analyze_messages(content)

        data = self.llm.complete_json(messages, temperature=0.4, stage="analyze")
        if not data.get("test_points"):
            raise LLMError("分析结果缺少 test_points 字段,请重试或更换模型")

        # 规整 LLM 脏输出(枚举模糊匹配 + 兜底),杜绝校验崩溃
        analysis = models.ProductAnalysis.model_validate(normalize_analysis(data))
        logger.info("产品分析完成: %s, 共 %d 个测试点", analysis.product_name, len(analysis.test_points))
        return analysis

    @staticmethod
    def to_text(analysis: models.ProductAnalysis) -> str:
        """序列化为可读文本(用于生成阶段上下文)。"""
        return json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2)
