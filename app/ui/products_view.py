import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from app.services import product_service as ps
from app.ui.widgets import Dialog, SortableTree, labeled_entry
from app.utils.format import fmt_money, fmt_qty, parse_amount, parse_quantity


class ProductsView(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent, padding=20)
        self.conn = conn
        ttk.Label(self, text="Produits", font=("Segoe UI", 18, "bold")).pack(anchor="w")

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=10)
        self.search = tk.StringVar()
        self.show_inactive = tk.BooleanVar(value=False)
        ttk.Label(bar, text="Rechercher :").pack(side="left")
        ttk.Entry(bar, textvariable=self.search, width=22).pack(side="left", padx=6)
        ttk.Checkbutton(
            bar, text="Afficher les produits désactivés", variable=self.show_inactive, command=self.refresh
        ).pack(side="left", padx=10)

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 10))
        for text, cmd in [
            ("Nouveau produit", self.new_product),
            ("Modifier", self.edit_product),
            ("Réapprovisionner", lambda: self.stock_action("restock")),
            ("Ajuster le stock", lambda: self.stock_action("adjust")),
            ("Déclarer une perte", lambda: self.stock_action("loss")),
            ("Activer / Désactiver", self.toggle_active),
        ]:
            ttk.Button(actions, text=text, command=cmd).pack(side="left", padx=(0, 6))

        columns = [
            ("nom", "Produit", 220, "w"), ("unite", "Unité", 70, "center"), ("stock", "Stock", 80, "e"),
            ("achat", "Prix d'achat", 100, "e"), ("vente", "Prix de vente", 100, "e"),
            ("marge", "Marge/unité", 100, "e"), ("taux", "Taux", 70, "e"),
            ("benef", "Bénéfice prévisionnel", 150, "e"),
        ]
        self.table = SortableTree(self, columns)
        self.table.pack(fill="both", expand=True)
        self.table.tree.tag_configure("low", foreground="#b00020")
        self.table.tree.tag_configure("inactive", foreground="#888888")
        self.total_label = ttk.Label(self, font=("Segoe UI", 11, "bold"))
        self.total_label.pack(anchor="e", pady=(10, 0))
        self.search.trace_add("write", lambda *a: self.refresh())
        self.refresh()

    def refresh(self):
        self.table.clear()
        total = 0
        for p in ps.list_products(self.conn, self.search.get(), self.show_inactive.get()):
            marge, taux = ps.margin(p["prix_achat"], p["prix_vente"])
            benef = ps.forecast_profit(p)
            tags = []
            if not p["actif"]:
                tags.append("inactive")
            else:
                total += benef
                if p["seuil_alerte"] is not None and p["quantite_stock"] <= p["seuil_alerte"]:
                    tags.append("low")
            self.table.insert(
                (p["nom"], p["unite"], fmt_qty(p["quantite_stock"]), fmt_money(p["prix_achat"]),
                 fmt_money(p["prix_vente"]), fmt_money(marge), "—" if taux is None else f"{taux:.0f} %",
                 fmt_money(benef)),
                iid=str(p["id"]), tags=tuple(tags),
            )
        self.total_label.config(text=f"Bénéfice prévisionnel total (stock actuel) : {fmt_money(total)}")

    def _selected(self):
        iid = self.table.selected()
        if iid is None:
            messagebox.showinfo("Produits", "Sélectionnez d'abord un produit dans la liste.")
            return None
        return ps.get_product(self.conn, int(iid))

    def new_product(self):
        ProductDialog(self, self.conn, None, self.refresh)

    def edit_product(self):
        product = self._selected()
        if product:
            ProductDialog(self, self.conn, product, self.refresh)

    def stock_action(self, mode):
        product = self._selected()
        if product:
            StockDialog(self, self.conn, product, mode, self.refresh)

    def toggle_active(self):
        product = self._selected()
        if not product:
            return
        if product["actif"] and not messagebox.askyesno(
            "Désactiver", f"Désactiver « {product['nom']} » ? Il n'apparaîtra plus dans la clôture."
        ):
            return
        ps.set_active(self.conn, product["id"], not product["actif"])
        self.refresh()


