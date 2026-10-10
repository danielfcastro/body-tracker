"""Body Tracker — interactive dashboard for Evolt 360 body-composition reports.

Run:  streamlit run app.py [reports_dir]
      (defaults to ./reports relative to this file; also reads BODYTRACKER_DIR)
"""
from __future__ import annotations

import os
import sys

import streamlit as st
import pandas as pd

from bodytracker import aggregate, plots
from bodytracker.metrics_schema import (GROUPS, METRIC_IDS, METRIC_LABEL,
                                        METRIC_UNIT, group_metrics)
from bodytracker.report_parser import parse_pdf

st.set_page_config(page_title="Body Tracker — Evolt 360", layout="wide")

# Auto-refresh: while the app is open, it re-runs itself on this interval, so
# dropping a new report PDF into reports/ is detected, parsed and charted
# automatically. Per-file parse results are cached by (path, mtime, size), so
# only new or modified files are re-parsed; everything else is served from
# cache. Set BODYTRACKER_AUTO_RERUN=0 to disable the loop.
AUTO_RERUN_SECONDS = int(os.environ.get("BODYTRACKER_AUTO_RERUN", "5"))

APP_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))


def _manifest(directory: str) -> tuple:
    """(path, mtime, size) for every PDF in the directory — the cache key.

    Any new or modified file changes the manifest, which invalidates the load
    cache and triggers a re-parse + chart update on the next run.
    """
    out = []
    for path in aggregate.scan_dir(directory):
        try:
            stat = os.stat(path)
            out.append((path, int(stat.st_mtime), stat.st_size))
        except OSError:
            continue
    return tuple(out)


@st.cache_data(show_spinner="Parsing PDF report…")
def _parse_one(path: str, mtime: int, size: int) -> dict:
    return parse_pdf(path)


@st.cache_data(show_spinner=False)
def _load(manifest: tuple) -> list[dict]:
    raw = []
    for path, mtime, size in manifest:
        try:
            rec = _parse_one(path, mtime, size)
            rec["file"] = path
            raw.append(rec)
        except Exception:
            continue
    return aggregate.dedupe(raw)


# ---------------------------------------------------------------------------
# Sidebar: filters
# ---------------------------------------------------------------------------
default_dir = os.environ.get("BODYTRACKER_DIR") or (
    sys.argv[1] if len(sys.argv) > 1 else os.path.join(APP_DIR, "reports"))
directory = st.sidebar.text_input("Reports directory", value=default_dir) or default_dir

manifest = _manifest(directory)
records = _load(manifest)
files = [path for path, _, _ in manifest]
if not records:
    st.error(f"No parsable reports found in `{directory}`. Point the sidebar "
             "field (or the BODYTRACKER_DIR env var) at the folder with the Evolt PDFs.")
    st.stop()

names = sorted({r.get("name") or "(unknown)" for r in records})
all_dates = sorted(r["date"] for r in records)

subject = st.sidebar.multiselect("Subject", names, default=names)
group_key = st.sidebar.radio("Metric group", list(GROUPS), index=0,
                             help="Predefined metric families; or pick metrics yourself.")
custom = st.sidebar.multiselect(
    "Or pick specific metrics (overrides group)",
    [METRIC_LABEL[m] for m in METRIC_IDS],
    help="Leave empty to use the group selected above.")
d_from = st.sidebar.date_input("From", value=pd.Timestamp(all_dates[0]),
                               min_value=pd.Timestamp(all_dates[0]),
                               max_value=pd.Timestamp(all_dates[-1]))
d_to = st.sidebar.date_input("To", value=pd.Timestamp(all_dates[-1]),
                             min_value=pd.Timestamp(all_dates[0]),
                             max_value=pd.Timestamp(all_dates[-1]))
prefer_lb = st.sidebar.toggle("Show masses in lb", value=False)

label_to_id = {METRIC_LABEL[m]: m for m in METRIC_IDS}
selected = [label_to_id[c] for c in custom] if custom else group_metrics()[group_key]

