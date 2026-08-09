"""JSON 导出:完整结构化产物(便于二次处理/对接其他工具)。"""

from __future__ import annotations

import json
import os

from .. import models


def export_json(result: models.GenerationResult, output_dir: str) -> str:
    payload = {
        "product_name": result.product_name,
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "analysis": result.analysis.model_dump(),
        "review": result.review.model_dump() if result.review else None,
        "cases": [c.model_dump() for c in result.cases],
    }
    path = os.path.join(output_dir, f"{result.product_name or 'product'}_测试用例.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
