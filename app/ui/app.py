import logging
import tkinter as tk
from tkinter import ttk, messagebox

from app.config import resource_path
from app.services import auth_service as auth
from app.ui.auth_views import CreateAccountView, LoginView, RecoveryView
from app.ui.main_window import MainWindow


class App(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.throttle = auth.LoginThrottle()
        self.title("AnastCompta")
        try:
            self.iconbitmap(str(resource_path("assets/app.ico")))
        except tk.TclError:
            pass
        style = ttk.Style()
        style.configure(".", font=("Segoe UI", 11))
        style.configure("Toolbutton", padding=(10, 8))
        self._current = None
        self.restart_session()

    def restart_session(self):
        if auth.user_exists(self.conn):
            self.show_login()
        else:
            self.show_create_account()

    def report_callback_exception(self, exc, val, tb):
        logging.error("Erreur non gérée", exc_info=(exc, val, tb))
        messagebox.showerror("Erreur", f"Une erreur inattendue s'est produite :\n{val}")

    def _show(self, view_class, size, minsize):
        if self._current is not None:
            self._current.destroy()
        self.geometry(size)
        self.minsize(*minsize)
        self._current = view_class(self)
        self._current.pack(fill="both", expand=True)

    def show_create_account(self):
        self._show(CreateAccountView, "460x600", (460, 600))

    def show_login(self):
        self._show(LoginView, "460x600", (460, 600))

    def show_recovery(self):
        self._show(RecoveryView, "460x600", (460, 600))

    def show_main(self):
        self._show(MainWindow, "1150x700", (950, 600))

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