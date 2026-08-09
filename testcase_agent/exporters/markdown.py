"""Markdown 导出:产品分析摘要 + 测试点清单 + 测试用例表格。"""

from __future__ import annotations

import os

from .. import models


def export_markdown(result: models.GenerationResult, output_dir: str) -> str:
    a = result.analysis
    lines: list[str] = []

    lines.append(f"# {a.product_name} —— 自动生成测试用例报告\n")
    lines.append(f"- **产品类型**: {a.product_type}")
    lines.append(f"- **目标用户**: {a.target_users}")
    lines.append(f"- **核心价值**: {a.core_value}")
    lines.append(f"- **用例总数**: {len(result.cases)} 条")
    if result.review:
        lines.append(f"- **评审结论**: {result.review.summary}")
    lines.append("")

    if a.business_flows:
        lines.append("## 关键业务流程\n")
        for b in a.business_flows:
            lines.append(f"- **{b.name}**: {b.description}")
        lines.append("")

    if a.risk_points:
        lines.append("## 风险点\n")
        for r in a.risk_points:
            lines.append(f"- {r}")
        lines.append("")

    lines.append("## 测试点清单\n")
    lines.append("| 编号 | 模块 | 测试点 | 类型 | 优先级 | 描述 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for tp in a.test_points:
        inferred = " ⚠推断" if tp.inferred else ""
        lines.append(f"| {tp.id} | {tp.module} | {tp.name} | {tp.type} | {tp.priority} | {tp.description}{inferred} |")
    lines.append("")

    lines.append("## 测试用例\n")
    lines.append("| 编号 | 模块 | 测试点 | 标题 | 优先级 | 类型 | 前置条件 | 测试数据 | 步骤 | 预期结果 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for c in result.cases:
        steps = "<br>".join(f"{i}. {s}" for i, s in enumerate(c.steps, 1))
        expected = "<br>".join(f"{i}. {e}" for i, e in enumerate(c.expected, 1))
        lines.append(
            f"| {c.case_id} | {c.module} | {c.test_point} | {c.title} | {c.priority} | {c.case_type} "
            f"| {c.precondition or '-'} | {c.test_data or '-'} | {steps} | {expected} |"
        )
    lines.append("")

    if result.review and (result.review.gaps or result.review.issues):
        lines.append("## 评审补充说明\n")
        if result.review.gaps:
            lines.append("**补充的遗漏点:**")
            for g in result.review.gaps:
                lines.append(f"- {g}")
        if result.review.issues:
            lines.append("**修正的问题:**")
            for i in result.review.issues:
                lines.append(f"- {i}")
        lines.append("")

    path = os.path.join(output_dir, f"{result.product_name or 'product'}_测试用例.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
