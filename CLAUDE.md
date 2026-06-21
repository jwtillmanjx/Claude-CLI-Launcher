# Claude CLI Launcher


A Windows desktop GUI for managing and launching Claude Code CLI instances against project directories.


## Tech Stack


- **Python 3.8+** with **tkinter only** (no pip dependencies)
- **ctypes** for Windows API calls (single-instance mutex, window management)
- Fonts: Segoe UI (primary), Consolas (monospace)
- Target OS: Windows 11


## Project Files


| File | Purpose |
|------|---------|
| `claude_code_launcher.py` | Thin entry point: single-instance guard, then build and run the app. The implementation lives in the `launcher/` package. |
| `launcher/` | Application package (see Architecture below) |
| `launch.bat` | Hands off to the silent VBS launcher (passed as `%1`, or local `launch.vbs`) via `start` + `exit` so its console window never waits on the GUI and always closes immediately |
| `launch.vbs` | Silent launcher (no console window, used by shortcut) |
| `Claude CLI Launcher.lnk` | Windows shortcut pointing to `launch.vbs` with custom icon |
| `launcher.ico` | App icon (16/32/48/256px, amber rounded square with `>_` symbol) |
| `generate_icon.py` | Generates the .ico file from scratch using pure Python (struct/zlib) |
| `de-elevate.cs` | C# source for `de-elevate.exe`, compiled at runtime to drop the admin token |


### `launcher/` package


| Module | Purpose |
|--------|---------|
| `config.py` | Constants only: file paths, the color palette, fonts, window geometry, `DEFAULT_MODEL`, mutex name |
| `store.py` | Data layer: read/write the CSV, scan, excluded, and INI files; `derive_projects`, `path_in_list` |
| `naming.py` | Pure helpers: `get_initials`, `badge_color`/`hsl_to_hex`, `sort_projects`, `tab_name_for`, `dir_name` |
| `platform_win.py` | Windows specifics: single-instance mutex, de-elevate compile/launch, launch-command builders, `launch_terminal`, `close_all_instances` |
| `icon.py` | Load a PNG out of the `.ico` as a `tk.PhotoImage` for the sidebar logo |
| `widgets.py` | Reusable tkinter helpers: `draw_rounded_rect`, `add_placeholder`, `btn_hover`, `ToggleSwitch`, `ScrollableList` |
| `model_field.py` | `ModelField` — the autocomplete model combobox plus history/placeholder state and the `--model` preview |
| `projects_view.py` | `ProjectsView` (options bar, action bar, project list, launch) and `ProjectRow` (one row's widgets + hover/tooltip/buttons) |
| `customize_view.py` | `CustomizeView` — scan-directory management |
| `app.py` | `ClaudeCLILauncher` — window chrome, shared state, sidebar nav, view switching |


## Data Files (auto-created on first run)


| File | Format | Purpose |
|------|--------|---------|
| `project-list-directories.csv` | `"full_path","timestamp"` (quoted CSV) | All known project directories and their last-launched timestamps |
| `project-scan-directories.txt` | One directory path per line | Parent directories to scan for child project dirs |
| `project-excluded-directories.txt` | One normalized path per line | Projects removed by the user; prevents re-derivation from scan dirs |
| `launcher.ini` | `[Models]` section (`selected` + pipe-delimited `history`) and `[Options]` section (`skip_permissions`, `run_as_admin` booleans) | Last-used model (auto-selected on next launch), model dropdown history, and the last Skip Permissions / Run as Administrator toggle states (restored on next launch) |


## Architecture


The app is split into the focused modules listed above. `ClaudeCLILauncher` (in `app.py`) is the shell: it owns the window, the shared in-memory state (`projects`, `scan_dirs`, `excluded`, the `skip_perms`/`run_admin` BooleanVars, and the `ModelField`), and switches between two views. Each view is its own class (`ProjectsView`, `CustomizeView`) constructed once and re-`show()`n on navigation; views read/write shared state through the `app` reference passed to them. The two views are toggled via sidebar navigation:


### Projects View
- **Options bar**: Row 1 has "Skip Permissions?" toggle (default ON, shows `--dangerously-skip-permissions` flag text when active) and "Run as Administrator?" toggle. Row 2 has the **Model** auto-complete combobox (history sorted descending, persisted to `launcher.ini`) with a Remove button and a live `--model <value>` preview. Empty input shows placeholder `sonnet`, which is also the default model used when no value is entered. The last-used model is saved to history (if new) only after a successful launch and auto-selected on next startup.
- **Action bar**: Search input (filters by name/path), Open button (folder browser), Close All Instances button (kills all `*claude*` processes)
- **Project list**: Scrollable rows with colored badge (initials from `.`-delimited dir name), project name, full path (word-wrapped). Hover reveals Show CMD and Remove buttons. Clicking a row launches Claude CLI. Ctrl+Click launches without closing the launcher.


### Customize View
- Manage scan directories. Adding a scan dir auto-discovers its immediate child directories and adds them to the project list.
- Users can type a path directly or use the folder browser.


### Key Behaviors
- **Single instance**: Uses a Windows named mutex (`ClaudeCLILauncherMutex_7a3f`). Second launch brings existing window to front via `FindWindowW`/`SetForegroundWindow`.
- **Launch process**: Updates timestamp in CSV, launches `wt.exe new-tab --title "DirName" -d "path" cmd /k claude --name <tab> --model <model> [--dangerously-skip-permissions]`, then closes the launcher (unless Ctrl held). Honors Run as Administrator (elevates via `runas`) and de-elevates when the launcher itself is elevated.
- **Project removal**: Removes from CSV and adds path to excluded list so scan dirs don't re-add it on next startup.
- **Startup**: Loads CSV + scan dirs, re-derives projects from scan dirs (respecting exclusions), displays Projects view.
- **Scroll preservation**: Removing a project preserves scroll position and re-binds mousewheel.
- **Row hover**: Each row is a `ProjectRow`; `ProjectsView._hovered_row` tracks the single active row so only one shows action buttons at a time. Ctrl while hovering swaps the badge to a "new window" icon and shows a tooltip.


## Color Palette


Light theme with amber accent (`#D97706`). All colors are constants in `launcher/config.py` (`C_BG`, `C_SIDEBAR`, `C_ACCENT`, `C_DANGER`, etc.) with hover variants (`C_HOVER_DARK`, `C_ACCENT_HOVER`, `C_DANGER_HOVER`).


## Conventions


- All button-like elements are `tk.Label` widgets with `cursor="hand2"` and hover style changes via the `btn_hover()` helper (in `widgets.py`) or `add="+"` bindings.
- Toggle switches use the reusable `ToggleSwitch` widget; scrollable areas use the reusable `ScrollableList` widget (both in `widgets.py`).
- Path comparisons always use `os.path.normcase(os.path.normpath(...))` for case-insensitive matching on Windows (see `store._norm`).
- CSV is read/written with Python's `csv` module using `QUOTE_ALL` to handle paths with commas.
- The window centers on screen at launch (900x650, min 780x580).
- Dialog windows (Show CMD) center within the main window and use the same icon.


## Running


```
# From terminal
python claude_code_launcher.py


# Or double-click
Claude CLI Launcher.lnk


# To regenerate the icon
python generate_icon.py
```


## Windows Shortcut


The `Claude CLI Launcher.lnk` shortcut should be placed on the user's desktop so it can be launched with a double-click. The shortcut targets `wscript.exe` running `launch.vbs` (to avoid a console window flash), with the working directory set to the project folder and the custom `.ico` as its icon.
