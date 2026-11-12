"""Lookup helpers for GOST 26645-85 table 6 (general machining allowance)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_TABLE: dict[str, Any] | None = None


def _table_path() -> Path:
    # cad_subsystem/eskd_cad/calc → knowledge/calc JSON (vendored table 6)
    return Path(__file__).resolve().parents[1] / "knowledge" / "calc" / "gost_26645_table6_full.json"


def load_table6() -> dict[str, Any]:
    global _TABLE
    if _TABLE is None:
        _TABLE = json.loads(_table_path().read_text(encoding="utf-8"))
    return _TABLE


def _parse_tol_bounds(label: str) -> tuple[float | None, float | None]:
    s = label.replace(",", ".").strip()
    if s.lower().startswith("до "):
        return (None, float(re.findall(r"[\d.]+", s)[0]))
    m = re.search(r"св\.\s*([\d.]+)\s*до\s*([\d.]+)", s, flags=re.I)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    return (None, None)


def find_tolerance_row(t: float) -> dict[str, Any] | None:
    """Return finishes dict for general tolerance t (mm)."""
    rows = load_table6()["rows"]
    for row in rows:
        lo, hi = _parse_tol_bounds(row["tolerance"])
        if lo is None and hi is not None and t <= hi + 1e-9:
            return row
        if lo is not None and hi is not None and t > lo - 1e-12 and t <= hi + 1e-9:
            return row
    return None


def allowance_mm(
    general_tolerance_mm: float,
    finish: str,
    allowance_row: int,
) -> float | None:
    """
    Return table-6 general allowance on side (mm) or None if not standardized.

    finish: Черновая | Получистовая | Чистовая | Тонкая
    allowance_row: 1..18
    """
    row = find_tolerance_row(general_tolerance_mm)
    if not row:
        return None
    finishes = row["finishes"]
    if finish not in finishes:
        # До 0.10 has no Получистовая
        return None
    key = str(int(allowance_row))
    return finishes[finish].get(key)


if __name__ == "__main__":
    # sanity: Св. 0.18..0.20 / Чистовая / ряд 9 → 1.6
    v = allowance_mm(0.19, "Чистовая", 9)
    print("0.19/Чистовая/9 =", v)
    assert v == 1.6
    print("ok")
