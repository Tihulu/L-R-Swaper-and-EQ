#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/lr-swaper"
VENV="$APP_DIR/.venv"

echo "== L/R Swaper install check =="
echo
echo "Binary:"
ls -l "$HOME/.local/bin/lr-swaper" 2>/dev/null || echo "missing ~/.local/bin/lr-swaper"
echo
echo "Launcher content:"
cat "$HOME/.local/bin/lr-swaper" 2>/dev/null || true
echo
echo "App dir:"
ls -la "$APP_DIR" 2>/dev/null || echo "missing $APP_DIR"
echo
echo "Venv Python:"
ls -l "$VENV/bin/python" 2>/dev/null || echo "missing venv python"
echo
echo "PySide6 in venv:"
"$VENV/bin/python" -c "import PySide6; print(PySide6.__version__)" 2>/dev/null || echo "PySide6 missing in venv"
echo
echo "Desktop files matching lr-swaper:"
ls -la "$HOME/.local/share/applications/"*lr-swaper*.desktop 2>/dev/null || echo "no matching desktop files"
echo
echo "New desktop file content:"
cat "$HOME/.local/share/applications/com.tihulu.lr-swaper.desktop" 2>/dev/null || echo "missing com.tihulu.lr-swaper.desktop"
echo
echo "Icon files:"
for p in \
  "$APP_DIR/icons/lr-swaper-256.png" \
  "$HOME/.local/share/pixmaps/lr-swaper.png" \
  "$HOME/.local/share/icons/hicolor/256x256/apps/lr-swaper.png"; do
  if [ -f "$p" ]; then
    ls -l "$p"
  else
    echo "missing $p"
  fi
done
echo
echo "Theme:"
cat "$HOME/.config/lr-swaper/theme.json" 2>/dev/null || echo "no theme.json yet"
echo
echo "Version markers:"
grep -R "v5.1\|v5.1\|v5.1\|Tihuluwave" "$APP_DIR"/*.py 2>/dev/null | head -80 || true
