"""The Projects view: the options bar (Skip Permissions / Run as Administrator /
Model), the search + action bar, and the scrollable list of project rows.

Each row is a ``ProjectRow`` object. In the original code this was a single
~270-line function full of nested closures sharing mutable cells; promoting it to
a class turns each of those closures into a named method with ordinary
attributes, which is far easier to follow.
"""

import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

from . import platform_win
from .config import (C_ACCENT, C_ACCENT_LIGHT, C_ACCENT_TEXT, C_BG, C_BORDER,
                     C_CTRL_HOVER, C_DANGER, C_DANGER_BORDER, C_DANGER_HOVER,
                     C_DANGER_LIGHT, C_HOVER, C_HOVER_DARK, C_INPUT_BG,
                     C_INPUT_BORDER, C_SHOWCMD_HOVER, C_SIDEBAR, C_TEXT,
                     C_TEXT_MUTED, C_TEXT_SEC, FONT, ICO_PATH, MONO)
from .naming import (badge_color, dir_name, get_initials, sort_projects,
                     tab_name_for)
from .store import (path_in_list, write_csv, write_excluded, write_options)
from .widgets import (ScrollableList, ToggleSwitch, add_placeholder, btn_hover,
                      draw_rounded_rect)


class ProjectsView:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.search_var = tk.StringVar()
        self._applied_search = None   # last search term actually rendered
        self._sort_mode = 0           # 0=default, 1=asc by path, 2=desc by path
        self._hovered_row = None      # the ProjectRow currently under the pointer
        self.search_var.trace_add("write", lambda *_: self._on_search_changed())

        # Widgets created in show().
        self.flag_label = None
        self.search_entry = None
        self.list = None
        self._sort_header = None

    # ── View construction ────────────────────────────────────────────────────
    def show(self):
        self._build_options_bar()
        self._build_action_bar()
        self._build_project_list()
        self.refresh_project_list()

    def _build_options_bar(self):
        """Row 1: Skip Permissions + Run as Administrator. Row 2: Model field."""
        inner = tk.Frame(self.app.options_panel, bg=C_SIDEBAR)
        inner.pack(fill=tk.X, padx=16, pady=10)

        row1 = tk.Frame(inner, bg=C_SIDEBAR)
        row1.pack(fill=tk.X)

        tk.Label(row1, text="Skip Permissions?", font=(FONT, 11),
                 fg=C_TEXT, bg=C_SIDEBAR).pack(side=tk.LEFT)
        ToggleSwitch(row1, self.app.skip_perms, C_SIDEBAR,
                     on_toggle=self._on_skip_toggle).pack(side=tk.LEFT, padx=(10, 0))

        tk.Frame(row1, bg=C_BORDER, width=1, height=20).pack(
            side=tk.LEFT, padx=(16, 16))

        tk.Label(row1, text="Run as Administrator?", font=(FONT, 11),
                 fg=C_TEXT, bg=C_SIDEBAR).pack(side=tk.LEFT)
        ToggleSwitch(row1, self.app.run_admin, C_SIDEBAR).pack(
            side=tk.LEFT, padx=(10, 0))

        self.flag_label = tk.Label(row1, text="--dangerously-skip-permissions",
                                   font=(MONO, 10), fg=C_ACCENT, bg=C_SIDEBAR)
        if self.app.skip_perms.get():
            self.flag_label.pack(side=tk.RIGHT)

        row2 = tk.Frame(inner, bg=C_SIDEBAR)
        row2.pack(fill=tk.X, pady=(12, 0))
        self.app.model.build(row2)

    def _on_skip_toggle(self):
        if self.app.skip_perms.get():
            self.flag_label.pack(side=tk.RIGHT)
        else:
            self.flag_label.pack_forget()

    def _build_action_bar(self):
        action_bar = tk.Frame(self.app.main_panel, bg=C_BG)
        action_bar.pack(fill=tk.X, padx=16, pady=(12, 0))

        # Search input
        search_frame = tk.Frame(action_bar, bg=C_INPUT_BG,
                                highlightbackground=C_INPUT_BORDER,
                                highlightthickness=1)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Label(search_frame, text="\U0001F50D", font=(FONT, 11),
                 bg=C_INPUT_BG, fg=C_TEXT_MUTED).pack(side=tk.LEFT, padx=(8, 4))
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     font=(FONT, 11), bg=C_INPUT_BG, fg=C_TEXT,
                                     relief=tk.FLAT, border=0)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                               padx=(0, 8), pady=6)
        self.search_entry.bind("<Return>", self._on_search_enter)
        add_placeholder(self.search_entry, "Search projects")

        # Open button
        open_btn = tk.Label(action_bar, text="Open", font=(FONT, 10),
                            fg=C_TEXT, bg=C_HOVER, padx=14, pady=6, cursor="hand2",
                            relief=tk.FLAT, highlightbackground=C_BORDER,
                            highlightthickness=1)
        open_btn.pack(side=tk.LEFT, padx=(0, 8))
        open_btn.bind("<Button-1>", lambda e: self._on_open_project())
        btn_hover(open_btn, C_HOVER, C_HOVER_DARK)

        # Close All Instances button
        close_btn = tk.Label(action_bar, text="Close All Instances",
                             font=(FONT, 10), fg=C_DANGER, bg=C_DANGER_LIGHT,
                             padx=14, pady=6, cursor="hand2", relief=tk.FLAT,
                             highlightbackground=C_DANGER_BORDER,
                             highlightthickness=1)
        close_btn.pack(side=tk.LEFT)
        close_btn.bind("<Button-1>", lambda e: self._on_close_all())
        btn_hover(close_btn, C_DANGER_LIGHT, C_DANGER_HOVER)

        # Ctrl+click hint
        hint = tk.Frame(self.app.main_panel, bg=C_BG)
        hint.pack(fill=tk.X, padx=16, pady=(6, 0))
        tk.Label(hint, text="Ctrl+Click a project to launch without closing "
                 "this window", font=(FONT, 9), fg=C_TEXT_MUTED,
                 bg=C_BG).pack(side=tk.LEFT)

    def _build_project_list(self):
        container = tk.Frame(self.app.main_panel, bg=C_BG)
        container.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        tk.Frame(container, bg=C_BORDER, height=1).pack(fill=tk.X)

        header = tk.Frame(container, bg=C_BG)
        header.pack(fill=tk.X)
        self._sort_header = tk.Label(header, text="Project Path",
                                     font=(FONT, 9, "bold"), fg=C_TEXT_MUTED,
                                     bg=C_BG, anchor="w", padx=16, pady=4,
                                     cursor="hand2")
        self._sort_header.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._sort_header.bind("<Button-1>", lambda e: self._cycle_sort())
        self._update_sort_header()
        tk.Frame(container, bg=C_BORDER, height=1).pack(fill=tk.X)

        self.list = ScrollableList(container, self.root, bg=C_BG,
                                   on_leave=self._on_list_leave)

    # ── Hover bookkeeping ────────────────────────────────────────────────────
    def _on_list_leave(self, _event):
        if self._hovered_row is not None:
            self._hovered_row.deactivate()
            self._hovered_row = None

    # ── Search ───────────────────────────────────────────────────────────────
    def _effective_search(self):
        """The active search term — empty while the placeholder is showing."""
        if self.search_entry is None:
            return ""
        if getattr(self.search_entry, "_has_placeholder", False):
            return ""
        return self.search_var.get().lower().strip()

    def _on_search_changed(self):
        # Inserting/removing placeholder text writes to search_var without
        # changing what the user is searching for; ignore those writes so the
        # list doesn't flicker on focus-in or vanish on focus-out.
        if self._effective_search() == self._applied_search:
            return
        self.refresh_project_list()

    # ── Sorting ──────────────────────────────────────────────────────────────
    def _cycle_sort(self):
        self._sort_mode = (self._sort_mode + 1) % 3
        self._update_sort_header()
        self.refresh_project_list()

    def _update_sort_header(self):
        labels = {0: "Project Path", 1: "Project Path  ▲",
                  2: "Project Path  ▼"}
        self._sort_header.config(text=labels[self._sort_mode])

    def _ordered_projects(self):
        projects = self.app.projects
        if self._sort_mode == 1:
            return sorted(projects, key=lambda r: r[0].lower())
        if self._sort_mode == 2:
            return sorted(projects, key=lambda r: r[0].lower(), reverse=True)
        return sort_projects(projects)

    # ── List rendering ───────────────────────────────────────────────────────
    def refresh_project_list(self):
        if self.list is None or not self.list.frame.winfo_exists():
            return
        self.list.clear()

        search = self._effective_search()
        self._applied_search = search

        filtered = []
        for row in self._ordered_projects():
            name = dir_name(row[0]).lower()
            if search and search not in name and search not in row[0].lower():
                continue
            filtered.append(row)

        if not filtered:
            self._render_empty()
            return

        for row in filtered:
            ProjectRow(self, row)

    def _render_empty(self):
        frame = tk.Frame(self.list.frame, bg=C_BG)
        frame.pack(fill=tk.BOTH, expand=True, pady=60)
        if not self.app.projects:
            msg = ("No projects have been added yet.\nUse 'Open' to add a "
                   "project or add scan directories in Customize.")
        else:
            msg = "No projects match your search."
        tk.Label(frame, text=msg, font=(FONT, 11), fg=C_TEXT_MUTED, bg=C_BG,
                 justify=tk.CENTER).pack()

    # ── Action handlers ──────────────────────────────────────────────────────
    def _on_search_enter(self, _event=None):
        text = self.search_var.get().strip()
        if getattr(self.search_entry, "_has_placeholder", False) or not text:
            self._on_open_project()
            return
        path = os.path.normpath(text)
        if os.path.isdir(path):
            if not path_in_list(path, self.app.projects):
                self.app.projects.append([path, ""])
            self.launch_project(path)
        else:
            messagebox.showwarning("Invalid Path", f"Directory not found:\n{path}")

    def _on_open_project(self):
        folder = filedialog.askdirectory(title="Select Project Directory")
        if not folder:
            return
        folder = os.path.normpath(folder)
        if not path_in_list(folder, self.app.projects):
            self.app.projects.append([folder, ""])
        self.launch_project(folder)

    def _on_close_all(self):
        if messagebox.askyesno(
                "Close All Instances",
                "Are you sure you want to kill all Claude instances?"):
            platform_win.close_all_instances()

    # ── Launching ────────────────────────────────────────────────────────────
    def launch_project(self, path, keep_open=False):
        """Update the timestamp, launch the terminal, persist choices, and close
        the launcher unless ``keep_open`` (Ctrl+click)."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        key = os.path.normcase(os.path.normpath(path))
        for row in self.app.projects:
            if os.path.normcase(os.path.normpath(row[0])) == key:
                row[1] = now
                break
        else:
            self.app.projects.append([path, now])
        write_csv(self.app.projects)

        model = self.app.model.current_model()
        params = self._wt_params(path, model)
        platform_win.launch_terminal(params, self.app.run_admin.get())

        # Persist the model used and the toggle states only after a launch.
        self.app.model.record_used(model)
        write_options(self.app.skip_perms.get(), self.app.run_admin.get())

        if not keep_open:
            self.root.destroy()

    def _wt_params(self, path, model):
        dirname = dir_name(path)
        claude = platform_win.claude_command(
            tab_name_for(dirname), model, self.app.skip_perms.get())
        return platform_win.wt_params(dirname, path, claude)

    def show_cmd_dialog_for(self, path):
        """Build and display the representative launch command for ``path``."""
        params = self._wt_params(path, self.app.model.current_model())
        cmd = platform_win.display_command(params, self.app.run_admin.get())
        self._show_cmd_dialog(cmd)

    def remove_project(self, path):
        """Remove ``path`` from the list, exclude it, and re-render in place."""
        key = os.path.normcase(os.path.normpath(path))
        self.app.projects = [r for r in self.app.projects
                             if os.path.normcase(os.path.normpath(r[0])) != key]
        write_csv(self.app.projects)
        self.app.excluded.add(key)
        write_excluded(self.app.excluded)

        self._hovered_row = None
        scroll_pos = self.list.canvas.yview()[0]
        self.refresh_project_list()
        self.list.canvas.update_idletasks()
        self.list.canvas.yview_moveto(scroll_pos)
        # Refocus + rebind so the mouse wheel keeps scrolling after the refresh.
        self.list.canvas.focus_set()
        self.list.bind_mousewheel()

    # ── Show CMD dialog ──────────────────────────────────────────────────────
    def _show_cmd_dialog(self, cmd):
        dlg = tk.Toplevel(self.root)
        dlg.title("Command")
        dlg.configure(bg=C_BG)
        if os.path.exists(ICO_PATH):
            try:
                dlg.iconbitmap(ICO_PATH)
            except Exception:
                pass
        dlg.transient(self.root)
        dlg.grab_set()

        dlg_w, dlg_h = 550, 200
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dlg_w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dlg_h) // 2
        dlg.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")

        tk.Label(dlg, text="Command to run:", font=(FONT, 11, "bold"),
                 fg=C_TEXT, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 8))

        cmd_frame = tk.Frame(dlg, bg=C_INPUT_BG, highlightbackground=C_INPUT_BORDER,
                             highlightthickness=1)
        cmd_frame.pack(fill=tk.X, padx=16)
        cmd_text = tk.Text(cmd_frame, font=(MONO, 10), fg=C_TEXT, bg=C_INPUT_BG,
                           relief=tk.FLAT, height=4, wrap=tk.WORD, border=0)
        cmd_text.pack(fill=tk.X, padx=8, pady=8)
        cmd_text.insert("1.0", cmd)
        cmd_text.configure(state=tk.DISABLED)

        btn_frame = tk.Frame(dlg, bg=C_BG)
        btn_frame.pack(fill=tk.X, padx=16, pady=(12, 16))

        def copy_cmd():
            self.root.clipboard_clear()
            self.root.clipboard_append(cmd)
            copy_btn.configure(text="Copied!")
            dlg.after(1500, lambda: copy_btn.configure(text="Copy"))

        close_btn = tk.Label(btn_frame, text="Close", font=(FONT, 10), fg=C_TEXT,
                             bg=C_HOVER, padx=16, pady=6, cursor="hand2",
                             highlightbackground=C_BORDER, highlightthickness=1)
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: dlg.destroy())
        btn_hover(close_btn, C_HOVER, C_HOVER_DARK)

        copy_btn = tk.Label(btn_frame, text="Copy", font=(FONT, 10), fg="white",
                            bg=C_ACCENT, padx=16, pady=6, cursor="hand2")
        copy_btn.pack(side=tk.RIGHT, padx=(0, 8))
        copy_btn.bind("<Button-1>", lambda e: copy_cmd())
        btn_hover(copy_btn, C_ACCENT, C_ACCENT_HOVER)


class ProjectRow:
    """One clickable project row. Building it wires up hover highlighting, the
    badge-swap-to-window-icon on Ctrl, the "opens in new window" tooltip, and the
    Show CMD / Remove buttons that appear on hover.
    """

    def __init__(self, view, row):
        self.view = view
        self.app = view.app
        self.root = view.root
        self.path = row[0]
        self.dirname = dir_name(self.path)
        self.initials = get_initials(self.path)
        self.color = badge_color(self.path)
        self._badge_showing_icon = False
        self._tooltip = None
        self._build()

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build(self):
        self.row_frame = tk.Frame(self.view.list.frame, bg=C_BG, cursor="hand2")
        self.row_frame.pack(fill=tk.X)
        tk.Frame(self.row_frame, bg=C_BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)

        self.inner = tk.Frame(self.row_frame, bg=C_BG, padx=16, pady=10)
        self.inner.pack(fill=tk.X)

        self.badge = tk.Canvas(self.inner, width=36, height=36, bg=C_BG,
                               highlightthickness=0)
        self.badge.pack(side=tk.LEFT, padx=(0, 12))
        self._draw_badge_initials()

        self.text_col = tk.Frame(self.inner, bg=C_BG)
        self.text_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.name_label = tk.Label(self.text_col, text=self.dirname,
                                   font=(FONT, 12, "bold"), fg=C_TEXT, bg=C_BG,
                                   anchor="w", wraplength=0)
        self.name_label.pack(fill=tk.X, anchor="w")
        self.path_label = tk.Label(self.text_col, text=self.path, font=(MONO, 10),
                                   fg=C_TEXT_MUTED, bg=C_BG, anchor="w",
                                   wraplength=0, justify=tk.LEFT)
        self.path_label.pack(fill=tk.X, anchor="w")
        self.text_col.bind("<Configure>", self._update_wrap)

        # Buttons (hidden until hover).
        self.btn_col = tk.Frame(self.inner, bg=C_BG)
        self.btn_col.pack(side=tk.RIGHT, padx=(4, 0))
        self.btn_col.pack_forget()
        self.show_cmd_btn = tk.Label(self.btn_col, text="Show CMD", font=(FONT, 9),
                                     fg=C_TEXT_SEC, bg=C_HOVER, padx=8, pady=4,
                                     cursor="hand2", highlightbackground=C_BORDER,
                                     highlightthickness=1)
        self.show_cmd_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.remove_btn = tk.Label(self.btn_col, text="Remove", font=(FONT, 9),
                                   fg=C_DANGER, bg=C_DANGER_LIGHT, padx=8, pady=4,
                                   cursor="hand2", highlightbackground=C_DANGER_BORDER,
                                   highlightthickness=1)
        self.remove_btn.pack(side=tk.LEFT)

        self._bind_events()

    @property
    def _tinted_widgets(self):
        """Widgets that take the row's hover background tint."""
        return [self.row_frame, self.inner, self.text_col,
                self.name_label, self.path_label]

    def _update_wrap(self, _event=None):
        avail = self.text_col.winfo_width()
        if avail > 1:
            self.path_label.configure(wraplength=avail)
            self.name_label.configure(wraplength=avail)

    def _bind_events(self):
        hover_widgets = [self.row_frame, self.inner, self.badge, self.text_col,
                         self.name_label, self.path_label, self.btn_col,
                         self.show_cmd_btn, self.remove_btn]
        for w in hover_widgets:
            w.bind("<Enter>", self.on_enter)

        # Ctrl press/release updates the highlight while hovering.
        for seq in ("<KeyPress-Control_L>", "<KeyRelease-Control_L>",
                    "<KeyPress-Control_R>", "<KeyRelease-Control_R>"):
            self.root.bind(seq, self.on_key, add="+")

        # Button-specific hover, layered on top of the row hover.
        self.show_cmd_btn.bind(
            "<Enter>", lambda e: self.show_cmd_btn.configure(bg=C_SHOWCMD_HOVER),
            add="+")
        self.show_cmd_btn.bind(
            "<Leave>", lambda e: self.show_cmd_btn.configure(bg=C_HOVER), add="+")
        self.remove_btn.bind(
            "<Enter>", lambda e: self.remove_btn.configure(bg=C_DANGER_HOVER),
            add="+")
        self.remove_btn.bind(
            "<Leave>", lambda e: self.remove_btn.configure(bg=C_DANGER_LIGHT),
            add="+")

        for w in [self.row_frame, self.inner, self.badge, self.text_col,
                  self.name_label, self.path_label]:
            w.bind("<Button-1>", self.on_click)
        self.show_cmd_btn.bind("<Button-1>", self.on_show_cmd)
        self.remove_btn.bind("<Button-1>", self.on_remove)

    # ── Badge drawing ────────────────────────────────────────────────────────
    def _draw_badge_initials(self):
        self.badge.delete("all")
        draw_rounded_rect(self.badge, 0, 0, 36, 36, 10, self.color)
        fs = 11 if len(self.initials) <= 2 else 9 if len(self.initials) == 3 else 8
        self.badge.create_text(18, 18, text=self.initials, fill="white",
                               font=(FONT, fs, "bold"))
        self._badge_showing_icon = False

    def _draw_badge_window_icon(self):
        self.badge.delete("all")
        draw_rounded_rect(self.badge, 0, 0, 36, 36, 10, self.color)
        # Two overlapping windows hinting "opens in a new window".
        self.badge.create_rectangle(10, 9, 26, 23, outline="white", width=1.5)
        self.badge.create_line(10, 13, 26, 13, fill="white", width=1.5)
        self.badge.create_rectangle(14, 15, 30, 29, fill=self.color,
                                    outline="white", width=1.5)
        self.badge.create_line(14, 19, 30, 19, fill="white", width=1.5)
        self._badge_showing_icon = True

    # ── Hover state ──────────────────────────────────────────────────────────
    def activate(self, ctrl_held=False):
        bg = C_CTRL_HOVER if ctrl_held else C_HOVER
        for w in self._tinted_widgets:
            w.configure(bg=bg)
        self.badge.configure(bg=bg)
        self.btn_col.pack(side=tk.RIGHT, padx=(4, 0))
        if ctrl_held and not self._badge_showing_icon:
            self._draw_badge_window_icon()
            self._show_tooltip()
        elif not ctrl_held and self._badge_showing_icon:
            self._draw_badge_initials()
            self._hide_tooltip()

    def deactivate(self):
        for w in self._tinted_widgets:
            try:
                w.configure(bg=C_BG)
            except tk.TclError:
                pass
        try:
            self.badge.configure(bg=C_BG)
        except tk.TclError:
            pass
        if self._badge_showing_icon:
            self._draw_badge_initials()
        self._hide_tooltip()
        self.btn_col.pack_forget()

    def on_enter(self, event):
        prev = self.view._hovered_row
        if prev is not None and prev is not self:
            prev.deactivate()
        self.view._hovered_row = self
        self.activate(bool(event.state & 0x4))

    def on_key(self, event):
        if self.view._hovered_row is not self:
            return
        ctrl_held = bool(event.state & 0x4) if event.type == "5" \
            else not bool(event.state & 0x4)
        # For Ctrl itself, KeyPress (type 2) means Ctrl is now held.
        if event.keysym in ("Control_L", "Control_R"):
            ctrl_held = (str(event.type) == "2")
        self.activate(ctrl_held)

    # ── Tooltip ──────────────────────────────────────────────────────────────
    def _show_tooltip(self):
        """A rounded, shadowed tooltip shown above the row on Ctrl+hover."""
        if self._tooltip:
            return
        tip_text = "Opens in new window — launcher stays open"
        measure_font = (FONT, 10, "bold")
        tmp = tk.Label(self.root, text=tip_text, font=measure_font)
        txt_w = tmp.winfo_reqwidth()
        txt_h = tmp.winfo_reqheight()
        tmp.destroy()

        icon_size, icon_gap = 20, 10
        pad_x, pad_y = 16, 10
        shadow_off, r = 3, 12
        cw = pad_x + icon_size + icon_gap + txt_w + pad_x + shadow_off
        ch = max(txt_h, icon_size) + pad_y * 2 + shadow_off

        transparent = "#F0F0F0"
        tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.attributes("-topmost", True)
        tw.attributes("-transparentcolor", transparent)
        tw.configure(bg=transparent)

        c = tk.Canvas(tw, width=cw, height=ch, bg=transparent, highlightthickness=0)
        c.pack()

        draw_rounded_rect(c, shadow_off, shadow_off, cw, ch, r, "#C4A36D")  # shadow
        draw_rounded_rect(c, 0, 0, cw - shadow_off, ch - shadow_off, r, C_ACCENT_LIGHT)

        body_h = ch - shadow_off
        ix = pad_x
        iy = (body_h - icon_size) // 2
        c.create_rectangle(ix, iy, ix + 14, iy + 12, outline=C_ACCENT, width=1.5)
        c.create_line(ix, iy + 4, ix + 14, iy + 4, fill=C_ACCENT, width=1.5)
        c.create_rectangle(ix + 6, iy + 8, ix + 20, iy + 20, fill=C_ACCENT_LIGHT,
                           outline=C_ACCENT, width=1.5)
        c.create_line(ix + 6, iy + 12, ix + 20, iy + 12, fill=C_ACCENT, width=1.5)

        c.create_text(pad_x + icon_size + icon_gap, body_h // 2, text=tip_text,
                      anchor="w", font=measure_font, fill=C_ACCENT_TEXT)

        tw.update_idletasks()
        row_x = self.row_frame.winfo_rootx()
        row_y = self.row_frame.winfo_rooty()
        row_w = self.row_frame.winfo_width()
        x = max(4, row_x + (row_w - cw) // 2)
        y = row_y - ch - 4
        if y < 0:
            y = row_y + self.row_frame.winfo_height() + 4
        tw.wm_geometry(f"+{x}+{y}")
        self._tooltip = tw

    def _hide_tooltip(self):
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    # ── Actions ──────────────────────────────────────────────────────────────
    def on_click(self, event):
        self.view.launch_project(self.path, keep_open=bool(event.state & 0x4))

    def on_show_cmd(self, _event):
        self.view.show_cmd_dialog_for(self.path)

    def on_remove(self, _event):
        self.view.remove_project(self.path)
