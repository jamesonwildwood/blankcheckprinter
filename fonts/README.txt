Optional E-13B MICR font
========================

CheckPrinter draws the bottom MICR line itself, as vector shapes built to the
ANSI X9 E-13B grid spec — so you do NOT need a font here to print checks.

If you would rather use a certified/licensed E-13B TrueType font (some banks or
auditors prefer a named commercial font), drop the .ttf in this folder, then in
Settings -> "E-13B font (optional)" choose that file. It will be used instead of
the built-in glyphs.

Only add a font you are licensed to use. Do NOT download random .ttf files from
the web — many "free" MICR fonts are actually proprietary. Look one up yourself:

  Free "MICR Encoding" (Digital Graphic Labs):
      https://www.1001fonts.com/micr-encoding-font.html
  More free E-13B options:
      https://www.1001fonts.com/micr-e-13b-fonts.html
  Commercial / certified fonts (IDAutomation):
      https://www.idautomation.com/micr-fonts/e13b/
