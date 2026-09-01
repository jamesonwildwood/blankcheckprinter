"""Render the E-13B MICR line at the bottom of a check.

The MICR line is drawn as vector rectangles from the digitized ANSI E-13B glyph
grid (see e13b_glyphs.py), so no external font is required and the physical
dimensions are exact:

  * module      = 0.013 in           (ANSI X9 design grid)
  * glyph cell  = 7 modules  = 0.091 in wide, 9 modules = 0.117 in tall
  * pitch       = 0.125 in           (8 characters per inch)

A properly licensed E-13B TrueType font may be supplied instead via
config `font_path`; if given and loadable it is used verbatim.

Template syntax (config `micr_template`):
  {r} -> routing number      {a} -> account number     {c} -> check number
  A/B/C/D -> Transit / Amount / On-Us / Dash symbols
  digits and spaces -> printed literally (a space = one blank 0.125 in cell)

IMPORTANT: the field order, symbols and spacing are dictated by YOUR bank's
MICR specification sheet. Match it exactly or the checks may be rejected.
"""

from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .e13b_glyphs import GLYPHS, SUBDIV, CELLS_W

MODULE = 0.013 * inch
PITCH = 0.125 * inch                 # 8 characters per inch
CELL = MODULE / SUBDIV               # size of one grid cell
GLYPH_HEIGHT = 9 * MODULE            # 0.117 in
# Center the 7-module glyph within the 0.125 in pitch cell.
GLYPH_LEFT_PAD = (PITCH - CELLS_W * CELL) / 2.0

_FONT_REGISTERED = {}


def expand_template(template, routing, account, check_number):
    """Substitute {r}/{a}/{c} tokens, leaving symbol/literal characters intact."""
    return (
        template
        .replace("{r}", str(routing))
        .replace("{a}", str(account))
        .replace("{c}", str(check_number))
    )


def micr_width(text):
    """Width in points of a rendered MICR string (one pitch cell per char)."""
    return len(text) * PITCH


def _draw_glyph_vector(c, ch, x, baseline_y):
    """Draw one E-13B glyph as filled rectangles at cell x/baseline."""
    grid = GLYPHS.get(ch)
    if grid is None:                 # space or unsupported -> blank cell
        return
    rows = len(grid)
    x0 = x + GLYPH_LEFT_PAD
    for j, row in enumerate(grid):
        # row 0 is the top; convert to a y measured up from the baseline.
        y = baseline_y + (rows - 1 - j) * CELL
        i = 0
        w = len(row)
        while i < w:
            if row[i] == "1":
                k = i
                while k < w and row[k] == "1":
                    k += 1
                c.rect(x0 + i * CELL, y, (k - i) * CELL, CELL, stroke=0, fill=1)
                i = k
            else:
                i += 1


def _font_point_size(font_path):
    """Point size at which this monospaced MICR font renders one char per
    0.125 in pitch (8 characters/inch). Falls back to 18 pt if metrics can't
    be read (18 pt is correct for the common advance=em/2, upm=4096 design)."""
    try:
        import logging
        logging.getLogger("fontTools").setLevel(logging.ERROR)
        from fontTools.ttLib import TTFont as _TT
        f = _TT(font_path)
        upm = f["head"].unitsPerEm
        # advance width of a digit (MICR fonts are monospaced)
        gname = f.getBestCmap()[ord("0")]
        adv = f["hmtx"][gname][0]
        pitch_pts = 0.125 * 72.0
        return pitch_pts * upm / adv
    except Exception:
        return 18.0


def _ensure_font(font_path):
    """Register a user-supplied E-13B TTF once.

    Returns (reportlab_name, point_size) or None if the font can't be loaded.
    point_size is chosen so the fixed-pitch advance equals 0.125 in.
    """
    if not font_path:
        return None
    if font_path in _FONT_REGISTERED:
        return _FONT_REGISTERED[font_path]
    try:
        name = "UserMICR_" + str(len(_FONT_REGISTERED))
        pdfmetrics.registerFont(TTFont(name, font_path))
        result = (name, _font_point_size(font_path))
        _FONT_REGISTERED[font_path] = result
        return result
    except Exception:
        _FONT_REGISTERED[font_path] = None
        return None


def draw_micr_line(c, text, right_x, baseline_y, font_path=None):
    """Draw `text` as a MICR line ending (right-justified) at right_x.

    baseline_y is the bottom of the characters. Uses vector glyphs unless a
    valid font_path is supplied. Returns the left x where drawing started.
    """
    total = micr_width(text)
    left_x = right_x - total

    font = _ensure_font(font_path)
    if font:
        name, size = font
        c.setFont(name, size)
        # Draw char-by-char to force exact 8/inch pitch. The font's own left
        # side bearing centers each glyph within its 0.125 in cell.
        x = left_x
        for ch in text:
            if ch != " ":
                c.drawString(x, baseline_y, ch)
            x += PITCH
        return left_x

    x = left_x
    for ch in text:
        _draw_glyph_vector(c, ch, x, baseline_y)
        x += PITCH
    return left_x
