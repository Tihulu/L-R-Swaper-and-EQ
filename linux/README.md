# L/R Swaper Linux

Pop!_OS / Ubuntu GUI + CLI app to swap left/right channels for any stereo audio output, apply simple bass/treble EQ, adjust L/R balance, and manage presets.

## Requirements

Install the recommended packages:

```bash
sudo apt install python3-tk pulseaudio-utils alsa-utils swh-plugins
```

What they provide:

- `python3-tk`: GUI support
- `pulseaudio-utils`: `pactl` and `paplay` commands used through PipeWire/PulseAudio compatibility
- `alsa-utils`: useful audio utilities
- `swh-plugins`: LADSPA `mbeq_1197` plugin for bass/treble EQ

## Install

From the repository root:

```bash
cd linux
chmod +x install.sh
./install.sh
```

Then open **L/R Swaper** from the app menu.

The installer also keeps the old command name as an alias:

```bash
bt-lr-swapper --status
```

## CLI

```bash
lr-swaper --swap-default
lr-swaper --swap-default-alt
lr-swaper --fix-now
lr-swaper --test-left
lr-swaper --test-right
lr-swaper --test-lr
lr-swaper --bass-db 4 --treble-db 2
lr-swaper --bass
lr-swaper --treble
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

## Recommended workflow

1. Select the real device you want, such as Bluetooth, USB, HDMI, or internal speakers.
2. Click **Use selected as target**.
3. Use swap, bass/treble, volume, and L/R balance.
4. Use **Save 1 / Load 1**, **Save 2 / Load 2**, or **Save 3 / Load 3** for presets.

## Controls

### Swap

- **Swap selected** creates a virtual swapped output for the selected device.
- **Alternate swap** uses the alternate channel mapping mode.
- **Swap target/default** applies the old one-click behavior.
- **Disable swap/EQ** restores a real output, moves active streams back, unloads app modules, and clears app state.

### Bass and treble

Bass and treble use the LADSPA `mbeq_1197` multiband EQ plugin from `swh-plugins`.

The sliders use a 0–100 range:

- 50 = normal / no EQ
- 0 = maximum cut
- 100 = maximum boost

If EQ fails, install the plugin package and reopen the app:

```bash
sudo apt install swh-plugins
```

### L/R balance

The L/R slider uses a 0–100 range:

- 50 = centered
- 0 = left only
- 100 = right only

The app preserves current system volume while changing the relative left/right channel level.

### Volume

The Volume slider uses a 0–150 range:

- 0 = mute
- 100 = normal
- 150 = boosted

Volume is independent from presets, so loading a preset does not jump the current volume.

## Presets

There are three saved setting slots:

- **Save 1 / Load 1**
- **Save 2 / Load 2**
- **Save 3 / Load 3**

Preset files:

```text
~/.config/lr-swaper/saved_settings.json
~/.config/lr-swaper/saved_settings_2.json
~/.config/lr-swaper/saved_settings_3.json
```

Presets save:

- target device
- swap mode/on-off
- bass
- treble
- L/R balance

Presets do not save volume.

## Dock icon

The launcher uses:

```text
Icon=lr-swaper
StartupWMClass=lr-swaper
```

After installing, close the old app, remove the old pinned dock item, open **L/R Swaper** from the app menu, then pin it again.

## Build standalone binary

```bash
cd linux
chmod +x build.sh
./build.sh
```

Output:

```text
dist/lr-swaper
```

## Uninstall

```bash
cd linux
chmod +x uninstall.sh
./uninstall.sh
```

## Troubleshooting

### `pactl` is missing

```bash
sudo apt install pulseaudio-utils
```

### Tkinter is missing

```bash
sudo apt install python3-tk
```

### Bass/Treble fails

```bash
sudo apt install swh-plugins
```

### Audio routed to the wrong output

Use **Use selected as target** before changing EQ/swap settings. This keeps EQ and swap chains locked to the real output device instead of accidentally rebuilding on the system/internal output.

### Virtual sinks remain after closing

Use:

```bash
lr-swaper --disable
```

Closing the app window should also disable L/R Swaper and unload its virtual PipeWire/PulseAudio modules.
