from __future__ import annotations

"""Command-line interface for batch processing (non-GUI)."""

import argparse
import subprocess
import sys
from pathlib import Path
import tempfile
from typing import List

from .core.ffmpeg_builder import FFmpegCommandBuilder
from .core.logger import setup_logger, get_logger
from .core.settings import SettingsManager  # noqa: F401  # ensure settings initialized
from .core.parsers import SRTParser, ASSParser, CSVParser
from .core.subtitle_model import SubtitleLine


def _build_output_path(video_path: Path) -> Path:
    return video_path.with_name(video_path.stem + "_sub" + video_path.suffix)


def run_once(
    video_path: Path,
    subtitles_path: Path | None = None,
    output_path: Path | None = None,
    codec_copy: bool = True,
    crf: int | None = None,
    preset: str | None = None,
) -> int:
    """Run FFmpeg job once and return return-code."""
    builder = FFmpegCommandBuilder(
        video_path=video_path,
        subtitles_path=subtitles_path,
        output_path=output_path or _build_output_path(video_path),
        codec_copy=codec_copy,
        crf=crf,
        preset=preset,
    )
    cmd = builder.build()
    logger = get_logger(__name__)
    logger.info("Run: %s", " ".join(cmd))
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> None:  # noqa: D401
    parser = argparse.ArgumentParser(
        prog="subtitle-inserter-cli",
        description="動画ファイルに字幕を焼き込むバッチツール (GUI を介さずに実行)",
    )
    parser.add_argument("video", type=Path, help="入力動画ファイル (mp4 等)")
    parser.add_argument(
        "-s",
        "--subtitle",
        type=Path,
        required=True,
        help="字幕ファイル (srt / ass / csv)。csv は GUI 同様に自動マッピング等は行われません。",
    )
    parser.add_argument("-o", "--output", type=Path, help="出力ファイルパス。省略時は *_sub.mp4 になります")
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="字幕フィルタ無しの場合でも再エンコードする (-c:v copy を使用しない)",
    )
    parser.add_argument("--crf", type=int, help="エンコード CRF 値 (デフォルト Settings の値)")
    parser.add_argument("--preset", help="x264 preset 値 (デフォルト veryfast)")
    parser.add_argument("--font-size", type=int, help="字幕フォントサイズ(px) を一時的に上書き")
    parser.add_argument("--font-family", help="字幕フォント名を上書き (例: 'Yu Gothic UI')")
    parser.add_argument("--font-color", help="字幕文字色 HEX (例: #ffcc00)")
    parser.add_argument("--outline-color", help="縁取り色 HEX (例: #000000)")
    parser.add_argument("--outline-width", type=int, help="縁取り幅 px (0 で無効)")
    parser.add_argument("--bold", action="store_true", help="太字を有効にする")
    shadow_grp = parser.add_mutually_exclusive_group()
    shadow_grp.add_argument("--shadow", dest="shadow", action="store_true", help="影を有効にする (デフォルト)")
    shadow_grp.add_argument("--no-shadow", dest="shadow", action="store_false", help="影を無効にする")
    parser.set_defaults(shadow=None)

    parser.add_argument(
        "--start-offset",
        type=float,
        default=0.0,
        help="字幕開始オフセット秒 (0 以上)。指定すると字幕全体を遅延させます。",
    )

    args = parser.parse_args(argv)

    if args.start_offset < 0:
        parser.error("--start-offset は 0 以上を指定してください")

    # ロガー初期化
    log_dir = Path.cwd() / "logs"
    setup_logger(log_dir)

    # 一時設定上書き
    font_override_fields = [
        "font_size",
        "font_family",
        "font_color",
        "outline_color",
        "outline_width",
        "bold",
        "shadow",
    ]

    if any(getattr(args, f.replace("-", "_")) is not None for f in font_override_fields):
        sm = SettingsManager()
        font_cfg = sm.get("font", {}).copy()

        if args.font_size is not None:
            font_cfg["size"] = args.font_size
        if args.font_family is not None:
            font_cfg["family"] = args.font_family
        if args.font_color is not None:
            font_cfg["color"] = args.font_color
        if args.outline_color is not None:
            font_cfg["outline_color"] = args.outline_color
        if args.outline_width is not None:
            font_cfg["outline_width"] = args.outline_width
        if args.bold:
            font_cfg["bold"] = True
        if args.shadow is not None:
            font_cfg["shadow"] = args.shadow

        sm.set("font", font_cfg)

    # Offset processing if needed
    sub_path: Path | None = args.subtitle
    if args.start_offset > 0:
        ext = sub_path.suffix.lower()
        if ext == ".srt":
            lines = SRTParser().parse(sub_path)
        elif ext == ".ass":
            lines = ASSParser().parse(sub_path)
        elif ext == ".csv":
            # CSV は列マッピング無し、start=0,text=2,end=1 の想定
            lines = CSVParser().parse(sub_path, start_col=0, text_col=2, end_col=1)
        else:
            parser.error(f"未対応の字幕形式です: {sub_path}")

        for ln in lines:
            ln.start += args.start_offset
            ln.end += args.start_offset

        sub_path = _write_temp_ass(lines)

    rc = run_once(
        video_path=args.video,
        subtitles_path=sub_path,
        output_path=args.output,
        codec_copy=not args.no_copy,
        crf=args.crf,
        preset=args.preset,
    )
    sys.exit(rc)


if __name__ == "__main__":  # pragma: no cover
    main()


# ----------------------------------------------------------------------
def _write_temp_ass(lines: List[SubtitleLine]) -> Path:
    """Generate temporary ASS file from SubtitleLine list and return path."""
    settings = SettingsManager()
    font_cfg = settings.get("font", {})
    fontname = font_cfg.get("family", "Arial")
    fontsize = font_cfg.get("size", 32)
    primary = font_cfg.get("color", "#ffffff")
    outline_color = font_cfg.get("outline_color", "#000000")
    outline_width = font_cfg.get("outline_width", 3)
    shadow_enabled = font_cfg.get("shadow", True)
    shadow_val = 3 if shadow_enabled else 0
    bold_flag = -1 if font_cfg.get("bold", False) else 0
    margin_v = font_cfg.get("margin_v", 10)

    def hex_to_ass(c: str):
        c = c.lstrip("#")
        if len(c) == 6:
            r, g, b = c[0:2], c[2:4], c[4:6]
            return f"&H00{b}{g}{r}"
        return "&H00FFFFFF"

    primary_ass = hex_to_ass(primary)
    outline_ass = hex_to_ass(outline_color)

    header = (
        "[Script Info]\nScriptType: v4.00+\nCollisions: Normal\nPlayResX: 1920\nPlayResY: 1080\nTimer: 100.0000\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{fontname},{fontsize},{primary_ass},&H000000FF,{outline_ass},&H64000000,{bold_flag},0,0,0,100,100,0,0,1,{outline_width},{shadow_val},2,10,10,{margin_v},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    dialogues = "\n".join(l.to_ass_dialogue() for l in lines)
    content = header + dialogues
    tmp_file = Path(tempfile.gettempdir()) / "subtitle_offset.ass"
    tmp_file.write_text(content, encoding="utf-8")
    return tmp_file 