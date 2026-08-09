"""多模态解析:文本 / 图片 / 视频 -> 统一的文本素材。"""

from .text_parser import extract_text
from .image_parser import analyze_images
from .video_parser import analyze_video

__all__ = ["extract_text", "analyze_images", "analyze_video"]
