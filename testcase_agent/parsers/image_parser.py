"""图片解析:调用视觉大模型提取页面/功能信息;不支持视觉时给出明确提示。"""

from __future__ import annotations

import io
import logging
import os
from typing import List

from PIL import Image

from ..config import PipelineConfig
from ..llm.client import encode_image_to_data_uri
from ..prompts import VISION_IMAGE_TMPL

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}


def is_image(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def _resize_image_to_data_uri(path: str, max_size: int) -> str:
    """压缩图片到 max_size 以内并编码为 JPEG data URI。"""
    with Image.open(path) as img:
        img = img.convert("RGB")
        w, h = img.size
        longest = max(w, h)
        if longest > max_size:
            scale = max_size / longest
            img = img.resize((max(int(w * scale), 1), max(int(h * scale), 1)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        data = buf.getvalue()
    import base64
    return f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"


def analyze_images(paths: List[str], llm, cfg: PipelineConfig) -> List[str]:
    """批量分析图片,返回每张图的描述文本(与源文件一一对应)。"""
    results: List[str] = []
    if not llm.vision_enabled:
        raise RuntimeError(
            "当前模型不支持视觉输入,无法分析图片。请在配置中指定支持视觉的模型,"
            "例如 vision_model: gpt-4o / qwen-vl-max / deepseek-vl,或用文本形式提供产品资料。"
        )
    for p in paths:
        logger.info("正在分析图片: %s", os.path.basename(p))
        uri = _resize_image_to_data_uri(p, cfg.max_image_size)
        desc = llm.vision_analyze(VISION_IMAGE_TMPL, [uri])
        # 组装为一段可读文本
        page = desc.get("page") or os.path.basename(p)
        elements = "、".join(desc.get("elements") or []) if isinstance(desc.get("elements"), list) else desc.get("elements", "")
        texts = "、".join(desc.get("texts") or []) if isinstance(desc.get("texts"), list) else desc.get("texts", "")
        notes = desc.get("notes") or desc.get("states") or ""
        block = [
            f"【图片素材:{os.path.basename(p)}】页面/用途:{page}",
            f"功能元素:{elements}" if elements else "",
            f"关键文案/字段:{texts}" if texts else "",
            f"说明:{notes}" if notes else "",
        ]
        results.append("\n".join(x for x in block if x))
    return results


def image_to_data_uri(path: str, max_size: int = 1280) -> str:
    """对外工具:单图转 data URI。"""
    return _resize_image_to_data_uri(path, max_size)
