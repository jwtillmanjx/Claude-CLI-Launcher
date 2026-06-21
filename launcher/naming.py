"""Pure, side-effect-free helpers for turning a project path into display bits:
its badge initials, a stable badge color, the launch tab name, and sort order.
"""

import hashlib
import math
import os
import re


def dir_name(path):
    """The final path component (the project's display name)."""
    return os.path.basename(os.path.normpath(path))


def tab_name_for(dirname):
    """Windows Terminal tab name: the part after the last dot, if any.

    e.g. "com.example.ResumeBuilder" -> "ResumeBuilder", "MyApp" -> "MyApp".
    """
    return dirname.rsplit(".", 1)[-1] if "." in dirname else dirname


def get_initials(path):
    """Up to four uppercase initials derived from the directory name.

    Splits on whitespace/dots/dashes/underscores, then further splits CamelCase
    ("ResumeBuilder" -> R, B; "CLI" -> C), and takes the first letter of each.
    """
    tokens = re.split(r"[\s.\-_]+", dir_name(path))
    words = []
    for token in tokens:
        if not token:
            continue
        # Split CamelCase / acronyms / digits into separate words.
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", token)
        words.extend(parts if parts else [token])
    initials = "".join(w[0].upper() for w in words if w)
    return initials[:4]


def hsl_to_hex(h, s, l):
    """Convert HSL (h in degrees, s/l in percent) to a #rrggbb string."""
    s /= 100
    l /= 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    r, g, b = int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def badge_color(path):
    """A deterministic, pleasant badge color derived from the full path."""
    h = int(hashlib.md5(path.encode()).hexdigest(), 16)
    hue = h % 360
    saturation = 55 + (h // 360) % 30   # 55-84
    lightness = 25 + (h // 10800) % 21  # 25-45
    return hsl_to_hex(hue, saturation, lightness)


def sort_projects(rows):
    """Default ordering: launched projects first (most recent first), then the
    never-launched ones alphabetically by directory name."""
    with_ts = [r for r in rows if r[1]]
    without_ts = [r for r in rows if not r[1]]
    with_ts.sort(key=lambda r: r[1], reverse=True)
    without_ts.sort(key=lambda r: dir_name(r[0]).lower())
    return with_ts + without_ts
