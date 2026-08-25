"""离屏渲染 GUI 并截图(开发验证用,无需显示器)。

用法:
  python tools/render_gui_preview.py [输出路径]
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from testcase_agent import models  # noqa: E402
from testcase_agent.gui import platform  # noqa: E402
from testcase_agent.gui.app import MainWindow, NAV_STYLE  # noqa: E402
from testcase_agent.gui.ui import QSS  # noqa: E402


def _load_offline_cjk_font(app: QApplication) -> None:
    """离屏渲染下 Qt 不加载系统字体,需手动 addApplicationFont 注入。"""
    from PySide6.QtGui import QFont, QFontDatabase
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            fid = QFontDatabase.addApplicationFont(path)
            if fid >= 0:
                families = QFontDatabase.applicationFontFamilies(fid)
                if families:
                    f = QFont(families[0])
                    f.setPointSize(10)
                    app.setFont(f)
                    return


def _sample_result() -> models.GenerationResult:
    analysis = models.ProductAnalysis(
        product_name="示例电商 App(演示)",
        product_type="移动App",
        target_users="C 端消费者",
        core_value="在线浏览商品、下单支付、订单管理的一站式购物体验",
        modules=[models.FunctionPoint(module="用户", feature="注册/登录",
                                      rules=["手机号+验证码登录", "支持微信第三方登录"]),
                 models.FunctionPoint(module="交易", feature="下单/支付",
                                      rules=["下单需登录", "支付超时 15 分钟自动取消"])],
        business_flows=[models.BusinessFlow(name="下单支付流程", description="浏览商品 → 结算 → 支付 → 生成订单")],
        risk_points=["支付并发导致库存超卖", "验证码接口未限流可被爆破"],
        test_points=[
            models.TestPoint(id="TP-001", module="用户", name="手机号登录验证码", type="功能",
                             description="验证码获取、输入校验、错误重试", priority="P0"),
            models.TestPoint(id="TP-002", module="用户", name="登录安全性", type="安全性",
                             description="验证码爆破防护、会话过期", priority="P1"),
            models.TestPoint(id="TP-003", module="交易", name="下单支付流程", type="功能",
                             description="正常下单支付、支付超时取消", priority="P0"),
        ],
    )
    cases = [
        models.TestCase(case_id="TC-001", module="用户", test_point="手机号登录验证码",
                        title="输入正确手机号获取验证码成功", priority="P0", case_type="功能",
                        precondition="已安装 App 并处于登录页", test_data="手机号:13800138000",
                        steps=["打开 App 进入登录页", "输入正确手机号", "点击『获取验证码』"],
                        expected=["60 秒倒计时开始", "收到短信验证码"]),
        models.TestCase(case_id="TC-002", module="用户", test_point="手机号登录验证码",
                        title="输入错误验证码登录失败并提示", priority="P1", case_type="异常",
                        precondition="已收到验证码", test_data="错误验证码:123456",
                        steps=["输入正确手机号并获取验证码", "输入错误验证码", "点击『登录』"],
                        expected=["提示『验证码错误』", "停留在登录页"]),
        models.TestCase(case_id="TC-003", module="交易", test_point="下单支付流程",
                        title="正常下单并完成支付", priority="P0", case_type="功能",
                        precondition="已登录、有可用商品与支付方式", test_data="商品 1 件 + 微信支付",
                        steps=["选择商品加入购物车", "进入结算页确认金额", "完成支付"],
                        expected=["生成订单,状态为『待支付』", "支付成功后状态变为『已支付』"]),
    ]
    review = models.ReviewResult(
        summary="用例覆盖主要功能与关键风险点,整体质量良好。",
        gaps=["补充弱网下支付结果不确定性处理用例"],
        issues=["TC-003 补充回调幂等断言"],
        cases=cases,
    )
    return models.GenerationResult(product_name="示例电商 App(演示)", analysis=analysis,
                                    cases=cases, review=review)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/gui_preview.png"
    app = QApplication(sys.argv)
    _load_offline_cjk_font(app)
    platform.apply_default_font(app)

    win = MainWindow()
    win.setStyleSheet(QSS + NAV_STYLE)
    win.resize(1320, 920)
    win.show()

    # 填充示例素材(用临时目录,避免污染真实 samples/)
    tmpdir = Path(tempfile.gettempdir()) / "testcase_agent_preview"
    tmpdir.mkdir(exist_ok=True)
    sample_files = []
    for name in ("需求文档_v2.1.md", "登录页_原型.png", "下单流程_演示.mp4"):
        p = tmpdir / name
        p.write_bytes(b"x" * 128)
        sample_files.append(str(p))
    win._add_files(sample_files)  # noqa: SLF001

    # 填充示例结果并切到结果页展示
    win._populate_result(_sample_result())  # noqa: SLF001
    win._stage_text.setText("全部完成 ✓")
    win._progress.setValue(100)
    win._steps.set_current(3)
    win._apply_status("完成", ok=True)
    win._on_nav_clicked(3)  # noqa: SLF001  展示结果页

    win.grab().save(out)
    print(f"截图已保存: {os.path.abspath(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
