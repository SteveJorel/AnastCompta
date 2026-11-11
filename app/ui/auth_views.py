from tkinter import ttk, messagebox

from app.services import auth_service as auth


class BaseView(ttk.Frame):
    def __init__(self, app):
        super().__init__(app, padding=30)
        self.app = app

    def add_title(self, text):
        ttk.Label(self, text=text, font=("Segoe UI", 18, "bold")).pack(pady=(10, 20))

    def field(self, label, secret=False):
        ttk.Label(self, text=label).pack(anchor="w")
        entry = ttk.Entry(self, show="•" if secret else "", width=34)
        entry.pack(fill="x", pady=(2, 12))
        return entry


class CreateAccountView(BaseView):
    def __init__(self, app):
        super().__init__(app)
        self.add_title("Créer votre compte")
        ttk.Label(
            self, text="Ce compte unique protège l'accès à vos données.", wraplength=360
        ).pack(pady=(0, 15))
        self.nom = self.field("Nom du responsable")
        self.user = self.field("Nom d'utilisateur")
        self.pwd = self.field("Mot de passe (6 caractères minimum)", secret=True)
        self.pwd2 = self.field("Confirmer le mot de passe", secret=True)
        ttk.Button(self, text="Créer le compte", command=self.submit).pack(pady=10)
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
        self.add_title("Connexion")
        self.user = self.field("Nom d'utilisateur")
        self.pwd = self.field("Mot de passe", secret=True)
        self.msg = ttk.Label(self, text="", foreground="#b00020", wraplength=360)
        self.msg.pack()
        self.btn = ttk.Button(self, text="Se connecter", command=self.submit)
        self.btn.pack(pady=10)
        ttk.Button(self, text="Mot de passe oublié ?", command=app.show_recovery).pack()
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
        self.add_title("Mot de passe oublié")
        ttk.Label(
            self,
            text="Saisissez le code de récupération remis à la création du compte.",
            wraplength=360,
        ).pack(pady=(0, 15))
        self.code = self.field("Code de récupération")
        self.pwd = self.field("Nouveau mot de passe", secret=True)
        self.pwd2 = self.field("Confirmer le nouveau mot de passe", secret=True)
        ttk.Button(self, text="Réinitialiser", command=self.submit).pack(pady=10)
        ttk.Button(self, text="Retour", command=app.show_login).pack()
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


class MainView(BaseView):
    """Écran provisoire : sera remplacé par la vraie fenêtre principale aux étapes suivantes."""

    def __init__(self, app):
        super().__init__(app)
        user = auth.get_user(app.conn)
        self.add_title(f"Bienvenue, {user['nom_complet']}")
        ttk.Label(self, text="Les modules arrivent dans les prochaines étapes.").pack(pady=10)
        ttk.Button(self, text="Verrouiller", command=app.show_login).pack(pady=10)