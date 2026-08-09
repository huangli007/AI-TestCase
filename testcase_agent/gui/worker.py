"""后台执行线程:在 QThread 中运行完整管线,避免阻塞 GUI。

分阶段实时上报中间产物(stage_done 信号),让 GUI 可以随分析/生成/评审完成
逐个填充 tab,提升交互体验。
"""

from __future__ import annotations

import os
import re
from typing import Optional

from PySide6.QtCore import QThread, Signal

from ..config import AppConfig
from ..pipeline.agent import TestCaseAgent

_STAGE_RE = re.compile(r"阶段\s*(\d+)\s*/\s*(\d+)")

# 视觉模型常见关键词(用于拉取后自动归类)
VISION_KEYWORDS = (
    "vl", "vision", "4o", "omni", "audio", "video", "multimodal",
    "glm-4v", "qwen-vl", "doubao-vision", "hunyuan-vision", "minicpm",
    "step-1v", "sensechat-vision", "llava",
)


class ModelFetchWorker(QThread):
    """后台拉取 OpenAI 兼容 /models 接口的模型列表。"""

    fetched = Signal(list)   # 模型 id 列表
    failed = Signal(str)

    def __init__(self, base_url: str, api_key: str, timeout: int = 30, parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    def run(self):  # noqa: D102
        try:
            from openai import OpenAI
            client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)
            resp = client.models.list()
            ids = sorted(m.id for m in resp.data)
            if not ids:
                raise RuntimeError("接口返回了空模型列表")
            self.fetched.emit(ids)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


def filter_vision_models(model_ids: list[str]) -> list[str]:
    """根据关键词从模型列表中筛出视觉模型候选。"""
    return [m for m in model_ids if any(k in m.lower() for k in VISION_KEYWORDS)]


class AgentWorker(QThread):
    """后台执行 TestCaseAgent 三阶段管线,实时上报中间产物。"""

    progress = Signal(str)
    stage = Signal(int, int, str)              # (当前阶段, 总阶段, 阶段名)
    stage_done = Signal(str, object)            # (阶段名, 中间产物)
    finished_ok = Signal(object)                # GenerationResult
    failed = Signal(str)

    def __init__(self, files: list[str], output_dir: str,
                 config: AppConfig, review: Optional[bool] = None, parent=None):
        super().__init__(parent)
        self.files = files
        self.output_dir = output_dir
        self.config = config
        self.review = review

    def run(self):  # noqa: D102
        try:
            agent = TestCaseAgent(self.config)

            def _on_progress(msg: str):
                m = _STAGE_RE.search(msg)
                if m:
                    cur, total = int(m.group(1)), int(m.group(2))
                    name = msg.split(":", 1)[1].strip() if ":" in msg else msg
                    self.stage.emit(cur, total, name)
                self.progress.emit(msg)

            agent.on_progress(_on_progress)

            # 解析素材
            work_dir = os.path.join(self.output_dir, ".work")
            os.makedirs(work_dir, exist_ok=True)
            parse = agent.parse_files(self.files, work_dir=work_dir)
            for err in parse.errors:
                self.progress.emit(f"[警告] {err}")
            if not parse.materials:
                raise RuntimeError(
                    "没有可用的素材内容,请检查输入文件。详情: " + "; ".join(parse.errors))
            self.progress.emit(f"已解析 {len(parse.parsed_files)} 个文件")

            # 阶段一:产品分析 → 实时填充产品分析 + 测试点 tab
            self.progress.emit("阶段 1/3: 分析产品,梳理测试点…")
            analysis = agent.analyzer.analyze(parse.materials)
            self.stage_done.emit("analysis", analysis)

            # 阶段二:用例生成 → 实时填充测试用例 tab
            self.progress.emit("阶段 2/3: 生成测试用例…")
            cases = agent.generator.generate(analysis)
            self.stage_done.emit("cases", (analysis, cases))

            # 阶段三:质量评审(可关闭)
            review_result = None
            if self.review is not False:
                self.progress.emit("阶段 3/3: 质量评审,补漏修正…")
                review_result = agent.reviewer.review(analysis, cases)
                cases = review_result.cases
                self.stage_done.emit("review", review_result)
            else:
                self.progress.emit("阶段 3/3: 已跳过质量评审")

            from .. import models
            result = models.GenerationResult(
                product_name=analysis.product_name,
                analysis=analysis,
                cases=cases,
                review=review_result,
            )
            agent._export(result, self.output_dir)  # noqa: SLF001
            self.finished_ok.emit(result)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))