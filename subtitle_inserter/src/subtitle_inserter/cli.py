from __future__ import annotations

"""Command-line interface for batch processing (non-GUI)."""

import argparse
import subprocess
import sys
from pathlib import Path

from .core.ffmpeg_builder import FFmpegCommandBuilder
from .core.logger import setup_logger, get_logger
from .core.settings import SettingsManager  # noqa: F401  # ensure settings initialized


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

    args = parser.parse_args(argv)

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

    rc = run_once(
        video_path=args.video,
        subtitles_path=args.subtitle,
        output_path=args.output,
        codec_copy=not args.no_copy,
        crf=args.crf,
        preset=args.preset,
    )
    sys.exit(rc)


if __name__ == "__main__":  # pragma: no cover
    main() 