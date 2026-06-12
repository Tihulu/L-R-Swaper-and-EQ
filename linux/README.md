# L/R Swaper Linux v4.9

Modern Linux version of **L/R Swaper and EQ** for Pop!_OS, Ubuntu, Linux Mint, Debian, and other apt-based systems using PipeWire/PulseAudio compatibility.

Repository: <https://github.com/Tihulu/L-R-Swaper-and-EQ>

## Quick install from GitHub

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)
```

The quick installer downloads the latest `main` branch from GitHub, installs required system packages, runs the Linux installer, and verifies the command.

After install, open **L/R Swaper** from the app menu or run:

```bash
lr-swaper
```

## What is included

- **Tihuluwave Theme**: PySide6/Qt modern UI, default on first launch
- **Plain Theme**: original v2.8-style Tkinter UI
- L/R swap and alternate swap mode
- stereo left/right test buttons
- bass and treble EQ using LADSPA `mbeq_1197`
- L/R balance
- volume control
- three volume-independent preset slots
- clean disable/restore behavior
- dock launcher and icon install for COSMIC/GNOME-like desktops

## Requirements

The quick installer handles these automatically on apt-based systems:

```bash
sudo apt install python3 python3-venv python3-tk pulseaudio-utils alsa-utils swh-plugins curl ca-certificates tar
```

What they provide:

- `python3`, `python3-venv`: app runtime and private PySide6 environment
- `python3-tk`: Plain Theme UI
- `pulseaudio-utils`: `pactl` and `paplay`
- `alsa-utils`: audio utilities
- `swh-plugins`: LADSPA bass/treble EQ plugin
- `curl`, `ca-certificates`, `tar`: GitHub quick install download/extract

The installer creates a private app venv at:

```text
~/.local/share/lr-swaper/.venv
```

and installs PySide6 there, so the Qt UI does not depend on the system Python packages.

## Manual install from cloned repository

```bash
git clone https://github.com/Tihulu/L-R-Swaper-and-EQ.git
cd L-R-Swaper-and-EQ/linux
chmod +x install.sh
./install.sh
lr-swaper
```

If `check-install.sh` exists in your checkout, run it after install:

```bash
chmod +x check-install.sh
./check-install.sh
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

## Dock note

If an old pinned dock icon opens an older version, remove the old pin, open **L/R Swaper** from the app menu or terminal, and pin the newly running app.

The current desktop launcher ID is:

```text
com.tihulu.lr-swaper.desktop
```

## CLI examples

```bash
lr-swaper --swap-default
lr-swaper --swap-default-alt
lr-swaper --fix-now
lr-swaper --test-left
lr-swaper --test-right
lr-swaper --test-lr
lr-swaper --bass-db 4 --treble-db 2
lr-swaper --tone-off
lr-swaper --balance 50
lr-swaper --balance-center
lr-swaper --volume 80
lr-swaper --save-slot 1
lr-swaper --load-slot 1
lr-swaper --neutral
lr-swaper --disable
lr-swaper --status
```

## Presets

Presets are stored in:

```text
~/.config/lr-swaper/saved_settings.json
~/.config/lr-swaper/saved_settings_2.json
~/.config/lr-swaper/saved_settings_3.json
```

Presets save target output, swap mode, bass, treble, and L/R balance. Presets do **not** save volume.

## Troubleshooting

### `pactl` is missing

```bash
sudo apt install pulseaudio-utils
```

### Plain Theme cannot open

```bash
sudo apt install python3-tk
```

### Bass/Treble does not work

```bash
sudo apt install swh-plugins
```

### `lr-swaper` is not found

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add that line to your shell profile if needed.

## Uninstall

```bash
cd L-R-Swaper-and-EQ/linux
chmod +x uninstall.sh
./uninstall.sh
```
