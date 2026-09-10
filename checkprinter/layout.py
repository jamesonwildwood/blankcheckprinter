"""Draw a business check (check-on-the-bottom format) to a PDF for blank stock.

Page (US Letter, 8.5 x 11 in), origin at bottom-left:

    +----------------------------------+  y = 11.0
    |            record stub 2         |
    +----------------------------------+  y = 2 * band_height
    |            record stub 1         |
    +----------------------------------+  y = band_height
    |     NEGOTIABLE CHECK (printed)   |
    |     ...            MICR line     |  <- MICR in the 5/8" clear band
    +----------------------------------+  y = 0

Everything is drawn by us because the stock is truly blank. A global
(offset_x, offset_y) nudge lets you register the print to your paper.
"""

import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from .micr import (draw_micr_line, expand_template, micr_width, PITCH,
                   GLYPH_LEFT_PAD)
from .numwords import amount_to_words

PAGE_W, PAGE_H = letter                 # 612 x 792 pt (8.5 x 11 in)
LM = 0.40 * inch                        # left margin inside the check
RX = PAGE_W - 0.40 * inch               # right content edge
CLEAR_BAND = 0.625 * inch               # MICR clear band; keep other ink above

# Double-window envelope guides (OSDS Payroll, 3-7/8 x 9-1/4"), as (x, y, w, h)
# in inches from the check's bottom-left, assuming the check is inserted flush to
# the envelope's bottom-left. Bottom window = payee (recipient); top = return.
# Both windows are left-aligned at ~0.25" on the envelope.
ENV_BOTTOM_WINDOW = (0.25, 0.75, 3.5, 1.0)    # payee window
ENV_TOP_WINDOW = (0.25, 2.5, 3.5, 0.875)      # return window

# Left edge (inches) of the return-address (From) and payee (To) blocks on the
# top fold; aligned to the check's left margin ("Pay to" text), slightly inset
# from the window edge. Nudge further with the window_return_dx / window_payee_dx
# offsets in Settings.
WIN_RETURN_X = 0.40     # From block
WIN_PAYEE_X = 0.40      # To block


def _line(c, x1, x2, y, width=0.7):
    c.setLineWidth(width)
    c.line(x1, y, x2, y)


def _label(c, x, y, text, size=6, align="left"):
    c.setFont("Helvetica", size)
    if align == "right":
        c.drawRightString(x, y, text)
    elif align == "center":
        c.drawCentredString(x, y, text)
    else:
        c.drawString(x, y, text)


def _fmt_amount(amount):
    return f"{amount:,.2f}"


def _transit_index(text):
    """Index of the left Transit symbol ('A') in an expanded MICR string."""
    i = text.find("A")
    return i if i >= 0 else 0


def _micr_right_x(cfg, text):
    """Right-edge x for the MICR line given the configured horizontal anchor.

    transit: micr_left_margin = inches from the left edge to the inked left edge
             of the left Transit symbol (routing/transit stay fixed regardless of
             how many digits the check number has).
    """
    align = cfg.get("micr_align", "transit")
    total = micr_width(text)
    if align == "transit":
        idx = _transit_index(text)
        left = cfg.get("micr_left_margin", 3.0) * inch - idx * PITCH - GLYPH_LEFT_PAD
        return left + total
    if align == "left":
        return cfg.get("micr_left_margin", 1.0) * inch + total
    if align == "center":
        return (PAGE_W + total) / 2.0
    return PAGE_W - cfg.get("micr_right_margin", 0.3125) * inch


