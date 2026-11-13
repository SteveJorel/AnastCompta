import tkinter as tk

from app.ui import theme


class Logo(tk.Canvas):
    """Logo AnastCompta dessiné par le code : aucun fichier image à embarquer dans le .exe."""

    BARS = [(0.18, 0.34, 0.52), (0.42, 0.58, 0.36), (0.66, 0.82, 0.22)]  # (x début, x fin, haut)

    def __init__(self, parent, size=56, background=theme.SURFACE):
        super().__init__(parent, width=size, height=size, highlightthickness=0, borderwidth=0,
                         background=background)
        s = size - 1
        self._rounded(0, 0, s, s, s * 0.18, theme.ACCENT)
        for x0, x1, top in self.BARS:
            self.create_rectangle(s * x0, s * top, s * x1, s * 0.78, fill="#ffffff", outline="")
        self.create_rectangle(s * 0.14, s * 0.80, s * 0.86, s * 0.84, fill="#ffffff", outline="")

    def _rounded(self, x0, y0, x1, y1, r, color):
        d = 2 * r
        for ox, oy in [(x0, y0), (x1 - d, y0), (x0, y1 - d), (x1 - d, y1 - d)]:
            self.create_oval(ox, oy, ox + d, oy + d, fill=color, outline="")
        self.create_rectangle(x0 + r, y0, x1 - r, y1, fill=color, outline="")
        self.create_rectangle(x0, y0 + r, x1, y1 - r, fill=color, outline="")
        