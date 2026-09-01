"""Persisted settings for CheckPrinter (bank/account info, layout, offsets).

Stored as JSON in ~/Library/Application Support/CheckPrinter/config.json.
The account/routing numbers live only on this Mac in that file.
"""

import json
import os

APP_DIR = os.path.expanduser("~/Library/Application Support/CheckPrinter")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
REGISTER_PATH = os.path.join(APP_DIR, "check_register.csv")
OUTPUT_DIR = os.path.join(APP_DIR, "printed")

# Common MICR presets. C = On-Us symbol, A = Transit symbol.
MICR_PRESET_PERSONAL = "A{r}A {a}C {c}"          # ⑆routing⑆ account⑇ check#
MICR_PRESET_BUSINESS = "C{c}C A{r}A {a}C"        # ⑇check#⑇ ⑆routing⑆ account⑇

DEFAULTS = {
    # --- Maker (your company) ---
    "company_name": "",
    "company_line2": "",
    "company_address": "",
    "company_citystate": "",
    "company_phone": "",
    # --- Bank ---
    "bank_name": "",
    "bank_citystate": "",
    "routing": "",            # 9-digit ABA routing/transit number
    "account": "",            # your account number
    "fraction": "",           # transit fraction, e.g. 66-1234/1210
    # --- MICR line ---
    "micr_template": MICR_PRESET_BUSINESS,
    "font_path": "",          # optional licensed E-13B .ttf; blank = vector glyphs
    # --- Numbering ---
    "next_check_number": 1001,
    # --- Printing ---
    "printer": "",              # remembered CUPS printer name (blank = system default)
    # --- Layout (inches) ---
    "check_band_height": 3.5,   # height of the check portion at page bottom
    "num_stubs": 2,             # record stubs printed above the check (0-2)
    "offset_x": 0.0,            # global registration nudge, right = +
    "offset_y": 0.0,            # global registration nudge, up = +
    "micr_baseline": 0.31,      # MICR baseline above page bottom (inches)
    "micr_align": "transit",    # MICR anchor: transit | left | center | right
    "micr_left_margin": 2.86,   # inches from left edge to the LEFT TRANSIT symbol
                                # (transit align); or to the line start (left align)
    "micr_right_margin": 0.3125,  # gap from right paper edge to end of MICR (right align)
    "draw_border": False,       # draw a border around the check (open top)
    "draw_perf_guides": False,  # draw dashed perforation guide lines
    "signature_text": "AUTHORIZED SIGNATURE",
    # --- Window-envelope format ---
    "check_format": "standard",   # standard | window (double-window envelope)
    "window_payee_dx": 0.0,       # nudge the payee address block (inches, right +)
    "window_payee_dy": 0.0,       # nudge the payee address block (inches, up +)
    "window_return_dx": 0.0,      # nudge the company return-address block
    "window_return_dy": 0.0,
}


def load():
    """Load config, filling any missing keys with defaults."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError):
        pass
    # keep only known keys but preserve default for missing ones
    return {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}


def save(cfg):
    """Persist config to disk (creates the app directory if needed)."""
    os.makedirs(APP_DIR, exist_ok=True)
    to_write = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    with open(CONFIG_PATH, "w") as f:
        json.dump(to_write, f, indent=2)


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
