"""Turn a line of extracted words for one report slot into structured data.

Slot lines look like one of:
    "58.1 / Optimal [51.1 - 62.5]"        value + status + target range
    "14.6 [ 19.4% ]"                      value + share-of-total note
    "22.7% / High [15 - 20]"              percent value + status + range
    "1624 kCal"                           value + unit
    "88.7 cm (Less than 102 cm)"          value + unit + textual note
    "12 / Over Range"                     value + status (no range)
    "7.0"                                 dial gauge value
    "07-10-2026 04:52"                    header date
    "177 cm" / "75.2 kg" / "49" / "Male" header metadata
    "Daniel"                              free text (name)

The parser is deliberately tolerant: it never raises, it returns whatever it
could understand and keeps the raw string for display/debug.
"""
from __future__ import annotations

import re

from .metrics_schema import STATUS_VOCAB

_NUM = r"-?\d+(?:[.,]\d+)?"
_DATE_RE = re.compile(r"^(?P<d>\d{1,2})[./-](?P<m>\d{1,2})[./-](?P<y>\d{4})$")
_TIME_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<mi>\d{2})(?::\d{2})?$")
_NUMPCT_RE = re.compile(rf"^({_NUM})%[/|]?$")
_NUM_RE = re.compile(rf"^({_NUM})[/|]?$")
_RANGE_RE = re.compile(rf"\[\s*({_NUM})\s*-\s*({_NUM})\s*\]")
_PAREN_RE = re.compile(r"\(([^)]*)\)")
_UNIT_TOKENS = {"kg", "kcal", "kcal", "cm", "cm2", "lbs", "lb", "%"}


def _num(s: str) -> float | None:
    s = s.strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_slot_line(tokens: list[str], kind: str) -> dict:
    """Parse one slot. `kind` is 'metric', 'date', 'name', 'meta' or 'dial'."""
    raw = " ".join(tokens)
    out = {"raw": raw, "value": None, "unit": None, "status": None,
           "range_lo": None, "range_hi": None, "note": None}

    if not tokens:
        return out

    # ---- header: date ----------------------------------------------------
    if kind == "date":
        m = _DATE_RE.match(tokens[0])
        if m:
            y, mo, d = int(m["y"]), int(m["m"]), int(m["d"])
            # Evolt prints DD-MM-YYYY; guard against MM-DD misread by range check
            if mo > 12 >= d:
                mo, d = d, mo
            out["value"] = f"{y:04d}-{mo:02d}-{d:02d}"
            if len(tokens) > 1 and _TIME_RE.match(tokens[1]):
                out["note"] = tokens[1]  # time of measurement
        return out

    # ---- header: name ----------------------------------------------------
    if kind == "name":
        out["value"] = raw
        return out

    # ---- header: sex -----------------------------------------------------
    if kind == "meta" and raw.lower() in {"male", "female"}:
        out["value"] = raw.capitalize()
        return out

    # ---- everything else starts with a numeric value ---------------------
    first = tokens[0]
    pct = _NUMPCT_RE.match(first)
    m_val = _NUM_RE.match(first)
    if pct:
        out["value"] = _num(pct.group(1))
        out["unit"] = "%"
        rest = tokens[1:]
    elif m_val:
        out["value"] = _num(m_val.group(1))
        rest = tokens[1:]
        # consume an immediately following unit word ("kg", "cm", "kCal")
        if rest and rest[0].lower().rstrip(").") in _UNIT_TOKENS:
            u = rest[0].lower().rstrip(").")
            out["unit"] = "kCal" if u in {"kcal", "kcal"} else u
            rest = rest[1:]
    else:
        # no numeric value at all (e.g. OCR noise) -> keep raw only
        return out

    # ---- status: words after '/' until a bracket -------------------------
    i = 0
    if i < len(rest) and rest[i] == "/":
        i += 1
        words: list[str] = []
        while i < len(rest) and not re.match(r"^[\[(]", rest[i]):
            words.append(rest[i])
            i += 1
        status = " ".join(words).strip()
        if status and status.lower() in STATUS_VOCAB:
            out["status"] = status
    # some OCR passes drop the slash; accept a bare status word right after value
    elif i < len(rest) and rest[i].lower() in STATUS_VOCAB:
        words = []
        while i < len(rest) and not re.match(r"^[\[(]", rest[i]):
            words.append(rest[i])
            i += 1
        status = " ".join(words).strip()
        if status.lower() in STATUS_VOCAB:
            out["status"] = status

    tail = " ".join(rest[i:])
    # ---- target range [lo - hi] ------------------------------------------
    m = _RANGE_RE.search(tail) or _RANGE_RE.search(raw)
    if m:
        out["range_lo"], out["range_hi"] = _num(m.group(1)), _num(m.group(2))
    # ---- parenthetical notes: "(Less than 102 cm)" or "[ 19.4% ]" -------
    pm = _PAREN_RE.search(raw)
    if pm:
        out["note"] = pm.group(1).strip()
    bm = re.search(r"\[\s*({_NUM}%)\s*\]", raw)
    if bm:
        out["note"] = (out["note"] + " | " if out["note"] else "") + bm.group(1) + " of total"
    return out
