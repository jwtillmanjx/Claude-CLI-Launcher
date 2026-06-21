"""Claude CLI Launcher — a GUI for managing and launching Claude Code CLI
instances against project directories.

This is the launchable entry point (referenced by launch.vbs, launch.bat, and
the desktop shortcut). The implementation lives in the ``launcher`` package; see
``launcher/__init__.py`` for the module map.

Requires Python 3.8+ with tkinter (standard library). No pip dependencies.
"""

from launcher.app import ClaudeCLILauncher
from launcher.platform_win import ensure_single_instance


def main():
    # Keep a reference to the mutex so it isn't garbage-collected while we run.
    _mutex = ensure_single_instance()
    ClaudeCLILauncher().run()


if __name__ == "__main__":
    main()
