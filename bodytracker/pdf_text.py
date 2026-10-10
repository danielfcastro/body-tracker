"""Word-with-coordinates extraction from PDFs.

Strategy 1 (primary): the PDF text layer via pdfplumber. Evolt reports keep
every numeric value as real text; only the labels are images.
Strategy 2 (fallback): lightweight OCR with pytesseract on a rendered page,
used when the text layer is missing/incomplete (scanned or image-only PDFs).

Both strategies return the same shape: a list of word boxes normalized to
page fractions so the fixed-template slot matcher can consume either.
"""
from __future__ import annotations

import subprocess
from typing import List

Word = dict  # {"text": str, "x0": float, "top": float, "x1": float, "bot": float} in page fractions


def from_text_layer(path: str, page_index: int = 0) -> list[Word]:
    """Extract words from the embedded text layer, normalized to 0..1 page coords."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        if page_index >= len(pdf.pages):
            return []
        page = pdf.pages[page_index]
        w, h = float(page.width), float(page.height)
        if w <= 0 or h <= 0:
            return []
        out: List[Word] = []
        for wd in page.extract_words():
            text = (wd.get("text") or "").strip()
            if not text:
                continue
            out.append({
                "text": text,
                "x0": wd["x0"] / w, "x1": wd["x1"] / w,
                "top": wd["top"] / h, "bot": wd["bottom"] / h,
            })
        return out


def from_ocr(path: str, page_index: int = 0, dpi: int = 200) -> list[Word]:
    """OCR fallback: render the page to an image, run tesseract word boxes.

    Uses pypdfium2 for rendering (already a pdfplumber dependency) and pytesseract
    for word-level boxes. Returns [] when the OCR toolchain is unavailable so
    callers can degrade gracefully.
    """
    try:
        import pytesseract
        import pypdfium2
    except ImportError:
        return []

    try:
        doc = pypdfium2.PdfDocument(path)
        page = doc[page_index]
        scale = dpi / 72.0
        img = page.render(scale=scale).to_pil()
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config="--psm 6")
    except Exception:
        return []

    try:
        mb = page.get_mediabox()
    except AttributeError:
        mb = page.mediabox
    pw, ph = float(mb[2]), float(mb[3])
    if pw <= 0 or ph <= 0:
        return []
    out: List[Word] = []
    n = len(data.get("text", []))
    for i in range(n):
        text = (data["text"][i] or "").strip()
        conf = data.get("conf", ["-1"] * (n + 1))[i]
        try:
            if int(float(conf)) < 30:
                continue
        except (ValueError, TypeError):
            pass
        if not text:
            continue
        x, y = data["left"][i], data["top"][i]
        wdt, hgt = data["width"][i], data["height"][i]
        out.append({
            "text": text,
            "x0": (x / scale) / pw, "x1": ((x + wdt) / scale) / pw,
            "top": (y / scale) / ph, "bot": ((y + hgt) / scale) / ph,
        })
    return out
