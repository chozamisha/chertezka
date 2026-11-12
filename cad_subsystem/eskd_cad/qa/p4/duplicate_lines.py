# -*- coding: utf-8 -*-
"""P4.3 / P4.3.1 DRW-006: дубликаты Line — HLR только при подтверждённом match.

P4.3.1 A4:
  - дедуп одинаковых HLR-сегментов (ViewResult часто дублирует curves);
  - ends-match + проверка длины;
  - consume: один HLR-сегмент → не более одной группы;
  - конкурирующие группы за один сегмент → ambiguous (не PASS).
Геометрия DXF не удаляется.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ...geom.view_types import CurveKind, ViewResult
from ...model.document import DrawingDocument
from ...model.entities import LAYER_HIDDEN, Line
from ...views.transform import ViewTransform
from .view_layout import ViewLayout

Point = Tuple[float, float]

_HLR_LAYERS = {LAYER_HIDDEN, "Невидимая", "HIDDEN", "Hidden"}
_DRAWING_LAYERS = {
    "Основная",
    "Тонкая",
    "Осевая",
    "Припуск",
    "Штриховка",
    "Размеры",
    "Текст",
    "Штамп",
}


@dataclass
class DupGroup:
    layer: str
    p1: Point
    p2: Point
    entity_type: str
    count: int
    classification: str  # hlr_coincident | drawing_duplicate | ambiguous_same_geom
    reason: str
    length_mm_sheet: float
    hlr_match: bool = False
    matched_view: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _seg_len(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _ends_match(a1: Point, a2: Point, b1: Point, b2: Point, tol: float) -> bool:
    """Отрезки совпадают с учётом направления (концы в tol)."""
    return (
        (_dist(a1, b1) <= tol and _dist(a2, b2) <= tol)
        or (_dist(a1, b2) <= tol and _dist(a2, b1) <= tol)
    )


def _length_compatible(la: float, lb: float, *, tol: float = 0.35) -> bool:
    """Концы близко недостаточно, если длины существенно различаются."""
    return abs(la - lb) <= max(tol, 0.05 * max(la, lb, 1e-9))


def _seg_key(a: Point, b: Point, nd: int = 4) -> Tuple[Point, Point]:
    ra = (round(a[0], nd), round(a[1], nd))
    rb = (round(b[0], nd), round(b[1], nd))
    return tuple(sorted([ra, rb]))  # type: ignore[return-value]


def _hlr_sheet_segments(
    views: Dict[str, ViewResult],
    view_layouts: Dict[str, ViewLayout],
) -> List[Tuple[str, Point, Point]]:
    """
    Эталонные HLR-отрезки в координатах листа (после дедупа).
    Model → sheet через ViewTransform явно: sheet = V.P(model).
    """
    raw: List[Tuple[str, Point, Point]] = []
    for vid, view in views.items():
        layout = view_layouts.get(vid)
        if layout is None:
            continue
        V = layout.transform()
        n_hidden_meta = view.meta.get("n_hidden")
        hidden_curves = [c for c in view.curves if c.kind == CurveKind.HIDDEN]
        if n_hidden_meta == 0 and not hidden_curves:
            continue
        for curve in hidden_curves:
            pts = list(curve.points)
            if len(pts) < 2:
                continue
            sheet = [V.P(x, y) for x, y in pts]
            for i in range(len(sheet) - 1):
                raw.append((vid, sheet[i], sheet[i + 1]))
            if curve.closed and len(sheet) >= 3:
                raw.append((vid, sheet[-1], sheet[0]))

    # дедуп диагностический: одинаковые endpoints → один эталон
    seen: set[Tuple[str, Tuple[Point, Point]]] = set()
    segs: List[Tuple[str, Point, Point]] = []
    for vid, a, b in raw:
        key = (vid, _seg_key(a, b))
        if key in seen:
            continue
        seen.add(key)
        segs.append((vid, a, b))
    return segs


def _candidate_seg_indices(
    p1: Point,
    p2: Point,
    hlr_segs: Sequence[Tuple[str, Point, Point]],
    *,
    tol: float = 0.35,
) -> List[int]:
    line_len = _seg_len(p1, p2)
    out: List[int] = []
    for i, (_vid, a, b) in enumerate(hlr_segs):
        if not _ends_match(p1, p2, a, b, tol):
            continue
        if not _length_compatible(line_len, _seg_len(a, b), tol=tol):
            continue
        out.append(i)
    return out


def classify_duplicate_lines(
    doc: DrawingDocument,
    *,
    views: Optional[Dict[str, ViewResult]] = None,
    view_layouts: Optional[Dict[str, ViewLayout]] = None,
) -> List[DupGroup]:
    """
    Группы Line с одинаковыми концами (round 3) на одном слое.

    hlr_coincident — только при однозначном совпадении с свободным HLR-сегментом
    ViewResult после ViewTransform в координаты листа.
    Без views / без match / конкуренция за сегмент → ambiguous_same_geom.
    """
    buckets: Dict[Tuple, List[Line]] = defaultdict(list)
    for e in doc.entities:
        if not isinstance(e, Line):
            continue
        a = (round(e.start[0], 3), round(e.start[1], 3))
        b = (round(e.end[0], 3), round(e.end[1], 3))
        key = tuple(sorted([a, b])) + (e.layer,)
        buckets[key].append(e)

    hlr_segs: List[Tuple[str, Point, Point]] = []
    have_hlr_evidence = False
    if views and view_layouts:
        hlr_segs = _hlr_sheet_segments(views, view_layouts)
        have_hlr_evidence = len(hlr_segs) > 0

    # Сначала собираем HLR-кандидатов по группам, затем назначаем без reuse
    pending_hlr: List[Tuple[Tuple, List[Line], Point, Point, float, int, List[int]]] = []
    out: List[DupGroup] = []

    for key, lines in buckets.items():
        if len(lines) < 2:
            continue
        (x1, y1), (x2, y2), layer = key[0], key[1], key[2]
        p1, p2 = (x1, y1), (x2, y2)
        length = _seg_len(p1, p2)
        n = len(lines)

        if layer in _DRAWING_LAYERS:
            out.append(
                DupGroup(
                    layer=layer,
                    p1=p1,
                    p2=p2,
                    entity_type="Line",
                    count=n,
                    classification="drawing_duplicate",
                    reason="совпадение на слое оформления/контура",
                    length_mm_sheet=round(length, 4),
                )
            )
            continue

        if layer in _HLR_LAYERS:
            cands: List[int] = []
            if have_hlr_evidence:
                cands = _candidate_seg_indices(p1, p2, hlr_segs)
            pending_hlr.append((key, lines, p1, p2, length, n, cands))
            continue

        out.append(
            DupGroup(
                layer=layer,
                p1=p1,
                p2=p2,
                entity_type="Line",
                count=n,
                classification="ambiguous_same_geom",
                reason=f"слой {layer!r} не классифицирован однозначно",
                length_mm_sheet=round(length, 4),
            )
        )

    # --- назначение HLR: конкуренция → ambiguous ---
    claim_count: Dict[int, int] = defaultdict(int)
    for *_, cands in pending_hlr:
        for si in set(cands):
            claim_count[si] += 1

    used_segs: set[int] = set()
    # сначала группы с единственным эксклюзивным кандидатом
    order = sorted(
        range(len(pending_hlr)),
        key=lambda i: (
            len([s for s in pending_hlr[i][6] if claim_count[s] == 1]),
            len(pending_hlr[i][6]),
        ),
    )

    resolved: Dict[int, DupGroup] = {}
    for i in order:
        _key, _lines, p1, p2, length, n, cands = pending_hlr[i]
        if not have_hlr_evidence:
            resolved[i] = DupGroup(
                layer=_key[2],
                p1=p1,
                p2=p2,
                entity_type="Line",
                count=n,
                classification="ambiguous_same_geom",
                reason="insufficient_hlr_evidence: нет views/layout или HLR-сегментов",
                length_mm_sheet=round(length, 4),
                hlr_match=False,
            )
            continue

        # Только эксклюзивные (claim_count==1) сегменты — без произвольного выбора
        free_exclusive = [
            s for s in cands if s not in used_segs and claim_count[s] == 1
        ]

        if len(free_exclusive) == 1:
            si = free_exclusive[0]
            vid = hlr_segs[si][0]
            used_segs.add(si)
            if n <= 4:
                resolved[i] = DupGroup(
                    layer=_key[2],
                    p1=p1,
                    p2=p2,
                    entity_type="Line",
                    count=n,
                    classification="hlr_coincident",
                    reason=(
                        f"подтверждено совпадение с HLR ViewResult[{vid}] "
                        f"после ViewTransform (sheet coords; seg consumed)"
                    ),
                    length_mm_sheet=round(length, 4),
                    hlr_match=True,
                    matched_view=vid,
                )
            else:
                resolved[i] = DupGroup(
                    layer=_key[2],
                    p1=p1,
                    p2=p2,
                    entity_type="Line",
                    count=n,
                    classification="ambiguous_same_geom",
                    reason=f"HLR-match ок, но count={n}>4",
                    length_mm_sheet=round(length, 4),
                    hlr_match=True,
                    matched_view=vid,
                )
        elif not cands:
            resolved[i] = DupGroup(
                layer=_key[2],
                p1=p1,
                p2=p2,
                entity_type="Line",
                count=n,
                classification="ambiguous_same_geom",
                reason=(
                    "слой Невидимая, но нет подтверждённого HLR-match с ViewResult "
                    "(ends+length)"
                ),
                length_mm_sheet=round(length, 4),
                hlr_match=False,
            )
        else:
            contested = any(claim_count[s] > 1 for s in cands)
            multi_excl = len(free_exclusive) > 1
            resolved[i] = DupGroup(
                layer=_key[2],
                p1=p1,
                p2=p2,
                entity_type="Line",
                count=n,
                classification="ambiguous_same_geom",
                reason=(
                    "ambiguous_hlr_assignment: конкурирующие группы за HLR-сегмент"
                    if contested
                    else (
                        "ambiguous_hlr_assignment: несколько эксклюзивных кандидатов"
                        if multi_excl
                        else "ambiguous_hlr_assignment: нет однозначного свободного "
                        "HLR-сегмента"
                    )
                ),
                length_mm_sheet=round(length, 4),
                hlr_match=False,
            )

    for i in range(len(pending_hlr)):
        out.append(resolved[i])
    return out


def summarize_duplicates(groups: List[DupGroup]) -> Dict[str, Any]:
    by = defaultdict(int)
    micro = 0
    for g in groups:
        by[g.classification] += 1
        # A5: статистика микросегментов (без фильтрации классификации)
        if g.length_mm_sheet < 0.05:
            micro += 1
    return {
        "total_groups": len(groups),
        "by_class": dict(by),
        "micro_segment_groups_lt_0_05mm": micro,
        "micro_segment_note": (
            "микросегменты <0.05 mm — артефакты HLR-тесселяции; "
            "не фильтруются и не удаляются из DXF (P4.3.1 A5)"
        ),
        "groups": [g.as_dict() for g in groups],
    }
