"""阶段二:用例生成器 —— 依据产品分析为每个测试点生成测试用例。"""

from __future__ import annotations

import logging
from typing import List

from .. import models
from ..llm import LLMError
from ..llm.normalize import normalize_cases_payload
from ..prompts import build_generate_messages

logger = logging.getLogger(__name__)


class Generator:
    def __init__(self, llm, max_cases: int = 80):
        self.llm = llm
        self.max_cases = max_cases

    def generate(self, analysis: models.ProductAnalysis) -> List[models.TestCase]:
        analysis_json = analysis.model_dump_json()
        messages = build_generate_messages(analysis_json, self.max_cases)

        data = self.llm.complete_json(messages, temperature=0.5, stage="generate")
        cases = normalize_cases_payload(data)
        if not cases:
            raise LLMError("生成结果缺少 cases 字段,请重试")
        cases = self._normalize_ids(cases)
        logger.info("用例生成完成: %d 条", len(cases))
        return cases

    @staticmethod
    def _normalize_ids(cases: List[models.TestCase]) -> List[models.TestCase]:
        """兜底:确保 case_id 全局唯一且连续(TC-001 起)。"""
        seen = set()
        for idx, c in enumerate(cases, start=1):
            new_id = f"TC-{idx:03d}"
            if c.case_id != new_id or c.case_id in seen:
                c.case_id = new_id
            seen.add(c.case_id)
        return cases
