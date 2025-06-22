from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

import chardet
import pandas as pd
import pysubs2

from .logger import get_logger
from .subtitle_model import SubtitleLine

logger = get_logger(__name__)


class SubtitleParserError(Exception):
    """Raised when failing to parse subtitle file."""


class SubtitleParser:
    """Base class for subtitle parsers."""

    def parse(self, file: Path, **kwargs) -> List[SubtitleLine]:  # noqa: D401
        """Parse file and return subtitle lines."""
        raise NotImplementedError


class SRTParser(SubtitleParser):
    def parse(self, file: Path, **kwargs) -> List[SubtitleLine]:
        try:
            subs = pysubs2.load(str(file), encoding="utf-8", fps=kwargs.get("fps"))
        except UnicodeDecodeError:
            # try chardet detection
            raw = file.read_bytes()
            enc = chardet.detect(raw)["encoding"] or "utf-8"
            subs = pysubs2.load_from_memory(raw, encoding=enc, fps=kwargs.get("fps"))
        lines: List[SubtitleLine] = []
        for e in subs:
            lines.append(
                SubtitleLine(
                    start=e.start / 1000.0,
                    end=e.end / 1000.0,
                    text=e.text.replace("\n", "\\N"),
                )
            )
        return lines


class ASSParser(SubtitleParser):
    def parse(self, file: Path, **kwargs) -> List[SubtitleLine]:
        subs = pysubs2.load(str(file))
        lines: List[SubtitleLine] = []
        for e in subs:
            lines.append(
                SubtitleLine(
                    start=e.start / 1000.0,
                    end=e.end / 1000.0,
                    text=e.text.replace("\n", "\\N"),
                )
            )
        return lines


class CSVParser(SubtitleParser):
    """CSV parser with configurable column mapping."""

    def parse(
        self,
        file: Path,
        start_col: str | int,
        text_col: str | int,
        end_col: str | int | None = None,
        fps: float = 30.0,
        time_format: str = "seconds",  # "seconds" or "frames"
        **kwargs,
    ) -> List[SubtitleLine]:
        # Auto encoding detect
        with file.open("rb") as f:
            raw = f.read()
        enc = chardet.detect(raw)["encoding"] or "utf-8"
        logger.debug("CSV encoding detect: %s", enc)

        df = pd.read_csv(file, encoding=enc)

        def _time_to_sec(value):
            if time_format == "frames":
                return float(value) / fps
            return float(value)

        lines: List[SubtitleLine] = []
        for _, row in df.iterrows():
            start = _time_to_sec(row[start_col])
            end: Optional[float] = None
            if end_col is not None and end_col in df.columns:
                end = _time_to_sec(row[end_col])
            if end is None or end <= start:
                end = start + 3.0  # default 3 seconds
            text = str(row[text_col])
            lines.append(SubtitleLine(start=start, end=end, text=text))
        return lines 