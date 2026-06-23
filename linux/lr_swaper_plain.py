#!/usr/bin/env python3
"""
L/R Swaper v5.1

A Pop!_OS / Ubuntu GUI + CLI helper for swapping left/right channels on any
stereo audio output through PipeWire's PulseAudio compatibility layer.

Features:
- Standard and alternate L/R swap modes.
- Move active audio streams to the selected/default output.
- L/R audio test tones.
- Adjustable bass and treble sliders using LADSPA mbeq when available.
- Pop!_OS dock icon / WM_CLASS matching.
"""

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
    HAS_TK = True
except Exception:
    HAS_TK = False

APP_NAME = "L/R Swaper"
VERSION = "2.8"
APP_ID = "lr-swaper"
STATE_DIR = Path.home() / ".config" / APP_ID
STATE_FILE = STATE_DIR / "state.json"
USER_SETTINGS_FILE = STATE_DIR / "saved_settings.json"
USER_SETTINGS_SLOTS = 3
CACHE_DIR = Path.home() / ".cache" / APP_ID
APP_SHARE_DIR = Path.home() / ".local" / "share" / APP_ID
APP_ICON_PATH = APP_SHARE_DIR / "icons" / "lr-swaper-256.png"
THEME_FILE = STATE_DIR / "theme.json"
THEME_TIHULUWAVE = "Tihuluwave Theme"


def save_theme_name(name):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        THEME_FILE.write_text(json.dumps({"theme": name}, indent=2))
    except Exception:
        pass


def restart_launcher():
    try:
        launcher = Path(__file__).resolve().with_name("lr-swaper.py")
        os.execv(sys.executable, [sys.executable, str(launcher)] + sys.argv[1:])
    except Exception:
        pass


SINK_PREFIX = "lr_swaper_"
EQ_PREFIX = "lr_swaper_eq_"
LEGACY_PREFIXES = ("bt_lr_swapper_", "lr_swaper_", "lr_swaper_eq_")


# ----------------------------- low-level helpers -----------------------------

def run_cmd(args):
    try:
        r = subprocess.run(args, text=True, capture_output=True)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {args[0]}"


def popen_cmd(args):
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, ""
    except FileNotFoundError:
        return False, f"Command not found: {args[0]}"
    except Exception as e:
        return False, str(e)


def have(cmd):
    return shutil.which(cmd) is not None


def require_pactl(gui=False):
    if have("pactl"):
        return True
    msg = (
        "pactl is not installed or not in PATH.\n\n"
        "Install it on Pop!_OS with:\n"
        "sudo apt install pulseaudio-utils"
    )
    if gui and HAS_TK:
        messagebox.showerror(APP_NAME, msg)
    else:
        print(msg, file=sys.stderr)
    return False


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))



def normalize_settings_slot(slot=1):
    try:
        slot = int(slot)
    except Exception:
        slot = 1
    return max(1, min(USER_SETTINGS_SLOTS, slot))


def user_settings_file(slot=1):
    """Return the saved settings file for a preset slot.

    Slot 1 keeps using the old saved_settings.json path for backward
    compatibility. Slots 2 and 3 use numbered files.
    """
    slot = normalize_settings_slot(slot)
    if slot == 1:
        return USER_SETTINGS_FILE
    return STATE_DIR / f"saved_settings_{slot}.json"


