#!/usr/bin/env python3
"""Classic Plain Theme for L/R Swaper Linux."""
from pathlib import Path
import importlib.util
import tkinter as tk
from tkinter import messagebox, ttk

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lr_backend", HERE / "lr_swaper_tihuluwave.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class PlainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("L/R Swaper v4.9 - Plain Theme")
        self.geometry("760x560")
        self.configure(padx=14, pady=14)
        self.target = tk.StringVar(value=backend.get_target_description())
        ttk.Label(self, text="L/R Swaper", font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        ttk.Label(self, text="Plain Theme - classic Linux controls").pack(anchor="w", pady=(0, 12))
        row = ttk.Frame(self); row.pack(fill="x", pady=4)
        ttk.Button(row, text="Tihuluwave Theme", command=self.switch_tw).pack(side="left")
        ttk.Button(row, text="Help", command=self.help).pack(side="left", padx=6)
        ttk.Label(self, textvariable=self.target).pack(anchor="w", pady=8)
        self.listbox = tk.Listbox(self, height=10)
        self.listbox.pack(fill="both", expand=True)
        buttons = ttk.Frame(self); buttons.pack(fill="x", pady=10)
        for text, cmd in [
            ("Refresh", self.refresh),
            ("Use selected", self.use_selected),
            ("Swap L/R", lambda: self.run(lambda: backend.load_swap(mode="A")[2])),
            ("Alt Swap", lambda: self.run(lambda: backend.load_swap(mode="B")[2])),
            ("Fix Streams", lambda: self.run(lambda: backend.fix_now()[1])),
            ("Disable", lambda: self.run(lambda: backend.restore_output_and_unload()[1])),
        ]:
            ttk.Button(buttons, text=text, command=cmd).pack(side="left", padx=3)
        tests = ttk.Frame(self); tests.pack(fill="x", pady=4)
        ttk.Button(tests, text="Left", command=lambda: self.run(lambda: backend.play_test("left")[1])).pack(side="left", padx=3)
        ttk.Button(tests, text="Right", command=lambda: self.run(lambda: backend.play_test("right")[1])).pack(side="left", padx=3)
        ttk.Button(tests, text="Both", command=lambda: self.run(lambda: backend.play_test("both")[1])).pack(side="left", padx=3)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status).pack(anchor="w", pady=(10, 0))
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, "end")
        for sink in backend.all_sinks():
            mark = "*" if sink.get("is_default") else " "
            self.listbox.insert("end", f"{mark} {sink.get('description')} [{sink.get('name')}]")

    def selected_name(self):
        idx = self.listbox.curselection()
        if not idx:
            return ""
        text = self.listbox.get(idx[0])
        if "[" in text and text.endswith("]"):
            return text.rsplit("[", 1)[1][:-1]
        return ""

    def use_selected(self):
        name = self.selected_name()
        ok, msg = backend.remember_target_sink(name)
        self.target.set(backend.get_target_description())
        self.status.set(msg)

    def run(self, func):
        try:
            msg = func()
            self.status.set(str(msg))
            self.refresh()
        except Exception as exc:
            messagebox.showerror(backend.APP_NAME, str(exc))

    def switch_tw(self):
        backend.save_theme_name(backend.THEME_TIHULUWAVE)
        self.destroy()

    def help(self):
        messagebox.showinfo(backend.APP_NAME, f"Repository:\n{backend.REPOSITORY_URL}")


if __name__ == "__main__":
    PlainApp().mainloop()
