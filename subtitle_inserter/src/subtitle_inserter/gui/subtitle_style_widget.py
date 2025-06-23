from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QFontComboBox,
    QSpinBox,
    QPushButton,
    QColorDialog,
    QCheckBox,
    QVBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from .outline_label import OutlineLabel

from ..core.settings import SettingsManager


class SubtitleStyleWidget(QWidget):
    """フォント・色など字幕スタイルを編集するタブ。"""

    styleChanged: Signal = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = SettingsManager()

        main_layout = QVBoxLayout(self)
        layout = QFormLayout()

        # Font family
        self.combo_font = QFontComboBox()
        layout.addRow("フォント", self.combo_font)

        # Font size
        self.spin_size = QSpinBox()
        self.spin_size.setRange(8, 200)
        layout.addRow("サイズ(px)", self.spin_size)

        # Outline width spinbox
        self.spin_outline_width = QSpinBox()
        self.spin_outline_width.setRange(0, 10)
        layout.addRow("縁取り幅", self.spin_outline_width)

        # Bottom margin
        self.spin_margin_v = QSpinBox()
        self.spin_margin_v.setRange(0, 500)
        layout.addRow("下余白(px)", self.spin_margin_v)

        # Color buttons
        self.btn_color = QPushButton()
        self.btn_color.clicked.connect(lambda: self._pick_color("color"))
        layout.addRow("文字色", self.btn_color)

        self.btn_outline = QPushButton()
        self.btn_outline.clicked.connect(lambda: self._pick_color("outline_color"))
        layout.addRow("縁取り色", self.btn_outline)

        # Bold / Shadow
        self.chk_bold = QCheckBox("太字")
        self.chk_shadow = QCheckBox("影を有効")
        hbox = QWidget()
        h_layout = QFormLayout(hbox)
        h_layout.addRow(self.chk_bold)
        h_layout.addRow(self.chk_shadow)
        layout.addRow("効果", hbox)

        # Reset button
        btn_reset = QPushButton("デフォルトにリセット")
        btn_reset.clicked.connect(self._reset_defaults)
        layout.addRow(btn_reset)

        main_layout.addLayout(layout)

        # Sample preview label
        self.sample_label: OutlineLabel = OutlineLabel("サンプル\nSample")
        self.sample_label.setFixedHeight(120)
        self.sample_label.setStyleSheet("background-color: black;")
        main_layout.addWidget(self.sample_label)

        self._load()

        # Connect
        self.combo_font.currentTextChanged.connect(self._save)
        self.spin_size.valueChanged.connect(self._save)
        self.spin_outline_width.valueChanged.connect(self._save)
        self.spin_margin_v.valueChanged.connect(self._save)
        self.chk_bold.stateChanged.connect(self._save)
        self.chk_shadow.stateChanged.connect(self._save)

        # 初期サンプル反映
        self._apply_to_sample(self.settings.get("font", {}))

    # ------------------------------------------------------------------
    def _color_to_qss(self, color_str: str) -> str:
        return color_str

    def _set_btn_color(self, btn: QPushButton, color_str: str):
        btn.setStyleSheet(f"background-color: {color_str};")

    def _pick_color(self, key: str):
        current = QColor(self.settings.get("font", {}).get(key, "#ffffff"))
        color = QColorDialog.getColor(current, self, "色を選択")
        if color.isValid():
            font_cfg = self.settings.get("font", {}).copy()
            font_cfg[key] = color.name()
            self.settings.set("font", font_cfg)
            self.settings.save()
            self._set_btn_color(self.btn_color if key == "color" else self.btn_outline, color.name())
            self.styleChanged.emit(font_cfg)
            self._apply_to_sample(font_cfg)

    def _load(self):
        cfg = self.settings.get("font", {})
        self.combo_font.setCurrentText(cfg.get("family", "Arial"))
        self.spin_size.setValue(int(cfg.get("size", 32)))
        self.spin_outline_width.setValue(int(cfg.get("outline_width", 2)))
        self.spin_margin_v.setValue(int(cfg.get("margin_v", 0)))
        self._set_btn_color(self.btn_color, cfg.get("color", "#ffffff"))
        self._set_btn_color(self.btn_outline, cfg.get("outline_color", "#000000"))
        self.chk_bold.setChecked(bool(cfg.get("bold", False)))
        self.chk_shadow.setChecked(bool(cfg.get("shadow", True)))
        self._apply_to_sample(cfg)

    def _save(self):
        cfg = self.settings.get("font", {}).copy()
        cfg.update(
            {
                "family": self.combo_font.currentText(),
                "size": self.spin_size.value(),
                "bold": self.chk_bold.isChecked(),
                "shadow": self.chk_shadow.isChecked(),
                "outline_width": self.spin_outline_width.value(),
                "margin_v": self.spin_margin_v.value(),
            }
        )
        self.settings.set("font", cfg)
        self.settings.save()
        self.styleChanged.emit(cfg)
        self._apply_to_sample(cfg)

    # ------------------------------------------------------------------
    def _apply_to_sample(self, cfg: dict):
        """サンプルラベルにスタイル適用"""
        family = cfg.get("family", "Arial")
        size = cfg.get("size", 32)
        color = cfg.get("color", "#ffffff")
        bold = cfg.get("bold", False)
        outline_width = cfg.get("outline_width", 2)
        weight = "bold" if bold else "normal"
        self.sample_label.setStyleSheet(
            f"background-color: black; color: {color}; font-size: {size}px; font-family: '{family}'; font-weight: {weight};"
        )

        self.sample_label.set_outline(cfg.get("outline_color", "#000000"), outline_width)
        self.sample_label.set_shadow(cfg.get("shadow", True))

    def _reset_defaults(self):
        """デフォルト値に戻す"""
        defaults = SettingsManager.DEFAULTS["font"].copy()
        self.settings.set("font", defaults)
        self.settings.save()
        # reload controls
        self._load()
        self.styleChanged.emit(defaults)
        self._apply_to_sample(defaults) 