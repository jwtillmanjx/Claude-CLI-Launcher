"""Claude CLI Launcher package.

A Windows desktop GUI for managing and launching Claude Code CLI instances.
The launchable entry point lives one directory up in ``claude_code_launcher.py``;
this package holds the actual implementation, split into focused modules:

    config         constants: paths, colors, fonts, defaults
    store          data layer: CSV / scan / excluded / INI read+write
    naming         pure helpers: initials, badge color, sort order, tab name
    platform_win   Windows specifics: single-instance, elevation, launch
    icon           load a PNG out of the .ico for window/sidebar use
    widgets        reusable tkinter helpers (rounded rect, toggle, scroll list)
    model_field    the model autocomplete combobox + history handling
    projects_view  the Projects view (options bar, action bar, project rows)
    customize_view the Customize view (scan-directory management)
    app            the application shell that wires the views together
"""
