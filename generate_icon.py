"""
Generate a modern .ico file for Claude CLI Launcher.
Pure Python (math + struct + zlib only). No pip dependencies.

Renders each size with:
  - Signed-distance-field rounded square (true circular corners, AA edge)
  - Anti-aliased ">_" symbol (distance-to-segment, soft stroke edges)
  - Subtle top-to-bottom amber gradient
"""

import math
import os
import struct
import zlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICO_PATH = os.path.join(SCRIPT_DIR, "launcher.ico")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _dist_seg(px, py, ax, ay, bx, by):
    """Euclidean distance from (px,py) to segment (ax,ay)-(bx,by)."""
    dx, dy = bx - ax, by - ay
    lsq = dx * dx + dy * dy
    if lsq < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / lsq))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _sdf_rrect(px, py, cx, cy, half, corner_r):
    """Signed distance to a square rounded-rect (negative = inside)."""
    qx = abs(px - cx) - (half - corner_r)
    qy = abs(py - cy) - (half - corner_r)
    return math.sqrt(max(qx, 0.0) ** 2 + max(qy, 0.0) ** 2) - corner_r


# ── Icon renderer ──────────────────────────────────────────────────────────────

def create_png(size):
    """Return PNG bytes for one icon size."""
    s    = size
    half = s / 2.0

    # ── Shape ─────────────────────────────────────────────────────────
    # Corner radius: 22 % of size → clean, slightly squarish circle
    corner_r = s * 0.22
    # Anti-alias band width (narrows at small sizes so thin icons stay crisp)
    aa = max(0.55, s * 0.016)

    def badge_d(px, py):
        return _sdf_rrect(px, py, half, half, half, corner_r)

    # ── Background gradient (top → bottom) ────────────────────────────
    # Bright warm amber at top, deep rich amber at bottom
    g_top = (0xF0, 0x9D, 0x0D)
    g_bot = (0xB8, 0x5C, 0x03)

    def bg(py):
        t = max(0.0, min(1.0, py / s))
        return (
            int(g_top[0] + (g_bot[0] - g_top[0]) * t),
            int(g_top[1] + (g_bot[1] - g_top[1]) * t),
            int(g_top[2] + (g_bot[2] - g_top[2]) * t),
        )

    # ── Symbol ">_" ───────────────────────────────────────────────────
    # Half-stroke width scales with size; minimum keeps it legible at 16 px
    hw = max(1.35, s * 0.043)

    tip_x  = s * 0.53          # ">" tip x (just right of centre)
    tip_y  = s * 0.475         # ">" tip y (just above midline)
    arm_lx = s * 0.205         # left end of both arms
    arm_h  = s * 0.228         # half-height of the chevron

    u_y    = tip_y + arm_h     # underscore baseline = bottom-arm y
    u_x1   = tip_x + s * 0.065
    u_x2   = s * 0.815

    segs = [
        (arm_lx, tip_y - arm_h, tip_x, tip_y),  # > top arm
        (arm_lx, tip_y + arm_h, tip_x, tip_y),  # > bottom arm
        (u_x1,   u_y,           u_x2,  u_y),    # _
    ]

    # ── Pixel loop ────────────────────────────────────────────────────
    pixels = []
    for y in range(s):
        row = []
        for x in range(s):
            px, py = x + 0.5, y + 0.5       # sample at pixel centre
            d = badge_d(px, py)

            # Outside badge — fully transparent
            if d > aa:
                row.append((0, 0, 0, 0))
                continue

            br, bg_, bb = bg(py)
            alpha = int(255 * max(0.0, min(1.0, (aa - d) / (2.0 * aa))))

            # Badge anti-aliased edge — background colour with fading alpha
            if d > -aa:
                row.append((br, bg_, bb, alpha))
                continue

            # Inside badge — test distance to symbol strokes
            md = min(_dist_seg(px, py, *seg) for seg in segs)

            if md < hw - aa:                  # fully inside stroke → white
                row.append((255, 255, 255, 255))
            elif md < hw + aa:                # stroke anti-aliased edge
                t = max(0.0, min(1.0, (md - (hw - aa)) / (2.0 * aa)))
                row.append((
                    int(255 + (br  - 255) * t),
                    int(255 + (bg_ - 255) * t),
                    int(255 + (bb  - 255) * t),
                    255,
                ))
            else:                             # plain badge background
                row.append((br, bg_, bb, 255))

        pixels.append(row)

    return _encode_png(pixels, s, s)


# ── PNG encoder ────────────────────────────────────────────────────────────────

def _encode_png(pixels, width, height):
    def chunk(tag, data):
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    sig  = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))

    raw = b''.join(
        b'\x00' + b''.join(struct.pack("BBBB", *px) for px in row)
        for row in pixels
    )
    idat = chunk(b'IDAT', zlib.compress(raw, 9))
    iend = chunk(b'IEND', b'')

    return sig + ihdr + idat + iend


# ── ICO builder ────────────────────────────────────────────────────────────────

def create_ico(sizes):
    images = [(s, create_png(s)) for s in sizes]
    n      = len(images)
    header = struct.pack("<HHH", 0, 1, n)

    entries = b''
    blocks  = b''
    offset  = 6 + n * 16

    for s, data in images:
        w = 0 if s >= 256 else s
        h = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        blocks  += data
        offset  += len(data)

    return header + entries + blocks


if __name__ == "__main__":
    print("Rendering icon sizes: 16, 32, 48, 256 …")
    ico_data = create_ico([16, 32, 48, 256])
    with open(ICO_PATH, "wb") as f:
        f.write(ico_data)
    print(f"Done: {ICO_PATH}  ({len(ico_data):,} bytes)")
