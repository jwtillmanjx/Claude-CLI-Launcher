"""The application shell: owns the window, the shared in-memory state, the
sidebar navigation, and switching between the two views. The views themselves
live in ``projects_view`` and ``customize_view``.
"""

import os
import tkinter as tk

from .config import (C_ACCENT, C_ACCENT_LIGHT, C_ACCENT_TEXT, C_BG, C_BORDER,
                     C_HOVER, C_SIDEBAR, C_TEXT, C_TEXT_MUTED, FONT, ICO_PATH,
                     MIN_H, MIN_W, MONO, WIN_H, WIN_W, WINDOW_TITLE)
from .customize_view import CustomizeView
from .icon import load_ico_png
from .model_field import ModelField
from .projects_view import ProjectsView
from .store import (derive_projects, read_csv, read_excluded, read_options,
                    read_scan_dirs, write_csv)
from .widgets import draw_rounded_rect


class ClaudeCLILauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.minsize(MIN_W, MIN_H)
        if os.path.exists(ICO_PATH):
            try:
                self.root.iconbitmap(ICO_PATH)
            except Exception:
                pass
        self._center_window()
        self.root.configure(bg=C_BG)

        # ── Shared state ─────────────────────────────────────────────────────
        self.projects = read_csv()
        self.scan_dirs = read_scan_dirs()
        self.excluded = read_excluded()
        skip, admin = read_options()
        self.skip_perms = tk.BooleanVar(value=skip)
        self.run_admin = tk.BooleanVar(value=admin)
        self.model = ModelField(self.root)

        # Derive projects from scan dirs on startup (skipping excluded ones).
        for scan_dir in self.scan_dirs:
            derive_projects(scan_dir, self.projects, self.excluded)
        write_csv(self.projects)

        # ── Views ────────────────────────────────────────────────────────────
        self.active_tab = "projects"
        self.projects_view = ProjectsView(self)
        self.customize_view = CustomizeView(self)

        self._build_chrome()
        self.show_projects_view()

    def _center_window(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - WIN_W) // 2
        y = (screen_h - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

    # ── Window chrome (header band + sidebar) ────────────────────────────────
    def _build_chrome(self):
        # Header band: logo (left) + options panel (right) share C_SIDEBAR so
        # they read as one unified header.
        header_band = tk.Frame(self.root, bg=C_SIDEBAR)
        header_band.pack(side=tk.TOP, fill=tk.X)

        sidebar_hdr = tk.Frame(header_band, bg=C_SIDEBAR, width=190, height=80)
        sidebar_hdr.pack(side=tk.LEFT, fill=tk.Y)
        sidebar_hdr.pack_propagate(False)

        tk.Frame(header_band, bg=C_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        self.options_panel = tk.Frame(header_band, bg=C_SIDEBAR)
        self.options_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Frame(self.root, bg=C_BORDER, height=1).pack(side=tk.TOP, fill=tk.X)

        # Body: sidebar nav (left) + main content panel (right).
        body = tk.Frame(self.root, bg=C_BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        sidebar_body = tk.Frame(body, bg=C_BG, width=190)
        sidebar_body.pack(side=tk.LEFT, fill=tk.Y)
        sidebar_body.pack_propagate(False)

        tk.Frame(body, bg=C_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        self.main_panel = tk.Frame(body, bg=C_BG)
        self.main_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_logo(sidebar_hdr)
        self._build_nav(sidebar_body)

    def _build_logo(self, parent):
        logo_frame = tk.Frame(parent, bg=C_SIDEBAR)
        logo_frame.pack(fill=tk.X, pady=(24, 20), padx=16)
        icon_row = tk.Frame(logo_frame, bg=C_SIDEBAR)
        icon_row.pack(anchor="w")

        self._sidebar_icon = load_ico_png(32)
        if self._sidebar_icon:
            tk.Label(icon_row, image=self._sidebar_icon, bg=C_SIDEBAR,
                     width=32, height=32).pack(side=tk.LEFT, padx=(0, 10))
        else:
            canvas = tk.Canvas(icon_row, width=36, height=36, bg=C_SIDEBAR,
                               highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=(0, 10))
            draw_rounded_rect(canvas, 2, 2, 34, 34, 8, C_ACCENT)
            canvas.create_text(18, 18, text=">_", fill="white", font=(MONO, 12, "bold"))

        text_col = tk.Frame(icon_row, bg=C_SIDEBAR)
        text_col.pack(side=tk.LEFT)
        tk.Label(text_col, text="Claude CLI", font=(FONT, 13, "bold"),
                 fg=C_TEXT, bg=C_SIDEBAR).pack(anchor="w")
        tk.Label(text_col, text="LAUNCHER", font=(FONT, 8),
                 fg=C_ACCENT, bg=C_SIDEBAR).pack(anchor="w")

    def _build_nav(self, parent):
        nav = tk.Frame(parent, bg=C_BG)
        nav.pack(fill=tk.X, padx=10, pady=(10, 0))
        self.btn_projects = self._nav_button(nav, "Projects", "projects")
        self.btn_projects.pack(fill=tk.X, pady=2)
        self.btn_customize = self._nav_button(nav, "Customize", "customize")
        self.btn_customize.pack(fill=tk.X, pady=2)

        footer = tk.Frame(parent, bg=C_BG)
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=12)
        tk.Label(footer, text="Claude CLI Launcher", font=(FONT, 9),
                 fg=C_TEXT_MUTED, bg=C_BG).pack(anchor="w")

    def _nav_button(self, parent, text, tab_name):
        btn = tk.Label(parent, text=text, font=(FONT, 11), fg=C_TEXT, bg=C_BG,
                       cursor="hand2", padx=14, pady=8, anchor="w")

        def on_enter(_e):
            if self.active_tab != tab_name:
                btn.configure(bg=C_HOVER)

        def on_leave(_e):
            if self.active_tab != tab_name:
                btn.configure(bg=C_BG)

        def on_click(_e):
            if tab_name == "projects":
                self.show_projects_view()
            else:
                self.show_customize_view()

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<Button-1>", on_click)
        return btn

    def _update_nav_highlight(self):
        projects_active = self.active_tab == "projects"
        self.btn_projects.configure(
            bg=C_ACCENT_LIGHT if projects_active else C_BG,
            fg=C_ACCENT_TEXT if projects_active else C_TEXT)
        self.btn_customize.configure(
            bg=C_BG if projects_active else C_ACCENT_LIGHT,
            fg=C_TEXT if projects_active else C_ACCENT_TEXT)

    def _clear_main(self):
        for w in self.main_panel.winfo_children():
            w.destroy()
        for w in self.options_panel.winfo_children():
            w.destroy()

    # ── View switching ───────────────────────────────────────────────────────
    def show_projects_view(self):
        self.active_tab = "projects"
        self._update_nav_highlight()
        self._clear_main()
        self.projects_view.show()

    def show_customize_view(self):
        self.active_tab = "customize"
        self._update_nav_highlight()
        self._clear_main()
        self.customize_view.show()

    # ── Run ──────────────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()
