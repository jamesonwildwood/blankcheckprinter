"""CheckPrinter desktop app (Tkinter) - write and print checks on blank stock."""

import csv
import datetime
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import config as cfgmod
from .layout import build_alignment_pdf, build_check_pdf
from .numwords import amount_to_words

# (config key, label, kind) for the Settings form. kind: str/int/float/bool/multiline
COMPANY_FIELDS = [
    ("company_name", "Company name", "str"),
    ("company_line2", "Line 2 (tagline, optional)", "str"),
    ("company_address", "Street address", "str"),
    ("company_citystate", "City, State ZIP", "str"),
    ("company_phone", "Phone", "str"),
]
BANK_FIELDS = [
    ("bank_name", "Bank name", "str"),
    ("bank_citystate", "Bank city, state", "str"),
    ("routing", "Routing number (9 digits)", "str"),
    ("account", "Account number", "str"),
    ("fraction", "Transit fraction (e.g. 66-1234/531)", "str"),
]
LAYOUT_FIELDS = [
    ("next_check_number", "Next check number", "int"),
    ("check_band_height", "Check height at page bottom (in)", "float"),
    ("num_stubs", "Record stubs above check (0-2)", "int"),
    ("offset_x", "Nudge everything X (in, right +)", "float"),
    ("offset_y", "Nudge everything Y (in, up +; raise if bottom clips)", "float"),
    ("micr_right_margin", "MICR right margin (in, for Right position)", "float"),
    ("window_payee_dx", "Window: nudge payee block X (in)", "float"),
    ("window_payee_dy", "Window: nudge payee block Y (in)", "float"),
    ("window_return_dx", "Window: nudge return address X (in)", "float"),
    ("window_return_dy", "Window: nudge return address Y (in)", "float"),
    ("signature_text", "Signature line label", "str"),
    ("draw_border", "Draw border around check", "bool"),
    ("draw_perf_guides", "Draw dashed perforation guides", "bool"),
]

FORMAT_LABELS = {"standard": "Standard single check", "window": "Window envelope"}
FORMAT_VALUES = {v: k for k, v in FORMAT_LABELS.items()}


