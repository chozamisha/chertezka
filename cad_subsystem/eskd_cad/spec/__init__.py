# -*- coding: utf-8 -*-
"""Единый слой параметров отливки (CastingSpec) — без дублирования koleso_data."""
from .casting_spec import CastingSpec
from .koleso_loader import KOLESO_PART_ID, load_koleso_spec
from .registry import build_drawing, register_builder

__all__ = [
    "CastingSpec",
    "load_koleso_spec",
    "KOLESO_PART_ID",
    "build_drawing",
    "register_builder",
]
