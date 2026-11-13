import tkinter as tk
from tkinter import ttk, messagebox

from app.services import sales_service as ss
from app.ui.widgets import Dialog, ScrollableFrame, SortableTree
from app.utils.format import fmt_money, fmt_qty, fr_to_iso, iso_to_fr, parse_amount, parse_quantity, today_iso

BOLD = ("Segoe UI", 11, "bold")


class SalesView(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent, padding=20)
        ttk.Label(self, text="Clôture de journée", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, pady=(10, 0))
        self.history = HistoryTab(tabs, conn)
        self.closure = ClosureTab(tabs, conn, on_saved=self.history.refresh)
        tabs.add(self.closure, text="Clôture du jour")
        tabs.add(self.history, text="Historique")


class ClosureTab(ttk.Frame):
    def __init__(self, parent, conn, on_saved):
        super().__init__(parent, padding=10)
        self.conn, self.on_saved = conn, on_saved
        self.rows, self.date_iso = [], today_iso()
        self._syncing = False

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Date :").pack(side="left")
        self.v_date = tk.StringVar(value=iso_to_fr(today_iso()))
        ttk.Entry(top, textvariable=self.v_date, width=12).pack(side="left", padx=6)
        ttk.Button(top, text="Charger", command=self.load).pack(side="left")
        self.status = ttk.Label(top, text="")
        self.status.pack(side="left", padx=15)
        ttk.Label(
            self,
            text="Pour chaque produit, saisissez la quantité vendue OU la quantité restante : "
                 "l'autre se calcule automatiquement.",
        ).pack(anchor="w", pady=(8, 0))

        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, pady=10)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x")
        self.v_total, self.v_benef = tk.StringVar(value="0"), tk.StringVar(value="0")
        self.v_encaisse, self.v_ecart = tk.StringVar(), tk.StringVar(value="—")
        self.v_comment = tk.StringVar()
        ttk.Label(bottom, text="Total théorique à encaisser :").grid(row=0, column=0, sticky="w")
        ttk.Label(bottom, textvariable=self.v_total, font=BOLD).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(bottom, text="Bénéfice théorique :").grid(row=0, column=2, sticky="w", padx=(30, 0))
        ttk.Label(bottom, textvariable=self.v_benef, font=BOLD).grid(row=0, column=3, sticky="w", padx=10)
        ttk.Label(bottom, text="Montant réellement encaissé :").grid(row=1, column=0, sticky="w", pady=8)
        self.enc_entry = ttk.Entry(bottom, textvariable=self.v_encaisse, width=14)
        self.enc_entry.grid(row=1, column=1, sticky="w", padx=10)
        ttk.Label(bottom, text="Écart de caisse :").grid(row=1, column=2, sticky="w", padx=(30, 0))
        self.ecart_lbl = ttk.Label(bottom, textvariable=self.v_ecart, font=BOLD)
        self.ecart_lbl.grid(row=1, column=3, sticky="w", padx=10)
        ttk.Label(bottom, text="Commentaire :").grid(row=2, column=0, sticky="w")
        ttk.Entry(bottom, textvariable=self.v_comment, width=50).grid(row=2, column=1, columnspan=3, sticky="w", padx=10)
        self.btn = ttk.Button(bottom, text="Valider la clôture", command=self.save)
        self.btn.grid(row=3, column=0, pady=10, sticky="w", ipady=4)
        self.v_encaisse.trace_add("write", lambda *a: self.recalc())
        self.load()

    def load(self):
        try:
            self.date_iso = fr_to_iso(self.v_date.get())
        except ValueError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        closure = ss.get_closure(self.conn, self.date_iso)
        inner = self.scroll.inner
        for child in inner.winfo_children():
            child.destroy()
        self.rows = []
        headers = ["Produit", "Unité", "Stock d'ouverture", "Quantité vendue", "Quantité restante",
                   "Montant théorique", "Bénéfice"]
        for c, text in enumerate(headers):
            ttk.Label(inner, text=text, font=BOLD).grid(
                row=0, column=c, padx=8, pady=(0, 6), sticky="w" if c == 0 else "e")
        for r, line in enumerate(ss.build_sheet(self.conn, self.date_iso), start=1):
            restant0 = line["restant"]
            v_restant = tk.StringVar(value="" if restant0 is None else fmt_qty(restant0))
            v_vendu = tk.StringVar(
                value="" if restant0 is None else fmt_qty(round(line["ouverture"] - restant0, 6)))
            ttk.Label(inner, text=line["nom"]).grid(row=r, column=0, padx=8, sticky="w")
            ttk.Label(inner, text=line["unite"]).grid(row=r, column=1, padx=8, sticky="e")
            ttk.Label(inner, text=fmt_qty(line["ouverture"])).grid(row=r, column=2, padx=8, sticky="e")
            e_vendu = ttk.Entry(inner, textvariable=v_vendu, width=10, justify="right")
            e_vendu.grid(row=r, column=3, padx=8, pady=2)
            e_restant = ttk.Entry(inner, textvariable=v_restant, width=10, justify="right")
            e_restant.grid(row=r, column=4, padx=8, pady=2)
            lbl_m, lbl_b = ttk.Label(inner, text="—"), ttk.Label(inner, text="—")
            lbl_m.grid(row=r, column=5, padx=8, sticky="e")
            lbl_b.grid(row=r, column=6, padx=8, sticky="e")
            row = {"line": line, "v_vendu": v_vendu, "v_restant": v_restant,
                   "e_vendu": e_vendu, "e_restant": e_restant, "montant": lbl_m, "benef": lbl_b}
            index = len(self.rows)
            e_vendu.bind("<Return>", lambda e, i=index: self.focus_next(i, "e_vendu"))
            e_restant.bind("<Return>", lambda e, i=index: self.focus_next(i, "e_restant"))
            v_vendu.trace_add("write", lambda *a, row=row: self.sync(row, "vendu"))
            v_restant.trace_add("write", lambda *a, row=row: self.sync(row, "restant"))
            self.rows.append(row)

        self.status.config(text="Modification d'une clôture existante" if closure else "Nouvelle clôture")
        self.v_encaisse.set("" if not closure or closure["montant_encaisse"] is None else str(closure["montant_encaisse"]))
        self.v_comment.set((closure["commentaire"] or "") if closure else "")
        self.btn.config(text="Enregistrer la modification" if closure else "Valider la clôture")
        self.recalc()
        if self.rows:
            self.rows[0]["e_vendu"].focus()

    def sync(self, row, source):
        """Quand une des deux quantités change, l'autre est recalculée à partir du stock d'ouverture."""
        if self._syncing:
            return
        self._syncing = True
        try:
            if source == "vendu":
                src, dst = row["v_vendu"], row["v_restant"]
            else:
                src, dst = row["v_restant"], row["v_vendu"]
            text = src.get().strip()
            if not text:
                dst.set("")
            else:
                try:
                    value = parse_quantity(text)
                except ValueError:
                    dst.set("")
                else:
                    dst.set(fmt_qty(round(row["line"]["ouverture"] - value, 6)))
        finally:
            self._syncing = False
        self.recalc()

    def focus_next(self, index, key):
        target = self.rows[index + 1][key] if index + 1 < len(self.rows) else self.enc_entry
        target.focus()

    def recalc(self):
        total = benef_total = 0
        for row in self.rows:
            line, text = row["line"], row["v_restant"].get().strip()
            try:
                restant = parse_quantity(text) if text else line["ouverture"]
                if restant > line["ouverture"]:
                    raise ValueError
            except ValueError:
                row["montant"].config(text="!")
                row["benef"].config(text="—")
                continue
            _, montant, _, benef = ss.compute_line(
                line["ouverture"], restant, line["prix_achat"], line["prix_vente"])
            row["montant"].config(text=fmt_money(montant))
            row["benef"].config(text=fmt_money(benef))
            total += montant
            benef_total += benef
        self.v_total.set(fmt_money(total))
        self.v_benef.set(fmt_money(benef_total))

        text = self.v_encaisse.get().strip()
        try:
            encaisse = parse_amount(text) if text else None
        except ValueError:
            encaisse = None
        if encaisse is None:
            self.v_ecart.set("—")
            self.ecart_lbl.config(foreground="black")
            return
        ecart = encaisse - total
        if ecart == 0:
            self.v_ecart.set("0 (équilibré)")
            self.ecart_lbl.config(foreground="#1b7f3b")
        elif ecart < 0:
            self.v_ecart.set(f"-{fmt_money(-ecart)} (manque)")
            self.ecart_lbl.config(foreground="#b00020")
        else:
            self.v_ecart.set(f"+{fmt_money(ecart)} (excédent)")
            self.ecart_lbl.config(foreground="#b26a00")

    def save(self):
        restants, blanks = {}, 0
        for row in self.rows:
            line, text = row["line"], row["v_restant"].get().strip()
            if not text:
                blanks += 1
                continue
            error = (f"« {line['nom']} » : quantité invalide. La quantité vendue doit être comprise "
                     f"entre 0 et le stock d'ouverture ({fmt_qty(line['ouverture'])}).")
            try:
                restant = parse_quantity(text)
            except ValueError:
                messagebox.showerror("Erreur", error)
                return
            if restant > line["ouverture"]:
                messagebox.showerror("Erreur", error)
                return
            if not line["decimales"] and restant != int(restant):
                messagebox.showerror(
                    "Erreur", f"« {line['nom']} » : la quantité doit être un nombre entier pour cette unité.")
                return
            restants[line["produit_id"]] = restant
        text = self.v_encaisse.get().strip()
        try:
            encaisse = parse_amount(text) if text else None
        except ValueError as exc:
            messagebox.showerror("Erreur", f"Montant encaissé : {exc}")
            return
        msg = (f"Clôture du {iso_to_fr(self.date_iso)}\n\nTotal théorique : {self.v_total.get()}\n"
               f"Bénéfice théorique : {self.v_benef.get()}\n")
        if encaisse is not None:
            msg += f"Écart de caisse : {self.v_ecart.get()}\n"
        if blanks:
            msg += f"\n{blanks} produit(s) sans quantité saisie seront considérés comme non vendus.\n"
        if not messagebox.askyesno("Confirmer la clôture", msg + "\nValider ?"):
            return
        try:
            ss.save_closure(self.conn, self.date_iso, restants, encaisse, self.v_comment.get())
        except ss.SalesError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        messagebox.showinfo("Clôture", "Clôture enregistrée.")
        self.on_saved()
        self.load()


