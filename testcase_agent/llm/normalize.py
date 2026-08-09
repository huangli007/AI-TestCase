"""LLM 输出规整层:将模型返回的"脏"数据规整为合法枚举与字段,防止 pydantic 校验崩溃。

真实场景中,大模型可能返回:
- type = "并发" / "边界" / "异常"(不在允许枚举内)
- priority = "p1" / "P-1" / "高"(非法格式)
- case_type 缺失或非法
- steps/expected 为字符串而非列表

本模块通过"精确匹配 → 双向包含匹配 → 语义映射 → 兜底"四层策略规整,
保证下游 model_validate 一定通过。
"""

from __future__ import annotations

from typing import Any, List

from .. import models

TEST_POINT_TYPES = ("功能", "UI", "兼容性", "安全性", "性能", "易用性", "接口", "数据")
CASE_TYPES = ("功能", "UI", "兼容性", "安全性", "性能", "易用性", "接口", "数据", "异常")
PRIORITIES = ("P0", "P1", "P2", "P3")
PRODUCT_TYPES = ("Web应用", "移动App", "小程序", "桌面应用", "接口服务", "硬件/嵌入式", "其他")

# 语义映射:常见"非枚举说法" → 合法枚举
SEMANTIC_MAP = {
    "并发": "性能", "并发性能": "性能", "边界": "功能", "边界值": "功能",
    "异常": "功能", "负向": "功能", "反例": "功能", "错误": "功能",
    "安全": "安全性", "安全漏洞": "安全性", "越权": "安全性", "权限": "安全性",
    "兼容": "兼容性", "多端": "兼容性", "适配": "兼容性",
    "易用": "易用性", "可用性": "易用性", "体验": "易用性",
    "数据一致性": "数据", "一致性": "数据", "精度": "数据", "数据正确": "数据",
    "性能测试": "性能", "压测": "性能", "稳定性": "性能", "响应": "性能",
}


def coerce_enum(value: Any, allowed: tuple, fallback: str) -> str:
    """将任意值规整到 allowed 枚举内;无法规整时返回 fallback。"""
    if value is None:
        return fallback
    s = str(value).strip()
    if s in allowed:
        return s
    # 双向包含匹配:如 "并发性能" → "性能","安全测试" → "安全性"
    for a in allowed:
        if a in s or s in a:
            return a
    # 语义映射(包含匹配,长 key 优先):如 "并发"→"性能","安全测试"→"安全性"
    for k in sorted(SEMANTIC_MAP, key=len, reverse=True):
        if k in s or s in k:
            return SEMANTIC_MAP[k]
    # 中文分隔符拆分后匹配
    for part in s.replace("/", " ").replace(",", " ").replace("、", " ").split():
        for a in allowed:
            if a in part or part in a:
                return a
    return fallback


def coerce_priority(value: Any) -> str:
    """规整优先级:P0~P3(兼容 p1 / P-2 / 高 等写法)。"""
    if value is None:
        return "P2"
    s = str(value).strip().upper().replace("-", "").replace(" ", "")
    if s in PRIORITIES:
        return s
    if s.startswith("P") and len(s) == 2 and s[1].isdigit():
        n = int(s[1])
        if 0 <= n <= 3:
            return f"P{n}"
    s = str(value).strip()
    if s in ("高", "紧急", "致命", "阻断"):
        return "P0"
    if s in ("中", "重要"):
        return "P1"
    if s in ("低", "一般"):
        return "P2"
    if s in ("很低", "轻微", "边缘"):
        return "P3"
    return "P2"


def _as_list(value: Any) -> list:
    """将字符串/None/非法类型规整为列表(用于 steps/expected)。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [line.strip() for line in value.replace("\r", "").split("\n") if line.strip()]
    return [str(value)]


# ------------------------------------------------------------------ #
# 各阶段规整
# ------------------------------------------------------------------ #
def normalize_test_point(tp: dict) -> dict:
    d = dict(tp)
    d["id"] = str(d.get("id") or "TP-00")
    d["module"] = str(d.get("module") or "未分类")
    d["name"] = str(d.get("name") or "未命名测试点")
    d["type"] = coerce_enum(d.get("type"), TEST_POINT_TYPES, "功能")
    d["description"] = str(d.get("description") or "")
    d["priority"] = coerce_priority(d.get("priority"))
    d.setdefault("inferred", False)
    return d


def normalize_case(c: dict) -> dict:
    d = dict(c)
    d["case_id"] = str(d.get("case_id") or "TC-000")
    d["module"] = str(d.get("module") or "未分类")
    d["test_point"] = str(d.get("test_point") or "未分类")
    d["title"] = str(d.get("title") or d["case_id"])
    d["priority"] = coerce_priority(d.get("priority"))
    d["case_type"] = coerce_enum(d.get("case_type"), CASE_TYPES, "功能")
    d["precondition"] = str(d.get("precondition") or "")
    d["test_data"] = str(d.get("test_data") or "")
    steps = _as_list(d.get("steps"))
    d["steps"] = steps or ["待补充操作步骤"]
    expected = _as_list(d.get("expected"))
    d["expected"] = expected or ["待补充预期结果"]
    return d


def normalize_analysis(data: dict) -> dict:
    d = dict(data)
    d["product_name"] = str(d.get("product_name") or "未知产品")
    d["product_type"] = coerce_enum(d.get("product_type"), PRODUCT_TYPES, "其他")
    d["target_users"] = str(d.get("target_users") or "")
    d["core_value"] = str(d.get("core_value") or "")
    d.setdefault("modules", [])
    d.setdefault("business_flows", [])
    d.setdefault("risk_points", [])
    d["test_points"] = [normalize_test_point(tp) for tp in (d.get("test_points") or [])]
    return d


def normalize_cases_payload(data: dict) -> List[models.TestCase]:
    """规整生成/评审返回的 cases 数据,输出合法 TestCase 列表。"""
    raw_cases = data.get("cases") if isinstance(data, dict) else None
    if not raw_cases:
        return []
    cases = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            continue
        try:
            cases.append(models.TestCase.model_validate(normalize_case(raw)))
        except Exception:  # noqa: BLE001 极端兜底
            cases.append(models.TestCase(
                case_id="TC-000", module="未分类", test_point="未分类",
                title="未命名用例", priority="P2", case_type="功能",
                precondition="", test_data="", steps=["待补充"], expected=["待补充"],
            ))
    return cases


def normalize_review(data: dict) -> dict:
    d = dict(data)
    d["summary"] = str(d.get("summary") or "评审完成")
    d["gaps"] = [str(g) for g in (d.get("gaps") or []) if g]
    d["issues"] = [str(i) for i in (d.get("issues") or []) if i]
    d["cases"] = normalize_cases_payload(d)
    return d