def save_user_settings(slot=1):
    """Save user-facing settings to one of three preset slots."""
    slot = normalize_settings_slot(slot)
    state = load_state()
    settings = {
        "version": VERSION,
        "slot": slot,
        "target_sink_name": state.get("target_sink_name", ""),
        "target_description": state.get("target_description", ""),
        # Volume is intentionally independent from preset slots.
        # Presets save audio shape/routing only; loading a preset keeps the current volume.
        "volume_independent": True,
        "bass": db_to_tone_slider_value(state.get("bass_db", 0.0)),
        "treble": db_to_tone_slider_value(state.get("treble_db", 0.0)),
        "balance": clamp_balance(state.get("balance_value", 50)),
        "swap_mode": state.get("mode", "A"),
        "swap_enabled": bool(state.get("swapped_sink_name")),
        "tone_enabled": abs(float(state.get("bass_db", 0.0) or 0.0)) > 0.05 or abs(float(state.get("treble_db", 0.0) or 0.0)) > 0.05,
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    user_settings_file(slot).write_text(json.dumps(settings, indent=2))
    return settings


def load_user_settings(slot=1):
    slot = normalize_settings_slot(slot)
    try:
        return json.loads(user_settings_file(slot).read_text())
    except Exception:
        return {}


def apply_user_settings(settings=None, slot=1):
    """Apply saved settings from one of three preset slots.

    Presets are volume-independent and preset loading is burst-safe:
    app/player streams are temporarily muted while the audio chain is rebuilt,
    then their previous mute state is restored.
    """
    slot = normalize_settings_slot(slot)
    settings = settings or load_user_settings(slot)
    if not settings:
        return False, f"No saved settings found in slot {slot}."

    messages = []
    target = settings.get("target_sink_name") or ""
    target_ok = False

    old_state = load_state()
    preserved_volume = clamp_system_volume(
        old_state.get("system_volume", get_current_output_volume_percent())
    )

    # Hard safety: silence real app/player streams while the chain is rebuilt.
    # This avoids the remaining short loud burst that can happen before
    # PipeWire finishes moving streams and applying virtual sink volumes.
    mute_states = mute_user_streams_for_rebuild()

    try:
        # Clean previous virtual chain first, but do not rely on the old state after this.
        unload_modules(app_modules())
        clear_state()

        if target:
            if sink_exists(target) and not is_our_sink(target):
                ok, msg = remember_target_sink(target)
                target_ok = ok
                messages.append(msg)
                if ok:
                    set_sink_raw_volume(target, preserved_volume, preserved_volume)
                    set_default_and_move(target)
            else:
                messages.append(f"Saved target not available: {target}")

        if not target_ok:
            fallback = current_master_candidate()
            if fallback and sink_exists(fallback) and not is_our_sink(fallback):
                remember_target_sink(fallback)
                target = fallback
                target_ok = True
                messages.append(f"Using fallback target: {sink_descriptions().get(fallback, fallback)}")

        balance = clamp_balance(settings.get("balance", 50))
        bass_slider = max(0, min(100, int(round(float(settings.get("bass", 50) or 50)))))
        treble_slider = max(0, min(100, int(round(float(settings.get("treble", 50) or 50)))))
        bass_db = tone_slider_value_to_db(bass_slider)
        treble_db = tone_slider_value_to_db(treble_slider)
        swap_enabled = bool(settings.get("swap_enabled", False))
        swap_mode = str(settings.get("swap_mode", "A") or "A").upper()
        if swap_mode not in ("A", "B"):
            swap_mode = "A"

        active_sink = get_target_sink() or target or current_master_candidate()

        # Stage current volume/balance in state before any virtual sink is created.
        state = load_state()
        state["system_volume"] = preserved_volume
        state["balance_value"] = balance
        save_state(state)

        if active_sink and sink_exists(active_sink) and not is_our_sink(active_sink):
            set_sink_raw_volume(active_sink, preserved_volume, preserved_volume)

        if swap_enabled and active_sink:
            ok, swapped, msg = load_swap(active_sink, swap_mode)
            messages.append(msg)
            if ok and swapped:
                active_sink = swapped

        if abs(bass_db) > 0.05 or abs(treble_db) > 0.05:
            ok, msg = apply_tone_values(bass_db, treble_db)
            messages.append(msg)
            state = load_state()
            active_sink = state.get("eq_sink_name") or state.get("swapped_sink_name") or active_sink

        # Keep volume independent from presets.
        ok, msg = apply_system_volume_value(preserved_volume, active_sink)
        messages.append("Volume kept unchanged. " + msg)
        ok, msg = apply_balance_value(balance, active_sink)
        messages.append(msg)

        state = load_state()
        state["system_volume"] = preserved_volume
        state["balance_value"] = balance
        state["bass_db"] = bass_db
        state["treble_db"] = treble_db
        state["volume_independent_presets"] = True
        save_state(state)

        return True, f"Loaded preset slot {slot} safely without changing volume. " + " ".join(m for m in messages if m)
    finally:
        restore_user_stream_mutes(mute_states)


def reset_to_neutral_settings():
    """Reset tone/swap/balance to neutral while preserving current volume.

    Neutral means:
      - swap/EQ off
      - bass/treble neutral
      - L/R centered
      - target kept when possible
      - volume NOT changed
    """
    state = load_state()

    # Preserve the user's current effective volume before removing virtual sinks.
    # Prefer app state because virtual EQ/swap chains may keep hidden masters at
    # 100% while the visible/front sink carries the user's real volume.
    preserved_volume = clamp_system_volume(
        state.get("system_volume", get_current_output_volume_percent())
    )

    target = (
        get_target_sink()
        or state.get("target_sink_name")
        or state.get("master_name")
        or state.get("previous_default")
        or current_master_candidate()
    )
    target_desc = sink_descriptions().get(target, target) if target else ""

    if target and sink_exists(target) and not is_our_sink(target):
        unload_modules(app_modules())
        clear_state()
        remember_target_sink(target)

        # Keep the user's volume, but center L/R for neutral.
        set_sink_raw_volume(target, preserved_volume, preserved_volume)
        set_default_and_move(target)

        state = load_state()
        state["system_volume"] = preserved_volume
        state["balance_value"] = 50
        state["balance_enabled"] = False
        state["bass_db"] = 0.0
        state["treble_db"] = 0.0
        state["bass_enabled"] = False
        state["treble_enabled"] = False
        state["mode"] = "A"
        save_state(state)

        return True, f"Neutral settings applied without changing volume ({int(round(preserved_volume))}%). Target kept: {target_desc or target}."

    unload_modules(app_modules())
    clear_state()
    return True, f"Neutral settings applied without changing volume ({int(round(preserved_volume))}%). No target device was available."


def clear_state():
    try:
        STATE_FILE.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        save_state({})


def remember_target_sink(sink_name):
    """Save the real output device that swap/EQ/volume should use."""
    if not sink_name:
        return False, "No output selected."
    if not sink_exists(sink_name):
        return False, f"Selected output does not exist: {sink_name}"
    if is_our_sink(sink_name):
        return False, "Select a real output device, not an L/R Swaper virtual output."

    desc = sink_descriptions().get(sink_name, sink_name)
    state = load_state()
    state["target_sink_name"] = sink_name
    state["target_description"] = desc
    # Make target the preferred real master and restore device.
    state["master_name"] = sink_name
    state["previous_default"] = sink_name
    save_state(state)
    return True, f"Target device set to: {desc}"


def get_target_sink():
    """Return the saved real target sink if available."""
    state = load_state()
    target = state.get("target_sink_name")
    if target and sink_exists(target) and not is_our_sink(target):
        return target
    return ""


def get_target_description():
    state = load_state()
    target = get_target_sink()
    if not target:
        return "No target selected"
    return state.get("target_description") or sink_descriptions().get(target, target)


def default_sink():
    code, out, _ = run_cmd(["pactl", "get-default-sink"])
    return out if code == 0 else ""


def is_our_sink(name):
    return any(name.startswith(prefix) for prefix in LEGACY_PREFIXES)


def is_eq_sink(name):
    return name.startswith(EQ_PREFIX)


def make_hash(*parts):
    return hashlib.sha1(":".join(parts).encode("utf-8")).hexdigest()[:10]


def swap_sink_name(master_name, mode):
    return f"{SINK_PREFIX}{mode.lower()}_{make_hash(master_name, mode)}"


def eq_sink_name(master_name, bass_db, treble_db):
    mode = f"b{int(round(float(bass_db) * 10))}_t{int(round(float(treble_db) * 10))}"
    return f"{EQ_PREFIX}{mode}_{make_hash(master_name, mode)}"


def db_to_tone_slider_value(db):
    """Map -10..+10 dB to a 0..100 slider, where 50 is normal."""
    return int(round(50 + clamp_db(db) * 5))


def tone_slider_value_to_db(value):
    """Map 0..100 slider to -10..+10 dB, where 50 is normal."""
    try:
        value = float(value)
    except Exception:
        value = 50.0
    value = max(0.0, min(100.0, value))
    return round((value - 50.0) / 5.0, 1)


def clamp_balance(value):
    """0 = left only, 50 = centered, 100 = right only."""
    try:
        value = float(value)
    except Exception:
        value = 50.0
    return max(0.0, min(100.0, value))


def balance_value_to_volumes(value):
    """Return (left_percent, right_percent) for a 0..100 balance slider.

    50 keeps both channels at 100%.
    Moving left reduces the right channel.
    Moving right reduces the left channel.
    """
    value = clamp_balance(value)
    if value < 50:
        left = 100
        right = int(round((value / 50.0) * 100))
    elif value > 50:
        left = int(round(((100.0 - value) / 50.0) * 100))
        right = 100
    else:
        left = right = 100
    return max(0, min(100, left)), max(0, min(100, right))


def format_tone_slider(value):
    return f"{tone_slider_value_to_db(value):+.1f} dB"


def format_balance_slider(value):
    value = int(round(clamp_balance(value)))
    if value == 50:
        return "Center"
    left, right = balance_value_to_volumes(value)
    return f"L {left}% / R {right}%"


def clamp_system_volume(value):
    """System output volume slider, 0..150 percent."""
    try:
        value = float(value)
    except Exception:
        value = 100.0
    return max(0.0, min(150.0, value))


def format_system_volume(value):
    return f"{int(round(clamp_system_volume(value)))}%"


def parse_percent_values(text):
    """Return all volume percentages found in pactl output."""
    values = []
    for match in re.finditer(r"/\s*(\d+(?:\.\d+)?)%", text):
        try:
            values.append(float(match.group(1)))
        except Exception:
            pass
    return values


def get_sink_volume_percent(sink_name):
    """Return approximate sink volume percent without changing it."""
    if not sink_name:
        return 100.0
    code, out, _ = run_cmd(["pactl", "get-sink-volume", sink_name])
    if code != 0:
        return 100.0
    values = parse_percent_values(out)
    if not values:
        return 100.0
    # Use the loudest channel as the user's effective system volume.
    return clamp_system_volume(max(values))


def get_current_output_volume_percent():
    return get_sink_volume_percent(default_sink())


def get_app_control_volume_percent():
    """Read the volume from the sink this app currently controls.

    This lets the GUI notice volume changes made outside the app, such as
    Pop!_OS volume keys or the system sound menu.
    """
    try:
        sink = preferred_control_sink()
    except Exception:
        sink = default_sink()
    return get_sink_volume_percent(sink)


def volumes_for_balance_at_base(balance_value, base_volume):
    """Return L/R channel volumes that preserve the user's chosen base volume.

    Example at base 37:
      balance 50 -> 37%, 37%
      balance 25 -> 37%, 18.5%
      balance 75 -> 18.5%, 37%

    This avoids the old bug where moving balance reset the output to 100%.
    """
    base = clamp_system_volume(base_volume)
    balance = clamp_balance(balance_value)
    if balance < 50:
        left = base
        right = base * (balance / 50.0)
    elif balance > 50:
        left = base * ((100.0 - balance) / 50.0)
        right = base
    else:
        left = right = base
    return max(0, round(left)), max(0, round(right))


# -------------------------------- sink parsing --------------------------------

def list_short_sinks():
    code, out, err = run_cmd(["pactl", "list", "short", "sinks"])
    if code != 0:
        raise RuntimeError(err or "Could not list sinks")
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            rows.append({
                "index": parts[0],
                "name": parts[1],
                "driver": parts[2] if len(parts) > 2 else "",
                "spec": parts[3] if len(parts) > 3 else "",
                "state": parts[4] if len(parts) > 4 else "",
            })
    return rows


def sink_descriptions():
    code, out, _ = run_cmd(["pactl", "list", "sinks"])
    desc = {}
    current = None
    if code != 0:
        return desc
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Name: "):
            current = s.split("Name: ", 1)[1]
        elif s.startswith("Description: ") and current:
            desc[current] = s.split("Description: ", 1)[1]
    return desc


def all_sinks():
    descriptions = sink_descriptions()
    cur = default_sink()
    result = []
    for row in list_short_sinks():
        name = row["name"]
        result.append({
            **row,
            "description": descriptions.get(name, name),
            "is_default": name == cur,
            "is_app": is_our_sink(name),
            "is_eq": is_eq_sink(name),
        })
    return result


def sink_exists(name):
    return any(s["name"] == name for s in all_sinks())


def sink_index_for_name(name):
    for s in all_sinks():
        if s["name"] == name:
            return s["index"]
    return ""


def bluetooth_sinks():
    return [s for s in all_sinks() if s["name"].startswith("bluez_output.")]


def current_master_candidate():
    # Prefer the manually locked target. This prevents System/Internal audio
    # from being chosen when the current default is a virtual swap/EQ chain.
    target = get_target_sink()
    if target:
        return target

    cur = default_sink()
    state = load_state()
    if is_our_sink(cur):
        for key in ("master_name", "previous_default", "eq_master"):
            val = state.get(key)
            if val and sink_exists(val) and not is_our_sink(val):
                return val
        bts = bluetooth_sinks()
        if bts:
            return bts[0]["name"]
    return cur


def current_audio_base():
    """Return the sink to use as EQ master.

    If a target device is locked, EQ should use that target unless there is an
    active swapped sink that was created from the same target. This prevents EQ
    from jumping back to the System/Internal audio device.
    """
    state = load_state()
    target = get_target_sink()
    swapped = state.get("swapped_sink_name")

    if swapped and sink_exists(swapped):
        if not target or state.get("master_name") == target:
            return swapped

    if target:
        return target

    eq_master = state.get("eq_master")
    if eq_master and sink_exists(eq_master):
        return eq_master

    cur = default_sink()
    if is_eq_sink(cur):
        return state.get("eq_master") or state.get("swapped_sink_name") or current_master_candidate()
    if is_our_sink(cur):
        return current_master_candidate()
    return cur


# --------------------------- modules and routing ------------------------------

def module_rows():
    code, out, _ = run_cmd(["pactl", "list", "modules", "short"])
    rows = []
    if code != 0:
        return rows
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            rows.append({"index": parts[0], "name": parts[1], "args": parts[2]})
    return rows


def app_modules(kind=None):
    rows = []
    for r in module_rows():
        args = r["args"]
        if any(f"sink_name={prefix}" in args for prefix in LEGACY_PREFIXES):
            if kind is None or r["name"] == kind:
                rows.append(r)
    return rows


def unload_modules(rows):
    count = 0
    for r in rows:
        code, _, _ = run_cmd(["pactl", "unload-module", r["index"]])
        if code == 0:
            count += 1
    return count


def unload_eq_modules():
    return unload_modules([r for r in app_modules() if "sink_name=" + EQ_PREFIX in r["args"]])


def unload_app_modules():
    count = unload_modules(app_modules())
    clear_state()
    return count


def pick_restore_sink(state=None):
    """Pick a real sink to restore before unloading virtual app sinks."""
    state = state or load_state()
    candidates = [
        state.get("previous_default"),
        state.get("master_name"),
        state.get("eq_master"),
    ]

    for name in candidates:
        if name and not is_our_sink(name) and sink_exists(name):
            return name

    for sink in all_sinks():
        if not sink.get("is_app"):
            return sink.get("name")

    return ""


def restore_output_and_unload():
    """Restore a real output, move active streams, unload virtual modules, and clear state.

    This is used when the window is closed so L/R Swaper does not keep virtual
    swap/EQ sinks running in the background.
    """
    state = load_state()
    restore_sink = pick_restore_sink(state)
    moved = 0
    msg_parts = []

    if restore_sink:
        code, _, err = run_cmd(["pactl", "set-default-sink", restore_sink])
        if code == 0:
            # If hidden masters had been kept at 100% for virtual EQ/swap, put
            # the real output back to the user's saved volume before quitting.
            saved_volume = clamp_system_volume(state.get("system_volume", get_sink_volume_percent(restore_sink)))
            saved_balance = clamp_balance(state.get("balance_value", 50))
            left, right = volumes_for_balance_at_base(saved_balance, saved_volume)
            set_sink_raw_volume(restore_sink, left, right)

            moved, errors = move_streams_to_sink(restore_sink)
            msg_parts.append(f"Restored output: {restore_sink}. Moved {moved} stream(s). Volume restored to {int(round(saved_volume))}%.")
            if errors:
                msg_parts.append("Some streams could not be moved: " + "; ".join(errors))
        else:
            msg_parts.append(f"Could not restore previous output: {err}")

    count = unload_modules(app_modules())
    clear_state()
    msg_parts.append(f"Unloaded {count} L/R Swaper module(s).")
    return count, " ".join(msg_parts)


def list_user_sink_input_ids():
    """Return sink-input IDs that look like real app/player streams.

    PipeWire/PulseAudio virtual sinks create internal sink-inputs to connect
    module-remap-sink / module-ladspa-sink to their real master device. In
    `pactl list short sink-inputs` those internal streams usually have client
    column "-". Moving those internal streams breaks the chain and can make
    audio appear to jump back to System/Internal audio.

    So we only move streams with a real client id.
    """
    code, out, err = run_cmd(["pactl", "list", "short", "sink-inputs"])
    if code != 0:
        return [], [err or "Could not list sink inputs"]

    ids = []
    errors = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        input_id, _current_sink, client_id = parts[0], parts[1], parts[2]
        if client_id == "-" or client_id == "":
            continue
        ids.append(input_id)
    return ids, errors


def sink_input_mute_states(input_ids):
    """Return {sink_input_id: is_muted} for real app/player sink inputs."""
    wanted = {str(i) for i in (input_ids or [])}
    if not wanted:
        return {}

    code, out, _ = run_cmd(["pactl", "list", "sink-inputs"])
    if code != 0:
        # Fallback: assume not muted. This is still safer than a loud burst.
        return {str(i): False for i in wanted}

    states = {}
    current = None
    for line in out.splitlines():
        stripped = line.strip()
        if stripped.startswith("Sink Input #"):
            current = stripped.split("#", 1)[1].strip()
        elif current in wanted and stripped.startswith("Mute:"):
            value = stripped.split(":", 1)[1].strip().lower()
            states[current] = value.startswith("yes")
    for i in wanted:
        states.setdefault(i, False)
    return states


def set_sink_input_mute(input_id, mute=True):
    code, _, _ = run_cmd(["pactl", "set-sink-input-mute", str(input_id), "1" if mute else "0"])
    return code == 0


def mute_user_streams_for_rebuild():
    """Mute real app/player streams during preset rebuild to prevent bursts.

    Internal PipeWire module streams are already filtered out by
    list_user_sink_input_ids(), so this does not mute/remap the EQ/swap
    internals. Previous mute states are preserved and restored.
    """
    ids, _ = list_user_sink_input_ids()
    states = sink_input_mute_states(ids)
    for input_id in states:
        set_sink_input_mute(input_id, True)
    return states


def restore_user_stream_mutes(states):
    for input_id, was_muted in (states or {}).items():
        set_sink_input_mute(input_id, was_muted)



def move_specific_streams_to_sink(sink_name, input_ids):
    sink_index = sink_index_for_name(sink_name)
    moved = 0
    errors = []
    for input_id in list(dict.fromkeys(input_ids or [])):
        # The stream may have ended while the app was rebuilding the chain.
        code, out, _ = run_cmd(["pactl", "list", "short", "sink-inputs"])
        if code != 0 or not any(line.split("\t", 1)[0] == str(input_id) for line in out.splitlines() if line.strip()):
            continue

        # Avoid moving streams already on the desired sink.
        current_sink = None
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] == str(input_id):
                current_sink = parts[1]
                break
        if current_sink == sink_index or current_sink == sink_name:
            continue

        code, _, err = run_cmd(["pactl", "move-sink-input", str(input_id), sink_name])
        if code == 0:
            moved += 1
        else:
            errors.append(f"sink-input {input_id}: {err}")
    return moved, errors


