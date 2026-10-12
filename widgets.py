import os
import tkinter as tk
from tkinter import messagebox, ttk

import theme
from index import CATS, CAT_OF, cat

CAP = 50_000  # max rows shown; the type summary still counts every match
SORT = {"name": lambda t: t[0].lower(), "type": lambda t: t[2], "folder": lambda t: t[1].lower()}


class Hero(tk.Canvas):
    """Gradient banner with the app title."""

    H = 84

    def __init__(self, parent):
        super().__init__(parent, height=self.H, highlightthickness=0, bd=0)
        self.bind("<Configure>", self.paint)

    def paint(self, _=None):
        self.delete("all")
        w, steps = self.winfo_width(), 64
        for i in range(steps):
            col = "#%02x%02x%02x" % tuple(int(a + (b - a) * i / (steps - 1)) for a, b in zip((37, 99, 235), (124, 58, 237)))
            self.create_rectangle(w * i / steps, 0, w * (i + 1) / steps + 1, self.H, fill=col, outline=col)
        self.create_text(24, 34, anchor="w", text="\U0001F50D  File Search", fill="white", font=("Segoe UI Semibold", 20))
        self.create_text(28, 62, anchor="w", text="Find any file on any drive in an instant", fill="#dbeafe", font=("Segoe UI", 10))


class TypePanel(ttk.Frame):
    """Card listing the matched file types with counts; picking one filters the table."""

    def __init__(self, parent, on_pick):
        super().__init__(parent, style="Card.TFrame")
        self.on_pick, self.keys = on_pick, []
        ttk.Label(self, text="File types", font=("Segoe UI Semibold", 10), background=theme.CARD, padding=(10, 8)).pack(anchor="w")
        self.box = tk.Listbox(self, activestyle="none", exportselection=False, bd=0, highlightthickness=0, bg=theme.CARD, fg=theme.TXT,
                              selectbackground=theme.SEL, selectforeground=theme.TXT, font=("Segoe UI", 10))
        self.box.bind("<<ListboxSelect>>", self._pick)
        self.box.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def show(self, total, counts):
        self.keys = [k for k, _ in counts.most_common()]
        self.box.delete(0, "end")
        self.box.insert("end", f"✨  All types ({total:,})")
        for i, k in enumerate(self.keys, 1):
            icon, colour = cat(k)
            self.box.insert("end", f"{icon}  {k}  ({counts[k]:,})")
            self.box.itemconfig(i, foreground=colour)
        self.box.selection_set(0)

    def _pick(self, _):
        sel = self.box.curselection()
        if sel:
            self.on_pick(None if sel[0] == 0 else self.keys[sel[0] - 1])


class ResultsTable(ttk.Frame):
    """Sortable table of matches; click a folder path to open it, double-click a row to open the file."""

    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")
        self.found, self.view, self.ext = [], [], None
        self.sort_col, self.sort_rev = "name", False
        self.tree = t = ttk.Treeview(self, columns=("name", "type", "folder"), show="headings")
        for c, w in (("name", 260), ("type", 80), ("folder", 420)):
            t.heading(c, text=c.title(), command=lambda c=c: self.sort(c))
            t.column(c, width=w)
        t.tag_configure("odd", background="#f9fafb")
        for k, (_, colour, _) in CATS.items():
            t.tag_configure(k, foreground=colour)
        sb = ttk.Scrollbar(self, command=t.yview)
        t.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(fill="both", expand=True, padx=1, pady=1)

        t.bind("<Double-1>", lambda ev: self._open(ev, True))
        t.bind("<Button-1>", lambda ev: self._on_folder(ev) and self._open(ev, False), add="+")
        t.bind("<Motion>", lambda ev: t.config(cursor="hand2" if self._on_folder(ev) else ""))
        t.bind("<Button-3>", self._menu)
        t.bind("<Control-a>", lambda _: self.select_all() or "break")
        self.ctx = tk.Menu(self, tearoff=0)
        self.ctx.add_command(label="Open file", command=lambda: self._open(None, True))
        self.ctx.add_command(label="Open folder", command=lambda: self._open(None, False))

    # ---- data -----------------------------------------------------------
    def set_rows(self, found):
        self.found, self.ext = found, None
        return self.render()

    def filter(self, ext):
        self.ext = ext
        return self.render()

    def sort(self, col):
        self.sort_rev = not self.sort_rev if col == self.sort_col else False
        self.sort_col = col
        self.render()

    def render(self):
        """Redraw; returns how many rows matched (before the display cap)."""
        rows = self.found if self.ext is None else [t for t in self.found if t[2] == self.ext]
        rows = sorted(rows, key=SORT[self.sort_col], reverse=self.sort_rev)
        self.view = rows[:CAP]
        self.tree.delete(*self.tree.get_children())
        for i, (n, d, x) in enumerate(self.view):
            icon, _ = cat(x)
            kind = CAT_OF.get(x, "other")
            self.tree.insert("", "end", iid=str(i), values=(f"{icon}  {n}", x, d), tags=(kind, "odd") if i % 2 else (kind,))
        for c in SORT:  # sort arrow on the active column
            self.tree.heading(c, text=c.title() + (("  ▼" if self.sort_rev else "  ▲") if c == self.sort_col else ""))
        return len(rows)

    # ---- selection / opening -------------------------------------------
    def selected(self):
        return [self.view[int(i)] for i in self.tree.selection()]

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def _menu(self, ev):
        row = self.tree.identify_row(ev.y)
        if row:
            if row not in self.tree.selection():
                self.tree.selection_set(row)
            self.ctx.tk_popup(ev.x_root, ev.y_root)

    def _on_folder(self, ev):
        return self.tree.identify_region(ev.x, ev.y) == "cell" and self.tree.identify_column(ev.x) == "#3"

    def _open(self, ev, file):
        row = self.tree.identify_row(ev.y) if ev else (self.tree.selection() or [None])[0]
        if row:
            n, d, _ = self.view[int(row)]
            try:
                os.startfile(os.path.join(d, n) if file else d)
            except OSError as e:
                messagebox.showerror("Open", str(e))
