"""液态玻璃背景层:渐变底 + 3 个径向光斑(缓存渲染,性能优先)。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget


class BackgroundWidget(QWidget):
    """窗口背景:深蓝紫渐变 + 琥珀/靛蓝/品红光斑(玻璃的折射光源)。

    渐变与光斑预先渲染到 QPixmap 缓存,尺寸变化时才重建,避免每帧重绘。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache: QPixmap | None = None

    def paintEvent(self, event):  # noqa: N802
        size = self.size()
        if self._cache is None or self._cache.size() != size:
            self._cache = self._render(size.width(), size.height())
        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache)

    def _render(self, w: int, h: int) -> QPixmap:
        pm = QPixmap(max(w, 1), max(h, 1))
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1) 深蓝紫渐变底
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor("#141B4D"))
        grad.setColorAt(0.45, QColor("#2A1E5C"))
        grad.setColorAt(1.0, QColor("#4B3A8F"))
        p.fillRect(0, 0, w, h, grad)

        # 2) 三个径向光斑(玻璃折射光源)
        spots = [
            (0.10 * w, 0.08 * h, 0.55 * w, QColor(255, 179, 0, 115)),   # 琥珀 α0.45
            (0.92 * w, 0.18 * h, 0.55 * w, QColor(63, 81, 181, 140)),   # 靛蓝 α0.55
            (0.55 * w, 0.98 * h, 0.62 * w, QColor(212, 83, 126, 90)),   # 品红 α0.35
        ]
        for cx, cy, radius, color in spots:
            rg = QRadialGradient(cx, cy, radius)
            c = QColor(color)
            rg.setColorAt(0.0, c)
            faded = QColor(c)
            faded.setAlpha(0)
            rg.setColorAt(1.0, faded)
            p.setBrush(rg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
        p.end()
        return pm
