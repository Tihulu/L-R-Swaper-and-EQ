#!/usr/bin/env python3
"""
L/R Swaper Linux backend v4.9

Small PipeWire/PulseAudio-compatible backend used by the GitHub quick install.
It provides CLI commands and shared functions for the Tihuluwave Qt UI.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

APP_NAME = "L/R Swaper"
VERSION = "4.9"
APP_ID = "lr-swaper"
REPOSITORY_URL = "https://github.com/Tihulu/L-R-Swaper-and-EQ"
THEME_PLAIN = "Plain Theme"
THEME_TIHULUWAVE = "Tihuluwave Theme"

STATE_DIR = Path.home() / ".config" / APP_ID
STATE_FILE = STATE_DIR / "state.json"
THEME_FILE = STATE_DIR / "theme.json"
CACHE_DIR = Path.home() / ".cache" / APP_ID
SINK_PREFIX = "lr_swaper_"
EQ_PREFIX = "lr_swaper_eq_"
LEGACY_PREFIXES = ("bt_lr_swapper_", "lr_swaper_", "lr_swaper_eq_")


def run_cmd(args):
    try:
        proc = subprocess.run(args, text=True, capture_output=True)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {args[0]}"


def have(cmd):
    return shutil.which(cmd) is not None


def require_pactl(gui=False):
    if have("pactl"):
        return True
    msg = "pactl is missing. Install it with: sudo apt install pulseaudio-utils"
    if gui:
        try:
            from tkinter import messagebox
            messagebox.showerror(APP_NAME, msg)
        except Exception:
            print(msg, file=sys.stderr)
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


def save_theme_name(theme):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    THEME_FILE.write_text(json.dumps({"theme": theme}, indent=2))


def clear_state():
    try:
        STATE_FILE.unlink()
    except Exception:
        pass


def default_sink():
    code, out, _ = run_cmd(["pactl", "get-default-sink"])
    return out if code == 0 else ""


def list_sink_inputs():
    code, out, _ = run_cmd(["pactl", "list", "short", "sink-inputs"])
    if code != 0 or not out:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if parts:
            rows.append(parts[0])
    return rows


def sink_descriptions():
    code, out, _ = run_cmd(["pactl", "list", "sinks"])
    desc = {}
    if code != 0:
        return desc
    current = ""
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Name:"):
            current = s.split("Name:", 1)[1].strip()
        elif s.startswith("Description:") and current:
            desc[current] = s.split("Description:", 1)[1].strip()
    return desc


def sink_names():
    code, out, _ = run_cmd(["pactl", "list", "short", "sinks"])
    if code != 0 or not out:
        return []
    return [line.split()[1] for line in out.splitlines() if len(line.split()) > 1]


def sink_exists(name):
    return bool(name) and name in sink_names()


def is_our_sink(name):
    return any(str(name).startswith(prefix) for prefix in LEGACY_PREFIXES)


def all_sinks():
    default = default_sink()
    desc = sink_descriptions()
    result = []
    for name in sink_names():
        result.append({
            "name": name,
            "description": desc.get(name, name),
            "is_default": name == default,
            "is_app": name.startswith(SINK_PREFIX),
            "is_eq": name.startswith(EQ_PREFIX),
        })
    return result


def current_master_candidate():
    state = load_state()
    for key in ("target_sink_name", "master_name", "previous_default"):
        val = state.get(key)
        if val and sink_exists(val) and not is_our_sink(val):
            return val
    d = default_sink()
    if d and not is_our_sink(d):
        return d
    for sink in sink_names():
        if not is_our_sink(sink):
            return sink
    return ""


def remember_target_sink(sink_name):
    if not sink_name:
        return False, "No output selected."
    if not sink_exists(sink_name):
        return False, f"Selected output does not exist: {sink_name}"
    if is_our_sink(sink_name):
        return False, "Select a real output device, not an L/R Swaper virtual output."
    state = load_state()
    desc = sink_descriptions().get(sink_name, sink_name)
    state["target_sink_name"] = sink_name
    state["target_description"] = desc
    state["master_name"] = sink_name
    state["previous_default"] = sink_name
    save_state(state)
    return True, f"Target device set to: {desc}"


def get_target_sink():
    state = load_state()
    target = state.get("target_sink_name") or state.get("master_name")
    if target and sink_exists(target) and not is_our_sink(target):
        return target
    return ""


def get_target_description():
    target = get_target_sink()
    if not target:
        return "No target selected"
    state = load_state()
    return state.get("target_description") or sink_descriptions().get(target, target)


def set_default_and_move(sink_name):
    if not sink_name:
        return False, "No sink selected."
    code, _, err = run_cmd(["pactl", "set-default-sink", sink_name])
    if code != 0:
        return False, err or "Could not set default sink."
    moved = 0
    for stream in list_sink_inputs():
        run_cmd(["pactl", "move-sink-input", stream, sink_name])
        moved += 1
    return True, f"Default output set. Moved {moved} active stream(s)."


def app_modules():
    state = load_state()
    mods = []
    for key in ("swap_module", "eq_module"):
        if state.get(key):
            mods.append(str(state[key]))
    code, out, _ = run_cmd(["pactl", "list", "short", "modules"])
    if code == 0:
        for line in out.splitlines():
            if "lr_swaper" in line or "bt_lr_swapper" in line:
                parts = line.split()
                if parts:
                    mods.append(parts[0])
    return sorted(set(mods))


def unload_modules(modules=None):
    for mid in modules or app_modules():
        run_cmd(["pactl", "unload-module", str(mid)])


def restore_output_and_unload():
    state = load_state()
    target = state.get("target_sink_name") or state.get("master_name") or state.get("previous_default") or current_master_candidate()
    unload_modules()
    if target and sink_exists(target) and not is_our_sink(target):
        set_default_and_move(target)
    clear_state()
    if target:
        remember_target_sink(target)
    return True, "L/R Swaper disabled and output restored."


def remove_swap_preserving_settings():
    state = load_state()
    target = state.get("target_sink_name") or current_master_candidate()
    if state.get("swap_module"):
        run_cmd(["pactl", "unload-module", str(state["swap_module"])])
    state.pop("swap_module", None)
    state.pop("swapped_sink_name", None)
    save_state(state)
    if target:
        set_default_and_move(target)
    return True, "Swap disabled."


def load_swap(master_name=None, mode="A"):
    if not require_pactl():
        return False, "", "pactl is missing."
    master = master_name or get_target_sink() or current_master_candidate()
    if not master or not sink_exists(master) or is_our_sink(master):
        return False, "", "Select a real output first."
    mode = (mode or "A").upper()
    unload_modules()
    name = f"{SINK_PREFIX}{mode.lower()}_{abs(hash(master + mode)) % 1000000}"
    desc = "L/R Swaper"
    args = [
        "pactl", "load-module", "module-remap-sink",
        f"sink_name={name}",
        f"master={master}",
        "channels=2",
        "channel_map=front-left,front-right",
        "master_channel_map=front-right,front-left",
        "remix=no",
        f"sink_properties=device.description={desc}",
    ]
    code, out, err = run_cmd(args)
    if code != 0:
        return False, "", err or "Could not create swapped output."
    state = load_state()
    state.update({
        "target_sink_name": master,
        "target_description": sink_descriptions().get(master, master),
        "master_name": master,
        "previous_default": master,
        "swap_module": out.strip(),
        "swapped_sink_name": name,
        "mode": mode,
    })
    save_state(state)
    set_default_and_move(name)
    return True, name, f"Swap {mode} enabled."


def clamp_system_volume(value):
    try:
        return max(0, min(150, float(value)))
    except Exception:
        return 100.0


def clamp_balance(value):
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return 50


def get_current_output_volume_percent():
    sink = default_sink()
    code, out, _ = run_cmd(["pactl", "get-sink-volume", sink]) if sink else (1, "", "")
    m = re.search(r"(\d+)%", out)
    return clamp_system_volume(m.group(1)) if m else 100.0


def apply_system_volume_value(value, sink_name=None):
    vol = int(round(clamp_system_volume(value)))
    sink = sink_name or default_sink() or current_master_candidate()
    if not sink:
        return False, "No output available."
    code, _, err = run_cmd(["pactl", "set-sink-volume", sink, f"{vol}%", f"{vol}%"])
    state = load_state()
    state["system_volume"] = vol
    save_state(state)
    return code == 0, f"Volume set to {vol}%." if code == 0 else err


def apply_balance_value(value, sink_name=None):
    bal = clamp_balance(value)
    sink = sink_name or default_sink() or current_master_candidate()
    if not sink:
        return False, "No output available."
    total = clamp_system_volume(load_state().get("system_volume", get_current_output_volume_percent()))
    if bal < 50:
        left = total
        right = total * (bal / 50.0)
    else:
        left = total * ((100 - bal) / 50.0)
        right = total
    code, _, err = run_cmd(["pactl", "set-sink-volume", sink, f"{int(left)}%", f"{int(right)}%"])
    state = load_state()
    state["balance_value"] = bal
    save_state(state)
    return code == 0, f"Balance set to {format_balance_slider(bal)}." if code == 0 else err


def format_balance_slider(value):
    value = clamp_balance(value)
    if value == 50:
        return "Center"
    if value < 50:
        return f"L {100 - value * 2}%"
    return f"R {(value - 50) * 2}%"


def tone_slider_value_to_db(value):
    try:
        value = float(value)
    except Exception:
        value = 50
    return round((value - 50.0) / 5.0, 1)


def db_to_tone_slider_value(db):
    try:
        db = float(db)
    except Exception:
        db = 0
    return int(max(0, min(100, round(50 + db * 5))))


def apply_tone_values(bass_db=0, treble_db=0):
    state = load_state()
    state["bass_db"] = float(bass_db or 0)
    state["treble_db"] = float(treble_db or 0)
    save_state(state)
    return True, f"Tone saved: bass {bass_db:+.1f} dB, treble {treble_db:+.1f} dB."


def reset_to_neutral_settings():
    state = load_state()
    target = state.get("target_sink_name") or current_master_candidate()
    restore_output_and_unload()
    if target and sink_exists(target):
        remember_target_sink(target)
        apply_balance_value(50, target)
    return True, "Neutral settings applied."


def fix_now():
    sink = default_sink()
    if not sink:
        return False, "No default output."
    return set_default_and_move(sink)


def diagnostics():
    lines = [
        f"{APP_NAME} v{VERSION}",
        f"Repository: {REPOSITORY_URL}",
        f"Default sink: {default_sink()}",
        f"Target: {get_target_description()}",
        "Sinks:",
    ]
    for s in all_sinks():
        mark = "*" if s["is_default"] else " "
        lines.append(f" {mark} {s['description']}  [{s['name']}]")
    return "\n".join(lines)


def _tone_file(channel):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"test_{channel}.wav"
    rate = 44100
    dur = 0.35
    freq = 660 if channel == "left" else 880
    n = int(rate * dur)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            amp = int(16000 * math.sin(2 * math.pi * freq * i / rate))
            l = amp if channel in ("left", "both") else 0
            r = amp if channel in ("right", "both") else 0
            frames += int(l).to_bytes(2, "little", signed=True)
            frames += int(r).to_bytes(2, "little", signed=True)
        wf.writeframes(frames)
    return path


def play_test(side="both"):
    side = {"lr": "both"}.get(side, side)
    if side not in ("left", "right", "both"):
        side = "both"
    path = _tone_file(side)
    if have("paplay"):
        subprocess.Popen(["paplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"Playing {side} test."
    return False, "paplay is missing. Install pulseaudio-utils."


def save_user_settings(slot=1):
    slot = max(1, min(3, int(slot or 1)))
    data = load_state()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / f"saved_settings_{slot}.json").write_text(json.dumps(data, indent=2))
    return data


def apply_user_settings(settings=None, slot=1):
    slot = max(1, min(3, int(slot or 1)))
    path = STATE_DIR / f"saved_settings_{slot}.json"
    try:
        data = settings or json.loads(path.read_text())
    except Exception:
        return False, f"No saved preset in slot {slot}."
    save_state(data)
    target = data.get("target_sink_name") or current_master_candidate()
    if target and sink_exists(target):
        set_default_and_move(target)
    return True, f"Loaded preset slot {slot}."


def cli(argv=None):
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{VERSION}")
    parser.add_argument("--swap-default", action="store_true")
    parser.add_argument("--swap-default-alt", action="store_true")
    parser.add_argument("--fix-now", action="store_true")
    parser.add_argument("--test-left", action="store_true")
    parser.add_argument("--test-right", action="store_true")
    parser.add_argument("--test-lr", action="store_true")
    parser.add_argument("--volume", type=float)
    parser.add_argument("--balance", type=int)
    parser.add_argument("--balance-center", action="store_true")
    parser.add_argument("--bass-db", type=float)
    parser.add_argument("--treble-db", type=float)
    parser.add_argument("--tone-off", action="store_true")
    parser.add_argument("--save-slot", type=int)
    parser.add_argument("--load-slot", type=int)
    parser.add_argument("--neutral", action="store_true")
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)

    if args.status:
        print(diagnostics()); return 0
    if args.disable:
        print(restore_output_and_unload()[1]); return 0
    if args.neutral:
        print(reset_to_neutral_settings()[1]); return 0
    if args.fix_now:
        print(fix_now()[1]); return 0
    if args.swap_default:
        print(load_swap(mode="A")[2]); return 0
    if args.swap_default_alt:
        print(load_swap(mode="B")[2]); return 0
    if args.test_left:
        print(play_test("left")[1]); return 0
    if args.test_right:
        print(play_test("right")[1]); return 0
    if args.test_lr:
        print(play_test("both")[1]); return 0
    if args.volume is not None:
        print(apply_system_volume_value(args.volume)[1]); return 0
    if args.balance is not None:
        print(apply_balance_value(args.balance)[1]); return 0
    if args.balance_center:
        print(apply_balance_value(50)[1]); return 0
    if args.tone_off:
        print(apply_tone_values(0, 0)[1]); return 0
    if args.bass_db is not None or args.treble_db is not None:
        print(apply_tone_values(args.bass_db or 0, args.treble_db or 0)[1]); return 0
    if args.save_slot:
        save_user_settings(args.save_slot); print(f"Saved preset slot {args.save_slot}."); return 0
    if args.load_slot:
        print(apply_user_settings(slot=args.load_slot)[1]); return 0

    print(diagnostics())
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