class ProductDialog(Dialog):
    def __init__(self, parent, conn, product, on_done):
        super().__init__(parent, "Nouveau produit" if product is None else "Modifier le produit")
        self.conn, self.product, self.on_done = conn, product, on_done
        b = self.body
        self.v_nom = tk.StringVar(value=product["nom"] if product else "")
        self.v_stock = tk.StringVar(value="0")
        self.v_achat = tk.StringVar(value=str(product["prix_achat"]) if product else "")
        self.v_vente = tk.StringVar(value=str(product["prix_vente"]) if product else "")
        seuil = product["seuil_alerte"] if product and product["seuil_alerte"] is not None else ""
        self.v_seuil = tk.StringVar(value=fmt_qty(seuil) if seuil != "" else "")
        self.v_marge = tk.StringVar(value="Marge : —")

        self.nom_entry = labeled_entry(b, "Nom du produit", 0, self.v_nom)
        ttk.Label(b, text="Unité de mesure").grid(row=1, column=0, sticky="w", pady=6)
        self.unit_box = ttk.Combobox(b, state="readonly", width=18)
        self.unit_box.grid(row=1, column=1, sticky="w", pady=6)
        ttk.Button(b, text="+ Unité", command=self.add_unit).grid(row=1, column=2, padx=6)
        self._load_units(product["unite"] if product else None)

        if product is None:
            labeled_entry(b, "Stock initial", 2, self.v_stock)
        else:
            ttk.Label(
                b, text=f"Stock actuel : {fmt_qty(product['quantite_stock'])} (à modifier via « Ajuster le stock »)"
            ).grid(row=2, column=0, columnspan=3, sticky="w", pady=6)
        labeled_entry(b, "Prix d'achat unitaire", 3, self.v_achat)
        labeled_entry(b, "Prix de vente unitaire", 4, self.v_vente)
        labeled_entry(b, "Seuil d'alerte (optionnel)", 5, self.v_seuil)
        ttk.Label(b, textvariable=self.v_marge, font=("Segoe UI", 11, "bold")).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        ttk.Button(b, text="Enregistrer", command=self.submit).grid(row=7, column=0, columnspan=3, pady=(16, 0))

        self.v_achat.trace_add("write", self.update_margin)
        self.v_vente.trace_add("write", self.update_margin)
        self.update_margin()
        self.bind("<Return>", lambda e: self.submit())
        self.nom_entry.focus()
        self.show()

    def _load_units(self, selected=None):
        self.units = ps.list_units(self.conn)
        labels = [u["libelle"] for u in self.units]
        self.unit_box["values"] = labels
        self.unit_box.current(labels.index(selected) if selected in labels else 0)

    def add_unit(self):
        name = simpledialog.askstring("Nouvelle unité", "Nom de l'unité (ex. sac, bouteille, carton) :", parent=self)
        if not name:
            return
        decimals = messagebox.askyesno("Nouvelle unité", "Autoriser les quantités décimales (ex. 2,5) ?", parent=self)
        try:
            ps.add_unit(self.conn, name, decimals)
        except ps.ProductError as exc:
            messagebox.showerror("Erreur", str(exc), parent=self)
            return
        self._load_units(name.strip())

    def update_margin(self, *args):
        try:
            achat, vente = parse_amount(self.v_achat.get()), parse_amount(self.v_vente.get())
        except ValueError:
            self.v_marge.set("Marge : —")
            return
        marge, taux = ps.margin(achat, vente)
        text = f"Marge par unité : {fmt_money(marge)}"
        if taux is not None:
            text += f" ({taux:.0f} %)"
        if marge < 0:
            text += " — vente sous le prix d'achat"
        self.v_marge.set(text)

    def submit(self):
        try:
            unit = self.units[self.unit_box.current()]
            achat, vente = parse_amount(self.v_achat.get()), parse_amount(self.v_vente.get())
            seuil_text = self.v_seuil.get().strip()
            seuil = parse_quantity(seuil_text) if seuil_text else None
            if vente < achat and not messagebox.askyesno(
                "Prix de vente", "Le prix de vente est inférieur au prix d'achat. Continuer ?", parent=self
            ):
                return
            if self.product is None:
                stock = parse_quantity(self.v_stock.get() or "0")
                ps.create_product(self.conn, self.v_nom.get(), unit["id"], stock, achat, vente, seuil)
            else:
                ps.update_product(self.conn, self.product["id"], self.v_nom.get(), unit["id"], achat, vente, seuil)
        except (ValueError, ps.ProductError) as exc:
            messagebox.showerror("Erreur", str(exc), parent=self)
            return
        self.on_done()
        self.destroy()


class StockDialog(Dialog):
    MODES = {
        "restock": ("Réapprovisionner", "Quantité reçue"),
        "adjust": ("Ajuster le stock", "Nouveau stock réel"),
        "loss": ("Déclarer une perte", "Quantité perdue"),
    }

    def __init__(self, parent, conn, product, mode, on_done):
        title, qty_label = self.MODES[mode]
        super().__init__(parent, f"{title} — {product['nom']}")
        self.conn, self.product, self.mode, self.on_done = conn, product, mode, on_done
        b = self.body
        ttk.Label(b, text=f"Stock actuel : {fmt_qty(product['quantite_stock'])} {product['unite']}").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self.qty = labeled_entry(b, f"{qty_label} ({product['unite']})", 1)
        row = 2
        self.price = None
        if mode == "restock":
            self.price = labeled_entry(b, "Nouveau prix d'achat (optionnel)", row)
            row += 1
        self.note = labeled_entry(b, "Note (optionnel)", row)
        ttk.Button(b, text="Valider", command=self.submit).grid(row=row + 1, column=0, columnspan=2, pady=(14, 0))
        self.bind("<Return>", lambda e: self.submit())
        self.qty.focus()
        self.show()

    def submit(self):
        try:
            qty = parse_quantity(self.qty.get())
            note = self.note.get().strip()
            pid = self.product["id"]
            if self.mode == "restock":
                price_text = self.price.get().strip()
                ps.restock(self.conn, pid, qty, parse_amount(price_text) if price_text else None, note)
            elif self.mode == "adjust":
                ps.adjust_stock(self.conn, pid, qty, note)
            else:
                ps.declare_loss(self.conn, pid, qty, note)
        except (ValueError, ps.ProductError) as exc:
            messagebox.showerror("Erreur", str(exc), parent=self)
            return
        self.on_done()
        self.destroy()