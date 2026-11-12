# -*- coding: utf-8 -*-
"""Обозначение баз по ГОСТ 2.308 (упрощённый треугольник + полка)."""
from __future__ import annotations

from typing import Tuple

from ..model.document import DrawingDocument
from ..model.entities import LAYER_THIN, LAYER_TEXT, Line, Polyline, Text

Point = Tuple[float, float]


def add_datum(
    doc: DrawingDocument,
    tip: Point,
    *,
    letter: str,
    outward: Tuple[float, float],
    size: float = 8.0,
) -> None:
    """База: заполненный треугольник у поверхности + буква в рамке на полке."""
    import math

    ox, oy = outward
    L = math.hypot(ox, oy) or 1.0
    nx, ny = ox / L, oy / L
    tx, ty = -ny, nx
    # triangle pointing to surface
    a = (tip[0] + nx * size, tip[1] + ny * size)
    b = (tip[0] + tx * size * 0.55, tip[1] + ty * size * 0.55)
    c = (tip[0] - tx * size * 0.55, tip[1] - ty * size * 0.55)
    doc.add(Polyline(points=[tip, b, a, c], closed=True, layer=LAYER_THIN))
    # shelf
    shelf0 = a
    shelf1 = (a[0] + nx * 12, a[1] + ny * 12)
    doc.add(Line(shelf0, shelf1, layer=LAYER_THIN))
    # letter box
    bx, by = shelf1[0] + nx * 2, shelf1[1] + ny * 2
    s = 7.0
    box = [(bx, by), (bx + s, by), (bx + s, by + s), (bx, by + s)]
    # orient box roughly axis-aligned for readability
    doc.add(Polyline(points=box, closed=True, layer=LAYER_THIN))
    doc.add(Text((bx + s / 2, by + 1.5), letter, height=5, halign="center", layer=LAYER_TEXT))
