import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox

from app.services import income_service as inc
from app.ui.widgets import SortableTree
from app.utils.format import fmt_money, fr_to_iso, iso_to_fr, parse_amount, today_iso


class IncomeView(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent, padding=20)
        self.conn = conn
        self.categories = inc.list_categories(conn)
        self.labels = [c["libelle"] for c in self.categories]
        self.editing_id = None

        ttk.Label(self, text="Recettes annexes", font=("Segoe UI", 18, "bold")).pack(anchor="w")

        form = ttk.LabelFrame(self, text="Saisie d'une recette", padding=12)
        form.pack(fill="x", pady=10)
        self.v_date = tk.StringVar(value=iso_to_fr(today_iso()))
        self.v_montant, self.v_note = tk.StringVar(), tk.StringVar()
        ttk.Label(form, text="Activité").grid(row=0, column=0, sticky="w")
        self.cat_box = ttk.Combobox(form, values=self.labels, state="readonly", width=20)
        self.cat_box.current(0)
        self.cat_box.grid(row=1, column=0, padx=(0, 12))
        ttk.Label(form, text="Date").grid(row=0, column=1, sticky="w")
        ttk.Entry(form, textvariable=self.v_date, width=12).grid(row=1, column=1, padx=(0, 12))
        ttk.Label(form, text="Montant").grid(row=0, column=2, sticky="w")
        montant_entry = ttk.Entry(form, textvariable=self.v_montant, width=14)
        montant_entry.grid(row=1, column=2, padx=(0, 12))
        ttk.Label(form, text="Note (optionnel)").grid(row=0, column=3, sticky="w")
        ttk.Entry(form, textvariable=self.v_note, width=30).grid(row=1, column=3, padx=(0, 12))
        self.submit_btn = ttk.Button(form, text="Ajouter", command=self.submit)
        self.submit_btn.grid(row=1, column=4, padx=(0, 6))
        ttk.Button(form, text="Annuler", command=self.reset_form).grid(row=1, column=5)
        montant_entry.bind("<Return>", lambda e: self.submit())

        flt = ttk.Frame(self)
        flt.pack(fill="x", pady=(5, 8))
        self.f_cat = ttk.Combobox(flt, values=["Toutes"] + self.labels, state="readonly", width=20)
        self.f_cat.current(0)
        self.f_start = tk.StringVar(value=iso_to_fr(date.today().replace(day=1).isoformat()))
        self.f_end = tk.StringVar(value=iso_to_fr(today_iso()))
        ttk.Label(flt, text="Afficher :").pack(side="left")
        self.f_cat.pack(side="left", padx=6)
        ttk.Label(flt, text="du").pack(side="left")
        ttk.Entry(flt, textvariable=self.f_start, width=12).pack(side="left", padx=6)
        ttk.Label(flt, text="au").pack(side="left")
        ttk.Entry(flt, textvariable=self.f_end, width=12).pack(side="left", padx=6)
        ttk.Button(flt, text="Filtrer", command=self.refresh).pack(side="left", padx=6)

        columns = [("date", "Date", 110, "w"), ("act", "Activité", 170, "w"), ("montant", "Montant", 120, "e"),
                   ("note", "Note", 350, "w")]
        self.table = SortableTree(self, columns)
        self.table.pack(fill="both", expand=True)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Modifier la sélection", command=self.edit_selected).pack(side="left", padx=(0, 6))
        ttk.Button(bottom, text="Supprimer la sélection", command=self.delete_selected).pack(side="left")
        self.total_label = ttk.Label(bottom, font=("Segoe UI", 11, "bold"))
        self.total_label.pack(side="right")
        self.refresh()

    def refresh(self):
        try:
            start, end = fr_to_iso(self.f_start.get()), fr_to_iso(self.f_end.get())
        except ValueError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        index = self.f_cat.current()
        cat_id = None if index <= 0 else self.categories[index - 1]["id"]
        self.table.clear()
        total = 0
        for r in inc.list_incomes(self.conn, cat_id, start, end):
            total += r["montant"]
            self.table.insert((iso_to_fr(r["date_recette"]), r["activite"], fmt_money(r["montant"]), r["note"] or ""),
                              iid=str(r["id"]))
        self.total_label.config(text=f"Total de la période : {fmt_money(total)}")

    def reset_form(self):
        self.editing_id = None
        self.v_date.set(iso_to_fr(today_iso()))
        self.v_montant.set("")
        self.v_note.set("")
        self.submit_btn.config(text="Ajouter")

    def submit(self):
        try:
            cat = self.categories[self.cat_box.current()]
            date_iso, montant = fr_to_iso(self.v_date.get()), parse_amount(self.v_montant.get())
            if self.editing_id is None:
                inc.add_income(self.conn, cat["id"], date_iso, montant, self.v_note.get())
            else:
                inc.update_income(self.conn, self.editing_id, cat["id"], date_iso, montant, self.v_note.get())
        except (ValueError, inc.IncomeError) as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self.reset_form()
        self.refresh()

    def edit_selected(self):
        iid = self.table.selected()
        if iid is None:
            messagebox.showinfo("Recettes", "Sélectionnez d'abord une ligne dans la liste.")
            return
        row = inc.get_income(self.conn, int(iid))
        self.editing_id = row["id"]
        self.cat_box.current([c["id"] for c in self.categories].index(row["categorie_id"]))
        self.v_date.set(iso_to_fr(row["date_recette"]))
        self.v_montant.set(str(row["montant"]))
        self.v_note.set(row["note"] or "")
        self.submit_btn.config(text="Enregistrer")

    def delete_selected(self):
        iid = self.table.selected()
        if iid is None:
            messagebox.showinfo("Recettes", "Sélectionnez d'abord une ligne dans la liste.")
            return
        if messagebox.askyesno("Supprimer", "Supprimer définitivement cette recette ?"):
            inc.delete_income(self.conn, int(iid))
            self.reset_form()
            self.refresh()