#!/bin/zsh
set -e

echo "L/R Swaper Mac required audio setup"
echo "===================================="
echo

echo "This installs/checks BlackHole 2ch and switchaudio-osx."
echo

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install Homebrew from https://brew.sh and run this again."
  read "?Press Enter to close..."
  exit 1
fi

echo "Installing/checking BlackHole 2ch..."
HOMEBREW_NO_AUTO_UPDATE=1 brew install --cask blackhole-2ch || true

echo
echo "Installing/checking SwitchAudioSource..."
HOMEBREW_NO_AUTO_UPDATE=1 brew install switchaudio-osx || true

echo
echo "Checking installed audio outputs:"
if command -v SwitchAudioSource >/dev/null 2>&1; then
  SwitchAudioSource -a -t output | grep -i blackhole || true
fi

echo
echo "Done. If BlackHole was installed for the first time, reboot your Mac."
read "?Press Enter to close..."
