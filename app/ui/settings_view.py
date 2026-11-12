import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.services import auth_service as auth
from app.services import backup_service
from app.services import product_service as ps
from app.services import settings_service
from app.ui.widgets import ScrollableFrame, SortableTree, labeled_entry


class SettingsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=20)
        self.app, self.conn = app, app.conn
        ttk.Label(self, text="Paramètres", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True, pady=10)
        body = scroll.inner
        self._shop_section(body)
        self._password_section(body)
        self._units_section(body)
        self._backup_section(body)

    @staticmethod
    def _section(parent, title):
        box = ttk.LabelFrame(parent, text=title, padding=12)
        box.pack(fill="x", pady=8, padx=(0, 12))
        return box

    # --- Boutique ---
    def _shop_section(self, parent):
        box = self._section(parent, "Boutique")
        self.v_shop = tk.StringVar(value=settings_service.get(self.conn, "nom_boutique", ""))
        self.v_devise = tk.StringVar(value=settings_service.get(self.conn, "devise", "FCFA"))
        labeled_entry(box, "Nom de la boutique", 0, self.v_shop)
        labeled_entry(box, "Devise", 1, self.v_devise, width=10)
        ttk.Button(box, text="Enregistrer", command=self.save_shop).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def save_shop(self):
        try:
            settings_service.save_shop(self.conn, self.v_shop.get(), self.v_devise.get())
        except settings_service.SettingsError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        messagebox.showinfo("Paramètres", "Paramètres enregistrés.")

    # --- Mot de passe ---
    def _password_section(self, parent):
        box = self._section(parent, "Changer le mot de passe")
        self.v_old, self.v_new, self.v_new2 = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for row, (label, var) in enumerate([
            ("Ancien mot de passe", self.v_old), ("Nouveau mot de passe", self.v_new),
            ("Confirmer le nouveau", self.v_new2),
        ]):
            labeled_entry(box, label, row, var).config(show="•")
        ttk.Button(box, text="Changer le mot de passe", command=self.change_password).grid(
            row=3, column=0, sticky="w", pady=(8, 0))

    def change_password(self):
        if self.v_new.get() != self.v_new2.get():
            messagebox.showerror("Erreur", "Les deux nouveaux mots de passe ne sont pas identiques.")
            return
        try:
            auth.change_password(self.conn, self.v_old.get(), self.v_new.get())
        except auth.AuthError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        for var in (self.v_old, self.v_new, self.v_new2):
            var.set("")
        messagebox.showinfo("Mot de passe", "Mot de passe modifié.")

    # --- Unités ---
    def _units_section(self, parent):
        box = self._section(parent, "Unités de mesure")
        self.units_table = SortableTree(
            box, [("nom", "Unité", 200, "w"), ("dec", "Décimales autorisées", 170, "center")], height=5)
        self.units_table.pack(fill="x")
        row = ttk.Frame(box)
        row.pack(fill="x", pady=(8, 0))
        self.v_unit, self.v_dec = tk.StringVar(), tk.BooleanVar(value=False)
        ttk.Entry(row, textvariable=self.v_unit, width=20).pack(side="left")
        ttk.Checkbutton(row, text="Autoriser les décimales", variable=self.v_dec).pack(side="left", padx=10)
        ttk.Button(row, text="Ajouter l'unité", command=self.add_unit).pack(side="left")
        self.refresh_units()

    def refresh_units(self):
        self.units_table.clear()
        for u in ps.list_units(self.conn):
            self.units_table.insert((u["libelle"], "Oui" if u["decimales_autorisees"] else "Non"))

    def add_unit(self):
        try:
            ps.add_unit(self.conn, self.v_unit.get(), self.v_dec.get())
        except ps.ProductError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self.v_unit.set("")
        self.v_dec.set(False)
        self.refresh_units()

    # --- Sauvegarde et maintenance ---
    def _backup_section(self, parent):
        box = self._section(parent, "Sauvegarde et maintenance")
        ttk.Label(
            box, wraplength=650,
            text=("Une sauvegarde automatique est faite à la fermeture du logiciel (les 10 dernières sont "
                  f"conservées) dans :\n{backup_service.backup_dir()}"),
        ).pack(anchor="w")
        row = ttk.Frame(box)
        row.pack(fill="x", pady=(10, 0))
        ttk.Button(row, text="Sauvegarder maintenant…", command=self.backup_now).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Restaurer une sauvegarde…", command=self.restore).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Ouvrir le dossier", command=self.open_folder).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Vérifier l'intégrité du stock", command=self.check_integrity).pack(side="left")

    def backup_now(self):
        folder = filedialog.askdirectory(title="Dossier de sauvegarde (ex. clé USB)")
        if not folder:
            return
        try:
            path = backup_service.create_backup(self.conn, folder)
        except Exception as exc:
            messagebox.showerror("Erreur", f"Sauvegarde impossible :\n{exc}")
            return
        messagebox.showinfo("Sauvegarde", f"Sauvegarde créée :\n{path}")

    def restore(self):
        path = filedialog.askopenfilename(
            title="Choisir la sauvegarde à restaurer", initialdir=str(backup_service.backup_dir()),
            filetypes=[("Sauvegarde AnastCompta", "*.db"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Restaurer",
            "Toutes les données actuelles seront remplacées par celles de la sauvegarde.\n"
            "Une copie de sécurité des données actuelles est créée automatiquement avant.\n\nContinuer ?",
            icon="warning",
        ):
            return
        try:
            backup_service.restore_backup(self.conn, path)
        except backup_service.BackupError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        messagebox.showinfo("Restauration", "Restauration terminée. Veuillez vous reconnecter.")
        self.app.restart_session()

    def open_folder(self):
        try:
            os.startfile(str(backup_service.backup_dir()))
        except OSError as exc:
            messagebox.showerror("Erreur", str(exc))

    def check_integrity(self):
        problems = ps.check_stock_integrity(self.conn)
        if not problems:
            messagebox.showinfo("Intégrité", "Aucune anomalie : le stock de chaque produit correspond à "
                                             "l'historique de ses mouvements.")
            return
        names = "\n".join(f"- {p['nom']} : stock {p['stock']:g}, historique {p['somme']:g}" for p in problems[:10])
        messagebox.showwarning("Intégrité", f"{len(problems)} produit(s) incohérent(s) :\n{names}")