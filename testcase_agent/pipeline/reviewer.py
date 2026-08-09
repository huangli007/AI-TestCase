"""阶段三:质量评审器 —— 对照产品分析修正用例集(补漏、去重、修正)。"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from .. import models
from ..llm import LLMError
from ..llm.normalize import normalize_review
from ..prompts import build_review_messages

logger = logging.getLogger(__name__)


class Reviewer:
    def __init__(self, llm):
        self.llm = llm

    def review(self, analysis: models.ProductAnalysis, cases: List[models.TestCase]) -> models.ReviewResult:
        analysis_json = analysis.model_dump_json()
        cases_json = json.dumps([c.model_dump() for c in cases], ensure_ascii=False, indent=2)
        messages = build_review_messages(analysis_json, cases_json)

        data = self.llm.complete_json(messages, temperature=0.3, stage="review")
        # 规整评审输出(枚举/字段兜底),cases 为空时回退原用例集
        rev = normalize_review(data)
        if not rev["cases"]:
            rev["cases"] = cases
        result = models.ReviewResult(
            summary=rev["summary"], gaps=rev["gaps"], issues=rev["issues"], cases=rev["cases"]
        )
        # 归一化编号
        for idx, c in enumerate(result.cases, start=1):
            c.case_id = f"TC-{idx:03d}"
        logger.info(
            "评审完成: 补充 %d 个遗漏点, 修正 %d 个问题, 最终 %d 条用例",
            len(result.gaps), len(result.issues), len(result.cases),
        )
        return result
