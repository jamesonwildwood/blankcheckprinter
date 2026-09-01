"""Generate CheckPrinter.icns (a check with a MICR strip) with no external assets.

Draws a 1024x1024 master PNG with Pillow, then builds a multi-size .iconset and
runs iconutil to produce CheckPrinter.icns next to the project root.
"""

import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from checkprinter.e13b_glyphs import GLYPHS  # noqa: E402

S = 1024
NAVY = (26, 71, 110, 255)
NAVY2 = (37, 99, 148, 255)
CARD = (252, 252, 250, 255)
LINE = (176, 186, 198, 255)
INK = (24, 28, 34, 255)
GREEN = (36, 158, 92, 255)


def _system_font(size):
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _vgradient(size, top, bottom):
    grad = Image.new("RGBA", (1, size), 0)
    for y in range(size):
        t = y / (size - 1)
        grad.putpixel((0, y), tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(4)))
    return grad.resize((size, size))


def _rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def draw_micr(d, x, y, cell, text):
    """Render E-13B glyphs (14x18 grid each) as ink blocks starting at x,y."""
    pitch = 15 * cell  # 14-wide glyph + 1 cell gap
    for ch in text:
        grid = GLYPHS.get(ch)
        if grid:
            for j, row in enumerate(grid):
                i = 0
                while i < len(row):
                    if row[i] == "1":
                        k = i
                        while k < len(row) and row[k] == "1":
                            k += 1
                        d.rectangle([x + i * cell, y + j * cell,
                                     x + k * cell, y + j * cell + cell], fill=INK)
                        i = k
                    else:
                        i += 1
        x += pitch


def build_master():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Rounded background with a subtle vertical gradient.
    bg = _vgradient(S, NAVY2, NAVY)
    img.paste(bg, (0, 0), _rounded_mask(S, 230))

    d = ImageDraw.Draw(img)

    # White check card.
    cx0, cy0, cx1, cy1 = 148, 292, S - 148, S - 292
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=44, fill=CARD)

    pad = 66
    lx0, lx1 = cx0 + pad, cx1 - pad

    # "$" and amount box, top-right of the card.
    box = [cx1 - 250, cy0 + 70, cx1 - pad, cy0 + 172]
    d.rounded_rectangle(box, radius=16, outline=(120, 130, 145, 255), width=9)
    f = _system_font(120)
    d.text((cx0 + pad, cy0 + 58), "$", font=f, fill=GREEN)

    # Payee / amount lines.
    for y in (cy0 + 210, cy0 + 300):
        d.rounded_rectangle([lx0, y, lx1 - 150, y + 26], radius=13, fill=LINE)
    d.rounded_rectangle([lx0, cy0 + 300 + 90, lx1, cy0 + 300 + 116], radius=13, fill=LINE)

    # MICR strip along the bottom of the card.
    cell = 7.0
    micr = "A013C24B"  # transit + digits + on-us/amount symbols: reads as MICR
    total_w = len(micr) * 15 * cell
    mx = cx0 + (cx1 - cx0 - total_w) / 2
    my = cy1 - 18 * cell - 40
    draw_micr(d, mx, my, cell, micr)

    return img


def main():
    master = build_master()
    iconset = os.path.join(HERE, "CheckPrinter.iconset")
    os.makedirs(iconset, exist_ok=True)
    specs = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2),
             (256, 1), (256, 2), (512, 1), (512, 2)]
    for base, scale in specs:
        px = base * scale
        name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
        master.resize((px, px), Image.LANCZOS).save(os.path.join(iconset, name))

    out = os.path.join(ROOT, "CheckPrinter.icns")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
    master.resize((512, 512), Image.LANCZOS).save(os.path.join(HERE, "icon_preview.png"))
    print("wrote", out)


if __name__ == "__main__":
    main()
