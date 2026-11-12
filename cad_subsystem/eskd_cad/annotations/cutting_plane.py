# -*- coding: utf-8 -*-
"""Секущая плоскость ГОСТ 2.305: тонкая линия + утолщённые штрихи + буквы."""
from __future__ import annotations

from typing import Tuple

from ..model.document import DrawingDocument
from ..model.entities import LAYER_TEXT, LAYER_THIN, Line, Text

Point = Tuple[float, float]


def add_cutting_plane(
    doc: DrawingDocument,
    p1: Point,
    p2: Point,
    *,
    letter: str = "А",
    tick: float = 10.0,
) -> None:
    import math

    doc.add(Line(p1, p2, layer=LAYER_THIN))
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    # thick end ticks (as short main lines)
    for origin, sgn in ((p1, 1), (p2, -1)):
        a = (origin[0] + ux * sgn * 0.5, origin[1] + uy * sgn * 0.5)
        b = (origin[0] + ux * sgn * 0.5 + nx * tick, origin[1] + uy * sgn * 0.5 + ny * tick)
        doc.add(Line(a, b, layer="Сечение"))
        # letter near tick
        lx = b[0] + nx * 3 + ux * sgn * 2
        ly = b[1] + ny * 3 + uy * sgn * 2
        doc.add(Text((lx, ly), letter, height=5, layer=LAYER_TEXT))
