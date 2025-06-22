# Subtitle Inserter

FFmpeg をバックエンドに用いて動画へハードサブ字幕を焼き込む PySide6 製デスクトップアプリです。

## セットアップ
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# 起動 (いずれか)
1. ダブルクリック `run_gui.bat` （推奨 / グローバル環境用）
2. 直接 Python で実行
   ```bash
   python subtitle_inserter/run_app.py
   ```

`run_app.py` は内部で `subtitle_inserter/src` を `sys.path` に追加するため、
どこから実行しても動作します。

### アイコンについて
ルートに `icon.png` を置くと初回起動時に **Pillow** を使って `icon.ico` が自動生成され、
タスクバーやタイトルバーに専用アイコンが表示されます。
（`requirements.txt` に Pillow を追加済み）

## バッチモード (CLI)

GUI を使わず、コマンドラインで 1 本ずつ処理したい場合は `subtitle_inserter.cli` を利用します。

```powershell
# 例: 基本的な使い方
set PYTHONPATH=%CD%\subtitle_inserter\src  # 初回のみ
python -m subtitle_inserter.cli <動画パス> -s <字幕ファイル>

# 例: 書式を細かく指定
python -m subtitle_inserter.cli input.mp4 -s input.srt ^
  --font-family "Yu Gothic UI" ^
  --font-size 20 ^
  --font-color #ffcc00 ^
  --outline-color #0000ff ^
  --outline-width 3 ^
  --bold ^
  --no-shadow
```

| オプション | 説明 |
| --- | --- |
| `-s, --subtitle` | 字幕ファイル (srt / ass / csv) **必須** |
| `-o, --output` | 出力ファイルパス (省略時は `<動画名>_sub.<拡張子>`)|
| `--no-copy` | 字幕フィルタ無しでも再エンコードする (-c:v copy を使用しない) |
| `--crf` | CRF 値を上書き |
| `--preset` | x264 preset を上書き |
| `--font-family` | フォント名を一時的に上書き |
| `--font-size` | フォントサイズ(px)を上書き |
| `--font-color` | 文字色 HEX (#RRGGBB) |
| `--outline-color` | 縁取り色 HEX (#RRGGBB) |
| `--outline-width` | 縁取り幅 px (0 で無効) |
| `--bold` | 太字を有効にする |
| `--shadow` / `--no-shadow` | 影の有無 |

これらのオプションによるフォント設定の変更は**その 1 回の実行のみに適用**され、GUI/CLI の次回起動時には元の設定に戻ります。 