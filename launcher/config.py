"""Application-wide constants: file paths, the color palette, and fonts.

Nothing here has behavior — it is the single place to change a path or a color.
"""

import os

# ── Identity ─────────────────────────────────────────────────────────────────
WINDOW_TITLE = "Claude CLI Launcher"
MUTEX_NAME = "ClaudeCLILauncherMutex_7a3f"  # named mutex for single-instance

# ── Paths ────────────────────────────────────────────────────────────────────
# APP_DIR is the project root (the folder above this package), where the data
# files, icon, and de-elevate sources live alongside the entry-point script.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSV_PATH = os.path.join(APP_DIR, "project-list-directories.csv")
SCAN_PATH = os.path.join(APP_DIR, "project-scan-directories.txt")
EXCLUDED_PATH = os.path.join(APP_DIR, "project-excluded-directories.txt")
INI_PATH = os.path.join(APP_DIR, "launcher.ini")
ICO_PATH = os.path.join(APP_DIR, "launcher.ico")
DE_ELEVATE_EXE = os.path.join(APP_DIR, "de-elevate.exe")
DE_ELEVATE_SRC = os.path.join(APP_DIR, "de-elevate.cs")

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_MODEL = "sonnet"

# ── Window geometry ──────────────────────────────────────────────────────────
WIN_W, WIN_H = 900, 650
MIN_W, MIN_H = 780, 580

# ── Color palette (light theme, amber accent) ────────────────────────────────
C_BG = "#FFFFFF"
C_SIDEBAR = "#F8F9FB"
C_BORDER = "#E5E7EB"
C_TEXT = "#1F2937"
C_TEXT_SEC = "#6B7280"
C_TEXT_MUTED = "#9CA3AF"
C_HOVER = "#F3F4F6"
C_INPUT_BG = "#F3F4F6"
C_INPUT_BORDER = "#E5E7EB"
C_ACCENT = "#D97706"
C_ACCENT_LIGHT = "#FEF3E2"   # ~rgba(217,119,6,0.08) on white
C_ACCENT_TEXT = "#B45309"
C_DANGER = "#EF4444"
C_DANGER_LIGHT = "#FEF2F2"   # ~rgba(239,68,68,0.06) on white
C_DANGER_BORDER = "#F9D0D0"  # ~rgba(239,68,68,0.18) on white

# Hover variants for button-like widgets
C_HOVER_DARK = "#E5E7EB"     # neutral button hover (darker than C_HOVER)
C_ACCENT_HOVER = "#B45309"   # amber button hover (darker than C_ACCENT)
C_DANGER_HOVER = "#FDDEDE"   # danger button hover (darker than C_DANGER_LIGHT)
C_SHOWCMD_HOVER = "#E5E7EB"  # Show CMD button hover
C_CTRL_HOVER = "#FEF3E2"     # Ctrl+hover row highlight (warm amber tint)

# ── Fonts ────────────────────────────────────────────────────────────────────
FONT = "Segoe UI"
MONO = "Consolas"
