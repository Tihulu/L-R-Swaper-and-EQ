# L/R Swaper Linux v4.8

Modern Linux build of **L/R Swaper and EQ** for Pop!_OS / Ubuntu / apt-based Linux systems.

Repository: <https://github.com/Tihulu/L-R-Swaper-and-EQ>

## Quick install from GitHub

[![Quick Install](https://img.shields.io/badge/Linux-Quick%20Install-1fc8ff?style=for-the-badge&logo=linux&logoColor=white)](#quick-install-from-github)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)
```

After install, open **L/R Swaper** from the app menu or run:

```bash
lr-swaper
```

## Included in v4.8

- Tihuluwave Theme, the modern Qt UI shown in this release
- Plain Theme, original v2.8-style interface
- GitHub repository link inside Help for future updates
- GitHub quick install command
- L/R swap and alternate swap
- Left / Right / Both audio test
- Sound controls for volume, bass, treble, and L/R balance
- Quick actions: set default, fix streams, diagnostics, disable
- Visible scrollbar and protected sliders, so mouse wheel scrolls the page instead of changing slider values
- COSMIC/GNOME-friendly launcher and icon setup

## Manual install

```bash
cd linux
chmod +x install.sh check-install.sh
./install.sh
./check-install.sh
lr-swaper
```

## Installed paths

```text
~/.local/share/lr-swaper/
~/.local/share/lr-swaper/.venv/
~/.local/bin/lr-swaper
~/.local/share/applications/com.tihulu.lr-swaper.desktop
~/.local/share/icons/hicolor/*/apps/lr-swaper.png
~/.local/share/pixmaps/lr-swaper.png
```

## Release

Recommended release tag:

```text
linux-v4.8
```

Recommended release title:

```text
L/R Swaper Linux v4.8
```

## Troubleshooting

If an old pinned dock icon opens an old version, unpin it, open **L/R Swaper** from the app menu or terminal, then pin the new running app.

If `lr-swaper` is not found after install:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

If PySide6 install fails, rerun `install.sh`; it creates a private venv under `~/.local/share/lr-swaper/.venv`.