def move_streams_to_sink(sink_name):
    ids, errors = list_user_sink_input_ids()
    if errors:
        return 0, errors
    moved, move_errors = move_specific_streams_to_sink(sink_name, ids)
    return moved, move_errors


def set_sink_raw_volume(sink_name, left_percent=100, right_percent=100):
    """Set channel volume without updating app state.

    Used for hidden master sinks in a virtual chain, so the app does not apply
    the user's volume twice.
    """
    if not sink_name or not sink_exists(sink_name):
        return False
    code, _, _ = run_cmd([
        "pactl",
        "set-sink-volume",
        sink_name,
        f"{int(round(left_percent))}%",
        f"{int(round(right_percent))}%",
    ])
    return code == 0


def hidden_master_sinks_for(front_sink):
    """Return downstream master sinks hidden behind a user-facing virtual sink.

    If the user-facing output is EQ, its master might be the swap sink or the
    real target. If it is the swap sink, its master is the real target.

    These hidden sinks must stay at 100% or the final loudness becomes:
      virtual volume × hidden master volume
    which is the volume-drop bug.
    """
    state = load_state()
    hidden = []

    if not front_sink:
        return hidden

    eq = state.get("eq_sink_name")
    swapped = state.get("swapped_sink_name")
    real_master = state.get("master_name") or state.get("target_sink_name")

    if front_sink == eq:
        eq_master = state.get("eq_master")
        if eq_master and sink_exists(eq_master):
            hidden.append(eq_master)
            if eq_master == swapped and real_master and sink_exists(real_master):
                hidden.append(real_master)
    elif front_sink == swapped:
        if real_master and sink_exists(real_master):
            hidden.append(real_master)

    # Never include the front sink itself and keep order/deduplicate.
    result = []
    for name in hidden:
        if name and name != front_sink and name not in result and sink_exists(name):
            result.append(name)
    return result


def normalize_hidden_chain_volume(front_sink):
    """Keep hidden master sinks at 100% so the front sink controls loudness."""
    for hidden in hidden_master_sinks_for(front_sink):
        set_sink_raw_volume(hidden, 100, 100)


def set_sink_volume_with_balance(sink_name, system_volume=None, balance_value=None):
    """Set output volume and optional L/R balance without forcing volume to 100%.

    `system_volume` is the base volume, 0..150. If omitted, the current sink
    volume is used. This is the key fix for the volume-jump bug.
    """
    if not sink_name or not sink_exists(sink_name):
        return False, "No valid output."

    state = load_state()
    if balance_value is None:
        balance_value = state.get("balance_value", 50)
    balance = clamp_balance(balance_value)

    if system_volume is None:
        system_volume = get_sink_volume_percent(sink_name)
    system_volume = clamp_system_volume(system_volume)

    # If sink_name is a user-facing virtual EQ/swap sink, keep hidden masters
    # at unity. Otherwise the volume is multiplied through the chain.
    normalize_hidden_chain_volume(sink_name)

    left, right = volumes_for_balance_at_base(balance, system_volume)
    code, _, err = run_cmd(["pactl", "set-sink-volume", sink_name, f"{left}%", f"{right}%"])
    if code != 0:
        return False, f"Could not set volume/balance: {err}"

    state["system_volume"] = system_volume
    state["balance_value"] = balance
    state["balance_enabled"] = abs(balance - 50.0) > 0.5
    save_state(state)

    if abs(balance - 50.0) <= 0.5:
        return True, f"System volume set to {int(round(system_volume))}%."
    return True, f"System volume {int(round(system_volume))}%, L/R balance {int(round(balance))} ({format_balance_slider(balance)})."


def set_sink_balance(sink_name, balance_value):
    """Set stereo balance while preserving the current output volume."""
    current_volume = get_sink_volume_percent(sink_name)
    return set_sink_volume_with_balance(sink_name, current_volume, balance_value)


def apply_saved_balance_to_sink(sink_name):
    state = load_state()
    balance = clamp_balance(state.get("balance_value", 50))
    saved_volume = clamp_system_volume(state.get("system_volume", get_sink_volume_percent(sink_name)))
    ok, msg = set_sink_volume_with_balance(sink_name, saved_volume, balance)
    return " " + msg if ok else " " + msg


def volume_before_rebuild():
    """Capture the user's effective volume before rebuilding EQ/swap."""
    state = load_state()
    if "system_volume" in state:
        return clamp_system_volume(state.get("system_volume"))
    return get_current_output_volume_percent()


def preferred_control_sink():
    """Pick the sink that volume/balance should control.

    Active EQ wins only if it belongs to the locked target chain. Then swapped
    output, then the locked target, then current default.
    """
    state = load_state()
    target = get_target_sink()

    eq = state.get("eq_sink_name")
    if eq and sink_exists(eq):
        if not target:
            return eq
        eq_master = state.get("eq_master")
        swapped = state.get("swapped_sink_name")
        if eq_master == target or (swapped and eq_master == swapped and state.get("master_name") == target):
            return eq

    swapped = state.get("swapped_sink_name")
    if swapped and sink_exists(swapped):
        if not target or state.get("master_name") == target:
            return swapped

    if target:
        return target

    return default_sink()


