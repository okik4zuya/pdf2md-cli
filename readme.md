# Ugly PDF

A free, offline PDF toolkit for Windows. No upload. No account. Just PDF tools.

---

## Download

**[Download UglyPDF v1.0.0](https://placeholder-link.com/UglyPDF.zip)**

- Windows 10 / 11
- ~40 MB (unzip and run — no installer, no Python needed)

---

## Features

| Tool | Description |
| --- | --- |
| **PDF → Markdown** | Extract text from PDFs. Auto OCR fallback for scanned files. |
| **Compress** | Reduce file size by stripping metadata and re-compressing streams. |
| **Merge** | Combine multiple PDFs into one. Reorder before merging. |
| **Split** | Split by every page or by custom ranges (e.g. `1-3, 5, 7-9`). |
| **Page Editor** | Drag pages to reorder, rotate, delete. Mix pages from multiple PDFs. |

---

## Usage (pre-built exe)

1. Download and unzip `UglyPDF.zip`
2. Open the `UglyPDF/` folder
3. Double-click `UglyPDF.exe`
4. Drag and drop PDF files onto the app

Output files are always saved next to the source PDF.

---

## Project Structure

```text
pdf2md-cli/
│
├── app/
│   ├── config.py          # paths for poppler / tesseract
│   ├── main.py            # app window + tab container
│   ├── toolbar.py         # top toolbar
│   ├── widgets.py         # shared: DropZone, LogPanel
│   ├── tab_convert.py     # PDF → Markdown
│   ├── tab_compress.py    # Compress
│   ├── tab_merge.py       # Merge
│   ├── tab_split.py       # Split
│   ├── tab_editor.py      # Page Editor
│   └── tab_about.py       # About
│
├── poppler/               # Poppler binaries (bundled)
├── tesseract/             # Tesseract OCR (bundled)
├── assets/
│   └── mascot.svg         # landing page mascot
│
├── pdf2md_gui.py          # entry point
├── pdf2md.py              # CLI version (legacy)
├── icon.ico               # app icon
├── index.html             # landing page
│
├── build.bat              # build standalone exe
├── setup.bat              # set up venv on a new machine
├── run.bat                # run from source (CLI mode)
├── register.bat           # add Windows context menu
├── unregister.bat         # remove Windows context menu
└── requirements.txt
```

---

## Development Setup

### 1. Clone the repo

```bat
git clone https://github.com/okik4zuya/uglypdf
cd uglypdf
```

### 2. Create virtual environment

```bat
python -m venv venv
```

Or use the provided script:

```bat
setup.bat
```

### 3. Install dependencies

```bat
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Add bundled binaries

Place the following in the project root:

**Poppler** — download from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)

```text
poppler/Library/bin/   ← extract here
```

**Tesseract** — download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

```text
tesseract/tesseract.exe
tesseract/tessdata/eng.traineddata
```

### 5. Run from source

```bat
venv\Scripts\python pdf2md_gui.py
```

---

## Build Standalone Exe

Requires UPX for smaller output (optional):

1. Download [upx.exe](https://github.com/upx/upx/releases) and place it in `upx/`
2. Run:

```bat
build.bat
```

Output: `dist/UglyPDF/` — copy this folder to any Windows machine.

---

## Dependencies

| Package | Purpose |
| --- | --- |
| `pdfminer.six` | Text extraction from PDFs |
| `pdf2image` | Render PDF pages to images (for OCR) |
| `Pillow` | Image processing |
| `pytesseract` | OCR via Tesseract |
| `pypdf` | Merge, split, compress, page editing |
| `tkinterdnd2` | Drag-and-drop support in the GUI |
| `pyinstaller` | Build standalone exe |

---

## Known Limitations

- Table structure is not preserved in Markdown output
- OCR quality depends on the scan resolution (300 DPI recommended)
- Compression results vary — some PDFs may not shrink significantly

---

## License

Free for personal use.
