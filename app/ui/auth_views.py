import tkinter as tk
from tkinter import ttk, messagebox

from app.services import auth_service as auth
from app.ui import theme


class BaseView(ttk.Frame):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.card = tk.Frame(
            self, bg=theme.SURFACE, highlightbackground=theme.BORDER, highlightthickness=1, padx=36, pady=28
        )
        self.card.place(relx=0.5, rely=0.5, anchor="center")

    def add_title(self, text, subtitle=""):
        ttk.Label(self.card, text="AnastCompta", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(self.card, text=text, style="CardHeading.TLabel").pack(anchor="w", pady=(4, 2))
        if subtitle:
            ttk.Label(self.card, text=subtitle, style="CardText.TLabel", wraplength=340, justify="left").pack(
                anchor="w", pady=(0, 4))

    def field(self, label, secret=False):
        ttk.Label(self.card, text=label, style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        entry = ttk.Entry(self.card, show="•" if secret else "", width=34)
        entry.pack(fill="x", pady=(3, 0))
        return entry


class CreateAccountView(BaseView):
    def __init__(self, app):
        super().__init__(app)
        self.add_title("Créer votre compte", "Ce compte unique protège l'accès à vos données.")
        self.nom = self.field("Nom du responsable")
        self.user = self.field("Nom d'utilisateur")
        self.pwd = self.field("Mot de passe (6 caractères minimum)", secret=True)
        self.pwd2 = self.field("Confirmer le mot de passe", secret=True)
        ttk.Button(self.card, text="Créer le compte", style="Accent.TButton", command=self.submit).pack(
            fill="x", pady=(20, 0))
        self.pwd2.bind("<Return>", lambda e: self.submit())
        self.nom.focus()

    def submit(self):
        if self.pwd.get() != self.pwd2.get():
            messagebox.showerror("Erreur", "Les deux mots de passe ne sont pas identiques.")
            return
        try:
            code = auth.create_user(self.app.conn, self.nom.get(), self.user.get(), self.pwd.get())
        except auth.AuthError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self.app.show_recovery_code(code)
        self.app.show_main()


class LoginView(BaseView):
    def __init__(self, app):
        super().__init__(app)
        self._locked = False
        self.add_title("Connexion", "Entrez vos identifiants pour accéder à votre boutique.")
        self.user = self.field("Nom d'utilisateur")
        self.pwd = self.field("Mot de passe", secret=True)
        self.msg = ttk.Label(self.card, text="", style="CardError.TLabel", wraplength=340)
        self.msg.pack(anchor="w", pady=(8, 0))
        self.btn = ttk.Button(self.card, text="Se connecter", style="Accent.TButton", command=self.submit)
        self.btn.pack(fill="x", pady=(12, 0))
        ttk.Button(self.card, text="Mot de passe oublié ?", style="Link.TButton", command=app.show_recovery).pack(
            pady=(8, 0))
        self.pwd.bind("<Return>", lambda e: self.submit())
        self.user.focus()
        self.refresh_lock()

    def refresh_lock(self):
        if not self.winfo_exists():
            return
        remaining = self.app.throttle.remaining()
        if remaining > 0:
            self._locked = True
            self.btn.state(["disabled"])
            self.msg.config(text=f"Trop de tentatives. Réessayez dans {remaining} s.")
            self.after(1000, self.refresh_lock)
        elif self._locked:
            self._locked = False
            self.btn.state(["!disabled"])
            self.msg.config(text="")

    def submit(self):
        if self.app.throttle.remaining() > 0:
            return
        if auth.authenticate(self.app.conn, self.user.get(), self.pwd.get()):
            self.app.throttle.reset()
            self.app.show_main()
            return
        self.app.throttle.register_failure()
        self.pwd.delete(0, "end")
        if self.app.throttle.remaining() > 0:
            self.refresh_lock()
        else:
            self.msg.config(text="Nom d'utilisateur ou mot de passe incorrect.")


class RecoveryView(BaseView):
    def __init__(self, app):
        super().__init__(app)
        self.add_title("Mot de passe oublié", "Saisissez le code de récupération remis à la création du compte.")
        self.code = self.field("Code de récupération")
        self.pwd = self.field("Nouveau mot de passe", secret=True)
        self.pwd2 = self.field("Confirmer le nouveau mot de passe", secret=True)
        ttk.Button(self.card, text="Réinitialiser", style="Accent.TButton", command=self.submit).pack(
            fill="x", pady=(20, 0))
        ttk.Button(self.card, text="Retour", command=app.show_login).pack(fill="x", pady=(8, 0))
        self.code.focus()

    def submit(self):
        if self.pwd.get() != self.pwd2.get():
            messagebox.showerror("Erreur", "Les deux mots de passe ne sont pas identiques.")
            return
        try:
            new_code = auth.reset_password_with_code(self.app.conn, self.code.get(), self.pwd.get())
        except auth.AuthError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self.app.show_recovery_code(new_code, renewed=True)
        self.app.show_login()