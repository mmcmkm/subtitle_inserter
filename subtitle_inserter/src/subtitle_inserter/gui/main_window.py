from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QWidget,
    QVBoxLayout,
    QLabel,
    QToolBar,
    QProgressBar,
    QTabWidget,
)
try:
    # PySide6 6.6 以降
    from PySide6.QtGui import QAction
except ImportError:  # pragma: no cover
    # 古いバージョン互換
    from PySide6.QtWidgets import QAction  # type: ignore

from ..core.logger import get_logger
from .drop_area import DropArea
from .preview_widget import PreviewWidget
from ..core.ffmpeg_builder import FFmpegCommandBuilder
from ..core.job_runner import JobRunner
from ..core.parsers import CSVParser
from ..core.subtitle_model import SubtitleLine
from .output_settings_widget import OutputSettingsWidget
from ..core.settings import SettingsManager
from .subtitle_style_widget import SubtitleStyleWidget

import tempfile

logger = get_logger(__name__)

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}
SUB_EXTS = {".srt", ".ass", ".csv"}


class MainWindow(QMainWindow):
    """メインウィンドウ。左にドロップエリア＋キュー、右にプレースホルダ設定パネル。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Subtitle Inserter")
        self.resize(900, 600)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ---------------- 左ペイン ----------------
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)

        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self.add_files)
        self.queue_list = QListWidget()
        self.queue_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        left_layout.addWidget(self.drop_area, stretch=1)
        left_layout.addWidget(QLabel("キュー一覧:"))
        left_layout.addWidget(self.queue_list, stretch=2)

        left_container.setLayout(left_layout)

        # ---------------- 右ペイン ----------------
        tabs = QTabWidget()
        self.preview_widget = PreviewWidget()
        tabs.addTab(self.preview_widget, "プレビュー")
        tabs.addTab(OutputSettingsWidget(), "出力設定")
        style_widget = SubtitleStyleWidget()
        style_widget.styleChanged.connect(self.preview_widget.apply_style)
        tabs.addTab(style_widget, "字幕スタイル")

        splitter.addWidget(left_container)
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

        # ---------------- Toolbar ----------------
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        self.action_start = QAction("開始", self)
        self.action_start.triggered.connect(self.start_processing)
        toolbar.addAction(self.action_start)

        self.action_cancel = QAction("停止", self)
        self.action_cancel.setEnabled(False)
        self.action_cancel.triggered.connect(self.cancel_current_job)
        toolbar.addAction(self.action_cancel)

        # ---------------- Status bar ----------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.statusBar().addPermanentWidget(self.progress_bar)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def add_files(self, paths: List[str]) -> None:
        """Add dropped files to queue."""
        for p in paths:
            ext = Path(p).suffix.lower()
            if ext in VIDEO_EXTS | SUB_EXTS:
                item = QListWidgetItem(p)
                self.queue_list.addItem(item)
                logger.debug("キューに追加: %s", p)
            else:
                logger.warning("非対応拡張子のため無視: %s", p)

    def start_processing(self):  # noqa: D401,N802
        """Queue にあるすべての動画を順番に処理開始。"""
        if self.queue_list.count() == 0:
            logger.warning("キューが空です")
            return

        # キュー作成
        paths = [self.queue_list.item(i).text() for i in range(self.queue_list.count())]
        videos = [p for p in paths if Path(p).suffix.lower() in VIDEO_EXTS]
        subs = [p for p in paths if Path(p).suffix.lower() in SUB_EXTS]

        if not videos:
            logger.warning("動画ファイルが見つかりません")
            return

        self.job_queue: List[tuple[Path, Path | None]] = []
        for v in videos:
            v_path = Path(v)
            match = None
            for s in subs:
                if Path(s).stem == v_path.stem:
                    match = Path(s)
                    break
            if match is None and subs:
                match = Path(subs[0])
            self.job_queue.append((v_path, match))

        self.current_job_index = -1
        self._start_next_job()

    def _start_next_job(self):  # noqa: N802
        """内部使用: 次のジョブを開始。"""
        self.current_job_index += 1
        if self.current_job_index >= len(getattr(self, "job_queue", [])):
            logger.info("すべてのジョブが完了しました")
            return

        video_path, sub_path = self.job_queue[self.current_job_index]

        # CSV を ASS に変換
        if sub_path and sub_path.suffix.lower() == ".csv":
            try:
                parser = CSVParser()
                settings = SettingsManager()
                csv_maps = settings.get("csv_mappings", {})
                mapping = csv_maps.get(str(sub_path))

                if mapping:
                    lines = parser.parse(
                        sub_path,
                        start_col=mapping["start_col"],
                        text_col=mapping["text_col"],
                        end_col=mapping.get("end_col"),
                        time_format=mapping.get("time_unit", "seconds"),
                        fps=float(mapping.get("fps", 30)),
                    )
                else:
                    # 簡易推測
                    header_line = open(sub_path, encoding="utf-8", errors="ignore").readline()

                    def _guess(col_name: str, default_idx: int):
                        return col_name if col_name in header_line else default_idx

                    lines = parser.parse(
                        sub_path,
                        start_col=_guess("start_time", 0),
                        text_col=_guess("text", 2),
                        end_col=_guess("end_time", 1),
                        time_format="seconds",
                    )
                sub_path = self._write_temp_ass(lines)
            except Exception as e:  # noqa: BLE001
                logger.exception("CSV 解析に失敗: %s", e)
                self._on_error(str(e))
                return

        settings = SettingsManager()
        custom_dir = settings.get("output_dir", "")
        if custom_dir:
            output_dir = Path(custom_dir)
        else:
            output_dir = video_path.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / (video_path.stem + "_sub" + video_path.suffix)

        # プレビュー用字幕テキストを抽出
        preview_texts: List[str] = []
        try:
            if sub_path:
                if sub_path.suffix.lower() == ".csv":
                    # CSV の場合は前段で作成した lines を再利用
                    if "lines" in locals():
                        preview_texts = [l.text for l in lines][:50]
                elif sub_path.suffix.lower() == ".srt":
                    from ..core.parsers import SRTParser

                    preview_texts = [l.text for l in SRTParser().parse(sub_path)][:50]
                elif sub_path.suffix.lower() == ".ass":
                    from ..core.parsers import ASSParser

                    preview_texts = [l.text for l in ASSParser().parse(sub_path)][:50]
        except Exception as e:  # noqa: BLE001
            logger.warning("プレビュー用字幕抽出に失敗: %s", e)

        self.preview_widget.display_lines(preview_texts)

        builder = FFmpegCommandBuilder(
            video_path=video_path,
            subtitles_path=sub_path,
            output_path=output_path,
            codec_copy=True,
            crf=int(settings.get("crf", 23)),
            preset=settings.get("preset", "veryfast"),
        )
        cmd = builder.build()

        self.job = JobRunner(cmd)
        self.job.progressChanged.connect(self._on_progress)
        self.job.finished.connect(self._on_finished)
        self.job.errorOccurred.connect(self._on_error)
        self.action_cancel.setEnabled(True)
        self.job.start()

    def _on_progress(self, value: float) -> None:
        self.progress_bar.setValue(int(value * 100))

    def _on_finished(self, rc: int) -> None:  # noqa: D401
        if rc == 0:
            logger.info("処理が完了しました")
        else:
            logger.error("FFmpeg がエラーコード %s で終了", rc)

        # プレビューをクリア
        self.preview_widget.clear()

        self.progress_bar.setValue(0)
        self.action_cancel.setEnabled(False)

        # 次のジョブへ
        self._start_next_job()

    def _on_error(self, msg: str) -> None:
        logger.error("JobRunner error: %s", msg)

    # ------------------------------------------------------------------
    def _write_temp_ass(self, lines: List[SubtitleLine]) -> Path:
        """Write ASS file to temp dir and return its path."""
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
        # ASS 色は &HAABBGGRR 形式（BBGGRR）。ここでは不透明扱い AA=00
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
            f"Style: Default,{fontname},{fontsize},{primary_ass},&H000000FF,{outline_ass},&H64000000,{bold_flag},0,0,0,100,100,0,0,1,{outline_width},{shadow_val},2,10,10,10,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        dialogues = "\n".join(l.to_ass_dialogue() for l in lines)
        content = header + dialogues
        tmp_dir = Path(tempfile.gettempdir())
        tmp_file = tmp_dir / "subtitle_from_csv.ass"
        tmp_file.write_text(content, encoding="utf-8")
        logger.debug("CSV から生成した ASS: %s", tmp_file)
        return tmp_file

    # ------------------------------------------------------------------
    def _on_item_double_clicked(self, item):  # noqa: D401,N802
        path = Path(item.text())
        ext = path.suffix.lower()

        if ext == ".csv":
            # 列マッピングダイアログ
            from .csv_mapping_dialog import CsvMappingDialog  # local import to avoid circular

            dlg = CsvMappingDialog(path, self)
            if dlg.exec() == dlg.Accepted:
                mapping = dlg.get_mapping()
                settings = SettingsManager()
                csv_maps = settings.get("csv_mappings", {})
                csv_maps[str(path)] = mapping
                settings.set("csv_mappings", csv_maps)
                settings.save()
                logger.info("CSV マッピングを保存しました: %s", mapping)
        elif ext in VIDEO_EXTS:
            # 動画ファイルをプレビュー: 同名字幕ファイルを探す
            subtitle_path: Path | None = None
            queue_paths = [Path(self.queue_list.item(i).text()) for i in range(self.queue_list.count())]
            for p in queue_paths:
                if p.stem == path.stem and p.suffix.lower() in SUB_EXTS:
                    subtitle_path = p
                    break

            if subtitle_path is None:
                # 同ディレクトリも検索
                for ext2 in SUB_EXTS:
                    cand = path.with_suffix(ext2)
                    if cand.exists():
                        subtitle_path = cand
                        break

            if subtitle_path is None:
                logger.warning("対応する字幕ファイルが見つかりません: %s", path)
                self.preview_widget.clear()
                return

            try:
                preview_texts: List[str] = []
                if subtitle_path.suffix.lower() == ".srt":
                    from ..core.parsers import SRTParser

                    preview_texts = [l.text for l in SRTParser().parse(subtitle_path)][:50]
                elif subtitle_path.suffix.lower() == ".ass":
                    from ..core.parsers import ASSParser

                    preview_texts = [l.text for l in ASSParser().parse(subtitle_path)][:50]
                elif subtitle_path.suffix.lower() == ".csv":
                    from ..core.parsers import CSVParser

                    parser = CSVParser()
                    settings = SettingsManager()
                    mapping = settings.get("csv_mappings", {}).get(str(subtitle_path))
                    if mapping:
                        lines = parser.parse(
                            subtitle_path,
                            start_col=mapping["start_col"],
                            text_col=mapping["text_col"],
                            end_col=mapping.get("end_col"),
                            time_format=mapping.get("time_unit", "seconds"),
                            fps=float(mapping.get("fps", 30)),
                        )
                    else:
                        lines = parser.parse(subtitle_path, start_col=0, text_col=2, end_col=1)
                    preview_texts = [l.text for l in lines][:50]

                self.preview_widget.display_lines(preview_texts)
            except Exception as e:  # noqa: BLE001
                logger.warning("プレビュー抽出に失敗: %s", e)
                self.preview_widget.clear()

    def cancel_current_job(self):  # noqa: N802
        if hasattr(self, "job") and self.job:
            logger.info("キャンセル要求を送信")
            self.job.stop()
            self.preview_widget.clear()
            self.progress_bar.setValue(0)
            self.action_cancel.setEnabled(False) 