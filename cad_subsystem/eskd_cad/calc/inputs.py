# -*- coding: utf-8 -*-
"""Исходные данные и решения инженера — отдельно от расчётных значений."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PartGeometryInputs:
    """Исходная геометрия детали (мм)."""

    d_out: float
    d_hub: float
    d_bore: float
    d_bore_lo: float
    d_boss: float
    h_hub: float
    t_disk: float
    h_ch: float
    h_step: float
    unit: str = "mm"


@dataclass(frozen=True)
class AllowanceInputs:
    """Параметры для табл.6 + принятые инженером припуски на сторону (мм)."""

    general_tolerance_mm: float  # общий допуск элемента для find_tolerance_row
    finish: str  # Черновая | Получистовая | Чистовая | Тонкая
    allowance_row: int  # 1..18
    # Принятые (могут отличаться от табл.6 — округление / верх формы)
    n_top: float
    n_bot: float
    n_face: float
    n_hub_od: float
    n_bore: float
    n_boss: float
    unit: str = "mm"


@dataclass(frozen=True)
class RiserInputs:
    """Прибыль — принятые размеры + схема стыка со стержнем."""

    d_riser: float
    d_neck: float
    h_riser: float
    core_scheme: str  # A | B | C
    unit: str = "mm"


@dataclass(frozen=True)
class GatingInputs:
    """Литниковая система."""

    f_pit_cm2: float
    n_pit: int
    ls_ratio_case: str  # ключ ls_ratios_all.csv
    unit: str = "cm2"


@dataclass(frozen=True)
class CorePrintInputs:
    """Знаки стержней."""

    # Для горизонтального знака Ст.1: сечение и длина рабочей части → табл.
    section_mm: float
    core_length_mm: float
    l_print: float  # принятый
    h_print2: float  # верт. знак Ст.2 (engineer); нормативный gate — табл.7
    unit: str = "mm"


@dataclass(frozen=True)
class MetaInputs:
    part_id: str
    code: str
    name: tuple[str, ...]
    material: tuple[str, ...]
    mass_stamp: float
    scale_k: float
    fmt: str
    dev: str
    chk: str
    rho: float  # кг/мм³
    rim_wall: float = 25.0
    bore_step_y: float = 43.0


@dataclass(frozen=True)
class CastingInputs:
    """Полный пакет входных данных для pipeline (без расчётных производных)."""

    meta: MetaInputs
    geometry: PartGeometryInputs
    allowance: AllowanceInputs
    riser: RiserInputs
    gating: GatingInputs
    cores: CorePrintInputs

    def missing_required(self) -> list[str]:
        """Имена обязательных полей с None / пустой строкой."""
        missing: list[str] = []
        for group_name in ("meta", "geometry", "allowance", "riser", "gating", "cores"):
            group = getattr(self, group_name)
            for f in fields(group):
                val = getattr(group, f.name)
                if val is None:
                    missing.append(f"{group_name}.{f.name}")
                elif isinstance(val, str) and not val.strip():
                    missing.append(f"{group_name}.{f.name}")
                elif isinstance(val, tuple) and len(val) == 0:
                    missing.append(f"{group_name}.{f.name}")
        return missing
