#!/usr/bin/env python3
"""
L/R Swaper - Tihuluwave Qt UI

Modern PySide6/Qt UI for Tihuluwave Theme.
Plain Theme still launches the classic Tkinter UI.
The audio backend is reused from lr_swaper_tihuluwave.py.
"""

import importlib.util
import os
import runpy
import sys
from pathlib import Path

APP_VERSION = "v5.1"
REPOSITORY_URL = "https://github.com/Tihulu/L-R-Swaper-and-EQ"
QUICK_INSTALL_COMMAND = "bash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)"

HERE = Path(__file__).resolve().parent
BACKEND_PATH = HERE / "lr_swaper_tihuluwave.py"
LAUNCHER_PATH = HERE / "lr-swaper.py"

spec = importlib.util.spec_from_file_location("lr_backend_tihuluwave", str(BACKEND_PATH))
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont, QIcon, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSlider,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QSizePolicy,
        QHeaderView,
    )
except Exception as exc:
    print("ERROR: PySide6 is required for Tihuluwave Theme.", file=sys.stderr)
    print("The app will not fall back to the old v3.8 Tk UI anymore.", file=sys.stderr)
    print("Run install.sh again, or install manually:", file=sys.stderr)
    print("  python3 -m pip install --user PySide6", file=sys.stderr)
    print(f"Import error: {exc}", file=sys.stderr)
    raise SystemExit(2)


APP_NAME = backend.APP_NAME
THEME_PLAIN = backend.THEME_PLAIN

BG = "#070b18"
PANEL = "#0d1425"
PANEL2 = "#121b31"
PANEL3 = "#17223a"
BORDER = "#243451"
TEXT = "#f4f7fb"
MUTED = "#9aa8bd"
CYAN = "#1fc8ff"
BLUE = "#1478ff"
MAGENTA = "#d94cff"
GREEN = "#25e070"
GREEN_BG = "#0c3422"
ORANGE = "#ff8a1f"
RED = "#ff5364"


def save_theme(name):
    backend.save_theme_name(name)


def restart_launcher():
    os.execv(sys.executable, [sys.executable, str(LAUNCHER_PATH)] + sys.argv[1:])


def card(title: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)

    title_label = QLabel(title)
    title_label.setObjectName("CardTitle")
    layout.addWidget(title_label)

    line = QFrame()
    line.setObjectName("CardLine")
    line.setFixedHeight(1)
    layout.addWidget(line)
    return frame


class NoWheelSlider(QSlider):
    """Slider that ignores mouse wheel changes so the page scrolls instead."""
    def wheelEvent(self, event):
        event.ignore()