def apply_balance_value(balance_value=50, target=None):
    target = target or preferred_control_sink()
    if not target or not sink_exists(target):
        return False, "No valid output for L/R balance."
    # Preserve the current real volume instead of resetting to 100.
    return set_sink_balance(target, balance_value)


def apply_system_volume_value(volume_value=100, target=None):
    target = target or preferred_control_sink()
    if not target or not sink_exists(target):
        return False, "No valid output for system volume."
    state = load_state()
    balance = clamp_balance(state.get("balance_value", 50))
    return set_sink_volume_with_balance(target, volume_value, balance)


def set_default_and_move(sink_name, stream_ids=None):
    if not sink_name:
        return False, "No sink selected."
    code, _, err = run_cmd(["pactl", "set-default-sink", sink_name])
    if code != 0:
        return False, f"Could not set default sink: {err}"

    if stream_ids is None:
        moved, errors = move_streams_to_sink(sink_name)
    else:
        moved, errors = move_specific_streams_to_sink(sink_name, stream_ids)

    balance_msg = apply_saved_balance_to_sink(sink_name)
    if errors:
        return True, f"Default set. Moved {moved} app stream(s). Some streams could not be moved: " + "; ".join(errors) + balance_msg
    return True, f"Default set. Moved {moved} app stream(s)." + balance_msg


# -------------------------------- swap logic ---------------------------------

def load_swap(master_name, mode="A"):
    if not master_name:
        return False, "", "No master sink selected."

    if is_our_sink(master_name):
        state = load_state()
        master_name = state.get("master_name") or state.get("previous_default") or ""
        if not master_name:
            return False, "", "Selected sink is already virtual, but no original output was saved."

    if not sink_exists(master_name):
        return False, "", f"Master sink not found: {master_name}"

    previous = default_sink()
    old = load_state()
    bass_db = clamp_db(old.get("bass_db", 0.0))
    treble_db = clamp_db(old.get("treble_db", 0.0))
    balance_value = clamp_balance(old.get("balance_value", 50))
    system_volume = clamp_system_volume(old.get("system_volume", get_current_output_volume_percent()))
    unload_app_modules()
    streams_to_move, _stream_errors = list_user_sink_input_ids()

    mode = mode.upper()
    if mode == "B":
        channel_map = "front-right,front-left"
        master_channel_map = "front-left,front-right"
    else:
        mode = "A"
        channel_map = "front-left,front-right"
        master_channel_map = "front-right,front-left"

    sink_name = swap_sink_name(master_name, mode)
    desc = f"L-R-Swaper-{mode}"
    args = [
        "pactl", "load-module", "module-remap-sink",
        f"sink_name={sink_name}",
        f"master={master_name}",
        "channels=2",
        f"channel_map={channel_map}",
        f"master_channel_map={master_channel_map}",
        "remix=no",
        f"sink_properties=device.description={desc}",
    ]
    code, out, err = run_cmd(args)
    if code != 0:
        return False, "", err or out or "Could not load module-remap-sink."

    state = {
        "version": VERSION,
        "mode": mode,
        "module_id": out.strip(),
        "master_name": master_name,
        "master_index": sink_index_for_name(master_name),
        "previous_default": previous,
        "swapped_sink_name": sink_name,
        "channel_map": channel_map,
        "master_channel_map": master_channel_map,
        "bass_db": bass_db,
        "treble_db": treble_db,
        "bass_enabled": abs(bass_db) > 0.05,
        "treble_enabled": abs(treble_db) > 0.05,
        "balance_value": balance_value,
        "balance_enabled": abs(balance_value - 50.0) > 0.5,
        "system_volume": system_volume,
        "target_sink_name": old.get("target_sink_name") or (master_name if not is_our_sink(master_name) else ""),
        "target_description": old.get("target_description") or sink_descriptions().get(master_name, master_name),
    }
    save_state(state)
    # Stage the new virtual swap sink volume before moving app streams to it.
    # Without this, preset loading can start loud for a moment and then settle.
    set_sink_volume_with_balance(sink_name, system_volume, balance_value)
    ok, msg = set_default_and_move(sink_name, streams_to_move)
    set_sink_volume_with_balance(sink_name, system_volume, balance_value)
    if ok and (abs(bass_db) > 0.05 or abs(treble_db) > 0.05):
        tone_ok, tone_msg = apply_tone_values(bass_db, treble_db, base_override=sink_name)
        return tone_ok, sink_name, msg + " " + tone_msg
    return ok, sink_name, msg


def fix_now():
    state = load_state()
    target = state.get("eq_sink_name") if (abs(float(state.get("bass_db", 0.0) or 0.0)) > 0.05 or abs(float(state.get("treble_db", 0.0) or 0.0)) > 0.05) else state.get("swapped_sink_name")
    if not target:
        target = default_sink()
    if not sink_exists(target):
        return False, f"Saved output does not exist anymore: {target}. Apply swap again."
    return set_default_and_move(target)


# -------------------------------- EQ logic -----------------------------------

def clamp_db(value):
    try:
        value = float(value)
    except Exception:
        value = 0.0
    return max(-10.0, min(10.0, value))


def eq_controls(bass_db=0.0, treble_db=0.0):
    """Return 15-band mbeq controls in dB.

    The sliders are -10..+10 dB. The lowest/highest bands get the strongest
    change while nearby bands get a smaller change, which sounds smoother
    than changing only one band.
    """
    bass_db = clamp_db(bass_db)
    treble_db = clamp_db(treble_db)
    bands = [0.0] * 15

    if abs(bass_db) > 0.05:
        bands[0] += bass_db
        bands[1] += bass_db
        bands[2] += bass_db * 0.65
        bands[3] += bass_db * 0.30

    if abs(treble_db) > 0.05:
        bands[10] += treble_db * 0.25
        bands[11] += treble_db * 0.45
        bands[12] += treble_db * 0.65
        bands[13] += treble_db * 0.90
        bands[14] += treble_db

    return ",".join(f"{x:.2f}".rstrip("0").rstrip(".") for x in bands)


def apply_tone_values(bass_db=0.0, treble_db=0.0, base_override=None):
    bass_db = clamp_db(bass_db)
    treble_db = clamp_db(treble_db)

    state = load_state()
    base = base_override or current_audio_base()
    if not base or not sink_exists(base):
        return False, "No valid output to apply bass/treble to."

    # Preserve loudness before rebuilding the EQ chain. New LADSPA sinks can
    # otherwise start with their own channel volume and sound lower even when
    # the displayed percentage looks unchanged.
    preserved_volume = volume_before_rebuild()

    # Stage the base at the preserved volume before creating the EQ sink.
    # The new EQ sink is also staged before activation below.
    set_sink_volume_with_balance(base, preserved_volume, state.get("balance_value", 50))

    # Do not stack EQ sinks. Recreate the EQ sink when the sliders change.
    unload_eq_modules()
    streams_to_move, _stream_errors = list_user_sink_input_ids()

    state["bass_db"] = bass_db
    state["treble_db"] = treble_db
    state["system_volume"] = preserved_volume
    state["bass_enabled"] = abs(bass_db) > 0.05
    state["treble_enabled"] = abs(treble_db) > 0.05
    state["eq_master"] = base
    state.pop("eq_sink_name", None)
    state.pop("eq_module_id", None)

    if abs(bass_db) <= 0.05 and abs(treble_db) <= 0.05:
        save_state(state)
        set_sink_volume_with_balance(base, preserved_volume, state.get("balance_value", 50))
        ok, msg = set_default_and_move(base, streams_to_move)
        set_sink_volume_with_balance(base, preserved_volume, state.get("balance_value", 50))
        return ok, "Bass/treble reset. " + msg

    sink_name = eq_sink_name(base, bass_db, treble_db)
    desc = f"L-R-Swaper-Tone-B{bass_db:.1f}-T{treble_db:.1f}".replace(".", "_")

    args = [
        "pactl", "load-module", "module-ladspa-sink",
        f"sink_name={sink_name}",
        f"master={base}",
        "plugin=mbeq_1197",
        "label=mbeq",
        f"control={eq_controls(bass_db, treble_db)}",
        f"sink_properties=device.description={desc}",
    ]
    code, out, err = run_cmd(args)
    if code != 0:
        save_state(state)
        msg = (err or out or "Could not load LADSPA equalizer sink.")
        msg += (
            "\n\nBass/Treble sliders need LADSPA mbeq. Install it with:\n"
            "sudo apt install swh-plugins\n\n"
            "Then close/reopen the app and try again."
        )
        return False, msg

    state["eq_module_id"] = out.strip()
    state["eq_sink_name"] = sink_name
    save_state(state)
    set_sink_volume_with_balance(sink_name, preserved_volume, state.get("balance_value", 50))
    ok, msg = set_default_and_move(sink_name, streams_to_move)
    set_sink_volume_with_balance(sink_name, preserved_volume, state.get("balance_value", 50))
    master_desc = sink_descriptions().get(base, base)
    return ok, f"Tone applied live on target/master [{master_desc}]: bass {bass_db:+.1f} dB, treble {treble_db:+.1f} dB. Volume preserved at {int(round(preserved_volume))}% with hidden master at unity. " + msg


def apply_tone(bass=False, treble=False):
    """Backward-compatible switch-style helper for CLI aliases."""
    return apply_tone_values(5.0 if bass else 0.0, 5.0 if treble else 0.0)


# ---------------------------------- tests ------------------------------------

