# L/R Swaper Linux v5.1

Modern Linux build of **L/R Swaper and EQ** for Pop!_OS, Ubuntu, Linux Mint, Debian, and other apt-based systems.

Repository: <https://github.com/Tihulu/L-R-Swaper-and-EQ>

## Quick install

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)
```

After install, open **L/R Swaper** from the app menu or run:

```bash
lr-swaper
```

## What changed in v5.1

- Fixed the L/R Balance value box so the right-side text fits cleanly.
- Balance value now uses compact format like `L:94%  R:100%`.
- Help dialog uses real line breaks instead of showing literal `\\n` text.
- Help includes the GitHub repository link for future updates.
- Version bumped to **v5.1**.

## Manual install from release archive

```bash
tar -xzf lr-swaper-linux-v5.1.tar.gz
cd lr-swaper-linux-v5.1
chmod +x install.sh check-install.sh
./install.sh
./check-install.sh
lr-swaper
```

## Manual install from repository

```bash
git clone https://github.com/Tihulu/L-R-Swaper-and-EQ.git
cd L-R-Swaper-and-EQ/linux
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
linux-v5.1
```

Recommended release title:

```text
L/R Swaper Linux v5.1
```

## License

GPL-3.0-or-later

If an old pinned dock icon opens an old version, unpin it, open **L/R Swaper** from the app menu or terminal, then pin the new running app.
