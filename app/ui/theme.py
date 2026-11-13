from tkinter import ttk

FONT = "Segoe UI"
BG = "#f3f5f9"            # fond des pages
SURFACE = "#ffffff"       # cartes, champs, tableaux
SIDEBAR = "#1e293b"       # menu latéral
SIDEBAR_HOVER = "#334155"
ACCENT = "#2563eb"        # couleur principale
ACCENT_DARK = "#1d4ed8"
TEXT = "#1f2937"
MUTED = "#6b7280"
BORDER = "#d9dee7"
HEADER_BG = "#e9eef6"
SELECT_BG = "#dbeafe"
ROW_ALT = "#f6f8fc"
SUCCESS, WARNING, DANGER = "#1b7f3b", "#b26a00", "#b00020"


def apply_theme(root):
    root.configure(background=BG)
    root.option_add("*TCombobox*Listbox.font", (FONT, 11))
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=(FONT, 11))

    # --- Conteneurs et textes ---
    style.configure("TFrame", background=BG)
    style.configure("Sidebar.TFrame", background=SIDEBAR)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Title.TLabel", font=(FONT, 20, "bold"))
    style.configure("Subtitle.TLabel", foreground=MUTED)
    style.configure("Card.TLabel", background=SURFACE)
    style.configure("CardTitle.TLabel", background=SURFACE, foreground=MUTED, font=(FONT, 10))
    style.configure("CardValue.TLabel", background=SURFACE, font=(FONT, 20, "bold"))
    style.configure("CardHeading.TLabel", background=SURFACE, font=(FONT, 20, "bold"))
    style.configure("CardText.TLabel", background=SURFACE, foreground=MUTED)
    style.configure("CardError.TLabel", background=SURFACE, foreground=DANGER)
    style.configure("Brand.TLabel", background=SURFACE, foreground=ACCENT, font=(FONT, 16, "bold"))
    style.configure("Sidebar.TLabel", background=SIDEBAR, foreground="#ffffff", font=(FONT, 16, "bold"))
    style.configure("SidebarMuted.TLabel", background=SIDEBAR, foreground="#94a3b8", font=(FONT, 10))

    # --- Boutons ---
    style.configure("TButton", background=SURFACE, foreground=TEXT, bordercolor=BORDER,
                    lightcolor=SURFACE, darkcolor=SURFACE, padding=(14, 8), focuscolor=SURFACE)
    style.map("TButton", background=[("active", "#e8edf5"), ("disabled", BG)],
              foreground=[("disabled", MUTED)])
    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff", bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, padding=(16, 9), font=(FONT, 11, "bold"))
    style.map("Accent.TButton",
              background=[("active", ACCENT_DARK), ("disabled", "#93b4f0")],
              bordercolor=[("active", ACCENT_DARK)], lightcolor=[("active", ACCENT_DARK)],
              darkcolor=[("active", ACCENT_DARK)], foreground=[("disabled", "#ffffff")])
    style.configure("Link.TButton", background=SURFACE, foreground=ACCENT, borderwidth=0, padding=(4, 6),
                    font=(FONT, 10, "underline"), bordercolor=SURFACE, lightcolor=SURFACE, darkcolor=SURFACE)
    style.map("Link.TButton", background=[("active", SURFACE)], foreground=[("active", ACCENT_DARK)])
    style.configure("Lock.TButton", background=SIDEBAR_HOVER, foreground="#ffffff", bordercolor=SIDEBAR_HOVER,
                    lightcolor=SIDEBAR_HOVER, darkcolor=SIDEBAR_HOVER, padding=(14, 9))
    style.map("Lock.TButton", background=[("active", "#475569")], bordercolor=[("active", "#475569")],
              lightcolor=[("active", "#475569")], darkcolor=[("active", "#475569")])

    # --- Menu latéral ---
    style.configure("Nav.Toolbutton", background=SIDEBAR, foreground="#cbd5e1", anchor="w", padding=(16, 11),
                    borderwidth=0, bordercolor=SIDEBAR, lightcolor=SIDEBAR, darkcolor=SIDEBAR, font=(FONT, 11))
    style.map("Nav.Toolbutton",
              background=[("selected", ACCENT), ("active", SIDEBAR_HOVER)],
              foreground=[("selected", "#ffffff"), ("active", "#ffffff")],
              bordercolor=[("selected", ACCENT), ("active", SIDEBAR_HOVER)],
              lightcolor=[("selected", ACCENT), ("active", SIDEBAR_HOVER)],
              darkcolor=[("selected", ACCENT), ("active", SIDEBAR_HOVER)])

    # --- Champs de saisie ---
    style.configure("TEntry", fieldbackground=SURFACE, foreground=TEXT, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, padding=6)
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)],
              darkcolor=[("focus", ACCENT)])
    style.configure("TCombobox", fieldbackground=SURFACE, background=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, arrowcolor=MUTED, padding=5)
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE)], background=[("readonly", SURFACE)],
              foreground=[("readonly", TEXT)], bordercolor=[("focus", ACCENT)])
    style.configure("TCheckbutton", background=BG)
    style.configure("TRadiobutton", background=BG)

    # --- Tableaux ---
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                    rowheight=30, bordercolor=BORDER, borderwidth=1, font=(FONT, 11))
    style.configure("Treeview.Heading", background=HEADER_BG, foreground=TEXT, font=(FONT, 10, "bold"),
                    padding=(8, 8), relief="flat", bordercolor=BORDER)
    style.map("Treeview.Heading", background=[("active", "#dbe4f1")])
    style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", TEXT)])

    # --- Onglets, cadres, ascenseurs ---
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
    style.configure("TNotebook.Tab", background="#e4e9f1", foreground=MUTED, padding=(18, 9), borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", SURFACE)], foreground=[("selected", ACCENT)])
    style.configure("TLabelframe", background=BG, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    style.configure("TLabelframe.Label", background=BG, foreground=ACCENT, font=(FONT, 11, "bold"))
    style.configure("TScrollbar", background="#c7cfdb", troughcolor=BG, bordercolor=BG,
                    lightcolor="#c7cfdb", darkcolor="#c7cfdb", arrowcolor=MUTED)
    style.map("TScrollbar", background=[("active", "#aab4c4")])