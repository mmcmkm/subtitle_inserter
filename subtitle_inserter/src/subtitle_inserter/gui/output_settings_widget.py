from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QFileDialog,
)

from ..core.settings import SettingsManager


class OutputSettingsWidget(QWidget):
    """Widget to edit output related settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.settings = SettingsManager()

        layout = QFormLayout(self)

        # Output directory
        hbox = QHBoxLayout()
        self.line_dir = QLineEdit()
        self.line_dir.setPlaceholderText("省略時は動画と同じ階層/output")
        btn_browse = QPushButton("…")
        btn_browse.clicked.connect(self._browse_dir)
        hbox.addWidget(self.line_dir, 1)
        hbox.addWidget(btn_browse)
        layout.addRow("出力フォルダー", hbox)

        # CRF spin
        self.spin_crf = QSpinBox()
        self.spin_crf.setRange(0, 51)
        layout.addRow("CRF (画質)", self.spin_crf)

        # Start offset
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(0.0, 3600.0)  # 0 秒～1 時間まで
        self.spin_offset.setSingleStep(0.1)
        self.spin_offset.setDecimals(2)
        layout.addRow("開始オフセット (秒)", self.spin_offset)

        # Preset combo
        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ])
        layout.addRow("Preset", self.combo_preset)

        self._load()

        self.line_dir.textChanged.connect(self._save)
        self.spin_crf.valueChanged.connect(self._save)
        self.spin_offset.valueChanged.connect(self._save)
        self.combo_preset.currentTextChanged.connect(self._save)

    # ------------------------------------------------------------------
    def _browse_dir(self):  # noqa: D401,N802
        d = QFileDialog.getExistingDirectory(self, "出力フォルダーを選択")
        if d:
            self.line_dir.setText(d)

    def _load(self):  # noqa: D401,N802
        self.line_dir.setText(self.settings.get("output_dir", ""))
        self.spin_crf.setValue(int(self.settings.get("crf", 23)))
        preset = self.settings.get("preset", "veryfast")
        idx = self.combo_preset.findText(preset)
        if idx >= 0:
            self.combo_preset.setCurrentIndex(idx)

        # start offset
        self.spin_offset.setValue(float(self.settings.get("start_offset", 0.0)))

    def _save(self):  # noqa: D401,N802
        self.settings.set("output_dir", self.line_dir.text())
        self.settings.set("crf", self.spin_crf.value())
        self.settings.set("preset", self.combo_preset.currentText())
        self.settings.set("start_offset", self.spin_offset.value())
        self.settings.save() 