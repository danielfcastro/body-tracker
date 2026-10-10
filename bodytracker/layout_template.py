"""Fixed Evolt 360 report template: slot anchors in normalized page coordinates.

The Evolt 360 PDFs are produced by a fixed PDFHummus template (A4, 595.2 x
841.92 pt). All *values* are real text in the PDF text layer (left-aligned at
fixed positions), while the *labels* are baked into the background image. We
therefore anchor every metric slot by its (x0, top) position, stored as
fractions of the page size so the mapping survives rescaling.

Coordinates were verified stable across every report in the corpus (0 misses
with a +/-2pt tolerance).
"""
from __future__ import annotations

PAGE_W, PAGE_H = 595.2, 841.92  # A4 pt, as emitted by the Evolt generator

# Header metadata slots: (key, x0, top) in pt.
HEADER_SLOTS: list[tuple[str, float, float]] = [
    ("date", 231.0, 60.3),      # "DD-MM-YYYY" + optional "HH:MM"
    ("name", 375.0, 60.3),      # subject name
    ("height", 21.0, 97.3),     # "177 cm"
    ("weight", 164.0, 97.3),    # "75.2 kg"
    ("age", 307.0, 97.3),       # integer years
    ("sex", 450.0, 97.3),       # Male / Female
]

# Row-based metric slots: (top, [(metric_id, x0), ...]) in pt.
# Main composition grid (3 columns) + segmented analysis (4 columns).
ROW_SLOTS: list[tuple[float, list[tuple[str, float]]]] = [
    (167.3, [("lean_mass", 21.0), ("fat_total", 164.0), ("visceral_fat_level", 307.0)]),
    (208.3, [("muscle_mass", 21.0), ("fat_subcutaneous", 164.0), ("liquid_icf", 307.0)]),
    (248.3, [("protein_mass", 21.0), ("fat_visceral", 164.0), ("liquid_ecf", 307.0)]),
    (288.3, [("mineral_mass", 21.0), ("visceral_fat_area", 164.0), ("bmr", 307.0)]),
    (328.4, [("water_mass", 21.0), ("fat_total_pct", 164.0), ("tee", 307.0)]),
    (417.3, [("seg_left_arm_lean", 23.0), ("seg_left_arm_fat", 138.0),
              ("seg_right_arm_lean", 355.0), ("seg_right_arm_fat", 469.0)]),
    (467.3, [("seg_trunk_lean", 23.0), ("seg_trunk_fat", 138.0),
              ("abdominal_circumference", 355.0), ("waist_hip_ratio", 469.0)]),
    (515.3, [("seg_left_leg_lean", 23.0), ("seg_left_leg_fat", 138.0),
              ("seg_right_leg_lean", 355.0), ("seg_right_leg_fat", 469.0)]),
]

# Dial gauges (right margin): single number near the anchor center.
DIAL_SLOTS: list[tuple[str, float, float]] = [
    ("biological_age", 518.0, 227.6),   # big "49" inside the gauge
    ("bwi_score", 511.6, 306.4),        # "7.0" over "10" inside the gauge
]

# Segment balance markers ("X" under EQUILIBRADO/DESEQUIBRADO legends).
BALANCE_SLOTS: list[tuple[str, float, float]] = [
    ("balance_left", 57.0, 378.8),
    ("balance_right", 417.0, 378.8),
]

# Tolerances in pt (scaled with the page at match time).
ANCHOR_TOL_X = 4.0
ANCHOR_TOL_Y = 4.0
LINE_TOL_Y = 4.0          # words considered part of the same slot line
MAX_SLOT_WIDTH = 170.0    # how far right a slot line may extend (pt)


def normalized() -> dict:
    """Return the template with all coordinates as page fractions (0..1)."""
    def fx(x: float) -> float:
        return x / PAGE_W

    def fy(y: float) -> float:
        return y / PAGE_H

    return {
        "header": [(k, fx(x), fy(t)) for k, x, t in HEADER_SLOTS],
        "rows": [(fy(t), [(mid, fx(x)) for mid, x in cols]) for t, cols in ROW_SLOTS],
        "dials": [(k, fx(x), fy(t)) for k, x, t in DIAL_SLOTS],
        "balance": [(k, fx(x), fy(t)) for k, x, t in BALANCE_SLOTS],
        "tol": {"x": fx(ANCHOR_TOL_X), "y": fy(ANCHOR_TOL_Y), "line": fy(LINE_TOL_Y),
                "width": fx(MAX_SLOT_WIDTH)},
    }
