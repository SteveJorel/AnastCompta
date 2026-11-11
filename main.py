import sys
import tkinter as tk
from tkinter import ttk
import sqlite3

VERSION = "0.1.0"


def main():
    root = tk.Tk()
    root.title(f"AnastCompta v{VERSION}")
    root.geometry("420x220")

    ttk.Label(root, text="AnastCompta", font=("Segoe UI", 18, "bold")).pack(pady=(30, 5))
    ttk.Label(root, text=f"Version {VERSION}").pack()
    ttk.Label(root, text=f"SQLite {sqlite3.sqlite_version} | Python {sys.version.split()[0]}").pack(pady=10)
    ttk.Button(root, text="Fermer", command=root.destroy).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()