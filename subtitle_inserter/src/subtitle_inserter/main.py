"""Main entry point for Subtitle Inserter."""
from __future__ import annotations

import sys
from pathlib import Path
import os
import ctypes

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap

from .core.logger import setup_logger, get_logger
from .core.settings import SettingsManager
from .gui.main_window import MainWindow


def main() -> None:
    # --------------------------------------------------
    # 初期化: ロガー & 設定
    # --------------------------------------------------
    # ------------- プロジェクトルート探索 -------------
    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        if (parent / "requirements.txt").exists() or (parent / "icon.png").exists():
            project_root = parent
            break
    else:
        project_root = file_path.parent  # フォールバック
    log_dir = project_root / "logs"
    setup_logger(log_dir)
    logger = get_logger(__name__)
    logger.info("Subtitle Inserter を起動します")

    SettingsManager()  # 設定ファイルを自動生成・読込

    # Windows タスクバーで独立表示させる (AppUserModelID)
    if os.name == "nt":  # pragma: windows-only
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SubtitleInserter")

    # --------------------------------------------------
    # GUI 起動
    # --------------------------------------------------
    app = QApplication(sys.argv)
    app.setApplicationName("Subtitle Inserter")

    # アイコン設定
    icon_path: Path | None = None
    png_path = project_root / "icon.png"
    ico_path = project_root / "icon.ico"

    if not ico_path.exists() and png_path.exists():
        # PNG → ICO 生成 (Pillow 必須)
        try:
            from PIL import Image

            img = Image.open(png_path)
            # 透過 PNG でも OK
            sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(ico_path, sizes=sizes)
            logger.info("icon.ico を自動生成しました: %s", ico_path)
        except Exception as e:  # noqa: BLE001
            logger.warning("ICO 生成に失敗しました (%s)。Pillow 未インストールの可能性", e)

    for cand in (ico_path, png_path):
        if cand.exists():
            icon_path = cand
            break
    
    if icon_path is not None and icon_path.exists():
        if icon_path.suffix.lower() == ".png":
            pix = QPixmap(str(icon_path))
            icon = QIcon()
            for sz in (16, 24, 32, 48, 64, 128, 256):
                icon.addPixmap(pix.scaled(sz, sz))
        else:
            icon = QIcon(str(icon_path))

        app.setWindowIcon(icon)
        logger.debug("アイコンを設定しました: %s", icon_path)

    window = MainWindow()
    if icon_path and icon_path.exists():
        window.setWindowIcon(icon)
        logger.debug("ウィンドウアイコンを設定しました")
    window.show()

    logger.debug("GUI が起動しました")
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 