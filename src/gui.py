"""Black-theme Tkinter interface for the B-Tree Network Log Investigation Engine.

Layout
------
* Sidebar   - navigation between pages, data loading, tools.
* Pages     - Log Explorer, Security Insights, B-Tree View, Benchmark.
* Dialogs   - custom dark dialogs (no light-grey native pop-ups).

Backend API used is unchanged (LogInvestigationSystem, LogRecord, BTreeNode).
"""
from __future__ import annotations

import csv
import sys
import time
import tkinter as tk
from collections import Counter
from pathlib import Path
from tkinter import filedialog, ttk
from tkinter import font as tkfont

from .btree import BTreeNode
from .log_generator import generate_synthetic_logs
from .log_system import LogInvestigationSystem
from .models import LogRecord

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_LOGS = DATA_DIR / "sample_logs.csv"                 # 15 hand-written records
LARGE_SAMPLE_LOGS = DATA_DIR / "sample_logs_10000.csv"     # 10,000 deterministic records
DUPLICATE_TEST_LOGS = DATA_DIR / "test_logs_with_duplicates.csv"

# ----------------------------------------------------------------- palette
BG = "#07070a"
SIDEBAR = "#0b0b0f"
PANEL = "#101015"
PANEL_ALT = "#17171e"
PANEL_HOVER = "#21212b"
INPUT_BG = "#0a0a0e"
BORDER = "#1f1f29"
TEXT = "#ececf1"
MUTED = "#8b8b99"
DIM = "#5a5a68"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#60a5fa"
ACCENT_PRESSED = "#2563eb"
ACCENT_TINT = "#0f1d33"
ACCENT_TINT_HOVER = "#16294a"
SELECT_BG = "#1e3a8a"
DANGER_TINT = "#2a1218"
DANGER_HOVER = "#3b1520"
GREEN = "#34d399"
RED = "#fb7185"
AMBER = "#fbbf24"
ORANGE = "#fb923c"
CYAN = "#22d3ee"
VIOLET = "#a78bfa"

ROW_ODD = "#0b0b0f"
ROW_EVEN = "#111116"

SEVERITY_COLORS = {"INFO": GREEN, "MEDIUM": AMBER, "HIGH": ORANGE, "ERROR": RED}
SEVERITY_ORDER = ("ERROR", "HIGH", "MEDIUM", "INFO")
ALL_SEVERITIES = "All severities"

# (fill, outline) per B-Tree depth in the visualization.
DEPTH_COLORS = [
    ("#1c1433", "#a78bfa"),
    ("#0f1f3d", "#60a5fa"),
    ("#082a33", "#22d3ee"),
    ("#082b21", "#34d399"),
    ("#2b2106", "#fbbf24"),
]

# Font families are resolved once a Tk root exists.
_UI = "TkDefaultFont"
_MONO = "TkFixedFont"


# Time complexity: O(1): return a fixed-size font tuple.
def ui(size: int = 10, weight: str = "normal") -> tuple:
    return (_UI, size, weight)


# Time complexity: O(1): return a fixed-size font tuple.
def mono(size: int = 10, weight: str = "normal") -> tuple:
    return (_MONO, size, weight)


# Time complexity: O(F + C): collect installed fonts and check C candidate families.
def _pick_font(root: tk.Misc, candidates: tuple[str, ...], fallback: str) -> str:
    """Return the first installed font family from candidates."""
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return name
    return fallback


# ----------------------------------------------------------- small widgets
class FlatButton(tk.Label):
    """Flat label-based button with hover / pressed states (looks identical on every OS)."""

    VARIANTS = {
        #            bg          fg          hover              pressed
        "default": (PANEL_ALT, TEXT, PANEL_HOVER, ACCENT),
        "accent": (ACCENT, "#ffffff", ACCENT_HOVER, ACCENT_PRESSED),
        "subtle": (ACCENT_TINT, "#93c5fd", ACCENT_TINT_HOVER, ACCENT),
        "danger": (DANGER_TINT, RED, DANGER_HOVER, "#be123c"),
        "side": (SIDEBAR, "#c8c8d2", PANEL_ALT, ACCENT_TINT),
    }

    # Time complexity: O(1): configure one widget and bind a fixed set of events.
    def __init__(self, parent, text, command=None, variant="default", anchor="center",
                 padx=14, pady=7, font=None, **kwargs):
        bg, fg, hover, pressed = self.VARIANTS[variant]
        bold = "bold" if variant in ("accent", "subtle", "danger") else "normal"
        super().__init__(parent, text=text, bg=bg, fg=fg, padx=padx, pady=pady, anchor=anchor,
                         cursor="hand2", font=font or ui(10, bold), **kwargs)
        self.command = command
        self._bg, self._hover, self._pressed = bg, hover, pressed
        self.bind("<Enter>", lambda _e: self.configure(bg=self._hover))
        self.bind("<Leave>", lambda _e: self.configure(bg=self._bg))
        self.bind("<ButtonPress-1>", lambda _e: self.configure(bg=self._pressed))
        self.bind("<ButtonRelease-1>", self._release)

    # Time complexity: O(1): update one widget state and invoke its callback.
    def _release(self, event: tk.Event) -> None:
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        self.configure(bg=self._hover if inside else self._bg)
        if inside and self.command:
            self.command()


class NavItem(tk.Frame):
    """Sidebar navigation entry with an active indicator bar."""

    # Time complexity: O(1): construct one navigation item and its fixed widgets.
    def __init__(self, parent, icon: str, text: str, command):
        super().__init__(parent, bg=SIDEBAR, cursor="hand2")
        self.command = command
        self.active = False
        self.bar = tk.Frame(self, bg=SIDEBAR, width=3)
        self.bar.pack(side="left", fill="y")
        self.label = tk.Label(self, text=f"{icon}   {text}", bg=SIDEBAR, fg="#c8c8d2",
                              font=ui(10, "bold"), anchor="w", padx=16, pady=10, cursor="hand2")
        self.label.pack(side="left", fill="x", expand=True)
        for widget in (self, self.label):
            widget.bind("<Enter>", lambda _e: self._paint(hover=True))
            widget.bind("<Leave>", lambda _e: self._paint())
            widget.bind("<Button-1>", lambda _e: self.command())

    # Time complexity: O(1): update the colors of one navigation item.
    def _paint(self, hover: bool = False) -> None:
        if self.active:
            bg, fg = ACCENT_TINT, "#ffffff"
        elif hover:
            bg, fg = PANEL_ALT, "#ffffff"
        else:
            bg, fg = SIDEBAR, "#c8c8d2"
        self.configure(bg=bg)
        self.label.configure(bg=bg, fg=fg)

    # Time complexity: O(1): update one navigation item's state.
    def set_active(self, active: bool) -> None:
        self.active = active
        self.bar.configure(bg=ACCENT if active else SIDEBAR)
        self._paint()


# Time complexity: O(1): create one frame widget.
def make_card(parent: tk.Misc) -> tk.Frame:
    return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)


# Time complexity: O(1): create one entry widget.
def make_entry(parent: tk.Misc, variable: tk.StringVar | None = None) -> tk.Entry:
    return tk.Entry(parent, textvariable=variable, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                    relief="flat", highlightthickness=1, highlightbackground=BORDER,
                    highlightcolor=ACCENT, selectbackground=ACCENT, selectforeground="#ffffff",
                    font=ui(11))


# Time complexity: O(1): create a fixed group of widgets for one statistic.
def stat_card(parent: tk.Misc, title: str, value, column: int, color: str, columns: int = 4) -> None:
    """Metric tile: coloured strip, small caps title, large value (str or tk variable)."""
    outer = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    outer.grid(row=0, column=column, sticky="ew",
               padx=(0 if column == 0 else 6, 0 if column == columns - 1 else 6))
    tk.Frame(outer, bg=color, width=3).pack(side="left", fill="y")
    card = tk.Frame(outer, bg=PANEL)
    card.pack(side="left", fill="both", expand=True, padx=16, pady=12)
    tk.Label(card, text=title, bg=PANEL, fg=MUTED, font=ui(8, "bold"), anchor="w").pack(anchor="w")
    options = {"textvariable": value} if isinstance(value, tk.Variable) else {"text": value}
    tk.Label(card, bg=PANEL, fg=color, font=ui(22, "bold"), anchor="w", **options).pack(
        anchor="w", pady=(4, 0)
    )


