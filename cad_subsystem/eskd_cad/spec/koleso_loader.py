# -*- coding: utf-8 -*-
"""Загрузка CastingSpec из ЕДИНСТВЕННОГО модуля koleso_data (knowledge/calc)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .casting_spec import CastingSpec

KOLESO_PART_ID = "koleso_rabochee"


def _canon_module():
    """Единственный источник констант колеса."""
    from ..knowledge.calc import koleso_data as kd

    return kd


def load_koleso_spec() -> CastingSpec:
    kd = _canon_module()
    return CastingSpec(
        part_id=KOLESO_PART_ID,
        code=kd.CODE,
        name=tuple(kd.NAME),
        material=tuple(kd.MAT),
        mass_stamp=float(kd.MASS_STAMP),
        scale_k=float(kd.SCALE_K),
        fmt=kd.FMT,
        dev=kd.DEV,
        chk=kd.CHK,
        d_out=float(kd.D_OUT),
        d_hub=float(kd.D_HUB),
        d_bore=float(kd.D_BORE),
        d_bore_lo=float(kd.D_BORE_LO),
        d_boss=float(kd.D_BOSS),
        h_hub=float(kd.H_HUB),
        t_disk=float(kd.T_DISK),
        h_ch=float(kd.H_CH),
        h_step=float(kd.H_STEP),
        n_top=float(kd.N_TOP),
        n_bot=float(kd.N_BOT),
        n_face=float(kd.N_FACE),
        n_hub_od=float(kd.N_HUB_OD),
        n_bore=float(kd.N_BORE),
        n_boss=float(kd.N_BOSS),
        c_hub=float(kd.C_HUB),
        c_bore=float(kd.C_BORE),
        c_bore_lo=float(kd.C_BORE_LO),
        c_boss=float(kd.C_BOSS),
        c_out=float(kd.C_OUT),
        c_h_hub=float(kd.C_H_HUB),
        c_t_top=float(kd.C_T_TOP),
        c_t_bot=float(kd.C_T_BOT),
        c_h_ch=float(kd.C_H_CH),
        y_bot=float(kd.Y_BOT),
        y_disk_lo_top=float(kd.Y_DISK_LO_TOP),
        y_disk_up_bot=float(kd.Y_DISK_UP_BOT),
        y_disk_up_top=float(kd.Y_DISK_UP_TOP),
        y_hub_top=float(kd.Y_HUB_TOP),
        h_body=float(kd.H_BODY),
        d_riser=float(kd.D_RISER),
        d_neck=float(kd.D_NECK),
        h_riser=float(kd.H_RISER),
        y_riser_top=float(kd.Y_RISER_TOP),
        l_print=float(kd.L_PRINT),
        h_print2=float(kd.H_PRINT2),
        f_pit=float(kd.F_PIT),
        n_pit=int(kd.N_PIT),
        f_slag=float(kd.F_SLAG),
        f_sprue=float(kd.F_SPRUE),
        rho=float(kd.RHO),
        rim_wall=25.0,
        bore_step_y=43.0,
    )


def spec_as_legacy_ns(spec: CastingSpec) -> SimpleNamespace:
    """Namespace с именами koleso_data — для builders без копирования чисел."""
    d = spec.as_legacy_module_dict()
    d["RIM_WALL"] = spec.rim_wall
    d["BORE_STEP_Y"] = spec.bore_step_y
    return SimpleNamespace(**d)


def assert_spec_aligned_with_canon(spec: CastingSpec | None = None) -> list[str]:
    from .casting_spec import compare_to_module

    spec = spec or load_koleso_spec()
    issues = spec.validate_derived()
    issues += compare_to_module(spec, _canon_module())
    return issues
