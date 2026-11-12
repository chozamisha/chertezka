# -*- coding: utf-8 -*-
"""Входной контур: чертёж детали → PartSpec → решения → CastingDraft → лист."""
from .part_spec import CastingDraft, DimensionReading, HoleGroup, PartSpec, Ribs
from .pipeline import build_casting, part_from_input, run

__all__ = [
    "PartSpec",
    "DimensionReading",
    "HoleGroup",
    "Ribs",
    "CastingDraft",
    "part_from_input",
    "build_casting",
    "run",
]
