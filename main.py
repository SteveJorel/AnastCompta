import sys
import tkinter as tk
from tkinter import messagebox

from app.db.schema import init_db
from app.ui.app import App


def main():
    try:
        conn = init_db()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erreur", f"Impossible d'ouvrir la base de données :\n{exc}")
        sys.exit(1)

    App(conn).mainloop()
    conn.close()


if __name__ == "__main__":
    main()