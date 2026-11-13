import tkinter as tk
from tkinter import ttk

from app.services import income_service, product_service, sales_service, settings_service
from app.ui import theme
from app.utils.format import fmt_money, iso_to_fr, today_iso


def _card(parent, column, title, value, color):
    card = tk.Frame(parent, bg=theme.SURFACE, highlightbackground=theme.BORDER, highlightthickness=1)
    card.grid(row=0, column=column, padx=8, sticky="nsew")
    parent.columnconfigure(column, weight=1, uniform="cards")
    tk.Frame(card, bg=color, height=4).pack(fill="x")
    inner = tk.Frame(card, bg=theme.SURFACE, padx=18, pady=14)
    inner.pack(fill="both", expand=True)
    ttk.Label(inner, text=title, style="CardTitle.TLabel").pack(anchor="w")
    ttk.Label(inner, text=fmt_money(value), style="CardValue.TLabel").pack(anchor="w", pady=(6, 0))


def _badge(parent, text, bg, fg):
    tk.Label(parent, text=text, bg=bg, fg=fg, font=(theme.FONT, 11), padx=14, pady=8,
             anchor="w", justify="left", wraplength=780).pack(anchor="w", pady=4)


class DashboardView(ttk.Frame):
    def __init__(self, parent, conn, navigate):
        super().__init__(parent, padding=30)
        today = today_iso()
        devise = settings_service.get(conn, "devise", "FCFA")
        closure = sales_service.get_closure(conn, today)
        incomes = income_service.totals_by_category(conn, today, today)
        boutique = closure["total_theorique"] if closure else 0
        machine, bois = incomes.get("MACHINE", 0), incomes.get("BOIS", 0)

        ttk.Label(self, text="Tableau de bord", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            self, text=f"Aujourd'hui : {iso_to_fr(today)}   |   montants en {devise}", style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 22))

        cards = ttk.Frame(self)
        cards.pack(fill="x")
        _card(cards, 0, "Boutique (théorique)", boutique, "#2f6fb2")
        _card(cards, 1, "Machine à écraser", machine, "#e08a1e")
        _card(cards, 2, "Bois de chauffage", bois, "#3a9a5b")
        _card(cards, 3, "Total du jour", boutique + machine + bois, theme.SIDEBAR)

        alerts = ttk.Frame(self)
        alerts.pack(fill="x", pady=(26, 0))
        if closure:
            _badge(alerts, "Clôture du jour : effectuée", "#dcfce7", "#166534")
        else:
            _badge(alerts, "Clôture du jour : non effectuée", "#fef3c7", "#92400e")
        low = product_service.low_stock(conn)
        if low:
            names = ", ".join(p["nom"] for p in low[:6]) + ("…" if len(low) > 6 else "")
            _badge(alerts, f"Stock bas ({len(low)}) : {names}", "#fee2e2", "#991b1b")

        buttons = ttk.Frame(self)
        buttons.pack(anchor="w", pady=26)
        ttk.Button(buttons, text="Faire la clôture", style="Accent.TButton",
                   command=lambda: navigate("sales")).pack(side="left", padx=(0, 10))
        ttk.Button(buttons, text="Saisir une recette", command=lambda: navigate("income")).pack(
            side="left", padx=(0, 10))
        ttk.Button(buttons, text="Voir les produits", command=lambda: navigate("products")).pack(side="left")