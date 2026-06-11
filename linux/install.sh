#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/lr-swaper"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_BASE="$HOME/.local/share/icons/hicolor"

mkdir -p "$APP_DIR/icons" "$BIN_DIR" "$DESKTOP_DIR"

cp lr-swaper.py "$APP_DIR/lr-swaper.py"
chmod +x "$APP_DIR/lr-swaper.py"
cp icons/*.png "$APP_DIR/icons/"

for size in 16 24 32 48 64 128 256 512; do
  mkdir -p "$ICON_BASE/${size}x${size}/apps"
  cp "icons/lr-swaper-${size}.png" "$ICON_BASE/${size}x${size}/apps/lr-swaper.png"
done

cat > "$BIN_DIR/lr-swaper" <<'EOF'
#!/usr/bin/env bash
exec python3 "$HOME/.local/share/lr-swaper/lr-swaper.py" "$@"
EOF
chmod +x "$BIN_DIR/lr-swaper"

# Backward-compatible command name from the older builds.
cat > "$BIN_DIR/bt-lr-swapper" <<'EOF'
#!/usr/bin/env bash
exec python3 "$HOME/.local/share/lr-swaper/lr-swaper.py" "$@"
EOF
chmod +x "$BIN_DIR/bt-lr-swapper"

# Remove old launcher to avoid duplicate dock entries.
rm -f "$DESKTOP_DIR/bt-lr-swapper.desktop"

cat > "$DESKTOP_DIR/lr-swaper.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=L/R Swaper
Comment=Swap left and right audio channels, test stereo, and apply tone boosts
Exec=$BIN_DIR/lr-swaper
Icon=lr-swaper
Terminal=false
Categories=Audio;Utility;
StartupWMClass=lr-swaper
StartupNotify=true
EOF

gtk-update-icon-cache "$ICON_BASE" >/dev/null 2>&1 || true
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

echo "Installed L/R Swaper v2.8."
echo
echo "Recommended packages:"
echo "  sudo apt install python3-tk pulseaudio-utils alsa-utils swh-plugins"
echo
echo "Run: lr-swaper"
echo "Old command still works: bt-lr-swapper"
echo
echo "For the dock icon: close the old app, remove the old pinned item, open L/R Swaper from the app menu, then pin it again."
