import tkinter as tk
from tkinter import ttk

from app.ui.dashboard_view import DashboardView
from app.ui.income_view import IncomeView
from app.ui.products_view import ProductsView
from app.ui.sales_view import SalesView
from app.ui.reports_view import ReportsView
from app.ui.settings_view import SettingsView

MENU = [
    ("dashboard", "Tableau de bord"),
    ("products", "Produits"),
    ("sales", "Clôture du jour"),
    ("income", "Recettes annexes"),
    ("reports", "Bilans"),
    ("settings", "Paramètres"),
]


class PlaceholderView(ttk.Frame):
    def __init__(self, parent, title, text):
        super().__init__(parent, padding=30)
        ttk.Label(self, text=title, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(self, text=text).pack(anchor="w", pady=10)


class MainWindow(ttk.Frame):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self._current = None
        self.nav_var = tk.StringVar()

        sidebar = ttk.Frame(self, padding=10)
        sidebar.pack(side="left", fill="y")
        self.content = ttk.Frame(self)
        self.content.pack(side="left", fill="both", expand=True)

        ttk.Label(sidebar, text="AnastCompta", font=("Segoe UI", 14, "bold")).pack(pady=(5, 20))
        for key, label in MENU:
            ttk.Radiobutton(
                sidebar, text=label, value=key, variable=self.nav_var, style="Toolbutton",
                width=20, command=lambda k=key: self.navigate(k),
            ).pack(fill="x", pady=2)
        ttk.Button(sidebar, text="Verrouiller", command=app.show_login).pack(side="bottom", fill="x", ipady=6)
        self.navigate("dashboard")

    def navigate(self, key):
        conn = self.app.conn
        factories = {
            "dashboard": lambda: DashboardView(self.content, conn, self.navigate),
            "products": lambda: ProductsView(self.content, conn),
            "sales": lambda: SalesView(self.content, conn),
            "income": lambda: IncomeView(self.content, conn),
            "reports": lambda: ReportsView(self.content, conn),
            "settings": lambda: SettingsView(self.content, self.app),
            }
        if self._current is not None:
            self._current.destroy()
        self.nav_var.set(key)
        self._current = factories[key]()
        self._current.pack(fill="both", expand=True)