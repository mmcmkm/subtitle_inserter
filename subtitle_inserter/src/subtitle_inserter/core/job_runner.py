from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from .logger import get_logger

logger = get_logger(__name__)


class JobRunner(QObject):
    """Run FFmpeg command in separate thread and emit progress/finished signals."""

    progressChanged: Signal = Signal(float)  # 0.0 - 1.0
    finished: Signal = Signal(object)  # returncode can exceed 32-bit range on Windows
    errorOccurred: Signal = Signal(str)

    def __init__(self, command: List[str], duration: Optional[float] = None):
        super().__init__()
        self._command = command
        self._duration = duration  # seconds, optional for progress calc
        self._thread: QThread | None = None
        self._proc: subprocess.Popen | None = None
        self._stop_requested = False

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def start(self) -> None:
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run)
        self._thread.start()

    def stop(self) -> None:
        """Request cancellation of the running job."""
        self._stop_requested = True
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------
    def _run(self) -> None:  # noqa: D401
        logger.info("FFmpeg 実行開始: %s", " ".join(self._command))
        try:
            with subprocess.Popen(
                self._command,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            ) as proc:
                if proc.stderr is None:
                    raise RuntimeError("stderr pipe を取得できませんでした")

                self._proc = proc
                for line in proc.stderr:
                    logger.debug("ffmpeg: %s", line.rstrip())
                    if self._duration is None and "Duration:" in line:
                        self._duration = self._parse_duration_line(line)
                    self._parse_progress(line)
                    if self._stop_requested:
                        proc.terminate()
                        break

            rc = proc.returncode if proc else -1
            self.finished.emit(rc)
        except Exception as e:  # noqa: BLE001
            logger.exception("JobRunner error: %s", e)
            self.errorOccurred.emit(str(e))
            self.finished.emit(-1)
        finally:
            if self._thread:
                self._thread.quit()
                self._thread.wait()
            self._proc = None

    # ------------------------------------------------------------
    def _parse_progress(self, line: str) -> None:
        """Parse FFmpeg stderr line and emit progress as percentage if possible."""
        if self._duration is None:
            return  # duration unknown; skip progress
        if "time=" not in line:
            return
        # example: frame=  240 fps=0.0 q=-1.0 Lsize=       0kB time=00:00:08.00 bitrate=   0.0kbits/s speed=15.9x
        try:
            time_part = line.split("time=")[1].split()[0]
            h, m, s = time_part.split(":")
            sec = int(h) * 3600 + int(m) * 60 + float(s)
            progress = min(sec / self._duration, 1.0)
            self.progressChanged.emit(progress)
        except Exception:
            # ignore parse errors
            pass

    @staticmethod
    def _parse_duration_line(line: str) -> float | None:
        """Extract duration seconds from a line like ' Duration: 00:01:23.45,'"""
        if "Duration:" not in line:
            return None
        try:
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            sec = int(h) * 3600 + int(m) * 60 + float(s)
            return sec
        except Exception:
            return None 