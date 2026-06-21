"""Windows-specific concerns, kept in one place so the rest of the app is plain
tkinter: the single-instance guard, building the Claude launch command, and
launching Windows Terminal at the right integrity level.

Integrity-level handling has three cases:
  * Run-as-admin requested   -> ShellExecuteW with the "runas" verb (elevates).
  * Launcher is itself admin  -> de-elevate.exe strips the admin token so the
                                 spawned terminal runs as a normal user.
  * Otherwise                 -> ShellExecuteW "open" inherits the normal token.
"""

import ctypes
import os
import subprocess
import sys
import tempfile
import uuid

from .config import (DE_ELEVATE_EXE, DE_ELEVATE_SRC, MUTEX_NAME, WINDOW_TITLE)

CREATE_NO_WINDOW = 0x08000000


# ── Single instance ──────────────────────────────────────────────────────────
def ensure_single_instance():
    """Acquire a named mutex. If another instance owns it, bring that window to
    the front and exit this process. Returns the mutex handle on success — the
    caller must keep a reference so it isn't garbage-collected.
    """
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, WINDOW_TITLE)
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        sys.exit(0)
    return mutex


# ── Elevation helpers ────────────────────────────────────────────────────────
def is_user_admin():
    """True if the current process is running elevated."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_de_elevate():
    """Compile de-elevate.exe from its C# source if the exe is missing.

    Returns True if the exe exists (or was successfully built), else False.
    """
    if os.path.exists(DE_ELEVATE_EXE):
        return True
    if not os.path.exists(DE_ELEVATE_SRC):
        return False
    for framework in (r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319",
                      r"C:\Windows\Microsoft.NET\Framework\v4.0.30319"):
        csc = os.path.join(framework, "csc.exe")
        if os.path.exists(csc):
            result = subprocess.run(
                [csc, "-nologo", "-optimize",
                 f"-out:{DE_ELEVATE_EXE}", DE_ELEVATE_SRC],
                capture_output=True, creationflags=CREATE_NO_WINDOW)
            return result.returncode == 0
    return False


# ── Command construction ─────────────────────────────────────────────────────
def claude_command(tab_name, model, skip_permissions):
    """The ``claude ...`` command run inside the terminal tab."""
    cmd = f"claude --name {tab_name} --model {model}"
    if skip_permissions:
        cmd += " --dangerously-skip-permissions"
    return cmd


def wt_params(dirname, path, claude_cmd):
    """The argument string passed to ``wt.exe`` to open the tab."""
    return f'new-tab --title "{dirname}" -d "{path}" cmd /k {claude_cmd}'


def display_command(params, run_as_admin):
    """A human-readable representation of the launch, for the Show CMD dialog."""
    if run_as_admin:
        return f"powershell Start-Process wt.exe -Verb RunAs -ArgumentList '{params}'"
    return f"wt.exe {params}"


# ── Launching ────────────────────────────────────────────────────────────────
def launch_terminal(params, run_as_admin):
    """Open Windows Terminal with ``params`` at the appropriate integrity level."""
    if run_as_admin:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "wt.exe", params, None, 1)
    elif is_user_admin() and ensure_de_elevate():
        # Launcher is elevated — drop the admin token via de-elevate.exe. The
        # command goes through a temp batch file to avoid argument-quoting issues.
        bat = os.path.join(tempfile.gettempdir(),
                           f"ClaudeLaunch_{uuid.uuid4().hex[:8]}.cmd")
        with open(bat, "w", encoding="utf-8") as f:
            f.write(f"@wt.exe {params}\n")
            f.write('@del "%~f0"\n')
        subprocess.Popen([DE_ELEVATE_EXE, "cmd", "/c", bat])
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "open", "wt.exe", params, None, 1)


def close_all_instances():
    """Kill every running process whose name contains 'claude'."""
    try:
        subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object {$_.ProcessName -like '*claude*'} "
             "| Stop-Process -Force"],
            capture_output=True)
    except Exception:
        pass
