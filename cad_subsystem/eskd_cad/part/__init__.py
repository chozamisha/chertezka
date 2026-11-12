# -*- coding: utf-8 -*-
"""Входной контур: чертёж детали → PartSpec → CastingDraft."""
from .part_spec import CastingDraft, DimensionReading, PartSpec
from .pipeline import build_casting, part_from_input, run

__all__ = [
    "PartSpec",
    "DimensionReading",
    "CastingDraft",
    "part_from_input",
    "build_casting",
    "run",
]