def write_tone_wav(path, which="lr", sample_rate=48000):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(path)
    amp = int(0.32 * 32767)

    def sample(freq, t):
        return int(amp * math.sin(2 * math.pi * freq * t))

    frames = []
    def add_segment(duration, left_freq=None, right_freq=None):
        n = int(sample_rate * duration)
        for i in range(n):
            t = i / sample_rate
            left = sample(left_freq, t) if left_freq else 0
            right = sample(right_freq, t) if right_freq else 0
            frames.append((left, right))

    if which == "left":
        add_segment(1.25, left_freq=440)
    elif which == "right":
        add_segment(1.25, right_freq=660)
    else:
        add_segment(0.9, left_freq=440)
        add_segment(0.25)
        add_segment(0.9, right_freq=660)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        raw = bytearray()
        for l, r in frames:
            raw += int(l).to_bytes(2, "little", signed=True)
            raw += int(r).to_bytes(2, "little", signed=True)
        wav.writeframes(bytes(raw))


def play_test(which="lr", sink=None):
    if not have("paplay"):
        return False, "paplay is missing. Install it with: sudo apt install pulseaudio-utils"
    sink = sink or default_sink()
    if not sink:
        return False, "No default sink found."
    wav_path = CACHE_DIR / f"test-{which}.wav"
    write_tone_wav(wav_path, which)
    ok, msg = popen_cmd(["paplay", f"--device={sink}", str(wav_path)])
    if ok:
        label = {"left": "left channel", "right": "right channel", "lr": "left then right"}.get(which, which)
        return True, f"Playing {label} test on {sink}."
    return False, msg


# ------------------------------ diagnostics / CLI -----------------------------

def diagnostics():
    cmds = [
        ["pactl", "info"],
        ["pactl", "get-default-sink"],
        ["pactl", "list", "short", "sinks"],
        ["pactl", "list", "short", "sink-inputs"],
        ["pactl", "list", "modules", "short"],
    ]
    lines = [f"{APP_NAME} v{VERSION}", f"State file: {STATE_FILE}", ""]
    for cmd in cmds:
        code, out, err = run_cmd(cmd)
        lines.append("$ " + " ".join(cmd))
        lines.append(f"exit code: {code}")
        if out:
            lines.append(out)
        if err:
            lines.append("stderr:")
            lines.append(err)
        lines.append("")
    lines.append("Saved state:")
    lines.append(json.dumps(load_state(), indent=2))
    return "\n".join(lines)


def cli(argv):
    if not require_pactl(False):
        return 1

    if "--status" in argv:
        print(diagnostics())
        return 0
    if "--disable" in argv:
        count, msg = restore_output_and_unload()
        print(msg or f"Disabled {count} {APP_NAME} module(s).")
        return 0
    if "--target" in argv:
        try:
            value = argv[argv.index("--target") + 1]
        except Exception:
            print("--target needs a sink name. Use: pactl list short sinks", file=sys.stderr)
            return 2
        ok, msg = remember_target_sink(value)
        print(msg)
        return 0 if ok else 2
    if "--save-slot" in argv:
        try:
            slot = argv[argv.index("--save-slot") + 1]
        except Exception:
            print("--save-slot needs 1, 2, or 3.", file=sys.stderr)
            return 2
        slot = normalize_settings_slot(slot)
        settings = save_user_settings(slot)
        print(f"Saved settings slot {slot} to {user_settings_file(slot)}")
        print(json.dumps(settings, indent=2))
        return 0
    if "--load-slot" in argv:
        try:
            slot = argv[argv.index("--load-slot") + 1]
        except Exception:
            print("--load-slot needs 1, 2, or 3.", file=sys.stderr)
            return 2
        slot = normalize_settings_slot(slot)
        ok, msg = apply_user_settings(slot=slot)
        print(msg)
        return 0 if ok else 2
    if "--neutral" in argv:
        ok, msg = reset_to_neutral_settings()
        print(msg)
        return 0 if ok else 2
    if "--save-settings" in argv:
        settings = save_user_settings(1)
        print(f"Saved settings slot 1 to {user_settings_file(1)}")
        print(json.dumps(settings, indent=2))
        return 0
    if "--load-settings" in argv:
        ok, msg = apply_user_settings(slot=1)
        print(msg)
        return 0 if ok else 2
    if "--fix-now" in argv:
        ok, msg = fix_now()
        print(msg)
        return 0 if ok else 2
    if "--swap-default-alt" in argv:
        ok, sink, msg = load_swap(current_master_candidate(), "B")
        print(msg)
        if sink:
            print(f"Swapped sink: {sink}")
        return 0 if ok else 2
    if "--swap-default" in argv:
        ok, sink, msg = load_swap(current_master_candidate(), "A")
        print(msg)
        if sink:
            print(f"Swapped sink: {sink}")
        return 0 if ok else 2
    if "--bass-db" in argv or "--treble-db" in argv:
        def read_number(flag, default=0.0):
            if flag not in argv:
                return default
            try:
                return float(argv[argv.index(flag) + 1])
            except Exception:
                print(f"Missing or invalid number after {flag}", file=sys.stderr)
                return None
        bass_db = read_number("--bass-db", 0.0)
        treble_db = read_number("--treble-db", 0.0)
        if bass_db is None or treble_db is None:
            return 2
        ok, msg = apply_tone_values(bass_db, treble_db)
        print(msg)
        return 0 if ok else 2
    if "--bass" in argv or "--treble" in argv:
        ok, msg = apply_tone("--bass" in argv, "--treble" in argv)
        print(msg)
        return 0 if ok else 2
    if "--tone-off" in argv:
        ok, msg = apply_tone_values(0.0, 0.0)
        print(msg)
        return 0 if ok else 2
    if "--balance" in argv:
        try:
            value = argv[argv.index("--balance") + 1]
        except Exception:
            print("--balance needs a value from 0 to 100. 50 = center.", file=sys.stderr)
            return 2
        ok, msg = apply_balance_value(value)
        print(msg)
        return 0 if ok else 2
    if "--balance-center" in argv:
        ok, msg = apply_balance_value(50)
        print(msg)
        return 0 if ok else 2
    if "--volume" in argv:
        try:
            value = argv[argv.index("--volume") + 1]
        except Exception:
            print("--volume needs a value from 0 to 150.", file=sys.stderr)
            return 2
        ok, msg = apply_system_volume_value(value)
        print(msg)
        return 0 if ok else 2
    if "--test-left" in argv:
        ok, msg = play_test("left")
        print(msg)
        return 0 if ok else 2
    if "--test-right" in argv:
        ok, msg = play_test("right")
        print(msg)
        return 0 if ok else 2
    if "--test-lr" in argv or "--test" in argv:
        ok, msg = play_test("lr")
        print(msg)
        return 0 if ok else 2
    return None


# ----------------------------------- GUI --------------------------------------


# -------------------------- custom dark tone slider ---------------------------

