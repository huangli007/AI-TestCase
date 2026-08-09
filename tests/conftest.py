"""pytest 共享 fixture:离屏 QApplication 与示例数据。"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from testcase_agent import models  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """单例 QApplication(offscreen 平台)。"""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(scope="session")
def sample_result() -> models.GenerationResult:
    """构造一个最小但字段完整的生成结果。"""
    analysis = models.ProductAnalysis(
        product_name="测试产品",
        product_type="Web应用",
        target_users="测试用户",
        core_value="核心价值描述",
        modules=[models.FunctionPoint(module="登录", feature="验证码登录", rules=["手机号+验证码"])],
        business_flows=[models.BusinessFlow(name="登录流程", description="输入手机号→获取验证码→登录")],
        risk_points=["验证码爆破"],
        test_points=[
            models.TestPoint(id="TP-001", module="登录", name="验证码登录", type="功能",
                             description="验证码获取与校验", priority="P0"),
            models.TestPoint(id="TP-002", module="登录", name="登录安全", type="安全性",
                             description="爆破防护", priority="P1"),
        ],
    )
    cases = [
        models.TestCase(case_id="TC-001", module="登录", test_point="验证码登录",
                        title="正确验证码登录成功", priority="P0", case_type="功能",
                        precondition="已获取验证码", test_data="验证码:123456",
                        steps=["输入手机号", "输入验证码", "点击登录"], expected=["登录成功"]),
        models.TestCase(case_id="TC-002", module="登录", test_point="验证码登录",
                        title="错误验证码登录失败", priority="P1", case_type="异常",
                        precondition="已获取验证码", test_data="验证码:000000",
                        steps=["输入错误验证码", "点击登录"], expected=["提示验证码错误"]),
    ]
    review = models.ReviewResult(summary="评审通过", gaps=["补充并发登录"], issues=["TC-002 预期明确"],
                                 cases=cases)
    return models.GenerationResult(product_name="测试产品", analysis=analysis,
                                    cases=cases, review=review)
