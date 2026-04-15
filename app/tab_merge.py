import os
import threading
import tkinter as tk
from tkinter import filedialog

from pypdf import PdfWriter, PdfReader

from .widgets import DropZone, LogPanel


class MergeTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f5f5f5")
        self.files: list[str] = []
        self._build()

    def _build(self):
        DropZone(self, label="Drop PDF files to merge",
                 on_drop=self._add_files,
                 on_browse=self._browse).pack(fill="x", padx=12, pady=(12, 4))

        tk.Label(self, text="Files to merge (in order):", bg="#f5f5f5",
                 font=("Segoe UI", 9), fg="#333").pack(anchor="w", padx=12)

        # List + reorder buttons
        list_frame = tk.Frame(self, bg="#f5f5f5")
        list_frame.pack(fill="both", expand=True, padx=12, pady=(2, 4))

        lb_wrap = tk.Frame(list_frame, bg="#f5f5f5")
        lb_wrap.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lb_wrap, orient="vertical")
        sb.pack(side="right", fill="y")
        self.listbox = tk.Listbox(lb_wrap, font=("Segoe UI", 9), yscrollcommand=sb.set,
                                   bg="white", selectbackground="#bbdefb",
                                   relief="solid", bd=1)
        self.listbox.pack(fill="both", expand=True)
        sb.config(command=self.listbox.yview)

        ctrl = tk.Frame(list_frame, bg="#f5f5f5")
        ctrl.pack(side="left", fill="y", padx=(6, 0))
        for text, cmd in [("↑", self._move_up), ("↓", self._move_down)]:
            tk.Button(ctrl, text=text, command=cmd, width=3,
                      relief="flat", bg="#e0e0e0",
                      font=("Segoe UI", 11)).pack(pady=2)
        tk.Button(ctrl, text="✕", command=self._remove, width=3,
                  relief="flat", bg="#e0e0e0",
                  fg="#c62828", font=("Segoe UI", 10)).pack(pady=(6, 0))

        # Output options
        opt = tk.LabelFrame(self, text=" Output ", bg="#f5f5f5",
                             font=("Segoe UI", 9), fg="#555")
        opt.pack(fill="x", padx=12, pady=4)

        row1 = tk.Frame(opt, bg="#f5f5f5")
        row1.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(row1, text="Filename:", bg="#f5f5f5",
                 font=("Segoe UI", 9)).pack(side="left")
        self.filename_var = tk.StringVar(value="merged_output.pdf")
        tk.Entry(row1, textvariable=self.filename_var,
                 font=("Segoe UI", 9), width=32).pack(side="left", padx=6)

        row2 = tk.Frame(opt, bg="#f5f5f5")
        row2.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(row2, text="Save to:", bg="#f5f5f5",
                 font=("Segoe UI", 9)).pack(side="left")
        self.save_mode = tk.StringVar(value="first")
        tk.Radiobutton(row2, text="Same folder as first file",
                       variable=self.save_mode, value="first",
                       bg="#f5f5f5", font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Radiobutton(row2, text="Choose…",
                       variable=self.save_mode, value="choose",
                       bg="#f5f5f5", font=("Segoe UI", 9)).pack(side="left")

        # Buttons
        btn_row = tk.Frame(self, bg="#f5f5f5")
        btn_row.pack(fill="x", padx=12, pady=4)
        tk.Button(btn_row, text="Clear All", command=self._clear,
                  relief="flat", bg="#e0e0e0", padx=8, pady=3).pack(side="left")
        self.btn = tk.Button(btn_row, text="Merge PDFs", command=self._start,
                              relief="flat", bg="#1565c0", fg="white",
                              font=("Segoe UI", 9, "bold"), padx=14, pady=3,
                              cursor="hand2")
        self.btn.pack(side="right")

        self.log = LogPanel(self, height=5, bg="#f5f5f5")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── file management ─────────────────────────────────────────────

    def _browse(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        self._add_files(list(paths))

    def _add_files(self, paths: list[str]):
        added = 0
        for p in paths:
            if p.lower().endswith(".pdf") and p not in self.files:
                self.files.append(p)
                self.listbox.insert("end", os.path.basename(p))
                added += 1
        if added:
            self.log.write(f"Added {added} file(s).", "info")

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.files[i - 1], self.files[i] = self.files[i], self.files[i - 1]
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i - 1, text)
        self.listbox.selection_set(i - 1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= self.listbox.size() - 1:
            return
        i = sel[0]
        self.files[i], self.files[i + 1] = self.files[i + 1], self.files[i]
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i + 1, text)
        self.listbox.selection_set(i + 1)

    def _remove(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            self.files.pop(sel[0])

    def _clear(self):
        self.listbox.delete(0, "end")
        self.files.clear()

    # ── merge ───────────────────────────────────────────────────────

    def _start(self):
        if len(self.files) < 2:
            self.log.write("Add at least 2 PDF files to merge.", "err")
            return

        if self.save_mode.get() == "first":
            output_dir = os.path.dirname(self.files[0])
        else:
            output_dir = filedialog.askdirectory(title="Select output folder")
            if not output_dir:
                return

        filename = self.filename_var.get().strip() or "merged_output.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        output_path = os.path.join(output_dir, filename)

        self.btn.configure(state="disabled", text="Merging…")
        threading.Thread(target=self._merge,
                         args=(list(self.files), output_path), daemon=True).start()

    def _merge(self, files: list[str], output_path: str):
        try:
            writer = PdfWriter()
            for path in files:
                self.after(0, lambda p=path: self.log.write(
                    f"  Adding: {os.path.basename(p)}", "info"))
                for page in PdfReader(path).pages:
                    writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
            self.after(0, lambda: self.log.write(f"\n\u2714 Saved: {output_path}", "ok"))
        except Exception as e:
            self.after(0, lambda e=e: self.log.write(f"\n\u2718 Error: {e}", "err"))
        finally:
            self.after(0, lambda: self.btn.configure(state="normal", text="Merge PDFs"))
