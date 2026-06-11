#!/usr/bin/env bash
set -euo pipefail

REPO="${LR_SWAPER_REPO:-Tihulu/L-R-Swaper-and-EQ}"
BRANCH="${LR_SWAPER_BRANCH:-main}"
ARCHIVE_URL="https://codeload.github.com/${REPO}/tar.gz/refs/heads/${BRANCH}"
PACKAGES=(
  python3
  python3-tk
  pulseaudio-utils
  alsa-utils
  swh-plugins
  curl
  ca-certificates
  tar
)

log() {
  printf '\n==> %s\n' "$*"
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

if ! command -v apt-get >/dev/null 2>&1; then
  fail "This quick installer currently supports apt-based Linux systems such as Pop!_OS, Ubuntu, Linux Mint, and Debian."
fi

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    fail "sudo is required when running as a normal user. Install sudo or run this script as root."
  fi
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

log "Installing required system packages"
$SUDO apt-get update
$SUDO apt-get install -y "${PACKAGES[@]}"

log "Downloading L/R Swaper from GitHub"
curl -fsSL "$ARCHIVE_URL" -o "$TMP_DIR/lr-swaper.tar.gz"
tar -xzf "$TMP_DIR/lr-swaper.tar.gz" -C "$TMP_DIR"

SRC_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -n "$SRC_DIR" ] || fail "Could not unpack repository archive."
[ -d "$SRC_DIR/linux" ] || fail "Repository archive does not contain the linux/ installer folder."

log "Installing L/R Swaper"
cd "$SRC_DIR/linux"
chmod +x install.sh
./install.sh

log "Verifying install"
if command -v lr-swaper >/dev/null 2>&1; then
  printf 'Installed successfully. Run: lr-swaper\n'
elif [ -x "$HOME/.local/bin/lr-swaper" ]; then
  printf 'Installed successfully at: %s\n' "$HOME/.local/bin/lr-swaper"
  printf 'If the command is not found, add this to your shell profile and reopen the terminal:\n'
  printf '  export PATH="$HOME/.local/bin:$PATH"\n'
else
  fail "Install script finished, but lr-swaper was not found in ~/.local/bin."
fi

printf '\nOpen L/R Swaper from the app menu, or run:\n  lr-swaper\n'