def draw_negotiable_check(c, cfg, check):
    """Draw the actual check in the bottom band (bottom edge at y = 0)."""
    bh = cfg["check_band_height"] * inch

    # Optional border around the check. The top edge is intentionally omitted
    # because the stock is perforated there (drawing it looks like a stray line).
    if cfg.get("draw_border"):
        c.setLineWidth(1.0)
        x0, x1 = 0.14 * inch, PAGE_W - 0.14 * inch
        y0, y1 = 0.14 * inch, bh - 0.14 * inch
        c.line(x0, y0, x1, y0)   # bottom
        c.line(x0, y0, x0, y1)   # left
        c.line(x1, y0, x1, y1)   # right

    # --- Company (maker) block, top-left ---
    y = bh - 0.42 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LM, y, cfg.get("company_name", ""))
    y -= 0.155 * inch
    for key, size in (("company_line2", 8), ("company_address", 8),
                      ("company_citystate", 8), ("company_phone", 8)):
        val = cfg.get(key, "")
        if val:
            c.setFont("Helvetica", size)
            c.drawString(LM, y, val)
            y -= 0.135 * inch

    # --- Check number + fraction, top-right ---
    c.setFont("Helvetica", 8)
    c.drawRightString(RX - 0.62 * inch, bh - 0.40 * inch, "No.")
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(RX, bh - 0.40 * inch, str(check["number"]))
    if cfg.get("fraction"):
        _label(c, RX, bh - 0.62 * inch, cfg["fraction"], size=8, align="right")

    # --- Date, mid-right ---
    date_y = bh - 1.02 * inch
    _line(c, RX - 1.75 * inch, RX, date_y)
    c.setFont("Helvetica", 10)
    c.drawString(RX - 1.65 * inch, date_y + 0.045 * inch, check.get("date", ""))
    _label(c, RX - 0.875 * inch, date_y - 0.135 * inch, "DATE", size=6,
           align="center")

    # --- Pay to the order of ---
    pay_y = bh - 1.55 * inch
    _label(c, LM, pay_y + 0.10 * inch, "PAY TO THE", size=6)
    _label(c, LM, pay_y + 0.02 * inch, "ORDER OF", size=6)
    _line(c, LM + 0.72 * inch, RX - 1.55 * inch, pay_y)
    c.setFont("Helvetica", 11)
    c.drawString(LM + 0.82 * inch, pay_y + 0.045 * inch, check.get("payee", ""))

    # --- Amount box (numeric) ---
    box_x0, box_x1 = RX - 1.45 * inch, RX
    box_y0, box_y1 = pay_y - 0.10 * inch, pay_y + 0.20 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(box_x0 - 0.06 * inch, pay_y + 0.02 * inch, "$")
    c.setLineWidth(0.9)
    c.rect(box_x0, box_y0, box_x1 - box_x0, box_y1 - box_y0, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(box_x1 - 0.06 * inch, box_y0 + 0.075 * inch,
                      "**" + _fmt_amount(check["amount"]))

    # --- Legal / written-amount line ("... DOLLARS") ---
    words_y = bh - 2.02 * inch
    _line(c, LM, RX - 0.80 * inch, words_y)
    c.setFont("Helvetica", 10.5)
    c.drawString(LM + 0.04 * inch, words_y + 0.045 * inch, check.get("words", ""))
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(RX, words_y + 0.045 * inch, "DOLLARS")

    # --- Bank block (anchored above the memo/signature row) ---
    bank_y = 1.24 * inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(LM, bank_y, cfg.get("bank_name", ""))
    if cfg.get("bank_citystate"):
        c.setFont("Helvetica", 8)
        c.drawString(LM, bank_y - 0.13 * inch, cfg["bank_citystate"])

    # --- Memo (left) and signature (right); anchored to the page bottom ---
    memo_y = 0.74 * inch
    _label(c, LM, memo_y, "MEMO", size=6)
    _line(c, LM + 0.50 * inch, LM + 2.9 * inch, memo_y)
    c.setFont("Helvetica", 9)
    c.drawString(LM + 0.58 * inch, memo_y + 0.04 * inch, check.get("memo", ""))

    sig_y = 0.92 * inch
    _line(c, RX - 2.7 * inch, RX, sig_y)
    _label(c, (RX - 2.7 * inch + RX) / 2.0, sig_y - 0.145 * inch,
           cfg.get("signature_text", "AUTHORIZED SIGNATURE"), size=6,
           align="center")

    # --- MICR line (clear band) ---
    _draw_micr(c, cfg, check)


def _draw_micr(c, cfg, check):
    """Draw the MICR line from the configured template/anchor (shared)."""
    text = expand_template(cfg["micr_template"], cfg.get("routing", ""),
                           cfg.get("account", ""), check["number"])
    draw_micr_line(
        c, text,
        right_x=_micr_right_x(cfg, text),
        baseline_y=cfg["micr_baseline"] * inch,
        font_path=cfg.get("font_path") or None,
    )


def draw_window_address_panel(c, cfg, check, y_bottom):
    """First-fold panel for window format: only the From (company) and To
    (payee) addresses, at the same window positions as the check.

    When trifolded so this panel faces the envelope, the windows show just the
    two addresses on an otherwise blank page (the check folds inside). Uses the
    same window nudge offsets as the check so both stay calibrated together.
    """
    pdx = cfg.get("window_payee_dx", 0.0) * inch
    pdy = cfg.get("window_payee_dy", 0.0) * inch
    rdx = cfg.get("window_return_dx", 0.0) * inch
    rdy = cfg.get("window_return_dy", 0.0) * inch

    # From (company) — top window position
    rx0 = WIN_RETURN_X * inch + rdx
    c.setFont("Helvetica-Bold", 11)
    c.drawString(rx0, y_bottom + 3.00 * inch + rdy, cfg.get("company_name", ""))
    c.setFont("Helvetica", 8.5)
    yy = y_bottom + 2.82 * inch + rdy
    for key in ("company_address", "company_citystate"):
        if cfg.get(key):
            c.drawString(rx0, yy, cfg[key])
            yy -= 0.14 * inch

    # To (payee) — bottom window position
    px0 = WIN_PAYEE_X * inch + pdx
    c.setFont("Helvetica-Bold", 12)
    c.drawString(px0, y_bottom + 1.50 * inch + pdy, check.get("payee", ""))
    c.setFont("Helvetica", 10.5)
    yy = y_bottom + 1.28 * inch + pdy
    for line in (check.get("payee_address", ""), check.get("payee_citystate", "")):
        if line:
            c.drawString(px0, yy, line)
            yy -= 0.20 * inch


def draw_stub(c, cfg, check, y_bottom, height):
    """Draw a compact record stub with its bottom edge at y_bottom."""
    top = y_bottom + height
    c.setLineWidth(0.5)
    # separator line at the top of the stub (near the perforation)
    _line(c, LM, RX, top - 0.05 * inch, width=0.4)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(LM, top - 0.35 * inch, cfg.get("company_name", ""))
    c.setFont("Helvetica", 8)
    c.drawRightString(RX, top - 0.35 * inch, f"Check No. {check['number']}")
    c.drawRightString(RX, top - 0.52 * inch, f"Date  {check.get('date', '')}")

    rows = [
        ("Pay to", check.get("payee", "")),
        ("Amount", "$ " + _fmt_amount(check["amount"])),
        ("", check.get("words", "")),
        ("Memo", check.get("memo", "")),
    ]
    ry = top - 0.85 * inch
    for label, value in rows:
        if label:
            c.setFont("Helvetica-Bold", 8)
            c.drawString(LM, ry, label + ":")
        c.setFont("Helvetica", 8.5)
        c.drawString(LM + 0.75 * inch, ry, value)
        ry -= 0.24 * inch


def _draw_perf_guides(c, cfg):
    bh = cfg["check_band_height"] * inch
    c.setDash(3, 3)
    c.setLineWidth(0.4)
    for i in range(1, cfg["num_stubs"] + 1):
        y = i * bh
        if y < PAGE_H:
            c.line(0, y, PAGE_W, y)
    c.setDash()


def _has_window_envelope(cfg):
    """True when a window envelope is selected (address panel is printed)."""
    return cfg.get("envelope", "10_double_left") not in (None, "", "none")


def check_bottom_y(cfg):
    """Y of the check panel's bottom edge (0 for check-on-bottom)."""
    if cfg.get("check_position") == "top":
        return cfg.get("num_stubs", 0) * cfg["check_band_height"] * inch
    return 0.0


def address_bottom_y(cfg):
    """Y of the address panel's bottom edge (the fold opposite the check)."""
    if cfg.get("check_position") == "top":
        return 0.0
    return cfg.get("num_stubs", 0) * cfg["check_band_height"] * inch


def _draw_page_content(c, cfg, check):
    """Draw the stubs + check for one page (shared by real and test output).

    The check is always the standard single-check layout (no payee address); a
    window envelope adds a To/From address panel on the fold opposite the check.
    Check-on-top swaps the check and address panels.
    """
    bh = cfg["check_band_height"] * inch
    window = _has_window_envelope(cfg)
    n = cfg.get("num_stubs", 0)
    top = cfg.get("check_position") == "top"

    for i in range(n):
        yb = i * bh if top else (i + 1) * bh
        is_address_fold = window and (i == 0 if top else i == n - 1)
        if is_address_fold:
            draw_window_address_panel(c, cfg, check, y_bottom=yb)
        else:
            draw_stub(c, cfg, check, y_bottom=yb, height=bh)

    c.saveState()
    c.translate(0, check_bottom_y(cfg))
    draw_negotiable_check(c, cfg, check)
    c.restoreState()


def build_check_pdf(cfg, check, out_path):
    """Render a full page (check + stubs) to out_path."""
    c = canvas.Canvas(out_path, pagesize=letter)
    c.translate(cfg.get("offset_x", 0.0) * inch, cfg.get("offset_y", 0.0) * inch)

    if cfg.get("draw_perf_guides"):
        _draw_perf_guides(c, cfg)

    _draw_page_content(c, cfg, check)
    c.showPage()
    c.save()
    return out_path


def _alignment_sample(cfg):
    """A fake, non-negotiable sample check for the alignment test.

    Uses 999999999 for routing and account so it can never be cashed, $0.00,
    the configured company as the From, and a placeholder payee.
    """
    sample_cfg = dict(cfg)
    sample_cfg["routing"] = "999999999"
    sample_cfg["account"] = "999999999"
    if not sample_cfg.get("company_name"):
        sample_cfg.update(company_name="Anytown Company", company_address="123 Main St",
                          company_citystate="Pleasantville, AA 99999")
    sample_chk = {
        "number": cfg.get("next_check_number", 1001),
        "date": datetime.date.today().strftime("%m/%d/%Y"),
        "payee": "Anytown Company",
        "payee_address": "123 Main St",
        "payee_citystate": "Pleasantville, AA 99999",
        "amount": 0.0,
        "words": amount_to_words(0.0),
        "memo": "ALIGNMENT TEST - VOID",
    }
    return sample_cfg, sample_chk


def _draw_window_guides(c, y_offset=0.0, prefix=""):
    """Dashed outlines of the envelope windows at a panel offset (alignment test)."""
    c.setDash(4, 3)
    c.setLineWidth(0.8)
    for (x, y, w, h), name in ((ENV_BOTTOM_WINDOW, "BOTTOM WINDOW (payee)"),
                               (ENV_TOP_WINDOW, "TOP WINDOW (return address)")):
        c.rect(x * inch, y * inch + y_offset, w * inch, h * inch, stroke=1, fill=0)
        _label(c, x * inch + 0.05 * inch, (y + h) * inch + y_offset + 0.05 * inch,
               prefix + name, size=7)
    c.setDash()


def build_alignment_pdf(cfg, out_path):
    """A test page: perforation guides, a 1-inch grid, and the MICR clear band.

    Print this on a blank sheet (or your stock) and hold it to the light against
    your check stock to check registration before printing real checks.
    """
    c = canvas.Canvas(out_path, pagesize=letter)
    c.translate(cfg.get("offset_x", 0.0) * inch, cfg.get("offset_y", 0.0) * inch)
    bh = cfg["check_band_height"] * inch
    sample_cfg, sample_chk = _alignment_sample(cfg)
    check_yb = check_bottom_y(cfg)      # bottom edge of the check panel

    # 1-inch grid (drawn first, behind everything)
    c.setLineWidth(0.25)
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    x = 0
    while x <= PAGE_W:
        c.line(x, 0, x, PAGE_H)
        x += inch
    y = 0
    while y <= PAGE_H:
        c.line(0, y, PAGE_W, y)
        y += inch
    c.setStrokeColorRGB(0, 0, 0)

    # MICR clear band shading, at the check's bottom edge (behind the check).
    c.setFillColorRGB(0.9, 0.95, 1.0)
    c.rect(0, check_yb, PAGE_W, CLEAR_BAND, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)

    # Perforation guides
    c.setDash(4, 3)
    for i in range(1, cfg["num_stubs"] + 1):
        yy = i * bh
        if yy < PAGE_H:
            c.line(0, yy, PAGE_W, yy)
    c.setDash()

    # The full sample check + stubs (fake routing/account, $0.00, non-negotiable)
    _draw_page_content(c, sample_cfg, sample_chk)

    _label(c, LM, check_yb + CLEAR_BAND - 0.18 * inch,
           'MICR clear band (5/8" from bottom of check) — keep clear except MICR',
           size=7)

    # Locate the MICR line the check drew, to mark the left Transit symbol.
    micr = expand_template(sample_cfg["micr_template"], sample_cfg["routing"],
                           sample_cfg["account"], sample_chk["number"])
    base = check_yb + sample_cfg["micr_baseline"] * inch
    left = _micr_right_x(sample_cfg, micr) - micr_width(micr)
    _label(c, left, base - 0.16 * inch,
           f'MICR starts {left / inch:.2f}" from left edge', size=6)
    tx = left + _transit_index(micr) * PITCH + GLYPH_LEFT_PAD
    c.setDash(2, 2)
    c.setLineWidth(0.5)
    c.line(tx, base, tx, base + 0.85 * inch)
    c.setDash()
    _label(c, tx + 0.03 * inch, base + 0.7 * inch,
           f'left transit: {tx / inch:.2f}" from left', size=6)

    # Envelope window outlines on the address fold (window envelope only)
    if _has_window_envelope(cfg) and cfg.get("num_stubs", 0) >= 1:
        _draw_window_guides(c, address_bottom_y(cfg), prefix="ADDRESS FOLD ")

    _label(c, LM, PAGE_H - 0.3 * inch,
           "ALIGNMENT TEST — VOID $0.00 sample, routing/account 999999999. "
           f"1in grid; band {cfg['check_band_height']}in, stubs {cfg['num_stubs']}.",
           size=8)
    c.showPage()
    c.save()
    return out_path
