from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubtitleLine:
    start: float  # seconds
    end: float  # seconds
    text: str

    def to_ass_dialogue(self) -> str:
        """Convert line to simple ASS dialogue line (no styling)."""
        def ts(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = sec % 60
            cs = int((s - int(s)) * 100)  # centiseconds
            return f"{h:d}:{m:02d}:{int(s):02d}.{cs:02d}"

        start_ts = ts(self.start)
        end_ts = ts(self.end)
        return f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{self.text}" 