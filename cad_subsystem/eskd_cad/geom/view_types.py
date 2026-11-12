# -*- coding: utf-8 -*-
"""Типы контуров проекций/сечений (без привязки к OCP)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

Point2 = Tuple[float, float]


class CurveKind(str, Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    OUTLINE = "outline"
    SECTION = "section"
    AXIS = "axis"


@dataclass(frozen=True)
class Curve2D:
    kind: CurveKind
    points: Tuple[Point2, ...]
    closed: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "points": [list(p) for p in self.points],
            "closed": self.closed,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Curve2D":
        pts = tuple((float(x), float(y)) for x, y in d["points"])
        return Curve2D(kind=CurveKind(d["kind"]), points=pts, closed=bool(d.get("closed", False)))


@dataclass
class ViewResult:
    """Результат одной геометрической операции (проекция или сечение)."""

    name: str
    operation: str  # hlr_projection | plane_section
    engine: str  # ocp8
    curves: List[Curve2D] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "operation": self.operation,
            "engine": self.engine,
            "curves": [c.as_dict() for c in self.curves],
            "meta": self.meta,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ViewResult":
        return ViewResult(
            name=d["name"],
            operation=d["operation"],
            engine=d.get("engine", "ocp8"),
            curves=[Curve2D.from_dict(c) for c in d.get("curves", [])],
            meta=dict(d.get("meta") or {}),
        )

    def curves_of(self, kind: CurveKind) -> List[Curve2D]:
        return [c for c in self.curves if c.kind == kind]

    def bbox(self) -> Optional[Tuple[float, float, float, float]]:
        xs: List[float] = []
        ys: List[float] = []
        for c in self.curves:
            for x, y in c.points:
                xs.append(x)
                ys.append(y)
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys)
