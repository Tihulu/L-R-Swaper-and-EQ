# L/R Swaper Linux v5.1

Modern Linux build of **L/R Swaper and EQ** for Pop!_OS, Ubuntu, Linux Mint, Debian, and other apt-based systems.

Repository: <https://github.com/Tihulu/L-R-Swaper-and-EQ>

## Screenshot

![L/R Swaper Tihuluwave UI](screenshots/tihuluwave-v5.1.png)

## Quick install

    bash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)

After install, open **L/R Swaper** from the app menu or run:

    lr-swaper

## Manual install from the repository

    git clone https://github.com/Tihulu/L-R-Swaper-and-EQ.git
    cd L-R-Swaper-and-EQ/linux
    chmod +x install.sh check-install.sh uninstall.sh
    ./install.sh
    ./check-install.sh
    lr-swaper

## Manual install from a release archive

    tar -xzf lr-swaper-linux-v5.1.tar.gz
    cd lr-swaper-linux-v5.1
    chmod +x install.sh check-install.sh uninstall.sh
    ./install.sh
    ./check-install.sh
    lr-swaper

## Uninstall

    ./uninstall.sh

The uninstaller removes the application files, launchers, desktop entry, and icons. It does not remove your user presets unless you manually delete:

    rm -rf ~/.config/lr-swaper

## What changed in v5.1

- Fixed the L/R Balance value box so text fits cleanly.
- Balance value uses compact format like `L:94%  R:100%`.
- Help dialog uses real line breaks.
- Help includes the GitHub repository link.
- Keeps Tihuluwave Qt UI and Plain Theme.
- Keeps L/R swap, alternate swap, EQ, volume, balance, test buttons, presets, and clean disable/unload behavior.

## Installed paths

- `~/.local/share/lr-swaper/`
- `~/.local/share/lr-swaper/.venv/`
- `~/.local/bin/lr-swaper`
- `~/.local/bin/bt-lr-swapper`
- `~/.local/share/applications/com.tihulu.lr-swaper.desktop`
- `~/.local/share/icons/hicolor/*/apps/lr-swaper.png`
- `~/.local/share/pixmaps/lr-swaper.png`

## Release

Recommended release tag: `linux-v5.1`

Recommended release asset: `lr-swaper-linux-v5.1.tar.gz`

## License

GPL-3.0-or-later
