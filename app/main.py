import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import TkinterDnD

from .tab_convert  import ConvertTab
from .tab_compress import CompressTab
from .tab_merge    import MergeTab
from .tab_split    import SplitTab
from .tab_editor   import PageEditor
from .tab_about    import AboutTab
from .toolbar      import Toolbar
from .config       import BASE_DIR


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ugly PDF")
        self.geometry("700x660")
        self.minsize(560, 520)
        self.configure(bg="#1a1a1a")
        self._set_icon()
        self._style()
        self._build()

    def _set_icon(self):
        icon_path = os.path.join(BASE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.wm_iconbitmap(icon_path)
            except Exception:
                pass

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook",     background="#f5f5f5", borderwidth=0)
        s.configure("TNotebook.Tab", font=("Segoe UI", 9),
                    padding=[12, 5], background="#e0e0e0", foreground="#333")
        s.map("TNotebook.Tab",
              background=[("selected", "#ffffff")],
              foreground=[("selected", "#1a1a1a")])

    def _build(self):
        # Notebook
        nb = ttk.Notebook(self)

        t_convert  = ConvertTab(nb)
        t_compress = CompressTab(nb)
        t_merge    = MergeTab(nb)
        t_split    = SplitTab(nb)
        t_editor   = PageEditor(nb)
        t_about    = AboutTab(nb)

        nb.add(t_convert,  text="  PDF → MD   ")
        nb.add(t_compress, text="  Compress   ")
        nb.add(t_merge,    text="  Merge      ")
        nb.add(t_split,    text="  Split      ")
        nb.add(t_editor,   text="  Page Editor ")
        nb.add(t_about,    text="  About      ")

        # Map tab index → frame (About has no _add_files, so omit it)
        tabs = {
            0: t_convert,
            1: t_compress,
            2: t_merge,
            3: t_split,
            4: t_editor,
        }

        # Toolbar (packed first so it sits above the notebook)
        Toolbar(self, notebook=nb, tabs=tabs).pack(fill="x")
        nb.pack(fill="both", expand=True, padx=0, pady=0)


def run():
    App().mainloop()