date_from, date_to = str(d_from), str(d_to)
records_w = [r for r in records
             if (r.get("name") or "(unknown)") in subject and date_from <= r["date"] <= date_to]
if not records_w:
    st.warning("No reports in the selected subject/date window.")
    st.stop()

# ---------------------------------------------------------------------------
# Header summary
# ---------------------------------------------------------------------------
latest, first = records_w[-1], records_w[0]
st.title(f"Body Tracker — {latest.get('name') or 'unknown subject'}")
st.caption(f"Parsed from {len(files)} PDF file(s) in `{directory}` · "
           f"{len(records_w)} reports in view · {all_dates[0]} → {all_dates[-1]}")

w_last = (latest.get("weight") or {}).get("value")
w_first = (first.get("weight") or {}).get("value")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Latest weight (kg)", f"{w_last:.1f}" if w_last else "—",
              f"{w_last - w_first:+.1f}" if w_last and w_first else None)
with c2:
    st.metric("Reports in view", len(records_w))
with c3:
    st.metric("Date span (days)",
              (pd.Timestamp(all_dates[-1]) - pd.Timestamp(all_dates[0])).days)
with c4:
    bmi = None
    h = (latest.get("height") or {}).get("value")
    if w_last and h:
        h_m = h / 100.0
        bmi = round(w_last / (h_m * h_m), 1)
    st.metric("BMI (latest)", str(bmi) if bmi else "—")

# ---------------------------------------------------------------------------
# Main time-series chart (X = measurement date, Y = metric value)
# ---------------------------------------------------------------------------
fig = plots.build_figure(records_w, selected, prefer_lb=prefer_lb,
                         date_from=date_from, date_to=date_to)
st.plotly_chart(fig, use_container_width=False, width="stretch")

# ---------------------------------------------------------------------------
# Latest evaluation per metric (value + status category + target range)
# ---------------------------------------------------------------------------
latest_map = aggregate.latest_status(records_w)
rows = []
for mid in selected:
    info = latest_map.get(mid)
    if not info:
        continue
    unit, mult = plots.unit_display(METRIC_UNIT[mid], prefer_lb)
    val = round(info["value"] * mult, 3)
    rng = (f"{info['range_lo']}–{info['range_hi']} {unit}"
           if info["range_lo"] is not None else "—")
    rows.append({"metric": METRIC_LABEL[mid], "value": f"{val} {unit}",
                 "status": info["status"] or "—", "target range": rng,
                 "measured": info["date"]})
if rows:
    st.subheader("Latest evaluation per metric")
    df = pd.DataFrame(rows)

    def _badge(status: str) -> str:
        icon = {"optimal": "🟢", "high": "🟠", "low": "🔵",
                "over range": "🔴", "under range": "🔵"}.get((status or "").lower(), "⚪")
        return f"{icon} {status}"

    df["status"] = df["status"].map(_badge)
    st.table(df)

# ---------------------------------------------------------------------------
# Raw data export
# ---------------------------------------------------------------------------
st.subheader("Data export")
dl = pd.DataFrame(aggregate.to_rows(records_w))
st.download_button("Download CSV (all metrics × dates)",
                   dl.to_csv(index=False).encode(), "bodytracker.csv",
                   "text/csv")
with st.expander("Parsed records (JSON sample)"):
    st.json(records_w[:2])

# ---------------------------------------------------------------------------
# Auto-refresh loop: after rendering, wait a few seconds and re-run, so new
# files dropped into reports/ are picked up without touching the browser.
# The manifest (paths+mtime+size) is the cache key: unchanged files are served
# from cache, only new/modified PDFs are re-parsed.
# ---------------------------------------------------------------------------
if AUTO_RERUN_SECONDS > 0:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    import time as _time

    if get_script_run_ctx() is not None:  # only inside a real Streamlit server
        _time.sleep(AUTO_RERUN_SECONDS)
        st.rerun()
