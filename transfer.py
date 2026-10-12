import os
import shutil
import threading


class Transfer:
    """Copies or moves index entries into a folder on a background thread."""

    def __init__(self, rows, dest, move):
        self.rows, self.dest, self.move = rows, dest, move
        self.done, self.failed, self.moved, self.finished = 0, [], [], False

    @property
    def verb(self):
        return "Move" if self.move else "Copy"

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def summary(self):
        bad = self.failed
        msg = f"{self.verb} done: {len(self.rows) - len(bad)} ok, {len(bad)} failed.\n{self.dest}"
        if bad:
            msg += "\n\nFailed:\n" + "\n".join(bad[:10]) + ("\n..." if len(bad) > 10 else "")
        return msg

    def _run(self):
        for name, folder, ext in self.rows:
            src, (base, e) = os.path.join(folder, name), os.path.splitext(name)
            target, n = os.path.join(self.dest, name), 1
            while os.path.exists(target):  # same name from different folders
                target, n = os.path.join(self.dest, f"{base} ({n}){e}"), n + 1
            try:
                (shutil.move if self.move else shutil.copy2)(src, target)
                if self.move:
                    self.moved.append((src, (os.path.basename(target), self.dest, ext)))
            except OSError as err:  # includes shutil.Error and permission problems
                self.failed.append(f"{name}: {err}")
            self.done += 1
        self.finished = True

    @staticmethod
    def new_folder(parent, name):
        """Create a brand-new folder, never merging into an existing one."""
        dest, n = os.path.join(parent, name), 1
        while os.path.exists(dest):
            dest, n = os.path.join(parent, f"{name} ({n})"), n + 1
        os.makedirs(dest)
        return dest
