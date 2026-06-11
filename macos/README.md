# L/R Swaper Mac

macOS Apple Silicon version of L/R Swaper and EQ.

## What it does

The macOS version uses BlackHole 2ch as a virtual audio device:

```text
macOS audio -> BlackHole 2ch -> L/R Swaper Mac -> selected output
```

Features:

- L/R swap
- L/R balance slider
- bass and treble sliders
- volume slider
- 3 volume-independent preset slots
- signal meter
- diagnostics button
- microphone permission helper
- standalone DMG builder
- right-side scrollbar

## Requirements

Build machine:

```bash
brew install python@3.13 python-tk@3.13
```

Runtime audio driver/helper:

```bash
brew install --cask blackhole-2ch
brew install switchaudio-osx
```

The DMG contains `Install Required Audio Driver.command` to install/check these.

## Build DMG

```bash
cd macos
chmod +x build_standalone_dmg.command
./build_standalone_dmg.command
```

Output:

```text
L-R-Swaper-Mac-Standalone-Apple-Silicon.dmg
```

## Privacy / permissions

macOS treats BlackHole as an audio input device, so the app needs Microphone permission.

The app does not record or upload audio. Processing is local.

If the signal meter stays at 0%:

```text
System Settings -> Privacy & Security -> Microphone -> enable L-R Swaper Mac
```

Then click Stop and Start again.

If the app does not appear in Microphone settings, open the app and press Start once to trigger the permission request.

## Important limitation

A normal app cannot bundle BlackHole as a no-install dependency because BlackHole is a macOS virtual audio driver. It must be installed into the system once.
