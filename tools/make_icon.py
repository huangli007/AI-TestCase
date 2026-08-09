"""生成应用图标:assets/icon.png(512) 与 assets/icon.ico(多尺寸,供 PyInstaller 打包)。

图标设计:靛蓝圆角方块 + 白色 "TC" 文字(与 GUI Logo 一致)。
"""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)


def _round_rect(draw: ImageDraw.ImageDraw, xy, radius, fill):
    """圆角矩形。"""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def make_icon(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 靛蓝圆角底
    pad = int(size * 0.04)
    _round_rect(draw, (pad, pad, size - pad, size - pad), radius=int(size * 0.2), fill=(47, 79, 196, 255))
    # 白色 TC 文字
    try:
        font = ImageFont.truetype("arial.ttf", int(size * 0.52))
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    text = "TC"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), text,
              font=font, fill=(255, 255, 255, 255))
    return img


def main() -> int:
    icon = make_icon(512)
    icon.save(ASSETS / "icon.png")
    # ICO 多尺寸
    icon.save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"图标已生成: {ASSETS / 'icon.png'}, {ASSETS / 'icon.ico'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
