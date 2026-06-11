#!/usr/bin/env python3
"""
L/R Swaper Mac — Apple Silicon standalone-friendly version.

User-facing workflow:
    Choose real output -> Start -> EQ / L-R controls

Hidden routing:
    macOS Output -> BlackHole 2ch -> app -> selected output

This is not a kernel/system audio driver. BlackHole 2ch is still required once.
"""

from __future__ import annotations

import datetime
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

APP_NAME = "L/R Swaper Mac"
VERSION = "2.4-mac-scrollbar"

# Finder-launched apps do not inherit Terminal PATH.
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + os.environ.get("PATH", "")

APP_DIR = Path.home() / "Library" / "Application Support" / "LR Swaper Mac"
STATE_FILE = APP_DIR / "state.json"
LOG_FILE = APP_DIR / "app.log"
PRESET_FILES = [
    APP_DIR / "preset_1.json",
    APP_DIR / "preset_2.json",
    APP_DIR / "preset_3.json",
]

try:
    import numpy as np
except Exception:
    np = None

try:
    import sounddevice as sd
except Exception:
    sd = None


# ------------------------------ logging ------------------------------------

def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def log_line(message: str) -> None:
    try:
        ensure_app_dir()
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with LOG_FILE.open("a") as f:
            f.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def log_exception(prefix: str, exc: BaseException) -> None:
    try:
        ensure_app_dir()
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with LOG_FILE.open("a") as f:
            f.write(f"\n[{stamp}] {prefix}: {exc}\n")
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass


def bundled_resource_path(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


# ------------------------------ SwitchAudioSource --------------------------

def switch_audio_source_cmd() -> str:
    """Return the real or bundled SwitchAudioSource helper path."""
    candidates = [
        shutil.which("SwitchAudioSource"),
        "/opt/homebrew/bin/SwitchAudioSource",
        "/usr/local/bin/SwitchAudioSource",
        bundled_resource_path("SwitchAudioSource"),
        bundled_resource_path("bin/SwitchAudioSource"),
    ]
    for c in candidates:
        if c and Path(str(c)).exists():
            return str(c)
    return ""


def run_switch_audio(args):
    cmd = switch_audio_source_cmd()
    if not cmd:
        return 127, "", "SwitchAudioSource not found. Run Install Required Audio Driver.command from the DMG."
    try:
        log_line("SwitchAudioSource: " + " ".join([cmd] + list(args)))
        p = subprocess.run([cmd] + list(args), text=True, capture_output=True, timeout=8)
        if p.returncode != 0:
            log_line(f"SwitchAudioSource failed rc={p.returncode} stdout={p.stdout.strip()} stderr={p.stderr.strip()}")
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as exc:
        log_exception("SwitchAudioSource exception", exc)
        return 1, "", str(exc)


def current_system_output_name() -> str:
    code, out, err = run_switch_audio(["-c", "-t", "output"])
    return out.strip() if code == 0 else ""


def list_system_outputs() -> list[str]:
    code, out, err = run_switch_audio(["-a", "-t", "output"])
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def find_blackhole_system_output() -> str:
    outputs = list_system_outputs()
    for name in outputs:
        lower = name.lower()
        if "blackhole" in lower and ("2ch" in lower or "2 ch" in lower or "2" in lower):
            return name
    for name in outputs:
        if "blackhole" in name.lower():
            return name
    return ""


def set_system_output_name(name: str):
    if not name:
        return False, "No output name provided."
    code, out, err = run_switch_audio(["-s", name, "-t", "output"])
    if code == 0:
        return True, out or f"System output set to {name}"
    return False, err or out or f"Could not set system output to {name}"


def current_system_input_name() -> str:
    code, out, err = run_switch_audio(["-c", "-t", "input"])
    return out.strip() if code == 0 else ""


def list_system_inputs() -> list[str]:
    code, out, err = run_switch_audio(["-a", "-t", "input"])
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def find_blackhole_system_input() -> str:
    inputs = list_system_inputs()
    for name in inputs:
        lower = name.lower()
        if "blackhole" in lower and ("2ch" in lower or "2 ch" in lower or "2" in lower):
            return name
    for name in inputs:
        if "blackhole" in name.lower():
            return name
    return ""


def set_system_input_name(name: str):
    if not name:
        return False, "No input name provided."
    code, out, err = run_switch_audio(["-s", name, "-t", "input"])
    if code == 0:
        return True, out or f"System input set to {name}"
    return False, err or out or f"Could not set system input to {name}"


def osascript(script: str):
    try:
        p = subprocess.run(["osascript", "-e", script], text=True, capture_output=True, timeout=8)
        if p.returncode != 0:
            log_line(f"osascript failed rc={p.returncode} stdout={p.stdout.strip()} stderr={p.stderr.strip()}")
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as exc:
        log_exception("osascript exception", exc)
        return 1, "", str(exc)


def get_system_input_volume() -> int | None:
    code, out, err = osascript("input volume of (get volume settings)")
    if code != 0:
        return None
    try:
        return int(float(out.strip()))
    except Exception:
        return None


def set_system_input_volume(value: int):
    value = max(0, min(100, int(value)))
    code, out, err = osascript(f"set volume input volume {value}")
    if code == 0:
        return True, f"macOS input volume set to {value}"
    return False, err or out or "Could not set macOS input volume"


def open_microphone_privacy_settings():
    # Newer macOS URL. If it fails, user can still open manually.
    try:
        subprocess.run(
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"],
            timeout=3,
        )
        return True, "Opened Microphone privacy settings."
    except Exception as exc:
        log_exception("Could not open microphone privacy settings", exc)
        return False, str(exc)


# ------------------------------ persistence / math --------------------------

def load_json(path: Path, default: dict | None = None) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict) -> None:
    ensure_app_dir()
    path.write_text(json.dumps(data, indent=2))


