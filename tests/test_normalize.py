"""LLM 输出规整层测试:脏数据(非法枚举/缺失字段)必须被规整而非崩溃。"""

from testcase_agent import models
from testcase_agent.llm.normalize import (
    coerce_enum, coerce_priority, normalize_analysis, normalize_cases_payload, normalize_review,
)


class TestCoerceEnum:
    def test_exact(self):
        assert coerce_enum("功能", ("功能", "UI"), "功能") == "功能"

    def test_contains_both_ways(self):
        assert coerce_enum("并发性能", ("功能", "性能"), "功能") == "性能"
        assert coerce_enum("安全测试", ("功能", "安全性"), "功能") == "安全性"

    def test_semantic_map(self):
        assert coerce_enum("并发", ("功能", "性能"), "功能") == "性能"
        assert coerce_enum("边界", ("功能", "数据"), "功能") == "功能"
        assert coerce_enum("越权", ("功能", "安全性"), "功能") == "安全性"
        assert coerce_enum("数据一致性", ("功能", "数据"), "功能") == "数据"

    def test_fallback(self):
        assert coerce_enum("量子力学", ("功能", "UI"), "功能") == "功能"
        assert coerce_enum(None, ("功能",), "功能") == "功能"


class TestCoercePriority:
    def test_standard(self):
        assert coerce_priority("P0") == "P0"
        assert coerce_priority("P3") == "P3"

    def test_lowercase_and_dirty(self):
        assert coerce_priority("p1") == "P1"
        assert coerce_priority("P-2") == "P2"
        assert coerce_priority("P 3") == "P3"

    def test_semantic(self):
        assert coerce_priority("高") == "P0"
        assert coerce_priority("紧急") == "P0"
        assert coerce_priority("中") == "P1"
        assert coerce_priority("低") == "P2"

    def test_fallback(self):
        assert coerce_priority(None) == "P2"
        assert coerce_priority("??") == "P2"


class TestNormalizeAnalysis:
    def test_concurrent_type_coerced(self):
        """复现用户报错:test_points[].type = '并发'。"""
        data = {
            "product_name": "X", "product_type": "Web应用",
            "test_points": [
                {"id": "TP-1", "module": "M", "name": "N", "type": "并发", "priority": "P1"},
                {"id": "TP-2", "module": "M", "name": "N2", "type": "功能", "priority": "高"},
            ],
        }
        norm = normalize_analysis(data)
        assert norm["test_points"][0]["type"] == "性能"
        assert norm["test_points"][1]["priority"] == "P0"
        analysis = models.ProductAnalysis.model_validate(norm)
        assert analysis.test_points[0].type == "性能"

    def test_missing_fields_filled(self):
        data = {"test_points": [{"name": "只有名字"}]}
        norm = normalize_analysis(data)
        assert norm["product_name"] == "未知产品"
        assert norm["product_type"] == "其他"
        tp = norm["test_points"][0]
        assert tp["module"] == "未分类" and tp["priority"] == "P2" and tp["type"] == "功能"


class TestNormalizeCases:
    def test_dirty_case_fields(self):
        data = {
            "cases": [
                {
                    "case_id": "TC-001", "module": "M", "test_point": "T", "title": "标题",
                    "priority": "p1", "case_type": "并发",
                    "steps": "1. 打开\n2. 点击",   # 字符串 steps
                    "expected": "成功",
                },
            ]
        }
        cases = normalize_cases_payload(data)
        assert len(cases) == 1
        c = cases[0]
        assert c.priority == "P1"
        assert c.case_type == "性能"   # 并发 → 性能
        assert c.steps == ["1. 打开", "2. 点击"]
        assert c.expected == ["成功"]

    def test_empty_payload(self):
        assert normalize_cases_payload({}) == []
        assert normalize_cases_payload({"cases": None}) == []

    def test_non_dict_items_skipped(self):
        data = {"cases": ["not-a-dict", None, {"case_id": "x", "title": "t"}]}
        cases = normalize_cases_payload(data)
        assert len(cases) == 1  # 非 dict 被跳过


class TestNormalizeReview:
    def test_review_dirty(self):
        data = {"cases": [{"case_id": "R1", "title": "t", "case_type": "接口"}]}
        rev = normalize_review(data)
        assert rev["summary"] == "评审完成"
        assert rev["cases"][0].case_type == "接口"
        assert rev["gaps"] == [] and rev["issues"] == []
