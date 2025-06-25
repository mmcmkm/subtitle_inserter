from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


class SettingsManager:
    """Singleton class to manage persistent application settings.

    設定ファイルは Windows の場合 `%APPDATA%/SubtitleInserter/config.json` に保存されます。
    初回起動時にデフォルト設定でファイルが生成され、以降アプリ終了時に自動保存します。
    """

    _instance: "SettingsManager | None" = None

    DEFAULTS: Dict[str, Any] = {
        "output_dir": "output",  # デフォルト出力フォルダ（動画と同じ階層に生成）
        "last_preset_file": "",
        "font": {
            "family": "Arial",
            "size": 32,
            "color": "#ffffff",
            "outline_color": "#000000",
            "outline_width": 2,
            "bold": False,
            "shadow": True,
            "margin_v": 10,
        },
        "position": {"x": 0.5, "y": 0.9},  # 正規化座標
        "fps": 30,
        "start_offset": 0.0,
        "csv_mappings": {},  # filename -> mapping dict
        "output_dir": "",  # custom output dir, empty means default
        "crf": 23,
        "preset": "veryfast",
    }

    def __new__(cls) -> "SettingsManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def get(self, key: str, default: Any | None = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value

    def save(self) -> None:
        """書き込みを強制実行します。"""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with self._config_path.open("w", encoding="utf-8") as f:
            json.dump(self._settings, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _initialize(self) -> None:
        """Load or create configuration file."""
        self._config_path = self._default_config_path()
        self._settings: Dict[str, Any]
        if self._config_path.exists():
            try:
                with self._config_path.open(encoding="utf-8") as f:
                    self._settings = json.load(f)
            except Exception:
                # 破損時はバックアップしてデフォルトを再生成
                corrupted = self._config_path.with_suffix(".bak")
                self._config_path.rename(corrupted)
                self._settings = self.DEFAULTS.copy()
                self.save()
        else:
            self._settings = self.DEFAULTS.copy()
            self.save()

    @staticmethod
    def _default_config_path() -> Path:
        if os.name == "nt":
            base = Path(os.getenv("APPDATA", Path.home()))
        else:
            base = Path.home() / ".config"
        return base / "SubtitleInserter" / "config.json" 