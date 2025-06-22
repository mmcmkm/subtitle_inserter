from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel


class DropArea(QLabel):
    """A QLabel that accepts file drops and emits a signal with file paths."""

    filesDropped: Signal = Signal(list)

    def __init__(self, text: str | None = None, parent=None) -> None:
        super().__init__(text or "ここに動画ファイルや字幕ファイルをドロップ")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setStyleSheet(
            """
            QLabel {
                border: 2px dashed #aaa;
                font-size: 14px;
                color: #666;
            }
            """
        )

    # ------------------------------------------------------------------
    # Qt Events
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        file_paths: List[str] = [Path(u.toLocalFile()).as_posix() for u in urls]
        if file_paths:
            self.filesDropped.emit(file_paths)
        event.acceptProposedAction() 