"""Plotly figure builder: time-series charts with X = measurement date.

One subplot per unit (kg, %, kCal, ...) sharing a common date axis, one trace
per selected metric. Plotly's legend supports click-to-toggle series hiding
directly in the browser. When exactly one metric is selected, its target
range [lo - hi] is drawn as a shaded band.
"""
from __future__ import annotations

import plotly as _plotly
from plotly import graph_objects as go
from plotly.subplots import make_subplots

from .metrics_schema import METRIC_LABEL, METRIC_UNIT
from .aggregate import build_series

# Stable palette cycled per metric (sorted metric ids -> deterministic colors).
PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#3a7ebf", "#e15759",
    "#76b7b2", "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab",
    "#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#e6a575",
    "#e9a3c2", "#da4453", "#7eb352", "#4f8c1f", "#b07aa8",
]

KG_TO_LB = 2.20462


def _color_for(mid: str) -> str:
    idx = sorted(METRIC_LABEL).index(mid)
    return PALETTE[idx % len(PALETTE)]


def unit_display(unit: str, prefer_lb: bool) -> tuple[str, float]:
    """Return (axis label, multiplier) applying the kg->lb display toggle."""
    if unit == "kg":
        return ("lb", KG_TO_LB) if prefer_lb else ("kg", 1.0)
    labels = {"%": "%", "kCal": "kCal", "cm": "cm", "cm2": "cm²",
              "level": "level", "years": "years", "ratio": "ratio",
              "score/10": "score /10"}
    return labels.get(unit, unit), 1.0


def build_figure(records: list[dict], metric_ids: list[str],
                 *, prefer_lb: bool = False, date_from: str | None = None,
                 date_to: str | None = None) -> "go.Figure":
    series_all = build_series(records)

    def in_window(d: str) -> bool:
        return ((date_from is None or d >= date_from) and
                (date_to is None or d <= date_to))

    series = {mid: [p for p in pts if in_window(p["date"])]
              for mid, pts in series_all.items() if mid in metric_ids}

    # group metrics by display unit -> one subplot per unit
    by_unit: dict[str, list[str]] = {}
    for mid in metric_ids:
        disp, _ = unit_display(METRIC_UNIT[mid], prefer_lb)
        by_unit.setdefault(disp, []).append(mid)
    units = sorted(by_unit, key=lambda u: (-len(by_unit[u]), u))

    rows = len(units)
    if rows == 0:
        fig = go.Figure()
        fig.update_layout(title="No metrics selected")
        return fig

    if rows == 1:
        fig = go.Figure()
        at = lambda r_i: (None, None)  # noqa: single subplot, default axes
    else:
        fig = make_subplots(
            rows=rows, cols=1, shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=[f"unit: {u}" for u in units])

    def add(trace, unit_idx: int):
        if rows == 1:
            fig.add_trace(trace)
        else:
            fig.add_trace(trace, row=unit_idx + 1, col=1)

    for u_i, disp_unit in enumerate(units):
        for mid in sorted(by_unit[disp_unit]):
            pts = series[mid]
            if not pts:
                continue
            _, mult = unit_display(METRIC_UNIT[mid], prefer_lb)
            color = _color_for(mid)
            add(go.Scatter(
                x=[p["date"] for p in pts],
                y=[round(p["value"] * mult, 3) for p in pts],
                mode="lines+markers", name=METRIC_LABEL[mid],
                line=dict(color=color, width=2.2),
                marker=dict(color=color, size=7),
                customdata=[p["status"] or "—" for p in pts],
                hovertemplate="%{x} = %{y} %{unit}\nstatus: %{customdata}",
                meta={"unit": disp_unit},
            ), u_i)

        # shaded target-range band when a single metric is selected
        if len(by_unit[disp_unit]) == 1:
            mid = by_unit[disp_unit][0]
            pts = [p for p in series[mid] if p["range_lo"] is not None]
            if len(pts) >= 2:
                _, mult = unit_display(METRIC_UNIT[mid], prefer_lb)
                xs = [p["date"] for p in pts]
                add(go.Scatter(x=xs, y=[p["range_hi"] * mult for p in pts],
                               mode="lines", line=dict(color="#9ca3af", width=1, dash="dot"),
                               showlegend=False,
                               hovertemplate="target max: %{y}"), u_i)
                add(go.Scatter(x=xs, y=[p["range_lo"] * mult for p in pts],
                               mode="lines", fill="tonexty",
                               line=dict(color="#9ca3af", width=1, dash="dot"),
                               fillcolor="rgba(148,163,163,0.15)",
                               name="target range",
                               hovertemplate="target min: %{y}"), u_i)

    # axis titles
    for u_i, disp_unit in enumerate(units):
        title = dict(text=f"Value ({disp_unit})", font=dict(size=11))
        if rows == 1:
            fig.update_yaxes(title=title)
        else:
            fig.update_yaxes(title=title, row=u_i + 1, secondary_y=False)

    fig.update_layout(
        xaxis=dict(title_text="Measurement date", type="date"),
        height=min(430 + 280 * (rows - 1), 1500),
        title=dict(text="Body composition time-series — click legend items to hide/show series",
                   font=dict(size=13)),
    )
    return fig
