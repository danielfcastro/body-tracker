"""Canonical metric schema for Evolt 360 body-composition reports (PT-BR template).

Every metric has a stable slug id, the label exactly as printed in the report
(used for the label-based fallback parser), aliases for tolerant matching, a
display unit and a dashboard group.
"""
from __future__ import annotations

import unicodedata

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------
# unit: canonical storage unit used by the parser ("kg", "%", "kCal", "cm",
# "cm2", "level", "score/10", "ratio", "years"). value_kind tells the value
# parser how to treat the slot (see value_parser for details).
METRICS: list[dict] = [
    # --- main body composition grid (slots 1-13) ---
    {"id": "lean_mass", "num": 1, "label": "MASSA MAGRA", "unit": "kg",
     "group": "overall", "aliases": ["massa magra", "lean mass"]},
    {"id": "muscle_mass", "num": 2, "label": "MASSA MUSCULAR ESQUELÉTICA", "unit": "kg",
     "group": "overall", "aliases": ["massa muscular esquelética", "muscle mass", "massa muscular"]},
    {"id": "protein_mass", "num": 3, "label": "PROTEÍNA", "unit": "kg",
     "group": "overall", "aliases": ["proteína", "protein mass"]},
    {"id": "mineral_mass", "num": 4, "label": "MINERAL", "unit": "kg",
     "group": "overall", "aliases": ["mineral", "bone mass"]},
    {"id": "water_mass", "num": 5, "label": "MASSA HÍDRICA", "unit": "kg",
     "group": "overall", "aliases": ["massa hídrica", "water mass"]},
    {"id": "fat_total", "num": 6, "label": "GORDURA TOTAL", "unit": "kg",
     "group": "overall", "aliases": ["gordura total", "total fat"]},
    {"id": "fat_subcutaneous", "num": 7, "label": "GORDURA SUBCUTÁNEA", "unit": "kg",
     "group": "overall", "aliases": ["gordura subcutánea", "subcutaneous fat"]},
    {"id": "fat_visceral", "num": 8, "label": "GORDURA VISCERAL", "unit": "kg",
     "group": "overall", "aliases": ["gordura visceral", "visceral fat"]},
    {"id": "visceral_fat_area", "num": 9, "label": "ÁREA DE GORDURA VISCERAL", "unit": "cm2",
     "group": "overall", "aliases": ["area de gordura visceral"]},
    {"id": "fat_total_pct", "num": 10, "label": "PERCENTUAL DE GORDURA TOTAL", "unit": "%",
     "group": "overall", "aliases": ["percentual de gordura total", "total fat %"]},
    {"id": "visceral_fat_level", "num": 11, "label": "NÍVEL DE GORDURA VISCERAL", "unit": "level",
     "group": "overall", "aliases": ["nivel de gordura visceral"]},
    {"id": "liquid_icf", "num": 12, "label": "LÍQUIDO INTRACELULAR (ICF)", "unit": "kg",
     "group": "overall", "aliases": ["liquid intracellular", "líquido intracelular"]},
    {"id": "liquid_ecf", "num": 13, "label": "LÍQUIDO EXTRACELULAR (ECF)", "unit": "kg",
     "group": "overall", "aliases": ["liquid extracellular", "líquido extracelular"]},
    # --- metabolic indicators (slots 14-17) ---
    {"id": "bmr", "num": 14, "label": "BMR (TAXA METABÓLICA BASAL)", "unit": "kCal",
     "group": "metabolic", "aliases": ["bmr", "taxa metabólica basal", "basal metabolic"]},
    {"id": "tee", "num": 15, "label": "TEE (GASTO ENERGÉTICO TOTAL)", "unit": "kCal",
     "group": "metabolic", "aliases": ["tee", "gasto energético total", "total energy"]},
    {"id": "biological_age", "num": 16, "label": "IDADE BIOLÓGICA", "unit": "years",
     "group": "metabolic", "aliases": ["idade biológica", "biological age"]},
    {"id": "bwi_score", "num": 17, "label": "NOTA BWI", "unit": "score/10",
     "group": "metabolic", "aliases": ["nota bwi", "bwi score", "bwi"]},
    # --- segmented analysis (slot 18) ---
    {"id": "seg_left_arm_lean", "num": 18, "label": "BRAÇO ESQUERDO - MASSA MAGRA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_left_arm_fat", "num": 18, "label": "BRAÇO ESQUERDO - GORDURA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_trunk_lean", "num": 18, "label": "TRONCO - MASSA MAGRA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_trunk_fat", "num": 18, "label": "TRONCO - GORDURA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_left_leg_lean", "num": 18, "label": "PERNA ESQUERDA - MASSA MAGRA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_left_leg_fat", "num": 18, "label": "PERNA ESQUERDA - GORDURA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_right_arm_lean", "num": 18, "label": "BRAÇO DIREITO - MASSA MAGRA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_right_arm_fat", "num": 18, "label": "BRAÇO DIREITO - GORDURA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_right_leg_lean", "num": 18, "label": "PERNA DIREITA - MASSA MAGRA", "unit": "kg",
     "group": "segmented", "aliases": []},
    {"id": "seg_right_leg_fat", "num": 18, "label": "PERNA DIREITA - GORDURA", "unit": "kg",
     "group": "segmented", "aliases": []},
    # --- body proportions (slots 19-20) ---
    {"id": "abdominal_circumference", "num": 19, "label": "CIRCUNFERÊNCIA ABDOMINAL", "unit": "cm",
     "group": "proportions", "aliases": ["circunferência abdominal"]},
    {"id": "waist_hip_ratio", "num": 20, "label": "RELAÇÃO CINTURA - QUADRIL", "unit": "ratio",
     "group": "proportions", "aliases": ["relação cintura", "waist hip ratio"]},
]

METRIC_IDS = [m["id"] for m in METRICS]
METRIC_BY_ID = {m["id"]: m for m in METRICS}
METRIC_LABEL = {m["id"]: m["label"] for m in METRICS}
METRIC_UNIT = {m["id"]: m["unit"] for m in METRICS}

GROUPS: dict[str, str] = {
    "overall": "Overall Body Composition",
    "segmented": "Segmented Fat & Muscle",
    "metabolic": "Metabolic Indicators",
    "proportions": "Body Proportions",
}

STATUS_VOCAB = {
    "optimal", "high", "low", "over range", "under range",
    "slightly high", "slightly low", "normal", "ideal",
}


def norm(s: str) -> str:
    """Lowercase, strip accents and collapse whitespace (for tolerant label matching)."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def group_metrics() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {g: [] for g in GROUPS}
    for m in METRICS:
        out[m["group"]].append(m["id"])
    return out
