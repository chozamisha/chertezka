# -*- coding: utf-8 -*-
"""Передача ViewResult → DrawingDocument (редактируемые 2D-примитивы)."""
from __future__ import annotations

from typing import Iterable, Optional, Tuple

from ..model.document import DrawingDocument
from ..model.entities import (
    LAYER_AXIS,
    LAYER_HATCH,
    LAYER_HIDDEN,
    LAYER_MAIN,
    LAYER_THIN,
    Hatch,
    Line,
    Polyline,
)
from ..views.transform import ViewTransform
from .view_types import Curve2D, CurveKind, ViewResult

Point = Tuple[float, float]


_LAYER = {
    CurveKind.VISIBLE: LAYER_MAIN,
    CurveKind.OUTLINE: LAYER_MAIN,
    CurveKind.SECTION: LAYER_MAIN,
    CurveKind.HIDDEN: LAYER_HIDDEN,
    CurveKind.AXIS: LAYER_AXIS,
}

_LINETYPE = {
    CurveKind.VISIBLE: "CONTINUOUS",
    CurveKind.OUTLINE: "CONTINUOUS",
    CurveKind.SECTION: "CONTINUOUS",
    CurveKind.HIDDEN: "HIDDEN",
    CurveKind.AXIS: "CENTER",
}


def _sheet_pts(V: ViewTransform, pts: Iterable[Tuple[float, float]]) -> list[Point]:
    return [V.P(x, y) for x, y in pts]


def emit_curve(doc: DrawingDocument, V: ViewTransform, curve: Curve2D) -> None:
    if len(curve.points) < 2:
        return
    layer = _LAYER[curve.kind]
    lt = _LINETYPE[curve.kind]
    sp = _sheet_pts(V, curve.points)
    if len(sp) == 2 and not curve.closed:
        doc.add(Line(sp[0], sp[1], layer=layer, linetype=lt))
    else:
        doc.add(Polyline(points=sp, closed=curve.closed, layer=layer, linetype=lt))


def emit_view(
    doc: DrawingDocument,
    V: ViewTransform,
    view: ViewResult,
    *,
    hatch_section: bool = False,
    hatch_scale: float = 1.2,
    hatch_angle: float = 45.0,
    skip_kinds: Optional[set[CurveKind]] = None,
) -> int:
    """Добавить кривые вида в документ. Возвращает число добавленных кривых."""
    skip = skip_kinds or set()
    n = 0
    section_loops: list[list[Point]] = []
    for curve in view.curves:
        if curve.kind in skip:
            continue
        emit_curve(doc, V, curve)
        n += 1
        if hatch_section and curve.kind == CurveKind.SECTION and len(curve.points) >= 3:
            section_loops.append(_sheet_pts(V, curve.points))
    if hatch_section and section_loops:
        # штрихуем только замкнутые/почти замкнутые контуры
        for loop in section_loops:
            if len(loop) < 3:
                continue
            p0, p1 = loop[0], loop[-1]
            closed = abs(p0[0] - p1[0]) < 1e-6 and abs(p0[1] - p1[1]) < 1e-6
            path = list(loop) if closed else list(loop) + [loop[0]]
            doc.add(
                Hatch(
                    path=path,
                    pattern="ANSI31",
                    scale=hatch_scale,
                    angle=hatch_angle,
                    layer=LAYER_HATCH,
                )
            )
    return n
