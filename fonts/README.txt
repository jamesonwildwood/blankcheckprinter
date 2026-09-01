Optional E-13B MICR font
========================

CheckPrinter draws the bottom MICR line itself, as vector shapes built to the
ANSI X9 E-13B grid spec — so you do NOT need a font here to print checks.

If you would rather use a certified/licensed E-13B TrueType font (some banks or
auditors prefer a named commercial font), drop the .ttf in this folder, then in
Settings -> "E-13B font (optional)" choose that file. It will be used instead of
the built-in glyphs.

Only add a font you are licensed to use. Do NOT download random .ttf files from
the web — many "free" MICR fonts are actually proprietary. Legitimate sources
include IDAutomation and other commercial MICR font vendors.
