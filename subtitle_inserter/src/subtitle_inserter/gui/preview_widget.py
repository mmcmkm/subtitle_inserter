from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..core.settings import SettingsManager
from .outline_label import OutlineLabel


class PreviewWidget(QWidget):
    """シンプルな字幕テキストサンプルを表示するウィジェット。"""

    def __init__(self, parent: Optional[QWidget] = None):  # noqa: D401
        super().__init__(parent)

        self._label: OutlineLabel = OutlineLabel("字幕プレビューなし")
        # 初期スタイル
        self.apply_style(SettingsManager().get("font", {}))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        self.setStyleSheet("background-color: black;")

        self._lines: List[str] = []
        self._index = 0

        self._timer = QTimer(self)
        self._timer.setInterval(1500)  # 1.5 秒ごとに切り替え
        self._timer.timeout.connect(self._next_line)

    # ------------------------------------------------------------------
    def display_lines(self, lines: List[str]):
        """字幕テキストのリストを受け取って順番に表示。"""
        self._lines = lines or ["字幕プレビューなし"]
        self._index = 0
        self._label.setText(self._lines[0])
        if len(self._lines) > 1:
            self._timer.start()
        else:
            self._timer.stop()

    def clear(self):  # noqa: D401
        """表示をリセット。"""
        self._timer.stop()
        self._lines = []
        self._label.setText("字幕プレビューなし")

    # ------------------------------------------------------------------
    def _next_line(self):
        if not self._lines:
            return
        self._index = (self._index + 1) % len(self._lines)
        self._label.setText(self._lines[self._index])

    # ------------------------------------------------------------------
    def sizeHint(self):  # noqa: D401
        return self.parent().size() if self.parent() else super().sizeHint()

    def apply_style(self, font_cfg: dict):
        """フォント設定 dict を受け取り、ラベルのスタイルを更新"""
        family = font_cfg.get("family", "Arial")
        size = font_cfg.get("size", 32)
        color = font_cfg.get("color", "#ffffff")
        outline_color = font_cfg.get("outline_color", "#000000")
        outline_width = font_cfg.get("outline_width", 2)
        bold = font_cfg.get("bold", False)
        shadow = font_cfg.get("shadow", True)

        weight = "bold" if bold else "normal"
        self._label.setStyleSheet(
            f"color: {color}; font-size: {size}px; font-family: '{family}'; font-weight: {weight};"
        )

        self._label.set_outline(outline_color, outline_width)
        self._label.set_shadow(shadow)

        # stroke is always drawn; shadow flag currently ignored in preview 