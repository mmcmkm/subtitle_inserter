@echo off
chcp 65001

REM --------------------------------------------------
REM Subtitle Inserter GUI 起動バッチ (グローバル Python)
REM --------------------------------------------------

cd /d %~dp0

python subtitle_inserter\run_app.py 