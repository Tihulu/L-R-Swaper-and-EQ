# L/R Swaper Linux v5.1

Modern Linux build of **L/R Swaper and EQ** for Pop!_OS, Ubuntu, Linux Mint, Debian, and other apt-based systems.

Repository: <https://github.com/Tihulu/L-R-Swaper-and-EQ>

## Quick install

Use the one-line installer shown in the root README. It installs the Linux build and then you can open **L/R Swaper** from the app menu or run `lr-swaper`.

## Manual install from the repository

Clone the repository, open the `linux/` folder, make `install.sh`, `check-install.sh`, and `uninstall.sh` executable, then run `install.sh`. Run `check-install.sh` after installation if you want to verify the installed files.

## Manual install from a release archive

Download the Linux v5.1 archive, extract it, enter the extracted folder, then run `install.sh`. Run `check-install.sh` afterwards if you want to verify the installation.

## Uninstall

Run `linux/uninstall.sh` from a repository checkout or from the extracted release archive. The uninstaller removes the application files, launchers, desktop entry, and icons. It does not remove your user presets unless you manually delete `~/.config/lr-swaper`.

## What changed in v5.1

- Fixed the L/R Balance value box so the right-side text fits cleanly.
- Balance value now uses compact format like `L:94%  R:100%`.
- Help dialog uses real line breaks instead of showing literal `\\n` text.
- Help includes the GitHub repository link for future updates.
- Version bumped to **v5.1**.

## Installed paths

- `~/.local/share/lr-swaper/`
- `~/.local/share/lr-swaper/.venv/`
- `~/.local/bin/lr-swaper`
- `~/.local/bin/bt-lr-swapper`
- `~/.local/share/applications/com.tihulu.lr-swaper.desktop`
- `~/.local/share/icons/hicolor/*/apps/lr-swaper.png`
- `~/.local/share/pixmaps/lr-swaper.png`

## Release and archive notes

Recommended release tag: `linux-v5.1`

Recommended release title: `L/R Swaper Linux v5.1`

Older release notes can stay archived under [`../RELEASES/`](../RELEASES/).

## License

GPL-3.0-or-later

If an old pinned dock icon opens an old version, unpin it, open **L/R Swaper** from the app menu or terminal, then pin the new running app.