class VolumeStyleSlider(tk.Frame):
    """Dark Pop!_OS-like slider with editable percent/value box."""

    def __init__(
        self,
        master,
        text,
        variable,
        command=None,
        release_command=None,
        from_=0,
        to=100,
        value_formatter=None,
        **kwargs
    ):
        super().__init__(master, bg="#1b1f24", **kwargs)
        self.text = text
        self.variable = variable
        self.command = command
        self.release_command = release_command
        self.from_ = float(from_)
        self.to = float(to)
        self.value_formatter = value_formatter
        self._dragging = False
        self._updating_entry = False

        self.name_label = tk.Label(
            self,
            text=text,
            bg="#1b1f24",
            fg="#e7ecf2",
            font=("Sans", 11, "bold"),
            width=9,
            anchor="w",
        )
        self.name_label.grid(row=0, column=0, padx=(12, 12), pady=10, sticky="w")

        self.canvas = tk.Canvas(
            self,
            height=38,
            bg="#1b1f24",
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.canvas.grid(row=0, column=1, sticky="ew", pady=10)

        self.entry_var = tk.StringVar(value="50")
        self.value_entry = tk.Entry(
            self,
            textvariable=self.entry_var,
            width=5,
            justify="right",
            bg="#111418",
            fg="#e7ecf2",
            insertbackground="#62d6de",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#46505a",
            highlightcolor="#62d6de",
            font=("Sans", 12),
        )
        self.value_entry.grid(row=0, column=2, padx=(14, 8), pady=10, sticky="e")

        self.detail_label = tk.Label(
            self,
            text="Center",
            bg="#1b1f24",
            fg="#9ba7b4",
            font=("Sans", 9),
            width=14,
            anchor="w",
        )
        self.detail_label.grid(row=0, column=3, padx=(0, 12), pady=10, sticky="w")

        self.columnconfigure(1, weight=1)

        self.canvas.bind("<Configure>", lambda _event: self.draw())
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.value_entry.bind("<Return>", self.on_entry_commit)
        self.value_entry.bind("<KP_Enter>", self.on_entry_commit)
        self.value_entry.bind("<FocusOut>", self.on_entry_commit)

        try:
            self.variable.trace_add("write", lambda *_: self.draw())
        except Exception:
            pass

        self.draw()

    def get_value(self):
        try:
            return float(self.variable.get())
        except Exception:
            return self.from_

    def clamp_value(self, value):
        try:
            value = float(value)
        except Exception:
            value = self.get_value()
        return max(self.from_, min(self.to, value))

    def set_value(self, value, live=True, commit=False):
        value = round(self.clamp_value(value))
        self.variable.set(value)
        if live and self.command:
            self.command()
        if commit and self.release_command:
            self.release_command()

    def set_from_x(self, x):
        width = max(1, self.canvas.winfo_width())
        left = 8
        right = max(left + 1, width - 8)
        x = max(left, min(right, x))
        ratio = (x - left) / (right - left)
        value = self.from_ + ratio * (self.to - self.from_)
        self.set_value(value, live=True, commit=False)

    def on_press(self, event):
        self._dragging = True
        self.set_from_x(event.x)

    def on_drag(self, event):
        self.set_from_x(event.x)

    def on_release(self, event):
        self.set_from_x(event.x)
        self._dragging = False
        if self.release_command:
            self.release_command()

    def on_entry_commit(self, _event=None):
        raw = self.entry_var.get().strip().replace("%", "")
        try:
            value = float(raw)
        except Exception:
            value = self.get_value()
        self.set_value(value, live=True, commit=True)
        self.draw()
        return "break"

    def draw(self):
        if not hasattr(self, "canvas"):
            return
        c = self.canvas
        c.delete("all")
        width = max(1, c.winfo_width())
        height = max(1, c.winfo_height())
        left = 8
        right = max(left + 1, width - 8)
        y = height // 2

        value = max(self.from_, min(self.to, self.get_value()))
        ratio = (value - self.from_) / (self.to - self.from_)
        x = left + ratio * (right - left)

        c.create_line(left, y, right, y, fill="#6b7178", width=4)
        c.create_line(left, y, x, y, fill="#62d6de", width=4)

        if self.to == 100 and self.from_ <= 50 <= self.to:
            cx = left + ((50 - self.from_) / (self.to - self.from_)) * (right - left)
            c.create_line(cx, y - 9, cx, y + 9, fill="#9ba7b4", width=2)

        r = 10
        c.create_oval(x - r, y - r, x + r, y + r, fill="#62d6de", outline="#62d6de")

        ivalue = int(round(value))
        # Do not overwrite while the user is typing in the entry box.
        if self.focus_get() is not self.value_entry:
            self.entry_var.set(str(ivalue))

        if self.value_formatter:
            self.detail_label.configure(text=self.value_formatter(ivalue))
        else:
            self.detail_label.configure(text="")

class App(tk.Tk):
    def __init__(self):
        super().__init__(className=APP_ID)
        if not require_pactl(True):
            self.destroy()
            return

        self.title(f"{APP_NAME} v{VERSION}")
        self.apply_window_icon()
        self.geometry("1080x780")
        self.minsize(880, 560)
        self.sinks = []
        self._tone_after_id = None

        state = load_state()
        self.bass_value = tk.DoubleVar(value=db_to_tone_slider_value(state.get("bass_db", 0.0)))
        self.treble_value = tk.DoubleVar(value=db_to_tone_slider_value(state.get("treble_db", 0.0)))
        self.balance_value = tk.DoubleVar(value=clamp_balance(state.get("balance_value", 50)))
        self.system_volume = tk.DoubleVar(value=clamp_system_volume(state.get("system_volume", get_current_output_volume_percent())))
        self.target_text = tk.StringVar(value=f"Target: {get_target_description()}")
        self._tone_after_id = None
        self._volume_after_id = None
        self._balance_after_id = None
        self._tone_applying = False
        self._volume_applying = False
        self._balance_applying = False
        self._volume_poll_after_id = None
        self._last_seen_system_volume = clamp_system_volume(self.system_volume.get())

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.configure(padx=0, pady=0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.setup_style()
        self._section_states = {}
        self._section_bodies = {}

        # General right-side scrollbar for the whole app.
        self.scroll_canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg="#111418")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.page = ttk.Frame(self.scroll_canvas, padding=(14, 12))
        self.page_window = self.scroll_canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.page.columnconfigure(0, weight=1)

        def _on_page_configure(_event=None):
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

        def _on_canvas_configure(event):
            self.scroll_canvas.itemconfigure(self.page_window, width=event.width)

        def _wheel_direction(event):
            # Return -1 for up, +1 for down.
            if getattr(event, "num", None) == 4:
                return -1
            if getattr(event, "num", None) == 5:
                return 1
            delta = getattr(event, "delta", 0)
            if delta > 0:
                return -1
            if delta < 0:
                return 1
            return 0

        def _can_widget_scroll(widget, direction):
            try:
                first, last = widget.yview()
            except Exception:
                return False

            # Tiny tolerance avoids floating-point edge jitter.
            if direction < 0:
                return first > 0.001
            if direction > 0:
                return last < 0.999
            return False

        def _find_inner_scrollable(widget):
            # If the mouse is inside a nested scrollable widget, such as the
            # Audio outputs Treeview, the main/general window must NOT scroll.
            # Even if that inner widget is already at its edge, stop there.
            current = widget
            while current is not None and current is not self.page:
                if current is not self.scroll_canvas and hasattr(current, "yview"):
                    return current
                try:
                    current = current.master
                except Exception:
                    break
            return None

        def _on_mousewheel(event):
            direction = _wheel_direction(event)
            if direction == 0:
                return "break"

            inner = _find_inner_scrollable(event.widget)
            if inner is not None:
                if _can_widget_scroll(inner, direction):
                    inner.yview_scroll(direction * 3, "units")
                # Always block the general window while mouse is inside an
                # inner scrollable widget.
                return "break"

            if _can_widget_scroll(self.scroll_canvas, direction):
                self.scroll_canvas.yview_scroll(direction * 3, "units")
            return "break"

        self.page.bind("<Configure>", _on_page_configure)
        self.scroll_canvas.bind("<Configure>", _on_canvas_configure)
        self.scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.scroll_canvas.bind_all("<Button-4>", _on_mousewheel)
        self.scroll_canvas.bind_all("<Button-5>", _on_mousewheel)

        header = ttk.Frame(self.page)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="L/R Swaper", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Choose a target output first, then swap, tune tone, balance L/R, and control volume. Click section headers to hide/show.",
            style="Subtle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        header_buttons = ttk.Frame(header)
        header_buttons.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(header_buttons, text="Collapse all", command=self.collapse_all_sections).grid(row=0, column=0, padx=(8, 4), pady=2)
        ttk.Button(header_buttons, text="Expand all", command=self.expand_all_sections).grid(row=0, column=1, padx=(4, 4), pady=2)
        ttk.Button(header_buttons, text="Tihuluwave Theme", command=self.switch_to_tihuluwave).grid(row=0, column=2, padx=(4, 0), pady=2)

        outputs = self.make_collapsible_section("Audio outputs", row=1, sticky="ew", pady=(0, 8), expanded=True)
        outputs.columnconfigure(0, weight=1)
        outputs.rowconfigure(0, weight=0)

        columns = ("default", "kind", "output", "state")
        self.tree = ttk.Treeview(outputs, columns=columns, show="headings", height=7, selectmode="browse")
        self.tree.heading("default", text="Default")
        self.tree.heading("kind", text="Type")
        self.tree.heading("output", text="Output")
        self.tree.heading("state", text="State")
        self.tree.column("default", width=80, anchor="center", stretch=False)
        self.tree.column("kind", width=130, anchor="w", stretch=False)
        self.tree.column("output", width=560, anchor="w", stretch=True)
        self.tree.column("state", width=110, anchor="center", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        scroll = ttk.Scrollbar(outputs, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.tree.configure(yscrollcommand=scroll.set)

        controls = self.make_collapsible_section("Controls", row=2, sticky="ew", pady=8, expanded=True)
        for i in range(6):
            controls.columnconfigure(i, weight=1)

        ttk.Button(controls, text="Refresh", command=self.refresh).grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Use selected as target", command=self.use_selected_target_gui).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Swap selected", command=lambda: self.swap_selected("A")).grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Alternate swap", command=lambda: self.swap_selected("B")).grid(row=0, column=3, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Swap target/default", command=self.swap_current_default_gui).grid(row=0, column=4, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Set selected default", command=self.set_selected_default_gui).grid(row=0, column=5, padx=6, pady=6, sticky="ew")
        ttk.Button(controls, text="Fix / move streams", command=self.fix_now_gui).grid(row=1, column=0, padx=6, pady=(0, 6), sticky="ew")
        ttk.Button(controls, text="Disable swap/EQ", command=self.disable_gui).grid(row=1, column=1, padx=6, pady=(0, 6), sticky="ew")
        ttk.Button(controls, text="Diagnostics", command=self.show_diagnostics).grid(row=1, column=2, padx=6, pady=(0, 6), sticky="ew")
        ttk.Label(controls, textvariable=self.target_text, style="Subtle.TLabel").grid(row=1, column=3, columnspan=3, padx=8, pady=(0, 6), sticky="w")

        test_frame = self.make_collapsible_section("L/R audio test", row=3, sticky="ew", pady=8, expanded=False)
        for i in range(5):
            test_frame.columnconfigure(i, weight=0)
        test_frame.columnconfigure(4, weight=1)
        ttk.Button(test_frame, text="Test Left", command=lambda: self.play_test_gui("left")).grid(row=0, column=0, padx=6, pady=8)
        ttk.Button(test_frame, text="Test Right", command=lambda: self.play_test_gui("right")).grid(row=0, column=1, padx=6, pady=8)
        ttk.Button(test_frame, text="L/R Test", command=lambda: self.play_test_gui("lr")).grid(row=0, column=2, padx=6, pady=8)
        ttk.Label(test_frame, text="After swap: Left test should come from the right speaker.", style="Subtle.TLabel").grid(row=0, column=3, columnspan=2, padx=12, pady=8, sticky="w")

        tone = self.make_collapsible_section("Volume / EQ / Presets", row=4, sticky="ew", pady=8, expanded=True)
        tone.columnconfigure(0, weight=1)
        tone.columnconfigure(1, weight=0)

        self.volume_slider = VolumeStyleSlider(
            tone,
            "Volume",
            self.system_volume,
            command=self.schedule_volume_apply,
            release_command=self.apply_volume_gui,
            from_=0,
            to=150,
            value_formatter=format_system_volume,
        )
        self.volume_slider.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="ew")

        self.bass_slider = VolumeStyleSlider(
            tone,
            "Bass",
            self.bass_value,
            command=self.schedule_tone_apply,
            release_command=self.apply_tone_gui,
            from_=0,
            to=100,
            value_formatter=format_tone_slider,
        )
        self.bass_slider.grid(row=1, column=0, padx=10, pady=4, sticky="ew")

        self.treble_slider = VolumeStyleSlider(
            tone,
            "Treble",
            self.treble_value,
            command=self.schedule_tone_apply,
            release_command=self.apply_tone_gui,
            from_=0,
            to=100,
            value_formatter=format_tone_slider,
        )
        self.treble_slider.grid(row=2, column=0, padx=10, pady=4, sticky="ew")

        self.balance_slider = VolumeStyleSlider(
            tone,
            "L / R",
            self.balance_value,
            command=self.schedule_balance_apply,
            release_command=self.apply_balance_gui,
            from_=0,
            to=100,
            value_formatter=format_balance_slider,
        )
        self.balance_slider.grid(row=3, column=0, padx=10, pady=(4, 10), sticky="ew")

        button_box = ttk.Frame(tone)
        button_box.grid(row=0, column=1, rowspan=4, padx=(6, 10), pady=10, sticky="ns")
        button_box.columnconfigure(0, weight=1)
        button_box.columnconfigure(1, weight=1)
        ttk.Button(button_box, text="Apply volume", command=self.apply_volume_gui).grid(row=0, column=0, columnspan=2, padx=0, pady=(0, 8), sticky="ew")
        ttk.Button(button_box, text="Apply tone", command=self.apply_tone_gui).grid(row=1, column=0, columnspan=2, padx=0, pady=(0, 8), sticky="ew")
        ttk.Button(button_box, text="Reset tone to 50", command=self.reset_tone_gui).grid(row=2, column=0, columnspan=2, padx=0, pady=(0, 8), sticky="ew")
        ttk.Button(button_box, text="Apply L/R", command=self.apply_balance_gui).grid(row=3, column=0, columnspan=2, padx=0, pady=(0, 8), sticky="ew")
        ttk.Button(button_box, text="Center L/R", command=self.reset_balance_gui).grid(row=4, column=0, columnspan=2, padx=0, pady=(0, 8), sticky="ew")
        ttk.Button(button_box, text="Neutral", command=self.neutral_gui).grid(row=5, column=0, columnspan=2, padx=0, pady=(0, 10), sticky="ew")

        ttk.Label(button_box, text="Preset slots", style="Subtle.TLabel").grid(row=6, column=0, columnspan=2, padx=0, pady=(0, 4), sticky="ew")
        ttk.Button(button_box, text="Save 1", command=lambda: self.save_settings_gui(1)).grid(row=7, column=0, padx=(0, 4), pady=(0, 6), sticky="ew")
        ttk.Button(button_box, text="Load 1", command=lambda: self.load_settings_gui(1)).grid(row=7, column=1, padx=(4, 0), pady=(0, 6), sticky="ew")
        ttk.Button(button_box, text="Save 2", command=lambda: self.save_settings_gui(2)).grid(row=8, column=0, padx=(0, 4), pady=(0, 6), sticky="ew")
        ttk.Button(button_box, text="Load 2", command=lambda: self.load_settings_gui(2)).grid(row=8, column=1, padx=(4, 0), pady=(0, 6), sticky="ew")
        ttk.Button(button_box, text="Save 3", command=lambda: self.save_settings_gui(3)).grid(row=9, column=0, padx=(0, 4), pady=0, sticky="ew")
        ttk.Button(button_box, text="Load 3", command=lambda: self.load_settings_gui(3)).grid(row=9, column=1, padx=(4, 0), pady=0, sticky="ew")
        ttk.Label(
            tone,
            text="Sliders apply live. Type values or drag sliders. Preset load temporarily mutes app streams during rebuild to prevent loud bursts.",
            style="Subtle.TLabel",
        ).grid(row=4, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

        self.status = ttk.Label(self.page, anchor="w", wraplength=920, style="Status.TLabel")
        self.status.grid(row=5, column=0, sticky="ew", pady=(8, 0))

        self.update_tone_labels()
        self.refresh()
        self.start_volume_polling()

    def switch_to_tihuluwave(self):
        save_theme_name(THEME_TIHULUWAVE)
        self.set_status("Switching to Tihuluwave Theme...")
        restart_launcher()

    def make_collapsible_section(self, title, row, sticky="ew", pady=8, expanded=True):
        """Create a click-to-hide section and return its content body frame."""
        outer = ttk.Frame(self.page)
        outer.grid(row=row, column=0, sticky=sticky, pady=pady)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        state = tk.BooleanVar(value=bool(expanded))
        label_var = tk.StringVar()
        body = ttk.Frame(outer)
        body.grid(row=1, column=0, sticky="nsew")

        def refresh_label():
            label_var.set(("▾  " if state.get() else "▸  ") + title)

        def toggle():
            state.set(not state.get())
            if state.get():
                body.grid()
            else:
                body.grid_remove()
            refresh_label()

        header_btn = ttk.Button(
            outer,
            textvariable=label_var,
            command=toggle,
            style="Section.TButton",
        )
        header_btn.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        refresh_label()
        if not state.get():
            body.grid_remove()

        self._section_states[title] = state
        self._section_bodies[title] = body
        return body

    def expand_all_sections(self):
        for title, state in self._section_states.items():
            state.set(True)
            body = self._section_bodies.get(title)
            if body:
                body.grid()

    def collapse_all_sections(self):
        for title, state in self._section_states.items():
            state.set(False)
            body = self._section_bodies.get(title)
            if body:
                body.grid_remove()

    def setup_style(self):
        try:
            style = ttk.Style(self)
            if "clam" in style.theme_names():
                style.theme_use("clam")

            bg = "#111418"
            panel = "#1b1f24"
            panel2 = "#20262d"
            fg = "#e7ecf2"
            subtle = "#9ba7b4"
            border = "#323942"
            accent = "#62d6de"
            selected = "#263f52"

            self.configure(bg=bg)

            default_font = ("Sans", 10)
            style.configure(".", background=bg, foreground=fg, fieldbackground=panel, font=default_font)
            style.configure("TFrame", background=bg)
            style.configure("TLabel", background=bg, foreground=fg, font=default_font)
            style.configure("TButton", background=panel2, foreground=fg, font=default_font, padding=(9, 6), borderwidth=1)
            style.map("TButton", background=[("active", "#2b333c")], foreground=[("active", fg)])
            style.configure("Section.TButton", background=panel2, foreground=fg, font=("Sans", 11, "bold"), padding=(10, 7), anchor="w")
            style.map("Section.TButton", background=[("active", "#2b333c")], foreground=[("active", fg)])
            style.configure("TLabelframe", background=bg, foreground=fg, bordercolor=border, relief="solid", padding=(8, 6))
            style.configure("TLabelframe.Label", background=bg, foreground=fg, font=("Sans", 10, "bold"))
            style.configure("Title.TLabel", background=bg, foreground=fg, font=("Sans", 20, "bold"))
            style.configure("Subtle.TLabel", background=bg, foreground=subtle, font=("Sans", 10))
            style.configure("Status.TLabel", background=bg, foreground=fg, font=("Sans", 10))
            style.configure("Treeview", background=panel, fieldbackground=panel, foreground=fg, rowheight=30, font=("Sans", 10), borderwidth=0)
            style.configure("Treeview.Heading", background=panel2, foreground=fg, font=("Sans", 10, "bold"), relief="flat")
            style.map("Treeview", background=[("selected", selected)], foreground=[("selected", fg)])
        except Exception:
            pass

    def apply_window_icon(self):
        try:
            if APP_ICON_PATH.exists():
                self._dock_icon = tk.PhotoImage(file=str(APP_ICON_PATH))
                self.iconphoto(True, self._dock_icon)
            try:
                self.wm_iconname(APP_NAME)
            except Exception:
                pass
        except Exception:
            pass

    def set_status(self, text):
        self.status.configure(text=text)

    def update_tone_labels(self):
        # Custom slider widgets redraw themselves through variable traces.
        pass

    def refresh(self):
        try:
            self.sinks = all_sinks()
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))
            return

        self.tree.delete(*self.tree.get_children())
        selected_iid = None
        for i, s in enumerate(self.sinks):
            iid = str(i)
            if s["is_eq"]:
                kind = "Tone/EQ"
            elif s["is_app"]:
                kind = "Swapped"
            elif s["name"].startswith("bluez_output."):
                kind = "Bluetooth"
            elif "usb" in s["name"].lower():
                kind = "USB"
            elif "hdmi" in s["description"].lower() or "nvidia" in s["description"].lower() or "radeon" in s["description"].lower():
                kind = "HDMI/Display"
            else:
                kind = "System"
            default = "★" if s["is_default"] else ""
            self.tree.insert("", "end", iid=iid, values=(default, kind, s["description"], s["state"]))
            if s["is_default"]:
                selected_iid = iid

        if selected_iid is None and self.sinks:
            selected_iid = "0"
        if selected_iid is not None:
            self.tree.selection_set(selected_iid)
            self.tree.focus(selected_iid)
            self.tree.see(selected_iid)
        self.target_text.set(f"Target: {get_target_description()}")
        self.set_status("Ready. Click section headers to hide/show panels. When mouse is inside a scrollable inner panel, the general window will not scroll.")

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(APP_NAME, "Select an output first.")
            return None
        try:
            return self.sinks[int(sel[0])]
        except Exception:
            messagebox.showwarning(APP_NAME, "Select an output first.")
            return None

    def use_selected_target_gui(self):
        s = self.selected()
        if not s:
            return
        ok, msg = remember_target_sink(s["name"])
        self.target_text.set(f"Target: {get_target_description()}")
        self.refresh()
        if ok:
            self.set_status(msg + " EQ/swap/volume will stay on this device.")
        else:
            messagebox.showerror(APP_NAME, msg)

    def swap_selected(self, mode):
        s = self.selected()
        if not s:
            return
        master = s["name"]
        if not is_our_sink(master):
            remember_target_sink(master)
            self.target_text.set(f"Target: {get_target_description()}")
        if is_our_sink(master):
            master = current_master_candidate()
        ok, sink_name, msg = load_swap(master, mode)
        self.refresh()
        if not ok:
            messagebox.showerror(APP_NAME, msg)
        else:
            self.set_status(f"{msg} Mode {mode}. Swapped sink: {sink_name}")

    def swap_current_default_gui(self):
        master = current_master_candidate()
        ok, sink_name, msg = load_swap(master, "A")
        self.refresh()
        if not ok:
            messagebox.showerror(APP_NAME, msg)
        else:
            self.set_status(f"{msg} Swapped current default: {sink_name}")

    def set_selected_default_gui(self):
        s = self.selected()
        if not s:
            return
        if not is_our_sink(s["name"]):
            remember_target_sink(s["name"])
            self.target_text.set(f"Target: {get_target_description()}")
        ok, msg = set_default_and_move(s["name"])
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            messagebox.showerror(APP_NAME, msg)

    def fix_now_gui(self):
        ok, msg = fix_now()
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            messagebox.showerror(APP_NAME, msg)

    def disable_gui(self):
        count, msg = restore_output_and_unload()
        self.bass_value.set(50)
        self.treble_value.set(50)
        self.balance_value.set(50)
        self.system_volume.set(get_current_output_volume_percent())
        self.update_tone_labels()
        self.target_text.set(f"Target: {get_target_description()}")
        self.refresh()
        self.set_status(msg or f"Disabled {count} {APP_NAME} module(s).")

    def play_test_gui(self, which):
        ok, msg = play_test(which)
        if ok:
            self.set_status(msg)
        else:
            messagebox.showerror(APP_NAME, msg)

    def apply_tone_gui(self):
        if self._tone_applying:
            return
        self._tone_applying = True
        try:
            self.update_tone_labels()
            if not get_target_sink():
                s = self.selected()
                if s and not is_our_sink(s["name"]):
                    remember_target_sink(s["name"])
                    self.target_text.set(f"Target: {get_target_description()}")
            ok, msg = apply_tone_values(
                tone_slider_value_to_db(self.bass_value.get()),
                tone_slider_value_to_db(self.treble_value.get()),
            )
            if ok:
                state = load_state()
                self.bass_value.set(db_to_tone_slider_value(state.get("bass_db", 0.0)))
                self.treble_value.set(db_to_tone_slider_value(state.get("treble_db", 0.0)))
                self.system_volume.set(clamp_system_volume(state.get("system_volume", self.system_volume.get())))
                self.update_tone_labels()
                self.target_text.set(f"Target: {get_target_description()}")
                self.set_status(msg)
            else:
                state = load_state()
                self.bass_value.set(db_to_tone_slider_value(state.get("bass_db", 0.0)))
                self.treble_value.set(db_to_tone_slider_value(state.get("treble_db", 0.0)))
                self.update_tone_labels()
                messagebox.showerror(APP_NAME, msg)
        finally:
            self._tone_applying = False

    def reset_tone_gui(self):
        self.bass_value.set(50)
        self.treble_value.set(50)
        self.update_tone_labels()
        self.apply_tone_gui()

    def schedule_tone_apply(self):
        self.update_tone_labels()
        if self._tone_after_id:
            try:
                self.after_cancel(self._tone_after_id)
            except Exception:
                pass
        self._tone_after_id = self.after(160, self.apply_tone_gui)

    def schedule_volume_apply(self):
        if self._volume_after_id:
            try:
                self.after_cancel(self._volume_after_id)
            except Exception:
                pass
        self._volume_after_id = self.after(60, self.apply_volume_gui)

    def schedule_balance_apply(self):
        if self._balance_after_id:
            try:
                self.after_cancel(self._balance_after_id)
            except Exception:
                pass
        self._balance_after_id = self.after(80, self.apply_balance_gui)

    def apply_volume_gui(self):
        if self._volume_applying:
            return
        self._volume_applying = True
        try:
            ok, msg = apply_system_volume_value(self.system_volume.get())
            if ok:
                self._last_seen_system_volume = clamp_system_volume(self.system_volume.get())
                self.set_status(msg)
            else:
                state = load_state()
                self.system_volume.set(clamp_system_volume(state.get("system_volume", get_current_output_volume_percent())))
                messagebox.showerror(APP_NAME, msg)
        finally:
            self._volume_applying = False

    def apply_balance_gui(self):
        if self._balance_applying:
            return
        self._balance_applying = True
        try:
            ok, msg = apply_balance_value(self.balance_value.get())
            if ok:
                self.system_volume.set(clamp_system_volume(load_state().get("system_volume", get_current_output_volume_percent())))
                self.set_status(msg)
            else:
                state = load_state()
                self.balance_value.set(clamp_balance(state.get("balance_value", 50)))
                messagebox.showerror(APP_NAME, msg)
        finally:
            self._balance_applying = False

    def reset_balance_gui(self):
        self.balance_value.set(50)
        self.apply_balance_gui()

    def start_volume_polling(self):
        if self._volume_poll_after_id:
            try:
                self.after_cancel(self._volume_poll_after_id)
            except Exception:
                pass
        self._volume_poll_after_id = self.after(900, self.poll_external_volume_change)

    def volume_entry_has_focus(self):
        slider = getattr(self, "volume_slider", None)
        if slider is None:
            return False
        try:
            return self.focus_get() is slider.value_entry
        except Exception:
            return False

    def poll_external_volume_change(self):
        """Refresh volume slider if system/OS volume changed outside the app."""
        try:
            if not self._volume_applying and not self.volume_entry_has_focus():
                slider = getattr(self, "volume_slider", None)
                dragging = bool(getattr(slider, "_dragging", False)) if slider else False

                if not dragging:
                    actual = clamp_system_volume(get_app_control_volume_percent())
                    shown = clamp_system_volume(self.system_volume.get())

                    if abs(actual - shown) >= 1:
                        self.system_volume.set(actual)
                        self._last_seen_system_volume = actual

                        state = load_state()
                        state["system_volume"] = actual
                        save_state(state)

                        self.refresh_slider_widgets()
        finally:
            try:
                self._volume_poll_after_id = self.after(900, self.poll_external_volume_change)
            except Exception:
                pass

    def refresh_slider_widgets(self):
        """Force slider graphics and typed number boxes to show current variables."""
        for slider_name in ("volume_slider", "bass_slider", "treble_slider", "balance_slider"):
            slider = getattr(self, slider_name, None)
            if slider is not None:
                try:
                    slider.draw()
                except Exception:
                    pass

    def sync_ui_from_state(self):
        state = load_state()
        self.system_volume.set(clamp_system_volume(state.get("system_volume", 100)))
        self.bass_value.set(db_to_tone_slider_value(state.get("bass_db", 0.0)))
        self.treble_value.set(db_to_tone_slider_value(state.get("treble_db", 0.0)))
        self.balance_value.set(clamp_balance(state.get("balance_value", 50)))
        self.target_text.set(f"Target: {get_target_description()}")
        self.refresh_slider_widgets()

    def neutral_gui(self):
        ok, msg = reset_to_neutral_settings()
        self.sync_ui_from_state()
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            messagebox.showerror(APP_NAME, msg)

    def save_settings_gui(self, slot=1):
        slot = normalize_settings_slot(slot)

        # Presets are volume-independent. Do not apply/store volume here.
        # The other sliders are live, but we copy current UI values into state so
        # typed values that were just committed are captured in the preset.
        state = load_state()
        state["balance_value"] = clamp_balance(self.balance_value.get())
        state["bass_db"] = tone_slider_value_to_db(self.bass_value.get())
        state["treble_db"] = tone_slider_value_to_db(self.treble_value.get())
        state["volume_independent_presets"] = True
        save_state(state)

        settings = save_user_settings(slot)
        self.sync_ui_from_state()
        target = settings.get("target_description") or settings.get("target_sink_name") or "none"
        self.set_status(f"Saved preset slot {slot} without volume. Target: {target}.")

    def load_settings_gui(self, slot=1):
        slot = normalize_settings_slot(slot)
        ok, msg = apply_user_settings(slot=slot)
        self.sync_ui_from_state()
        self.refresh()
        self.sync_ui_from_state()
        if ok:
            self.set_status(msg)
        else:
            messagebox.showerror(APP_NAME, msg)

    def on_close(self):
        # Closing the window should not leave virtual swap/EQ sinks running.
        if self._volume_poll_after_id:
            try:
                self.after_cancel(self._volume_poll_after_id)
            except Exception:
                pass
        restore_output_and_unload()
        self.destroy()

    def show_diagnostics(self):
        win = tk.Toplevel(self)
        win.title(f"{APP_NAME} Diagnostics")
        win.geometry("940x680")
        text = tk.Text(win, wrap="none")
        text.pack(fill="both", expand=True)
        text.insert("1.0", diagnostics())
        text.configure(state="disabled")


def main():
    cli_result = cli(sys.argv[1:])
    if cli_result is not None:
        sys.exit(cli_result)
    if not HAS_TK:
        print("Tkinter is not available. Install it with: sudo apt install python3-tk", file=sys.stderr)
        print("CLI examples: lr-swaper --neutral | --save-slot 1 | --load-slot 1 | --save-slot 2 | --load-slot 2 | --status")
        sys.exit(2)
    App().mainloop()


if __name__ == "__main__":
    main()
