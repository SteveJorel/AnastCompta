from tkinter import ttk

from app.services import income_service, product_service, sales_service
from app.utils.format import fmt_money, iso_to_fr, today_iso


class DashboardView(ttk.Frame):
    def __init__(self, parent, conn, navigate):
        super().__init__(parent, padding=30)
        today = today_iso()
        closure = sales_service.get_closure(conn, today)
        incomes = income_service.totals_by_category(conn, today, today)
        boutique = closure["total_theorique"] if closure else 0
        machine, bois = incomes.get("MACHINE", 0), incomes.get("BOIS", 0)

        ttk.Label(self, text="Tableau de bord", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(self, text=f"Aujourd'hui : {iso_to_fr(today)}").pack(anchor="w", pady=(0, 20))

        cards = ttk.Frame(self)
        cards.pack(fill="x")
        values = [
            ("Boutique (théorique)", boutique),
            ("Machine à écraser", machine),
            ("Bois de chauffage", bois),
            ("Total du jour", boutique + machine + bois),
        ]
        for i, (label, value) in enumerate(values):
            card = ttk.LabelFrame(cards, text=label, padding=15)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            cards.columnconfigure(i, weight=1)
            ttk.Label(card, text=fmt_money(value), font=("Segoe UI", 16, "bold")).pack()

        if closure:
            ttk.Label(self, text="Clôture du jour : effectuée", foreground="#1b7f3b").pack(anchor="w", pady=(25, 5))
        else:
            ttk.Label(self, text="Clôture du jour : non effectuée", foreground="#b26a00").pack(anchor="w", pady=(25, 5))

        low = product_service.low_stock(conn)
        if low:
            names = ", ".join(p["nom"] for p in low[:6]) + ("…" if len(low) > 6 else "")
            ttk.Label(
                self, text=f"Stock bas ({len(low)}) : {names}", foreground="#b00020", wraplength=800
            ).pack(anchor="w", pady=5)

        buttons = ttk.Frame(self)
        buttons.pack(anchor="w", pady=25)
        ttk.Button(buttons, text="Faire la clôture", command=lambda: navigate("sales")).pack(side="left", padx=(0, 8), ipady=4)
        ttk.Button(buttons, text="Saisir une recette", command=lambda: navigate("income")).pack(side="left", padx=(0, 8), ipady=4)
        ttk.Button(buttons, text="Voir les produits", command=lambda: navigate("products")).pack(side="left", ipady=4)