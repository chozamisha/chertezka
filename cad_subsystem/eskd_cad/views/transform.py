# -*- coding: utf-8 -*-
"""Ортогональный вид: модельные мм → мм листа."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np

Point = Tuple[float, float]


@dataclass
class ViewTransform:
    """Масштаб 1:k, центр вида (ox, oy) на листе = модель (0,0) или заданный."""

    ox: float
    oy: float
    k: float  # sheet = model / k

    def P(self, x: float, y: float) -> Point:
        return (self.ox + x / self.k, self.oy + y / self.k)

    def pts(self, points: Sequence[Point]) -> List[Point]:
        return [self.P(x, y) for x, y in points]

    def r(self, radius: float) -> float:
        return radius / self.k
