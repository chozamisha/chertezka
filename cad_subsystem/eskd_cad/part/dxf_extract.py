# -*- coding: utf-8 -*-
"""Надписи листа детали: размерные числа, выноски отверстий, шероховатость."""
from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from .dxf_geom import TextItem, in_box
from .part_spec import DimensionReading

_DIA_SIGN = r"(?:%%[cC]|⌀|Ø|ø|∅)"
_NUM = r"([0-9]+(?:[.,][0-9]+)?)"
_DIAM = re.compile(rf"^{_DIA_SIGN}\s*{_NUM}\*?$")
_RAD = re.compile(rf"^R\s*{_NUM}\*?$")
_LIN = re.compile(rf"^{_NUM}\*?$")
_ROUGH = re.compile(r"^R[az]\s*[0-9]+(?:[.,][0-9]+)?$")
_HOLES = re.compile(rf"^([0-9]+)\s*отв\.?\s*(.*)$", re.I)
_HOLE_D = re.compile(rf"^{_DIA_SIGN}\s*{_NUM}")
_THREAD = re.compile(r"^(М\s*([0-9]+(?:[.,][0-9]+)?)[^,;]*)", re.I)
_CBORE = re.compile(rf"(?:цек\.?|⌴)\s*{_DIA_SIGN}?\s*{_NUM}(?:\s*[×xXх]\s*{_NUM})?", re.I)
_TT_LINE = re.compile(r"^\s*(\d+\.\s+\D|\s{2,})")


def _f(s: str) -> float:
    return float(s.replace(",", "."))


def clean(text: str) -> str:
    return text.replace("%%c", "⌀").replace("%%C", "⌀").replace("%%d", "°").replace("%%p", "±")


def parse_hole_note(text: str) -> Optional[dict]:
    """«6 отв. ⌀12, цек. ⌀24×16» или «4 отв. М8-7Н» → число, диаметр, цековка, резьба."""
    m = _HOLES.match(text.strip())
    if not m:
        return None
    out = {"n": int(m.group(1)), "label": clean(text.strip())}
    rest = m.group(2).strip()
    md, mt = _HOLE_D.match(rest), _THREAD.match(rest)
    if md:
        out["d"] = _f(md.group(1))
    elif mt:
        out["thread"] = mt.group(1).strip()
        out["d"] = _f(mt.group(2))
    mc = _CBORE.search(rest)
    if mc:
        out["d_cb"] = _f(mc.group(1))
        if mc.group(2):
            out["cb_depth"] = _f(mc.group(2))
    return out


def readings_from_texts(texts: Sequence[TextItem], stamp_box=None) -> List[DimensionReading]:
    """Надписи поля чертежа без основной надписи и строк ТТ."""
    out: List[DimensionReading] = []
    for t in texts:
        if in_box(t, stamp_box) or _TT_LINE.match(t.text):
            continue
        s = t.text.strip()
        kind, value = None, None
        if _ROUGH.match(s):
            kind = "roughness"
        elif _HOLES.match(s):
            kind = "holes"
        elif _DIAM.match(s):
            kind, value = "diameter", _f(_DIAM.match(s).group(1))
        elif _RAD.match(s):
            kind, value = "radius", _f(_RAD.match(s).group(1))
        elif _LIN.match(s):
            kind, value = "linear", _f(_LIN.match(s).group(1))
        if kind:
            out.append(DimensionReading(clean(s), kind, value, round(t.x, 2), round(t.y, 2)))
    return out


def tt_lines(texts: Sequence[TextItem], stamp_box=None) -> List[str]:
    """Строки технических требований детали сверху вниз."""
    rows = [t for t in texts if not in_box(t, stamp_box) and abs(t.rot) < 1 and _TT_LINE.match(t.text)]
    return [clean(t.text) for t in sorted(rows, key=lambda t: -t.y)]


class Snapper:
    """Привязка измеренного по геометрии значения к размерному числу с чертежа."""

    def __init__(self, readings: List[DimensionReading]):
        self.readings = readings

    def snap(self, measured: float, kind: str, name: str) -> Tuple[float, str]:
        tol = max(0.3, 0.004 * abs(measured))
        best = None
        for r in self.readings:
            if r.kind != kind or r.value_mm is None or abs(r.value_mm - measured) > tol:
                continue
            # уже занятое число годится (15 — и толщина фланца, и стенка), свободное лучше
            rank = (abs(r.value_mm - measured), bool(r.used_for))
            if best is None or rank < best[0]:
                best = (rank, r)
        if best is None:
            return round(measured, 2), "геометрия DXF, размерного числа нет"
        r = best[1]
        r.used_for = f"{r.used_for}, {name}" if r.used_for else name
        return r.value_mm, f"размерное число «{r.raw_text}» + геометрия DXF"

    def score(self, measured: float, kind: str) -> bool:
        tol = max(0.3, 0.004 * abs(measured))
        return any(r.kind == kind and r.value_mm is not None and abs(r.value_mm - measured) <= tol
                   for r in self.readings)
