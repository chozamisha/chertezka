# -*- coding: utf-8 -*-
"""Знаки стержней ГОСТ 3212: гориз. JSON + верт. табл.7 (P4.5.1).

Горизонтальный loader не переписывался. Вертикальный — отдельный JSON/API.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .errors import MissingInputError, OutOfRangeError


def _json_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "knowledge"
        / "calc"
        / "sterzhni_horiz_syroe.json"
    )


def _vert_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "knowledge"
        / "calc"
        / "sterzhni_vert_lower.json"
    )


def load_horiz_syroe(path: Optional[Path] = None) -> dict[str, Any]:
    path = path or _json_path()
    if not path.is_file():
        raise MissingInputError(f"Таблица горизонтальных знаков не найдена: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_range(label: str) -> Tuple[float, float]:
    s = label.strip().replace("–", "-").replace("—", "-")
    # "0-40", "≤40" style not used in JSON keys; columns like "0-40"
    m = re.fullmatch(r"([\d.]+)\s*-\s*([\d.]+)", s)
    if not m:
        raise OutOfRangeError(f"Не разобран диапазон таблицы стержней: {label!r}")
    return float(m.group(1)), float(m.group(2))


def _pick_range_key(value: float, keys: list[str], *, what: str) -> str:
    """Выбор строки/столбца: значение в (lo, hi] кроме первого столбца 0-*, где [0, hi]."""
    if value is None or value <= 0:
        raise MissingInputError(f"{what} должен быть > 0 мм")
    for key in keys:
        lo, hi = _parse_range(key)
        if lo <= 0:
            if value <= hi + 1e-9:
                return key
        elif value > lo - 1e-12 and value <= hi + 1e-9:
            return key
    raise OutOfRangeError(
        f"{what}={value} мм вне диапазонов таблицы: {', '.join(keys)}"
    )


def horiz_print_l_max(
    section_mm: float,
    core_length_mm: float,
    path: Optional[Path] = None,
) -> Tuple[float, str, str]:
    """l_max горизонтального знака, мм.

    Returns: (l_max, row_key, col_key)
    """
    table = load_horiz_syroe(path)
    rows = table["rows"]
    cols: list[str] = list(table["columns_L"])
    row_key = _pick_range_key(section_mm, list(rows.keys()), what="Сечение знака D или (a+b)/2")
    col_key = _pick_range_key(core_length_mm, cols, what="Длина стержня L")
    col_idx = cols.index(col_key)
    cell = rows[row_key][col_idx]
    if cell is None:
        raise OutOfRangeError(
            f"В sterzhni_horiz_syroe.json нет значения для сечения {row_key}, "
            f"L={col_key} (ячейка пустая по ГОСТ/Михальцов)."
        )
    return float(cell), row_key, col_key


def check_horiz_print(
    l_print_mm: float,
    section_mm: float,
    core_length_mm: float,
    path: Optional[Path] = None,
) -> Tuple[float, list[str]]:
    """Проверить принятый L_PRINT ≤ l_max таблицы. Возвращает (l_max, issues)."""
    if l_print_mm is None:
        raise MissingInputError("L_PRINT (мм) обязателен — принятая длина горизонтального знака")
    if l_print_mm <= 0:
        raise OutOfRangeError(f"L_PRINT должен быть > 0 мм, получено {l_print_mm}")
    l_max, _row, _col = horiz_print_l_max(section_mm, core_length_mm, path=path)
    issues: list[str] = []
    if l_print_mm - 1e-9 > l_max:
        issues.append(
            f"L_PRINT={l_print_mm} мм > l_max={l_max} мм "
            f"(sterzhni_horiz_syroe / ГОСТ 3212, сеч.={section_mm}, L={core_length_mm}). STOP."
        )
    return l_max, issues


# ---------------------------------------------------------------------------
# P4.5.1 — вертикальные знаки (табл.7), отдельно от горизонтальных
# ---------------------------------------------------------------------------


@dataclass
class VertPrintLookup:
    """Результат lookup табл.7 (нижний вертикальный знак)."""

    status: str  # ok | unavailable | unverified | missing_input | out_of_range
    value_mm: Optional[float]
    D_mm: Optional[float]
    L_mm: Optional[float]
    row_key: Optional[str]
    col_key: Optional[str]
    cell: Optional[Dict[str, Any]]
    source_ref: str
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_vert_lower(path: Optional[Path] = None) -> dict[str, Any]:
    path = path or _vert_json_path()
    if not path.is_file():
        raise MissingInputError(f"Таблица вертикальных знаков не найдена: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def vert_print_h_max(
    D_mm: Optional[float],
    L_mm: Optional[float],
    path: Optional[Path] = None,
) -> VertPrintLookup:
    """h_max нижнего вертикального знака по табл.7 (не более).

    Не интерполирует. Для unavailable / unverified ячеек value_mm=None.
    """
    src = "sterzhni_vert_lower.json / ГОСТ 3212-92 табл.7 п.2.3"
    if D_mm is None or L_mm is None:
        return VertPrintLookup(
            status="missing_input",
            value_mm=None,
            D_mm=D_mm,
            L_mm=L_mm,
            row_key=None,
            col_key=None,
            cell=None,
            source_ref=src,
            reason="D и/или L Ст.2 отсутствуют",
        )
    if D_mm <= 0 or L_mm <= 0:
        return VertPrintLookup(
            status="missing_input",
            value_mm=None,
            D_mm=D_mm,
            L_mm=L_mm,
            row_key=None,
            col_key=None,
            cell=None,
            source_ref=src,
            reason=f"D и L должны быть > 0 (D={D_mm}, L={L_mm})",
        )

    table = load_vert_lower(path)
    rows = table["rows"]
    cols: list[str] = list(table["columns_L"])
    try:
        row_key = _pick_range_key(float(D_mm), list(rows.keys()), what="Сечение знака D или (a+b)/2")
        col_key = _pick_range_key(float(L_mm), cols, what="Высота стержня L")
    except (MissingInputError, OutOfRangeError) as exc:
        return VertPrintLookup(
            status="out_of_range",
            value_mm=None,
            D_mm=float(D_mm),
            L_mm=float(L_mm),
            row_key=None,
            col_key=None,
            cell=None,
            source_ref=src,
            reason=str(exc),
        )

    col_idx = cols.index(col_key)
    cell = rows[row_key][col_idx]
    page = table.get("page_pdf", "С.7")
    src_full = f"{src}; {page}; row={row_key}, col={col_key}"

    kind = cell.get("kind")
    verified = bool(cell.get("verified", False))
    if kind == "unavailable":
        return VertPrintLookup(
            status="unavailable",
            value_mm=None,
            D_mm=float(D_mm),
            L_mm=float(L_mm),
            row_key=row_key,
            col_key=col_key,
            cell=cell,
            source_ref=src_full,
            reason=(
                f"ячейка табл.7 «—» / не нормирована для D∈{row_key}, L∈{col_key}"
            ),
        )
    if kind != "max" or not verified or cell.get("value") is None:
        return VertPrintLookup(
            status="unverified",
            value_mm=None,
            D_mm=float(D_mm),
            L_mm=float(L_mm),
            row_key=row_key,
            col_key=col_key,
            cell=cell,
            source_ref=src_full,
            reason=(
                "ячейка не verified=true или не kind=max — "
                "числовой h_max не выдаётся (P4.5.1)"
            ),
        )
    return VertPrintLookup(
        status="ok",
        value_mm=float(cell["value"]),
        D_mm=float(D_mm),
        L_mm=float(L_mm),
        row_key=row_key,
        col_key=col_key,
        cell=cell,
        source_ref=src_full,
        reason="h_max из табл.7 (не более)",
    )


def check_vert_print_lower(
    h_print2_mm: Optional[float],
    D_mm: Optional[float],
    L_mm: Optional[float],
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Сравнить H_PRINT2 с h_max. Не изменяет H_PRINT2.

    Returns dict: status PASS|WARNING|NOT_CHECKED, lookup, comparison fields.
    """
    lookup = vert_print_h_max(D_mm, L_mm, path=path)
    out: Dict[str, Any] = {
        "lookup": lookup.as_dict(),
        "H_PRINT2": h_print2_mm,
        "h_max": lookup.value_mm,
        "comparison": None,
        "status": "NOT_CHECKED",
        "detail": lookup.reason,
        "source_ref": lookup.source_ref,
    }
    if lookup.status != "ok" or lookup.value_mm is None:
        out["status"] = "NOT_CHECKED"
        return out
    if h_print2_mm is None:
        out["status"] = "NOT_CHECKED"
        out["detail"] = "H_PRINT2 отсутствует"
        return out
    if h_print2_mm <= 0:
        out["status"] = "NOT_CHECKED"
        out["detail"] = f"H_PRINT2 должен быть > 0, получено {h_print2_mm}"
        return out

    ok = h_print2_mm - 1e-9 <= float(lookup.value_mm)
    out["comparison"] = {
        "op": "H_PRINT2 <= h_max",
        "H_PRINT2": h_print2_mm,
        "h_max": lookup.value_mm,
        "ok": ok,
    }
    if ok:
        out["status"] = "PASS"
        out["detail"] = (
            f"H_PRINT2={h_print2_mm} ≤ h_max={lookup.value_mm} "
            f"(табл.7 row={lookup.row_key}, col={lookup.col_key})"
        )
    else:
        out["status"] = "WARNING"
        out["detail"] = (
            f"H_PRINT2={h_print2_mm} > h_max={lookup.value_mm} мм "
            f"(табл.7 «не более»; D={D_mm}, L={L_mm}; геометрия не менялась)"
        )
    return out


