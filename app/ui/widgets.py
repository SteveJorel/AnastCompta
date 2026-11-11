import tkinter as tk
from tkinter import ttk


class SortableTree(ttk.Frame):
    """Tableau avec défilement et tri par clic sur les en-têtes.
    columns : liste de (id, titre, largeur, alignement)."""

    def __init__(self, parent, columns, **tree_opts):
        super().__init__(parent)
        self.tree = ttk.Treeview(
            self, columns=[c[0] for c in columns], show="headings", selectmode="browse", **tree_opts
        )
        for cid, text, width, anchor in columns:
            self.tree.heading(cid, text=text, command=lambda c=cid: self.sort_by(c))
            self.tree.column(cid, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._reverse = {}

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def insert(self, values, iid=None, tags=()):
        self.tree.insert("", "end", iid=iid, values=values, tags=tags)

    def selected(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def sort_by(self, col):
        items = [(self.tree.set(i, col), i) for i in self.tree.get_children("")]

        def key(item):
            text = item[0].replace(" ", "").replace(",", ".").replace("%", "").replace("+", "")
            try:
                return (0, float(text), "")
            except ValueError:
                return (1, 0.0, item[0].lower())

        reverse = self._reverse.get(col, False)
        items.sort(key=key, reverse=reverse)
        for index, (_, iid) in enumerate(items):
            self.tree.move(iid, "", index)
        self._reverse[col] = not reverse


class ScrollableFrame(ttk.Frame):
    """Zone défilante : placer les widgets dans self.inner."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._window, width=e.width))
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._wheel, add="+")

    def _wheel(self, event):
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
            while widget is not None:
                if widget is self:
                    self.canvas.yview_scroll(int(-event.delta / 120), "units")
                    return
                widget = widget.master
        except tk.TclError:
            pass


class Dialog(tk.Toplevel):
    """Fenêtre modale : remplir self.body puis appeler self.show()."""

    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.body = ttk.Frame(self, padding=20)
        self.body.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda e: self.destroy())

    def show(self):
        self.update_idletasks()
        root = self.master.winfo_toplevel()
        x = root.winfo_rootx() + (root.winfo_width() - self.winfo_width()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.wait_visibility()
        self.grab_set()
        self.wait_window()


def labeled_entry(parent, label, row, var=None, width=28):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
    entry = ttk.Entry(parent, textvariable=var, width=width)
    entry.grid(row=row, column=1, sticky="ew", pady=6)
    return entry