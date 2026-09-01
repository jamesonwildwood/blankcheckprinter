# CheckPrinter

A small macOS desktop app for printing your own business checks on **blank**
check stock. It draws the entire check — company block, payee, amount, legal
line, bank block, signature line, record stubs, and the **E-13B MICR line** at
the bottom — as a print-ready PDF you send to your printer.

Built for the "check on the bottom" stock format: one negotiable check in the
bottom ~3.5" of a Letter sheet, with up to two record stubs above it.

---

## ⚠️ Read this before you print real checks

Printing your own checks is legal, but a check only clears reliably if a few
things are right. Own these:

1. **Use MICR magnetic toner.** The bottom number line should be printed with a
   MICR toner cartridge (magnetic). Many banks now read checks optically and
   accept regular toner, but some reject or surcharge non-magnetic checks.
   **Confirm with your bank.**
2. **Match your bank's MICR spec sheet exactly.** The order, symbols, and
   spacing of the bottom line are dictated by your bank. Get their MICR
   specification sheet and set the template in Settings to match. A wrong layout
   = rejected checks.
3. **Print at Actual Size (100% / no scaling).** In the print dialog choose
   "Actual Size", never "Fit to Page", or every field shifts.
4. **Run one test check first.** Print a single check and either deposit it or
   have your bank confirm it reads before printing a batch.
5. Consider **security/VOID stock** and keep the printed-check register
   (`~/Library/Application Support/CheckPrinter/check_register.csv`) for
   reconciliation.

This tool does not give legal, banking, or accounting advice. If you're unsure
about MICR compliance or check fraud controls, ask your bank or accountant.

---

## Setup & launch

Requirements: macOS, Homebrew, Python 3 (the app installs the rest itself).

**Easiest:** in Finder, double-click **`CheckPrinter.command`**. The first launch
installs Tk and dependencies (~30 seconds), then opens the app. (If macOS blocks
it the first time: right-click → Open, or System Settings → Privacy & Security →
Open Anyway.)

**From a terminal:**

```bash
./CheckPrinter.command          # or:
python3 -m venv --system-site-packages .venv
./.venv/bin/pip install -r requirements.txt
brew install python-tk@3.14     # Tk toolkit for the GUI
./.venv/bin/python -m checkprinter
```

### Make it an app icon

To get a real double-clickable **CheckPrinter.app** with an icon:

```bash
./build_app.sh
```

This creates `CheckPrinter.app` in the project folder. Double-click it, or drag
it into the **Dock** or **Applications** (the app launches this project's local
environment, so keep the project folder where it is; re-run `./build_app.sh` if
you move it). The app is unsigned but built locally, so Gatekeeper won't block
it. First launch finishes any one-time setup automatically.

---

## First-time setup (Settings tab)

Fill in and **Save Settings**:

- **Your Company** — name, address, optional tagline/phone.
- **Bank / Account** — bank name, city/state, 9-digit routing number, account
  number, and the transit fraction (from a voided check or your bank).
- **MICR Line** — the bottom number line. Pick a preset or edit the template:
  - `{r}` routing, `{a}` account, `{c}` check number
  - `A`=Transit `B`=Amount `C`=On-Us `D`=Dash symbols; digits/spaces literal
  - **Business preset:** `C{c}C A{r}A {a}C` → `⑈check#⑈ ⑆routing⑆ account⑈`
  - **Personal preset:** `A{r}A {a}C {c}`
  - Edit it to match your bank's spec sheet exactly.
- **Layout & Registration** — next check number, check band height, number of
  stubs, and fine-registration nudges (see below).

## Writing a check (Write a Check tab)

Enter check number (auto-fills/advances), date (defaults to today), payee,
amount, and memo. The amount-in-words fills in automatically. Pick the target
in the **Printer** dropdown (↻ refreshes the list) — point it at your dedicated
check printer with MICR toner. Then:

- **Generate & Open in Preview** — opens the PDF; print from Preview at Actual
  Size, choosing the printer in the Print dialog's Printer menu. (Recommended.)
- **Print to selected printer** — sends straight to the printer chosen in the
  dropdown via `lpr` (no scaling applied).
- **Print Alignment Test** — prints a 1-inch grid + perforation guides + MICR
  clear band + a left-transit marker to the **selected printer** (same print
  path as a real check), to dial in placement on your stock.

The **Printer** selection is remembered between runs.

Each printed check is logged to the register CSV and the next check number
advances automatically.

## Aligning to your stock

Because the stock is blank, the app prints everything — there are no pre-printed
lines to line up against, only the paper edges and perforations. To register:

1. **Print Alignment Test** on a blank sheet, hold it against your check stock in
   the light.
2. If the check portion doesn't sit within your bottom perforation, adjust
   **Check height at page bottom** to match your stock's check section.
3. Use **Registration nudge X/Y** (inches) to shift everything slightly.
4. Keep the MICR line inside the bottom 5/8" clear band (the shaded band on the
   test page) and clear of other printing.

## MICR line

Drawn as vector shapes built to the ANSI X9 E-13B grid (module 0.013", 8
characters/inch), so no font install is required.

**Positioning (Settings → MICR):** the **MICR position** dropdown chooses the
anchor. `transit` (default) pins the **left Transit symbol (⑆)** to an exact
distance from the left edge — set it with **Left transit — from left (in)** —
and keeps the routing/transit fixed no matter how many digits the check number
has. **MICR height — from bottom (in)** sets the vertical position. Both are
0.01" spinboxes. The **Print Alignment Test** page marks where the left transit
lands so you can dial it to your stock. (`left`/`center`/`right` anchor the
whole line instead.) To use a licensed E-13B
TrueType font instead, drop it in `fonts/` and pick it in Settings (see
`fonts/README.txt`).

## Where your data lives

Everything stays on this Mac:

- Settings (incl. routing/account): `~/Library/Application Support/CheckPrinter/config.json`
- Printed checks (PDFs): `~/Library/Application Support/CheckPrinter/printed/`
- Register: `~/Library/Application Support/CheckPrinter/check_register.csv`

## Project layout

```
checkprinter/
  app.py           Tkinter GUI
  layout.py        check + stub PDF drawing (reportlab)
  micr.py          E-13B MICR line renderer
  e13b_glyphs.py   digitized E-13B glyph grid (self-contained)
  numwords.py      amount-to-words
  config.py        settings + paths
CheckPrinter.command   double-click launcher
```
