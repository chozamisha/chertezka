# -*- coding: utf-8 -*-
"""Best-effort извлечение размеров и штампа из DXF детали."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Tuple

from .part_spec import DimensionReading

_DIAM = re.compile(r"(?:%%[cC]|⌀)\s*([0-9]+(?:[.,][0-9]+)?)")
_RAD = re.compile(r"^[Rr]\s*([0-9]+(?:[.,][0-9]+)?)$")
_NUM = re.compile(r"^([0-9]+(?:[.,][0-9]+)?)$")
_THREAD = re.compile(r"М\s*([0-9]+)", re.I)
_CB = re.compile(
    r"([0-9]+)\s*отв\.?\s*(?:%%[cC]|⌀)\s*([0-9]+(?:[.,][0-9]+)?)"
    r".*?(?:цек\.?|cek\.?)\s*(?:%%[cC]|⌀)?\s*([0-9]+(?:[.,][0-9]+)?)\s*[×xX]\s*([0-9]+(?:[.,][0-9]+)?)",
    re.I | re.S,
)


def _f(s: str) -> float:
    return float(s.replace(",", "."))


def _iter_texts(msp) -> Iterable[str]:
    for e in msp:
        t = e.dxftype()
        if t == "TEXT":
            yield str(e.dxf.text or "")
        elif t == "MTEXT":
            yield str(e.text or "")


def extract_readings(dxf_path: str | Path) -> List[DimensionReading]:
    """Снять TEXT/MTEXT с DXF. Без OCR; PDF сюда не подаём."""
    try:
        import ezdxf
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Нужен пакет ezdxf: pip install ezdxf") from exc

    path = Path(dxf_path)
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    out: List[DimensionReading] = []

    for raw in _iter_texts(msp):
        text = raw.strip()
        if not text:
            continue
        flat = text.replace("\n", " ")

        if "ПП-" in flat or re.search(r"[A-ZА-Я]{2,}-\d", flat):
            # designation-like
            if re.fullmatch(r"ПП-\d{9}-\d{2}", flat) or flat.startswith("ПП-"):
                out.append(
                    DimensionReading(
                        raw_text=flat,
                        kind="designation",
                        confidence=0.95,
                        hint="штамп/обозначение",
                    )
                )
                continue

        if flat in ("СЧ15", "СЧ20", "СЧ25") or flat.startswith("ГОСТ 1412"):
            out.append(
                DimensionReading(
                    raw_text=flat,
                    kind="material",
                    confidence=0.9,
                    hint="штамп материал",
                )
            )
            continue

        m_cb = _CB.search(flat)
        if m_cb:
            out.append(
                DimensionReading(
                    raw_text=flat,
                    kind="other",
                    confidence=0.85,
                    hint=(
                        f"holes n={m_cb.group(1)} d={_f(m_cb.group(2))} "
                        f"cb={_f(m_cb.group(3))}x{_f(m_cb.group(4))}"
                    ),
                )
            )
            # also expose numeric pieces
            out.append(
                DimensionReading(
                    raw_text=m_cb.group(2),
                    kind="diameter",
                    value_mm=_f(m_cb.group(2)),
                    confidence=0.8,
                    hint="thru_hole",
                )
            )
            out.append(
                DimensionReading(
                    raw_text=m_cb.group(3),
                    kind="diameter",
                    value_mm=_f(m_cb.group(3)),
                    confidence=0.8,
                    hint="counterbore_d",
                )
            )
            out.append(
                DimensionReading(
                    raw_text=m_cb.group(4),
                    kind="linear",
                    value_mm=_f(m_cb.group(4)),
                    confidence=0.8,
                    hint="counterbore_depth",
                )
            )
            continue

        if _THREAD.search(flat) and "отв" in flat.lower():
            out.append(
                DimensionReading(
                    raw_text=flat,
                    kind="thread",
                    confidence=0.8,
                    hint="machined_threads",
                )
            )
            continue

        for m in _DIAM.finditer(flat):
            out.append(
                DimensionReading(
                    raw_text=flat if flat != m.group(0) else f"⌀{m.group(1)}",
                    kind="diameter",
                    value_mm=_f(m.group(1)),
                    confidence=0.9 if flat.startswith("%%") or "⌀" in flat or "%%c" in flat.lower() else 0.75,
                    hint="diameter_text",
                )
            )

        m_r = _RAD.match(flat)
        if m_r:
            out.append(
                DimensionReading(
                    raw_text=flat,
                    kind="radius",
                    value_mm=_f(m_r.group(1)),
                    confidence=0.85,
                    hint="radius",
                )
            )
            continue

        m_n = _NUM.match(flat)
        if m_n:
            val = _f(m_n.group(1))
            # Голое число на поле — линейный размер (мм). Массу не угадываем
            # без контекста штампа: иначе 15/100 уезжают из linears.
            out.append(
                DimensionReading(
                    raw_text=flat,
                    kind="linear",
                    value_mm=val,
                    confidence=0.55,
                    hint="bare_number",
                )
            )
            continue

        if flat in ("Корпус", "Колесо", "Отливка"):
            out.append(
                DimensionReading(
                    raw_text=flat,
                    kind="other",
                    confidence=0.7,
                    hint="name",
                )
            )

    return out


def diameter_values(readings: List[DimensionReading]) -> List[float]:
    return sorted({r.value_mm for r in readings if r.kind == "diameter" and r.value_mm is not None})


def linear_values(readings: List[DimensionReading]) -> List[float]:
    return sorted({r.value_mm for r in readings if r.kind == "linear" and r.value_mm is not None})


def pick_designation(readings: List[DimensionReading]) -> str:
    for r in readings:
        if r.kind == "designation":
            return r.raw_text.strip()
    return ""


def pick_materials(readings: List[DimensionReading]) -> Tuple[str, ...]:
    mats = []
    for r in readings:
        if r.kind == "material":
            mats.append(r.raw_text.strip())
    # unique preserve order
    seen = set()
    out = []
    for m in mats:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return tuple(out)
