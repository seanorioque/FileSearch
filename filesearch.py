import os
import tkinter as tk
from collections import Counter
from tkinter import filedialog, messagebox, simpledialog, ttk

import theme
from index import FileIndex, drives
from transfer import Transfer
from widgets import CAP, Hero, ResultsTable, TypePanel


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Search")
        self.geometry("1000x650")
        self.minsize(860, 500)
        theme.apply(self)
        self.folder, self.query = tk.StringVar(), tk.StringVar()  # empty folder = all drives
        self.index, self.job, self.last_q, self.counts = FileIndex(), None, "", Counter()

        Hero(self).pack(fill="x")
        self._build_search_bar()
        self._build_status_bar()
        self._build_actions()
        self.result_lbl = ttk.Label(self, style="Muted.TLabel", padding=(16, 6, 16, 2))
        self.result_lbl.pack(fill="x")
        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=16)
        self.table = ResultsTable(body)
        self.types = TypePanel(body, self.pick_type)
        body.add(self.table, weight=4)
        body.add(self.types, weight=1)

        self.result_lbl.config(text="\U0001F44B Type a name or extension above and press Enter")
        self.reindex()

    # ---- layout ---------------------------------------------------------
    def _build_search_bar(self):
        head = ttk.Frame(self, padding=(16, 14, 16, 4))
        head.pack(fill="x")
        e = ttk.Entry(head, textvariable=self.query, font=("Segoe UI", 12))
        e.grid(row=1, column=0, columnspan=2, sticky="ew")
        e.bind("<Return>", lambda _: self.start())
        e.focus()
        ttk.Button(head, text="Search", style="Accent.TButton", command=self.start).grid(row=1, column=2, padx=(8, 0))
        ttk.Entry(head, textvariable=self.folder).grid(row=2, column=0, sticky="ew", pady=8)
        ttk.Button(head, text="Browse...", command=self.browse).grid(row=2, column=1, padx=8)
        bar = ttk.Frame(head)
        bar.grid(row=2, column=2)
        ttk.Button(bar, text="Refresh", command=self.reindex).pack(side="left")
        ttk.Button(bar, text="Stop", command=self.index.cancel).pack(side="left", padx=(8, 0))
        ttk.Label(head, text="Folder empty = all drives.  Search a name part (sean), an extension (.jpg) or a wildcard (sean*.jpg).",
                  style="Muted.TLabel").grid(row=3, column=0, columnspan=3, sticky="w")
        head.columnconfigure(0, weight=1)

    def _build_status_bar(self):
        bar = ttk.Frame(self, padding=(16, 4))
        bar.pack(side="bottom", fill="x")
        self.scan_lbl = ttk.Label(bar, style="Muted.TLabel")
        self.scan_lbl.pack(side="left")
        self.prog = ttk.Progressbar(bar, mode="indeterminate", length=140, style="Accent.Horizontal.TProgressbar")

    def _build_actions(self):
        bar = ttk.Frame(self, padding=(16, 6))
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text="Select all", command=lambda: self.table.select_all()).pack(side="left")
        for label, move in (("Move to  ▾", True), ("Copy to  ▾", False)):
            mb = ttk.Menubutton(bar, text=label)
            mb["menu"] = m = tk.Menu(mb, tearoff=0)
            m.add_command(label="New folder...", command=lambda mv=move: self.transfer(mv, True))
            m.add_command(label="Existing folder...", command=lambda mv=move: self.transfer(mv, False))
            mb.pack(side="right", padx=(8, 0))

    # ---- indexing -------------------------------------------------------
    def current_roots(self):
        f = self.folder.get().strip()
        return [os.path.normpath(f)] if f else drives()

    def reindex(self):
        roots = self.current_roots()
        if not all(os.path.isdir(r) for r in roots):
            return messagebox.showerror("Folder", "That folder doesn't exist.")
        self.index.start(roots)
        self.prog.pack(side="right")
        self.prog.start(12)
        self.watch_scan(self.index.entries)

    def watch_scan(self, entries):
        if entries is not self.index.entries:  # superseded by a newer scan
            return
        n = len(entries)
        if self.index.running:
            self.scan_lbl.config(text=f"⏳ Indexing... {n:,} files (searches use what's indexed so far)")
            return self.after(300, self.watch_scan, entries)
        self.prog.stop()
        self.prog.pack_forget()
        stopped = self.index.stopped
        self.scan_lbl.config(text=f"{'⏹ Stopped - partial index' if stopped else '✅ Indexed'}: {n:,} files")
        if self.last_q and not stopped:
            self.run_search()  # pick up files found after the user searched

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.folder.set(os.path.normpath(d))

    # ---- searching ------------------------------------------------------
    def start(self):
        q = self.query.get().strip()
        if not q:
            return
        self.last_q = q
        if self.current_roots() != self.index.roots:
            return self.reindex()  # new scope; the search reruns when indexing finishes
        self.run_search()

    def run_search(self):
        found = self.index.search(self.last_q)
        self.counts = Counter(t[2] for t in found)
        self.types.show(len(found), self.counts)
        self.show_count(self.table.set_rows(found))

    def pick_type(self, ext):
        self.show_count(self.table.filter(ext))

    def show_count(self, n):
        note = f" - showing first {CAP:,}, refine your search" if n > CAP else ""
        self.result_lbl.config(text=f"✨ {n:,} files, {len(self.counts)} types{note}" if n
                               else "\U0001F615 No files found - try a shorter name or another extension")

    # ---- copy / move ----------------------------------------------------
    def transfer(self, move, new=True):
        rows, verb = self.table.selected(), "Move" if move else "Copy"
        if self.job and not self.job.finished:
            return messagebox.showinfo(verb, "Another transfer is still running.")
        if not rows:
            return messagebox.showinfo(verb, "Select one or more files first (Ctrl/Shift+click).")
        if move and self.index.running:
            return messagebox.showinfo(verb, "Wait for indexing to finish (or press Stop) before moving.")
        dest = self.ask_new_folder() if new else self.ask_existing_folder(verb)
        if dest:
            self.job = Transfer(rows, dest, move)
            self.job.start()
            self.watch_job(self.job)

    @staticmethod
    def ask_new_folder():
        parent = filedialog.askdirectory(title="Where to create the new folder?")
        name = parent and simpledialog.askstring("New folder", "Folder name:")
        return Transfer.new_folder(parent, name.strip()) if name and name.strip() else None

    @staticmethod
    def ask_existing_folder(verb):
        d = filedialog.askdirectory(title=f"{verb} to which existing folder?")
        return os.path.normpath(d) if d else None

    def watch_job(self, job):
        if not job.finished:
            self.result_lbl.config(text=f"{job.verb}ing {job.done}/{len(job.rows)}...")
            return self.after(200, self.watch_job, job)
        if job.moved:
            self.index.apply_moves(job.moved)
            self.run_search()
        messagebox.showinfo(job.verb, job.summary())
        os.startfile(job.dest)


if __name__ == "__main__":
    App().mainloop()
