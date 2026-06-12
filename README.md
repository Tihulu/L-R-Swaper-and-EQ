# L/R Swaper and EQ

Cross-platform left/right channel swapper and simple EQ project.

Repository: <https://github.com/Tihulu/L-R-Swaper-and-EQ>

## Platforms

| Platform | Folder | Status |
| --- | --- | --- |
| Pop!_OS / Ubuntu Linux | [`linux/`](linux/) | Linux v4.9 GUI + CLI app with PySide6 Tihuluwave Theme and v2.8 Plain Theme |
| macOS Apple Silicon | [`macos/`](macos/) | macOS app, build scripts, and BlackHole-based routing notes |

## Linux quick install from GitHub

For Pop!_OS, Ubuntu, Linux Mint, Debian, and other apt-based Linux systems:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)
```

Then open **L/R Swaper** from the app menu, or run:

```bash
lr-swaper
```

Details: [`linux/README.md`](linux/README.md)

## What the app does

- swap left and right channels
- test left/right audio channels
- adjust bass and treble
- adjust L/R balance
- manage three volume-independent preset slots
- restore/disable virtual audio chains cleanly

## Linux v4.9 notes

- **Tihuluwave Theme** is the default first-launch theme.
- **Plain Theme** keeps the original v2.8-style interface.
- The Qt UI uses a private app venv under `~/.local/share/lr-swaper/.venv`.
- The Linux dock launcher uses `com.tihulu.lr-swaper.desktop`.

## Repository layout

```text
.
├── README.md
├── linux/
│   ├── README.md
│   ├── quick-install.sh
│   ├── install.sh
│   ├── check-install.sh
│   ├── uninstall.sh
│   ├── build.sh
│   ├── lr-swaper.py
│   ├── lr_swaper_tihuluwave.py
│   ├── lr_swaper_tihuluwave_qt.py
│   ├── lr_swaper_plain.py
│   └── icons/
└── macos/
```

## macOS quick start

```bash
cd macos
```

Follow the macOS notes in [`macos/README.md`](macos/README.md). The macOS version uses BlackHole 2ch as the virtual audio driver and requires macOS microphone permission for local audio processing.

## Notes

The Linux and macOS versions use different audio backends, so setup and troubleshooting are intentionally separated by folder.
