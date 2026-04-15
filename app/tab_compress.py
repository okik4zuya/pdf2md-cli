import os
import threading
import tkinter as tk
from tkinter import filedialog

from pypdf import PdfReader, PdfWriter

from .widgets import DropZone, LogPanel


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


class CompressTab(tk.Frame):
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
        self.listbox = tk.Listbox(inner, font=("Segoe UI", 9),
                                   yscrollcommand=sb.set, bg="white",
                                   selectbackground="#bbdefb",
                                   relief="solid", bd=1)
        self.listbox.pack(fill="both", expand=True)
        sb.config(command=self.listbox.yview)

        # Options
        opt = tk.LabelFrame(self, text=" Options ", bg="#f5f5f5",
                             font=("Segoe UI", 9), fg="#555")
        opt.pack(fill="x", padx=12, pady=6)

        self.remove_meta = tk.BooleanVar(value=True)
        self.compress_streams = tk.BooleanVar(value=True)
        self.remove_images = tk.BooleanVar(value=False)

        tk.Checkbutton(opt, text="Remove metadata  (author, dates, software info)",
                       variable=self.remove_meta, bg="#f5f5f5",
                       font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(6, 2))
        tk.Checkbutton(opt, text="Re-compress content streams",
                       variable=self.compress_streams, bg="#f5f5f5",
                       font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=2)
        tk.Checkbutton(opt, text="Remove embedded thumbnails",
                       variable=self.remove_images, bg="#f5f5f5",
                       font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(2, 8))

        # Save location
        save_lf = tk.LabelFrame(self, text=" Save To ", bg="#f5f5f5",
                                 font=("Segoe UI", 9), fg="#555")
        save_lf.pack(fill="x", padx=12)
        self.save_mode = tk.StringVar(value="same")
        tk.Radiobutton(save_lf, text="Same folder as source  (adds _compressed suffix)",
                       variable=self.save_mode, value="same",
                       bg="#f5f5f5", font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(6, 2))
        tk.Radiobutton(save_lf, text="Choose folder…",
                       variable=self.save_mode, value="choose",
                       bg="#f5f5f5", font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(0, 6))

        # Buttons
        btn_row = tk.Frame(self, bg="#f5f5f5")
        btn_row.pack(fill="x", padx=12, pady=8)
        tk.Button(btn_row, text="Remove Selected", command=self._remove,
                  relief="flat", bg="#e0e0e0", padx=8, pady=3).pack(side="left")
        tk.Button(btn_row, text="Clear All", command=self._clear,
                  relief="flat", bg="#e0e0e0", padx=8, pady=3).pack(side="left", padx=6)
        self.btn = tk.Button(btn_row, text="Compress", command=self._start,
                              relief="flat", bg="#e65100", fg="white",
                              font=("Segoe UI", 9, "bold"), padx=14, pady=3,
                              cursor="hand2")
        self.btn.pack(side="right")

        self.log = LogPanel(self, height=5, bg="#f5f5f5")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── file management ──────────────────────────────────────────────

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

    # ── compression ──────────────────────────────────────────────────

    def _start(self):
        if not self.files:
            self.log.write("No files queued.", "err")
            return

        if self.save_mode.get() == "choose":
            output_dir = filedialog.askdirectory(title="Select output folder")
            if not output_dir:
                return
        else:
            output_dir = None   # resolved per-file

        self.btn.configure(state="disabled", text="Compressing…")
        opts = {
            "remove_meta":      self.remove_meta.get(),
            "compress_streams": self.compress_streams.get(),
            "remove_images":    self.remove_images.get(),
        }
        threading.Thread(
            target=self._run,
            args=(list(self.files), output_dir, opts),
            daemon=True
        ).start()

    def _run(self, files: list[str], output_dir: str | None, opts: dict):
        for i, path in enumerate(files, 1):
            self.after(0, lambda p=path, n=i, t=len(files):
                       self.log.write(f"\n[{n}/{t}] {os.path.basename(p)}", "info"))
            self._compress_one(path, output_dir, opts)
        self.after(0, lambda: self.log.write("\nDone.", "ok"))
        self.after(0, lambda: self.btn.configure(state="normal", text="Compress"))

    def _compress_one(self, path: str, output_dir: str | None, opts: dict):
        try:
            before = os.path.getsize(path)
            reader = PdfReader(path)
            writer = PdfWriter()

            # 1. Copy and Compress Pages
            for page in reader.pages:
                new_page = writer.add_page(page)
                if opts["compress_streams"]:
                    # Must be called on the page after add_page()
                    new_page.compress_content_streams()

            # 2. Metadata management
            if not opts["remove_meta"] and reader.metadata:
                writer.add_metadata(reader.metadata)

            # 3. Global compression optimization
            writer.compress_identical_objects()

            # 4. Remove all images/XObjects if requested
            if opts["remove_images"]:
                for page in writer.pages:
                    if "/Resources" in page and "/XObject" in page["/Resources"]:
                        del page["/Resources"]["/XObject"]

            # 5. Save the file
            stem = os.path.splitext(os.path.basename(path))[0]
            out_dir = output_dir or os.path.dirname(path)
            out_path = os.path.join(out_dir, f"{stem}_compressed.pdf")

            with open(out_path, "wb") as f:
                writer.write(f)

            after = os.path.getsize(out_path)
            saved = before - after
            pct   = (saved / before * 100) if before else 0

            if saved > 0:
                self.after(0, lambda a=after, b=before, p=pct, o=out_path:
                           self.log.write(
                               f"  \u2714 {_human_size(b)} \u2192 {_human_size(a)}"
                               f"  (\u2212{p:.1f}%)  \u2192  {os.path.basename(o)}", "ok"))
            else:
                self.after(0, lambda o=out_path:
                           self.log.write(
                               f"  \u2714 Saved (no size reduction achieved) \u2192 {os.path.basename(o)}",
                               "ok"))

        except Exception as e:
            self.after(0, lambda e=e: self.log.write(f"  \u2718 Error: {e}", "err"))
