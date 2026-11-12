# -*- coding: utf-8 -*-
"""PartSpec — канон детали после разбора входного чертежа (до технологии отливки)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DimensionReading:
    """Сырое чтение с чертежа (ещё без жёсткой семантики)."""

    raw_text: str
    kind: str  # diameter | linear | radius | thread | mass | material | designation | other
    value_mm: Optional[float] = None
    confidence: float = 0.5
    source: str = "dxf_text"  # dxf_text | dxf_circle | engineer | profile_default
    hint: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartSpec:
    """
    Структурированная деталь.

    `dimensions` — семантические ключи профиля (для Корпуса: h_part, d_top, …).
    `readings` — всё, что снято с DXF/PDF до интерпретации.
    `questions` — что нужно подтвердить человеку перед сдачей отливки.
    """

    part_id: str
    designation: str = ""
    name: List[str] = field(default_factory=list)
    material: List[str] = field(default_factory=list)
    mass_kg: Optional[float] = None
    scale: Optional[str] = None
    profile: str = "generic"  # korpus | koleso | generic
    dimensions: Dict[str, float] = field(default_factory=dict)
    readings: List[DimensionReading] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    process_hints: Dict[str, Any] = field(default_factory=dict)
    source_path: str = ""

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def missing_dimensions(self, required: List[str]) -> List[str]:
        return [k for k in required if k not in self.dimensions]


@dataclass
class CastingDraft:
    """
    Черновик отливки после PartSpec + технологические решения.

    `params` — числа для рендера профиля (для Корпуса совместимы с korpus_data).
    `provenance` — откуда каждое ключевое поле.
    """

    profile: str
    designation: str
    params: Dict[str, Any]
    provenance: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
