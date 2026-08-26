"""原型图链接解析:支持 Figma / MasterGo 分享链接,拉取页面截图作为视觉素材。

策略:
- Figma   : 优先官方 REST API(`X-Figma-Token` 导出节点 PNG);无 Token 时降级浏览器截图
- MasterGo: 无公开稳定的 REST 截图接口,使用无头浏览器(Playwright,可选依赖)打开分享链接截图

返回统一结构: (screenshot_paths, errors)
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

FIGMA_API = "https://api.figma.com"
# 单次导出节点上限与最大导出张数
MAX_EXPORT_NODES = 12

# 链接识别正则
_FIGMA_RE = re.compile(
    r"figma\.com/(?:design|file|proto)/([A-Za-z0-9_-]+)", re.IGNORECASE)
_MASTERGO_RE = re.compile(
    r"mastergo\.com/(?:file|app/file|community|proto)/([A-Za-z0-9_-]+)", re.IGNORECASE)


def parse_prototype_url(url: str) -> Tuple[str, str]:
    """解析原型图链接,返回 (platform, file_key);无法识别抛 ValueError。"""
    url = url.strip()
    m = _FIGMA_RE.search(url)
    if m:
        return "figma", m.group(1)
    m = _MASTERGO_RE.search(url)
    if m:
        return "mastergo", m.group(1)
    raise ValueError(f"无法识别原型图链接(仅支持 Figma / MasterGo): {url}")


# ------------------------------------------------------------------ #
# Figma REST API
# ------------------------------------------------------------------ #
def fetch_figma_screenshots(url: str, token: str, work_dir: str) -> Tuple[List[str], List[str]]:
    """通过 Figma REST API 导出文件首层画板为 PNG。"""
    _, file_key = parse_prototype_url(url)
    headers = {"X-Figma-Token": token}
    errors: List[str] = []
    paths: List[str] = []

    # 1) 获取文件结构(顶层 canvas/frame 节点)
    try:
        resp = requests.get(f"{FIGMA_API}/v1/files/{file_key}",
                            headers=headers, timeout=60)
        resp.raise_for_status()
        doc = resp.json()["document"]
    except Exception as e:  # noqa: BLE001
        errors.append(f"Figma 获取文件失败({file_key}): {_short_err(e)}")
        return paths, errors

    nodes: List[dict] = []
    for canvas in doc.get("children", [])[:6]:
        for child in canvas.get("children", [])[:4]:
            if child.get("type") in ("FRAME", "COMPONENT", "SECTION", "BOOLEAN_OPERATION"):
                nodes.append(child)
        if len(nodes) >= MAX_EXPORT_NODES:
            break
    if not nodes:
        errors.append("Figma 文件中未找到可导出的画板(FRAME)节点")
        return paths, errors

    # 2) 批量导出节点图片
    ids = [n["id"] for n in nodes]
    try:
        resp = requests.get(
            f"{FIGMA_API}/v1/images/{file_key}",
            params={"ids": ",".join(ids), "format": "png", "scale": "1.5"},
            headers=headers, timeout=120,
        )
        resp.raise_for_status()
        images = resp.json().get("images", {})
    except Exception as e:  # noqa: BLE001
        errors.append(f"Figma 导出图片失败({file_key}): {_short_err(e)}")
        return paths, errors

    os.makedirs(work_dir, exist_ok=True)
    for idx, n in enumerate(nodes, start=1):
        img_url = images.get(n["id"])
        if not img_url:
            continue
        try:
            r = requests.get(img_url, timeout=120)
            r.raise_for_status()
            fname = f"figma_{file_key[:6]}_{idx:02d}.png"
            out = os.path.join(work_dir, fname)
            with open(out, "wb") as fh:
                fh.write(r.content)
            paths.append(out)
        except Exception as e:  # noqa: BLE001
            errors.append(f"下载 Figma 截图失败({n.get('name', n['id'])}): {_short_err(e)}")
    return paths, errors


# ------------------------------------------------------------------ #
# 浏览器截图(任意网页/Figma 无 Token 降级/MasterGo)
# ------------------------------------------------------------------ #
def browser_screenshot(url: str, out_path: str, timeout: int = 45) -> None:
    """用 Playwright 无头浏览器截图。

    启动顺序:系统 Edge -> 系统 Chrome -> Playwright Chromium,
    优先用系统自带浏览器,无需打包/下载浏览器二进制。
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = None
        last_err: Optional[Exception] = None
        for kw in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
            try:
                browser = p.chromium.launch(headless=True, **kw)
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
        if browser is None:
            raise RuntimeError(
                f"找不到可用浏览器(Edge/Chrome/Playwright Chromium): {_short_err(last_err)}")
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            # 拦截字体/媒体请求 + 强制本地字体:避免慢资源/远程字体阻塞截图
            page.route("**/*", lambda route: (
                route.abort() if route.request.resource_type in ("font", "media")
                else route.continue_()))
            page.goto(url, wait_until="commit", timeout=min(timeout, 40) * 1000)
            page.add_style_tag(content="*{font-family:'Segoe UI',Arial,sans-serif !important;}")
            page.wait_for_timeout(6000)
            try:
                page.wait_for_selector("body", timeout=3000)
            except Exception:  # noqa: BLE001
                pass
            page.screenshot(path=out_path, full_page=False, timeout=15000)
        finally:
            browser.close()


