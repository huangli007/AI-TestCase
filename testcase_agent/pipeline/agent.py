"""主 Agent:多模态解析 -> 产品分析 -> 用例生成 -> 质量评审 -> 导出。"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .. import models
from ..config import AppConfig
from ..llm import LLMClient, LLMError, MockLLMClient
from ..parsers import analyze_images, analyze_video, extract_text
from ..parsers.image_parser import is_image
from ..parsers.prototype_link import fetch_prototype_screenshots, is_prototype_url
from ..parsers.video_parser import is_video
from .analyzer import Analyzer
from .generator import Generator
from .reviewer import Reviewer

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """解析阶段产物:分类后的素材文本列表。"""

    materials: List[str] = field(default_factory=list)
    parsed_files: List[str] = field(default_factory=list)   # 成功解析的文件
    skipped: List[str] = field(default_factory=list)        # 跳过的文件(不支持类型)
    errors: List[str] = field(default_factory=list)         # 解析失败的文件


ProgressCb = Callable[[str], None]


class TestCaseAgent:
    """自动生成测试用例的 Agent 主入口。"""

    def __init__(self, config: Optional[AppConfig] = None, llm=None):
        self.cfg = config or AppConfig.load()
        self.llm = llm or (
            MockLLMClient() if self.cfg.pipeline.mock_mode else LLMClient(self.cfg.llm)
        )
        self.analyzer = Analyzer(self.llm)
        self.generator = Generator(self.llm, max_cases=self.cfg.pipeline.max_cases)
        self.reviewer = Reviewer(self.llm)
        self._progress: ProgressCb = lambda msg: logger.info("[进度] %s", msg)

    # ------------------------------------------------------------------ #
    def on_progress(self, cb: ProgressCb) -> None:
        self._progress = cb

    # ------------------------------------------------------------------ #
    def parse_files(self, file_paths: List[str], work_dir: Optional[str] = None) -> ParseResult:
        """解析多模态文件与原型图链接为统一的文本素材。"""
        result = ParseResult()
        work_dir = work_dir or tempfile.mkdtemp(prefix="testcase_agent_")
        image_paths, video_paths, text_paths, link_urls = [], [], [], []

        for p in file_paths:
            if p.strip().startswith(("http://", "https://")):
                link_urls.append(p.strip())
            elif not os.path.exists(p):
                result.errors.append(f"文件不存在: {p}")
            elif is_image(p):
                image_paths.append(p)
            elif is_video(p):
                video_paths.append(p)
            else:
                text_paths.append(p)

        # 0) 原型图链接(Figma / MasterGo)→ 拉取页面截图后走视觉分析
        if link_urls:
            proto_images: List[str] = []
            for url in link_urls:
                if is_prototype_url(url):
                    self._progress(f"读取原型图链接: {url}")
                    shots, errs = fetch_prototype_screenshots(
                        url, work_dir,
                        figma_token=self.cfg.prototype.figma_token,
                        mastergo_token=self.cfg.prototype.mastergo_token,
                    )
                    proto_images.extend(shots)
                    for e in errs:
                        result.errors.append(f"{url}: {e}")
                else:
                    result.errors.append(f"不支持的链接(仅支持 Figma/MasterGo 原型图): {url}")
            if proto_images:
                self._progress(f"分析 {len(proto_images)} 张原型图截图(视觉模型)...")
                try:
                    descs = analyze_images(proto_images, self.llm, self.cfg.pipeline)
                    for d in descs:
                        result.materials.append(d)
                    result.parsed_files.extend(proto_images)
                except Exception as e:  # noqa: BLE001
                    result.errors.append(f"原型图截图分析失败: {e}")
                    logger.error("原型图截图分析失败: %s", e)

        # 1) 文本
        for p in text_paths:
            try:
                self._progress(f"解析文本文件: {os.path.basename(p)}")
                content = extract_text(p)
                if content.strip():
                    result.materials.append(f"[来源文件: {os.path.basename(p)}]\n{content}")
                    result.parsed_files.append(p)
                else:
                    result.skipped.append(p)
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"{os.path.basename(p)}: {e}")
                logger.error("文本解析失败 %s: %s", p, e)

        # 2) 图片(视觉模型)
        if image_paths:
            try:
                self._progress(f"分析 {len(image_paths)} 张图片(视觉模型)...")
                descs = analyze_images(image_paths, self.llm, self.cfg.pipeline)
                for p, d in zip(image_paths, descs):
                    result.materials.append(d)
                    result.parsed_files.append(p)
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"图片分析失败: {e}")
                logger.error("图片分析失败: %s", e)

        # 3) 视频(抽帧 + 视觉模型)
        for p in video_paths:
            try:
                self._progress(f"分析视频: {os.path.basename(p)}(抽帧 + 视觉模型)...")
                desc = analyze_video(p, self.llm, self.cfg.pipeline, work_dir)
                result.materials.append(desc)
                result.parsed_files.append(p)
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"{os.path.basename(p)}: {e}")
                logger.error("视频分析失败 %s: %s", p, e)

        return result

    # ------------------------------------------------------------------ #
    def run(self, file_paths: List[str], output_dir: str = "output",
            review: Optional[bool] = None) -> models.GenerationResult:
        """完整执行:解析 -> 分析 -> 生成 -> (评审) -> 导出。返回最终产物。"""
        if not file_paths:
            raise ValueError("请至少提供一个输入文件(图片 / 视频 / 文本)")

        os.makedirs(output_dir, exist_ok=True)
        parse = self.parse_files(file_paths, work_dir=os.path.join(output_dir, ".work"))
        for err in parse.errors:
            logger.warning("解析告警: %s", err)
        if not parse.materials:
            raise RuntimeError("没有可用的素材内容,请检查输入文件。详情: " + "; ".join(parse.errors))

        # 阶段一:产品分析
        self._progress("阶段 1/3: 分析产品,梳理测试点...")
        analysis = self.analyzer.analyze(parse.materials)

        # 阶段二:用例生成
        self._progress(f"阶段 2/3: 生成测试用例(上限 {self.cfg.pipeline.max_cases} 条)...")
        cases = self.generator.generate(analysis)

        # 阶段三:质量评审
        review_enabled = self.cfg.pipeline.review_enabled if review is None else review
        review_result = None
        if review_enabled:
            self._progress("阶段 3/3: 质量评审,补漏修正...")
            review_result = self.reviewer.review(analysis, cases)
            cases = review_result.cases

        result = models.GenerationResult(
            product_name=analysis.product_name, analysis=analysis,
            cases=cases, review=review_result,
        )

        # 导出
        self._export(result, output_dir)
        self._progress("全部完成 ✔")
        return result

    # ------------------------------------------------------------------ #
    def _export(self, result: models.GenerationResult, output_dir: str) -> List[str]:
        from ..exporters import export_all
        return export_all(result, output_dir, formats=self.cfg.export.formats)