def clamp(value: float, lo: float, hi: float) -> float:
    try:
        value = float(value)
    except Exception:
        value = lo
    return max(lo, min(hi, value))


def clean_device_display_name(display: str) -> str:
    if ":" in str(display):
        display = str(display).split(":", 1)[1].strip()
    display = re.sub(r"\s+\[\d+\s+(in|out)\]\s*$", "", display).strip()
    return display


def tone_slider_to_db(value: float) -> float:
    return round((clamp(value, 0, 100) - 50.0) / 5.0, 1)


def db_to_tone_slider(db: float) -> int:
    return int(round(50 + clamp(db, -10, 10) * 5))


def balance_to_gains(value: float) -> tuple[float, float]:
    value = clamp(value, 0, 100)
    if value < 50:
        return 1.0, value / 50.0
    if value > 50:
        return (100.0 - value) / 50.0, 1.0
    return 1.0, 1.0


# -------------------------------- DSP ---------------------------------------

class Biquad:
    def __init__(self) -> None:
        self.b0 = 1.0
        self.b1 = 0.0
        self.b2 = 0.0
        self.a1 = 0.0
        self.a2 = 0.0
        self.z1 = 0.0
        self.z2 = 0.0

    def set_coefficients(self, b0, b1, b2, a0, a1, a2) -> None:
        if abs(a0) < 1e-12:
            self.b0, self.b1, self.b2, self.a1, self.a2 = 1.0, 0.0, 0.0, 0.0, 0.0
            return
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0

    def process_channel(self, x):
        y = np.empty_like(x)
        b0, b1, b2, a1, a2 = self.b0, self.b1, self.b2, self.a1, self.a2
        z1, z2 = self.z1, self.z2
        for i in range(len(x)):
            sample = float(x[i])
            out = b0 * sample + z1
            z1 = b1 * sample - a1 * out + z2
            z2 = b2 * sample - a2 * out
            y[i] = out
        self.z1, self.z2 = z1, z2
        return y


