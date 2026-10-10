"""Body-tracker: parse Evolt 360 body-composition PDF reports and chart them.

Run `python -m bodytracker <reports_dir>` for a quick CLI dump, or launch the
Streamlit dashboard with `streamlit run app.py`.
"""
from __future__ import annotations

__all__ = ["metrics_schema", "layout_template", "pdf_text", "value_parser",
           "report_parser", "aggregate"]
