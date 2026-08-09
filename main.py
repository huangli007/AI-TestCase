"""命令行入口:自动生成测试用例 Agent(跨平台)。

用法示例:
  # 真实模式(在 config.yaml 或环境变量配置 API Key)
  python main.py --files prd.pdf prototype.png demo.mp4 --out output/ --config config.yaml

  # 离线演示模式(无需 API Key)
  python main.py --files samples/sample_prd.md --out output/ --mock

  # 跳过质量评审
  python main.py --files samples/sample_prd.md --mock --no-review

  # 启动桌面 GUI
  python main.py --gui
"""

from __future__ import annotations

import argparse
import logging
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="testcase-agent", description="自动生成测试用例的 Agent(跨平台)")
    p.add_argument("--files", "-f", nargs="+",
                   help="输入文件:文本(txt/md/docx/pdf/csv)、图片(png/jpg)、视频(mp4/mov)等,可传多个")
    p.add_argument("--out", "-o", default="output", help="输出目录(默认 output/)")
    p.add_argument("--config", "-c", default=None, help="配置文件路径(config.yaml)")
    p.add_argument("--mock", action="store_true", help="离线演示模式,无需 API Key")
    p.add_argument("--no-review", action="store_true", help="跳过质量评审阶段")
    p.add_argument("--format", nargs="+", default=None,
                   choices=["xlsx", "md", "json"], help="导出格式(默认 xlsx/md/json)")
    p.add_argument("--verbose", "-v", action="store_true", help="输出详细日志")
    p.add_argument("--gui", action="store_true", help="启动桌面图形界面(Windows/macOS)")
    return p


def _run_cli(args) -> int:
    from testcase_agent.config import AppConfig
    from testcase_agent.pipeline.agent import TestCaseAgent

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    if not args.files:
        print("错误: --files 至少需要一个输入文件(或使用 --gui 启动图形界面)")
        return 2

    cfg = AppConfig.load(args.config)
    if args.mock:
        cfg.pipeline.mock_mode = True

    agent = TestCaseAgent(cfg)
    agent.on_progress(lambda msg: print(f"[进度] {msg}"))

    try:
        result = agent.run(
            args.files,
            output_dir=args.out,
            review=None if not args.no_review else False,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    print(f"\n✅ 完成:产品「{result.product_name}」共 {len(result.cases)} 条用例")
    return 0


def main() -> int:
    args = build_parser().parse_args()

    if args.gui:
        from testcase_agent.gui.app import main as gui_main
        return gui_main()

    return _run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