class TihuluwaveQt(QMainWindow):
    def __init__(self):
        super().__init__()
        if not backend.require_pactl(True):
            self.close()
            return

        self.setWindowTitle("L/R Swaper v5.1 - Tihuluwave Theme")
        icon_path = HERE / "icons" / "lr-swaper-256.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1280, 820)
        self.setMinimumSize(1080, 680)

        self.sinks = []
        self.selected_row = -1
        self._volume_timer = QTimer(self)
        self._volume_timer.setSingleShot(True)
        self._volume_timer.timeout.connect(self.apply_volume)

        self._tone_timer = QTimer(self)
        self._tone_timer.setSingleShot(True)
        self._tone_timer.timeout.connect(self.apply_tone)

        self._balance_timer = QTimer(self)
        self._balance_timer.setSingleShot(True)
        self._balance_timer.timeout.connect(self.apply_balance)

        self.apply_style()
        self.build_ui()
        self.refresh()

    # ---------------- UI ----------------

    def apply_style(self):
        QApplication.instance().setFont(QFont("Noto Sans", 10))
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {BG};
                color: {TEXT};
            }}
            QWidget {{
                background: {BG};
                color: {TEXT};
                font-family: "Noto Sans", "Inter", "DejaVu Sans", sans-serif;
                font-size: 10pt;
            }}
            QFrame#Card {{
                background-color: {PANEL};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            QFrame#Inner {{
                background-color: {PANEL2};
                border: 1px solid {BORDER};
                border-radius: 13px;
            }}
            QFrame#CardLine {{
                background: #18243c;
                border: none;
            }}
            QLabel#Title {{
                font-size: 24pt;
                font-weight: 800;
                color: {TEXT};
            }}
            QLabel#Subtitle {{
                color: {MUTED};
                font-size: 10pt;
            }}
            QLabel#CardTitle {{
                color: {CYAN};
                font-weight: 800;
                font-size: 12pt;
                letter-spacing: 0.4px;
                background: transparent;
                border: none;
                min-height: 24px;
                padding: 0 0 2px 0;
            }}
            QLabel#Small {{
                color: {MUTED};
                background: transparent;
                border: none;
            }}
            QLabel#TargetName {{
                color: {MAGENTA};
                font-weight: 800;
                font-size: 13pt;
                background: transparent;
                border: none;
            }}
            QLabel#SectionLead {{
                color: #c6d4f5;
                font-size: 9pt;
                font-weight: 800;
                letter-spacing: 0.4px;
                background: #081222;
                border: 1px solid #1a2a44;
                border-radius: 9px;
                padding: 6px 10px;
            }}
            QLabel#SliderName {{
                color: #eef4ff;
                font-size: 10.5pt;
                font-weight: 700;
                background: #081222;
                border: 1px solid #1a2a44;
                border-radius: 9px;
                padding: 6px 10px;
            }}
            QLabel#ValueBox {{
                color: #d6e4ff;
                font-size: 9.5pt;
                font-weight: 700;
                background: #0b1426;
                border: 1px solid #243553;
                border-radius: 9px;
                padding: 5px 8px;
            }}
            QLabel#PillOn {{
                color: {GREEN};
                background-color: {GREEN_BG};
                border: 1px solid #176a42;
                border-radius: 10px;
                padding: 7px 10px;
                font-weight: 700;
            }}
            QLabel#PillOff {{
                color: {MUTED};
                background-color: {PANEL2};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 7px 10px;
                font-weight: 700;
            }}
            QLabel#Status {{
                color: {TEXT};
                background: transparent;
                border: none;
            }}
            QPushButton {{
                background-color: {PANEL2};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 10px 14px;
                font-weight: 700;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {PANEL3};
                border-color: {CYAN};
            }}
            QPushButton#Primary {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {CYAN}, stop:1 {MAGENTA});
                color: white;
                border: 1px solid {CYAN};
                min-height: 42px;
                font-size: 13pt;
            }}
            QPushButton#ActionButton {{
                min-height: 28px;
                padding: 12px 14px;
            }}
            QPushButton#TestButton {{
                min-height: 28px;
                padding: 12px 14px;
            }}
            QPushButton#Active {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {BLUE}, stop:1 {MAGENTA});
                color: white;
                border: 1px solid {CYAN};
            }}
            QTableWidget {{
                background-color: {PANEL2};
                border: 1px solid {BORDER};
                border-radius: 14px;
                gridline-color: #1b2940;
                selection-background-color: #113b70;
                selection-color: {TEXT};
                color: {TEXT};
                alternate-background-color: #0f1728;
                padding: 4px 8px 4px 4px;
            }}
            QHeaderView::section {{
                background-color: #18243c;
                color: {TEXT};
                border: none;
                border-bottom: 1px solid {BORDER};
                padding: 8px;
                font-weight: 700;
            }}
            QTableCornerButton::section {{
                background-color: #18243c;
                border: none;
            }}
            QScrollArea {{
                border: none;
                background: {BG};
            }}
            QScrollBar:vertical {{
                background: #0d1728;
                width: 13px;
                margin: 0px;
                border-left: 1px solid #1d2b42;
                border-radius: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #4e6fa3;
                min-height: 38px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {CYAN};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background: #0d1728;
                height: 13px;
                margin: 0px;
                border-top: 1px solid #1d2b42;
            }}
            QScrollBar::handle:horizontal {{
                background: #4e6fa3;
                min-width: 38px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
            QSlider::groove:horizontal {{
                background: #344052;
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {CYAN}, stop:1 {MAGENTA});
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: #f3d8ff;
                border: 1px solid {MAGENTA};
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }}
            QTextEdit {{
                background-color: {PANEL};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 14, 18, 10)
        root_layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(56, 56)
        logo.setObjectName("HeaderLogo")
        logo.setStyleSheet(f"background:{PANEL2}; border:1px solid {BORDER}; border-radius:18px;")
        header_icon_path = HERE / "icons" / "lr-swaper-256.png"
        if header_icon_path.exists():
            pix = QPixmap(str(header_icon_path))
            if not pix.isNull():
                logo.setPixmap(pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logo.setText("L/R")
                logo.setStyleSheet(f"background:{PANEL2}; border:1px solid {BORDER}; border-radius:18px; color:{CYAN}; font-size:16pt; font-weight:800;")
        else:
            logo.setText("L/R")
            logo.setStyleSheet(f"background:{PANEL2}; border:1px solid {BORDER}; border-radius:18px; color:{CYAN}; font-size:16pt; font-weight:800;")
        header.addWidget(logo)

        title_box = QVBoxLayout()
        title = QLabel("L/R Swaper")
        title.setObjectName("Title")
        subtitle = QLabel("Linux  -  Tihuluwave Theme")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        plain_btn = QPushButton("Plain Theme")
        plain_btn.clicked.connect(self.switch_plain)
        header.addWidget(plain_btn)

        tw_btn = QPushButton("Tihuluwave Theme")
        tw_btn.setObjectName("Active")
        tw_btn.clicked.connect(lambda: self.set_status("Tihuluwave Theme active."))
        header.addWidget(tw_btn)

        help_btn = QPushButton("Help")
        help_btn.clicked.connect(self.show_help)
        header.addWidget(help_btn)

        diag_btn = QPushButton("Diagnostics")
        diag_btn.clicked.connect(self.show_diagnostics)
        header.addWidget(diag_btn)

        root_layout.addLayout(header)

        # Scroll content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFocusPolicy(Qt.StrongFocus)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

        # Routing card
        routing = card("ROUTING & SIGNAL")
        routing_layout = routing.layout()
        routing_grid = QGridLayout()
        routing_grid.setSpacing(14)
        routing_layout.addLayout(routing_grid)

        output_title = QLabel("Output Devices")
        output_title.setObjectName("SectionLead")
        routing_grid.addWidget(output_title, 0, 0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Default", "Type", "Output", "State"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.itemSelectionChanged.connect(self.on_table_selection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(210)
        routing_grid.addWidget(self.table, 1, 0, 1, 1)

        route_buttons = QVBoxLayout()
        start = QPushButton("Start")
        start.setObjectName("Primary")
        start.clicked.connect(self.start_swap)
        route_buttons.addWidget(start)

        stop = QPushButton("Stop")
        stop.clicked.connect(self.disable_gui)
        route_buttons.addWidget(stop)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        route_buttons.addWidget(refresh)

        use_selected = QPushButton("Use selected")
        use_selected.clicked.connect(self.use_selected_target)
        route_buttons.addWidget(use_selected)
        route_buttons.addStretch(1)
        routing_grid.addLayout(route_buttons, 1, 1)

        target = QFrame()
        target.setObjectName("Inner")
        target_layout = QVBoxLayout(target)
        target_layout.setContentsMargins(16, 14, 16, 14)
        target_layout.setSpacing(10)

        target_head = QLabel("Target Output")
        target_head.setObjectName("SectionLead")
        target_layout.addWidget(target_head)
        self.target_name = QLabel("-")
        self.target_name.setObjectName("TargetName")
        self.target_name.setWordWrap(True)
        target_layout.addWidget(self.target_name)

        pills = QHBoxLayout()
        self.route_pill = QLabel("Virtual Route")
        self.swap_pill = QLabel("Swap")
        self.eq_pill = QLabel("EQ")
        pills.addWidget(self.route_pill)
        pills.addWidget(self.swap_pill)
        pills.addWidget(self.eq_pill)
        target_layout.addLayout(pills)

        desc = QLabel("Virtual route is active when default output is L/R Swaper. Use Fix Streams if an app still plays direct.")
        desc.setObjectName("Small")
        desc.setStyleSheet("color:#a9b8d6; background:transparent; line-height:1.35em;")
        desc.setWordWrap(True)
        target_layout.addWidget(desc)
        target_layout.addStretch(1)
        routing_grid.addWidget(target, 1, 2)

        routing_grid.setColumnStretch(0, 5)
        routing_grid.setColumnStretch(1, 0)
        routing_grid.setColumnStretch(2, 3)
        content_layout.addWidget(routing)

        # Middle row
        middle = QGridLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setHorizontalSpacing(10)
        middle.setVerticalSpacing(10)

        sound = card("SOUND CONTROLS")
        sound.setMinimumHeight(320)
        sound_layout = sound.layout()
        self.add_slider(sound_layout, "Volume", 0, 150, self.schedule_volume, "volume")
        self.add_slider(sound_layout, "Bass", 0, 100, self.schedule_tone, "bass")
        self.add_slider(sound_layout, "Treble", 0, 100, self.schedule_tone, "treble")
        self.add_slider(sound_layout, "L / R Balance", 0, 100, self.schedule_balance, "balance")

        sound_bottom = QHBoxLayout()
        sound_bottom.setContentsMargins(2, 2, 2, 2)
        sound_bottom.setSpacing(10)
        reset = QPushButton("Reset Neutral")
        reset.clicked.connect(self.neutral_gui)
        sound_bottom.addWidget(reset)
        sound_bottom.addStretch(1)
        ok_label = QLabel("Neutral keeps volume unchanged")
        ok_label.setStyleSheet(f"color:{GREEN}; background:transparent; font-weight:700;")
        sound_bottom.addWidget(ok_label)
        sound_layout.addStretch(1)
        sound_layout.addLayout(sound_bottom)
        middle.addWidget(sound, 0, 0)

        quick = card("QUICK ACTIONS")
        quick.setMinimumHeight(320)
        quick_grid = QGridLayout()
        quick_grid.setContentsMargins(0, 2, 0, 2)
        quick_grid.setHorizontalSpacing(10)
        quick_grid.setVerticalSpacing(10)
        quick.layout().addLayout(quick_grid)

        self.swap_btn = QPushButton("Swap L/R")
        self.swap_btn.setObjectName("ActionButton")
        self.swap_btn.clicked.connect(lambda: self.toggle_swap("A"))
        quick_grid.addWidget(self.swap_btn, 0, 0)

        self.alt_swap_btn = QPushButton("Alt Swap")
        self.alt_swap_btn.setObjectName("ActionButton")
        self.alt_swap_btn.clicked.connect(lambda: self.toggle_swap("B"))
        quick_grid.addWidget(self.alt_swap_btn, 0, 1)

        set_default = QPushButton("Set Default")
        set_default.setObjectName("ActionButton")
        set_default.clicked.connect(self.set_default)
        quick_grid.addWidget(set_default, 1, 0)

        fix = QPushButton("Fix Streams")
        fix.setObjectName("ActionButton")
        fix.clicked.connect(self.fix_streams)
        quick_grid.addWidget(fix, 1, 1)

        diag2 = QPushButton("Diagnostics")
        diag2.setObjectName("ActionButton")
        diag2.clicked.connect(self.show_diagnostics)
        quick_grid.addWidget(diag2, 2, 0)

        disable = QPushButton("Disable")
        disable.setObjectName("ActionButton")
        disable.clicked.connect(self.disable_gui)
        quick_grid.addWidget(disable, 2, 1)

        hint = QLabel("Swap buttons are press-again-to-release toggles.")
        hint.setObjectName("Small")
        hint.setWordWrap(True)
        quick.layout().addStretch(1)
        quick.layout().addWidget(hint)
        middle.addWidget(quick, 0, 1)

        test = card("L / R TEST")
        test.setMinimumHeight(320)
        test_layout = test.layout()
        left = QPushButton("Left")
        left.setObjectName("TestButton")
        left.clicked.connect(lambda: self.play_test("left"))
        right = QPushButton("Right")
        right.setObjectName("TestButton")
        right.clicked.connect(lambda: self.play_test("right"))
        both = QPushButton("Both")
        both.setObjectName("TestButton")
        both.clicked.connect(lambda: self.play_test("lr"))
        test_layout.addWidget(left)
        test_layout.addWidget(right)
        test_layout.addWidget(both)
        test_hint = QLabel("After swap, Left should come from the right speaker.")
        test_hint.setObjectName("Small")
        test_hint.setWordWrap(True)
        test_layout.addStretch(1)
        test_layout.addWidget(test_hint)
        middle.addWidget(test, 0, 2)

        middle.setColumnStretch(0, 5)
        middle.setColumnStretch(1, 3)
        middle.setColumnStretch(2, 3)
        content_layout.addLayout(middle)

        # Presets
        presets = card("PRESETS")
        preset_grid = QGridLayout()
        preset_grid.setSpacing(10)
        presets.layout().addLayout(preset_grid)
        for i in range(3):
            preset_grid.addWidget(self.preset_card(i + 1), 0, i)
        content_layout.addWidget(presets)

        # Help/info
        info = card("HELP & INFO")
        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        info.layout().addLayout(info_grid)
        for i, (title, body) in enumerate([
            ("Start / Swap", "Begin routing through L/R Swaper."),
            ("Adjust EQ and L/R", "Tune sound and balance."),
            ("Fix Streams", "Move apps to the virtual route."),
            ("Local Only", "No data is sent anywhere."),
        ]):
            box = QFrame()
            box.setObjectName("Inner")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(14, 12, 14, 12)
            h = QLabel(title)
            h.setStyleSheet("font-weight:700; background:transparent;")
            b = QLabel(body)
            b.setObjectName("Small")
            b.setWordWrap(True)
            box_layout.addWidget(h)
            box_layout.addWidget(b)
            info_grid.addWidget(box, 0, i)
        content_layout.addWidget(info)

        # Footer
        footer = QFrame()
        footer.setObjectName("Card")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 8, 14, 8)
        self.status = QLabel("Status: Ready")
        self.status.setObjectName("Status")
        footer_layout.addWidget(self.status, 1)
        footer_label = QLabel("L/R Swaper v5.1  |  Local Only  |  No Data Sent")
        footer_label.setStyleSheet(f"color:{CYAN}; background:transparent; font-weight:700;")
        footer_layout.addWidget(footer_label)
        root_layout.addWidget(footer)

    def add_slider(self, layout, label, minimum, maximum, callback, key):
        row = QFrame()
        row.setObjectName("Inner")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 12, 16, 12)
        row_layout.setSpacing(12)

        name = QLabel(label)
        name.setObjectName("SliderName")
        name.setFixedWidth(128)
        row_layout.addWidget(name)

        slider = NoWheelSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.NoFocus)
        slider.setRange(minimum, maximum)
        slider.valueChanged.connect(callback)
        row_layout.addSpacing(4)
        row_layout.addWidget(slider, 1)
        row_layout.addSpacing(6)

        value = QLabel("")
        value.setObjectName("ValueBox")
        value.setAlignment(Qt.AlignCenter)
        value.setFixedWidth(128)
        row_layout.addWidget(value)

        if key == "volume":
            self.volume_slider = slider
            self.volume_value = value
        elif key == "bass":
            self.bass_slider = slider
            self.bass_value = value
        elif key == "treble":
            self.treble_slider = slider
            self.treble_value = value
        elif key == "balance":
            self.balance_slider = slider
            self.balance_value = value

        layout.addWidget(row)

    def preset_card(self, slot: int) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Inner")
        layout = QGridLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        colors = [BLUE, MAGENTA, ORANGE]

        badge = QLabel(str(slot))
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(42, 42)
        badge.setStyleSheet(f"background:{colors[slot-1]}; color:white; border-radius:12px; font-weight:800; font-size:16pt;")
        layout.addWidget(badge, 0, 0, 2, 1)

        title = QLabel(f"Preset {slot}")
        title.setStyleSheet("font-weight:700; background:transparent;")
        layout.addWidget(title, 0, 1)

        subtitle = QLabel("Volume independent")
        subtitle.setObjectName("Small")
        layout.addWidget(subtitle, 1, 1)

        save = QPushButton("Save")
        save.clicked.connect(lambda: self.save_preset(slot))
        layout.addWidget(save, 2, 0, 1, 2)

        load = QPushButton("Load")
        load.clicked.connect(lambda: self.load_preset(slot))
        layout.addWidget(load, 3, 0, 1, 2)
        return frame

    # ---------------- Backend ----------------

    def set_status(self, text):
        self.status.setText(f"Status: {text}")

    def classify_sink(self, sink):
        if sink.get("is_eq"):
            return "Tone/EQ"
        if sink.get("is_app"):
            return "Swapped"
        name = sink.get("name", "")
        desc = sink.get("description", "")
        if name.startswith("bluez_output."):
            return "Bluetooth"
        if "usb" in name.lower():
            return "USB"
        if "hdmi" in desc.lower() or "nvidia" in desc.lower() or "radeon" in desc.lower():
            return "HDMI/Display"
        return "System"

    def refresh(self):
        try:
            self.sinks = backend.all_sinks()
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return

        self.table.setRowCount(len(self.sinks))
        for row, sink in enumerate(self.sinks):
            values = [
                "*" if sink.get("is_default") else "",
                self.classify_sink(sink),
                sink.get("description", sink.get("name", "")),
                sink.get("state", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        default_row = next((i for i, s in enumerate(self.sinks) if s.get("is_default")), 0 if self.sinks else -1)
        if default_row >= 0:
            self.table.selectRow(default_row)
            self.selected_row = default_row

        self.target_name.setText(backend.get_target_description())
        self.sync_sliders()
        self.update_status()
        self.update_swap_buttons()
        self.set_status("Ready")

    def on_table_selection(self):
        indexes = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if indexes:
            self.selected_row = indexes[0].row()

    def selected_sink(self):
        if self.selected_row < 0 or self.selected_row >= len(self.sinks):
            QMessageBox.warning(self, APP_NAME, "Select an output first.")
            return None
        return self.sinks[self.selected_row]

    def sync_sliders(self):
        state = backend.load_state()
        self.volume_slider.blockSignals(True)
        self.bass_slider.blockSignals(True)
        self.treble_slider.blockSignals(True)
        self.balance_slider.blockSignals(True)

        self.volume_slider.setValue(int(round(backend.clamp_system_volume(state.get("system_volume", backend.get_current_output_volume_percent())))))
        self.bass_slider.setValue(int(round(backend.db_to_tone_slider_value(state.get("bass_db", 0.0)))))
        self.treble_slider.setValue(int(round(backend.db_to_tone_slider_value(state.get("treble_db", 0.0)))))
        self.balance_slider.setValue(int(round(backend.clamp_balance(state.get("balance_value", 50)))))

        self.volume_slider.blockSignals(False)
        self.bass_slider.blockSignals(False)
        self.treble_slider.blockSignals(False)
        self.balance_slider.blockSignals(False)
        self.update_slider_labels()

    def compact_balance_text(self, value):
        try:
            value = int(round(float(value)))
        except Exception:
            value = 50
        value = max(0, min(100, value))
        if value < 50:
            left = 100
            right = int(round((value / 50) * 100))
        elif value > 50:
            left = int(round(((100 - value) / 50) * 100))
            right = 100
        else:
            left = 100
            right = 100
        return f"L:{left}%  R:{right}%"

    def update_slider_labels(self):
        self.volume_value.setText(f"{self.volume_slider.value()}%")
        self.bass_value.setText(f"{backend.tone_slider_value_to_db(self.bass_slider.value()):+.1f} dB")
        self.treble_value.setText(f"{backend.tone_slider_value_to_db(self.treble_slider.value()):+.1f} dB")
        self.balance_value.setText(self.compact_balance_text(self.balance_slider.value()))

    def update_status(self):
        state = backend.load_state()
        cur = backend.default_sink()
        route_active = bool(cur and backend.is_our_sink(cur))
        swap_active = bool(state.get("swapped_sink_name") and backend.sink_exists(state.get("swapped_sink_name")))
        eq_active = bool(
            (state.get("eq_sink_name") and backend.sink_exists(state.get("eq_sink_name")))
            or abs(float(state.get("bass_db", 0.0) or 0.0)) > 0.05
            or abs(float(state.get("treble_db", 0.0) or 0.0)) > 0.05
        )

        self.set_pill(self.route_pill, "Virtual Route: Active" if route_active else "Virtual Route: Inactive", route_active)
        self.set_pill(self.swap_pill, "Swap: On" if swap_active else "Swap: Off", swap_active)
        self.set_pill(self.eq_pill, "EQ: On" if eq_active else "EQ: Off", eq_active)

    def set_pill(self, pill: QLabel, text: str, active: bool):
        pill.setText(text)
        pill.setObjectName("PillOn" if active else "PillOff")
        pill.style().unpolish(pill)
        pill.style().polish(pill)

    def active_swap_mode(self):
        state = backend.load_state()
        swapped = state.get("swapped_sink_name")
        if swapped and backend.sink_exists(swapped):
            return str(state.get("mode", "A") or "A").upper()
        return None

    def update_swap_buttons(self):
        active = self.active_swap_mode()
        for btn, mode, base_text in [(self.swap_btn, "A", "Swap L/R"), (self.alt_swap_btn, "B", "Alt Swap")]:
            if active == mode:
                btn.setText(base_text + " ON")
                btn.setObjectName("Active")
            else:
                btn.setText(base_text)
                btn.setObjectName("")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def start_swap(self):
        ok, _sink, msg = backend.load_swap(backend.current_master_candidate(), "A")
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def toggle_swap(self, mode):
        mode = str(mode or "A").upper()
        if self.active_swap_mode() == mode:
            ok, msg = backend.remove_swap_preserving_settings()
            self.refresh()
            if ok:
                self.set_status(msg)
            else:
                QMessageBox.critical(self, APP_NAME, msg)
            return

        sink = self.selected_sink()
        if sink and not backend.is_our_sink(sink["name"]):
            backend.remember_target_sink(sink["name"])
            master = sink["name"]
        else:
            master = backend.current_master_candidate()
        ok, _sink, msg = backend.load_swap(master, mode)
        self.refresh()
        if ok:
            self.set_status(f"Swap mode {mode} enabled. Press again to release.")
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def use_selected_target(self):
        sink = self.selected_sink()
        if not sink:
            return
        ok, msg = backend.remember_target_sink(sink["name"])
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def set_default(self):
        sink = self.selected_sink()
        if not sink:
            return
        if not backend.is_our_sink(sink["name"]):
            backend.remember_target_sink(sink["name"])
        ok, msg = backend.set_default_and_move(sink["name"])
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def fix_streams(self):
        ok, msg = backend.fix_now()
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def disable_gui(self):
        count, msg = backend.restore_output_and_unload()
        self.refresh()
        self.set_status(msg or f"Disabled {count} module(s).")

    def neutral_gui(self):
        ok, msg = backend.reset_to_neutral_settings()
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def schedule_volume(self):
        self.update_slider_labels()
        self._volume_timer.start(180)

    def apply_volume(self):
        ok, msg = backend.apply_system_volume_value(self.volume_slider.value())
        if ok:
            state = backend.load_state()
            state["system_volume"] = backend.clamp_system_volume(self.volume_slider.value())
            backend.save_state(state)
            self.set_status(f"Volume {self.volume_slider.value()}%")
        else:
            self.set_status(msg)

    def schedule_tone(self):
        self.update_slider_labels()
        self._tone_timer.start(450)

    def apply_tone(self):
        ok, msg = backend.apply_tone_values(
            backend.tone_slider_value_to_db(self.bass_slider.value()),
            backend.tone_slider_value_to_db(self.treble_slider.value()),
        )
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def schedule_balance(self):
        self.update_slider_labels()
        self._balance_timer.start(180)

    def apply_balance(self):
        ok, msg = backend.apply_balance_value(self.balance_slider.value())
        if ok:
            state = backend.load_state()
            state["balance_value"] = backend.clamp_balance(self.balance_slider.value())
            backend.save_state(state)
            self.set_status("L/R balance updated.")
        else:
            self.set_status(msg)

    def play_test(self, which):
        ok, msg = backend.play_test(which)
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def save_preset(self, slot):
        state = backend.load_state()
        state["balance_value"] = backend.clamp_balance(self.balance_slider.value())
        state["bass_db"] = backend.tone_slider_value_to_db(self.bass_slider.value())
        state["treble_db"] = backend.tone_slider_value_to_db(self.treble_slider.value())
        state["volume_independent_presets"] = True
        backend.save_state(state)
        settings = backend.save_user_settings(slot)
        target = settings.get("target_description") or settings.get("target_sink_name") or "none"
        self.set_status(f"Saved preset {slot} without volume. Target: {target}.")

    def load_preset(self, slot):
        ok, msg = backend.apply_user_settings(slot=slot)
        self.refresh()
        if ok:
            self.set_status(msg)
        else:
            QMessageBox.critical(self, APP_NAME, msg)

    def show_diagnostics(self):
        win = QMainWindow(self)
        win.setWindowTitle("L/R Swaper Diagnostics")
        win.resize(900, 600)
        text = QTextEdit()
        text.setPlainText(backend.diagnostics())
        text.setReadOnly(True)
        win.setCentralWidget(text)
        win.show()
        self._diag_window = win

    def show_help(self):
        text = 'L/R Swaper v5.1\n\nWhat this app does:\n• Swaps left and right audio channels on Linux.\n• Lets you test Left / Right / Both channels.\n• Provides volume, bass, treble, and balance controls.\n• Includes Plain Theme and Tihuluwave Theme.\n\nHow to use:\n1. Select your real output device from the list.\n2. Click Use Selected.\n3. Click Swap L/R or Alt Swap.\n4. Use Disable to restore normal audio.\n\nRepository / future updates:\nhttps://github.com/Tihulu/L-R-Swaper-and-EQ\n\nQuick install from GitHub:\nbash <(curl -fsSL https://raw.githubusercontent.com/Tihulu/L-R-Swaper-and-EQ/main/linux/quick-install.sh)'

        box = QMessageBox(self)
        box.setWindowTitle("L/R Swaper Help")
        box.setIcon(QMessageBox.Information)
        box.setText(text)
        box.setTextFormat(Qt.PlainText)
        box.setMinimumWidth(760)
        box.exec()

    def switch_plain(self):
        save_theme(THEME_PLAIN)
        restart_launcher()

    def closeEvent(self, event):
        try:
            backend.restore_output_and_unload()
        finally:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("L/R Swaper")
    app.setApplicationDisplayName("L/R Swaper")
    app.setDesktopFileName("com.tihulu.lr-swaper")
    icon_path = HERE / "icons" / "lr-swaper-256.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = TihuluwaveQt()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
