import tkinter as tk
from tkinterdnd2 import DND_FILES


def _parse_drop(data: str) -> list[str]:
    """Split tkinterdnd2 drop string into individual file paths."""
    paths = []
    data = data.strip()
    while data:
        if data.startswith("{"):
            end = data.index("}")
            paths.append(data[1:end])
            data = data[end + 1:].strip()
        else:
            parts = data.split(" ", 1)
            paths.append(parts[0])
            data = parts[1].strip() if len(parts) > 1 else ""
    return paths


class DropZone(tk.Frame):
    """Reusable drag-and-drop zone with optional Browse button."""

    def __init__(self, parent, label="Drop files here",
                 on_drop=None, on_browse=None, **kw):
        super().__init__(parent, bg="#dceefb", relief="ridge", bd=2, height=70, **kw)
        self.pack_propagate(False)
        self._cb = on_drop

        inner = tk.Frame(self, bg="#dceefb")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        lbl = tk.Label(inner, text=label, bg="#dceefb",
                       font=("Segoe UI", 10), fg="#1565c0")
        lbl.pack(side="left")

        if on_browse:
            tk.Label(inner, text="  or  ", bg="#dceefb",
                     font=("Segoe UI", 10), fg="#555").pack(side="left")
            tk.Button(inner, text="Browse…", command=on_browse,
                      relief="flat", bg="#1976d2", fg="white",
                      font=("Segoe UI", 9), padx=10, pady=3,
                      cursor="hand2").pack(side="left")

        # Register DnD on all parts of the zone
        for w in (self, inner, lbl):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", self._handle)

    def _handle(self, event):
        if self._cb:
            self._cb(_parse_drop(event.data))


class LogPanel(tk.Frame):
    """Dark scrollable log widget."""

    def __init__(self, parent, height=7, **kw):
        super().__init__(parent, **kw)

        lf = tk.LabelFrame(self, text=" Log ", font=("Segoe UI", 9), fg="#555",
                            bg=kw.get("bg", "#f5f5f5"))
        lf.pack(fill="both", expand=True)

        sb = tk.Scrollbar(lf, orient="vertical")
        sb.pack(side="right", fill="y")

        self._txt = tk.Text(lf, font=("Consolas", 8), state="disabled",
                            bg="#1e1e1e", fg="#d4d4d4", relief="flat",
                            padx=6, pady=4, height=height,
                            yscrollcommand=sb.set)
        self._txt.pack(fill="both", expand=True)
        sb.config(command=self._txt.yview)

        self._txt.tag_configure("ok",   foreground="#6aaa64")
        self._txt.tag_configure("err",  foreground="#e06c75")
        self._txt.tag_configure("info", foreground="#56b6c2")

    def write(self, msg: str, tag: str = ""):
        self._txt.configure(state="normal")
        self._txt.insert("end", msg + "\n", tag)
        self._txt.see("end")
        self._txt.configure(state="disabled")

    def clear(self):
        self._txt.configure(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.configure(state="disabled")
