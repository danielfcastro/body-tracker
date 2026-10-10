"""CLI debug entry: python -m bodytracker [reports_dir] -> JSON dump."""
from __future__ import annotations

import json
import sys

from .aggregate import load_records
from .report_parser import parse_pdf


def main(argv: list[str]) -> int:
    directory = argv[1] if len(argv) > 1 else "reports"
    if "--single" in argv:
        print(json.dumps(parse_pdf(argv[-1]), ensure_ascii=False, indent=2))
        return 0
    records = load_records(directory, verbose=True)
    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
