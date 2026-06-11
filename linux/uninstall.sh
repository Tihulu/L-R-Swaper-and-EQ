#!/usr/bin/env bash
set -euo pipefail

lr-swaper --disable >/dev/null 2>&1 || bt-lr-swapper --disable >/dev/null 2>&1 || true

rm -rf "$HOME/.local/share/lr-swaper"
rm -f "$HOME/.local/bin/lr-swaper"
rm -f "$HOME/.local/bin/bt-lr-swapper"
rm -f "$HOME/.local/share/applications/lr-swaper.desktop"
rm -f "$HOME/.local/share/applications/bt-lr-swapper.desktop"

for size in 16 24 32 48 64 128 256 512; do
  rm -f "$HOME/.local/share/icons/hicolor/${size}x${size}/apps/lr-swaper.png"
done

gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true

echo "Uninstalled L/R Swaper."
