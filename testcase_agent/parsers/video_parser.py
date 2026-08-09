"""视频解析:基于 ffmpeg(imageio-ffmpeg 自带二进制)抽帧,再交给视觉模型理解。"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from typing import List

from ..config import PipelineConfig
from ..prompts import VISION_VIDEO_TMPL

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}


def is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("未找到 ffmpeg,请安装 imageio-ffmpeg 或系统 ffmpeg") from e


def probe_video(path: str) -> dict:
    """读取视频基础信息:时长、分辨率、帧率。"""
    ffmpeg = _ffmpeg_exe()
    try:
        out = subprocess.run(
            [ffmpeg, "-i", path, "-hide_banner"], capture_output=True, text=True, timeout=60
        ).stderr
    except Exception as e:  # noqa: BLE001
        logger.warning("probe 视频信息失败: %s", e)
        return {}
    info: dict = {}
    for line in out.splitlines():
        line = line.strip()
        if "Duration:" in line and "Duration" not in info:
            dur = line.split("Duration:")[1].split(",")[0].strip()
            info["duration"] = dur
        if "Stream" in line and ("Video:" in line):
            match = line.split("Video:")[1]
            if "," in match:
                res = match.split(",")[1].strip()
                info["resolution"] = res
    return info


def extract_frames(path: str, cfg: PipelineConfig, out_dir: str) -> List[str]:
    """按时间均匀抽帧,返回帧图片路径列表。"""
    ffmpeg = _ffmpeg_exe()
    info = probe_video(path)
    duration_sec: float = 0.0
    if info.get("duration"):
        try:
            parts = info["duration"].split(":")
            duration_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except Exception:  # noqa: BLE001
            duration_sec = 0.0

    if duration_sec <= 0:
        duration_sec = cfg.max_frames_per_video * cfg.frame_interval  # 未知时长则保守抽样

    n_frames = min(cfg.max_frames_per_video, max(2, int(duration_sec / cfg.frame_interval)))
    interval = duration_sec / n_frames

    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "frame_%03d.jpg")
    cmd = [ffmpeg, "-y", "-i", path, "-vf", f"fps=1/{interval:.3f}", "-q:v", "3", pattern]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"视频抽帧失败: {result.stderr[-500:]}")

    frames = sorted(
        f for f in os.listdir(out_dir) if f.startswith("frame_") and f.endswith(".jpg")
    )
    # 若抽帧数远超上限,等距截取
    if len(frames) > cfg.max_frames_per_video:
        step = len(frames) / cfg.max_frames_per_video
        frames = [frames[int(i * step)] for i in range(cfg.max_frames_per_video)]
    return [os.path.join(out_dir, f) for f in frames]


def analyze_video(path: str, llm, cfg: PipelineConfig, work_dir: str) -> str:
    """抽帧 -> 视觉模型理解 -> 返回结构化描述文本。"""
    if not llm.vision_enabled:
        raise RuntimeError(
            "当前模型不支持视觉输入,无法分析视频。请配置视觉模型"
            "(vision_model: gpt-4o / qwen-vl-max / deepseek-vl 等)。"
        )
    logger.info("正在分析视频: %s", os.path.basename(path))
    frame_dir = os.path.join(work_dir, f"frames_{os.path.splitext(os.path.basename(path))[0]}")
    frames = extract_frames(path, cfg, frame_dir)

    from .image_parser import image_to_data_uri
    uris = [image_to_data_uri(f, cfg.max_image_size) for f in frames]
    desc = llm.vision_analyze(VISION_VIDEO_TMPL, uris)

    info = probe_video(path)
    head = (
        f"【视频素材:{os.path.basename(path)}】"
        f"时长 {info.get('duration', '未知')}, 分辨率 {info.get('resolution', '未知')}\n"
    )
    body = json.dumps(desc, ensure_ascii=False, indent=2) if isinstance(desc, dict) else str(desc)
    return head + body
