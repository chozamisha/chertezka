# -*- coding: utf-8 -*-
"""
P1: подключение существующих расчётов/таблиц к CastingSpec.

Не дублирует формулы: вызывает gost26645_table6, riser_gates,
ls_ratios, core_prints. Геометрия видов — в foundry, не здесь.
"""
from __future__ import annotations

from .errors import CalcDataError, MissingInputError, OutOfRangeError, UnitError
from .pipeline import CalcResult, build_casting_from_inputs, build_koleso_casting_result
from .provenance import ParamKind, ParamProvenance

__all__ = [
    "CalcDataError",
    "CalcResult",
    "MissingInputError",
    "OutOfRangeError",
    "ParamKind",
    "ParamProvenance",
    "UnitError",
    "build_casting_from_inputs",
    "build_koleso_casting_result",
]
