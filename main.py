import logging
import sys
import tkinter as tk
from tkinter import messagebox

from app.config import get_data_dir
from app.db.schema import init_db
from app.services import backup_service
from app.ui.app import App


def main():
    logging.basicConfig(
        filename=get_data_dir() / "anastcompta.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8",
    )
    try:
        conn = init_db()
    except Exception as exc:
        logging.exception("Ouverture de la base impossible")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erreur", f"Impossible d'ouvrir la base de données :\n{exc}")
        sys.exit(1)

    App(conn).mainloop()
    try:
        backup_service.auto_backup(conn)
    except Exception:
        logging.exception("Sauvegarde automatique impossible")
    conn.close()


if __name__ == "__main__":
    main()