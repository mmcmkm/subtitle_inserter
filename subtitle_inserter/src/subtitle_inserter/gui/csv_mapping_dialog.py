from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from ..core.logger import get_logger

logger = get_logger(__name__)


class CsvMappingDialog(QDialog):
    """Dialog to configure CSV column mapping."""

    def __init__(self, csv_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV 列マッピング設定")
        self.resize(400, 200)

        self.csv_path = csv_path
        df = pd.read_csv(csv_path, nrows=1)
        self.columns: List[str] = list(df.columns)
        if not self.columns:  # no header
            self.columns = [str(i) for i in range(len(df.iloc[0]))]

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_start = QComboBox()
        self.combo_start.addItems(self.columns)
        form.addRow("開始列", self.combo_start)

        self.combo_end = QComboBox()
        self.combo_end.addItems(["<なし>"] + self.columns)
        form.addRow("終了列", self.combo_end)

        self.combo_text = QComboBox()
        self.combo_text.addItems(self.columns)
        form.addRow("テキスト列", self.combo_text)

        # time unit
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["seconds", "frames"])
        form.addRow("時間単位", self.combo_unit)

        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(1, 240)
        self.spin_fps.setValue(30)
        form.addRow("FPS", self.spin_fps)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    def get_mapping(self) -> Dict[str, str | int | None]:
        """Return mapping dict chosen by user."""
        start_col = self.combo_start.currentText()
        end_col = None if self.combo_end.currentIndex() == 0 else self.combo_end.currentText()
        text_col = self.combo_text.currentText()
        return {
            "start_col": start_col,
            "end_col": end_col,
            "text_col": text_col,
            "time_unit": self.combo_unit.currentText(),
            "fps": self.spin_fps.value(),
        } 