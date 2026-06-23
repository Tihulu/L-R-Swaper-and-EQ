#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --user pyinstaller
python3 -m PyInstaller \
  --onefile \
  --windowed \
  --name lr-swaper \
  --add-data "icons/lr-swaper-256.png:icons" \
  lr-swaper.py

echo "Standalone binary created at: dist/lr-swaper"
