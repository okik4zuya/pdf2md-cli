import os
import threading
import tkinter as tk
from tkinter import filedialog

from pdfminer.high_level import extract_text
from pdf2image import convert_from_path
import pytesseract

from .config import POPPLER_PATH, TESSERACT_PATH
from .widgets import DropZone, LogPanel

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


class ConvertTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f5f5f5")
        self.files: list[str] = []
        self._build()

    def _build(self):
        DropZone(self, label="Drop PDF files here",
                 on_drop=self._add_files,
                 on_browse=self._browse).pack(fill="x", padx=12, pady=(12, 4))

        # File list
        list_frame = tk.Frame(self, bg="#f5f5f5")
        list_frame.pack(fill="both", expand=True, padx=12, pady=4)
        tk.Label(list_frame, text="Files queued:", bg="#f5f5f5",
                 font=("Segoe UI", 9), fg="#333").pack(anchor="w")

        inner = tk.Frame(list_frame, bg="#f5f5f5")
        inner.pack(fill="both", expand=True)
        sb = tk.Scrollbar(inner, orient="vertical")
        sb.pack(side="right", fill="y")
        self.listbox = tk.Listbox(inner, font=("Segoe UI", 9), yscrollcommand=sb.set,
                                   bg="white", selectbackground="#bbdefb",
                                   relief="solid", bd=1)
        self.listbox.pack(fill="both", expand=True)
        sb.config(command=self.listbox.yview)

        # Buttons
        btn_row = tk.Frame(self, bg="#f5f5f5")
        btn_row.pack(fill="x", padx=12, pady=4)
        tk.Button(btn_row, text="Remove Selected", command=self._remove,
                  relief="flat", bg="#e0e0e0", padx=8, pady=3).pack(side="left")
        tk.Button(btn_row, text="Clear All", command=self._clear,
                  relief="flat", bg="#e0e0e0", padx=8, pady=3).pack(side="left", padx=6)
        self.btn = tk.Button(btn_row, text="Convert All", command=self._start,
                              relief="flat", bg="#388e3c", fg="white",
                              font=("Segoe UI", 9, "bold"), padx=14, pady=3,
                              cursor="hand2")
        self.btn.pack(side="right")

        self.log = LogPanel(self, height=7, bg="#f5f5f5")
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

    def _remove(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            self.files.pop(sel[0])

    def _clear(self):
        self.listbox.delete(0, "end")
        self.files.clear()

    # ── conversion ──────────────────────────────────────────────────

    def _start(self):
        if not self.files:
            self.log.write("No files queued.", "err")
            return
        self.btn.configure(state="disabled", text="Converting…")
        threading.Thread(target=self._run, args=(list(self.files),), daemon=True).start()

    def _run(self, files: list[str]):
        for i, path in enumerate(files, 1):
            self.after(0, lambda p=path, n=i, t=len(files):
                       self.log.write(f"\n[{n}/{t}] {os.path.basename(p)}", "info"))
            self._convert(path)
        self.after(0, lambda: self.log.write("\nAll done.", "ok"))
        self.after(0, lambda: self.btn.configure(state="normal", text="Convert All"))

    def _convert(self, pdf_path: str):
        try:
            output_md = os.path.splitext(pdf_path)[0] + ".md"
            text = extract_text(pdf_path)

            if not text.strip():
                self.after(0, lambda: self.log.write(
                    "  No text layer — running OCR…", "info"))
                pages = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
                parts = []
                for j, page in enumerate(pages, 1):
                    self.after(0, lambda j=j, t=len(pages):
                               self.log.write(f"  OCR page {j}/{t}…"))
                    parts.append(pytesseract.image_to_string(page))
                text = "\n".join(parts)
            else:
                self.after(0, lambda: self.log.write("  Text layer detected."))

            with open(output_md, "w", encoding="utf-8") as f:
                f.write("# Extracted PDF Content\n\n" + text)

            self.after(0, lambda p=output_md: self.log.write(f"  \u2714 Saved: {p}", "ok"))

        except Exception as e:
            self.after(0, lambda e=e: self.log.write(f"  \u2718 Error: {e}", "err"))
