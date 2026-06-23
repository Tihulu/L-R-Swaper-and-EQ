#!/usr/bin/env python3
"""Theme dispatcher for L/R Swaper Linux.

Plain Theme launches the classic interface.
Tihuluwave Theme launches the modern neon dashboard.
"""
import json
import runpy
import sys
from pathlib import Path

APP_ID = "lr-swaper"
STATE_DIR = Path.home() / ".config" / APP_ID
THEME_FILE = STATE_DIR / "theme.json"
THEME_PLAIN = "Plain Theme"
THEME_TIHULUWAVE = "Tihuluwave Theme"


def current_theme():
    try:
        data = json.loads(THEME_FILE.read_text())
        return data.get("theme", THEME_TIHULUWAVE)
    except Exception:
        return THEME_TIHULUWAVE


def main():
    here = Path(__file__).resolve().parent
    theme = current_theme()

    # CLI stays on the newer backend by default so the newest flags remain
    # available even if the user chose Plain Theme for the GUI.
    if len(sys.argv) > 1:
        target = here / "lr_swaper_tihuluwave.py"
    elif theme == THEME_PLAIN:
        target = here / "lr_swaper_plain.py"
    else:
        target = here / "lr_swaper_tihuluwave_qt.py"

    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
