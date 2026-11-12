# -*- coding: utf-8 -*-
"""Векторные CAD-сущности (не растр)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Point = Tuple[float, float]


@dataclass
class Line:
    start: Point
    end: Point
    layer: str = "0"
    linetype: str = "CONTINUOUS"


@dataclass
class Circle:
    center: Point
    radius: float
    layer: str = "0"
    linetype: str = "CONTINUOUS"


@dataclass
class Arc:
    center: Point
    radius: float
    start_angle: float  # degrees CCW from +X
    end_angle: float
    layer: str = "0"
    linetype: str = "CONTINUOUS"


@dataclass
class Polyline:
    points: List[Point]
    closed: bool = False
    layer: str = "0"
    linetype: str = "CONTINUOUS"


@dataclass
class Hatch:
    path: List[Point]
    pattern: str = "ANSI31"
    scale: float = 1.0
    angle: float = 45.0
    holes: List[List[Point]] = field(default_factory=list)
    layer: str = "Штриховка"
    linetype: str = "CONTINUOUS"


@dataclass
class Text:
    position: Point
    content: str
    height: float = 3.5
    rotation: float = 0.0
    halign: str = "left"  # left|center|right
    valign: str = "baseline"  # baseline|bottom|middle|top
    layer: str = "Текст"
    linetype: str = "CONTINUOUS"


@dataclass
class MText:
    position: Point
    content: str
    height: float = 3.5
    width: float = 80.0
    rotation: float = 0.0
    attachment: int = 1  # TOP_LEFT
    layer: str = "Текст"
    linetype: str = "CONTINUOUS"


@dataclass
class DimLinear:
    """Линейный размер — в DXF станет DIMENSION."""
    p1: Point
    p2: Point
    offset: float = 10.0
    text: Optional[str] = None
    dimstyle: str = "ESKD"
    layer: str = "Размеры"
    linetype: str = "CONTINUOUS"


@dataclass
class Leader:
    tip: Point
    knee: Point
    text: str
    text_height: float = 3.5
    side: str = "right"
    layer: str = "Тонкая"
    linetype: str = "CONTINUOUS"


# --- layer presets (ГОСТ 2.303 names) ---
LAYER_MAIN = "Основная"
LAYER_THIN = "Тонкая"
LAYER_AXIS = "Осевая"
LAYER_HIDDEN = "Невидимая"
LAYER_HATCH = "Штриховка"
LAYER_DIM = "Размеры"
LAYER_TEXT = "Текст"
LAYER_TITLE = "Штамп"
LAYER_ALLOW = "Припуск"


def poly_rect(x0: float, y0: float, x1: float, y1: float) -> List[Point]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
