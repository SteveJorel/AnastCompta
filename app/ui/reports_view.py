import tempfile
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.services import income_service
from app.services import report_service as rs
from app.services import settings_service
from app.ui.widgets import SortableTree
from app.utils.format import fmt_money, fmt_qty, fr_to_iso, iso_to_fr, today_iso

BOLD = ("Segoe UI", 11, "bold")
KINDS = {"Jour": "jour", "Semaine": "semaine", "Mois": "mois"}
COLORS = ["#2f6fb2", "#e08a1e", "#3a9a5b", "#8a5bb5", "#b5563a"]


class ReportsView(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent, padding=20)
        self.conn = conn
        self.categories = income_service.list_categories(conn)
        self.devise = settings_service.get(conn, "devise", "FCFA")
        self.shop = settings_service.get(conn, "nom_boutique", "")
        self._days, self._current = [], None

        ttk.Label(self, text="Bilans", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(10, 4))
        self.kind_box = ttk.Combobox(bar, values=list(KINDS), state="readonly", width=10)
        self.kind_box.current(0)
        self.kind_box.pack(side="left")
        self.kind_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.v_ref = tk.StringVar(value=iso_to_fr(today_iso()))
        ttk.Button(bar, text="Précédent", command=lambda: self.shift(-1)).pack(side="left", padx=(10, 2))
        entry = ttk.Entry(bar, textvariable=self.v_ref, width=12)
        entry.pack(side="left", padx=2)
        entry.bind("<Return>", lambda e: self.refresh())
        ttk.Button(bar, text="Suivant", command=lambda: self.shift(1)).pack(side="left", padx=2)
        ttk.Button(bar, text="Afficher", command=self.refresh).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Imprimer", command=self.print_report).pack(side="right")
        ttk.Button(bar, text="Exporter en CSV", command=self.export_csv).pack(side="right", padx=6)
        self.period_lbl = ttk.Label(self, font=BOLD)
        self.period_lbl.pack(anchor="w", pady=(4, 8))

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)
        summary_tab = ttk.Frame(tabs, padding=10)
        self.kpi = ttk.Frame(summary_tab)
        self.kpi.pack(fill="x")
        self.chart = tk.Canvas(summary_tab, height=260, highlightthickness=0)
        self.chart.pack(fill="both", expand=True, pady=(15, 0))
        self.chart.bind("<Configure>", lambda e: self.draw_chart())

        columns = [("date", "Date", 110, "w"), ("boutique", "Boutique", 110, "e")]
        columns += [(c["code"], c["libelle"], 130, "e") for c in self.categories]
        columns += [("total", "Total", 110, "e"), ("benef", "Bénéfice", 110, "e")]
        self.detail = SortableTree(tabs, columns)
        self.products = SortableTree(tabs, [
            ("nom", "Produit", 240, "w"), ("unite", "Unité", 80, "center"),
            ("qte", "Quantité vendue", 120, "e"), ("montant", "Montant", 120, "e"), ("benef", "Bénéfice", 120, "e"),
        ])
        tabs.add(summary_tab, text="Synthèse")
        tabs.add(self.detail, text="Détail par jour")
        tabs.add(self.products, text="Produits vendus")
        self.refresh()

    def _kind(self):
        return KINDS[self.kind_box.get()]

    def shift(self, direction):
        try:
            ref = fr_to_iso(self.v_ref.get())
        except ValueError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self.v_ref.set(iso_to_fr(rs.shift_period(self._kind(), ref, direction)))
        self.refresh()

    def refresh(self):
        try:
            ref = fr_to_iso(self.v_ref.get())
        except ValueError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        kind = self._kind()
        start, end = rs.period_bounds(kind, ref)
        current = rs.summary(self.conn, start, end)
        prev_start, prev_end = rs.period_bounds(kind, rs.shift_period(kind, start, -1))
        previous = rs.summary(self.conn, prev_start, prev_end)
        self._current = (kind, start, end)
        self.period_lbl.config(text=f"{rs.period_label(kind, start, end)}   |   montants en {self.devise}")
        self._fill_kpis(current, previous)

        self._days = rs.daily_breakdown(self.conn, start, end)
        codes = [c["code"] for c in self.categories]
        self.detail.clear()
        for r in self._days:
            self.detail.insert(
                (iso_to_fr(r["date"]), fmt_money(r["boutique"]))
                + tuple(fmt_money(r["annexes"].get(code, 0)) for code in codes)
                + (fmt_money(r["total"]), fmt_money(r["benefice"]))
            )
        self.products.clear()
        for p in rs.top_products(self.conn, start, end, 100):
            self.products.insert((p["nom"], p["unite"], fmt_qty(p["quantite"]),
                                  fmt_money(p["montant"]), fmt_money(p["benefice"])))
        self.draw_chart()

    def _fill_kpis(self, s, previous):
        for widget in self.kpi.winfo_children():
            widget.destroy()
        ca = s["ca_global"]

        def pct(value):
            return f"  ({value / ca * 100:.0f} %)" if ca else ""

        rows = [("Chiffre d'affaires global", fmt_money(ca), True),
                ("      dont boutique (théorique)", fmt_money(s["boutique"]) + pct(s["boutique"]), False)]
        rows += [(f"      dont {libelle.lower()}", fmt_money(total) + pct(total), False)
                 for _, libelle, total in s["annexes"]]
        variation = rs.variation_pct(ca, previous["ca_global"])
        rows += [
            ("Coût d'achat des marchandises vendues", fmt_money(s["cout_achat"]), False),
            ("Bénéfice boutique", fmt_money(s["benefice_boutique"]), False),
            ("Bénéfice total", fmt_money(s["benefice_total"]), True),
            ("Montant encaissé (boutique)", fmt_money(s["encaisse"]), False),
            ("Écart de caisse cumulé", fmt_money(s["ecart"]), False),
            ("Clôtures enregistrées", str(s["nb_clotures"]), False),
            ("Évolution du chiffre d'affaires vs période précédente",
             "—" if variation is None else f"{variation:+.0f} %", False),
        ]
        for i, (label, value, bold) in enumerate(rows):
            font = BOLD if bold else ("Segoe UI", 11)
            ttk.Label(self.kpi, text=label, font=font).grid(row=i, column=0, sticky="w", pady=1)
            ttk.Label(self.kpi, text=value, font=font).grid(row=i, column=1, sticky="e", padx=(30, 0), pady=1)

    def draw_chart(self):
        c = self.chart
        c.delete("all")
        days = self._days
        if not days:
            return
        width, height = max(c.winfo_width(), 400), max(c.winfo_height(), 200)
        left, right, top, bottom = 60, 20, 34, height - 26
        maxv = max([d["total"] for d in days] + [1])
        names = ["Boutique"] + [cat["libelle"] for cat in self.categories]
        codes = [cat["code"] for cat in self.categories]
        x = left
        for k, name in enumerate(names):
            c.create_rectangle(x, 10, x + 12, 22, fill=COLORS[k % len(COLORS)], outline="")
            item = c.create_text(x + 18, 16, text=name, anchor="w", font=("Segoe UI", 9))
            x = c.bbox(item)[2] + 18
        c.create_line(left, top, left, bottom, fill="#999999")
        c.create_line(left, bottom, width - right, bottom, fill="#999999")
        c.create_text(left - 6, top, text=fmt_money(maxv), anchor="e", font=("Segoe UI", 8))
        c.create_text(left - 6, bottom, text="0", anchor="e", font=("Segoe UI", 8))
        slot = (width - left - right) / len(days)
        bar_w = min(slot * 0.7, 46)
        for i, d in enumerate(days):
            x0 = left + i * slot + (slot - bar_w) / 2
            y = bottom
            parts = [d["boutique"]] + [d["annexes"].get(code, 0) for code in codes]
            for k, value in enumerate(parts):
                if value <= 0:
                    continue
                h = value / maxv * (bottom - top)
                c.create_rectangle(x0, y - h, x0 + bar_w, y, fill=COLORS[k % len(COLORS)], outline="")
                y -= h
            if len(days) <= 16 or i % 2 == 0:
                c.create_text(x0 + bar_w / 2, bottom + 12, text=str(int(d["date"][8:10])), font=("Segoe UI", 8))

    def _title(self):
        kind, start, end = self._current
        return rs.report_title(kind, start, end, self.shop)

    def export_csv(self):
        if not self._current:
            return
        kind, start, end = self._current
        path = filedialog.asksaveasfilename(
            title="Exporter le bilan", defaultextension=".csv",
            filetypes=[("CSV (Excel)", "*.csv")], initialfile=f"bilan_{kind}_{start}.csv",
        )
        if not path:
            return
        try:
            rs.write_csv(path, self._title(), rs.report_sections(self.conn, start, end))
        except OSError as exc:
            messagebox.showerror("Erreur", f"Écriture impossible :\n{exc}")
            return
        messagebox.showinfo("Export", f"Bilan exporté :\n{path}")

    def print_report(self):
        if not self._current:
            return
        _, start, end = self._current
        html = rs.build_html(self._title(), rs.report_sections(self.conn, start, end))
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(Path(f.name).as_uri())