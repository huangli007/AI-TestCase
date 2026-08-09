"""Mock 大模型客户端:无需 API Key 即可端到端演示/测试全流程。"""

from __future__ import annotations

import json
from typing import List

from .. import models


class MockLLMClient:
    """返回固定的高质量示例数据,用于离线演示与 CI 测试。"""

    def __init__(self, *_args, **_kwargs):
        pass

    @property
    def vision_enabled(self) -> bool:
        return True

    # ------------------------------------------------------------------ #
    def _sample_analysis(self) -> dict:
        return models.ProductAnalysis(
            product_name="示例电商 App(演示)",
            product_type="移动App",
            target_users="C 端消费者",
            core_value="在线浏览商品、下单支付、订单管理的一站式购物体验",
            modules=[
                models.FunctionPoint(module="用户", feature="注册/登录",
                                     rules=["手机号+验证码登录", "支持微信第三方登录", "连续输错 5 次验证码需图形验证"]),
                models.FunctionPoint(module="商品", feature="商品列表/详情",
                                     rules=["列表支持分页加载", "库存为 0 的商品置灰不可购买"]),
                models.FunctionPoint(module="交易", feature="下单/支付",
                                     rules=["下单需登录", "支付超时 15 分钟自动取消", "优惠券与满减不可叠加"]),
                models.FunctionPoint(module="订单", feature="订单管理",
                                     rules=["订单状态:待支付/已支付/已发货/已完成/已取消", "仅限本人查看订单"]),
            ],
            business_flows=[
                models.BusinessFlow(name="下单支付流程", description="浏览商品 -> 加入购物车 -> 结算 -> 支付 -> 生成订单"),
                models.BusinessFlow(name="售后流程", description="申请退款 -> 商家审核 -> 退款到账"),
            ],
            risk_points=["支付并发下单导致库存超卖", "验证码接口未限流可被爆破", "订单状态机流转异常", "敏感信息(手机号/地址)泄露"],
            test_points=[
                models.TestPoint(id="TP-001", module="用户", name="手机号登录验证码", type="功能",
                                 description="验证码获取、输入校验、错误重试、图形验证触发", priority="P0"),
                models.TestPoint(id="TP-002", module="用户", name="登录安全性", type="安全性",
                                 description="验证码爆破防护、会话过期、账号锁定", priority="P1"),
                models.TestPoint(id="TP-003", module="商品", name="商品列表与分页", type="功能",
                                 description="分页加载、下拉刷新、空态、网络异常", priority="P1"),
                models.TestPoint(id="TP-004", module="商品", name="商品库存边界", type="功能",
                                 description="库存临界值、超卖防护、售罄置灰", priority="P1"),
                models.TestPoint(id="TP-005", module="交易", name="下单支付流程", type="功能",
                                 description="正常下单支付、支付超时取消、支付回调幂等", priority="P0"),
                models.TestPoint(id="TP-006", module="交易", name="优惠与价格计算", type="数据",
                                 description="优惠券/满减叠加规则、价格精度、税费计算", priority="P1"),
                models.TestPoint(id="TP-007", module="交易", name="并发与一致性", type="性能",
                                 description="高并发下单、库存扣减一致性、超卖防护", priority="P1"),
                models.TestPoint(id="TP-008", module="订单", name="订单状态机", type="功能",
                                 description="各状态流转合法性、非法状态迁移拦截", priority="P0"),
                models.TestPoint(id="TP-009", module="订单", name="订单权限与隐私", type="安全性",
                                 description="越权访问他人订单、敏感信息脱敏", priority="P1"),
                models.TestPoint(id="TP-010", module="全产品", name="多端兼容性", type="兼容性",
                                 description="iOS/Android 主流版本、屏幕适配、弱网", priority="P2"),
            ],
        ).model_dump()

    def _sample_cases(self) -> dict:
        cases = [
            models.TestCase(case_id="TC-001", module="用户", test_point="手机号登录验证码",
                            title="输入正确手机号获取验证码成功", priority="P0", case_type="功能",
                            precondition="已安装 App 并处于登录页", test_data="手机号:13800138000",
                            steps=["打开 App 进入登录页", "输入正确手机号 13800138000", "点击『获取验证码』"],
                            expected=["60 秒倒计时开始", "收到短信验证码", "『获取验证码』按钮变为『重新获取(58s)』"]),
            models.TestCase(case_id="TC-002", module="用户", test_point="手机号登录验证码",
                            title="输入错误验证码登录失败并提示", priority="P1", case_type="异常",
                            precondition="已收到验证码", test_data="错误验证码:123456",
                            steps=["输入正确手机号并获取验证码", "输入错误验证码 123456", "点击『登录』"],
                            expected=["提示『验证码错误』", "停留在登录页,不跳转", "不消耗有效验证码次数"]),
            models.TestCase(case_id="TC-003", module="用户", test_point="登录安全性",
                            title="连续输错 5 次验证码触发图形验证", priority="P1", case_type="安全性",
                            precondition="登录页可用", test_data="连续 5 次错误验证码",
                            steps=["连续 5 次输入错误验证码并提交", "第 6 次尝试获取验证码"],
                            expected=["第 6 次起出现图形验证码校验", "验证码接口触发限流,频繁请求被拒绝"]),
            models.TestCase(case_id="TC-004", module="商品", test_point="商品列表与分页",
                            title="商品列表滚动到底自动加载下一页", priority="P1", case_type="功能",
                            precondition="网络正常,商品列表非空", test_data="商品总数 > 一页条数",
                            steps=["进入商品列表页", "快速滚动到底部", "观察加载行为"],
                            expected=["滚动到底自动加载下一页,有 loading 提示", "数据无重复无缺漏", "最后一页出现『没有更多了』"]),
            models.TestCase(case_id="TC-005", module="商品", test_point="商品列表与分页",
                            title="弱网/断网下列表的异常处理", priority="P2", case_type="异常",
                            precondition="可模拟弱网或断网", test_data="断网状态",
                            steps=["断网后进入商品列表页", "下拉刷新", "恢复网络后再次刷新"],
                            expected=["显示错误提示与『重试』按钮", "无白屏/崩溃", "恢复网络后可正常加载"]),
            models.TestCase(case_id="TC-006", module="商品", test_point="商品库存边界",
                            title="库存仅剩 1 件时多端同时下单不超卖", priority="P1", case_type="功能",
                            precondition="商品库存=1,双端登录", test_data="库存 1 件",
                            steps=["A/B 两个账号同时下单该商品", "两端同时提交支付"],
                            expected=["仅一端下单成功", "另一端提示『库存不足』", "最终库存不为负数"]),
            models.TestCase(case_id="TC-007", module="交易", test_point="下单支付流程",
                            title="正常下单并完成支付", priority="P0", case_type="功能",
                            precondition="已登录、有可用商品与支付方式", test_data="商品 1 件 + 微信支付",
                            steps=["选择商品加入购物车", "进入结算页确认金额", "选择微信支付并完成支付"],
                            expected=["生成订单,状态为『待支付』", "支付成功后状态变为『已支付』", "库存正确扣减,支付回调幂等不重复扣款"]),
            models.TestCase(case_id="TC-008", module="交易", test_point="下单支付流程",
                            title="支付超时订单自动取消", priority="P1", case_type="功能",
                            precondition="已下单未支付", test_data="订单超时 15 分钟",
                            steps=["提交订单不支付", "等待超过 15 分钟", "查看订单状态"],
                            expected=["订单状态自动变为『已取消』", "库存自动释放", "用户收到超时取消提醒"]),
            models.TestCase(case_id="TC-009", module="交易", test_point="优惠与价格计算",
                            title="优惠券与满减不同时生效", priority="P1", case_type="数据",
                            precondition="有可用优惠券与满减活动", test_data="订单金额 100 元,券减 10,满 99 减 20",
                            steps=["结算页同时满足优惠券与满减条件", "观察优惠计算", "对比优惠明细"],
                            expected=["仅生效金额更优的优惠,不叠加", "优惠明细展示正确", "实付金额=商品金额-优惠,精度精确到分"]),
            models.TestCase(case_id="TC-010", module="交易", test_point="并发与一致性",
                            title="高并发下单库存不超卖", priority="P1", case_type="性能",
                            precondition="库存 100,压测工具", test_data="1000 并发抢购",
                            steps=["对秒杀接口发起 1000 并发请求", "结束后核对库存与订单数"],
                            expected=["成功订单数 <= 库存数", "库存不为负数,无超卖", "响应成功率与平均耗时符合 SLA"]),
            models.TestCase(case_id="TC-011", module="订单", test_point="订单状态机",
                            title="非法状态迁移被拦截(已发货不可再取消)", priority="P0", case_type="异常",
                            precondition="存在已发货订单", test_data="已发货订单",
                            steps=["对已发货订单点击『取消订单』", "尝试接口直接提交取消请求"],
                            expected=["UI 层无取消入口", "接口层拒绝并返回错误码", "订单状态不变"]),
            models.TestCase(case_id="TC-012", module="订单", test_point="订单权限与隐私",
                            title="越权访问他人订单被拒绝", priority="P1", case_type="安全性",
                            precondition="两个不同账号各有一笔订单", test_data="账号 A 访问账号 B 订单号",
                            steps=["账号 A 通过订单号直接访问 B 的订单详情", "检查响应"],
                            expected=["返回 403/404,不返回订单数据", "手机号、地址等敏感信息脱敏展示", "无水平越权漏洞"]),
            models.TestCase(case_id="TC-013", module="全产品", test_point="多端兼容性",
                            title="主流机型与系统版本兼容", priority="P2", case_type="兼容性",
                            precondition="覆盖 iOS 15+ / Android 10+ 主流机型", test_data="主流机型清单",
                            steps=["在主流机型上执行核心流程", "检查布局与功能", "检查不同分辨率适配"],
                            expected=["核心流程全部可用", "无布局错乱、文字截断、按钮遮挡", "深色模式/字体缩放下不破版"]),
        ]
        return {"cases": [c.model_dump() for c in cases]}

    def _sample_review(self) -> dict:
        cases = self._sample_cases()["cases"]
        return {
            "summary": "用例覆盖主要功能与关键风险点,补充了弱网、越权、并发等场景,整体质量良好。",
            "gaps": ["补充弱网/断网下支付结果不确定性的处理用例", "补充重复提交订单的幂等校验用例"],
            "issues": ["TC-010 补充 SLA 断言", "TC-009 明确精度校验"],
            "cases": cases,
        }

    # ------------------------------------------------------------------ #
    def complete_json(self, messages: List[dict], *, stage: str = "", **kwargs) -> dict:
        if stage == "analyze":
            return self._sample_analysis()
        if stage == "generate":
            return self._sample_cases()
        if stage == "review":
            return self._sample_review()
        # 无显式 stage 时的兼容推断
        joined = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        if "评审" in joined:
            return self._sample_review()
        if '"cases"' in joined:
            return self._sample_cases()
        return self._sample_analysis()

    def vision_analyze(self, text: str, image_data_uris: List[str], **kwargs) -> dict:
        return {
            "product_name": "示例产品(视觉素材)",
            "page": "素材中识别的页面",
            "elements": ["从素材中提取的功能元素(演示数据)"],
            "texts": ["素材中的关键文案"],
            "states": ["可见状态"],
            "notes": "Mock 模式:未调用真实视觉模型,请配置 vision_model 获取真实分析。",
        }

    @staticmethod
    def is_available() -> bool:
        return True
