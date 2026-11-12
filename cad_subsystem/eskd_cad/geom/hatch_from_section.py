# -*- coding: utf-8 -*-
"""Попытка собрать замкнутые контуры штриховки из рёбер сечения (shapely)."""
from __future__ import annotations

from typing import List, Sequence, Tuple

from .view_types import Curve2D, CurveKind, ViewResult

Point2 = Tuple[float, float]


def closed_loops_from_section(view: ViewResult, *, tol: float = 0.75) -> List[List[Point2]]:
    """Склеить section-рёбра в кольца. Если не удалось — пустой список (без выдумок)."""
    try:
        from shapely.geometry import LineString, MultiLineString
        from shapely.ops import linemerge, polygonize, unary_union
    except ImportError:
        return []

    lines = []
    for c in view.curves_of(CurveKind.SECTION):
        if len(c.points) < 2:
            continue
        lines.append(LineString(list(c.points)))
    if not lines:
        return []
    merged = linemerge(unary_union(lines))
    if merged.is_empty:
        return []
    if merged.geom_type == "LineString":
        geoms = [merged]
    else:
        geoms = list(merged.geoms)
    # polygonize wants MultiLineString of closed-capable pieces
    polys = list(polygonize(geoms))
    loops: List[List[Point2]] = []
    for poly in polys:
        if poly.is_empty or poly.area < 1.0:
            continue
        coords = list(poly.exterior.coords)
        loops.append([(float(x), float(y)) for x, y in coords])
    return loops
