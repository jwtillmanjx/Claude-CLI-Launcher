"""Small, reusable tkinter building blocks shared by both views.

Keeping these here removes the duplication that made the original single file
hard to follow: there were two near-identical toggle switches, two copies of the
scroll-frame plumbing, and an inline rounded-rectangle routine.
"""

import math
import tkinter as tk

from .config import (C_ACCENT, C_BG, C_TEXT_MUTED, C_TEXT)


def draw_rounded_rect(canvas, x1, y1, x2, y2, r, fill):
    """Draw a filled rounded rectangle as a polygon with arc-traced corners."""
    steps = 12  # points per corner; more = smoother
    pts = []
    for cx, cy, start_deg in (
        (x1 + r, y1 + r, 180),  # top-left
        (x2 - r, y1 + r, 270),  # top-right
        (x2 - r, y2 - r, 0),    # bottom-right
        (x1 + r, y2 - r, 90),   # bottom-left
    ):
        for i in range(steps + 1):
            a = math.radians(start_deg + i * 90 / steps)
            pts.extend([cx + r * math.cos(a), cy + r * math.sin(a)])
    canvas.create_polygon(pts, fill=fill, outline=fill, smooth=False)


def btn_hover(widget, bg_normal, bg_hover, fg_normal=None, fg_hover=None):
    """Bind enter/leave so a label-as-button changes color on hover."""
    def on_enter(_e):
        widget.configure(bg=bg_hover)
        if fg_hover:
            widget.configure(fg=fg_hover)

    def on_leave(_e):
        widget.configure(bg=bg_normal)
        if fg_normal:
            widget.configure(fg=fg_normal)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def add_placeholder(entry, placeholder):
    """Give an Entry classic placeholder behavior.

    The widget tracks its own state on ``entry._has_placeholder`` /
    ``entry._placeholder`` so callers can tell whether the visible text is real
    user input or just the prompt.
    """
    entry._placeholder = placeholder
    entry._has_placeholder = True

    def on_focus_in(_e):
        if entry._has_placeholder:
            # Flip the flag before mutating text so any textvariable trace sees
            # the correct placeholder state.
            entry._has_placeholder = False
            entry.delete(0, tk.END)
            entry.configure(fg=C_TEXT)

    def on_focus_out(_e):
        if not entry.get():
            entry._has_placeholder = True
            entry.insert(0, placeholder)
            entry.configure(fg=C_TEXT_MUTED)

    entry.insert(0, placeholder)
    entry.configure(fg=C_TEXT_MUTED)
    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)


class ToggleSwitch:
    """A pill-shaped on/off switch drawn on a canvas, backed by a BooleanVar.

    Clicking flips the var, redraws, and invokes the optional ``on_toggle``.
    """

    def __init__(self, parent, var, bg, on_toggle=None):
        self.var = var
        self.on_toggle = on_toggle
        self.canvas = tk.Canvas(parent, width=44, height=24, bg=bg,
                                highlightthickness=0, cursor="hand2")
        self._draw()
        self.canvas.bind("<Button-1>", self._on_click)

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)
        return self

    def _draw(self):
        c = self.canvas
        c.delete("all")
        on = self.var.get()
        color = C_ACCENT if on else C_TEXT_MUTED
        # Track: two end-caps plus a connecting rectangle.
        c.create_oval(0, 0, 24, 24, fill=color, outline=color)
        c.create_oval(20, 0, 44, 24, fill=color, outline=color)
        c.create_rectangle(12, 0, 32, 24, fill=color, outline=color)
        # Knob
        knob_x = 30 if on else 12
        c.create_oval(knob_x - 9, 3, knob_x + 9, 21, fill="white", outline="white")

    def _on_click(self, _e):
        self.var.set(not self.var.get())
        self._draw()
        if self.on_toggle:
            self.on_toggle()


class ScrollableList:
    """A vertically scrollable region: a Canvas + Scrollbar wrapping an inner
    Frame (``.frame``) that callers fill with rows.

    Mouse-wheel scrolling is bound while the pointer is over the canvas. An
    optional ``on_leave`` callback fires when the pointer leaves (the Projects
    view uses it to clear its hovered-row highlight).
    """

    def __init__(self, parent, root, bg=C_BG, on_leave=None):
        self.root = root
        self.on_leave = on_leave
        self.canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL,
                                      command=self.canvas.yview)
        self.frame = tk.Frame(self.canvas, bg=bg)

        self.frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self._window = self.canvas.create_window((0, 0), window=self.frame,
                                                  anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Keep the inner frame as wide as the canvas.
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._window, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.bind_mousewheel())
        self.canvas.bind("<Leave>", self._handle_leave)

    def bind_mousewheel(self):
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def unbind_mousewheel(self):
        self.root.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _handle_leave(self, event):
        self.unbind_mousewheel()
        if self.on_leave:
            self.on_leave(event)

    def clear(self):
        for child in self.frame.winfo_children():
            child.destroy()