def lowshelf(fs: float, f0: float, gain_db: float, slope: float = 1.0):
    if abs(gain_db) <= 0.05:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    A = 10 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / 2.0 * math.sqrt(max(0.0, (A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0))
    sqrtA = math.sqrt(A)
    b0 = A * ((A + 1) - (A - 1) * cosw + 2 * sqrtA * alpha)
    b1 = 2 * A * ((A - 1) - (A + 1) * cosw)
    b2 = A * ((A + 1) - (A - 1) * cosw - 2 * sqrtA * alpha)
    a0 = (A + 1) + (A - 1) * cosw + 2 * sqrtA * alpha
    a1 = -2 * ((A - 1) + (A + 1) * cosw)
    a2 = (A + 1) + (A - 1) * cosw - 2 * sqrtA * alpha
    return b0, b1, b2, a0, a1, a2


def highshelf(fs: float, f0: float, gain_db: float, slope: float = 1.0):
    if abs(gain_db) <= 0.05:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    A = 10 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / 2.0 * math.sqrt(max(0.0, (A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0))
    sqrtA = math.sqrt(A)
    b0 = A * ((A + 1) + (A - 1) * cosw + 2 * sqrtA * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cosw)
    b2 = A * ((A + 1) + (A - 1) * cosw - 2 * sqrtA * alpha)
    a0 = (A + 1) - (A - 1) * cosw + 2 * sqrtA * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cosw)
    a2 = (A + 1) - (A - 1) * cosw - 2 * sqrtA * alpha
    return b0, b1, b2, a0, a1, a2


class StereoShelf:
    def __init__(self) -> None:
        self.low_l = Biquad()
        self.low_r = Biquad()
        self.high_l = Biquad()
        self.high_r = Biquad()
        self.fs = 48000.0
        self.bass_db = 0.0
        self.treble_db = 0.0
        self.set_params(48000.0, 0.0, 0.0)

    def set_params(self, fs: float, bass_db: float, treble_db: float) -> None:
        fs = float(fs or 48000.0)
        bass_db = clamp(bass_db, -10, 10)
        treble_db = clamp(treble_db, -10, 10)
        if abs(fs - self.fs) > 1 or abs(bass_db - self.bass_db) > 0.01 or abs(treble_db - self.treble_db) > 0.01:
            self.fs, self.bass_db, self.treble_db = fs, bass_db, treble_db
            low = lowshelf(fs, 120.0, bass_db)
            high = highshelf(fs, 6000.0, treble_db)
            self.low_l.set_coefficients(*low)
            self.low_r.set_coefficients(*low)
            self.high_l.set_coefficients(*high)
            self.high_r.set_coefficients(*high)

    def process(self, data):
        if abs(self.bass_db) <= 0.05 and abs(self.treble_db) <= 0.05:
            return data
        out = data.copy()
        if abs(self.bass_db) > 0.05:
            out[:, 0] = self.low_l.process_channel(out[:, 0])
            out[:, 1] = self.low_r.process_channel(out[:, 1])
        if abs(self.treble_db) > 0.05:
            out[:, 0] = self.high_l.process_channel(out[:, 0])
            out[:, 1] = self.high_r.process_channel(out[:, 1])
        return out


# ------------------------------ audio engine --------------------------------

class AudioEngine:
    def __init__(self) -> None:
        self.stream = None
        self.lock = threading.RLock()
        self.eq = StereoShelf()
        self.sample_rate = 48000.0
        self.status_queue = queue.Queue()
        self.level_lock = threading.RLock()
        self.input_level = 0.0
        self.output_level = 0.0
        self.settings = {
            "volume": 100.0,
            "bass": 50.0,
            "treble": 50.0,
            "balance": 50.0,
            "swap": False,
            "muted": False,
        }

    def is_running(self) -> bool:
        return self.stream is not None

    def set_settings(self, *, volume=None, bass=None, treble=None, balance=None, swap=None, muted=None) -> None:
        with self.lock:
            if volume is not None:
                self.settings["volume"] = clamp(volume, 0, 100)
            if bass is not None:
                self.settings["bass"] = clamp(bass, 0, 100)
            if treble is not None:
                self.settings["treble"] = clamp(treble, 0, 100)
            if balance is not None:
                self.settings["balance"] = clamp(balance, 0, 100)
            if swap is not None:
                self.settings["swap"] = bool(swap)
            if muted is not None:
                self.settings["muted"] = bool(muted)
            self.eq.set_params(
                self.sample_rate,
                tone_slider_to_db(self.settings["bass"]),
                tone_slider_to_db(self.settings["treble"]),
            )

    def stop(self) -> None:
        stream = self.stream
        self.stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    def best_sample_rate(self, input_device: int, output_device: int) -> float:
        try:
            indev = sd.query_devices(input_device)
            outdev = sd.query_devices(output_device)
            in_rate = float(indev.get("default_samplerate") or 48000.0)
            out_rate = float(outdev.get("default_samplerate") or in_rate)
            if abs(in_rate - out_rate) < 1:
                return in_rate
        except Exception:
            pass
        return 48000.0

    def channel_counts(self, input_device: int, output_device: int) -> tuple[int, int]:
        indev = sd.query_devices(input_device)
        outdev = sd.query_devices(output_device)
        in_max = int(indev.get("max_input_channels", 0) or 0)
        out_max = int(outdev.get("max_output_channels", 0) or 0)
        if in_max < 1:
            raise RuntimeError(f"Selected input device has no input channels: {indev.get('name', input_device)}")
        if out_max < 1:
            raise RuntimeError(f"Selected output device has no output channels: {outdev.get('name', output_device)}")
        return min(2, in_max), min(2, out_max)

    def start(self, input_device: int, output_device: int, sample_rate: float | None = None, blocksize: int = 1024) -> None:
        if sd is None or np is None:
            raise RuntimeError("Missing dependencies inside app: sounddevice/numpy")

        self.stop()
        if sample_rate is None:
            sample_rate = self.best_sample_rate(input_device, output_device)
        self.sample_rate = float(sample_rate)
        input_channels, output_channels = self.channel_counts(input_device, output_device)

        with self.lock:
            self.eq.set_params(
                self.sample_rate,
                tone_slider_to_db(self.settings["bass"]),
                tone_slider_to_db(self.settings["treble"]),
            )

        log_line(
            f"Opening stream input={input_device} output={output_device} "
            f"rate={self.sample_rate} channels=({input_channels},{output_channels})"
        )
        try:
            self.stream = sd.Stream(
                device=(input_device, output_device),
                samplerate=self.sample_rate,
                blocksize=int(blocksize),
                channels=(input_channels, output_channels),
                dtype="float32",
                latency="high",
                callback=self.callback,
            )
            self.stream.start()
        except Exception as exc:
            log_exception("PortAudio stream open failed", exc)
            raise

    def get_levels(self) -> tuple[float, float]:
        with self.level_lock:
            return float(self.input_level), float(self.output_level)

    def callback(self, indata, outdata, frames, time_info, status) -> None:
        if status:
            try:
                self.status_queue.put_nowait(str(status))
            except Exception:
                pass

        try:
            if indata.shape[1] >= 2:
                data = indata[:, :2].copy()
            elif indata.shape[1] == 1:
                data = np.repeat(indata[:, :1], 2, axis=1).astype(np.float32)
            else:
                outdata.fill(0)
                return

            try:
                input_rms = float(np.sqrt(np.mean(np.square(data)))) if data.size else 0.0
            except Exception:
                input_rms = 0.0

            with self.lock:
                settings = dict(self.settings)
                volume = clamp(settings["volume"], 0, 100) / 100.0
                bass = clamp(settings["bass"], 0, 100)
                treble = clamp(settings["treble"], 0, 100)
                balance = clamp(settings["balance"], 0, 100)
                swap = bool(settings["swap"])
                muted = bool(settings["muted"])
                self.eq.set_params(self.sample_rate, tone_slider_to_db(bass), tone_slider_to_db(treble))
                data = self.eq.process(data)

            # Stable chain: EQ -> L/R percentage -> optional swap -> output
            left_gain, right_gain = balance_to_gains(balance)
            data[:, 0] *= left_gain * volume
            data[:, 1] *= right_gain * volume

            if swap:
                data = data[:, [1, 0]]

            if muted:
                data *= 0.0

            data = np.clip(data, -1.0, 1.0)

            try:
                output_rms = float(np.sqrt(np.mean(np.square(data)))) if data.size else 0.0
                with self.level_lock:
                    self.input_level = input_rms
                    self.output_level = output_rms
            except Exception:
                pass

            if outdata.shape[1] >= 2:
                outdata[:, :2] = data[:, :2]
                if outdata.shape[1] > 2:
                    outdata[:, 2:] = 0
            elif outdata.shape[1] == 1:
                outdata[:, 0] = (data[:, 0] + data[:, 1]) * 0.5
            else:
                outdata.fill(0)
        except Exception:
            outdata.fill(0)

    def play_test_tone(self, output_device: int, side: str = "left", duration: float = 0.9, frequency: float = 440.0) -> None:
        if sd is None or np is None:
            raise RuntimeError("Missing dependencies inside app")
        outdev = sd.query_devices(output_device)
        out_channels = min(2, int(outdev.get("max_output_channels", 0) or 0))
        if out_channels < 1:
            raise RuntimeError(f"Selected output device has no output channels: {outdev.get('name', output_device)}")
        fs = float(outdev.get("default_samplerate") or 48000.0)
        n = int(fs * float(duration))
        t = np.arange(n, dtype=np.float32) / fs
        tone = np.sin(2.0 * np.pi * float(frequency) * t).astype(np.float32)
        fade_len = max(1, min(int(0.025 * fs), n // 4))
        fade = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
        tone[:fade_len] *= fade
        tone[-fade_len:] *= fade[::-1]

        with self.lock:
            settings = dict(self.settings)
            volume = clamp(settings["volume"], 0, 100) / 100.0
            swap = bool(settings["swap"])
            muted = bool(settings["muted"])

        side = str(side or "left").lower()
        if swap:
            side = "right" if side == "left" else "left"

        data = np.zeros((n, max(1, out_channels)), dtype=np.float32)
        amp = 0.75 * volume * (0.0 if muted else 1.0)
        if out_channels == 1:
            data[:, 0] = tone * amp
        else:
            data[:, 1 if side == "right" else 0] = tone * amp

        sd.play(data, samplerate=fs, device=output_device, blocking=False)


# -------------------------------- UI ----------------------------------------

class ValueSlider(ttk.Frame):
    def __init__(self, master, label, variable, from_, to, detail_func=None, command=None):
        super().__init__(master)
        self.variable = variable
        self.detail_func = detail_func
        self.command = command
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text=label, width=10).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.scale = ttk.Scale(self, from_=from_, to=to, variable=variable, command=self.on_scale)
        self.scale.grid(row=0, column=1, sticky="ew")

        self.entry_var = tk.StringVar(value=str(int(round(variable.get()))))
        self.entry = ttk.Entry(self, textvariable=self.entry_var, width=6, justify="right")
        self.entry.grid(row=0, column=2, sticky="e", padx=(8, 4))

        self.detail = ttk.Label(self, text="", width=14)
        self.detail.grid(row=0, column=3, sticky="w", padx=(4, 0))

        self.entry.bind("<Return>", self.commit_entry)
        self.entry.bind("<KP_Enter>", self.commit_entry)
        self.entry.bind("<FocusOut>", self.commit_entry)

        try:
            variable.trace_add("write", lambda *_: self.refresh())
        except Exception:
            pass

        self.refresh()

    def on_scale(self, _value=None):
        self.refresh()
        if self.command:
            self.command()

    def commit_entry(self, _event=None):
        raw = self.entry_var.get().strip().replace("%", "")
        try:
            value = float(raw)
        except Exception:
            value = self.variable.get()
        self.variable.set(value)
        self.refresh()
        if self.command:
            self.command()
        return "break"

    def refresh(self):
        value = self.variable.get()
        if self.focus_get() is not self.entry:
            self.entry_var.set(str(int(round(value))))
        if self.detail_func:
            self.detail.configure(text=self.detail_func(value))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_app_dir()
        log_line(f"App launch {VERSION}")

        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("980x720")
        self.minsize(760, 520)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.engine = AudioEngine()
        self.devices = []
        self.input_choices = []
        self.output_choices = []
        self.previous_system_output = ""
        self.previous_system_input = ""
        self.previous_input_volume = None
        self.auto_routed = False
        self.auto_input_routed = False
        self.running = False
        self.starting = False

        self.hidden_input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.volume_var = tk.DoubleVar(value=100)
        self.bass_var = tk.DoubleVar(value=50)
        self.treble_var = tk.DoubleVar(value=50)
        self.balance_var = tk.DoubleVar(value=50)
        self.swap_var = tk.BooleanVar(value=False)
        self.muted_var = tk.BooleanVar(value=False)
        self.input_status_var = tk.StringVar(value="Hidden route: macOS Output/Input → BlackHole 2ch → selected output")
        self.status_var = tk.StringVar(value="Choose output and click Start. Use the right scrollbar if the window is small.")

        self.build_ui()
        self.refresh_devices()
        self.load_state_into_ui()
        self.apply_settings_to_engine()
        self.update_buttons()
        self.after(250, self.update_meter)
        self.after(500, self.poll_engine_status)

    def build_ui(self):
        # One general right-side scrollbar for the whole app window.
        # This keeps the controls usable on smaller screens.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.scroll_canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.page = ttk.Frame(self.scroll_canvas)
        self.page_window = self.scroll_canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.page.columnconfigure(0, weight=1)

        def _on_page_configure(_event=None):
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

        def _on_canvas_configure(event):
            self.scroll_canvas.itemconfigure(self.page_window, width=event.width)

        def _on_mousewheel(event):
            # macOS uses event.delta; some Tk builds use Button-4/5.
            if getattr(event, "num", None) == 4:
                self.scroll_canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                self.scroll_canvas.yview_scroll(3, "units")
            else:
                delta = getattr(event, "delta", 0)
                if delta:
                    self.scroll_canvas.yview_scroll(int(-1 * (delta / 120)), "units")
            return "break"

        self.page.bind("<Configure>", _on_page_configure)
        self.scroll_canvas.bind("<Configure>", _on_canvas_configure)
        self.scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.scroll_canvas.bind_all("<Button-4>", _on_mousewheel)
        self.scroll_canvas.bind_all("<Button-5>", _on_mousewheel)

        header = ttk.Frame(self.page, padding=(12, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_NAME, font=("TkDefaultFont", 20, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Choose output only. Start auto-routes macOS output/input through BlackHole and restores on Stop.",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        routing = ttk.LabelFrame(self.page, text="Routing", padding=10)
        routing.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        routing.columnconfigure(1, weight=1)

        ttk.Label(routing, text="Output").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.output_menu = ttk.OptionMenu(routing, self.output_var, "")
        self.output_menu.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(routing, textvariable=self.input_status_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.meter_var = tk.StringVar(value="Signal: waiting")
        self.meter_bar = ttk.Progressbar(routing, maximum=100, value=0)
        self.meter_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Label(routing, textvariable=self.meter_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))

        buttons = ttk.Frame(routing)
        buttons.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=(12, 0))
        self.refresh_button = ttk.Button(buttons, text="Refresh", command=self.refresh_devices)
        self.refresh_button.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.start_button = ttk.Button(buttons, text="Start", command=self.start_audio)
        self.start_button.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop_audio)
        self.stop_button.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.diagnostics_button = ttk.Button(buttons, text="Diagnostics", command=self.show_diagnostics)
        self.diagnostics_button.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        self.permission_button = ttk.Button(buttons, text="Mic Permission", command=self.show_permission_help)
        self.permission_button.grid(row=4, column=0, sticky="ew")

        main = ttk.Frame(self.page, padding=(12, 0))
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)

        controls = ttk.LabelFrame(main, text="Controls", padding=10)
        controls.grid(row=0, column=0, sticky="ew", pady=8)
        controls.columnconfigure(0, weight=1)

        self.volume_slider = ValueSlider(controls, "Volume", self.volume_var, 0, 100, lambda v: f"{int(round(v))}%", self.on_settings_change)
        self.volume_slider.grid(row=0, column=0, sticky="ew", pady=5)
        self.bass_slider = ValueSlider(controls, "Bass", self.bass_var, 0, 100, lambda v: f"{tone_slider_to_db(v):+.1f} dB", self.on_settings_change)
        self.bass_slider.grid(row=1, column=0, sticky="ew", pady=5)
        self.treble_slider = ValueSlider(controls, "Treble", self.treble_var, 0, 100, lambda v: f"{tone_slider_to_db(v):+.1f} dB", self.on_settings_change)
        self.treble_slider.grid(row=2, column=0, sticky="ew", pady=5)
        self.balance_slider = ValueSlider(controls, "L / R", self.balance_var, 0, 100, self.format_balance, self.on_settings_change)
        self.balance_slider.grid(row=3, column=0, sticky="ew", pady=5)

        toggles = ttk.Frame(controls)
        toggles.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Checkbutton(toggles, text="Swap L/R", variable=self.swap_var, command=self.on_settings_change).grid(row=0, column=0, padx=(0, 12))
        ttk.Checkbutton(toggles, text="Mute", variable=self.muted_var, command=self.on_settings_change).grid(row=0, column=1, padx=(0, 12))
        ttk.Button(toggles, text="Neutral", command=self.neutral).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(toggles, text="Save state", command=self.save_state).grid(row=0, column=3, padx=(0, 8))

        tests = ttk.Frame(controls)
        tests.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(tests, text="L/R audio test").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Button(tests, text="Play Left", command=lambda: self.play_lr_test("left")).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(tests, text="Play Right", command=lambda: self.play_lr_test("right")).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(tests, text="Play Both", command=lambda: self.play_lr_test("both")).grid(row=0, column=3, padx=(0, 8))

        presets = ttk.LabelFrame(main, text="Volume-independent presets", padding=10)
        presets.grid(row=1, column=0, sticky="ew", pady=8)
        for i in range(3):
            ttk.Button(presets, text=f"Save {i+1}", command=lambda slot=i+1: self.save_preset(slot)).grid(row=i, column=0, sticky="ew", padx=(0, 6), pady=4)
            ttk.Button(presets, text=f"Load {i+1}", command=lambda slot=i+1: self.load_preset(slot)).grid(row=i, column=1, sticky="ew", padx=(6, 0), pady=4)
        presets.columnconfigure(0, weight=1)
        presets.columnconfigure(1, weight=1)

        instructions = ttk.LabelFrame(main, text="macOS routing", padding=10)
        instructions.grid(row=2, column=0, sticky="ew", pady=8)
        ttk.Label(
            instructions,
            justify="left",
            wraplength=900,
            text=(
                "1. Run Install Required Audio Driver.command once if BlackHole is missing.\n"
                "2. Choose only your real Output device here.\n"
                "3. Click Start. The app switches macOS Output and Input to BlackHole automatically.\n"
                "4. Click Stop or close the app to restore your previous macOS Output.\n\n"
                "Do not choose BlackHole as Output in this app. If Signal stays 0%, click Mic Permission and enable L-R Swaper Mac."
            ),
        ).grid(row=0, column=0, sticky="ew")

        self.status = ttk.Label(self.page, textvariable=self.status_var, padding=(12, 8), anchor="w")
        self.status.grid(row=3, column=0, sticky="ew")

    def format_balance(self, value):
        value = int(round(clamp(value, 0, 100)))
        if value == 50:
            return "Center"
        left, right = balance_to_gains(value)
        return f"L {int(round(left*100))}% / R {int(round(right*100))}%"

    def format_choices(self, choices):
        return [f"{idx}: {name}" for idx, name in choices]

    def find_blackhole_input_choice(self):
        formatted = self.format_choices(self.input_choices)
        for item in formatted:
            lower = item.lower()
            if "blackhole" in lower and ("2ch" in lower or "2 ch" in lower or "2 " in lower):
                return item
        for item in formatted:
            if "blackhole" in item.lower():
                return item
        return ""

    def rebuild_menu(self, option_menu, variable, choices, prefer=None):
        menu = option_menu["menu"]
        menu.delete(0, "end")
        for item in choices:
            menu.add_command(label=item, command=lambda value=item: variable.set(value))
        current = variable.get()
        if current not in choices:
            selected = choices[0] if choices else ""
            if prefer:
                selected = next((c for c in choices if prefer.lower() in c.lower()), selected)
            variable.set(selected)

    def refresh_devices(self):
        if sd is None:
            self.status_var.set("Missing sounddevice inside app.")
            return
        try:
            self.devices = list(sd.query_devices())
            log_line(f"Found {len(self.devices)} PortAudio devices")
        except Exception as exc:
            log_exception("Could not list audio devices", exc)
            messagebox.showerror(APP_NAME, f"Could not list audio devices:\n{exc}\n\nLog: {LOG_FILE}")
            return

        inputs = []
        outputs = []
        for idx, dev in enumerate(self.devices):
            name = str(dev.get("name", f"Device {idx}"))
            in_ch = int(dev.get("max_input_channels", 0) or 0)
            out_ch = int(dev.get("max_output_channels", 0) or 0)
            if in_ch >= 1:
                inputs.append((idx, f"{name}  [{in_ch} in]"))
            if out_ch >= 1:
                outputs.append((idx, f"{name}  [{out_ch} out]"))

        self.input_choices = inputs
        self.output_choices = outputs

        blackhole = self.find_blackhole_input_choice()
        if blackhole:
            self.hidden_input_var.set(blackhole)
            self.input_status_var.set(f"Hidden input: {blackhole.split(':', 1)[1].strip()}")
        else:
            self.hidden_input_var.set("")
            self.input_status_var.set("Hidden input: BlackHole 2ch not found. Run the DMG audio setup and reboot.")

        output_items = self.format_choices(outputs)
        old_output = self.output_var.get()
        self.rebuild_menu(self.output_menu, self.output_var, output_items, prefer=None)

        # Preserve real output if still present, and never default to BlackHole.
        if old_output in output_items and "blackhole" not in old_output.lower():
            self.output_var.set(old_output)
        elif (not self.output_var.get()) or ("blackhole" in self.output_var.get().lower()):
            first_real = next((item for item in output_items if "blackhole" not in item.lower()), output_items[0] if output_items else "")
            self.output_var.set(first_real)

    def selected_index(self, value):
        try:
            return int(str(value).split(":", 1)[0])
        except Exception:
            return None

    def show_permission_help(self):
        open_microphone_privacy_settings()
        messagebox.showinfo(
            APP_NAME + " Permission",
            "macOS sees BlackHole as an audio input device, so L/R Swaper Mac "
            "needs Microphone permission.\n\n"
            "Open:\n"
            "System Settings → Privacy & Security → Microphone\n\n"
            "Then enable:\n"
            "L-R Swaper Mac\n\n"
            "After enabling it, click Stop, then Start again. If the app does "
            "not appear there, quit and reopen the app, then press Start once "
            "to trigger the permission request."
        )

    def show_diagnostics(self):
        try:
            helper = switch_audio_source_cmd() or "missing"
            current = current_system_output_name() or "unknown"
            outputs = list_system_outputs()
            inputs = list_system_inputs()
            blackhole_out = find_blackhole_system_output() or "missing"
            blackhole_in = find_blackhole_system_input() or "missing"
            current_input = current_system_input_name() or "unknown"
            input_volume = get_system_input_volume()
            devices_text = ""
            try:
                devices_text = str(sd.query_devices()) if sd is not None else "sounddevice missing"
            except Exception as exc:
                devices_text = f"Could not query PortAudio devices: {exc}"
            msg = (
                f"Version: {VERSION}\n"
                f"Log: {LOG_FILE}\n"
                f"Permission: System Settings → Privacy & Security → Microphone → enable L-R Swaper Mac\n\n"
                f"SwitchAudioSource: {helper}\n"
                f"Current macOS output: {current}\n"
                f"Current macOS input: {current_input}\n"
                f"macOS input volume: {input_volume if input_volume is not None else 'unknown'}\n"
                f"BlackHole system output: {blackhole_out}\n"
                f"BlackHole system input: {blackhole_in}\n\n"
                f"Hidden PortAudio input: {self.hidden_input_var.get() or 'missing'}\n"
                f"Output: {self.output_var.get() or 'missing'}\n\n"
                f"System outputs:\n" + "\n".join(outputs[:30]) + "\n\n"
                f"System inputs:\n" + "\n".join(inputs[:30]) + "\n\n"
                f"PortAudio devices:\n{devices_text[:3500]}"
            )
            log_line("Diagnostics requested")
            messagebox.showinfo(APP_NAME + " Diagnostics", msg)
        except Exception as exc:
            log_exception("Diagnostics failed", exc)
            messagebox.showerror(APP_NAME, f"Diagnostics failed:\n{exc}\n\nLog: {LOG_FILE}")

    def fail_start(self, message=None):
        self.starting = False
        self.running = False
        self.update_buttons()
        if message:
            self.status_var.set(message)

    def update_buttons(self):
        try:
            if self.starting or self.running:
                self.start_button.configure(state="disabled")
                self.stop_button.configure(state="normal")
            else:
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="normal")
        except Exception:
            pass

    def update_meter(self):
        try:
            in_level, out_level = self.engine.get_levels()
            # RMS around 0.1 is already a strong signal, so scale for visibility.
            percent = max(0, min(100, int(round(in_level * 650))))
            self.meter_bar.configure(value=percent)
            if self.running:
                if percent <= 1:
                    self.meter_var.set("Signal: 0% — allow Microphone permission for this app, then restart Start")
                else:
                    self.meter_var.set(f"Signal from BlackHole: {percent}%")
            else:
                self.meter_var.set("Signal: stopped")
        except Exception:
            pass
        self.after(250, self.update_meter)

    def start_audio(self):
        log_line("Start pressed")
        if self.starting:
            self.status_var.set("Already starting...")
            return
        if self.running and self.engine.is_running():
            self.status_var.set("Already running. Click Stop before changing output.")
            return

        self.starting = True
        self.update_buttons()
        self.status_var.set("Starting: checking devices...")
        self.update_idletasks()

        if sd is None or np is None:
            messagebox.showerror(APP_NAME, f"Missing bundled dependencies.\n\nLog: {LOG_FILE}")
            return

        try:
            self.refresh_devices()
            input_idx = self.selected_index(self.hidden_input_var.get())
            output_idx = self.selected_index(self.output_var.get())
            log_line(f"Hidden input={self.hidden_input_var.get()} index={input_idx}")
            log_line(f"Output={self.output_var.get()} index={output_idx}")

            if input_idx is None:
                messagebox.showwarning(
                    APP_NAME,
                    "BlackHole 2ch input was not found.\n\n"
                    "Run Install Required Audio Driver.command from the DMG.\n"
                    "If BlackHole was just installed, reboot your Mac.\n\n"
                    f"Log: {LOG_FILE}"
                )
                self.fail_start("Start failed: BlackHole input missing.")
                return

            if output_idx is None:
                messagebox.showwarning(APP_NAME, "Select your real output device first.")
                self.fail_start("Start failed: select a real output device.")
                return

            if "blackhole" in self.output_var.get().lower():
                messagebox.showwarning(
                    APP_NAME,
                    "Choose your real speaker/headphones as Output.\n\n"
                    "BlackHole is used automatically in the background; do not select it as the app output."
                )
                self.fail_start("Start failed: choose a real output, not BlackHole.")
                return

            helper = switch_audio_source_cmd()
            log_line(f"SwitchAudioSource path: {helper or 'missing'}")
            if not helper:
                messagebox.showwarning(
                    APP_NAME,
                    "SwitchAudioSource helper was not found.\n\n"
                    "Run Install Required Audio Driver.command from the DMG.\n\n"
                    f"Log: {LOG_FILE}"
                )
                self.fail_start("Start failed: SwitchAudioSource missing.")
                return

            blackhole_output = find_blackhole_system_output()
            blackhole_input = find_blackhole_system_input()
            log_line(f"BlackHole system output: {blackhole_output or 'missing'}")
            log_line(f"BlackHole system input: {blackhole_input or 'missing'}")
            if not blackhole_output:
                messagebox.showwarning(
                    APP_NAME,
                    "BlackHole 2ch output was not found.\n\n"
                    "Run Install Required Audio Driver.command from the DMG.\n"
                    "If BlackHole was just installed, reboot your Mac.\n\n"
                    f"Log: {LOG_FILE}"
                )
                self.fail_start("Start failed: BlackHole output missing.")
                return
            if not blackhole_input:
                messagebox.showwarning(
                    APP_NAME,
                    "BlackHole 2ch input was not found in macOS input devices.\n\n"
                    "Run Install Required Audio Driver.command from the DMG.\n"
                    "If BlackHole was just installed, reboot your Mac.\n\n"
                    f"Log: {LOG_FILE}"
                )
                self.fail_start("Start failed: BlackHole input missing.")
                return

            current_output = current_system_output_name()
            current_input = current_system_input_name()
            selected_real_output = clean_device_display_name(self.output_var.get())
            if current_output and "blackhole" not in current_output.lower():
                self.previous_system_output = current_output
            elif selected_real_output:
                self.previous_system_output = selected_real_output

            if current_input and "blackhole" not in current_input.lower():
                self.previous_system_input = current_input
            self.previous_input_volume = get_system_input_volume()
            log_line(f"Current macOS input: {current_input}")
            log_line(f"Previous input volume: {self.previous_input_volume}")

            self.status_var.set("Starting: routing macOS input to BlackHole and raising input volume...")
            self.update_idletasks()

            ok_in, input_msg = set_system_input_name(blackhole_input)
            log_line(f"Route input to BlackHole ok={ok_in}: {input_msg}")
            if not ok_in:
                self.fail_start("Start failed: could not route input to BlackHole.")
                messagebox.showwarning(
                    APP_NAME,
                    "Could not set macOS input to BlackHole.\n\n"
                    f"{input_msg}\n\n"
                    f"Log: {LOG_FILE}"
                )
                return
            self.auto_input_routed = True

            ok_vol, vol_msg = set_system_input_volume(100)
            log_line(f"Set input volume ok={ok_vol}: {vol_msg}")

            self.status_var.set("Starting: routing macOS output to BlackHole...")
            self.update_idletasks()

            ok, route_msg = set_system_output_name(blackhole_output)
            log_line(f"Route to BlackHole ok={ok}: {route_msg}")
            if not ok:
                messagebox.showwarning(
                    APP_NAME,
                    "Could not auto-route macOS output to BlackHole.\n\n"
                    f"{route_msg}\n\n"
                    "Run Install Required Audio Driver.command from the DMG.\n\n"
                    f"Log: {LOG_FILE}"
                )
                self.fail_start("Start failed: could not route to BlackHole.")
                return
            self.auto_routed = True
            time.sleep(0.35)

            self.status_var.set("Starting audio stream...")
            self.update_idletasks()

            self.apply_settings_to_engine()
            self.engine.start(input_idx, output_idx)
            self.running = True
            self.starting = False
            self.update_buttons()
            self.status_var.set(f"Running. If Signal stays 0%, click Mic Permission.")
            log_line("Audio stream started successfully")
            self.save_state(silent=True)
        except Exception as exc:
            log_exception("Could not start audio", exc)
            self.fail_start("Start failed. See Diagnostics/log.")
            messagebox.showerror(
                APP_NAME,
                "Could not start audio:\n"
                f"{exc}\n\n"
                f"Hidden input: {self.hidden_input_var.get()}\n"
                f"Output: {self.output_var.get()}\n\n"
                f"Log file:\n{LOG_FILE}"
            )

    def restore_system_output(self):
        ok_all = True
        messages = []

        if self.auto_routed and self.previous_system_output:
            ok, msg = set_system_output_name(self.previous_system_output)
            ok_all = ok_all and ok
            messages.append(msg)
            self.auto_routed = False

        if self.auto_input_routed and self.previous_system_input:
            ok, msg = set_system_input_name(self.previous_system_input)
            ok_all = ok_all and ok
            messages.append(msg)
            self.auto_input_routed = False

        if self.previous_input_volume is not None:
            ok, msg = set_system_input_volume(int(self.previous_input_volume))
            ok_all = ok_all and ok
            messages.append(msg)

        return ok_all, " ".join(m for m in messages if m)

    def stop_audio(self):
        self.engine.stop()
        self.running = False
        self.starting = False
        self.update_buttons()
        ok, msg = self.restore_system_output()
        if ok and self.previous_system_output:
            self.status_var.set(f"Stopped. Restored macOS Output to {self.previous_system_output}.")
        elif self.previous_system_output:
            self.status_var.set(f"Stopped. Could not restore output automatically: {msg}")
        else:
            self.status_var.set("Stopped.")

    def on_close(self):
        self.save_state(silent=True)
        self.engine.stop()
        self.restore_system_output()
        try:
            self.scroll_canvas.unbind_all("<MouseWheel>")
            self.scroll_canvas.unbind_all("<Button-4>")
            self.scroll_canvas.unbind_all("<Button-5>")
        except Exception:
            pass
        self.destroy()

    def on_settings_change(self):
        self.apply_settings_to_engine()
        self.save_state(silent=True)

    def apply_settings_to_engine(self):
        self.engine.set_settings(
            volume=self.volume_var.get(),
            bass=self.bass_var.get(),
            treble=self.treble_var.get(),
            balance=self.balance_var.get(),
            swap=self.swap_var.get(),
            muted=self.muted_var.get(),
        )

    def play_lr_test(self, side):
        output_idx = self.selected_index(self.output_var.get())
        if output_idx is None:
            messagebox.showwarning(APP_NAME, "Select your output device first.")
            return
        try:
            self.apply_settings_to_engine()
            if side == "both":
                self.engine.play_test_tone(output_idx, "left", duration=0.55, frequency=440.0)
                self.after(650, lambda: self.engine.play_test_tone(output_idx, "right", duration=0.55, frequency=660.0))
                self.status_var.set("Played Left then Right test tones.")
            else:
                self.engine.play_test_tone(output_idx, side, duration=0.9, frequency=440.0 if side == "left" else 660.0)
                self.status_var.set(f"Played {side.title()} test tone.")
        except Exception as exc:
            log_exception("L/R test failed", exc)
            messagebox.showerror(APP_NAME, f"Could not play L/R test:\n{exc}")

    def neutral(self):
        # Keep volume unchanged.
        self.bass_var.set(50)
        self.treble_var.set(50)
        self.balance_var.set(50)
        self.swap_var.set(False)
        self.muted_var.set(False)
        self.on_settings_change()
        self.status_var.set("Neutral applied. Volume unchanged.")

    def state_dict(self):
        return {
            "output": self.output_var.get(),
            "volume": self.volume_var.get(),
            "bass": self.bass_var.get(),
            "treble": self.treble_var.get(),
            "balance": self.balance_var.get(),
            "swap": self.swap_var.get(),
            "muted": self.muted_var.get(),
        }

    def save_state(self, silent=False):
        save_json(STATE_FILE, self.state_dict())
        if not silent:
            self.status_var.set(f"Saved state to {STATE_FILE}")

    def load_state_into_ui(self):
        state = load_json(STATE_FILE)
        if not state:
            return
        if state.get("output"):
            self.output_var.set(state["output"])
        self.volume_var.set(clamp(state.get("volume", 100), 0, 100))
        self.bass_var.set(clamp(state.get("bass", 50), 0, 100))
        self.treble_var.set(clamp(state.get("treble", 50), 0, 100))
        self.balance_var.set(clamp(state.get("balance", 50), 0, 100))
        self.swap_var.set(bool(state.get("swap", False)))
        self.muted_var.set(bool(state.get("muted", False)))

    def save_preset(self, slot):
        slot = int(slot)
        preset = {
            "output": self.output_var.get(),
            "bass": self.bass_var.get(),
            "treble": self.treble_var.get(),
            "balance": self.balance_var.get(),
            "swap": self.swap_var.get(),
            "muted": False,
            "volume_independent": True,
        }
        save_json(PRESET_FILES[slot - 1], preset)
        self.status_var.set(f"Saved preset {slot} without volume.")

    def load_preset(self, slot):
        slot = int(slot)
        preset = load_json(PRESET_FILES[slot - 1])
        if not preset:
            messagebox.showinfo(APP_NAME, f"No preset saved in slot {slot}.")
            return
        current_volume = self.volume_var.get()
        old_mute = self.muted_var.get()

        self.muted_var.set(True)
        self.apply_settings_to_engine()
        self.update_idletasks()

        if preset.get("output"):
            self.output_var.set(preset["output"])
        self.bass_var.set(clamp(preset.get("bass", 50), 0, 100))
        self.treble_var.set(clamp(preset.get("treble", 50), 0, 100))
        self.balance_var.set(clamp(preset.get("balance", 50), 0, 100))
        self.swap_var.set(bool(preset.get("swap", False)))
        self.volume_var.set(current_volume)

        self.muted_var.set(old_mute)
        self.apply_settings_to_engine()
        self.save_state(silent=True)
        self.status_var.set(f"Loaded preset {slot}. Volume unchanged.")

    def poll_engine_status(self):
        try:
            while True:
                msg = self.engine.status_queue.get_nowait()
                self.status_var.set(f"Audio status: {msg}")
                log_line("Audio status: " + msg)
        except queue.Empty:
            pass
        self.after(500, self.poll_engine_status)


def main():
    if sd is None or np is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            APP_NAME,
            "Missing bundled dependencies: sounddevice/numpy.\n\nRebuild the standalone app.",
        )
        return 2
    App().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
