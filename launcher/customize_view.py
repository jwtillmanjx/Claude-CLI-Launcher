"""The Customize view: manage the parent directories that are scanned for child
projects. Adding a scan directory immediately derives its child directories into
the project list.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from .config import (C_ACCENT, C_ACCENT_HOVER, C_BG, C_BORDER, C_DANGER,
                     C_DANGER_BORDER, C_DANGER_HOVER, C_DANGER_LIGHT, C_INPUT_BG,
                     C_INPUT_BORDER, C_TEXT, C_TEXT_MUTED, FONT, MONO)
from .store import derive_projects, write_csv, write_scan_dirs
from .widgets import ScrollableList, add_placeholder, btn_hover

PLACEHOLDER = r"C:\path\to\directory"


class CustomizeView:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.scan_entry = None
        self.list = None

    def show(self):
        header = tk.Frame(self.app.main_panel, bg=C_BG)
        header.pack(fill=tk.X, padx=20, pady=(20, 0))
        tk.Label(header, text="Project Scan Directories", font=(FONT, 16, "bold"),
                 fg=C_TEXT, bg=C_BG).pack(anchor="w")
        tk.Label(header, text="Add directories to scan for projects. "
                 "Subdirectories containing recognized project files will be "
                 "auto-added to your Projects list.", font=(FONT, 10),
                 fg=C_TEXT_MUTED, bg=C_BG, wraplength=600,
                 justify=tk.LEFT).pack(anchor="w", pady=(4, 0))

        input_bar = tk.Frame(self.app.main_panel, bg=C_BG)
        input_bar.pack(fill=tk.X, padx=20, pady=(16, 0))
        input_frame = tk.Frame(input_bar, bg=C_INPUT_BG,
                               highlightbackground=C_INPUT_BORDER, highlightthickness=1)
        input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.scan_entry = tk.Entry(input_frame, font=(MONO, 11), bg=C_INPUT_BG,
                                   fg=C_TEXT, relief=tk.FLAT, border=0)
        self.scan_entry.pack(fill=tk.X, padx=8, pady=6)
        add_placeholder(self.scan_entry, PLACEHOLDER)
        self.scan_entry.bind("<Return>", lambda e: self._on_add())

        add_btn = tk.Label(input_bar, text="Add Directory", font=(FONT, 10, "bold"),
                           fg="white", bg=C_ACCENT, padx=14, pady=6, cursor="hand2")
        add_btn.pack(side=tk.LEFT)
        add_btn.bind("<Button-1>", lambda e: self._on_add())
        btn_hover(add_btn, C_ACCENT, C_ACCENT_HOVER)

        tk.Frame(self.app.main_panel, bg=C_BORDER, height=1).pack(
            fill=tk.X, padx=20, pady=(16, 0))

        container = tk.Frame(self.app.main_panel, bg=C_BG)
        container.pack(fill=tk.BOTH, expand=True)
        self.list = ScrollableList(container, self.root, bg=C_BG)

        self._refresh()

    def _refresh(self):
        self.list.clear()
        if not self.app.scan_dirs:
            self._render_empty()
            return
        for d in self.app.scan_dirs:
            self._create_row(d)

    def _render_empty(self):
        frame = tk.Frame(self.list.frame, bg=C_BG)
        frame.pack(fill=tk.BOTH, expand=True, pady=60)
        tk.Label(frame, text="\U0001F4C1", font=(FONT, 28), fg=C_TEXT_MUTED,
                 bg=C_BG).pack()
        tk.Label(frame, text="No scan directories configured.", font=(FONT, 12),
                 fg=C_TEXT_MUTED, bg=C_BG).pack(pady=(8, 4))
        tk.Label(frame, text="Add a directory above to start auto-detecting "
                 "projects.", font=(FONT, 10), fg=C_TEXT_MUTED, bg=C_BG).pack()

    def _create_row(self, dir_path):
        row = tk.Frame(self.list.frame, bg=C_BG)
        row.pack(fill=tk.X, padx=20, pady=2)
        tk.Frame(row, bg=C_BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)

        inner = tk.Frame(row, bg=C_BG, pady=8)
        inner.pack(fill=tk.X)
        inner.columnconfigure(1, weight=1)

        tk.Label(inner, text="\U0001F4C1", font=(FONT, 14), fg=C_ACCENT,
                 bg=C_BG).grid(row=0, column=0, padx=(0, 8), sticky="ns")
        tk.Label(inner, text=dir_path, font=(MONO, 11), fg=C_TEXT, bg=C_BG,
                 anchor="w").grid(row=0, column=1, sticky="ew")

        remove_btn = tk.Label(inner, text="Remove", font=(FONT, 9), fg=C_DANGER,
                              bg=C_DANGER_LIGHT, padx=8, pady=4, cursor="hand2",
                              highlightbackground=C_DANGER_BORDER, highlightthickness=1)
        remove_btn.grid(row=0, column=2, padx=(8, 0), sticky="ns")
        btn_hover(remove_btn, C_DANGER_LIGHT, C_DANGER_HOVER)
        remove_btn.bind("<Button-1>", lambda e: self._on_remove(dir_path))

    def _on_remove(self, dir_path):
        key = os.path.normcase(os.path.normpath(dir_path))
        self.app.scan_dirs = [d for d in self.app.scan_dirs
                              if os.path.normcase(os.path.normpath(d)) != key]
        write_scan_dirs(self.app.scan_dirs)
        self._refresh()

    def _on_add(self):
        # Use a typed path if present and real; otherwise open a folder picker.
        typed = self.scan_entry.get().strip()
        if (typed and not getattr(self.scan_entry, "_has_placeholder", False)
                and typed != PLACEHOLDER):
            folder = typed
        else:
            folder = filedialog.askdirectory(title="Select Scan Directory")
        if not folder:
            return
        folder = os.path.normpath(folder)

        key = os.path.normcase(folder)
        if any(os.path.normcase(os.path.normpath(d)) == key
               for d in self.app.scan_dirs):
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"Directory does not exist:\n{folder}")
            return

        self.app.scan_dirs.append(folder)
        write_scan_dirs(self.app.scan_dirs)
        derive_projects(folder, self.app.projects, self.app.excluded)
        write_csv(self.app.projects)

        # Reset the entry back to its placeholder.
        self.scan_entry.delete(0, tk.END)
        self.scan_entry.insert(0, PLACEHOLDER)
        self.scan_entry.configure(fg=C_TEXT_MUTED)
        self.scan_entry._has_placeholder = True

        self._refresh()
