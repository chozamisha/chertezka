# -*- coding: utf-8 -*-
"""PartSpec — деталь после разбора исходного чертежа, до литейной технологии."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA = 2


@dataclass
class DimensionReading:
    """Надпись с чертежа: размерное число, обозначение, материал."""

    raw_text: str
    kind: str  # diameter | linear | radius | thread | holes | roughness | other
    value_mm: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    used_for: str = ""  # какой размер PartSpec подтвердила эта надпись

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HoleGroup:
    """Отверстия по окружности. Они не льются, но попадают в ТТ и в массу отливки."""

    pcd: float
    n: int
    d: float
    angle0: float = 0.0
    kind: str = "thru"  # thru | cbore | thread
    d_cb: Optional[float] = None
    cb_depth: Optional[float] = None
    depth: Optional[float] = None  # None: сквозное через фланец
    label: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Ribs:
    n: int
    width: float
    angle0: float = 0.0
    r_out: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartSpec:
    """
    Структурированная деталь.

    `dimensions` — размеры профиля в мм детали; `provenance` — откуда каждый взят;
    `questions` — что не удалось прочитать и надо спросить; `warnings` — что
    прочитано, но выглядит подозрительно.
    """

    part_id: str
    designation: str = ""
    name: List[str] = field(default_factory=list)
    material: List[str] = field(default_factory=list)
    mass_kg: Optional[float] = None
    scale: Optional[str] = None
    profile: str = "korpus"
    dimensions: Dict[str, float] = field(default_factory=dict)
    holes: List[HoleGroup] = field(default_factory=list)
    ribs: Optional[Ribs] = None
    roughness: Dict[str, Optional[str]] = field(default_factory=dict)  # top | bottom | bore | general
    stamp: Dict[str, Any] = field(default_factory=dict)  # dev, chk, org, lit
    notes: Dict[str, str] = field(default_factory=dict)  # hardness, radii … из ТТ детали
    provenance: Dict[str, str] = field(default_factory=dict)
    readings: List[DimensionReading] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    source_path: str = ""

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["schema"] = SCHEMA
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source_path: str = "") -> "PartSpec":
        ribs = data.get("ribs")
        return cls(
            part_id=data.get("part_id") or data.get("designation") or "part",
            designation=data.get("designation", ""),
            name=list(data.get("name") or []),
            material=list(data.get("material") or []),
            mass_kg=data.get("mass_kg"),
            scale=data.get("scale"),
            profile=data.get("profile", "korpus"),
            dimensions={k: float(v) for k, v in (data.get("dimensions") or {}).items() if v is not None},
            holes=[HoleGroup(**h) for h in data.get("holes") or []],
            ribs=Ribs(**ribs) if ribs else None,
            roughness=dict(data.get("roughness") or {}),
            stamp=dict(data.get("stamp") or {}),
            notes=dict(data.get("notes") or {}),
            provenance=dict(data.get("provenance") or {}),
            readings=[DimensionReading(**r) for r in data.get("readings") or []],
            questions=list(data.get("questions") or []),
            warnings=list(data.get("warnings") or []),
            source_path=data.get("source_path") or source_path,
        )

    def missing_dimensions(self, required: List[str]) -> List[str]:
        return [k for k in required if k not in self.dimensions]


@dataclass
class CastingDraft:
    """Параметры листа отливки (имена как в cad_work/korpus_data.py) и их происхождение."""

    profile: str
    designation: str
    params: Dict[str, Any]
    provenance: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
