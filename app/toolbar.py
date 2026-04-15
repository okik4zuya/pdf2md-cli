import tkinter as tk
from tkinter import filedialog


class Toolbar(tk.Frame):
    """
    Thin top bar: app name (left) + Open PDF button (right).
    `notebook` and `tabs` are passed in so Open PDF can route
    files to whichever tab is currently active.
    """

    def __init__(self, parent, notebook, tabs: dict, **kw):
        super().__init__(parent, bg="#1a1a1a", height=38, **kw)
        self.pack_propagate(False)
        self._nb   = notebook
        self._tabs = tabs   # { tab_index: tab_frame }
        self._build()

    def _build(self):
        # App name — left
        tk.Label(self, text="Ugly PDF", bg="#1a1a1a", fg="#ffffff",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=14)

        # Open PDF button — right
        tk.Button(
            self, text="+ Open PDF",
            command=self._open,
            relief="flat",
            bg="#333333", fg="#ffffff",
            activebackground="#444444", activeforeground="#ffffff",
            font=("Segoe UI", 9),
            padx=10, pady=0,
            cursor="hand2",
            bd=0
        ).pack(side="right", padx=10, pady=6)

    def _open(self):
        paths = filedialog.askopenfilenames(
            title="Open PDF files",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not paths:
            return

        active_idx = self._nb.index(self._nb.select())
        tab = self._tabs.get(active_idx)

        # Route to the active tab if it accepts files, else default to index 0
        if tab and hasattr(tab, "_add_files"):
            tab._add_files(list(paths))
        elif self._tabs.get(0) and hasattr(self._tabs[0], "_add_files"):
            self._nb.select(0)
            self._tabs[0]._add_files(list(paths))
