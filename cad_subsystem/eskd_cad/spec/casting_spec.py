# -*- coding: utf-8 -*-
"""CastingSpec — единый контейнер параметров технологического чертежа отливки."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, List, Mapping, Tuple


@dataclass(frozen=True)
class CastingSpec:
    """Параметры отливки. Числа только из calc/knowledge, не приближения."""

    part_id: str
    code: str
    name: Tuple[str, ...]
    material: Tuple[str, ...]
    mass_stamp: float
    scale_k: float
    fmt: str
    dev: str
    chk: str

    # деталь
    d_out: float
    d_hub: float
    d_bore: float
    d_bore_lo: float
    d_boss: float
    h_hub: float
    t_disk: float
    h_ch: float
    h_step: float

    # припуски
    n_top: float
    n_bot: float
    n_face: float
    n_hub_od: float
    n_bore: float
    n_boss: float

    # отливка (производные — должны совпадать с формулами)
    c_hub: float
    c_bore: float
    c_bore_lo: float
    c_boss: float
    c_out: float
    c_h_hub: float
    c_t_top: float
    c_t_bot: float
    c_h_ch: float

    y_bot: float
    y_disk_lo_top: float
    y_disk_up_bot: float
    y_disk_up_top: float
    y_hub_top: float
    h_body: float

    # прибыль / стержни / ЛС
    d_riser: float
    d_neck: float
    h_riser: float
    y_riser_top: float
    l_print: float
    h_print2: float
    f_pit: float
    n_pit: int
    f_slag: float
    f_sprue: float
    rho: float

    # геометрия разреза (не расчёт, а принятая толщина обода в сечении)
    rim_wall: float = 25.0
    bore_step_y: float = 43.0

    def key_params(self) -> Dict[str, float | int | str]:
        """Ключевые параметры для паритет-тестов (без изменения семантики)."""
        return {
            "part_id": self.part_id,
            "CODE": self.code,
            "D_OUT": self.d_out,
            "D_HUB": self.d_hub,
            "D_BORE": self.d_bore,
            "D_BORE_LO": self.d_bore_lo,
            "D_BOSS": self.d_boss,
            "H_HUB": self.h_hub,
            "T_DISK": self.t_disk,
            "H_CH": self.h_ch,
            "N_TOP": self.n_top,
            "N_BOT": self.n_bot,
            "N_FACE": self.n_face,
            "N_HUB_OD": self.n_hub_od,
            "N_BORE": self.n_bore,
            "N_BOSS": self.n_boss,
            "C_HUB": self.c_hub,
            "C_BORE": self.c_bore,
            "C_BORE_LO": self.c_bore_lo,
            "C_BOSS": self.c_boss,
            "C_OUT": self.c_out,
            "C_H_HUB": self.c_h_hub,
            "C_T_TOP": self.c_t_top,
            "C_T_BOT": self.c_t_bot,
            "C_H_CH": self.c_h_ch,
            "H_BODY": self.h_body,
            "D_RISER": self.d_riser,
            "D_NECK": self.d_neck,
            "H_RISER": self.h_riser,
            "Y_RISER_TOP": self.y_riser_top,
            "L_PRINT": self.l_print,
            "H_PRINT2": self.h_print2,
            "F_PIT": self.f_pit,
            "N_PIT": self.n_pit,
            "F_SLAG": self.f_slag,
            "F_SPRUE": self.f_sprue,
            "MASS_STAMP": self.mass_stamp,
            "SCALE_K": self.scale_k,
            "FMT": self.fmt,
        }

    def validate_derived(self) -> List[str]:
        """Проверка формул отливки — без изменения чисел, только контроль."""
        issues: List[str] = []

        def eq(name: str, got: float, exp: float) -> None:
            if abs(got - exp) > 1e-9:
                issues.append(f"{name}: got {got}, expected {exp}")

        eq("C_HUB", self.c_hub, self.d_hub + 2 * self.n_hub_od)
        eq("C_BORE", self.c_bore, self.d_bore - 2 * self.n_bore)
        eq("C_BORE_LO", self.c_bore_lo, self.d_bore_lo - 2 * self.n_bore)
        eq("C_BOSS", self.c_boss, self.d_boss + 2 * self.n_boss)
        eq("C_OUT", self.c_out, self.d_out)
        eq("C_H_HUB", self.c_h_hub, self.h_hub + self.n_top)
        eq("C_T_TOP", self.c_t_top, self.t_disk + self.n_face)
        eq("C_T_BOT", self.c_t_bot, self.t_disk + self.n_face)
        eq("C_H_CH", self.c_h_ch, self.h_ch)
        eq("Y_DISK_LO_TOP", self.y_disk_lo_top, self.c_t_bot)
        eq("Y_DISK_UP_BOT", self.y_disk_up_bot, self.c_t_bot + self.c_h_ch)
        eq("Y_DISK_UP_TOP", self.y_disk_up_top, self.y_disk_up_bot + self.c_t_top)
        eq("Y_HUB_TOP", self.y_hub_top, self.y_disk_up_top + self.c_h_hub)
        eq("H_BODY", self.h_body, self.y_hub_top)
        eq("Y_RISER_TOP", self.y_riser_top, self.h_body + self.h_riser)
        if self.d_riser + 1e-9 < 1.15 * self.c_hub:
            issues.append(f"D_RISER {self.d_riser} < 1.15*C_HUB {1.15 * self.c_hub}")
        if self.d_neck - 1e-9 > self.c_hub:
            issues.append(f"D_NECK {self.d_neck} > C_HUB {self.c_hub}")
        return issues

    def as_legacy_module_dict(self) -> Dict[str, Any]:
        """Имена как в koleso_data.py — для сравнения с legacy-модулем."""
        return {
            "D_OUT": self.d_out,
            "D_HUB": self.d_hub,
            "D_BORE": self.d_bore,
            "D_BORE_LO": self.d_bore_lo,
            "D_BOSS": self.d_boss,
            "H_HUB": self.h_hub,
            "T_DISK": self.t_disk,
            "H_CH": self.h_ch,
            "H_STEP": self.h_step,
            "N_TOP": self.n_top,
            "N_BOT": self.n_bot,
            "N_FACE": self.n_face,
            "N_HUB_OD": self.n_hub_od,
            "N_BORE": self.n_bore,
            "N_BOSS": self.n_boss,
            "C_HUB": self.c_hub,
            "C_BORE": self.c_bore,
            "C_BORE_LO": self.c_bore_lo,
            "C_BOSS": self.c_boss,
            "C_OUT": self.c_out,
            "C_H_HUB": self.c_h_hub,
            "C_T_TOP": self.c_t_top,
            "C_T_BOT": self.c_t_bot,
            "C_H_CH": self.c_h_ch,
            "Y_BOT": self.y_bot,
            "Y_DISK_LO_TOP": self.y_disk_lo_top,
            "Y_DISK_UP_BOT": self.y_disk_up_bot,
            "Y_DISK_UP_TOP": self.y_disk_up_top,
            "Y_HUB_TOP": self.y_hub_top,
            "H_BODY": self.h_body,
            "D_RISER": self.d_riser,
            "D_NECK": self.d_neck,
            "H_RISER": self.h_riser,
            "Y_RISER_TOP": self.y_riser_top,
            "L_PRINT": self.l_print,
            "H_PRINT2": self.h_print2,
            "F_PIT": self.f_pit,
            "N_PIT": self.n_pit,
            "F_SLAG": self.f_slag,
            "F_SPRUE": self.f_sprue,
            "RHO": self.rho,
            "MASS_STAMP": self.mass_stamp,
            "SCALE_K": self.scale_k,
            "FMT": self.fmt,
            "CODE": self.code,
            "NAME": list(self.name),
            "MAT": list(self.material),
            "DEV": self.dev,
            "CHK": self.chk,
        }


def compare_to_module(spec: CastingSpec, module: Any) -> List[str]:
    """Сравнить CastingSpec с модулем koleso_data (legacy) — без изменения значений."""
    issues = []
    expected = spec.as_legacy_module_dict()
    for key, want in expected.items():
        if not hasattr(module, key):
            issues.append(f"legacy missing attr {key}")
            continue
        got = getattr(module, key)
        if isinstance(want, float):
            if abs(float(got) - want) > 1e-9:
                issues.append(f"{key}: legacy={got} spec={want}")
        else:
            if got != want:
                issues.append(f"{key}: legacy={got!r} spec={want!r}")
    return issues
