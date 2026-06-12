#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/lr-swaper"
VENV="$APP_DIR/.venv"

printf '== L/R Swaper install check ==\n\n'

printf 'Binary:\n'
ls -l "$HOME/.local/bin/lr-swaper" 2>/dev/null || echo "missing ~/.local/bin/lr-swaper"
printf '\n'

printf 'App dir:\n'
ls -la "$APP_DIR" 2>/dev/null || echo "missing $APP_DIR"
printf '\n'

printf 'Venv Python:\n'
ls -l "$VENV/bin/python" 2>/dev/null || echo "missing venv python"
printf '\n'

printf 'PySide6 in venv:\n'
"$VENV/bin/python" -c "import PySide6; print(PySide6.__version__)" 2>/dev/null || echo "PySide6 missing in venv"
printf '\n'

printf 'Desktop files matching lr-swaper:\n'
ls -la "$HOME/.local/share/applications/"*lr-swaper*.desktop 2>/dev/null || echo "no matching desktop files"
printf '\n'

printf 'New desktop file content:\n'
cat "$HOME/.local/share/applications/com.tihulu.lr-swaper.desktop" 2>/dev/null || echo "missing com.tihulu.lr-swaper.desktop"
printf '\n'

printf 'Icon files:\n'
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
printf '\n'

printf 'Theme:\n'
cat "$HOME/.config/lr-swaper/theme.json" 2>/dev/null || echo "no theme.json yet"
printf '\n'

printf 'Version markers:\n'
grep -R "v4.9\|v4.8\|v4.7\|Tihuluwave" "$APP_DIR"/*.py 2>/dev/null | head -80 || true
