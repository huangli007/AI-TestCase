"""领域数据模型:产品分析、测试点、测试用例、评审结果。"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

PRIORITY = Literal["P0", "P1", "P2", "P3"]
PRODUCT_TYPE = Literal["Web应用", "移动App", "小程序", "桌面应用", "接口服务", "硬件/嵌入式", "其他"]
TEST_POINT_TYPE = Literal["功能", "UI", "兼容性", "安全性", "性能", "易用性", "接口", "数据"]
CASE_TYPE = Literal["功能", "UI", "兼容性", "安全性", "性能", "易用性", "接口", "数据", "异常"]


class FunctionPoint(BaseModel):
    """功能点:模块 -> 功能 -> 业务规则。"""

    module: str = Field(description="所属模块")
    feature: str = Field(description="功能点名称")
    rules: List[str] = Field(default_factory=list, description="业务规则列表")


class BusinessFlow(BaseModel):
    """关键业务流程。"""

    name: str = Field(description="流程名称")
    description: str = Field(description="流程描述")


class TestPoint(BaseModel):
    """测试点:一条可执行的测试关注点。"""

    id: str = Field(description="测试点编号,如 TP-001")
    module: str = Field(description="所属模块")
    name: str = Field(description="测试点名称")
    type: TEST_POINT_TYPE = Field(description="测试点类型")
    description: str = Field(description="测试点描述")
    priority: PRIORITY = Field(description="优先级")
    inferred: bool = Field(default=False, description="是否为资料缺失时基于常识推断")


class ProductAnalysis(BaseModel):
    """产品分析结果。"""

    product_name: str = Field(description="产品名称")
    product_type: PRODUCT_TYPE = Field(description="产品类型")
    target_users: str = Field(description="目标用户")
    core_value: str = Field(description="核心价值")
    modules: List[FunctionPoint] = Field(default_factory=list, description="功能清单")
    business_flows: List[BusinessFlow] = Field(default_factory=list, description="关键业务流程")
    risk_points: List[str] = Field(default_factory=list, description="风险点")
    test_points: List[TestPoint] = Field(default_factory=list, description="测试点清单")


class TestCase(BaseModel):
    """一条测试用例。"""

    case_id: str = Field(description="用例编号,如 TC-001")
    module: str = Field(description="所属模块")
    test_point: str = Field(description="对应测试点")
    title: str = Field(description="用例标题")
    priority: PRIORITY = Field(description="优先级")
    case_type: CASE_TYPE = Field(description="用例类型")
    precondition: str = Field(default="", description="前置条件")
    test_data: str = Field(default="", description="测试数据")
    steps: List[str] = Field(description="操作步骤")
    expected: List[str] = Field(description="预期结果")


class ReviewResult(BaseModel):
    """评审结果:补充遗漏、修正问题后的最终用例集。"""

    summary: str = Field(description="评审总结")
    gaps: List[str] = Field(default_factory=list, description="补充的遗漏测试点")
    issues: List[str] = Field(default_factory=list, description="修正的问题")
    cases: List[TestCase] = Field(description="修正后的完整用例集")


class GenerationResult(BaseModel):
    """一次完整生成的最终产物。"""

    product_name: str = Field(default="", description="产品名称")
    analysis: ProductAnalysis = Field(description="产品分析")
    cases: List[TestCase] = Field(default_factory=list, description="测试用例集")
    review: Optional[ReviewResult] = Field(default=None, description="评审结果")
