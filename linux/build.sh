#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --user pyinstaller PySide6
python3 -m PyInstaller \
  --onefile \
  --windowed \
  --name lr-swaper \
  --add-data "icons/lr-swaper-256.png:icons" \
  --add-data "lr_swaper_tihuluwave.py:." \
  --add-data "lr_swaper_plain.py:." \
  --add-data "lr_swaper_tihuluwave_qt.py:." \
  lr-swaper.py

echo "Standalone binary created at: dist/lr-swaper"
