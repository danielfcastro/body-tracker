# Body Tracker

Local app that parses **Evolt 360 body-composition PDF reports** from
`reports/` and presents an **interactive time-series dashboard**
(X-axis = measurement date, Y-axis = metric value, click legend / filter
panel to show or hide metrics).

Built with Python + Streamlit + Plotly (interactive Chart.js-style charts
rendered in the browser). No server, no cloud, no API keys.

## Features

- **PDF parsing** of the full Evolt 360 template:
  - Header metadata: `NOME`, `DATA` (timestamp), `IDADE`, `SEXO`, `ALTURA`, `PESO`.
  - Main metrics: Massa Magra, Massa Muscular Esquelética, Proteína, Mineral,
    Massa Hídrica, Gordura Total, Gordura Subcutânea, Gordura Visceral,
    Área de Gordura Visceral, Percentual de Gordura Total, Nível de Gordura
    Visceral, Líquido Intracelular/Extracelular, BMR, TEE, Idade Biológica,
    Nota BWI.
  - Segmented analysis (left/right arm, trunk, left/right leg — lean & fat),
    body proportions (circunference abdominal, waist/hip ratio), balance markers.
- **Ambiguity handling**: `"20.3 / High"` → numeric `20.3` + classification
  `"High"`; target ranges `[28.6 - 34.9]`, percent notes `[ 19.4% ]`,
  parenthetical notes `(Less than 102 cm)` and units are separated cleanly.
- **Robustness ladder** (see `bodytracker/report_parser.py`):
  1. PDF text layer + fixed-template slot anchors (fast path — Evolt keeps all
     values as real text; only labels are images),
  2. OCR fallback (`pytesseract` on a rendered page) for image-only/scanned PDFs,
  3. label-based matching for unknown layouts.
- **Aggregation**: dates normalized to ISO `YYYY-MM-DD`, identical files and
  same-subject/same-date repeats deduped (latest scan kept), all series grouped
  per metric across every report.
- **Dashboard**: metric group toggles (Overall Body Composition / Segmented
  Fat & Muscle / Metabolic Indicators / Body Proportions), custom metric
  multiselect, date-range and subject filters, kg⇄lb display toggle,
  click-to-toggle legend on the charts, shaded target-range band when a single
  metric is selected, latest-status table with evaluation badges, CSV export.
- **Auto-refresh**: while the app is open it re-scans the reports directory
  every few seconds (self-rerun loop, default 5s, override with
  `BODYTRACKER_AUTO_RERUN` seconds, `0` disables). Dropping a new report PDF
  into `reports/` is detected, parsed and added to every chart automatically;
  per-file parse results are cached by `(path, mtime, size)` so only the new
  file is actually re-parsed.

## Repository structure

```
body-tracker/
├── app.py                       # Streamlit dashboard (entry point)
├── requirements.txt
├── README.md
├── reports/                     # ⚠ local-only input data — gitignored, NOT committed
└── bodytracker/                 # parsing + aggregation library
    ├── __init__.py
    ├── __main__.py              # CLI debug dump: python -m bodytracker reports
    ├── metrics_schema.py        # canonical metric ids, labels, units, groups
    ├── layout_template.py       # fixed Evolt template slot anchors
    ├── pdf_text.py              # text-layer extraction + OCR word boxes
    ├── value_parser.py          # "20.3 / High [9.7 - 14.5]" -> structured dict
    ├── report_parser.py         # words -> slots -> one record per PDF
    ├── aggregate.py             # scan dir, dedupe, ISO dates, series grouping
    └── plots.py                 # Plotly figure builder (time-series, bands)
```

## Setup & run (step by step)

1. **Create a virtual environment** (Python 3.11+):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   (`pytesseract` is only needed for the OCR fallback; the app runs without it
   as long as the PDFs have a text layer. If you use OCR, the system `tesseract`
   binary plus `eng.traineddata` must be available — set `TESSDATA_PREFIX`
   accordingly.)
3. **Launch the dashboard**:
   ```bash
   streamlit run app.py                    # uses ./reports
   streamlit run app.py /path/to/pdfs      # or pass another directory
   BODYTRACKER_DIR=/path/to/pdfs streamlit run app.py
   ```
   Open the printed local URL (default `http://localhost:8501`).
   Note: the sample reports are **not** in this repository (they are personal
   health data, kept local and gitignored) — put your Evolt PDFs in `reports/`
   or point the app at your own folder. New files are picked up automatically
   while the app is running (see Auto-refresh).
4. **Optional CLI sanity check** (no UI, dumps parsed JSON):
   ```bash
   python -m bodytracker reports           # all reports, deduped
   python -m bodytracker --single reports/16758976.pdf   # one file
   ```

## Using the dashboard

- Sidebar: pick a **metric group** or specific metrics, a **subject** and a
  **date window**; masses can be displayed in **lb**.
- The chart draws one trace per metric, grouped into subplots by unit
  (kg / % / kCal / …). **Click legend items to hide/show individual series**
  directly in the browser; hovering a point shows its evaluation status.
- Select exactly **one metric** to get its target range drawn as a shaded band.
- Below the chart: latest value + status badge + target range per metric, and a
  **CSV export** of the full parsed dataset.

## Parsing notes

- The Evolt PDFs are generated from a fixed template (PDFHummus, A4). Values
  live in the text layer at stable positions; the parser anchors every metric
  by normalized page coordinates (verified stable across the whole corpus), so
  no OCR is needed for the bundled reports.
- Dates are parsed from `DD-MM-YYYY HH:MM` and normalized to ISO
  `YYYY-MM-DD`; reports are sorted and deduped by (subject, date) keeping the
  latest scan of a day.
- If a report's text layer is missing/incomplete, the parser re-extracts the
  page with `pytesseract` at 200 dpi and matches the same slots; if even the
  template does not fit, it falls back to label→value proximity matching.
