#!/usr/bin/env python3
"""Clean dashboard UI entry point for L/R Swaper Mac.

This keeps the existing audio engine from lr_swaper_mac.py and only replaces
how the window is arranged.
"""

from lr_swaper_mac import *


class CleanApp(App):
    def configure_style(self):
        try:
            style = ttk.Style(self)
            style.configure("Card.TLabelframe", padding=10)
            style.configure("Hero.TLabel", font=("TkDefaultFont", 22, "bold"))
            style.configure("Subtle.TLabel", foreground="#5f6b7a")
            style.configure("Status.TLabel", padding=(14, 8))
            style.configure("Primary.TButton", padding=(14, 8))
            style.configure("Compact.TButton", padding=(10, 5))
        except Exception:
            pass

    def build_ui(self):
        self.configure_style()
        self.geometry("900x680")
        self.minsize(760, 500)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.scroll_canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
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

        def _on_mousewheel(event):
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

        header = ttk.Frame(self.page)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        title_row = ttk.Frame(header)
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="L/R Swaper", style="Hero.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title_row, text=VERSION, style="Subtle.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(
            header,
            text="System audio EQ, L/R balance and channel swap for macOS.",
            style="Subtle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        routing = ttk.LabelFrame(self.page, text="Routing", style="Card.TLabelframe", padding=12)
        routing.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        routing.columnconfigure(1, weight=1)

        ttk.Label(routing, text="Output").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 8))
        self.output_menu = ttk.OptionMenu(routing, self.output_var, "")
        self.output_menu.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        route_buttons = ttk.Frame(routing)
        route_buttons.grid(row=0, column=2, sticky="e", padx=(12, 0), pady=(0, 8))
        self.start_button = ttk.Button(route_buttons, text="Start", style="Primary.TButton", command=self.start_audio)
        self.start_button.grid(row=0, column=0, padx=(0, 6))
        self.stop_button = ttk.Button(route_buttons, text="Stop", style="Compact.TButton", command=self.stop_audio)
        self.stop_button.grid(row=0, column=1, padx=(0, 6))
        self.refresh_button = ttk.Button(route_buttons, text="Refresh", style="Compact.TButton", command=self.refresh_devices)
        self.refresh_button.grid(row=0, column=2)

        ttk.Label(routing, textvariable=self.input_status_var, style="Subtle.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(2, 6)
        )

        meter_frame = ttk.Frame(routing)
        meter_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        meter_frame.columnconfigure(0, weight=1)

        self.meter_var = tk.StringVar(value="Signal: waiting")
        self.meter_bar = ttk.Progressbar(meter_frame, maximum=100, value=0)
        self.meter_bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(meter_frame, textvariable=self.meter_var, style="Subtle.TLabel").grid(
            row=1, column=0, sticky="w", pady=(3, 0)
        )

        main = ttk.Frame(self.page)
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)

        controls = ttk.LabelFrame(main, text="Sound Controls", style="Card.TLabelframe", padding=12)
        controls.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10), pady=(0, 10))
        controls.columnconfigure(0, weight=1)

        self.volume_slider = ValueSlider(controls, "Volume", self.volume_var, 0, 100, lambda v: f"{int(round(v))}%", self.on_settings_change)
        self.volume_slider.grid(row=0, column=0, sticky="ew", pady=7)
        self.bass_slider = ValueSlider(controls, "Bass", self.bass_var, 0, 100, lambda v: f"{tone_slider_to_db(v):+.1f} dB", self.on_settings_change)
        self.bass_slider.grid(row=1, column=0, sticky="ew", pady=7)
        self.treble_slider = ValueSlider(controls, "Treble", self.treble_var, 0, 100, lambda v: f"{tone_slider_to_db(v):+.1f} dB", self.on_settings_change)
        self.treble_slider.grid(row=2, column=0, sticky="ew", pady=7)
        self.balance_slider = ValueSlider(controls, "L / R", self.balance_var, 0, 100, self.format_balance, self.on_settings_change)
        self.balance_slider.grid(row=3, column=0, sticky="ew", pady=7)

        quick = ttk.LabelFrame(main, text="Quick Actions", style="Card.TLabelframe", padding=12)
        quick.grid(row=0, column=1, sticky="new", pady=(0, 10))
        quick.columnconfigure(0, weight=1)
        quick.columnconfigure(1, weight=1)

        ttk.Checkbutton(quick, text="Swap L/R", variable=self.swap_var, command=self.on_settings_change).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        ttk.Checkbutton(quick, text="Mute", variable=self.muted_var, command=self.on_settings_change).grid(
            row=0, column=1, sticky="w", pady=(0, 8)
        )
        ttk.Button(quick, text="Neutral", style="Compact.TButton", command=self.neutral).grid(
            row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        ttk.Button(quick, text="Save State", style="Compact.TButton", command=self.save_state).grid(
            row=1, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        ttk.Button(quick, text="Diagnostics", style="Compact.TButton", command=self.show_diagnostics).grid(
            row=2, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(quick, text="Mic Permission", style="Compact.TButton", command=self.show_permission_help).grid(
            row=2, column=1, sticky="ew", padx=(6, 0)
        )

        tone_card = ttk.LabelFrame(main, text="L/R Test", style="Card.TLabelframe", padding=12)
        tone_card.grid(row=1, column=1, sticky="ew", pady=(0, 10))
        tone_card.columnconfigure(0, weight=1)
        tone_card.columnconfigure(1, weight=1)
        tone_card.columnconfigure(2, weight=1)
        ttk.Button(tone_card, text="Left", style="Compact.TButton", command=lambda: self.play_lr_test("left")).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(tone_card, text="Right", style="Compact.TButton", command=lambda: self.play_lr_test("right")).grid(
            row=0, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(tone_card, text="Both", style="Compact.TButton", command=lambda: self.play_lr_test("both")).grid(
            row=0, column=2, sticky="ew"
        )

        presets = ttk.LabelFrame(self.page, text="Presets", style="Card.TLabelframe", padding=12)
        presets.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        for col in range(6):
            presets.columnconfigure(col, weight=1)
        for i in range(3):
            ttk.Label(presets, text=f"Slot {i+1}").grid(row=0, column=i * 2, sticky="e", padx=(0, 4))
            ttk.Button(presets, text="Save", style="Compact.TButton", command=lambda slot=i+1: self.save_preset(slot)).grid(
                row=0, column=i * 2 + 1, sticky="ew", padx=(0, 10)
            )
            ttk.Button(presets, text="Load", style="Compact.TButton", command=lambda slot=i+1: self.load_preset(slot)).grid(
                row=1, column=i * 2 + 1, sticky="ew", padx=(0, 10), pady=(6, 0)
            )

        help_card = ttk.LabelFrame(self.page, text="Help", style="Card.TLabelframe", padding=12)
        help_card.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        help_card.columnconfigure(0, weight=1)
        ttk.Label(
            help_card,
            justify="left",
            wraplength=820,
            style="Subtle.TLabel",
            text=(
                "Use a real speaker/headphone as Output. The app uses BlackHole automatically in the background. "
                "If Signal stays 0%, open Mic Permission and enable L-R Swaper Mac in macOS Privacy settings."
            ),
        ).grid(row=0, column=0, sticky="ew")

        self.status = ttk.Label(self.page, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        self.status.grid(row=5, column=0, sticky="ew")


def main():
    if sd is None or np is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            APP_NAME,
            "Missing bundled dependencies: sounddevice/numpy. Rebuild the standalone app.",
        )
        return 2
    CleanApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
