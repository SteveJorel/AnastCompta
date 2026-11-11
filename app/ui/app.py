import tkinter as tk
from tkinter import ttk, messagebox

from app.services import auth_service as auth
from app.ui.auth_views import CreateAccountView, LoginView, RecoveryView, MainView


class App(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.throttle = auth.LoginThrottle()
        self.title("AnastCompta")
        self.geometry("460x600")
        ttk.Style().configure(".", font=("Segoe UI", 11))
        self._current = None
        if auth.user_exists(conn):
            self.show_login()
        else:
            self.show_create_account()

    def _show(self, view_class):
        if self._current is not None:
            self._current.destroy()
        self._current = view_class(self)
        self._current.pack(fill="both", expand=True)

    def show_create_account(self):
        self._show(CreateAccountView)

    def show_login(self):
        self._show(LoginView)

    def show_recovery(self):
        self._show(RecoveryView)

    def show_main(self):
        self._show(MainView)

    def show_recovery_code(self, code, renewed=False):
        self.clipboard_clear()
        self.clipboard_append(code)
        self.update()
        intro = "Votre NOUVEAU code de récupération" if renewed else "Votre code de récupération"
        messagebox.showinfo(
            "Code de récupération",
            f"{intro} :\n\n{code}\n\n"
            "Notez-le sur papier et gardez-le en lieu sûr : il permet de réinitialiser "
            "le mot de passe en cas d'oubli. Il est aussi copié dans le presse-papiers.",
        )