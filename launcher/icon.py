"""Load a specific size out of the multi-resolution .ico as a tk.PhotoImage,
used for the in-window sidebar logo. (The titlebar icon uses iconbitmap on the
.ico directly; this is only for drawing the icon inside a widget.)
"""

import base64
import os
import struct
import tkinter as tk

from .config import ICO_PATH


def load_ico_png(target_size=32):
    """Return a tk.PhotoImage for the ``target_size`` entry in the .ico, or None.

    Each entry in a .ico is itself a PNG here, so we locate the matching entry,
    slice out its bytes, and hand them to tk via base64 (PhotoImage's data=).
    """
    if not os.path.exists(ICO_PATH):
        return None
    try:
        with open(ICO_PATH, "rb") as f:
            _reserved, _type, count = struct.unpack("<HHH", f.read(6))
            entries = []
            for _ in range(count):
                w, h, _cc, _res, _planes, _bits, img_size, offset = \
                    struct.unpack("<BBBBHHII", f.read(16))
                entries.append((256 if w == 0 else w, img_size, offset))
            match = next((e for e in entries if e[0] == target_size), None)
            if match is None:
                return None
            _, img_size, offset = match
            f.seek(offset)
            png_bytes = f.read(img_size)
        return tk.PhotoImage(data=base64.b64encode(png_bytes).decode("ascii"))
    except Exception:
        return None
