# -*- coding: utf-8 -*-
"""Заготовки литейных элементов. Числа не выдумывать — передавать из calc."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

Point = Tuple[float, float]


@dataclass(frozen=True)
class CoreMark:
    """Стержневой знак: диаметры/длины из расчёта стержней."""
    diameter: float
    length: float
    taper: float  # уклон, град или отношение — как в calc


@dataclass(frozen=True)
class Riser:
    diameter: float
    height: float
    neck_d: float
    neck_h: float


@dataclass(frozen=True)
class Vent:
    diameter: float
    height: float


@dataclass(frozen=True)
class Chill:
    width: float
    height: float
    thickness: float


@dataclass(frozen=True)
class GatingElement:
    """Элемент ЛС: стояк / шлакоуловитель / питатель — площади из соотношения F."""
    kind: str  # sprue|slag|ingate
    section_points: tuple  # контур сечения в мм модели
