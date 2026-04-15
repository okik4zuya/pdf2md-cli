import tkinter as tk
from tkinter import font as tkfont
import webbrowser

APP_NAME    = "Ugly PDF"
VERSION     = "1.0.0"
GITHUB_URL  = "https://github.com/okik4zuya/uglypdf"   # replace with real URL


class AboutTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#ffffff")
        self._build()

    def _build(self):
        # Centre everything in a fixed-width column
        wrap = tk.Frame(self, bg="#ffffff")
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        # App name
        tk.Label(wrap, text=APP_NAME, bg="#ffffff",
                 font=("Segoe UI", 32, "bold"),
                 fg="#1a1a1a").pack(anchor="w")

        # Version + tagline
        tk.Label(wrap, text=f"Version {VERSION}",
                 bg="#ffffff", font=("Segoe UI", 10), fg="#888").pack(anchor="w")
        tk.Label(wrap, text="No upload. No account. Just PDF tools.",
                 bg="#ffffff", font=("Segoe UI", 11), fg="#555").pack(anchor="w", pady=(4, 20))

        # Divider
        tk.Frame(wrap, height=1, bg="#e5e5e5", width=340).pack(fill="x", pady=(0, 20))

        # Features
        features = [
            ("PDF → Markdown", "Extract text from PDFs. Auto OCR for scanned files."),
            ("Compress",        "Reduce PDF file size by stripping metadata and re-compressing streams."),
            ("Merge",           "Combine multiple PDFs into one. Reorder before merging."),
            ("Split",           "Split by every page or custom ranges like 1–3, 5, 7–9."),
            ("Page Editor",     "Reorder, rotate and delete pages. Mix pages from multiple PDFs."),
        ]

        for title, desc in features:
            row = tk.Frame(wrap, bg="#ffffff")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=title, bg="#ffffff",
                     font=("Segoe UI", 9, "bold"), fg="#1a1a1a",
                     width=18, anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg="#ffffff",
                     font=("Segoe UI", 9), fg="#555",
                     anchor="w", justify="left",
                     wraplength=240).pack(side="left")

        # Divider
        tk.Frame(wrap, height=1, bg="#e5e5e5", width=340).pack(fill="x", pady=(20, 16))

        # Built with
        tk.Label(wrap, text="Built with  Python · tkinter · pypdf · pdfminer · Tesseract OCR",
                 bg="#ffffff", font=("Segoe UI", 8), fg="#aaa").pack(anchor="w")

        # GitHub link
        link = tk.Label(wrap, text=GITHUB_URL, bg="#ffffff",
                        font=("Segoe UI", 8), fg="#1976d2",
                        cursor="hand2")
        link.pack(anchor="w", pady=(4, 0))
        link.bind("<Button-1>", lambda _: webbrowser.open(GITHUB_URL))

        # Free forever note
        tk.Label(wrap, text="Free forever.", bg="#ffffff",
                 font=("Segoe UI", 8), fg="#aaa").pack(anchor="w", pady=(8, 0))
