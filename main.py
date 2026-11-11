import sys
import tkinter as tk
from tkinter import ttk, messagebox

from app.config import VERSION, get_db_path
from app.db.schema import init_db


def main():
    root = tk.Tk()
    root.title(f"AnastCompta v{VERSION}")
    root.geometry("520x240")

    try:
        conn = init_db()
        version_db = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
    except Exception as exc:
        messagebox.showerror("Erreur", f"Impossible d'ouvrir la base de données :\n{exc}")
        root.destroy()
        sys.exit(1)

    ttk.Label(root, text="AnastCompta", font=("Segoe UI", 18, "bold")).pack(pady=(30, 5))
    ttk.Label(root, text=f"Version {VERSION} | Base v{version_db}").pack()
    ttk.Label(root, text=str(get_db_path()), wraplength=480).pack(pady=10)
    ttk.Button(root, text="Fermer", command=root.destroy).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()