class CheckPrinterApp:
    def __init__(self, root):
        self.root = root
        self.cfg = cfgmod.load()
        cfgmod.ensure_dirs()
        self.vars = {}

        root.title("CheckPrinter")
        root.geometry("760x680")

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.write_tab = ttk.Frame(nb)
        self.settings_tab = ttk.Frame(nb)
        nb.add(self.write_tab, text="  Write a Check  ")
        nb.add(self.settings_tab, text="  Settings  ")

        self._build_write_tab()
        self._build_settings_tab()

    # ---------- Write a Check ----------
    def _build_write_tab(self):
        f = self.write_tab
        pad = {"padx": 8, "pady": 5}
        today = datetime.date.today().strftime("%m/%d/%Y")

        ttk.Label(f, text="Write a Check", font=("Helvetica", 15, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad)

        self.w_number = tk.StringVar(value=str(self.cfg["next_check_number"]))
        self.w_date = tk.StringVar(value=today)
        self.w_payee = tk.StringVar()
        self.w_payee_addr = tk.StringVar()
        self.w_payee_city = tk.StringVar()
        self.w_amount = tk.StringVar()
        self.w_memo = tk.StringVar()

        # Format selector
        ttk.Label(f, text="Format").grid(row=1, column=0, sticky="e", **pad)
        self.w_format = tk.StringVar(
            value=FORMAT_LABELS.get(self.cfg.get("check_format", "standard")))
        fmt_cb = ttk.Combobox(f, textvariable=self.w_format, state="readonly",
                              values=list(FORMAT_LABELS.values()), width=24)
        fmt_cb.grid(row=1, column=1, sticky="w", **pad)
        fmt_cb.bind("<<ComboboxSelected>>", lambda e: self._save_format())

        rows = [
            ("Check number", self.w_number),
            ("Date", self.w_date),
            ("Pay to the order of", self.w_payee),
            ("Payee address (window format)", self.w_payee_addr),
            ("Payee city, state ZIP (window format)", self.w_payee_city),
            ("Amount ($)", self.w_amount),
            ("Memo", self.w_memo),
        ]
        r = 2
        for label, var in rows:
            ttk.Label(f, text=label).grid(row=r, column=0, sticky="e", **pad)
            e = ttk.Entry(f, textvariable=var, width=48)
            e.grid(row=r, column=1, columnspan=2, sticky="w", **pad)
            r += 1

        # Live warning if the check number is already in the register.
        self.dup_lbl = ttk.Label(f, text="", foreground="#a00")
        self.dup_lbl.grid(row=r, column=1, columnspan=2, sticky="w", padx=8)
        r += 1
        self.w_number.trace_add("write", lambda *a: self._update_dup_warning())
        self._update_dup_warning()

        self.w_amount.trace_add("write", lambda *a: self._update_words())
        self.words_lbl = ttk.Label(f, text="", foreground="#444",
                                   font=("Helvetica", 11, "italic"))
        self.words_lbl.grid(row=r, column=1, columnspan=2, sticky="w", **pad)
        r += 1

        # Printer selector
        ttk.Label(f, text="Printer").grid(row=r, column=0, sticky="e", **pad)
        printers, default = self._list_printers()
        saved = self.cfg.get("printer", "")
        initial = saved if saved in printers else (default or (printers[0] if printers else ""))
        self.w_printer = tk.StringVar(value=initial)
        pr = ttk.Frame(f)
        pr.grid(row=r, column=1, columnspan=2, sticky="w", **pad)
        self.printer_cb = ttk.Combobox(pr, textvariable=self.w_printer,
                                       values=printers, state="readonly", width=42)
        self.printer_cb.pack(side="left")
        self.printer_cb.bind("<<ComboboxSelected>>", lambda e: self._save_printer())
        ttk.Button(pr, text="↻", width=3, command=self._refresh_printers).pack(
            side="left", padx=4)
        r += 1

        btns = ttk.Frame(f)
        btns.grid(row=r, column=0, columnspan=3, sticky="w", padx=8, pady=16)
        ttk.Button(btns, text="Generate & Open in Preview",
                   command=self.generate_and_open).pack(side="left", padx=4)
        ttk.Button(btns, text="Print to selected printer",
                   command=self.generate_and_print).pack(side="left", padx=4)
        ttk.Button(btns, text="Print Alignment Test",
                   command=self.print_alignment).pack(side="left", padx=4)
        ttk.Button(btns, text="View Check Log",
                   command=self.show_log).pack(side="left", padx=4)

        note = ("When printing, choose Actual Size / Scale 100% (never "
                "'Fit to Page') so everything lands in the right spot.\n"
                "Use MICR magnetic toner and run one test check past your bank "
                "before printing a batch.")
        ttk.Label(f, text=note, foreground="#a00", justify="left").grid(
            row=r + 1, column=0, columnspan=3, sticky="w", padx=8)

    def _update_words(self):
        try:
            amt = self._parse_amount()
            self.words_lbl.config(text=amount_to_words(amt) + " DOLLARS")
        except Exception:
            self.words_lbl.config(text="")

    def _parse_amount(self):
        raw = self.w_amount.get().replace("$", "").replace(",", "").strip()
        return float(raw)

    def _collect_check(self):
        try:
            amt = self._parse_amount()
        except ValueError:
            messagebox.showerror("Invalid amount",
                                 "Enter a dollar amount, e.g. 4287.19")
            return None
        if amt <= 0:
            messagebox.showerror("Invalid amount", "Amount must be greater than 0.")
            return None
        if not self.w_payee.get().strip():
            messagebox.showerror("Missing payee", "Enter who the check is paid to.")
            return None
        try:
            number = int(self.w_number.get())
        except ValueError:
            messagebox.showerror("Invalid number", "Check number must be a whole number.")
            return None
        return {
            "number": number,
            "date": self.w_date.get().strip(),
            "payee": self.w_payee.get().strip(),
            "payee_address": self.w_payee_addr.get().strip(),
            "payee_citystate": self.w_payee_city.get().strip(),
            "amount": amt,
            "words": amount_to_words(amt),
            "memo": self.w_memo.get().strip(),
        }

    def _render(self, check):
        cfgmod.ensure_dirs()
        fname = f"check_{check['number']}.pdf"
        path = os.path.join(cfgmod.OUTPUT_DIR, fname)
        build_check_pdf(self.cfg, check, path)
        return path

    def _log_register(self, check):
        new = not os.path.exists(cfgmod.REGISTER_PATH)
        with open(cfgmod.REGISTER_PATH, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["printed_at", "check_number", "date", "payee",
                            "amount", "memo"])
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                        check["number"], check["date"], check["payee"],
                        f"{check['amount']:.2f}", check["memo"]])

    def _advance_number(self, number):
        self.cfg["next_check_number"] = number + 1
        cfgmod.save(self.cfg)
        self.w_number.set(str(self.cfg["next_check_number"]))
        if "next_check_number" in self.vars:
            self.vars["next_check_number"].set(str(self.cfg["next_check_number"]))

    def _register_rows(self):
        """All rows from the register CSV as dicts (empty list if none)."""
        try:
            with open(cfgmod.REGISTER_PATH, newline="") as f:
                return list(csv.DictReader(f))
        except (FileNotFoundError, OSError):
            return []

    def _register_matches(self, number):
        """Register rows whose check_number equals `number`."""
        number = str(number).strip()
        if not number:
            return []
        return [r for r in self._register_rows()
                if str(r.get("check_number", "")).strip() == number]

    def _update_dup_warning(self):
        matches = self._register_matches(self.w_number.get())
        if matches:
            last = matches[-1]
            self.dup_lbl.config(
                text=f"⚠ #{self.w_number.get().strip()} already printed to "
                     f"{last.get('payee','')} on {last.get('date','')} "
                     f"(${last.get('amount','')})")
        else:
            self.dup_lbl.config(text="")

    def _dup_ok_to_proceed(self, check):
        """If the check number was already printed, confirm before reprinting."""
        matches = self._register_matches(check["number"])
        if not matches:
            return True
        last = matches[-1]
        return messagebox.askyesno(
            "Check number already used",
            f"Check #{check['number']} was already printed on "
            f"{last.get('date','')} to {last.get('payee','')} for "
            f"${last.get('amount','')}.\n\nUse this number again anyway?")

    def show_log(self):
        """Open a window listing every recorded check (newest first)."""
        rows = self._register_rows()
        win = tk.Toplevel(self.root)
        win.title("Check Log")
        win.geometry("760x440")

        top = ttk.Frame(win)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text=f"{len(rows)} check(s) recorded",
                  font=("Helvetica", 12, "bold")).pack(side="left")
        ttk.Button(top, text="Open CSV file",
                   command=lambda: subprocess.run(["open", cfgmod.REGISTER_PATH])
                   ).pack(side="right")

        cols = [("check_number", "Check #", 70), ("date", "Date", 90),
                ("payee", "Pay to", 210), ("amount", "Amount", 90),
                ("memo", "Memo", 150), ("printed_at", "Printed", 140)]
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        tree = ttk.Treeview(frame, columns=[c[0] for c in cols], show="headings")
        for key, title, width in cols:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for row in reversed(rows):
            amt = row.get("amount", "")
            try:
                amt = f"${float(amt):,.2f}"
            except (ValueError, TypeError):
                pass
            tree.insert("", "end", values=(row.get("check_number", ""),
                        row.get("date", ""), row.get("payee", ""), amt,
                        row.get("memo", ""), row.get("printed_at", "")))
        if not rows:
            ttk.Label(win, text="No checks recorded yet.",
                      foreground="#555").pack(pady=8)

    def _list_printers(self):
        """Return (printer_names, default_name) from CUPS via lpstat."""
        printers = []
        default = None
        try:
            out = subprocess.run(["lpstat", "-p"], capture_output=True,
                                 text=True).stdout
            for line in out.splitlines():
                if line.startswith("printer "):
                    printers.append(line.split()[1])
        except Exception:
            pass
        try:
            d = subprocess.run(["lpstat", "-d"], capture_output=True,
                               text=True).stdout.strip()
            if ":" in d:
                default = d.split(":", 1)[1].strip()
        except Exception:
            pass
        return printers, default

    def _refresh_printers(self):
        printers, default = self._list_printers()
        self.printer_cb["values"] = printers
        if self.w_printer.get() not in printers:
            self.w_printer.set(default or (printers[0] if printers else ""))
        self._save_printer()

    def _save_printer(self):
        """Remember the selected printer across runs."""
        self.cfg["printer"] = self.w_printer.get()
        cfgmod.save(self.cfg)

    def _save_format(self):
        """Remember the selected check format across runs."""
        self.cfg["check_format"] = FORMAT_VALUES.get(self.w_format.get(), "standard")
        cfgmod.save(self.cfg)

    def _clear_check_fields(self):
        """Clear payee, amount and memo for the next check (keep date)."""
        self.w_payee.set("")
        self.w_payee_addr.set("")
        self.w_payee_city.set("")
        self.w_amount.set("")
        self.w_memo.set("")

    def _confirm_printed(self, check):
        """Ask whether the check printed OK; only then log/advance/clear.

        No: leave the check number and all fields unchanged so it can be
        reprinted with the same number.
        """
        if messagebox.askyesno(
                "Did that print OK?",
                f"Did check #{check['number']} to "
                f"{check['payee']} for ${check['amount']:,.2f} print correctly?\n\n"
                "Yes  –  record it, advance to the next check number, and clear "
                "the check.\n"
                "No  –  keep everything as-is so you can reprint the same check."):
            self._log_register(check)
            self._advance_number(check["number"])
            self._clear_check_fields()

    def generate_and_open(self):
        check = self._collect_check()
        if not check:
            return
        if not self._dup_ok_to_proceed(check):
            return
        path = self._render(check)
        subprocess.run(["open", path])
        self._confirm_printed(check)

    def generate_and_print(self):
        check = self._collect_check()
        if not check:
            return
        if not self._dup_ok_to_proceed(check):
            return
        printer = self.w_printer.get().strip()
        self._save_printer()
        path = self._render(check)
        # -o fit-to-page is intentionally NOT used, to preserve exact placement.
        cmd = ["lpr"]
        if printer:
            cmd += ["-P", printer]
        cmd.append(path)
        subprocess.run(cmd)
        self._confirm_printed(check)

    def print_alignment(self):
        cfgmod.ensure_dirs()
        self._save_printer()
        path = os.path.join(cfgmod.OUTPUT_DIR, "alignment_test.pdf")
        build_alignment_pdf(self.cfg, path)
        printer = self.w_printer.get().strip()
        target = printer or "the default printer"
        cmd = ["lpr"]
        if printer:
            cmd += ["-P", printer]
        cmd.append(path)
        subprocess.run(cmd)
        messagebox.showinfo("Alignment test",
                            f"Alignment test sent to {target} (same print path as a "
                            "real check). Check the marks against your stock.")

    # ---------- Settings ----------
    def _build_settings_tab(self):
        # scrollable container
        canvas = tk.Canvas(self.settings_tab, highlightthickness=0)
        sb = ttk.Scrollbar(self.settings_tab, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def section(title):
            lf = ttk.LabelFrame(inner, text=title)
            lf.pack(fill="x", expand=True, padx=10, pady=6)
            return lf

        def add_fields(parent, fields):
            for i, (key, label, kind) in enumerate(fields):
                if kind == "bool":
                    var = tk.BooleanVar(value=bool(self.cfg.get(key)))
                    ttk.Checkbutton(parent, text=label, variable=var).grid(
                        row=i, column=0, columnspan=2, sticky="w", padx=8, pady=3)
                else:
                    var = tk.StringVar(value=str(self.cfg.get(key, "")))
                    ttk.Label(parent, text=label).grid(
                        row=i, column=0, sticky="e", padx=8, pady=3)
                    ttk.Entry(parent, textvariable=var, width=42).grid(
                        row=i, column=1, sticky="w", padx=8, pady=3)
                self.vars[key] = var

        add_fields(section("Your Company"), COMPANY_FIELDS)
        add_fields(section("Bank / Account"), BANK_FIELDS)

        # MICR section with presets + font chooser
        micr = section("MICR Line (bottom number line)")
        ttk.Label(micr, text="Template").grid(row=0, column=0, sticky="e", padx=8, pady=3)
        self.vars["micr_template"] = tk.StringVar(value=self.cfg["micr_template"])
        ttk.Entry(micr, textvariable=self.vars["micr_template"], width=42).grid(
            row=0, column=1, sticky="w", padx=8, pady=3)
        pf = ttk.Frame(micr)
        pf.grid(row=1, column=1, sticky="w", padx=8)
        ttk.Button(pf, text="Business preset",
                   command=lambda: self.vars["micr_template"].set(cfgmod.MICR_PRESET_BUSINESS)
                   ).pack(side="left", padx=2)
        ttk.Button(pf, text="Personal preset",
                   command=lambda: self.vars["micr_template"].set(cfgmod.MICR_PRESET_PERSONAL)
                   ).pack(side="left", padx=2)
        ttk.Label(micr, text="{r}=routing  {a}=account  {c}=check#   "
                             "A=Transit B=Amount C=On-Us D=Dash",
                  foreground="#555").grid(row=2, column=0, columnspan=2, sticky="w",
                                          padx=8, pady=2)
        ttk.Label(micr, text="Match your bank's MICR spec sheet EXACTLY.",
                  foreground="#a00").grid(row=3, column=0, columnspan=2, sticky="w",
                                          padx=8, pady=2)
        ttk.Label(micr, text="E-13B font (optional)").grid(row=4, column=0, sticky="e",
                                                           padx=8, pady=3)
        self.vars["font_path"] = tk.StringVar(value=self.cfg.get("font_path", ""))
        ttk.Entry(micr, textvariable=self.vars["font_path"], width=34).grid(
            row=4, column=1, sticky="w", padx=8, pady=3)
        ttk.Button(micr, text="Choose…", command=self._choose_font).grid(
            row=4, column=2, padx=4)

        ttk.Label(micr, text="MICR position").grid(row=5, column=0, sticky="e",
                                                   padx=8, pady=3)
        self.vars["micr_align"] = tk.StringVar(value=self.cfg.get("micr_align", "transit"))
        ttk.Combobox(micr, textvariable=self.vars["micr_align"], state="readonly",
                     values=["transit", "left", "center", "right"], width=12).grid(
            row=5, column=1, sticky="w", padx=8, pady=3)

        # Fine nudges (0.01" steps) for aligning the left transit symbol.
        ttk.Label(micr, text="Left transit — from left (in)").grid(
            row=6, column=0, sticky="e", padx=8, pady=3)
        self.vars["micr_left_margin"] = tk.StringVar(
            value=f"{float(self.cfg.get('micr_left_margin', 3.0)):.2f}")
        ttk.Spinbox(micr, textvariable=self.vars["micr_left_margin"], from_=-2.0,
                    to=8.0, increment=0.01, format="%.2f", width=10).grid(
            row=6, column=1, sticky="w", padx=8, pady=3)

        ttk.Label(micr, text="MICR height — from bottom (in)").grid(
            row=7, column=0, sticky="e", padx=8, pady=3)
        self.vars["micr_baseline"] = tk.StringVar(
            value=f"{float(self.cfg.get('micr_baseline', 0.4375)):.2f}")
        ttk.Spinbox(micr, textvariable=self.vars["micr_baseline"], from_=0.0,
                    to=0.50, increment=0.01, format="%.2f", width=10).grid(
            row=7, column=1, sticky="w", padx=8, pady=3)
        ttk.Label(micr, text="'transit' anchors the left ⑆ symbol to the value "
                             "above. Use the alignment test to measure.",
                  foreground="#555").grid(row=8, column=0, columnspan=2, sticky="w",
                                          padx=8, pady=2)

        add_fields(section("Layout & Registration"), LAYOUT_FIELDS)

        save = ttk.Frame(inner)
        save.pack(fill="x", pady=12)
        ttk.Button(save, text="Save Settings", command=self.save_settings).pack(
            side="left", padx=12)
        ttk.Label(save, text=f"Stored in {cfgmod.CONFIG_PATH}",
                  foreground="#555").pack(side="left")

    def _choose_font(self):
        p = filedialog.askopenfilename(title="Choose an E-13B TrueType font",
                                       filetypes=[("TrueType font", "*.ttf")])
        if p:
            self.vars["font_path"].set(p)

    def save_settings(self):
        allfields = COMPANY_FIELDS + BANK_FIELDS + LAYOUT_FIELDS
        kinds = {k: kind for k, _, kind in allfields}
        kinds["micr_template"] = "str"
        kinds["font_path"] = "str"
        kinds["micr_align"] = "str"
        kinds["micr_left_margin"] = "float"
        kinds["micr_baseline"] = "float"
        for key, var in self.vars.items():
            kind = kinds.get(key, "str")
            val = var.get()
            try:
                if kind == "int":
                    self.cfg[key] = int(val)
                elif kind == "float":
                    self.cfg[key] = float(val)
                elif kind == "bool":
                    self.cfg[key] = bool(val)
                else:
                    self.cfg[key] = val
            except ValueError:
                messagebox.showerror("Invalid value",
                                     f"'{val}' is not valid for {key}.")
                return
        cfgmod.save(self.cfg)
        self.w_number.set(str(self.cfg["next_check_number"]))
        messagebox.showinfo("Saved", "Settings saved.")


def main():
    root = tk.Tk()
    CheckPrinterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
