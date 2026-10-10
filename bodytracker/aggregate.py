"""Aggregation layer: scan a directory, dedupe, normalize dates, group series."""
from __future__ import annotations

import glob
import os
import sys
from typing import Any

from .metrics_schema import METRIC_IDS
from .report_parser import parse_pdf, file_fingerprint

PDF_GLOBS = ("*.pdf", "*.PDF")


def scan_dir(directory: str) -> list[str]:
    files: set[str] = set()
    for pat in PDF_GLOBS:
        files |= set(glob.glob(os.path.join(directory, pat)))
    return sorted(files)


def dedupe(records: list[dict], *, verbose: bool = False) -> list[dict]:
    """Drop identical files and same-subject/same-date repeats (keep latest)."""
    kept: list[dict] = []
    by_key: dict[tuple[str, str], int] = {}
    seen_hash: set[str] = set()
    skipped: list[str] = []

    for rec in records:
        if rec.get("date") is None:
            skipped.append(rec.get("file", "?"))
            if verbose:
                print(f"  ? {os.path.basename(rec.get('file','?'))}: no date found -> skipped", file=sys.stderr)
            continue
        fp = rec.get("_fingerprint") or file_fingerprint(rec["file"])
        key = (rec.get("name") or "?", rec["date"])
        if fp in seen_hash:
            skipped.append(rec["file"])
            if verbose:
                print(f"  = {os.path.basename(rec['file'])}: identical file -> skipped", file=sys.stderr)
            continue
        seen_hash.add(fp)
        if key in by_key:
            idx = by_key[key]
            if rec.get("time", "") <= kept[idx].get("time", ""):
                skipped.append(rec["file"])
                if verbose:
                    print(f"  = {os.path.basename(rec['file'])}: same subject/date (older or equal time) -> skipped", file=sys.stderr)
                continue
            if verbose:
                print(f"  ~ {os.path.basename(rec['file'])}: same subject/date but later time -> replaces previous", file=sys.stderr)
            kept[idx] = rec
            continue
        by_key[key] = len(kept)
        kept.append(rec)

    kept.sort(key=lambda r: (r["date"], r.get("time", "")))
    if skipped and verbose:
        print(f"  skipped {len(skipped)} duplicate/unreadable file(s)", file=sys.stderr)
    return kept


def load_records(directory: str, *, verbose: bool = False) -> list[dict]:
    """Parse every PDF in `directory`, dedupe identical reports, sort by date."""
    raw = []
    for path in scan_dir(directory):
        try:
            raw.append(parse_pdf(path))
        except Exception as exc:  # keep scanning; a broken file must not kill the app
            if verbose:
                print(f"  ! {os.path.basename(path)}: {exc}", file=sys.stderr)
    return dedupe(raw, verbose=verbose)


def build_series(records: list[dict]) -> dict[str, list[dict]]:
    """Group time-series data per metric across all records.

    Returns {metric_id: [{date, value, status, range_lo, range_hi}, ...]} sorted
    by date. Dates are already ISO (YYYY-MM-DD) from the parser.
    """
    series: dict[str, list[dict]] = {mid: [] for mid in METRIC_IDS}
    for rec in records:
        for mid, slot in rec.get("metrics", {}).items():
            if mid in series and slot.get("value") is not None:
                series[mid].append({
                    "date": rec["date"],
                    "value": slot["value"],
                    "status": slot.get("status"),
                    "range_lo": slot.get("range_lo"),
                    "range_hi": slot.get("range_hi"),
                })
    return series


def latest_status(records: list[dict]) -> dict[str, dict]:
    """Latest known value/status/range per metric (for the status table)."""
    out: dict[str, dict] = {}
    for rec in records:
        for mid, slot in rec.get("metrics", {}).items():
            if slot.get("value") is not None:
                out[mid] = {"date": rec["date"], "value": slot["value"],
                            "status": slot.get("status"),
                            "range_lo": slot.get("range_lo"), "range_hi": slot.get("range_hi")}
    return out


def to_rows(records: list[dict]) -> list[dict[str, Any]]:
    """Flatten records into a CSV-friendly table (one row per report)."""
    rows = []
    for rec in records:
        row: dict[str, Any] = {
            "date": rec["date"], "time": rec.get("time", ""),
            "name": rec.get("name", ""), "sex": rec.get("sex", ""),
            "age": rec.get("age", {}).get("value") if isinstance(rec.get("age"), dict) else rec.get("age"),
            "height_cm": rec.get("height", {}).get("value") if isinstance(rec.get("height"), dict) else None,
            "weight_kg": rec.get("weight", {}).get("value") if isinstance(rec.get("weight"), dict) else None,
            "file": os.path.basename(rec["file"]), "source": rec.get("source"),
        }
        for mid, slot in rec.get("metrics", {}).items():
            row[mid] = slot.get("value")
            row[mid + "_status"] = slot.get("status")
        rows.append(row)
    return rows