def fetch_mastergo_screenshots(url: str, work_dir: str) -> Tuple[List[str], List[str]]:
    """MasterGo 分享链接 → 无头浏览器截图(需要可选依赖 playwright)。"""
    _, file_key = parse_prototype_url(url)
    os.makedirs(work_dir, exist_ok=True)
    out = os.path.join(work_dir, f"mastergo_{file_key[:6]}_01.png")
    try:
        browser_screenshot(url, out)
        return [out], []
    except ImportError:
        return [], ["读取 MasterGo 需要浏览器截图能力,请先安装: pip install playwright && playwright install chromium"]
    except Exception as e:  # noqa: BLE001
        return [], [f"MasterGo 截图失败({file_key}): {_short_err(e)};若为权限链接,请导出图片后本地添加"]


# ------------------------------------------------------------------ #
# 统一入口
# ------------------------------------------------------------------ #
def fetch_prototype_screenshots(url: str, work_dir: str,
                                figma_token: str = "", mastergo_token: str = ""
                                ) -> Tuple[List[str], List[str]]:
    """解析链接并拉取截图。返回 (截图路径列表, 错误列表)。

    支持: Figma(有 Token 走 REST API,无则浏览器截图)、MasterGo、任意网页原型(浏览器截图)。
    """
    try:
        platform, key = parse_prototype_url(url)
    except ValueError:
        platform, key = "web", "site"

    if platform == "figma" and figma_token:
        return fetch_figma_screenshots(url, figma_token, work_dir)

    # 无 Token 或非 Figma:浏览器截图(优先系统 Edge,回退 Chromium)
    os.makedirs(work_dir, exist_ok=True)
    out = os.path.join(work_dir, f"{platform}_{key[:8]}_01.png")
    try:
        browser_screenshot(url, out)
        return [out], []
    except ImportError:
        return [], ["读取该链接需要浏览器截图能力,请先安装: pip install playwright && playwright install chromium;"
                    "或配置 Figma Token"]
    except Exception as e:  # noqa: BLE001
        return [], [f"{'Figma' if platform == 'figma' else '网页'}截图失败: {_short_err(e)};"
                    "建议配置 Figma Token,或确认系统已安装 Edge/Chrome"]


def _short_err(e: Exception, limit: int = 160) -> str:
    s = str(e).strip().replace("\n", " ")
    return s if len(s) <= limit else s[:limit] + "…"


def is_prototype_url(url: str) -> bool:
    return bool(_FIGMA_RE.search(url) or _MASTERGO_RE.search(url))
