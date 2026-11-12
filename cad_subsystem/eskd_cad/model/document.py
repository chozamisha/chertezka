# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Union

from .entities import (
    Arc,
    Circle,
    DimLinear,
    Hatch,
    Leader,
    Line,
    MText,
    Polyline,
    Text,
)

AnyEntity = Union[
    Line, Arc, Circle, Polyline, Hatch, DimLinear, Leader, Text, MText
]

FORMATS = {
    "A4": (210.0, 297.0),
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
    "A1": (841.0, 594.0),
}


@dataclass
class DrawingDocument:
    """Сцена чертежа в мм бумаги (model space = лист)."""

    fmt: str = "A3"
    landscape: bool = True
    entities: List[AnyEntity] = field(default_factory=list)
    title: dict = field(default_factory=dict)

    @property
    def width(self) -> float:
        w, h = FORMATS[self.fmt]
        a, b = (max(w, h), min(w, h)) if self.landscape else (min(w, h), max(w, h))
        return a

    @property
    def height(self) -> float:
        w, h = FORMATS[self.fmt]
        a, b = (max(w, h), min(w, h)) if self.landscape else (min(w, h), max(w, h))
        return b

    def add(self, *ents: AnyEntity) -> None:
        self.entities.extend(ents)

    def extend(self, ents: Sequence[AnyEntity]) -> None:
        self.entities.extend(ents)
