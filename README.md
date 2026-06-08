# L/R Swaper v2.8

Small Pop!_OS / Ubuntu GUI + CLI app to swap left/right channels for any stereo audio output plus EQ.

## New in v2.8

- Renamed app to **L/R Swaper**.
- Added **L/R audio test** buttons: Test Left, Test Right, and L/R Test.
- Replaced bass/treble switches with adjustable **Bass** and **Treble** sliders.
- Added **Swap current default** for the old one-click behavior, plus **Set selected default**.
- Keeps the old `bt-lr-swapper` command as an alias.

## Install

```bash
sudo apt install python3-tk pulseaudio-utils alsa-utils swh-plugins
unzip -o lr-swaper-v28.zip
cd lr-swaper-v7
chmod +x install.sh
./install.sh
```

Then open **L/R Swaper** from the app menu.

## Notes about Bass/Treble

The bass and treble sliders use Pulse/PipeWire's LADSPA sink with the `mbeq_1197` multiband EQ plugin from `swh-plugins`.

If the sliders fail, install:

```bash
sudo apt install swh-plugins
```

Then close and reopen the app.

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
lr-swaper --disable
lr-swaper --status
```

The old command also works:

```bash
bt-lr-swapper --status
```

## Dock icon

The launcher uses:

```text
Icon=lr-swaper
StartupWMClass=lr-swaper
```

After installing, close the old app, remove the old pinned dock item, open **L/R Swaper** from the app menu, then pin it again.

## Bass/Treble sliders

The sliders are 0 to 10 dB. Move the slider and release it, or click **Apply tone**. Use **Reset tone** to turn the EQ off.


## v2.8 tone sliders

Bass and Treble now use Pop!_OS-style volume sliders:

- 100 = normal / no EQ
- below 100 = cut
- above 100 = boost
- the small dB value shows the actual EQ amount

The slider applies when you release the handle. Use **Reset to 100** to turn tone EQ off.


## v2.8 sliders

Bass and Treble now use a **0–100** range:

- 50 = normal / no EQ
- 0 = maximum cut
- 100 = maximum boost

A new optional **L/R balance** slider was added:

- 50 = centered
- 0 = left only
- 100 = right only

CLI examples:

```bash
lr-swaper --balance 50
lr-swaper --balance 25
lr-swaper --balance-center
```


## v2.8 volume fix

The L/R balance slider no longer resets the output to 100%. It preserves the
current system volume and only changes the relative left/right channel level.

A dedicated **Volume** slider was added:

- 0 = mute
- 100 = normal
- 150 = boosted

CLI examples:

```bash
lr-swaper --volume 80
lr-swaper --balance 35
```


## v2.8 hotfix

Fixes startup crash:

```text
NameError: name 're' is not defined
```

The issue was a missing `import re` used by volume percentage parsing.


## v2.8 close behavior

Closing the app window now disables L/R Swaper instead of leaving virtual
PipeWire/PulseAudio sinks running:

- restores a real output when possible
- moves active streams back to that output
- unloads swap/EQ modules
- clears the saved app state

The **Disable** button and `lr-swaper --disable` use the same cleanup behavior.


## v2.8 target device lock

A new **Use selected as target** button was added.

Recommended workflow:

1. Select the real device you want, such as Bluetooth or USB.
2. Click **Use selected as target**.
3. Use swap, bass/treble, volume, and L/R balance.

This prevents EQ from accidentally rebuilding on the System/Internal audio output
when the current default sink is already a virtual swap/EQ chain.

CLI example:

```bash
pactl list short sinks
lr-swaper --target bluez_output.YOUR_DEVICE_NAME
```


## v2.8 routing fix

Fixes the issue where touching Bass/Treble could make audio run through the
System/Internal output instead of the selected target device.

The app now avoids moving PipeWire/PulseAudio internal module streams. It only
moves real app/player streams when rebuilding swap/EQ chains.


## v2.8 live sliders and EQ loudness fix

- Volume, Bass, Treble, and L/R sliders apply while dragging.
- EQ rebuilds preserve the saved system volume on the new EQ sink.
- This reduces the perceived volume drop caused by newly-created tone/EQ sinks.


## v2.8 volume-drop fix

Fixes the remaining volume drop after touching EQ.

Cause: when EQ/swap virtual sinks are active, volume can be multiplied through
the chain, for example:

```text
EQ sink 50% × Bluetooth master 50% = perceived 25%
```

Fix: the app now keeps hidden master sinks at 100% and applies the user's
volume only to the visible/front EQ or swap sink. When the app closes or
Disable is used, the real output volume is restored.


## v2.8 manual values and saved settings

- Slider values can now be typed by hand in the number boxes.
- Press Enter or click away from the number box to apply.
- **Save settings** stores:
  - target device
  - volume
  - bass
  - treble
  - L/R balance
  - swap mode
- **Load saved** reapplies those settings.
- Saved settings live at:

```text
~/.config/lr-swaper/saved_settings.json
```

CLI:

```bash
lr-swaper --save-settings
lr-swaper --load-settings
```


## v2.8 three preset slots

L/R Swaper now has three saved setting slots:

- **Save 1 / Load 1**
- **Save 2 / Load 2**
- **Save 3 / Load 3**

Each slot stores target device, volume, bass, treble, L/R balance, and swap mode.

Files:

```text
~/.config/lr-swaper/saved_settings.json
~/.config/lr-swaper/saved_settings_2.json
~/.config/lr-swaper/saved_settings_3.json
```

CLI:

```bash
lr-swaper --save-slot 1
lr-swaper --load-slot 1
lr-swaper --save-slot 2
lr-swaper --load-slot 2
lr-swaper --save-slot 3
lr-swaper --load-slot 3
```


## v2.8 preset load fix and Neutral button

- Loading a preset now starts from a clean audio chain, so old EQ/swap modules
  do not remain active.
- The number boxes beside sliders are forced to refresh after loading.
- Added **Neutral** button:
  - disables swap/EQ
  - volume = 100
  - bass = 50
  - treble = 50
  - L/R = center
  - keeps the target device when possible

CLI:

```bash
lr-swaper --neutral
```


## v2.8 Neutral volume behavior

Neutral now preserves the current volume instead of forcing it to 100.

Neutral now means:

- swap/EQ off
- bass = 50
- treble = 50
- L/R = center
- target device kept when possible
- volume unchanged


## v2.8 volume-independent presets

Preset slots no longer save or load volume.

Presets affect:

- target device
- swap mode/on-off
- bass
- treble
- L/R balance

Presets do **not** affect:

- current volume

This means you can keep one volume level and switch between presets without
the volume jumping.


## v2.8 preset-load loud-start fix

Fixes the momentary loud sound when pressing **Load preset**.

Cause: preset loading could briefly make the target or newly-created swap/EQ
sink active before the preserved current volume was fully applied.

Fix: the app now pre-stages the real target, swap sink, and EQ base at the
current volume before switching/moving app streams.


## v2.8 external volume refresh

The Volume slider and number box now refresh automatically when volume is
changed outside the app, such as from Pop!_OS volume keys or the system sound
menu.

Preset loading remains volume-independent and keeps the current volume.


## v2.8 burst-safe preset loading

Fixes the remaining short loud burst during preset loading.

Preset load now:

1. records current app/player stream mute states
2. temporarily mutes only real app/player streams
3. rebuilds swap/EQ chain and stages volume
4. restores each stream's previous mute state

Internal PipeWire module streams are not muted or moved.


## v2.8 collapsible sections

Main UI sections are now click-to-hide/click-to-show:

- Audio outputs
- Controls
- L/R audio test
- Volume / EQ / Presets

There are also **Collapse all** and **Expand all** buttons at the top.
The L/R audio test section starts collapsed to save vertical space.


## v2.8 layout resize fix

Earlier, only the **Audio outputs** section grew when the app window was
resized. This happened because its grid row had vertical stretch weight and the
other sections only stretched horizontally.

v2.8 makes the layout more balanced:

- Audio outputs no longer takes all extra vertical height.
- Audio outputs has a fixed 7-row table height.
- Section collapse/expand still works.


## v2.8 general right-side scrollbar

The app now has one main vertical scrollbar on the right side.

Instead of the Audio Outputs or Volume section stretching when you resize the
window, each section keeps its natural size and the whole page scrolls. Mouse
wheel scrolling works too.


## v2.8 nested scroll behavior

Mouse-wheel scrolling now works like this:

1. If the mouse is over a scrollable inner widget, such as the Audio outputs
   table, that widget scrolls first.
2. If the inner widget is already at its top or bottom edge, the main app window
   scrollbar scrolls instead.

This prevents the whole app from moving while you are still scrolling inside an
inner panel.


## v2.8 strict inner scroll blocking

Mouse-wheel scrolling now behaves like this:

- If the mouse is inside an inner scrollable widget, such as **Audio outputs**,
  only that widget may scroll.
- The general/right-side window scrollbar will not move while the mouse is
  inside that inner scrollable widget.
- The general window scrolls only when the mouse is outside inner scrollable
  widgets.
