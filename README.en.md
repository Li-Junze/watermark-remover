# Watermark Remover

[![CI](https://github.com/Li-Junze/watermark-remover/actions/workflows/ci.yml/badge.svg)](https://github.com/Li-Junze/watermark-remover/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)

A **fully local** desktop tool that removes **flat-color watermarks** from PDFs
and images: pick the watermark color on the page, set a tolerance, and every
pixel within that color range is replaced with a target color (white by
default). All processing happens offline — **no data ever leaves your machine**.

> 中文文档：[README.md](README.md)

## Features

- 🎨 One-click color picking + live tolerance preview
- 📄 Multi-page PDF processing, optionally synced across all pages
- ✂️ Region of interest (ROI) — only process inside a dragged rectangle
- 🌡️ Edge feathering for soft, natural transitions
- 🔍 Before/after compare view with a draggable divider
- 💾 Export current page as PNG or all pages as a merged PDF
- 🔒 100% offline — safe for sensitive documents
- ⌨️ Keyboard shortcuts + drag & drop to open files

## Install & Run

```bash
git clone https://github.com/Li-Junze/watermark-remover.git
cd watermark-remover
pip install -r requirements.txt
python run.py                # or: python run.py file.pdf
```

Or install as a command:

```bash
pip install .
watermark-remover
```

Requires Python 3.9+.

## Usage

> No watermarked file at hand? The repo includes a demo file
> [`docs/sample-watermarked.pdf`](docs/sample-watermarked.pdf) to try it out.

1. **Open** — drag a PDF/image into the window, click *Open*, or pass a path on the command line
2. **Pick** — with the *Pick color* mode, click the watermark on the page
3. **Tolerance** — increase until the watermark disappears without harming the text
4. Optional: switch to *ROI* mode to restrict processing, or *Compare* view to inspect the result
5. **Export** — current page as PNG, or all pages merged into a PDF

| Shortcut | Action |
| --- | --- |
| `Ctrl + O` | Open file |
| `Ctrl + Wheel` | Free zoom |
| `Ctrl + =` / `Ctrl + -` | Zoom in / out |
| `Ctrl + 0` | Fit width |
| `Ctrl + 1` | Actual size |

## How it works

For each pixel the max channel difference from the target color
`max(|ΔR|, |ΔG|, |ΔB|)` is computed; pixels at or below the tolerance are
blended toward the fill color, with a linear soft band when feathering is
enabled. PDFs are rasterized with PyMuPDF and re-composited on export.

## Limitations

- Works best on **solid-color** watermarks; image or semi-transparent logo
  watermarks cannot be removed by color matching
- Large tolerances may affect text with similar colors — use preview & ROI
- Exported PDFs are rasterized, so their size is comparable to scanned files

## License

[MIT](LICENSE) © 2026 Li-Junze
