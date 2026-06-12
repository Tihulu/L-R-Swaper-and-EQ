#!/usr/bin/env bash
set -euo pipefail

APP_ID="lr-swaper"
DESKTOP_ID="com.tihulu.lr-swaper"
APP_NAME="L/R Swaper"
APP_DIR="$HOME/.local/share/lr-swaper"
VENV_DIR="$APP_DIR/.venv"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_BASE="$HOME/.local/share/icons/hicolor"
PIXMAP_DIR="$HOME/.local/share/pixmaps"
DESKTOP_FILE="$DESKTOP_DIR/${DESKTOP_ID}.desktop"

echo "==> Removing old installed app files and old desktop entries"
rm -rf "$APP_DIR"
rm -f "$BIN_DIR/lr-swaper" "$BIN_DIR/bt-lr-swapper"
rm -f "$DESKTOP_DIR/lr-swaper.desktop"
rm -f "$DESKTOP_DIR/lr-swaper-iconname.desktop"
rm -f "$DESKTOP_DIR/bt-lr-swapper.desktop"
rm -f "$DESKTOP_DIR/com.tihulu.lr-swaper.desktop"
rm -f "$PIXMAP_DIR/lr-swaper.png"

mkdir -p "$APP_DIR/icons" "$BIN_DIR" "$DESKTOP_DIR" "$PIXMAP_DIR"

# First/default launch should open Tihuluwave Theme.
mkdir -p "$HOME/.config/lr-swaper"
cat > "$HOME/.config/lr-swaper/theme.json" <<'EOF'
{
  "theme": "Tihuluwave Theme"
}
EOF


echo "==> Installing app files"
cp lr-swaper.py "$APP_DIR/lr-swaper.py"
cp lr_swaper_tihuluwave.py "$APP_DIR/lr_swaper_tihuluwave.py"
cp lr_swaper_plain.py "$APP_DIR/lr_swaper_plain.py"
cp lr_swaper_tihuluwave_qt.py "$APP_DIR/lr_swaper_tihuluwave_qt.py"
chmod +x "$APP_DIR/lr-swaper.py" "$APP_DIR/lr_swaper_tihuluwave.py" "$APP_DIR/lr_swaper_plain.py" "$APP_DIR/lr_swaper_tihuluwave_qt.py"

cp icons/*.png "$APP_DIR/icons/"
cp icons/lr-swaper-256.png "$PIXMAP_DIR/lr-swaper.png" 2>/dev/null || cp lr-swaper.png "$PIXMAP_DIR/lr-swaper.png" 2>/dev/null || true

echo "==> Installing icons"
for size in 16 24 32 48 64 128 256 512; do
  mkdir -p "$ICON_BASE/${size}x${size}/apps"
  rm -f "$ICON_BASE/${size}x${size}/apps/lr-swaper.png"
  cp "icons/lr-swaper-${size}.png" "$ICON_BASE/${size}x${size}/apps/lr-swaper.png"
  touch "$ICON_BASE/${size}x${size}/apps/lr-swaper.png"
done

echo "==> Creating private Python venv"
python3 -m venv "$VENV_DIR"

echo "==> Installing PySide6 into app venv"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install PySide6

cat > "$BIN_DIR/lr-swaper" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$APP_DIR/lr-swaper.py" "\$@"
EOF
chmod +x "$BIN_DIR/lr-swaper"

cat > "$BIN_DIR/bt-lr-swapper" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$APP_DIR/lr-swaper.py" "\$@"
EOF
chmod +x "$BIN_DIR/bt-lr-swapper"

echo "==> Installing desktop launcher: $DESKTOP_FILE"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=L/R Swaper
Comment=Swap left and right audio channels, test stereo, and apply tone boosts
Exec=$BIN_DIR/lr-swaper
TryExec=$BIN_DIR/lr-swaper
Path=$APP_DIR
Icon=lr-swaper
Terminal=false
Categories=Audio;AudioVideo;Utility;
StartupWMClass=com.tihulu.lr-swaper
StartupNotify=true
NoDisplay=false
EOF
chmod +x "$DESKTOP_FILE" || true
touch "$DESKTOP_FILE"

echo "==> Refreshing desktop/icon caches"
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
command -v xdg-desktop-menu >/dev/null 2>&1 && xdg-desktop-menu forceupdate >/dev/null 2>&1 || true

echo
echo "Installed L/R Swaper v4.9 venv Qt no-fallback."
echo
echo "IMPORTANT:"
echo "  Remove/unpin the OLD dock icon."
echo "  Open L/R Swaper from the app menu or terminal."
echo "  Then pin the NEW running icon."
echo
echo "Run:"
echo "  lr-swaper"
