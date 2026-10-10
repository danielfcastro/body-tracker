"""Per-PDF orchestration: word boxes -> fixed-template slots -> one record.

A record is a dict:
    {"file", "date" (ISO), "time", "name", "sex", "height_cm", "weight_kg",
     "age", "balance", "metrics": {metric_id: parsed_slot}, "source": "text"|"ocr"|"merged"}

Robustness ladder:
    1. text layer + fixed template  (fast, no OCR)
    2. OCR + fixed template         (image-only PDFs of the same template)
    3. OCR + label-based matching   (unknown layouts: find a metric label,
       take the nearest numeric token below/right of it)
The best-scoring strategy wins; results are merged slot-by-slot when both
text and OCR see the page.
"""
from __future__ import annotations

import hashlib
import re

from .layout_template import normalized
from .metrics_schema import METRIC_BY_ID, METRIC_IDS, norm
from .pdf_text import from_text_layer, from_ocr
from .value_parser import parse_slot_line

MIN_GOOD_SLOTS = 10  # below this the text layer is considered incomplete


def match_template(words: list[dict]) -> dict:
    """Assign words to fixed-template slots and parse each line."""
    tpl = normalized()
    tol = tpl["tol"]
    slots: dict[str, list[dict]] = {}

    def bucket(word: dict, key: str):
        slots.setdefault(key, []).append(word)

    # rows: assign each word to the nearest slot on its line
    for top, cols in tpl["rows"]:
        line_words = [w for w in words if abs(w["top"] - top) <= tol["line"]]
        for w in line_words:
            # choose the rightmost anchor that starts at/just before the word
            best = None
            for mid, x0 in cols:
                if w["x0"] >= x0 - tol["x"] and (best is None or x0 > best[1]):
                    best = (mid, x0)
            if best and w["x0"] - best[1] <= tol["width"]:
                bucket(w, best[0])

    # header slots: same line logic, single anchors
    for key, x0, top in tpl["header"]:
        for w in words:
            if abs(w["top"] - top) <= tol["line"] and x0 - tol["x"] <= w["x0"] <= x0 + tol["width"]:
                bucket(w, "hdr_" + key)

    # dials + balance markers: nearest word to the anchor center
    for key, x0, top in tpl["dials"] + tpl["balance"]:
        cands = [w for w in words if abs(w["x0"] + (w["x1"] - w["x0"]) / 2 - x0) <= 0.03
                 and abs(w["top"] + (w["bot"] - w["top"]) / 2 - top) <= 0.02]
        if cands:
            cands.sort(key=lambda w: (w["top"], w["x0"]))
            for w in cands:
                bucket(w, key)

    # ---- assemble ---------------------------------------------------------
    out: dict = {"metrics": {}}
    for key, ws in slots.items():
        ws.sort(key=lambda w: w["x0"])
        tokens = [w["text"] for w in ws]
        if key.startswith("hdr_"):
            hkey = key[4:]
            kind = "date" if hkey == "date" else "name" if hkey == "name" else "meta"
            p = parse_slot_line(tokens, kind)
            if p["value"] is not None:
                if hkey == "date":
                    out["date"] = p["value"]
                    if p["note"]:
                        out["time"] = p["note"]
                elif hkey == "name":
                    out["name"] = p["value"]
                elif hkey == "sex":
                    out["sex"] = p["value"]
                else:  # height / weight / age
                    try:
                        num = float(p["value"]) if p["value"] is not None else None
                    except (TypeError, ValueError):
                        num = None
                    if num is not None:
                        out[hkey] = {"value": num, "unit": p["unit"]}
        else:
            kind = "dial" if key in {"biological_age", "bwi_score"} else "metric"
            p = parse_slot_line(tokens, kind)
            if p["value"] is not None or p["status"] is not None:
                out["metrics"][key] = p
    for key in ("balance_left", "balance_right"):
        if key in slots:
            out.setdefault("balance", {})[key] = "marked"
    return out


def score(rec: dict) -> int:
    return sum(1 for m in rec.get("metrics", {}).values() if m.get("value") is not None)


def label_fallback(words: list[dict]) -> dict:
    """Strategy 3: unknown layouts. Find a metric label in the word stream,
    then take the nearest numeric token below/right of it."""
    out: dict = {"metrics": {}}
    joined = [(w["text"], w["x0"], w["top"]) for w in words]
    num_words = [w for w in words if re.match(r"^-?[\d.,]+%?$", w["text"])]
    for mid, m in METRIC_BY_ID.items():
        needles = [norm(a) for a in ([m["label"]] + m["aliases"]) if a]
        hit = None
        for i in range(len(joined)):
            window = " ".join(t for t, _, _ in joined[i:i + 4]).lower()
            for needle in needles:
                if needle and needle in window:
                    lx = min(joined[i + k][1] for k in range(min(4, len(joined) - i)))
                    ly = joined[i][2]
                    hit = (lx, ly)
                    break
            if hit:
                break
        if not hit:
            continue
        lx, ly = hit
        cands = [w for w in num_words
                 if w["x0"] >= lx - 0.02 and -0.01 <= w["top"] - ly <= 0.06]
        if not cands:
            continue
        best = min(cands, key=lambda w: ((w["top"] - ly) * 3 + abs(w["x0"] - lx)))
        line = [w for w in words if abs(w["top"] - best["top"]) <= 0.006 and w["x0"] >= lx]
        line.sort(key=lambda w: w["x0"])
        p = parse_slot_line([w["text"] for w in line[:12]], "metric")
        if p["value"] is not None:
            out["metrics"][mid] = p
    return out


def parse_pdf(path: str) -> dict:
    """Parse one report PDF into a record (see module docstring)."""
    words_text = from_text_layer(path, 0)
    rec = match_template(words_text) if words_text else {"metrics": {}}
    src = "text" if score(rec) >= MIN_GOOD_SLOTS else "text?"

    if score(rec) < MIN_GOOD_SLOTS:
        words_ocr = from_ocr(path, 0)
        if words_ocr:
            rec_ocr = match_template(words_ocr)
            if score(rec_ocr) > score(rec):
                rec = rec_ocr
                src = "ocr"
            if score(rec) < MIN_GOOD_SLOTS:
                rec_lb = label_fallback(words_ocr)
                if score(rec_lb) > score(rec):
                    rec = rec_lb
                    src = "ocr+labels"

    rec["file"] = path
    rec["source"] = src
    return rec


def file_fingerprint(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