class HistoryTab(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent, padding=10)
        self.conn = conn
        columns = [("date", "Date", 110, "w"), ("theo", "Théorique", 120, "e"), ("benef", "Bénéfice", 120, "e"),
                   ("enc", "Encaissé", 120, "e"), ("ecart", "Écart", 100, "e")]
        self.table = SortableTree(self, columns)
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<Double-1>", lambda e: self.details())
        ttk.Label(self, text="Double-cliquez sur une ligne pour voir le détail par produit.").pack(anchor="w", pady=6)
        self.refresh()

    def refresh(self):
        self.table.clear()
        for c in ss.list_closures(self.conn):
            enc = "—" if c["montant_encaisse"] is None else fmt_money(c["montant_encaisse"])
            ecart = "—" if c["ecart_caisse"] is None else f"{c['ecart_caisse']:+d}"
            self.table.insert(
                (iso_to_fr(c["date_cloture"]), fmt_money(c["total_theorique"]), fmt_money(c["total_benefice"]), enc, ecart),
                iid=str(c["id"]),
            )

    def details(self):
        iid = self.table.selected()
        if iid is not None:
            DetailsDialog(self, self.conn, int(iid))


class DetailsDialog(Dialog):
    def __init__(self, parent, conn, closure_id):
        closure = ss.get_closure_by_id(conn, closure_id)
        super().__init__(parent, f"Clôture du {iso_to_fr(closure['date_cloture'])}")
        columns = [("nom", "Produit", 200, "w"), ("ouv", "Ouverture", 90, "e"), ("rest", "Restant", 90, "e"),
                   ("vendu", "Vendu", 80, "e"), ("pv", "Prix vente", 90, "e"), ("montant", "Montant", 100, "e"),
                   ("benef", "Bénéfice", 100, "e")]
        table = SortableTree(self.body, columns, height=14)
        table.pack(fill="both", expand=True)
        for l in ss.get_closure_lines(conn, closure_id):
            table.insert((l["nom"], fmt_qty(l["stock_ouverture"]), fmt_qty(l["stock_cloture"]),
                          fmt_qty(l["quantite_vendue"]), fmt_money(l["prix_vente_unit"]),
                          fmt_money(l["montant_theorique"]), fmt_money(l["benefice"])))
        ttk.Button(self.body, text="Fermer", style="Accent.TButton", command=self.destroy).pack(pady=(10, 0))
        self.show()