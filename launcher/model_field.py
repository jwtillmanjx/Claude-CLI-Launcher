"""The Model selector: an autocomplete combobox plus its history, placeholder
behavior, a Remove button, and the live ``--model <value>`` preview label.

This is self-contained so the Projects view doesn't have to carry the model's
considerable state. Construct one ``ModelField`` for the app's lifetime and call
``build(parent)`` each time the Projects view is (re)shown to attach widgets.
"""

import tkinter as tk
from tkinter import ttk

from .config import (C_ACCENT, C_BG, C_DANGER, C_DANGER_BORDER, C_DANGER_LIGHT,
                     C_DANGER_HOVER, C_INPUT_BORDER, C_SIDEBAR, C_TEXT,
                     C_TEXT_MUTED, C_TEXT_SEC, DEFAULT_MODEL, FONT, MONO)
from .store import read_model_config, write_model_config
from .widgets import btn_hover


class ModelField:
    def __init__(self, root):
        self.root = root
        self.selected, self.history = read_model_config()
        self.var = tk.StringVar()
        self._has_placeholder = False

        if self.selected:
            # The previously used model is auto-selected on the next launch.
            self.var.set(self.selected)
        elif self.history:
            self.selected = sorted(self.history, reverse=True)[0]
            self.var.set(self.selected)
        else:
            # No history yet — show the default model as muted placeholder text.
            self._has_placeholder = True
            self.var.set(DEFAULT_MODEL)

        # Widgets, created in build().
        self.combo = None
        self.remove_btn = None
        self.flag_label = None

        self._init_style()
        self.var.trace_add("write", lambda *_: self._update_flag_label())

    # ── ttk styling ──────────────────────────────────────────────────────────
    def _init_style(self):
        """Configure a ttk style so the combobox matches the light theme."""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self._vpad = 4  # per-side vertical padding, tuned at render time
        self.style.configure(
            "Model.TCombobox",
            fieldbackground=C_BG, background=C_BG, foreground=C_TEXT,
            arrowcolor=C_TEXT_SEC, bordercolor=C_INPUT_BORDER,
            lightcolor=C_INPUT_BORDER, darkcolor=C_INPUT_BORDER, relief="flat",
            padding=(4, self._vpad, 4, self._vpad))
        self.style.map(
            "Model.TCombobox",
            fieldbackground=[("readonly", C_BG), ("focus", C_BG)],
            bordercolor=[("focus", C_ACCENT)])
        # Style the dropdown listbox (a classic Tk Listbox under the hood).
        self.root.option_add("*TCombobox*Listbox.background", C_BG)
        self.root.option_add("*TCombobox*Listbox.foreground", C_TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", C_ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")

    # ── Construction ─────────────────────────────────────────────────────────
    def build(self, parent):
        """Create the Model label, combobox, Remove button, and flag preview,
        packing them into ``parent`` (the options row)."""
        tk.Label(parent, text="Model", font=(FONT, 11),
                 fg=C_TEXT, bg=C_SIDEBAR).pack(side=tk.LEFT)

        self.combo = ttk.Combobox(
            parent, textvariable=self.var, font=(MONO, 10),
            style="Model.TCombobox", values=self.sorted_history(), width=32)
        self.combo.pack(side=tk.LEFT, padx=(10, 8))
        self._set_fg()
        self.combo.bind("<FocusIn>", self._on_focus_in)
        self.combo.bind("<FocusOut>", self._on_focus_out)
        self.combo.bind("<KeyRelease>", self._on_keyrelease)
        # Selecting from the dropdown counts as entering a value.
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._on_focus_in())

        self.remove_btn = tk.Label(
            parent, text="Remove", font=(FONT, 9), fg=C_DANGER,
            bg=C_DANGER_LIGHT, padx=10, pady=4, cursor="hand2",
            highlightbackground=C_DANGER_BORDER, highlightthickness=1)
        self.remove_btn.pack(side=tk.LEFT)
        self.remove_btn.bind("<Button-1>", lambda e: self._on_remove())
        btn_hover(self.remove_btn, C_DANGER_LIGHT, C_DANGER_HOVER)

        # Match the combobox height to the Remove button once both are laid out.
        self.root.after_idle(self._match_height)

        self.flag_label = tk.Label(
            parent, text=f"--model {self.current_model()}",
            font=(MONO, 10), fg=C_ACCENT, bg=C_SIDEBAR)
        self.flag_label.pack(side=tk.RIGHT)
        self._update_flag_label()

    def _match_height(self):
        """Nudge the combobox vertical padding so its height matches the Remove
        button (their natural request heights differ)."""
        combo, btn = self.combo, self.remove_btn
        if combo is None or btn is None:
            return
        try:
            if not combo.winfo_exists() or not btn.winfo_exists():
                return
            combo.update_idletasks()
            btn.update_idletasks()
            btn_h = btn.winfo_reqheight()
            vpad = self._vpad
            # Converge on a matching height (padding feeds back into reqheight).
            for _ in range(5):
                delta = btn_h - combo.winfo_reqheight()
                if abs(delta) <= 1:
                    break
                vpad = max(0, vpad + delta / 2)
                self.style.configure(
                    "Model.TCombobox",
                    padding=(4, int(round(vpad)), 4, int(round(vpad))))
                combo.update_idletasks()
            self._vpad = vpad
        except tk.TclError:
            pass

    # ── History ──────────────────────────────────────────────────────────────
    def sorted_history(self):
        """History sorted descending and de-duplicated."""
        return sorted(set(self.history), reverse=True)

    def _refresh_values(self):
        if self.combo is not None:
            try:
                self.combo["values"] = self.sorted_history()
            except tk.TclError:
                pass

    # ── Placeholder / foreground ─────────────────────────────────────────────
    def _set_fg(self):
        fg = C_TEXT_MUTED if self._has_placeholder else C_TEXT
        self.style.configure("Model.TCombobox", foreground=fg)

    def _show_placeholder(self):
        self._has_placeholder = True
        self.var.set(DEFAULT_MODEL)
        self._set_fg()

    def _clear_placeholder(self):
        if self._has_placeholder:
            self._has_placeholder = False
            self.var.set("")
            self._set_fg()

    def _on_focus_in(self, _event=None):
        self._clear_placeholder()

    def _on_focus_out(self, _event=None):
        if self._has_placeholder:
            return
        trimmed = self.var.get().strip()
        self.var.set(trimmed)
        if not trimmed:
            self._show_placeholder()

    def _on_keyrelease(self, event):
        # Filter the dropdown as the user types (autocomplete).
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab",
                            "Left", "Right", "Home", "End"):
            return
        if self._has_placeholder:
            return
        typed = self.var.get().strip().lower()
        history = self.sorted_history()
        if typed:
            matches = [m for m in history if typed in m.lower()]
            self.combo["values"] = matches if matches else history
        else:
            self.combo["values"] = history

    # ── Flag preview ─────────────────────────────────────────────────────────
    def _update_flag_label(self):
        if self.flag_label is None:
            return
        try:
            self.flag_label.config(text=f"--model {self.current_model()}")
        except tk.TclError:
            pass

    # ── Public API ───────────────────────────────────────────────────────────
    def current_model(self):
        """The model to launch with — the entered value, or the default."""
        if self._has_placeholder:
            return DEFAULT_MODEL
        val = self.var.get().strip()
        return val if val else DEFAULT_MODEL

    def record_used(self, model):
        """Persist ``model`` as used: add to history if new, mark as selected."""
        if not model:
            return
        if model not in self.history:
            self.history.append(model)
        self.selected = model
        write_model_config(self.selected, self.history)
        self._refresh_values()

    def _on_remove(self):
        """Remove the current model from history and select the next one."""
        if self._has_placeholder:
            return
        current = self.var.get().strip()
        self.var.set(current)
        if not current or current not in self.history:
            return
        # Find the "next" model in the descending list before removing.
        ordered = self.sorted_history()
        idx = ordered.index(current)
        self.history.remove(current)
        if self.selected == current:
            self.selected = ""
        remaining = self.sorted_history()
        if remaining:
            next_model = remaining[idx] if idx < len(remaining) else remaining[-1]
            self.selected = next_model
            self._has_placeholder = False
            self.var.set(next_model)
            self._set_fg()
        else:
            self._show_placeholder()
        write_model_config(self.selected, self.history)
        self._refresh_values()
