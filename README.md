# L/R Swaper and EQ

Cross-platform left/right channel swapper and simple EQ project.

This repository is split by operating system so each platform can keep its own install steps, dependencies, and build scripts.

## Platforms

| Platform | Folder | Status |
| --- | --- | --- |
| Pop!_OS / Ubuntu Linux | [`linux/`](linux/) | Working GUI + CLI app using PipeWire/PulseAudio tools |
| macOS Apple Silicon | [`macos/`](macos/) | macOS app, build scripts, and BlackHole-based audio routing notes |

## What the app does

L/R Swaper helps with stereo output routing and quick tone adjustment:

- swap left and right channels
- test left/right audio channels
- adjust bass and treble
- adjust L/R balance
- manage three volume-independent preset slots
- restore/disable virtual audio chains cleanly

## Linux quick install from GitHub

For Pop!_OS / Ubuntu / other apt-based Linux systems:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)
```

The quick installer downloads the latest `main` branch, installs required packages, runs the Linux installer, and verifies that `lr-swaper` is available.

Then open **L/R Swaper** from the app menu, or run:

```bash
lr-swaper
```

More details and manual install steps: [`linux/README.md`](linux/README.md)

## macOS quick start

```bash
cd macos
```

Follow the macOS notes in [`macos/README.md`](macos/README.md). The macOS version uses BlackHole 2ch as the virtual audio driver and requires macOS microphone permission for local audio processing.

## Repository layout

```text
.
├── README.md          # general project overview
├── linux/             # Pop!_OS / Ubuntu version
│   ├── README.md
│   ├── quick-install.sh
│   ├── lr-swaper.py
│   ├── install.sh
│   ├── uninstall.sh
│   ├── build.sh
│   └── icons/
└── macos/             # macOS version and build docs
```

## Notes

The Linux version and macOS version use different audio backends, so setup and troubleshooting are intentionally separated by folder.
