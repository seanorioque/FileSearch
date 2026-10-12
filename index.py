import fnmatch
import os
import queue
import re
import string
import threading

WORKERS = 64  # directory listing is I/O bound, so many threads overlap the waits
SKIP = {"windows", "node_modules", "$recycle.bin", "system volume information", ".git"}

# category -> (icon, colour, extensions)
CATS = {
    "image": ("\U0001F5BC", "#db2777", ".jpg .jpeg .png .gif .bmp .webp .svg .ico .tiff .heic"),
    "video": ("\U0001F3AC", "#7c3aed", ".mp4 .mkv .avi .mov .wmv .webm .flv"),
    "audio": ("\U0001F3B5", "#0891b2", ".mp3 .wav .flac .aac .ogg .m4a"),
    "doc": ("\U0001F4C4", "#2563eb", ".pdf .doc .docx .txt .rtf .odt .md .ppt .pptx .xls .xlsx .csv"),
    "code": ("\U0001F4BB", "#059669", ".py .js .ts .html .css .php .java .c .cpp .cs .json .xml .sql .sh .bat .kt .go .rs"),
    "archive": ("\U0001F4E6", "#d97706", ".zip .rar .7z .tar .gz .iso"),
    "other": ("\U0001F4CE", "#4b5563", ""),
}
CAT_OF = {x: k for k, (_, _, xs) in CATS.items() for x in xs.split()}


def cat(ext):
    """(icon, colour) for a file extension."""
    icon, colour, _ = CATS[CAT_OF.get(ext, "other")]
    return icon, colour


def drives():
    return [f"{c}:\\" for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")]


def matcher(q):
    """Substring match, or wildcard match (* ? [) against the whole name."""
    q = q.lower()
    if any(c in q for c in "*?["):
        return re.compile(fnmatch.translate(q)).match
    return lambda n: q in n


class FileIndex:
    """Background-built list of (name, folder, ext) for every file under the roots."""

    def __init__(self):
        self.entries, self.roots = [], None
        self._stop, self.done = threading.Event(), threading.Event()

    @property
    def running(self):
        return not self.done.is_set()

    @property
    def stopped(self):
        return self._stop.is_set()

    def start(self, roots):
        self._stop.set()  # cancel the previous scan; its workers append to the old list only
        self._stop, self.entries, self.roots = threading.Event(), [], roots
        self.done = self._scan(roots, self.entries, self._stop)

    def cancel(self):
        self._stop.set()

    def search(self, q):
        test = matcher(q)
        return [t for t in self.entries[:] if test(t[0].lower())]  # [:] = snapshot while scanning

    def apply_moves(self, moved):
        """moved = [(old_path, new_entry)]; keeps the index correct after a Move."""
        gone = {src for src, _ in moved}
        self.entries[:] = [t for t in self.entries if os.path.join(t[1], t[0]) not in gone] + [t for _, t in moved]

    @staticmethod
    def _scan(roots, entries, stop):
        """Parallel scandir walk. Returns an Event that is set when finished."""
        dirs, done = queue.Queue(), threading.Event()
        for r in roots:
            dirs.put(r)

        def worker():
            while not done.is_set():
                try:
                    d = dirs.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    if not stop.is_set():
                        with os.scandir(d) as it:
                            for e in it:
                                if e.is_dir(follow_symlinks=False):  # no symlink/junction loops
                                    if e.name.lower() not in SKIP:
                                        dirs.put(e.path)
                                else:
                                    entries.append((e.name, d, os.path.splitext(e.name)[1].lower() or "(none)"))
                except OSError:  # no permission / vanished
                    pass
                finally:
                    dirs.task_done()

        for _ in range(WORKERS):
            threading.Thread(target=worker, daemon=True).start()

        def finish():
            dirs.join()
            done.set()

        threading.Thread(target=finish, daemon=True).start()
        return done