# --------------------------------------------------------------- dialogs
class DarkDialog(tk.Toplevel):
    """Modal dark dialog: title, optional subtitle, body frame and right-aligned footer buttons."""

    # Time complexity: O(1): create the fixed dialog layout.
    def __init__(self, parent: tk.Misc, title: str, subtitle: str = "", width: int = 440):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.dialog_width = width
        self.result = None
        self.initial_focus: tk.Misc | None = None
        self.title(title)
        self.configure(bg=BORDER)
        self.resizable(False, False)
        self.transient(parent)

        shell = tk.Frame(self, bg=PANEL)
        shell.pack(fill="both", expand=True, padx=1, pady=1)
        head = tk.Frame(shell, bg=PANEL)
        head.pack(fill="x", padx=24, pady=(22, 0))
        tk.Label(head, text=title, bg=PANEL, fg="#ffffff", font=ui(15, "bold"), anchor="w").pack(fill="x")
        if subtitle:
            tk.Label(head, text=subtitle, bg=PANEL, fg=MUTED, font=ui(10), anchor="w",
                     justify="left", wraplength=width - 50).pack(fill="x", pady=(4, 0))
        self.body = tk.Frame(shell, bg=PANEL)
        self.body.pack(fill="both", expand=True, padx=24, pady=(16, 0))
        tk.Frame(shell, bg=BORDER, height=1).pack(fill="x", pady=(14, 0))
        self.footer = tk.Frame(shell, bg=SIDEBAR)
        self.footer.pack(fill="x")
        self.footer_inner = tk.Frame(self.footer, bg=SIDEBAR)
        self.footer_inner.pack(fill="x", padx=24, pady=14)

        self.bind("<Escape>", lambda _e: self.cancel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    # Time complexity: O(1): create and register one button.
    def add_button(self, text: str, command, variant: str = "default") -> FlatButton:
        button = FlatButton(self.footer_inner, text, command, variant, padx=18, pady=8)
        button.pack(side="right", padx=(8, 0))
        return button

    # Time complexity: O(1): close the dialog and set its result.
    def cancel(self) -> None:
        self.result = None
        self.destroy()

    # Time complexity: O(1) setup time, excluding the user wait in the modal event loop.
    def show(self):
        self.update_idletasks()
        width = max(self.dialog_width, self.winfo_reqwidth())
        height = self.winfo_reqheight()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - width) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - height) // 3
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.lift()
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        if self.initial_focus is not None:
            self.initial_focus.focus_set()
            if isinstance(self.initial_focus, tk.Entry):
                self.initial_focus.selection_range(0, "end")
        else:
            self.focus_set()
        self.wait_window(self)
        return self.result


class MessageDialog(DarkDialog):
    """Info / success / warning / error message, or a confirmation with two buttons."""

    KINDS = {
        "info": ("i", ACCENT_HOVER, ACCENT_TINT),
        "success": ("✓", GREEN, "#0a2a20"),
        "warning": ("!", AMBER, "#2b2106"),
        "error": ("✕", RED, DANGER_TINT),
    }

    # Time complexity: O(1) relative to log count: create a fixed dialog layout.
    def __init__(self, parent, title, message, kind="info", confirm_text: str | None = None,
                 danger: bool = False, monospace: bool = False):
        super().__init__(parent, title, width=480)
        icon, color, tint = self.KINDS[kind]
        row = tk.Frame(self.body, bg=PANEL)
        row.pack(fill="x")
        tk.Label(row, text=icon, bg=tint, fg=color, font=ui(14, "bold"), width=3, pady=6).pack(
            side="left", anchor="n", padx=(0, 16)
        )
        tk.Label(row, text=message, bg=PANEL, fg=TEXT, font=mono(10) if monospace else ui(10),
                 anchor="w", justify="left", wraplength=380).pack(side="left", fill="x", expand=True)
        self.bind("<Return>", lambda _e: self._accept())
        if confirm_text:
            self.add_button(confirm_text, self._accept, "danger" if danger else "accent")
            self.add_button("Cancel", self.cancel)
        else:
            self.add_button("OK", self._accept, "accent")

    # Time complexity: O(1): set the confirmation result and close the dialog.
    def _accept(self) -> None:
        self.result = True
        self.destroy()


class FormDialog(DarkDialog):
    """Single dialog that collects several fields at once, with inline validation."""

    # Time complexity: O(f): create one set of widgets for each of f form fields.
    def __init__(self, parent, title, fields, subtitle="", submit_text="Apply", validate=None,
                 danger=False):
        super().__init__(parent, title, subtitle, width=470)
        self.vars: dict[str, tk.StringVar] = {}
        self.validate = validate
        for field in fields:
            row = tk.Frame(self.body, bg=PANEL)
            row.pack(fill="x", pady=(0, 10))
            tk.Label(row, text=field["label"].upper(), bg=PANEL, fg=MUTED, font=ui(8, "bold"),
                     anchor="w").pack(fill="x", pady=(0, 4))
            var = tk.StringVar(value=str(field.get("initial", "")))
            if field.get("choices"):
                widget = ttk.Combobox(row, textvariable=var, values=field["choices"],
                                      state="readonly", style="Dark.TCombobox", font=ui(11))
            else:
                widget = make_entry(row, var)
            widget.pack(fill="x", ipady=5)
            if field.get("hint"):
                tk.Label(row, text=field["hint"], bg=PANEL, fg=DIM, font=ui(8), anchor="w").pack(
                    fill="x", pady=(3, 0)
                )
            self.vars[field["key"]] = var
            if self.initial_focus is None:
                self.initial_focus = widget
        self.error_var = tk.StringVar()
        tk.Label(self.body, textvariable=self.error_var, bg=PANEL, fg=RED, font=ui(9), anchor="w",
                 justify="left", wraplength=410).pack(fill="x")
        self.add_button(submit_text, self._submit, "danger" if danger else "accent")
        self.add_button("Cancel", self.cancel)
        self.bind("<Return>", lambda _e: self._submit())

    # Time complexity: O(f): read and validate the form fields.
    def _submit(self) -> None:
        values = {key: var.get().strip() for key, var in self.vars.items()}
        if self.validate:
            error = self.validate(values)
            if error:
                self.error_var.set(error)
                return
        self.result = values
        self.destroy()