def check_vert_print_upper(
    h_upper_mm: Optional[float],
    h_lower_mm: Optional[float],
    *,
    upper_present: bool,
) -> Dict[str, Any]:
    """П.2.3.3: H_upper ≥ 0.5 * H_lower — только если верхний знак есть."""
    src = "ГОСТ 3212-92 п.2.3.3 (PDF С.8)"
    if not upper_present:
        return {
            "status": "NOT_CHECKED",
            "detail": "верхний вертикальный знак отсутствует (схема A / не задан)",
            "source_ref": src,
            "rule": "H_upper >= 0.5 * H_lower",
        }
    if h_upper_mm is None or h_lower_mm is None:
        return {
            "status": "NOT_CHECKED",
            "detail": "нет H_upper и/или H_lower для п.2.3.3",
            "source_ref": src,
            "rule": "H_upper >= 0.5 * H_lower",
        }
    need = 0.5 * float(h_lower_mm)
    ok = float(h_upper_mm) + 1e-9 >= need
    return {
        "status": "PASS" if ok else "WARNING",
        "detail": (
            f"H_upper={h_upper_mm} {'≥' if ok else '<'} 0.5*H_lower={need}"
        ),
        "source_ref": src,
        "rule": "H_upper >= 0.5 * H_lower",
        "H_upper": h_upper_mm,
        "H_lower": h_lower_mm,
        "min_required": need,
        "ok": ok,
    }
