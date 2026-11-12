# -*- coding: utf-8 -*-
"""
Сборка CastingSpec из входных данных через существующие таблицы и гейты.

Не переносит расчётную логику в CAD; не подставляет выдуманные значения.
Формулы отливки (C_*, Y_*) — те же, что в koleso_data / CastingSpec.validate_derived.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..spec.casting_spec import CastingSpec
from .core_prints import (
    check_horiz_print,
    check_vert_print_lower,
    check_vert_print_upper,
    horiz_print_l_max,
)
from .errors import CalcDataError, MissingInputError, OutOfRangeError
from .gost26645_table6 import allowance_mm
from .inputs import CastingInputs
from .ls_ratios import areas_from_pit, get_ls_ratio
from .provenance import ParamKind, ParamProvenance
from .riser_gates import check_riser, check_riser_core_scheme, check_riser_neck
from .validate import validate_inputs


@dataclass
class CalcResult:
    spec: CastingSpec
    provenance: Dict[str, ParamProvenance] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    table6_base_mm: float | None = None
    l_print_max_mm: float | None = None
    ls_ratio_case: str | None = None
    h_print2_max_mm: float | None = None
    vert_print_check: dict | None = None

    def provenance_report(self) -> List[dict]:
        return [p.as_dict() for p in self.provenance.values()]


def _rec(
    bag: Dict[str, ParamProvenance],
    name: str,
    value,
    kind: ParamKind,
    unit: str,
    source: str,
    detail: str = "",
    doc_ref: str | None = None,
) -> None:
    bag[name] = ParamProvenance(
        name=name,
        value=value,
        kind=kind,
        unit=unit,
        source=source,
        detail=detail,
        doc_ref=doc_ref,
    )


def build_casting_from_inputs(inp: CastingInputs) -> CalcResult:
    """Вызвать таблицы/гейты и собрать проверенный CastingSpec."""
    validate_inputs(inp)
    prov: Dict[str, ParamProvenance] = {}
    warnings: List[str] = []

    g = inp.geometry
    a = inp.allowance
    r = inp.riser
    gt = inp.gating
    c = inp.cores
    m = inp.meta

    # --- исходная геометрия ---
    for name, val in (
        ("D_OUT", g.d_out),
        ("D_HUB", g.d_hub),
        ("D_BORE", g.d_bore),
        ("D_BORE_LO", g.d_bore_lo),
        ("D_BOSS", g.d_boss),
        ("H_HUB", g.h_hub),
        ("T_DISK", g.t_disk),
        ("H_CH", g.h_ch),
        ("H_STEP", g.h_step),
    ):
        _rec(prov, name, val, ParamKind.SOURCE, "mm", "исходные данные детали", doc_ref="чертеж детали")

    # --- ГОСТ 26645 табл.6 ---
    base = allowance_mm(a.general_tolerance_mm, a.finish, int(a.allowance_row))
    if base is None:
        raise OutOfRangeError(
            f"ГОСТ 26645 табл.6: нет стандартизованного припуска для "
            f"tolerance={a.general_tolerance_mm}, finish={a.finish!r}, "
            f"row={a.allowance_row}. Нельзя подставлять приближение."
        )
    _rec(
        prov,
        "TABLE6_BASE",
        base,
        ParamKind.CALCULATED,
        "mm",
        "таблица",
        detail=f"allowance_mm({a.general_tolerance_mm}, {a.finish!r}, {a.allowance_row})",
        doc_ref="ГОСТ 26645-85 табл.6",
    )
    _rec(
        prov,
        "GENERAL_TOLERANCE",
        a.general_tolerance_mm,
        ParamKind.SOURCE,
        "mm",
        "нормативный документ / ТТ",
        doc_ref="ГОСТ 26645-85",
    )
    _rec(prov, "ALLOWANCE_ROW", a.allowance_row, ParamKind.ENGINEER, "-", "ручной ввод", detail="ряд припуска")
    _rec(prov, "FINISH", a.finish, ParamKind.ENGINEER, "-", "ручной ввод")

    # Принятые припуски (инженер) — не заменяем на base автоматически
    for name, val in (
        ("N_TOP", a.n_top),
        ("N_BOT", a.n_bot),
        ("N_FACE", a.n_face),
        ("N_HUB_OD", a.n_hub_od),
        ("N_BORE", a.n_bore),
        ("N_BOSS", a.n_boss),
    ):
        _rec(
            prov,
            name,
            val,
            ParamKind.ENGINEER,
            "mm",
            "ручной ввод",
            detail=f"принято относительно табл.6 base={base}",
            doc_ref="ГОСТ 26645-85 табл.6 + лист расчёта",
        )
        if val + 1e-9 < base and name in {"N_TOP", "N_BOT", "N_FACE"}:
            warnings.append(
                f"{name}={val} < табл.6 base={base} мм — проверьте назначение припуска"
            )

    # --- производные отливки (те же формулы, что koleso_data) ---
    c_hub = g.d_hub + 2 * a.n_hub_od
    c_bore = g.d_bore - 2 * a.n_bore
    c_bore_lo = g.d_bore_lo - 2 * a.n_bore
    c_boss = g.d_boss + 2 * a.n_boss
    c_out = g.d_out
    c_h_hub = g.h_hub + a.n_top
    c_t_top = g.t_disk + a.n_face
    c_t_bot = g.t_disk + a.n_face
    c_h_ch = g.h_ch
    y_bot = 0.0
    y_disk_lo_top = c_t_bot
    y_disk_up_bot = c_t_bot + c_h_ch
    y_disk_up_top = y_disk_up_bot + c_t_top
    y_hub_top = y_disk_up_top + c_h_hub
    h_body = y_hub_top
    y_riser_top = h_body + r.h_riser

    derived = {
        "C_HUB": (c_hub, "D_HUB + 2*N_HUB_OD"),
        "C_BORE": (c_bore, "D_BORE - 2*N_BORE"),
        "C_BORE_LO": (c_bore_lo, "D_BORE_LO - 2*N_BORE"),
        "C_BOSS": (c_boss, "D_BOSS + 2*N_BOSS"),
        "C_OUT": (c_out, "D_OUT"),
        "C_H_HUB": (c_h_hub, "H_HUB + N_TOP"),
        "C_T_TOP": (c_t_top, "T_DISK + N_FACE"),
        "C_T_BOT": (c_t_bot, "T_DISK + N_FACE"),
        "C_H_CH": (c_h_ch, "H_CH"),
        "Y_BOT": (y_bot, "0"),
        "Y_DISK_LO_TOP": (y_disk_lo_top, "C_T_BOT"),
        "Y_DISK_UP_BOT": (y_disk_up_bot, "C_T_BOT + C_H_CH"),
        "Y_DISK_UP_TOP": (y_disk_up_top, "Y_DISK_UP_BOT + C_T_TOP"),
        "Y_HUB_TOP": (y_hub_top, "Y_DISK_UP_TOP + C_H_HUB"),
        "H_BODY": (h_body, "Y_HUB_TOP"),
        "Y_RISER_TOP": (y_riser_top, "H_BODY + H_RISER"),
    }
    for name, (val, formula) in derived.items():
        _rec(prov, name, val, ParamKind.CALCULATED, "mm", "формула", detail=formula)

    # --- прибыль: гейты qa_check ---
    _rec(prov, "D_RISER", r.d_riser, ParamKind.ENGINEER, "mm", "ручной ввод", doc_ref="лист расчёта §2")
    _rec(prov, "D_NECK", r.d_neck, ParamKind.ENGINEER, "mm", "ручной ввод", doc_ref="pribyli_sheyka.md")
    _rec(prov, "H_RISER", r.h_riser, ParamKind.ENGINEER, "mm", "ручной ввод", doc_ref="лист расчёта §2")
    _rec(
        prov,
        "RISER_CORE_SCHEME",
        r.core_scheme,
        ParamKind.ENGINEER,
        "-",
        "ручной ввод",
        doc_ref="pribyli_sheyka.md",
    )

    riser_issues = []
    riser_issues += check_riser(r.d_riser, c_hub)
    riser_issues += check_riser_neck(r.d_neck, c_hub, r.d_riser, c_hub)
    riser_issues += check_riser_core_scheme(r.core_scheme)
    if riser_issues:
        raise CalcDataError("Гейты прибыли не пройдены:\n- " + "\n- ".join(riser_issues))
    _rec(
        prov,
        "RISER_GATES",
        "OK",
        ParamKind.CALCULATED,
        "-",
        "формула",
        detail="check_riser / check_riser_neck / check_riser_core_scheme",
        doc_ref="qa_check.py / STOP_GATES G3",
    )

    # --- литниковая: CSV ratios ---
    ratio = get_ls_ratio(gt.ls_ratio_case)
    f_pit, f_slag, f_sprue = areas_from_pit(gt.f_pit_cm2, ratio)
    _rec(
        prov,
        "F_PIT",
        f_pit,
        ParamKind.ENGINEER,
        "cm2",
        "ручной ввод",
        detail="ΣFп принято",
        doc_ref="лист расчёта §3",
    )
    _rec(prov, "N_PIT", gt.n_pit, ParamKind.ENGINEER, "-", "ручной ввод")
    _rec(
        prov,
        "F_SLAG",
        f_slag,
        ParamKind.CALCULATED,
        "cm2",
        "таблица",
        detail=f"F_PIT * ({ratio.f_slag}/{ratio.f_pit}) case={ratio.alloy_or_case}",
        doc_ref=f"ls_ratios_all.csv / {ratio.source_note}",
    )
    _rec(
        prov,
        "F_SPRUE",
        f_sprue,
        ParamKind.CALCULATED,
        "cm2",
        "таблица",
        detail=f"F_PIT * ({ratio.f_sprue}/{ratio.f_pit}) case={ratio.alloy_or_case}",
        doc_ref=f"ls_ratios_all.csv / {ratio.source_note}",
    )
    _rec(
        prov,
        "LS_RATIO_CASE",
        ratio.alloy_or_case,
        ParamKind.ENGINEER,
        "-",
        "таблица",
        detail=f"1 : {ratio.f_slag:g} : {ratio.f_sprue:g}",
        doc_ref="ls_ratios_all.csv",
    )

    # --- стержни: гориз. знак из JSON ---
    l_max, row_key, col_key = horiz_print_l_max(c.section_mm, c.core_length_mm)
    _, print_issues = check_horiz_print(c.l_print, c.section_mm, c.core_length_mm)
    if print_issues:
        raise CalcDataError("Проверка знаков стержней:\n- " + "\n- ".join(print_issues))
    _rec(
        prov,
        "L_PRINT_MAX",
        l_max,
        ParamKind.CALCULATED,
        "mm",
        "таблица",
        detail=f"row={row_key}, col={col_key}",
        doc_ref="sterzhni_horiz_syroe.json / ГОСТ 3212-92",
    )
    _rec(
        prov,
        "L_PRINT",
        c.l_print,
        ParamKind.ENGINEER,
        "mm",
        "ручной ввод",
        detail=f"≤ l_max={l_max}",
        doc_ref="лист расчёта §4 / sterzhni_raschet",
    )
    # P4.5.1: верт. знак Ст.2 — check-only по табл.7 (D=C_BORE, L=H_BODY)
    vert_chk = check_vert_print_lower(
        c.h_print2, float(c_bore), float(h_body)
    )
    upper_chk = check_vert_print_upper(
        None, c.h_print2, upper_present=False
    )
    vert_chk["upper"] = upper_chk
    vert_chk["core2_params"] = {
        "D_mm": float(c_bore),
        "D_source": "CastingSpec.c_bore (Core2Params.diameter_mm)",
        "L_mm": float(h_body),
        "L_source": "CastingSpec.h_body (Core2Params.height_mm, рабочая высота Ст.2)",
        "H_PRINT2_source": "CorePrintInputs.h_print2 / engineer",
    }
    h_print2_max = vert_chk.get("h_max")
    _rec(
        prov,
        "H_PRINT2",
        c.h_print2,
        ParamKind.ENGINEER,
        "mm",
        "ручной ввод",
        detail=(
            f"верт. нижний знак Ст.2; gate={vert_chk['status']}: {vert_chk['detail']}"
        ),
        doc_ref="лист расчёта §4 / ГОСТ 3212-92 табл.7",
    )
    if h_print2_max is not None:
        _rec(
            prov,
            "H_PRINT2_MAX",
            h_print2_max,
            ParamKind.CALCULATED,
            "mm",
            "таблица",
            detail=(
                f"табл.7 row={vert_chk['lookup'].get('row_key')}, "
                f"col={vert_chk['lookup'].get('col_key')}; D={c_bore}, L={h_body}"
            ),
            doc_ref=str(vert_chk.get("source_ref") or "sterzhni_vert_lower.json"),
        )
    else:
        _rec(
            prov,
            "H_PRINT2_MAX",
            None,
            ParamKind.CALCULATED,
            "mm",
            "таблица",
            detail=(
                f"h_max недоступен: {vert_chk['lookup'].get('status')} — "
                f"{vert_chk['detail']}"
            ),
            doc_ref=str(vert_chk.get("source_ref") or "sterzhni_vert_lower.json"),
        )
    if vert_chk["status"] == "WARNING":
        warnings.append(vert_chk["detail"])
    _rec(prov, "CORE_SECTION", c.section_mm, ParamKind.SOURCE, "mm", "исходные данные детали", detail="H_CH / сеч. знака Ст.1")
    _rec(prov, "CORE_LENGTH", c.core_length_mm, ParamKind.ENGINEER, "mm", "ручной ввод", detail="L для табл. гориз. знаков Ст.1")
    _rec(
        prov,
        "CORE2_D",
        float(c_bore),
        ParamKind.CALCULATED,
        "mm",
        "формула",
        detail="D Ст.2 = C_BORE для табл.7",
        doc_ref="ГОСТ 3212-92 табл.7 / Core2Params.diameter_mm",
    )
    _rec(
        prov,
        "CORE2_L",
        float(h_body),
        ParamKind.CALCULATED,
        "mm",
        "формула",
        detail="L Ст.2 = H_BODY (рабочая высота отверстия), не высота знака",
        doc_ref="ГОСТ 3212-92 табл.7 / Core2Params.height_mm",
    )

    # мета
    _rec(prov, "CODE", m.code, ParamKind.SOURCE, "-", "исходные данные детали")
    _rec(prov, "MASS_STAMP", m.mass_stamp, ParamKind.ENGINEER, "kg", "ручной ввод", doc_ref="лист расчёта §6")
    _rec(prov, "RHO", m.rho, ParamKind.SOURCE, "kg/mm3", "нормативный документ / материал")
    _rec(prov, "SCALE_K", m.scale_k, ParamKind.ENGINEER, "-", "ручной ввод")
    _rec(prov, "RIM_WALL", m.rim_wall, ParamKind.ENGINEER, "mm", "ручной ввод", detail="толщина обода в сечении")
    _rec(prov, "BORE_STEP_Y", m.bore_step_y, ParamKind.ENGINEER, "mm", "ручной ввод")

    spec = CastingSpec(
        part_id=m.part_id,
        code=m.code,
        name=tuple(m.name),
        material=tuple(m.material),
        mass_stamp=float(m.mass_stamp),
        scale_k=float(m.scale_k),
        fmt=m.fmt,
        dev=m.dev,
        chk=m.chk,
        d_out=float(g.d_out),
        d_hub=float(g.d_hub),
        d_bore=float(g.d_bore),
        d_bore_lo=float(g.d_bore_lo),
        d_boss=float(g.d_boss),
        h_hub=float(g.h_hub),
        t_disk=float(g.t_disk),
        h_ch=float(g.h_ch),
        h_step=float(g.h_step),
        n_top=float(a.n_top),
        n_bot=float(a.n_bot),
        n_face=float(a.n_face),
        n_hub_od=float(a.n_hub_od),
        n_bore=float(a.n_bore),
        n_boss=float(a.n_boss),
        c_hub=float(c_hub),
        c_bore=float(c_bore),
        c_bore_lo=float(c_bore_lo),
        c_boss=float(c_boss),
        c_out=float(c_out),
        c_h_hub=float(c_h_hub),
        c_t_top=float(c_t_top),
        c_t_bot=float(c_t_bot),
        c_h_ch=float(c_h_ch),
        y_bot=float(y_bot),
        y_disk_lo_top=float(y_disk_lo_top),
        y_disk_up_bot=float(y_disk_up_bot),
        y_disk_up_top=float(y_disk_up_top),
        y_hub_top=float(y_hub_top),
        h_body=float(h_body),
        d_riser=float(r.d_riser),
        d_neck=float(r.d_neck),
        h_riser=float(r.h_riser),
        y_riser_top=float(y_riser_top),
        l_print=float(c.l_print),
        h_print2=float(c.h_print2),
        f_pit=float(f_pit),
        n_pit=int(gt.n_pit),
        f_slag=float(f_slag),
        f_sprue=float(f_sprue),
        rho=float(m.rho),
        rim_wall=float(m.rim_wall),
        bore_step_y=float(m.bore_step_y),
    )

    derived_issues = spec.validate_derived()
    if derived_issues:
        raise CalcDataError(
            "CastingSpec не прошёл validate_derived:\n- " + "\n- ".join(derived_issues)
        )

    return CalcResult(
        spec=spec,
        provenance=prov,
        warnings=warnings,
        table6_base_mm=float(base),
        l_print_max_mm=float(l_max),
        ls_ratio_case=ratio.alloy_or_case,
        h_print2_max_mm=(
            float(h_print2_max) if h_print2_max is not None else None
        ),
        vert_print_check=vert_chk,
    )


def build_koleso_casting_result() -> CalcResult:
    """Runtime-путь для рабочего колеса: inputs → таблицы/гейты → CastingSpec."""
    from .wheel_inputs import koleso_casting_inputs

    return build_casting_from_inputs(koleso_casting_inputs())
