#!/usr/bin/env python3
"""Tihuluwave Qt UI for L/R Swaper Linux v4.9."""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lr_backend", HERE / "lr_swaper_tihuluwave.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QIcon, QPixmap
    from PySide6.QtWidgets import (
        QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
        QMessageBox, QPushButton, QScrollArea, QSlider, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView
    )
except Exception as exc:
    print("PySide6 is required for Tihuluwave Theme.", file=sys.stderr)
    print("Run install.sh again or install PySide6.", file=sys.stderr)
    print(exc, file=sys.stderr)
    raise SystemExit(2)

BG = "#070b18"
PANEL = "#0d1425"
PANEL2 = "#121b31"
PANEL3 = "#17223a"
BORDER = "#243451"
TEXT = "#f4f7fb"
MUTED = "#9aa8bd"
CYAN = "#1fc8ff"
MAGENTA = "#d94cff"
GREEN = "#25e070"


class NoWheelSlider(QSlider):
    def wheelEvent(self, event):
        event.ignore()


def card(title):
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    label = QLabel(title)
    label.setObjectName("CardTitle")
    layout.addWidget(label)
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet("background:#18243c; border:none;")
    layout.addWidget(line)
    return frame


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sinks = []
        self.setWindowTitle("L/R Swaper v4.9 - Tihuluwave Theme")
        self.resize(1180, 760)
        icon = HERE / "icons" / "lr-swaper-256.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        QApplication.instance().setFont(QFont("Noto Sans", 10))
        QApplication.instance().setDesktopFileName("com.tihulu.lr-swaper")
        self.apply_style()
        self.build_ui()
        self.refresh()

    def apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{BG}; color:{TEXT}; font-family:"Noto Sans","DejaVu Sans",sans-serif; }}
            QFrame#Card {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:18px; }}
            QFrame#Inner {{ background:{PANEL2}; border:1px solid {BORDER}; border-radius:13px; }}
            QLabel#Title {{ font-size:24pt; font-weight:800; }}
            QLabel#Subtitle {{ color:{MUTED}; }}
            QLabel#CardTitle {{ color:{CYAN}; font-weight:800; font-size:12pt; letter-spacing:0.4px; }}
            QLabel#Small {{ color:{MUTED}; background:transparent; }}
            QLabel#TargetName {{ color:{MAGENTA}; font-weight:800; font-size:13pt; background:transparent; }}
            QPushButton {{ background:{PANEL2}; color:{TEXT}; border:1px solid {BORDER}; border-radius:14px; padding:10px 14px; font-weight:700; min-height:26px; }}
            QPushButton:hover {{ background:{PANEL3}; border-color:{CYAN}; }}
            QPushButton#Primary {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {CYAN},stop:1 {MAGENTA}); color:white; border:1px solid {CYAN}; min-height:42px; }}
            QPushButton#Active {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1478ff,stop:1 {MAGENTA}); color:white; border:1px solid {CYAN}; }}
            QTableWidget {{ background:{PANEL2}; border:1px solid {BORDER}; border-radius:14px; gridline-color:#1b2940; selection-background-color:#113b70; alternate-background-color:#0f1728; padding:4px; }}
            QHeaderView::section {{ background:#18243c; color:{TEXT}; border:none; border-bottom:1px solid {BORDER}; padding:8px; font-weight:700; }}
            QSlider::groove:horizontal {{ background:#344052; height:6px; border-radius:3px; }}
            QSlider::sub-page:horizontal {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {CYAN},stop:1 {MAGENTA}); border-radius:3px; }}
            QSlider::handle:horizontal {{ background:#f3d8ff; border:1px solid {MAGENTA}; width:18px; height:18px; margin:-7px 0; border-radius:9px; }}
            QScrollBar:vertical {{ background:#0d1728; width:13px; border-left:1px solid #1d2b42; }}
            QScrollBar::handle:vertical {{ background:#4e6fa3; min-height:38px; border-radius:6px; margin:2px; }}
            QScrollBar::handle:vertical:hover {{ background:{CYAN}; }}
        """)

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(18, 14, 18, 10)
        main.setSpacing(10)

        header = QHBoxLayout()
        logo = QLabel("L/R")
        logo.setFixedSize(56, 56)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"background:{PANEL2}; border:1px solid {BORDER}; border-radius:18px; color:{CYAN}; font-size:16pt; font-weight:800;")
        pix_path = HERE / "icons" / "lr-swaper-256.png"
        if pix_path.exists():
            pix = QPixmap(str(pix_path))
            if not pix.isNull():
                logo.setPixmap(pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(logo)

        titles = QVBoxLayout()
        title = QLabel("L/R Swaper"); title.setObjectName("Title")
        subtitle = QLabel("Linux  -  Tihuluwave Theme"); subtitle.setObjectName("Subtitle")
        titles.addWidget(title); titles.addWidget(subtitle)
        header.addLayout(titles, 1)

        plain = QPushButton("Plain Theme")
        plain.clicked.connect(self.switch_plain)
        header.addWidget(plain)
        active = QPushButton("Tihuluwave Theme")
        active.setObjectName("Active")
        header.addWidget(active)
        help_btn = QPushButton("Help")
        help_btn.clicked.connect(self.show_help)
        header.addWidget(help_btn)
        main.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)
        scroll.setWidget(content)
        main.addWidget(scroll, 1)

        routing = card("ROUTING & SIGNAL")
        rgrid = QGridLayout()
        rgrid.setSpacing(14)
        routing.layout().addLayout(rgrid)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Default", "Type", "Output", "State"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(220)
        rgrid.addWidget(self.table, 0, 0)

        route_btns = QVBoxLayout()
        for text, slot, primary in [
            ("Start", self.start_swap, True),
            ("Stop", self.disable, False),
            ("Refresh", self.refresh, False),
            ("Use selected", self.use_selected, False),
        ]:
            b = QPushButton(text)
            if primary: b.setObjectName("Primary")
            b.clicked.connect(slot)
            route_btns.addWidget(b)
        route_btns.addStretch(1)
        rgrid.addLayout(route_btns, 0, 1)

        target = QFrame(); target.setObjectName("Inner")
        tl = QVBoxLayout(target); tl.setContentsMargins(16, 14, 16, 14)
        tl.addWidget(QLabel("Target Output"))
        self.target_name = QLabel("-"); self.target_name.setObjectName("TargetName"); self.target_name.setWordWrap(True)
        tl.addWidget(self.target_name)
        self.pills = QLabel("Virtual Route  /  Swap  /  EQ"); self.pills.setObjectName("Small")
        tl.addWidget(self.pills)
        desc = QLabel("Use selected output as target, then start swap or adjust sound controls.")
        desc.setObjectName("Small"); desc.setWordWrap(True)
        tl.addWidget(desc); tl.addStretch(1)
        rgrid.addWidget(target, 0, 2)
        rgrid.setColumnStretch(0, 5); rgrid.setColumnStretch(1, 0); rgrid.setColumnStretch(2, 3)
        body.addWidget(routing)

        mid = QGridLayout()
        mid.setHorizontalSpacing(10)
        sound = card("SOUND CONTROLS")
        self.volume = self.add_slider(sound.layout(), "Volume", 0, 150, 100, self.volume_changed)
        self.bass = self.add_slider(sound.layout(), "Bass", 0, 100, 50, self.tone_changed)
        self.treble = self.add_slider(sound.layout(), "Treble", 0, 100, 50, self.tone_changed)
        self.balance = self.add_slider(sound.layout(), "L / R Balance", 0, 100, 50, self.balance_changed)
        reset = QPushButton("Reset Neutral"); reset.clicked.connect(self.neutral)
        sound.layout().addWidget(reset)
        mid.addWidget(sound, 0, 0)

        quick = card("QUICK ACTIONS")
        qg = QGridLayout(); qg.setSpacing(10); quick.layout().addLayout(qg)
        for i, (text, slot) in enumerate([
            ("Swap L/R", lambda: self.swap("A")),
            ("Alt Swap", lambda: self.swap("B")),
            ("Set Default", self.set_default),
            ("Fix Streams", self.fix),
            ("Diagnostics", self.diagnostics),
            ("Disable", self.disable),
        ]):
            b = QPushButton(text); b.clicked.connect(slot)
            qg.addWidget(b, i // 2, i % 2)
        hint = QLabel("Swap buttons are press-again-to-release toggles."); hint.setObjectName("Small"); hint.setWordWrap(True)
        quick.layout().addStretch(1); quick.layout().addWidget(hint)
        mid.addWidget(quick, 0, 1)

        test = card("L / R TEST")
        for text, side in [("Left", "left"), ("Right", "right"), ("Both", "both")]:
            b = QPushButton(text); b.clicked.connect(lambda checked=False, s=side: self.run(lambda: backend.play_test(s)[1]))
            test.layout().addWidget(b)
        test.layout().addStretch(1)
        mid.addWidget(test, 0, 2)
        mid.setColumnStretch(0, 5); mid.setColumnStretch(1, 3); mid.setColumnStretch(2, 2)
        body.addLayout(mid)

        footer = QFrame(); footer.setObjectName("Card")
        fl = QHBoxLayout(footer); fl.setContentsMargins(14, 8, 14, 8)
        self.status = QLabel("Status: Ready")
        fl.addWidget(self.status, 1)
        foot = QLabel("L/R Swaper v4.9  |  Local Only  |  No Data Sent")
        foot.setStyleSheet(f"color:{CYAN}; background:transparent; font-weight:700;")
        fl.addWidget(foot)
        main.addWidget(footer)

    def add_slider(self, layout, label, minimum, maximum, value, callback):
        row = QFrame(); row.setObjectName("Inner")
        r = QHBoxLayout(row); r.setContentsMargins(16, 12, 16, 12)
        name = QLabel(label); name.setFixedWidth(120); r.addWidget(name)
        s = NoWheelSlider(Qt.Horizontal); s.setRange(minimum, maximum); s.setValue(value); s.valueChanged.connect(callback)
        r.addWidget(s, 1)
        layout.addWidget(row)
        return s

    def current_sink_name(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.sinks):
            return ""
        return self.sinks[row]["name"]

    def set_status(self, msg):
        self.status.setText(f"Status: {msg}")

    def run(self, func):
        try:
            msg = func()
            self.set_status(str(msg))
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, backend.APP_NAME, str(exc))

    def refresh(self):
        self.sinks = backend.all_sinks()
        self.table.setRowCount(len(self.sinks))
        for row, sink in enumerate(self.sinks):
            vals = [
                "*" if sink.get("is_default") else "",
                "L/R" if backend.is_our_sink(sink["name"]) else "Output",
                sink.get("description", sink["name"]),
                "Default" if sink.get("is_default") else "Ready",
            ]
            for col, val in enumerate(vals):
                self.table.setItem(row, col, QTableWidgetItem(val))
        self.target_name.setText(backend.get_target_description())

    def use_selected(self):
        name = self.current_sink_name()
        ok, msg = backend.remember_target_sink(name)
        self.set_status(msg)
        self.refresh()

    def start_swap(self): self.swap("A")
    def swap(self, mode): self.run(lambda: backend.load_swap(mode=mode)[2])
    def disable(self): self.run(lambda: backend.restore_output_and_unload()[1])
    def fix(self): self.run(lambda: backend.fix_now()[1])
    def set_default(self): self.run(lambda: backend.set_default_and_move(self.current_sink_name())[1])
    def neutral(self): self.run(lambda: backend.reset_to_neutral_settings()[1])
    def diagnostics(self): QMessageBox.information(self, backend.APP_NAME, backend.diagnostics())
    def volume_changed(self, v): backend.apply_system_volume_value(v)
    def balance_changed(self, v): backend.apply_balance_value(v)
    def tone_changed(self, _): backend.apply_tone_values(backend.tone_slider_value_to_db(self.bass.value()), backend.tone_slider_value_to_db(self.treble.value()))

    def switch_plain(self):
        backend.save_theme_name(backend.THEME_PLAIN)
        self.close()

    def show_help(self):
        QMessageBox.information(
            self,
            backend.APP_NAME,
            "Tihuluwave Theme uses the Qt modern interface.\n\n"
            "Repository:\n"
            f"{backend.REPOSITORY_URL}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    raise SystemExit(app.exec())
