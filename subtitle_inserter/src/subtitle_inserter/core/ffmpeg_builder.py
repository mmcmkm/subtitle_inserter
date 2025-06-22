from __future__ import annotations

import shlex
from pathlib import Path
from typing import List

from .logger import get_logger
from .subtitle_model import SubtitleLine
from .settings import SettingsManager

logger = get_logger(__name__)


class FFmpegCommandBuilder:
    """Build FFmpeg command for burning subtitles."""

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        video_path: Path | None = None,
        subtitles_path: Path | None = None,
        output_path: Path | None = None,
        codec_copy: bool = True,
        extra_opts: List[str] | None = None,
        crf: int | None = None,
        preset: str | None = None,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.video_path = Path(video_path) if video_path else None
        self.subtitles_path = Path(subtitles_path) if subtitles_path else None
        self.output_path = Path(output_path) if output_path else None
        self.codec_copy = codec_copy
        self.extra_opts: List[str] = extra_opts or []
        self.crf = crf
        self.preset = preset

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build(self) -> List[str]:
        if not self.video_path or not self.output_path:
            raise ValueError("video_path と output_path は必須です")

        cmd = [self.ffmpeg_path, "-y", "-i", str(self.video_path)]

        # Subtitles filter
        vf_parts: List[str] = []
        if self.subtitles_path:
            sub_path = self._escape_path(self.subtitles_path)
            style_str = self._build_force_style()
            if style_str:
                vf_parts.append(f"subtitles='{sub_path}':force_style='{style_str}'")
            else:
                vf_parts.append(f"subtitles='{sub_path}'")

        if vf_parts:
            cmd += ["-vf", ",".join(vf_parts)]

        if self.codec_copy and not vf_parts:
            # フィルタ未使用時のみコーデックコピーを許可
            cmd += ["-c:v", "copy", "-c:a", "copy"]
        else:
            # フィルタを使用する場合は再エンコード（H.264 / AAC）
            crf_val = str(self.crf or 23)
            preset_val = self.preset or "veryfast"
            cmd += ["-c:v", "libx264", "-crf", crf_val, "-preset", preset_val, "-c:a", "aac"]

        if self.extra_opts:
            cmd += self.extra_opts

        cmd.append(str(self.output_path))
        logger.debug("FFmpeg command: %s", shlex.join(cmd))
        return cmd

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    @staticmethod
    def _escape_path(path: Path) -> str:
        # Windows の場合、バックスラッシュをスラッシュに置換してエスケープ
        p = path.as_posix()
        # For FFmpeg filter path on Windows, backslash-escape backslash and colon.
        escaped = p.replace("\\", "\\\\")
        escaped = escaped.replace(":", "\\:")
        return escaped

    def _build_force_style(self) -> str | None:
        """Settings のフォント設定を libass force_style 文字列に変換"""
        cfg = SettingsManager().get("font", {})
        if not cfg:
            return None
        parts = []
        if family := cfg.get("family"):
            parts.append(f"FontName={family}")
        if size := cfg.get("size"):
            parts.append(f"FontSize={size}")

        def hex_to_ass(col: str):
            c = col.lstrip("#")
            if len(c) != 6:
                return None
            r, g, b = c[0:2], c[2:4], c[4:6]
            return f"&H00{b}{g}{r}"

        if color := cfg.get("color"):
            v = hex_to_ass(color)
            if v:
                parts.append(f"PrimaryColour={v}")
        if outline := cfg.get("outline_color"):
            v = hex_to_ass(outline)
            if v:
                parts.append(f"OutlineColour={v}")
        if width := cfg.get("outline_width"):
            parts.append(f"Outline={width}")
        if cfg.get("bold"):
            parts.append("Bold=1")
        if cfg.get("shadow"):
            parts.append("Shadow=1")
        else:
            parts.append("Shadow=0")
        return ",".join(parts) if parts else None 