# ------------------------------------------------------------ application
class LogInvestigationApp(tk.Tk):
    """Desktop application for loading, indexing, querying and testing log data."""

    PAGES = (
        ("logs", "☰", "Log Explorer", "Search, filter and inspect every indexed event"),
        ("insights", "◐", "Security Insights", "Severity mix, busiest sources and repeated failed logins"),
        ("btree", "❖", "B-Tree View", "Drag to pan  •  scroll wheel to move  •  Shift+scroll for sideways"),
        ("benchmark", "↯", "Benchmark", "Indexed B-Tree lookup versus a linear scan"),
    )

    # Time complexity: O(N log N): initialize the UI and load/index N records when the bundled dataset exists.
    def __init__(self) -> None:
        super().__init__()
        global _UI, _MONO
        self.title("B-Tree Network Log Investigation Engine")
        self.geometry("1440x880")
        self.minsize(1280, 760)
        self.configure(bg=BG)
        _UI = _pick_font(
            self, ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "DejaVu Sans"), "TkDefaultFont"
        )
        _MONO = _pick_font(self, ("Cascadia Code", "Consolas", "Menlo", "DejaVu Sans Mono"), "TkFixedFont")
        self._configure_theme()

        self.system = LogInvestigationSystem(min_degree=3)
        self.current_records: list[LogRecord] = []
        self.page_key = ""
        self.pages: dict[str, tk.Frame] = {}
        self.nav_items: dict[str, NavItem] = {}
        self._tree_dirty = True

        self._build_sidebar()
        self._build_main()
        self._bind_shortcuts()
        self.show_page("logs")

        # Open directly with 10,000 records so the main demo is ready to use.
        if LARGE_SAMPLE_LOGS.exists():
            self._load_file(LARGE_SAMPLE_LOGS, show_dialog=False)
        elif SAMPLE_LOGS.exists():
            self._load_file(SAMPLE_LOGS, show_dialog=False)

    # ------------------------------------------------------------------ theme
    # Time complexity: O(1) relative to log count: configure a fixed set of widget styles.
    def _configure_theme(self) -> None:
        f = _UI
        self.option_add("*Background", BG)
        self.option_add("*Foreground", TEXT)
        self.option_add("*Font", (f, 10))
        self.option_add("*selectBackground", ACCENT)
        self.option_add("*selectForeground", "#ffffff")
        # Drop-down list of ttk.Combobox is a classic Tk listbox.
        self.option_add("*TCombobox*Listbox.background", PANEL_ALT)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.option_add("*TCombobox*Listbox.font", (f, 10))
        self.option_add("*TCombobox*Listbox.borderWidth", 0)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=TEXT, font=(f, 10), focuscolor=BG,
                        bordercolor=BORDER, lightcolor=BG, darkcolor=BG)

        # Combobox
        style.configure("Dark.TCombobox", fieldbackground=INPUT_BG, background=PANEL_ALT,
                        foreground=TEXT, arrowcolor=MUTED, bordercolor=BORDER, lightcolor=BORDER,
                        darkcolor=BORDER, insertcolor=TEXT, padding=(8, 7), arrowsize=14,
                        selectbackground=INPUT_BG, selectforeground=TEXT)
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", INPUT_BG)], foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", INPUT_BG)], selectforeground=[("readonly", TEXT)],
                  background=[("active", PANEL_HOVER)], arrowcolor=[("active", TEXT)],
                  bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)],
                  darkcolor=[("focus", ACCENT)])

        # Table
        style.configure("Treeview", background=ROW_ODD, fieldbackground=ROW_ODD, foreground=TEXT,
                        rowheight=32, borderwidth=0, relief="flat", font=(f, 10))
        style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", "#ffffff")])
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground="#f5f5f5",
                        font=(f, 9, "bold"), padding=(12, 10), relief="flat", borderwidth=0)
        style.map("Treeview.Heading", background=[("active", PANEL_HOVER)])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        # Work around the Tk 8.6.9 bug where tag colours are ignored in Treeview.
        # Time complexity: O(S): filter S style-map entries for one option.
        def fixed_map(option: str):
            return [entry for entry in style.map("Treeview", query_opt=option)
                    if entry[:2] != ("!disabled", "!selected")]

        style.map("Treeview", foreground=fixed_map("foreground"), background=fixed_map("background"))

        # Slim, arrow-less scrollbars.
        for orient, sticky in (("Vertical", "ns"), ("Horizontal", "ew")):
            name = f"Dark.{orient}.TScrollbar"
            style.layout(name, [(f"{orient}.Scrollbar.trough", {"sticky": sticky, "children": [
                (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
            style.configure(name, background=PANEL_HOVER, troughcolor=BG, bordercolor=BG,
                            lightcolor=PANEL_HOVER, darkcolor=PANEL_HOVER, gripcount=0, width=10,
                            relief="flat")
            style.map(name, background=[("pressed", ACCENT), ("active", "#33333f")],
                      lightcolor=[("pressed", ACCENT), ("active", "#33333f")],
                      darkcolor=[("pressed", ACCENT), ("active", "#33333f")])

    # ---------------------------------------------------------------- sidebar
    # Time complexity: O(W): create W fixed sidebar widgets.
    def _build_sidebar(self) -> None:
        side = tk.Frame(self, bg=SIDEBAR, width=250)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(self, bg=BORDER, width=1).pack(side="left", fill="y")

        # Footer first so it keeps its place at the bottom.
        tk.Label(side, bg=SIDEBAR, fg=DIM, font=ui(8), justify="left", anchor="w",
                 text="Ctrl+F  search       F5  show all\nCtrl+O  import     Ctrl+N  add log\n"
                      "Ctrl+1…4  switch page").pack(side="bottom", anchor="w", padx=20, pady=(8, 18))

        brand = tk.Frame(side, bg=SIDEBAR)
        brand.pack(fill="x", padx=18, pady=(26, 14))
        tk.Label(brand, text="B", bg=ACCENT, fg="#ffffff", font=ui(16, "bold"), width=2, pady=3).pack(
            side="left"
        )
        names = tk.Frame(brand, bg=SIDEBAR)
        names.pack(side="left", padx=(12, 0))
        tk.Label(names, text="LOG ENGINE", bg=SIDEBAR, fg="#ffffff", font=ui(13, "bold")).pack(anchor="w")
        tk.Label(names, text="B-Tree Investigator", bg=SIDEBAR, fg=MUTED, font=ui(9)).pack(anchor="w")

        self._section(side, "WORKSPACE")
        for key, icon, label, _subtitle in self.PAGES:
            item = NavItem(side, icon, label, lambda k=key: self.show_page(k))
            item.pack(fill="x", padx=(0, 12), pady=1)
            self.nav_items[key] = item

        self._section(side, "DATA")
        self._side_button(side, "Load 10,000 logs", self.load_10000, accent=True)
        self._side_button(side, "Load 15-log sample", self.load_sample)
        self._side_button(side, "Test duplicate file", self.load_duplicate_test)
        self._side_button(side, "Import CSV…", self.import_csv)
        self._side_button(side, "Generate dataset…", self.generate_dataset)

        self._section(side, "TOOLS")
        self._side_button(side, "Check indexes", self.check_indexes)
        self._side_button(side, "Export results…", self.export_results)

    # Time complexity: O(1): create one section label.
    @staticmethod
    def _section(parent: tk.Misc, title: str) -> None:
        tk.Label(parent, text=title, bg=SIDEBAR, fg=DIM, font=ui(8, "bold"), anchor="w").pack(
            fill="x", padx=22, pady=(20, 6)
        )

    # Time complexity: O(1): create one sidebar button.
    @staticmethod
    def _side_button(parent: tk.Misc, text: str, command, accent: bool = False) -> None:
        FlatButton(parent, text, command, "subtle" if accent else "side", anchor="w",
                   padx=16, pady=7).pack(fill="x", padx=(10, 12), pady=1)

    # ------------------------------------------------------------------- main
    # Time complexity: O(W): create W fixed main-page widgets.
    def _build_main(self) -> None:
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        # Status bar (packed first so it stays at the bottom).
        status_bar = tk.Frame(main, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        status_bar.pack(side="bottom", fill="x", padx=28, pady=(12, 20))
        self.status_dot = tk.Label(status_bar, text="●", bg=PANEL, fg=GREEN, font=ui(11))
        self.status_dot.pack(side="left", padx=(14, 8), pady=9)
        self.status_var = tk.StringVar(value="Ready — loading the 10,000-record demonstration dataset.")
        tk.Label(status_bar, textvariable=self.status_var, bg=PANEL, fg=TEXT, font=ui(10),
                 anchor="w").pack(side="left", fill="x", expand=True)

        header = tk.Frame(main, bg=BG)
        header.pack(fill="x", padx=28, pady=(26, 16))
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left")
        self.title_var = tk.StringVar()
        self.subtitle_var = tk.StringVar()
        tk.Label(titles, textvariable=self.title_var, bg=BG, fg="#ffffff", font=ui(22, "bold"),
                 anchor="w").pack(anchor="w")
        tk.Label(titles, textvariable=self.subtitle_var, bg=BG, fg=MUTED, font=ui(10),
                 anchor="w").pack(anchor="w", pady=(3, 0))
        self.degree_var = tk.StringVar(value="")
        tk.Label(header, textvariable=self.degree_var, bg=PANEL_ALT, fg=ACCENT_HOVER,
                 font=ui(9, "bold"), padx=14, pady=7).pack(side="right", anchor="n")

        self.page_host = tk.Frame(main, bg=BG)
        self.page_host.pack(fill="both", expand=True, padx=28)
        self.pages["logs"] = self._build_logs_page(self.page_host)
        self.pages["insights"] = self._build_insights_page(self.page_host)
        self.pages["btree"] = self._build_btree_page(self.page_host)
        self.pages["benchmark"] = self._build_benchmark_page(self.page_host)

    # Time complexity: O(N + u log u) for insights, O(N) for a tree redraw, otherwise O(1).
    def show_page(self, key: str) -> None:
        for page in self.pages.values():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self.page_key = key
        for name, item in self.nav_items.items():
            item.set_active(name == key)
        for page_key, _icon, title, subtitle in self.PAGES:
            if page_key == key:
                self.title_var.set(title)
                self.subtitle_var.set(subtitle)
        if key == "insights":
            self._refresh_insights()
        elif key == "btree" and self._tree_dirty:
            self.update_idletasks()
            self._draw_tree()

    # Time complexity: O(1): update status widgets.
    def set_status(self, message: str, level: str = "ok") -> None:
        self.status_var.set(message)
        self.status_dot.configure(fg={"ok": GREEN, "warn": AMBER, "error": RED}.get(level, GREEN))

    # --------------------------------------------------------- dialog helpers
    # Time complexity: O(1) relative to record count: create and show a fixed message dialog.
    def notify(self, title: str, message: str, kind: str = "info", monospace: bool = False) -> None:
        MessageDialog(self, title, message, kind, monospace=monospace).show()

    # Time complexity: O(1) setup time, excluding the time waiting for user confirmation.
    def confirm(self, title: str, message: str, confirm_text: str = "Delete", danger: bool = True) -> bool:
        return bool(MessageDialog(self, title, message, "warning", confirm_text=confirm_text,
                                  danger=danger).show())

    # Time complexity: O(f): display a form containing f fields.
    def ask_form(self, title, fields, validate=None, submit_text="Apply", subtitle="", danger=False):
        return FormDialog(self, title, fields, subtitle, submit_text, validate, danger).show()

    # --------------------------------------------------------------- logs page
    # Time complexity: O(W): create W fixed widgets for the log-explorer page.
    def _build_logs_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=BG)

        self.total_var = tk.StringVar(value="0")
        self.visible_var = tk.StringVar(value="0")
        self.height_var = tk.StringVar(value="0")
        self.nodes_var = tk.StringVar(value="0")
        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="x", pady=(0, 14))
        stat_card(cards, "LOG RECORDS", self.total_var, 0, ACCENT_HOVER)
        stat_card(cards, "VISIBLE RESULTS", self.visible_var, 1, CYAN)
        stat_card(cards, "B-TREE HEIGHT", self.height_var, 2, VIOLET)
        stat_card(cards, "B-TREE NODES", self.nodes_var, 3, GREEN)
        for col in range(4):
            cards.columnconfigure(col, weight=1, uniform="stat")

        # Search bar: text / IP / ID plus severity filter.
        bar = make_card(page)
        bar.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(bar, bg=PANEL)
        inner.pack(fill="x", padx=14, pady=(12, 4))
        self.search_var = tk.StringVar()
        self.severity_var = tk.StringVar(value=ALL_SEVERITIES)
        box = tk.Frame(inner, bg=INPUT_BG, highlightbackground=BORDER, highlightthickness=1)
        box.pack(side="left", fill="x", expand=True)
        tk.Label(box, text="⌕", bg=INPUT_BG, fg=MUTED, font=ui(13)).pack(side="left", padx=(12, 4))
        self.search_entry = tk.Entry(box, textvariable=self.search_var, bg=INPUT_BG, fg=TEXT,
                                     insertbackground=TEXT, relief="flat", highlightthickness=0,
                                     selectbackground=ACCENT, selectforeground="#ffffff", font=ui(11))
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        self.search_entry.bind("<FocusIn>", lambda _e: box.configure(highlightbackground=ACCENT))
        self.search_entry.bind("<FocusOut>", lambda _e: box.configure(highlightbackground=BORDER))
        self.search_entry.bind("<Return>", lambda _e: self.quick_search())
        severity_box = ttk.Combobox(inner, textvariable=self.severity_var, state="readonly", width=15,
                                    values=[ALL_SEVERITIES, *SEVERITY_ORDER], style="Dark.TCombobox",
                                    font=ui(10))
        severity_box.pack(side="left", padx=(10, 0), ipady=3)
        severity_box.bind("<<ComboboxSelected>>", lambda _e: self.quick_search())
        FlatButton(inner, "Search", self.quick_search, "accent", pady=9).pack(side="left", padx=(10, 0))
        FlatButton(inner, "Clear", self.clear_search, "default", pady=9).pack(side="left", padx=(8, 0))
        tk.Label(bar, text="Matches event text, source IP, severity or event ID   •   Enter to search   •   "
                           "Ctrl+F to focus", bg=PANEL, fg=DIM, font=ui(8), anchor="w").pack(
            fill="x", padx=16, pady=(0, 10)
        )

        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)

        # Detail panel (right).
        details = make_card(body)
        details.pack(side="right", fill="y", padx=(14, 0))
        details.configure(width=310)
        details.pack_propagate(False)
        self._build_detail_panel(details)

        # Table card (left).
        table_card = make_card(body)
        table_card.pack(side="left", fill="both", expand=True)
        tools = tk.Frame(table_card, bg=PANEL)
        tools.pack(fill="x", padx=14, pady=10)
        tk.Label(tools, text="Events", bg=PANEL, fg="#ffffff", font=ui(12, "bold")).pack(side="left")
        self.badge_var = tk.StringVar(value="0 shown")
        tk.Label(tools, textvariable=self.badge_var, bg=PANEL_ALT, fg=ACCENT_HOVER, font=ui(8, "bold"),
                 padx=10, pady=3).pack(side="left", padx=(10, 0))
        FlatButton(tools, "Delete ID", self.delete_log, "danger", padx=10, pady=6).pack(side="right")
        FlatButton(tools, "Time range", self.search_time_range, padx=10, pady=6).pack(
            side="right", padx=(0, 6)
        )
        FlatButton(tools, "Find ID", self.search_id, padx=10, pady=6).pack(side="right", padx=(0, 6))
        FlatButton(tools, "+ Add log", self.add_log, "subtle", padx=10, pady=6).pack(
            side="right", padx=(0, 6)
        )
        tk.Frame(table_card, bg=BORDER, height=1).pack(fill="x")

        table_frame = tk.Frame(table_card, bg=PANEL)
        table_frame.pack(fill="both", expand=True)
        columns = ("event_id", "timestamp", "source_ip", "severity", "event")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "event_id": ("Event ID", 90),
            "timestamp": ("Timestamp", 170),
            "source_ip": ("Source IP", 130),
            "severity": ("Severity", 105),
            "event": ("Event Description", 420),
        }
        for key, (heading, width) in headings.items():
            self.table.heading(key, text=heading, anchor="w")
            self.table.column(key, width=width, anchor="w", stretch=(key == "event"))
        self.table.tag_configure("odd", background=ROW_ODD)
        self.table.tag_configure("even", background=ROW_EVEN)
        for severity, color in SEVERITY_COLORS.items():
            self.table.tag_configure(severity, foreground=color)

        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview,
                                 style="Dark.Vertical.TScrollbar")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview,
                                   style="Dark.Horizontal.TScrollbar")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.empty_label = tk.Label(self.table, text="No matching records", bg=ROW_ODD, fg=DIM,
                                    font=ui(12))

        self.row_menu = tk.Menu(self, tearoff=0, bg=PANEL_ALT, fg=TEXT, activebackground=ACCENT,
                                activeforeground="#ffffff", bd=0, relief="flat", font=ui(10))
        self.row_menu.add_command(label="Copy row", command=self._copy_selected)
        self.row_menu.add_command(label="Show only this source IP", command=self._filter_selected_ip)
        self.row_menu.add_separator()
        self.row_menu.add_command(label="Delete this event", command=self._delete_selected)
        self.table.bind("<Button-3>", self._show_context_menu)
        self.table.bind("<Button-2>", self._show_context_menu)
        self.table.bind("<Delete>", lambda _e: self._delete_selected())
        self.table.bind("<<TreeviewSelect>>", lambda _e: self._render_details(self._selected_record()))
        return page

    # Time complexity: O(W): create a fixed detail-panel widget layout.
    def _build_detail_panel(self, details: tk.Frame) -> None:
        tk.Label(details, text="EVENT DETAILS", bg=PANEL, fg=MUTED, font=ui(8, "bold"), anchor="w").pack(
            fill="x", padx=18, pady=(18, 0)
        )
        self.detail_empty = tk.Label(
            details, bg=PANEL, fg=DIM, font=ui(10), justify="center",
            text="Select an event in the table\nto inspect it here.\n\nRight-click a row for\nquick actions.",
        )
        self.detail_empty.pack(expand=True)

        self.detail_body = tk.Frame(details, bg=PANEL)
        self.d_id = tk.Label(self.detail_body, bg=PANEL, fg="#ffffff", font=ui(26, "bold"), anchor="w")
        self.d_id.pack(fill="x", pady=(10, 0))
        self.d_sev = tk.Label(self.detail_body, bg=PANEL, font=ui(10, "bold"), anchor="w")
        self.d_sev.pack(fill="x", pady=(2, 0))
        self._detail_values: list[tk.Label] = []

        # Time complexity: O(1): create one detail field widget.
        def field(title: str, font) -> tk.Label:
            tk.Label(self.detail_body, text=title, bg=PANEL, fg=MUTED, font=ui(8, "bold"),
                     anchor="w").pack(fill="x", pady=(16, 3))
            value = tk.Label(self.detail_body, bg=PANEL, fg=TEXT, font=font, anchor="w",
                             justify="left", wraplength=250)
            value.pack(fill="x")
            self._detail_values.append(value)
            return value

        self.d_time = field("TIMESTAMP", mono(10))
        self.d_ip = field("SOURCE IP", mono(10))
        self.d_event = field("DESCRIPTION", ui(10))
        actions = tk.Frame(self.detail_body, bg=PANEL)
        actions.pack(fill="x", pady=(22, 0))
        FlatButton(actions, "Copy row", self._copy_selected, "default").pack(fill="x", pady=2)
        FlatButton(actions, "Show only this IP", self._filter_selected_ip, "subtle").pack(fill="x", pady=2)
        FlatButton(actions, "Delete event", self._delete_selected, "danger").pack(fill="x", pady=2)
        details.bind("<Configure>", lambda e: [lbl.configure(wraplength=max(120, e.width - 40))
                                               for lbl in self._detail_values])

    # Time complexity: O(1): render one selected record or clear the detail panel.
    def _render_details(self, record: LogRecord | None) -> None:
        if record is None:
            self.detail_body.pack_forget()
            self.detail_empty.pack(expand=True)
            return
        self.detail_empty.pack_forget()
        self.detail_body.pack(fill="both", expand=True, padx=18)
        self.d_id.configure(text=f"#{record.event_id}")
        self.d_sev.configure(text=f"●  {record.severity}", fg=SEVERITY_COLORS.get(record.severity, MUTED))
        self.d_time.configure(text=record.timestamp)
        self.d_ip.configure(text=record.source_ip)
        self.d_event.configure(text=record.event)

    # ------------------------------------------------------------ insights page
    # Time complexity: O(1): create the insights-page container.
    def _build_insights_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=BG)
        self.insight_host = tk.Frame(page, bg=BG)
        self.insight_host.pack(fill="both", expand=True)
        return page

    # Time complexity: O(1): create one panel with a fixed set of widgets.
    def _panel(self, parent: tk.Misc, title: str, accent: str = ACCENT) -> tuple[tk.Frame, tk.Frame]:
        card = make_card(parent)
        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=18, pady=(16, 8))
        tk.Frame(head, bg=accent, width=3, height=14).pack(side="left", padx=(0, 8))
        tk.Label(head, text=title, bg=PANEL, fg="#ffffff", font=ui(11, "bold")).pack(side="left")
        body = tk.Frame(card, bg=PANEL)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        return card, body

    # Time complexity: O(1): create one bar row.
    @staticmethod
    def _bar_row(parent: tk.Misc, label: str, value: float, maximum: float, color: str,
                 value_text: str, label_width: int = 16) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=5)
        tk.Label(row, text=label, width=label_width, anchor="w", bg=PANEL, fg=TEXT, font=mono(10)).pack(
            side="left"
        )
        tk.Label(row, text=value_text, width=16, anchor="e", bg=PANEL, fg=MUTED, font=mono(9)).pack(
            side="right"
        )
        track = tk.Frame(row, bg=PANEL_ALT, height=10)
        track.pack(side="left", fill="x", expand=True, padx=(8, 12))
        fraction = value / maximum if maximum else 0
        tk.Frame(track, bg=color).place(x=0, y=0, relheight=1, relwidth=max(0.01, min(1.0, fraction)))

    # Time complexity: O(N + u log u): count N records and sort qualifying IP summaries.
    def _refresh_insights(self) -> None:
        host = self.insight_host
        for child in host.winfo_children():
            child.destroy()
        records = list(self.system.store.records.values())
        if not records:
            tk.Label(host, text="Load log records to see insights.", bg=BG, fg=DIM, font=ui(12)).pack(
                expand=True
            )
            return

        total = len(records)
        severities = Counter(record.severity for record in records)
        sources = Counter(record.source_ip for record in records)
        patterns = self.system.queries.repeated_failed_logins(minimum_attempts=3)
        critical = severities.get("ERROR", 0) + severities.get("HIGH", 0)

        chips = tk.Frame(host, bg=BG)
        chips.pack(fill="x", pady=(0, 14))
        stat_card(chips, "TOTAL RECORDS", f"{total:,}", 0, ACCENT_HOVER)
        stat_card(chips, "UNIQUE SOURCE IPS", f"{len(sources):,}", 1, CYAN)
        stat_card(chips, "HIGH + ERROR EVENTS", f"{critical:,}  ({critical / total:.0%})", 2, ORANGE)
        stat_card(chips, "IPS WITH REPEATED FAILED LOGINS", f"{len(patterns):,}", 3, RED)
        for col in range(4):
            chips.columnconfigure(col, weight=1, uniform="chip")

        grid = tk.Frame(host, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1, uniform="col")
        grid.columnconfigure(1, weight=1, uniform="col")

        card, body = self._panel(grid, "Severity distribution", AMBER)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 14))
        ordered = [s for s in SEVERITY_ORDER if s in severities]
        ordered += sorted(set(severities) - set(SEVERITY_ORDER))
        top = max(severities.values())
        for severity in ordered:
            count = severities[severity]
            self._bar_row(body, severity, count, top, SEVERITY_COLORS.get(severity, MUTED),
                          f"{count:,}  {count / total:.1%}")

        card, body = self._panel(grid, "Busiest source IPs", CYAN)
        card.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 14))
        common = sources.most_common(6)
        for ip, count in common:
            self._bar_row(body, ip, count, common[0][1], CYAN, f"{count:,} event(s)", label_width=16)

        card, body = self._panel(grid, "Repeated failed-login patterns (3+ attempts)", RED)
        card.grid(row=1, column=0, columnspan=2, sticky="nsew")
        if patterns:
            top_failed = patterns[0][1]
            for ip, count in patterns[:8]:
                self._bar_row(body, ip, count, top_failed, RED, f"{count:,} failed login(s)")
        else:
            tk.Label(body, text="No matching pattern found.", bg=PANEL, fg=DIM, font=ui(10)).pack(anchor="w")
        tk.Label(body, text="Repeated events are investigation hints, not proof of an attack.", bg=PANEL,
                 fg=DIM, font=ui(8)).pack(anchor="w", pady=(10, 0))
        grid.rowconfigure(1, weight=1)

    # ------------------------------------------------------------- b-tree page
    # Time complexity: O(W): create the fixed B-Tree page layout.
    def _build_btree_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=BG)
        bar = make_card(page)
        bar.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(bar, bg=PANEL)
        inner.pack(fill="x", padx=14, pady=10)
        tk.Label(inner, text="Levels shown", bg=PANEL, fg=MUTED, font=ui(9, "bold")).pack(side="left")
        self.levels_var = tk.StringVar(value="3")
        self.levels_box = ttk.Combobox(inner, textvariable=self.levels_var, values=["1", "2", "3"],
                                       state="readonly", width=4, style="Dark.TCombobox", font=ui(10))
        self.levels_box.pack(side="left", padx=(8, 8), ipady=2)
        self.levels_box.bind("<<ComboboxSelected>>", lambda _e: self._draw_tree())
        FlatButton(inner, "Redraw", self._draw_tree, "subtle", padx=12, pady=6).pack(side="left")
        self.legend = tk.Frame(inner, bg=PANEL)
        self.legend.pack(side="left", padx=(18, 0))
        self.tree_info_var = tk.StringVar()
        tk.Label(inner, textvariable=self.tree_info_var, bg=PANEL, fg=MUTED, font=ui(9)).pack(side="right")

        border = make_card(page)
        border.pack(fill="both", expand=True)
        frame = tk.Frame(border, bg=BG)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        canvas = tk.Canvas(frame, background=BG, highlightthickness=0, cursor="fleur")
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview,
                             style="Dark.Horizontal.TScrollbar")
        vbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview,
                             style="Dark.Vertical.TScrollbar")
        canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.tree_canvas = canvas

        # Time complexity: O(1): adjust the canvas viewport.
        def on_wheel(event: tk.Event) -> None:
            delta = -1 if (event.num == 4 or event.delta > 0) else 1
            if event.state & 0x1:
                canvas.xview_scroll(delta * 3, "units")
            else:
                canvas.yview_scroll(delta * 3, "units")

        canvas.bind("<MouseWheel>", on_wheel)
        canvas.bind("<Button-4>", on_wheel)
        canvas.bind("<Button-5>", on_wheel)
        canvas.bind("<ButtonPress-1>", lambda e: canvas.scan_mark(e.x, e.y))
        canvas.bind("<B1-Motion>", lambda e: canvas.scan_dragto(e.x, e.y, gain=1))
        return page

    # Time complexity: O(h) = O(log N): follow the leftmost B-Tree path.
    @staticmethod
    def _tree_levels(root: BTreeNode) -> int:
        levels, node = 1, root
        while not node.leaf:
            node = node.children[0]
            levels += 1
        return levels

    # Time complexity: O(N): validate statistics and lay out/draw the displayed B-Tree nodes.
    def _draw_tree(self) -> None:
        self._tree_dirty = False
        tree = self.system.indexes.event_id_index
        canvas = self.tree_canvas
        canvas.delete("all")
        for widget in self.legend.winfo_children():
            widget.destroy()

        if not tree.root.keys:
            canvas.create_text(250, 80, text="The B-Tree is empty.", fill=TEXT, font=ui(13))
            canvas.configure(scrollregion=(0, 0, 700, 300))
            self.tree_info_var.set("")
            return

        total_levels = self._tree_levels(tree.root)
        self.levels_box.configure(values=[str(i) for i in range(1, total_levels + 1)])
        try:
            limit = int(self.levels_var.get())
        except ValueError:
            limit = 3
        limit = max(1, min(limit, total_levels))
        self.levels_var.set(str(limit))
        self.tree_info_var.set(
            f"t = {tree.t}   •   height = {tree.height()}   •   nodes = {tree.node_count():,}   •   "
            f"showing {limit} of {total_levels} levels"
        )

        key_width, node_height, gap, level_gap, margin = 48, 38, 22, 90, 50
        width_cache: dict[int, float] = {}

        # Time complexity: O(1): check leaf and depth conditions.
        def shows_children(node: BTreeNode, depth: int) -> bool:
            return not node.leaf and depth + 1 < limit

        # Time complexity: O(t): inspect the keys in one node; O(1) for fixed degree t.
        def own_width_of(node: BTreeNode) -> float:
            return max(60, len(node.keys) * key_width)

        # Time complexity: O(V) total across the memoized drawing pass for V displayed nodes.
        def subtree_width(node: BTreeNode, depth: int) -> float:
            cached = width_cache.get(id(node))
            if cached is not None:
                return cached
            own = own_width_of(node)
            if shows_children(node, depth):
                widths = [subtree_width(child, depth + 1) for child in node.children]
                result = max(own, sum(widths) + gap * (len(widths) - 1))
            else:
                result = own
            width_cache[id(node)] = result
            return result

        positions: dict[int, tuple[float, float, float, int]] = {}

        # Time complexity: O(V) total across the displayed tree layout.
        def layout(node: BTreeNode, left: float, depth: int) -> None:
            width = subtree_width(node, depth)
            center_x, center_y = left + width / 2, margin + depth * level_gap
            positions[id(node)] = (center_x, center_y, own_width_of(node), depth)
            if not shows_children(node, depth):
                return
            child_widths = [subtree_width(child, depth + 1) for child in node.children]
            child_total = sum(child_widths) + gap * (len(child_widths) - 1)
            child_left = left + (width - child_total) / 2
            for child, child_width in zip(node.children, child_widths):
                child_center_x = child_left + child_width / 2
                y1 = center_y + node_height / 2
                y2 = margin + (depth + 1) * level_gap - node_height / 2
                mid = (y1 + y2) / 2
                canvas.create_line(center_x, y1, center_x, mid, child_center_x, mid,
                                   child_center_x, y2, smooth=True, fill="#3f3f4a", width=1.6)
                layout(child, child_left, depth + 1)
                child_left += child_width + gap

        # Time complexity: O(V) total across the displayed node-rendering pass for fixed t.
        def draw_nodes(node: BTreeNode, depth: int) -> None:
            center_x, center_y, own_width, _depth = positions[id(node)]
            fill, outline = DEPTH_COLORS[depth % len(DEPTH_COLORS)]
            x1, x2 = center_x - own_width / 2, center_x + own_width / 2
            y1, y2 = center_y - node_height / 2, center_y + node_height / 2
            canvas.create_rectangle(x1 + 2, y1 + 3, x2 + 2, y2 + 3, fill="#000000", outline="")
            canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2)
            cell = own_width / len(node.keys)
            for index, key in enumerate(node.keys):
                if index:
                    divider = x1 + index * cell
                    canvas.create_line(divider, y1 + 5, divider, y2 - 5, fill=outline, width=1)
                canvas.create_text(x1 + index * cell + cell / 2, center_y, text=str(key),
                                   font=mono(9, "bold"), fill="#f5f5f5")
            if shows_children(node, depth):
                for child in node.children:
                    draw_nodes(child, depth + 1)
            elif not node.leaf:
                canvas.create_text(center_x, y2 + 12, text=f"⋯ {len(node.children)} subtrees",
                                   font=ui(8), fill=MUTED)

        full_width = subtree_width(tree.root, 0)
        layout(tree.root, margin, 0)
        draw_nodes(tree.root, 0)

        max_depth = max(depth for *_rest, depth in positions.values())
        for depth in range(max_depth + 1):
            _fill, outline = DEPTH_COLORS[depth % len(DEPTH_COLORS)]
            label = "Root" if depth == 0 else f"Level {depth}"
            tk.Label(self.legend, text=f"■ {label}", bg=PANEL, fg=outline, font=ui(9, "bold")).pack(
                side="left", padx=(0, 12)
            )

        total_width = full_width + margin * 2
        canvas.configure(scrollregion=(0, 0, total_width,
                                       max(260, (max_depth + 1) * level_gap + margin * 2)))
        self.update_idletasks()
        root_x = positions[id(tree.root)][0]
        canvas.xview_moveto(max(0.0, (root_x - canvas.winfo_width() / 2) / total_width))
        canvas.yview_moveto(0)

    # --------------------------------------------------------- benchmark page
    # Time complexity: O(W): create the fixed benchmark-page layout.
    def _build_benchmark_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=BG)
        bar = make_card(page)
        bar.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(bar, bg=PANEL)
        inner.pack(fill="x", padx=18, pady=14)
        text = tk.Frame(inner, bg=PANEL)
        text.pack(side="left")
        tk.Label(text, text="Exact-search performance", bg=PANEL, fg="#ffffff", font=ui(12, "bold")).pack(
            anchor="w"
        )
        tk.Label(text, text="Looks up the middle record by event ID, repeatedly, with the B-Tree index and "
                            "with a plain linear scan.", bg=PANEL, fg=MUTED, font=ui(9)).pack(anchor="w", pady=(3, 0))
        FlatButton(inner, "Run benchmark", self.run_benchmark, "accent", padx=20, pady=10).pack(side="right")
        self.bench_host = tk.Frame(page, bg=BG)
        self.bench_host.pack(fill="both", expand=True)
        tk.Label(self.bench_host, text="Press “Run benchmark” to compare the two search strategies.",
                 bg=BG, fg=DIM, font=ui(11)).pack(expand=True)
        return page

    # Time complexity: O(rN + r log N): r repetitions of linear and B-Tree search; dominated by linear scans.
    def run_benchmark(self) -> None:
        """Compare indexed exact-search timing with a linear-search baseline."""
        records = self.system.store.all_records()
        if not records:
            self.notify("Benchmark", "Load some logs before running the benchmark.", "warning")
            return
        self.set_status("Running benchmark…", "warn")
        self.update_idletasks()
        target_id = records[len(records) // 2].event_id
        repetitions = max(20, min(500, 250_000 // len(records)))

        start = time.perf_counter()
        btree_comparisons = 0
        for _ in range(repetitions):
            _value, comparisons = self.system.indexes.event_id_index.search_with_comparisons(target_id)
            btree_comparisons += comparisons
        btree_seconds = time.perf_counter() - start

        start = time.perf_counter()
        linear_comparisons = 0
        for _ in range(repetitions):
            for record in records:
                linear_comparisons += 1
                if record.event_id == target_id:
                    break
        linear_seconds = time.perf_counter() - start

        self._render_benchmark(len(records), target_id, repetitions, btree_seconds, linear_seconds,
                               btree_comparisons, linear_comparisons)
        self.set_status(f"Benchmark complete using {len(records):,} records.")

    # Time complexity: O(1) relative to record count: render a fixed number of benchmark widgets.
    def _render_benchmark(self, count, target_id, repetitions, btree_s, linear_s, btree_cmp, linear_cmp):
        host = self.bench_host
        for child in host.winfo_children():
            child.destroy()
        btree_ms = btree_s / repetitions * 1000
        linear_ms = linear_s / repetitions * 1000
        speedup = linear_s / btree_s if btree_s > 0 else float("inf")
        cmp_ratio = linear_cmp / btree_cmp if btree_cmp else float("inf")

        chips = tk.Frame(host, bg=BG)
        chips.pack(fill="x", pady=(0, 14))
        stat_card(chips, "RECORDS INDEXED", f"{count:,}", 0, ACCENT_HOVER, columns=4)
        stat_card(chips, "SEARCH TARGET", f"ID {target_id}", 1, VIOLET, columns=4)
        stat_card(chips, "REPETITIONS", f"{repetitions:,}", 2, CYAN, columns=4)
        stat_card(chips, "B-TREE SPEED-UP", "—" if speedup == float("inf") else f"{speedup:,.1f}×",
                  3, GREEN, columns=4)
        for col in range(4):
            chips.columnconfigure(col, weight=1, uniform="bench")

        grid = tk.Frame(host, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1, uniform="b")
        grid.columnconfigure(1, weight=1, uniform="b")
        for column, (title, ms, cmp_total, color) in enumerate((
            ("B-Tree index", btree_ms, btree_cmp, GREEN),
            ("Linear scan", linear_ms, linear_cmp, AMBER),
        )):
            card, body = self._panel(grid, title, color)
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 7) if column == 0 else (7, 0))
            tk.Label(body, text="AVERAGE SEARCH TIME", bg=PANEL, fg=MUTED, font=ui(8, "bold")).pack(anchor="w")
            tk.Label(body, text=f"{ms:.6f} ms", bg=PANEL, fg=color, font=ui(22, "bold")).pack(
                anchor="w", pady=(4, 14)
            )
            tk.Label(body, text="KEY COMPARISONS (TOTAL)", bg=PANEL, fg=MUTED, font=ui(8, "bold")).pack(anchor="w")
            tk.Label(body, text=f"{cmp_total:,}", bg=PANEL, fg=TEXT, font=ui(16, "bold")).pack(
                anchor="w", pady=(4, 0)
            )

        card, body = self._panel(host, "Relative time (shorter is better)", ACCENT)
        card.pack(fill="x", pady=(14, 0))
        slowest = max(btree_ms, linear_ms) or 1
        self._bar_row(body, "B-Tree", btree_ms, slowest, GREEN, f"{btree_ms:.5f} ms", label_width=10)
        self._bar_row(body, "Linear", linear_ms, slowest, AMBER, f"{linear_ms:.5f} ms", label_width=10)
        ratio_text = "" if cmp_ratio == float("inf") else f"   •   {cmp_ratio:,.1f}× fewer key comparisons"
        tk.Label(body, text=f"Timing depends on this computer and the dataset{ratio_text}.", bg=PANEL,
                 fg=DIM, font=ui(8)).pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------- shortcuts
    # Time complexity: O(1): bind one keyboard shortcut.
    def _shortcut(self, sequence: str, action) -> None:
        # Ignore shortcuts while a modal dialog is open.
        self.bind_all(sequence, lambda _e: None if self.grab_current() else action())

    # Time complexity: O(P): bind shortcuts for P fixed navigation pages.
    def _bind_shortcuts(self) -> None:
        self._shortcut("<Control-f>", self._focus_search)
        self._shortcut("<Control-o>", self.import_csv)
        self._shortcut("<Control-n>", self.add_log)
        self._shortcut("<F5>", self.show_all)
        for index, (key, *_rest) in enumerate(self.PAGES, start=1):
            self._shortcut(f"<Control-Key-{index}>", lambda k=key: self.show_page(k))

    # Time complexity: O(1): switch page and focus the search entry.
    def _focus_search(self) -> None:
        self.show_page("logs")
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")

    # ------------------------------------------------------------- row actions
    # Time complexity: O(log N): retrieve the selected ID from the event-ID B-Tree.
    def _selected_record(self) -> LogRecord | None:
        selection = self.table.selection()
        if not selection:
            return None
        return self.system.search_by_id(int(selection[0]))

    # Time complexity: O(1): identify and display the context menu for one row.
    def _show_context_menu(self, event: tk.Event) -> None:
        row = self.table.identify_row(event.y)
        if not row:
            return
        self.table.selection_set(row)
        try:
            self.row_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.row_menu.grab_release()

    # Time complexity: O(log N): retrieve the selected record and copy its fields.
    def _copy_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        self.clipboard_clear()
        self.clipboard_append(
            f"{record.event_id}\t{record.timestamp}\t{record.source_ip}\t{record.severity}\t{record.event}"
        )
        self.set_status(f"Copied event ID {record.event_id} to the clipboard.")

    # Time complexity: O(N): retrieve and filter all chronologically ordered records.
    def _filter_selected_ip(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        filtered = self.system.filter_records(self.system.all_chronological(), "", record.source_ip)
        self._display_records(filtered, f"Showing {len(filtered):,} record(s) from {record.source_ip}.")

    # Time complexity: O(N) including the refreshed display after a successful deletion.
    def _delete_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        if not self.confirm("Delete event", f"Delete event ID {record.event_id}?\nThis removes it from "
                                             "both B-Tree indexes."):
            return
        if self.system.delete_record(record.event_id):
            self.show_all()
            self.set_status(f"Deleted event ID {record.event_id}; both B-Tree indexes updated.")

    # ------------------------------------------------------------ data display
    # Time complexity: O(N): height is O(log N), but node_count traverses the tree.
    def _refresh_stats(self, visible_count: int) -> None:
        tree = self.system.indexes.event_id_index
        self.total_var.set(f"{len(self.system.store.records):,}")
        self.visible_var.set(f"{visible_count:,}")
        self.height_var.set(str(tree.height()))
        self.nodes_var.set(f"{tree.node_count():,}")
        self.degree_var.set(f"B-TREE  ·  MIN DEGREE t = {tree.t}")
        self.badge_var.set(f"{visible_count:,} shown")
        self._tree_dirty = True

    # Time complexity: O(m + N): render m visible rows and refresh N-dependent tree statistics.
    def _display_records(self, records: list[LogRecord], status: str = "", level: str = "ok") -> None:
        if self.page_key != "logs":
            self.show_page("logs")
        self.current_records = list(records)
        self.table.delete(*self.table.get_children())
        for index, record in enumerate(records):
            self.table.insert(
                "", "end", iid=str(record.event_id),
                values=(record.event_id, record.timestamp, record.source_ip,
                        f"●  {record.severity}", record.event),
                tags=(record.severity, "even" if index % 2 else "odd"),
            )
        if records:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self._render_details(None)
        self._refresh_stats(len(records))
        self.set_status(
            status or f"Showing {len(records):,} record(s). Total stored: {len(self.system.store.records):,}.",
            level,
        )

    # Time complexity: O(R + N log N): load R rows, rebuild indexes for N records, then display results.
    def _load_file(self, path: Path, show_dialog: bool = True) -> None:
        try:
            report = self.system.load_csv(path)
        except (OSError, ValueError) as exc:
            self.notify("Cannot load CSV", str(exc), "error")
            self.set_status(f"Load failed: {exc}", "error")
            return
        self.show_all()
        self.set_status(
            f"Loaded {report.loaded_rows:,} record(s) from {path.name}; "
            f"{report.duplicate_ids} duplicate ID(s), {report.invalid_rows} invalid row(s) skipped."
        )
        if show_dialog:
            details = report.summary()
            if report.issues:
                details += "\n\nExamples of skipped rows:\n" + "\n".join(report.issues[:5])
                if len(report.issues) > 5:
                    details += f"\n... and {len(report.issues) - 5} more issue(s)."
            self.notify("CSV import complete", details, "success", monospace=True)

    # ------------------------------------------------------------- data actions
    # Time complexity: O(N log N): load and index the bundled/generated dataset.
    def load_10000(self) -> None:
        """Load the included 10,000-record synthetic dataset."""
        if not LARGE_SAMPLE_LOGS.exists():
            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                generate_synthetic_logs(LARGE_SAMPLE_LOGS, count=10_000)
            except OSError as exc:
                self.notify("Dataset creation failed", str(exc), "error")
                return
        self._load_file(LARGE_SAMPLE_LOGS)

    # Time complexity: O(N log N): load and index the small sample dataset.
    def load_sample(self) -> None:
        """Load the compact 15-record dataset for quick demonstrations."""
        if SAMPLE_LOGS.exists():
            self._load_file(SAMPLE_LOGS)
        else:
            self.notify("Sample not found", f"Expected file:\n{SAMPLE_LOGS}", "error")

    # Time complexity: O(R + N log N): load rows, skip invalid/duplicate data, and rebuild indexes.
    def load_duplicate_test(self) -> None:
        """Load the supplied file that contains duplicate IDs and invalid rows."""
        if DUPLICATE_TEST_LOGS.exists():
            self._load_file(DUPLICATE_TEST_LOGS)
        else:
            self.notify("Test file not found", f"Expected file:\n{DUPLICATE_TEST_LOGS}", "error")

    # Time complexity: O(R + N log N) for selected CSV ingestion and index rebuilding.
    def import_csv(self) -> None:
        """Ask the user to select a CSV log file and load it."""
        selected = filedialog.askopenfilename(
            parent=self, title="Select log CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self._load_file(Path(selected))

    # Time complexity: O(N log N): generate/sort N rows and then load and index them.
    def generate_dataset(self) -> None:
        """Generate a reproducible synthetic dataset with the requested row count."""
        # Time complexity: O(1): validate the requested row count.
        def validate(values: dict) -> str | None:
            if not values["count"].isdigit() or not 1 <= int(values["count"]) <= 50_000:
                return "Enter a whole number between 1 and 50,000."
            return None

        result = self.ask_form(
            "Generate synthetic logs",
            [{"key": "count", "label": "Number of log records", "initial": "10000",
              "hint": "Between 1 and 50,000. The file is saved in the data folder."}],
            validate, "Generate", subtitle="Creates a reproducible dataset and loads it.",
        )
        if result is None:
            return
        count = int(result["count"])
        output_path = DATA_DIR / f"generated_logs_{count}.csv"
        if output_path.exists() and not self.confirm(
            "Overwrite dataset", f"{output_path.name} already exists. Replace it?", "Replace", danger=False
        ):
            return
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            generate_synthetic_logs(output_path, count=count)
        except (OSError, ValueError) as exc:
            self.notify("Dataset generation failed", str(exc), "error")
            return
        self._load_file(output_path, show_dialog=False)
        self.notify("Dataset generated", f"Created and loaded {count:,} synthetic log records.\n\n"
                                         f"Saved to:\n{output_path}", "success")

    # --------------------------------------------------------- query actions
    # Time complexity: O(log N) for inserting one record into both indexes, followed by display refresh.
    def add_log(self) -> None:
        """One form for all five fields; the record is inserted into the store and both indexes."""
        # Time complexity: O(log N): validate fields and insert into the store and both indexes.
        def validate(values: dict) -> str | None:
            if not values["event_id"].isdigit():
                return "Event ID must be a non-negative whole number."
            try:
                record = LogRecord(int(values["event_id"]), values["timestamp"], values["source_ip"],
                                   values["severity"], values["event"])
                self.system.add_record(record)
            except (ValueError, TypeError) as exc:
                return str(exc)
            return None

        result = self.ask_form(
            "Add log event",
            [
                {"key": "event_id", "label": "Event ID", "hint": "Non-negative integer, must be unique"},
                {"key": "timestamp", "label": "Timestamp", "initial": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "hint": "YYYY-MM-DD HH:MM:SS"},
                {"key": "source_ip", "label": "Source IP", "initial": ""},
                {"key": "severity", "label": "Severity", "initial": "INFO", "choices": list(reversed(SEVERITY_ORDER))},
                {"key": "event", "label": "Event description", "initial": ""},
            ],
            validate, "Add event", subtitle="The event is added to both B-Tree indexes.",
        )
        if result is None:
            return
        self.show_all()
        self.set_status(f"Inserted event ID {result['event_id']}; both B-Tree indexes updated.")

    # Time complexity: O(N) including GUI result rendering and full-tree node-count statistics.
    def search_id(self) -> None:
        """Search a record through the event-ID B-Tree."""
        found: dict = {}

        # Time complexity: O(1): validate and parse the event ID.
        def validate(values: dict) -> str | None:
            if not values["event_id"].isdigit():
                return "Enter a non-negative whole number."
            found["id"] = int(values["event_id"])
            return None

        if self.ask_form("Find event by ID", [{"key": "event_id", "label": "Event ID"}], validate,
                         "Search", subtitle="Looks the ID up directly in the B-Tree index.") is None:
            return
        event_id = found["id"]
        record = self.system.search_by_id(event_id)
        if record is None:
            self._display_records([], f"No record found for event ID {event_id}.", "error")
        else:
            self._display_records([record], f"Found event ID {event_id} using the B-Tree index.")
            self.table.selection_set(str(event_id))

    # Time complexity: O(N): inspect records and filter text, IP, severity, and ID.
    def _run_text_search(self, query: str, severity: str = ALL_SEVERITIES) -> None:
        """Show records whose text, IP, severity or ID contains the query, optionally by severity."""
        query = query.strip().casefold()
        records = self.system.all_chronological()
        if severity != ALL_SEVERITIES:
            records = [record for record in records if record.severity.upper() == severity]
        if query:
            records = [
                record for record in records
                if query in record.event.casefold()
                or query in record.source_ip.casefold()
                or query in record.severity.casefold()
                or query in str(record.event_id)
            ]
        parts = []
        if query:
            parts.append(f"text {query!r}")
        if severity != ALL_SEVERITIES:
            parts.append(f"severity {severity}")
        self._display_records(records, f"Search ({', '.join(parts)}) returned {len(records):,} record(s).")

    # Time complexity: O(N) when it runs a text search or displays all records.
    def quick_search(self) -> None:
        """Search using the search bar and the severity filter (both empty shows everything)."""
        query = self.search_var.get().strip()
        severity = self.severity_var.get()
        if not query and severity == ALL_SEVERITIES:
            self.show_all()
            return
        self._run_text_search(query, severity)

    # Time complexity: O(N): reset filters and display all records.
    def clear_search(self) -> None:
        """Reset the search bar and filter, then show every stored record."""
        self.search_var.set("")
        self.severity_var.set(ALL_SEVERITIES)
        self.show_all()

    # Time complexity: O(N + k): obtains all records for defaults, runs the range query, and updates the GUI.
    def search_time_range(self) -> None:
        """Retrieve all log records in the inclusive timestamp interval."""
        chronological = self.system.all_chronological()
        first = chronological[0].timestamp if chronological else ""
        last = chronological[-1].timestamp if chronological else ""
        found: dict = {}

        # Time complexity: O(log N + k): execute and validate a timestamp range query.
        def validate(values: dict) -> str | None:
            try:
                found["records"] = self.system.time_range(values["start"], values["end"])
            except ValueError as exc:
                return str(exc)
            return None

        result = self.ask_form(
            "Time-range search",
            [
                {"key": "start", "label": "Start timestamp", "initial": first, "hint": "YYYY-MM-DD HH:MM:SS"},
                {"key": "end", "label": "End timestamp", "initial": last, "hint": "YYYY-MM-DD HH:MM:SS"},
            ],
            validate, "Search", subtitle="Uses the timestamp B-Tree; both ends are inclusive.",
        )
        if result is None:
            return
        results = found["records"]
        self._display_records(results, f"Time-range query returned {len(results):,} record(s).")

    # Time complexity: O(N): retrieve and render every record.
    def show_all(self) -> None:
        """Display all stored records in timestamp order."""
        self._display_records(self.system.all_chronological())

    # Time complexity: O(N) on successful deletion due to the subsequent full-list refresh.
    def delete_log(self) -> None:
        """Delete a record by ID and remove its keys from both B-Tree indexes."""
        found: dict = {}

        # Time complexity: O(log N): validate and check the event ID through the B-Tree.
        def validate(values: dict) -> str | None:
            if not values["event_id"].isdigit():
                return "Enter a non-negative whole number."
            event_id = int(values["event_id"])
            if self.system.search_by_id(event_id) is None:
                return f"Event ID {event_id} was not found."
            found["id"] = event_id
            return None

        if self.ask_form("Delete event", [{"key": "event_id", "label": "Event ID to delete"}], validate,
                         "Delete", subtitle="The event is removed from both B-Tree indexes.",
                         danger=True) is None:
            return
        if self.system.delete_record(found["id"]):
            self.show_all()
            self.set_status(f"Deleted event ID {found['id']}; both B-Tree indexes updated.")

    # ----------------------------------------------------------------- tools
    # Time complexity: O(m): serialize and write the m visible records.
    def export_results(self) -> None:
        """Export currently visible query results to a CSV file."""
        if not self.current_records:
            self.notify("Export results", "There are no visible records to export.", "warning")
            return
        destination = filedialog.asksaveasfilename(
            parent=self, title="Export current results", defaultextension=".csv",
            initialfile="log_search_results.csv", filetypes=[("CSV files", "*.csv")],
        )
        if not destination:
            return
        try:
            with Path(destination).open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["event_id", "timestamp", "source_ip",
                                                            "severity", "event"])
                writer.writeheader()
                for record in self.current_records:
                    writer.writerow(record.to_row())
        except OSError as exc:
            self.notify("Export failed", str(exc), "error")
            return
        self.set_status(f"Exported {len(self.current_records):,} record(s) to {destination}.")
        self.notify("Export complete", f"Exported {len(self.current_records):,} record(s).", "success")

    # Time complexity: O(N log N): validate both indexes and check stored-record consistency.
    def check_indexes(self) -> None:
        """Validate B-Tree structural rules and record-index consistency."""
        id_errors = self.system.indexes.event_id_index.validation_errors()
        time_errors = self.system.indexes.timestamp_index.validation_errors()
        if self.system.is_consistent() and not id_errors and not time_errors:
            self.notify("Index check", "PASS: both B-Trees are valid and the indexes match the stored "
                                       "records.", "success")
            self.set_status("Index integrity check passed.")
            return
        details = "Index consistency check failed."
        if id_errors:
            details += "\n\nEvent-ID B-Tree:\n- " + "\n- ".join(id_errors[:6])
        if time_errors:
            details += "\n\nTimestamp B-Tree:\n- " + "\n- ".join(time_errors[:6])
        self.notify("Index check failed", details, "error")
        self.set_status("Index consistency check failed; see details.", "error")


# Time complexity: O(1) setup before entering Tkinter mainloop; the event loop runs until the window closes.
def main() -> None:
    """Start the desktop application."""
    if sys.platform == "win32":
        try:  # Crisp text on high-DPI Windows displays.
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    app = LogInvestigationApp()
    app.mainloop()


if __name__ == "__main__":
    main()
