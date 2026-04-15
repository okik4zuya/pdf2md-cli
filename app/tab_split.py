import os
import re
import threading
import tkinter as tk
from tkinter import filedialog

from pypdf import PdfWriter, PdfReader

from .widgets import DropZone, LogPanel


def _parse_ranges(text: str, max_page: int) -> list[tuple[int, int]]:
    """Parse '1-3, 5, 7-9' → list of (start, end) tuples (0-indexed)."""
    result = []
    for part in re.split(r"[,\s]+", text.strip()):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 1 <= a <= b <= max_page:
                result.append((a - 1, b - 1))
        elif re.fullmatch(r"\d+", part):
            n = int(part)
            if 1 <= n <= max_page:
                result.append((n - 1, n - 1))
    return result


class SplitTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f5f5f5")
        self.pdf_path: str | None = None
        self.page_count: int = 0
        self._build()

    def _build(self):
        DropZone(self, label="Drop a PDF file here",
                 on_drop=self._load_file,
                 on_browse=self._browse).pack(fill="x", padx=12, pady=(12, 4))

        self.info_var = tk.StringVar(value="No file selected.")
        tk.Label(self, textvariable=self.info_var, bg="#f5f5f5",
                 font=("Segoe UI", 9), fg="#555").pack(anchor="w", padx=14)

        # Split mode
        mode_lf = tk.LabelFrame(self, text=" Split Mode ", bg="#f5f5f5",
                                 font=("Segoe UI", 9), fg="#555")
        mode_lf.pack(fill="x", padx=12, pady=8)

        self.mode = tk.StringVar(value="all")

        tk.Radiobutton(mode_lf, text="Split every page into separate files",
                       variable=self.mode, value="all", bg="#f5f5f5",
                       font=("Segoe UI", 9),
                       command=self._toggle_range).pack(anchor="w", padx=8, pady=(6, 2))

        range_row = tk.Frame(mode_lf, bg="#f5f5f5")
        range_row.pack(anchor="w", padx=8, pady=(0, 8))
        tk.Radiobutton(range_row, text="Split by range:", variable=self.mode,
                       value="range", bg="#f5f5f5", font=("Segoe UI", 9),
                       command=self._toggle_range).pack(side="left")
        self.range_var = tk.StringVar()
        self.range_entry = tk.Entry(range_row, textvariable=self.range_var,
                                    font=("Segoe UI", 9), width=22, state="disabled")
        self.range_entry.pack(side="left", padx=6)
        tk.Label(range_row, text="e.g. 1-3, 5, 7-9", bg="#f5f5f5",
                 font=("Segoe UI", 8), fg="#888").pack(side="left")

        # Save location
        save_lf = tk.LabelFrame(self, text=" Save To ", bg="#f5f5f5",
                                 font=("Segoe UI", 9), fg="#555")
        save_lf.pack(fill="x", padx=12)
        self.save_mode = tk.StringVar(value="same")
        tk.Radiobutton(save_lf, text="Same folder as source",
                       variable=self.save_mode, value="same",
                       bg="#f5f5f5", font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(6, 2))
        tk.Radiobutton(save_lf, text="Choose folder…",
                       variable=self.save_mode, value="choose",
                       bg="#f5f5f5", font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(0, 6))

        # Buttons
        btn_row = tk.Frame(self, bg="#f5f5f5")
        btn_row.pack(fill="x", padx=12, pady=8)
        tk.Button(btn_row, text="Clear", command=self._clear,
                  relief="flat", bg="#e0e0e0", padx=8, pady=3).pack(side="left")
        self.btn = tk.Button(btn_row, text="Split PDF", command=self._start,
                              relief="flat", bg="#6a1b9a", fg="white",
                              font=("Segoe UI", 9, "bold"), padx=14, pady=3,
                              cursor="hand2")
        self.btn.pack(side="right")

        self.log = LogPanel(self, height=6, bg="#f5f5f5")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _toggle_range(self):
        self.range_entry.configure(
            state="normal" if self.mode.get() == "range" else "disabled")

    # ── file loading ─────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self._load_file([path])

    def _load_file(self, paths: list[str]):
        pdfs = [p for p in paths if p.lower().endswith(".pdf")]
        if not pdfs:
            return
        path = pdfs[0]
        try:
            self.page_count = len(PdfReader(path).pages)
            self.pdf_path = path
            self.info_var.set(
                f"  {os.path.basename(path)}  ({self.page_count} pages)")
            self.log.write(
                f"Loaded: {os.path.basename(path)} — {self.page_count} pages", "info")
        except Exception as e:
            self.log.write(f"Error reading PDF: {e}", "err")

    def _clear(self):
        self.pdf_path = None
        self.page_count = 0
        self.info_var.set("No file selected.")
        self.range_var.set("")

    # ── split ────────────────────────────────────────────────────────

    def _start(self):
        if not self.pdf_path:
            self.log.write("No file loaded.", "err")
            return

        if self.save_mode.get() == "same":
            output_dir = os.path.dirname(self.pdf_path)
        else:
            output_dir = filedialog.askdirectory(title="Select output folder")
            if not output_dir:
                return

        if self.mode.get() == "all":
            ranges = [(i, i) for i in range(self.page_count)]
        else:
            raw = self.range_var.get().strip()
            if not raw:
                self.log.write("Enter page ranges.", "err")
                return
            ranges = _parse_ranges(raw, self.page_count)
            if not ranges:
                self.log.write("No valid ranges found.", "err")
                return

        self.btn.configure(state="disabled", text="Splitting…")
        threading.Thread(target=self._split,
                         args=(self.pdf_path, ranges, output_dir), daemon=True).start()

    def _split(self, pdf_path: str, ranges: list[tuple[int, int]], output_dir: str):
        try:
            reader = PdfReader(pdf_path)
            stem = os.path.splitext(os.path.basename(pdf_path))[0]
            total = len(ranges)
            for i, (start, end) in enumerate(ranges, 1):
                writer = PdfWriter()
                for p in range(start, end + 1):
                    writer.add_page(reader.pages[p])
                label = f"p{start + 1}" if start == end else f"p{start + 1}-{end + 1}"
                out = os.path.join(output_dir, f"{stem}_{label}.pdf")
                with open(out, "wb") as f:
                    writer.write(f)
                self.after(0, lambda n=i, t=total, p=out:
                           self.log.write(f"[{n}/{t}] \u2714 {os.path.basename(p)}", "ok"))
            self.after(0, lambda: self.log.write(f"\nDone. {total} file(s) saved.", "ok"))
        except Exception as e:
            self.after(0, lambda e=e: self.log.write(f"\u2718 Error: {e}", "err"))
        finally:
            self.after(0, lambda: self.btn.configure(state="normal", text="Split PDF"))
