import math
import os
import threading
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox
from typing import Optional

from PIL import Image, ImageTk
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter
from tkinterdnd2 import DND_FILES

from .config import POPPLER_PATH
from .widgets import _parse_drop

# ── thumbnail constants ──────────────────────────────────────────────────────
THUMB_W   = 110
THUMB_H   = 150
PAD       = 10
LABEL_H   = 26
CELL_W    = THUMB_W + PAD * 2
CELL_H    = THUMB_H + LABEL_H + PAD * 2
THUMB_DPI = 72


@dataclass
class PageItem:
    pdf_path:   str
    page_index: int          # 0-based original index
    rotation:   int  = 0    # 0 / 90 / 180 / 270
    thumb:      Optional[Image.Image]    = field(default=None, repr=False)
    photo:      Optional[ImageTk.PhotoImage] = field(default=None, repr=False)


class PageEditor(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#ebebeb")
        self.pages:    list[PageItem] = []
        self._sel:     set[int]       = set()   # selected indices
        self._drag_src: Optional[int] = None    # index being dragged
        self._ins_idx:  Optional[int] = None    # insertion target
        self._ghost_id  = None
        self._line_id   = None
        self._build()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build(self):
        # Toolbar
        tb = tk.Frame(self, bg="#e0e0e0")
        tb.pack(fill="x")
        self._make_tb(tb)

        # Status bar
        self._status = tk.StringVar(value="No pages loaded.")
        tk.Label(tb, textvariable=self._status, bg="#e0e0e0",
                 font=("Segoe UI", 8), fg="#555").pack(side="right", padx=10)

        # Canvas + vertical scrollbar
        wrap = tk.Frame(self, bg="#ebebeb")
        wrap.pack(fill="both", expand=True)

        self._vsb = tk.Scrollbar(wrap, orient="vertical")
        self._vsb.pack(side="right", fill="y")

        self.canvas = tk.Canvas(wrap, bg="#ebebeb", highlightthickness=0,
                                 yscrollcommand=self._vsb.set)
        self.canvas.pack(fill="both", expand=True)
        self._vsb.config(command=self.canvas.yview)

        # Bindings
        self.canvas.bind("<Configure>",       lambda _: self._redraw())
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(
                             -1 if e.delta > 0 else 1, "units"))
        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",        self._on_drag)
        self.canvas.bind("<ButtonRelease-1>",  self._on_release)
        self.canvas.bind("<Button-3>",         self._on_rclick)

        # Accept PDF files dropped from outside
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self._on_file_drop)

        # Context menu
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="Rotate 90° CW",  command=lambda: self._rotate(90))
        self._menu.add_command(label="Rotate 90° CCW", command=lambda: self._rotate(-90))
        self._menu.add_separator()
        self._menu.add_command(label="Delete Page",    command=self._delete_sel)

    def _make_tb(self, tb):
        def btn(text, cmd, bg="#e0e0e0", fg="#222"):
            return tk.Button(tb, text=text, command=cmd, relief="flat",
                             bg=bg, fg=fg, font=("Segoe UI", 9),
                             padx=8, pady=4, cursor="hand2",
                             activebackground="#bdbdbd")

        def sep():
            tk.Frame(tb, width=1, bg="#bdbdbd").pack(
                side="left", fill="y", padx=2, pady=4)

        btn("+ Add PDF",    self._add_pdf).pack(side="left", padx=(4, 0), pady=4)
        sep()
        btn("Select All",   self._select_all).pack(side="left", padx=2)
        btn("✕ Delete",     self._delete_sel, "#ffcdd2", "#c62828").pack(side="left", padx=2)
        sep()
        btn("↺ Rotate CW",  lambda: self._rotate(90)).pack(side="left", padx=2)
        btn("↻ Rotate CCW", lambda: self._rotate(-90)).pack(side="left", padx=2)
        sep()
        btn("💾 Save PDF…",  self._save, "#c8e6c9", "#1b5e20").pack(side="left", padx=2)

    # ── geometry helpers ─────────────────────────────────────────────────────

    def _cols(self) -> int:
        w = self.canvas.winfo_width()
        return max(1, w // CELL_W)

    def _cell_xy(self, idx: int) -> tuple[int, int]:
        cols = self._cols()
        row, col = divmod(idx, cols)
        return col * CELL_W + PAD, row * CELL_H + PAD

    def _hit_idx(self, cx: int, cy: int) -> Optional[int]:
        """Return page index at canvas-coordinate (cx, cy), or None."""
        cols = self._cols()
        col  = cx // CELL_W
        row  = cy // CELL_H
        if col >= cols:
            return None
        idx = row * cols + col
        return idx if 0 <= idx < len(self.pages) else None

    def _insert_at(self, cx: int, cy: int) -> int:
        """Return insertion index (0 … len) for drop at canvas coords."""
        cols = self._cols()
        col  = min(cx // CELL_W, cols - 1)
        row  = cy // CELL_H
        idx  = row * cols + col
        if cx > col * CELL_W + CELL_W // 2:   # right half → insert after
            idx += 1
        return max(0, min(idx, len(self.pages)))

    # ── drawing ──────────────────────────────────────────────────────────────

    def _redraw(self):
        self.canvas.delete("all")
        self._ghost_id = None
        self._line_id  = None

        if not self.pages:
            w = max(self.canvas.winfo_width(),  1)
            h = max(self.canvas.winfo_height(), 1)
            self.canvas.create_text(
                w // 2, h // 2,
                text="Click '+ Add PDF' or drop a PDF here",
                fill="#aaa", font=("Segoe UI", 11))
            self.canvas.configure(scrollregion=(0, 0, w, h))
            return

        cols  = self._cols()
        rows  = math.ceil(len(self.pages) / cols)
        total_h = rows * CELL_H + PAD
        self.canvas.configure(
            scrollregion=(0, 0, self.canvas.winfo_width(), total_h))

        for i in range(len(self.pages)):
            if i == self._drag_src:
                continue          # drawn as ghost during drag
            self._draw_card(i)

    def _draw_card(self, idx: int):
        page     = self.pages[idx]
        selected = idx in self._sel
        x, y     = self._cell_xy(idx)

        bg      = "#1976d2" if selected else "white"
        outline = "#1976d2" if selected else "#cccccc"
        lw      = 2         if selected else 1

        self.canvas.create_rectangle(
            x, y, x + CELL_W - PAD, y + CELL_H - PAD,
            fill=bg, outline=outline, width=lw)

        if page.photo:
            self.canvas.create_image(
                x + (CELL_W - PAD) // 2,
                y + PAD // 2 + THUMB_H // 2,
                image=page.photo, anchor="center")
        else:
            # Placeholder while rendering
            self.canvas.create_rectangle(
                x + 4, y + 4, x + CELL_W - PAD - 4, y + THUMB_H,
                fill="#e0e0e0", outline="#ccc")
            self.canvas.create_text(
                x + (CELL_W - PAD) // 2, y + THUMB_H // 2,
                text="…", fill="#aaa", font=("Segoe UI", 9))

        # Label: "p1 · filename"
        fname = os.path.splitext(os.path.basename(page.pdf_path))[0]
        label = f"p{page.page_index + 1}  ·  {fname}"
        self.canvas.create_text(
            x + (CELL_W - PAD) // 2,
            y + THUMB_H + PAD // 2 + LABEL_H // 2,
            text=label,
            fill="white" if selected else "#555",
            font=("Segoe UI", 7),
            width=CELL_W - PAD - 6)

    def _draw_insert_line(self, ins: int):
        if self._line_id:
            self.canvas.delete(self._line_id)
        cols        = self._cols()
        row, col    = divmod(min(ins, len(self.pages)), cols)
        x           = col * CELL_W + (PAD // 2 if col > 0 else 0)
        y1          = row * CELL_H + PAD
        y2          = row * CELL_H + CELL_H - PAD
        self._line_id = self.canvas.create_line(
            x, y1, x, y2, fill="#1976d2", width=3)

    # ── adding / thumbnail loading ────────────────────────────────────────────

    def _add_pdf(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for p in paths:
            self._load_pdf(p)

    def _on_file_drop(self, event):
        for p in _parse_drop(event.data):
            if p.lower().endswith(".pdf"):
                self._load_pdf(p)

    def _load_pdf(self, path: str):
        try:
            count = len(PdfReader(path).pages)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read PDF:\n{e}")
            return

        start = len(self.pages)
        for i in range(count):
            self.pages.append(PageItem(pdf_path=path, page_index=i))

        self._redraw()
        self._update_status()

        threading.Thread(
            target=self._render_thumbs, args=(path, start, count), daemon=True
        ).start()

    def _render_thumbs(self, path: str, start: int, count: int):
        try:
            images = convert_from_path(path, dpi=THUMB_DPI, poppler_path=POPPLER_PATH)
            for i, img in enumerate(images):
                if start + i >= len(self.pages):
                    break
                photo = self._make_photo(img, self.pages[start + i].rotation)
                self.pages[start + i].thumb = img
                self.pages[start + i].photo = photo
                self.after(0, self._redraw)
        except Exception:
            pass

    @staticmethod
    def _make_photo(img: Image.Image, rotation: int = 0) -> ImageTk.PhotoImage:
        if rotation:
            img = img.rotate(-rotation, expand=True)
        # Fit inside THUMB_W × THUMB_H keeping aspect ratio
        scale  = min(THUMB_W / img.width, THUMB_H / img.height)
        new_sz = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_sz, Image.LANCZOS)
        canvas  = Image.new("RGB", (THUMB_W, THUMB_H), (235, 235, 235))
        px = (THUMB_W - new_sz[0]) // 2
        py = (THUMB_H - new_sz[1]) // 2
        canvas.paste(resized, (px, py))
        return ImageTk.PhotoImage(canvas)

    # ── mouse / DnD ──────────────────────────────────────────────────────────

    def _on_press(self, event):
        cy  = int(self.canvas.canvasy(event.y))
        idx = self._hit_idx(event.x, cy)

        if idx is None:
            self._sel.clear()
            self._redraw()
            return

        ctrl  = bool(event.state & 0x4)
        shift = bool(event.state & 0x1)

        if ctrl:
            self._sel ^= {idx}
        elif shift and self._sel:
            anchor = min(self._sel)
            self._sel = set(range(min(anchor, idx), max(anchor, idx) + 1))
        else:
            if idx not in self._sel:
                self._sel = {idx}

        self._drag_src = idx
        self._redraw()

    def _on_drag(self, event):
        if self._drag_src is None:
            return

        cy  = int(self.canvas.canvasy(event.y))
        page = self.pages[self._drag_src]

        # Ghost thumbnail at pointer
        self.canvas.delete("ghost")
        if page.photo:
            self._ghost_id = self.canvas.create_image(
                event.x, cy, image=page.photo, anchor="center", tags="ghost")

        # Insertion indicator
        ins = self._insert_at(event.x, cy)
        if ins not in (self._drag_src, self._drag_src + 1):
            self._ins_idx = ins
            self._draw_insert_line(ins)
        else:
            self._ins_idx = None
            if self._line_id:
                self.canvas.delete(self._line_id)
                self._line_id = None

    def _on_release(self, event):
        if self._drag_src is None:
            return

        if self._ins_idx is not None:
            src = self._drag_src
            dst = self._ins_idx
            if dst > src:
                dst -= 1
            item = self.pages.pop(src)
            self.pages.insert(dst, item)
            self._sel = {dst}

        self.canvas.delete("ghost")
        if self._line_id:
            self.canvas.delete(self._line_id)

        self._drag_src = None
        self._ins_idx  = None
        self._line_id  = None
        self._redraw()
        self._update_status()

    def _on_rclick(self, event):
        cy  = int(self.canvas.canvasy(event.y))
        idx = self._hit_idx(event.x, cy)
        if idx is not None:
            if idx not in self._sel:
                self._sel = {idx}
                self._redraw()
            self._menu.post(event.x_root, event.y_root)

    # ── actions ──────────────────────────────────────────────────────────────

    def _select_all(self):
        self._sel = set(range(len(self.pages)))
        self._redraw()

    def _delete_sel(self):
        if not self._sel:
            return
        self.pages = [p for i, p in enumerate(self.pages) if i not in self._sel]
        self._sel.clear()
        self._redraw()
        self._update_status()

    def _rotate(self, degrees: int):
        for idx in self._sel:
            page = self.pages[idx]
            page.rotation = (page.rotation + degrees) % 360
            if page.thumb:
                page.photo = self._make_photo(page.thumb, page.rotation)
        self._redraw()

    def _save(self):
        if not self.pages:
            messagebox.showwarning("No pages", "Add pages before saving.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save PDF as…")
        if path:
            threading.Thread(target=self._write_pdf, args=(path,), daemon=True).start()

    def _write_pdf(self, output_path: str):
        try:
            writer = PdfWriter()
            # Cache open readers to avoid re-opening the same file repeatedly
            readers: dict[str, PdfReader] = {}
            for page in self.pages:
                if page.pdf_path not in readers:
                    readers[page.pdf_path] = PdfReader(page.pdf_path)
                pdf_page = readers[page.pdf_path].pages[page.page_index]
                if page.rotation:
                    pdf_page.rotate(page.rotation)
                writer.add_page(pdf_page)
            with open(output_path, "wb") as f:
                writer.write(f)
            self.after(0, lambda: messagebox.showinfo(
                "Saved", f"PDF saved:\n{output_path}"))
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror(
                "Error", f"Could not save PDF:\n{e}"))

    # ── status ───────────────────────────────────────────────────────────────

    def _update_status(self):
        n = len(self.pages)
        if n == 0:
            self._status.set("No pages loaded.")
            return
        counts: dict[str, int] = {}
        for p in self.pages:
            name = os.path.basename(p.pdf_path)
            counts[name] = counts.get(name, 0) + 1
        src_str = "  ·  ".join(f"{k} ({v})" for k, v in counts.items())
        self._status.set(f"{n} page{'s' if n != 1 else ''}  ·  {src_str}")
