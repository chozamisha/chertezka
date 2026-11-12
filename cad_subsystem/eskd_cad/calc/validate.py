# -*- coding: utf-8 -*-
"""Проверка единиц, обязательных параметров и допустимых диапазонов."""
from __future__ import annotations

from .errors import MissingInputError, OutOfRangeError, UnitError
from .inputs import CastingInputs

_MM = "mm"
_CM2 = "cm2"
_FINISHES = {"Черновая", "Получистовая", "Чистовая", "Тонкая"}


def require_unit(actual: str, expected: str, field: str) -> None:
    if (actual or "").strip().lower() != expected.lower():
        raise UnitError(
            f"{field}: ожидается единица '{expected}', получено '{actual}'. "
            "Пересчёт единиц в pipeline не выполняется — исправьте вход."
        )


def validate_inputs(inp: CastingInputs) -> None:
    missing = inp.missing_required()
    if missing:
        raise MissingInputError(
            "Недостаточно исходных данных для расчёта CastingSpec. "
            "Недостаёт: " + ", ".join(missing)
        )

    require_unit(inp.geometry.unit, _MM, "geometry.unit")
    require_unit(inp.allowance.unit, _MM, "allowance.unit")
    require_unit(inp.riser.unit, _MM, "riser.unit")
    require_unit(inp.cores.unit, _MM, "cores.unit")
    require_unit(inp.gating.unit, _CM2, "gating.unit")

    g = inp.geometry
    for name, val in (
        ("d_out", g.d_out),
        ("d_hub", g.d_hub),
        ("d_bore", g.d_bore),
        ("d_bore_lo", g.d_bore_lo),
        ("d_boss", g.d_boss),
        ("h_hub", g.h_hub),
        ("t_disk", g.t_disk),
        ("h_ch", g.h_ch),
        ("h_step", g.h_step),
    ):
        if val <= 0:
            raise OutOfRangeError(f"geometry.{name} должен быть > 0 мм, получено {val}")

    if not (g.d_bore < g.d_bore_lo <= g.d_hub < g.d_boss < g.d_out):
        raise OutOfRangeError(
            "Диаметры детали вне ожидаемого порядка: "
            "d_bore < d_bore_lo ≤ d_hub < d_boss < d_out "
            f"(получили {g.d_bore}, {g.d_bore_lo}, {g.d_hub}, {g.d_boss}, {g.d_out})"
        )

    a = inp.allowance
    if a.finish not in _FINISHES:
        raise OutOfRangeError(
            f"allowance.finish={a.finish!r} недопустим; "
            f"ожидается одно из: {sorted(_FINISHES)}"
        )
    if not (1 <= int(a.allowance_row) <= 18):
        raise OutOfRangeError(
            f"allowance_row должен быть 1..18, получено {a.allowance_row}"
        )
    if a.general_tolerance_mm <= 0:
        raise OutOfRangeError("general_tolerance_mm должен быть > 0")
    for name in ("n_top", "n_bot", "n_face", "n_hub_od", "n_bore", "n_boss"):
        if getattr(a, name) < 0:
            raise OutOfRangeError(f"allowance.{name} не может быть < 0")

    r = inp.riser
    for name, val in (("d_riser", r.d_riser), ("d_neck", r.d_neck), ("h_riser", r.h_riser)):
        if val <= 0:
            raise OutOfRangeError(f"riser.{name} должен быть > 0 мм")

    gt = inp.gating
    if gt.f_pit_cm2 <= 0:
        raise OutOfRangeError("gating.f_pit_cm2 должен быть > 0 см²")
    if gt.n_pit < 1:
        raise OutOfRangeError("gating.n_pit должен быть ≥ 1")

    c = inp.cores
    for name, val in (
        ("section_mm", c.section_mm),
        ("core_length_mm", c.core_length_mm),
        ("l_print", c.l_print),
        ("h_print2", c.h_print2),
    ):
        if val <= 0:
            raise OutOfRangeError(f"cores.{name} должен быть > 0 мм")

    if inp.meta.scale_k <= 0:
        raise OutOfRangeError("meta.scale_k должен быть > 0")
    if inp.meta.rho <= 0:
        raise OutOfRangeError("meta.rho должен быть > 0")
