from __future__ import annotations

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel


class OutlineLabel(QLabel):
    """QLabel 派生 - 簡易縁取りテキスト描画用。"""

    def __init__(self, text: str | None = None, parent=None):
        super().__init__(text or "", parent)
        self._outline_color = QColor("black")
        self._outline_width = 2
        self._shadow_enabled = True
        self._shadow_offset = 2
        self.setAlignment(Qt.AlignCenter)

    # ------------------------------------------------------------------
    def set_outline(self, color: str, width: int = 2):
        self._outline_color = QColor(color)
        self._outline_width = max(0, width)
        self.update()

    def set_shadow(self, enabled: bool, offset: int = 2):
        """ドロップシャドウの有無とオフセットを設定"""
        self._shadow_enabled = enabled
        self._shadow_offset = max(0, offset)
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event):  # noqa: N802, D401
        # ベースのスタイルシートから文字色を取得
        color = self.palette().windowText().color()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect: QRect = self.rect()

        # 影
        if self._shadow_enabled and self._shadow_offset > 0:
            painter.setPen(QColor(0, 0, 0, 150))  # 半透明ブラック
            painter.drawText(
                rect.translated(self._shadow_offset, self._shadow_offset),
                self.alignment(),
                self.text(),
            )

        # 縁取り (幅 0 ならスキップ)
        if self._outline_width > 0:
            for dx in range(-self._outline_width, self._outline_width + 1):
                for dy in range(-self._outline_width, self._outline_width + 1):
                    if dx == 0 and dy == 0:
                        continue
                    painter.setPen(self._outline_color)
                    painter.drawText(rect.translated(dx, dy), self.alignment(), self.text())

        # 本体
        painter.setPen(color)
        painter.drawText(rect, self.alignment(), self.text()) 