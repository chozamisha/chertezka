# -*- coding: utf-8 -*-
"""Профиль koleso: рабочее колесо (два диска, ступица, канал, лопасти).

Числа геометрии детали — из PartSpec (исходный чертёж). Припуски, прибыль,
ЛС — из decisions / листа расчёта КП-062215009-01. Рендер — DrawingDocument
(eskd_cad.foundry), не cad_work/draw_otl.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ...calc.inputs import (
    AllowanceInputs,
    CastingInputs,
    CorePrintInputs,
    GatingInputs,
    MetaInputs,
    PartGeometryInputs,
    RiserInputs,
)
from ...calc.pipeline import build_casting_from_inputs
from ...calc.wheel_inputs import koleso_casting_inputs
from ...spec.casting_spec import CastingSpec
from ..decisions import Decision
from ..part_spec import CastingDraft, PartSpec

REQUIRED_DIMS = [
    "d_out", "d_hub", "d_bore", "d_bore_lo", "d_boss",
    "h_hub", "t_disk", "h_ch", "h_step",
]
DIM_LABELS = {
    "d_out": "⌀ наружный",
    "d_hub": "⌀ ступицы",
    "d_bore": "⌀ отверстия",
    "d_bore_lo": "⌀ нижней расточки",
    "d_boss": "⌀ бобышки",
    "h_hub": "высота ступицы над диском",
    "t_disk": "толщина диска",
    "h_ch": "высота канала",
    "h_step": "высота ступени отверстия",
}

# эталон исходника КП-062215009-01
GOLDEN = {
    "d_out": 825.0, "d_hub": 240.0, "d_bore": 140.0, "d_bore_lo": 180.0, "d_boss": 340.0,
    "h_hub": 253.0, "t_disk": 40.0, "h_ch": 115.0, "h_step": 38.0,
}


def validate(part: PartSpec) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if part.profile != "koleso":
        errors.append(f"ожидался profile=koleso, получено {part.profile!r}")
    missing = part.missing_dimensions(REQUIRED_DIMS)
    if missing:
        errors.append("Нет размеров: " + ", ".join(f"{k} ({DIM_LABELS[k]})" for k in missing))
    if not part.designation:
        errors.append("Нет обозначения.")
    if not part.material:
        errors.append("Нет материала.")
    if part.mass_kg is None:
        errors.append("Нет массы детали.")
    if missing:
        return errors, warnings
    d = part.dimensions
    for k in REQUIRED_DIMS:
        if d[k] <= 0:
            errors.append(f"{DIM_LABELS[k]} должен быть > 0.")
    if d["d_bore"] >= d["d_hub"]:
        errors.append("Отверстие ступицы не меньше наружного ⌀ ступицы.")
    if d["d_bore_lo"] <= d["d_bore"]:
        warnings.append("Нижняя расточка не больше ⌀140 — проверьте h_step/d_bore_lo.")
    if d["d_boss"] <= d["d_hub"]:
        warnings.append("Бобышка не больше ступицы — необычно для этого профиля.")
    return errors, warnings


def matches_golden(part: PartSpec, tol: float = 0.05) -> bool:
    return all(abs(part.dimensions.get(k, -1) - v) <= tol for k, v in GOLDEN.items())


def default_decisions(part: PartSpec) -> Dict[str, Decision]:
    """Решения по листу расчёта КП-062215009-01; неподтверждённые — спросить."""
    calc = "лист расчёта KP-062215009-01_calc.md"
    src = "исходный чертёж детали"
    out: Dict[str, Decision] = {}
    # на этом комплекте обозначение отливки = обозначение детали
    out["designation_casting"] = Decision(
        part.designation, f"{src}: обозначение отливки совпадает с деталью", True)
    out["mold_position"] = Decision(
        "ступица вверх, разъём по середине канала", calc, False)
    out["allow_top"] = Decision(6.0, f"{calc}: табл.6 ≈5,2 + верх формы", False, "мм")
    out["allow_bot"] = Decision(5.0, calc, False, "мм")
    out["allow_face"] = Decision(5.0, calc, False, "мм, торцы дисков")
    out["allow_hub_od"] = Decision(4.0, calc, False, "мм на сторону")
    out["allow_bore"] = Decision(4.0, calc, False, "мм на сторону")
    out["allow_boss"] = Decision(3.0, calc, False, "мм на сторону")
    out["accuracy"] = Decision(
        part.notes.get("accuracy") or "10-10-5-3 ГОСТ 26645-85",
        f"{src}: ТТ" if part.notes.get("accuracy") else calc, True)
    out["draft_ext"] = Decision(1.5, "ГОСТ 3212-92", True, "градусы")
    out["draft_int"] = Decision(2.0, "ГОСТ 3212-92", True, "градусы")
    out["shrinkage"] = Decision(1.9, f"{calc}: усадка ИЧХ28Н2", False, "%")
    out["r_fillet"] = Decision(
        part.notes.get("cast_radii") or "R5…R10",
        f"{src}: ТТ" if part.notes.get("cast_radii") else calc, True)
    out["mass_cast_kg"] = Decision(420.0, f"{calc}: штамп отливки", False,
                                   f"масса детали {part.mass_kg:g} кг")
    out["d_riser"] = Decision(300.0, calc, False)
    out["d_neck"] = Decision(240.0, calc, False)
    out["h_riser"] = Decision(300.0, calc, False)
    out["l_print"] = Decision(60.0, calc, False)
    out["h_print2"] = Decision(40.0, calc, False)
    out["f_pit"] = Decision(12.0, calc, False, "см²")
    out["n_pit"] = Decision(2, calc, False)
    stamp = part.stamp
    out["dev"] = Decision(stamp.get("dev") or "Шарабуров",
                          f"{src}: Разраб." if stamp.get("dev") else calc, bool(stamp.get("dev")))
    out["chk"] = Decision(stamp.get("chk") or "Степанова",
                          f"{src}: Пров." if stamp.get("chk") else calc, bool(stamp.get("chk")))
    out["org"] = Decision(list(stamp.get("org") or ["СФУ ИЦМ", "гр. ЗЦМ22-01Б"]),
                          f"{src}: орг." if stamp.get("org") else calc, bool(stamp.get("org")))
    out["lit"] = Decision(stamp.get("lit") or "У", src if stamp.get("lit") else calc, True)
    out["n_blades"] = Decision(4, f"{src}: ТТ «лопасти 4 шт.»", True)
    hardness = part.notes.get("hardness")
    if hardness:
        out["hardness"] = Decision(hardness, f"{src}: ТТ / подтверждение инженера", True)
    else:
        out["hardness"] = Decision("HB 500…550", calc, False, "уточнить по исходнику")
    return out


def _inputs_from(part: PartSpec, decisions: Dict[str, Decision]) -> CastingInputs:
    """PartSpec + decisions → CastingInputs для calc.pipeline."""
    v = {k: d.value for k, d in decisions.items()}
    d = part.dimensions
    base = koleso_casting_inputs()
    return CastingInputs(
        meta=MetaInputs(
            # registry builder ключ — не обозначение ЕСКД
            part_id="koleso_rabochee",
            code=str(v["designation_casting"]),
            name=("Колесо рабочее", "Отливка"),
            material=tuple(part.material),
            mass_stamp=float(v["mass_cast_kg"]),
            scale_k=5.0 if (part.scale or "").endswith("5") else float(base.meta.scale_k),
            fmt="A2",
            dev=str(v["dev"]),
            chk=str(v["chk"]),
            rho=7.46e-6,
            rim_wall=base.meta.rim_wall,
            bore_step_y=base.meta.bore_step_y,
        ),
        geometry=PartGeometryInputs(
            d_out=d["d_out"], d_hub=d["d_hub"], d_bore=d["d_bore"],
            d_bore_lo=d["d_bore_lo"], d_boss=d["d_boss"],
            h_hub=d["h_hub"], t_disk=d["t_disk"], h_ch=d["h_ch"], h_step=d["h_step"],
        ),
        allowance=AllowanceInputs(
            general_tolerance_mm=2.8,
            finish="Чистовая",
            allowance_row=11,
            n_top=float(v["allow_top"]),
            n_bot=float(v["allow_bot"]),
            n_face=float(v["allow_face"]),
            n_hub_od=float(v["allow_hub_od"]),
            n_bore=float(v["allow_bore"]),
            n_boss=float(v["allow_boss"]),
        ),
        riser=RiserInputs(
            d_riser=float(v["d_riser"]), d_neck=float(v["d_neck"]), h_riser=float(v["h_riser"]),
            core_scheme="A",
        ),
        gating=GatingInputs(
            f_pit_cm2=float(v["f_pit"]), n_pit=int(v["n_pit"]),
            ls_ratio_case="ICHX_academic_default",
        ),
        cores=CorePrintInputs(
            section_mm=d["h_ch"],
            core_length_mm=200.0,
            l_print=float(v["l_print"]),
            h_print2=float(v["h_print2"]),
        ),
    )


def build_casting(part: PartSpec, decisions: Dict[str, Decision]) -> CastingDraft:
    errors, _ = validate(part)
    if errors:
        raise ValueError("PartSpec koleso не годится: " + " ".join(errors))
    inputs = _inputs_from(part, decisions)
    result = build_casting_from_inputs(inputs)
    spec: CastingSpec = result.spec
    params: Dict[str, Any] = {
        "SPEC": spec,
        "CALC": result,
        "CODE": spec.code,
        "MASS_CAST": spec.mass_stamp,
        "H_BODY": spec.h_body,
        "C_OUT": spec.c_out,
        "C_HUB": spec.c_hub,
        "C_BORE": spec.c_bore,
        "N_TOP": spec.n_top,
        "N_BOT": spec.n_bot,
        "N_FACE": spec.n_face,
        "N_HUB_OD": spec.n_hub_od,
        "N_BORE": spec.n_bore,
        "N_BOSS": spec.n_boss,
        "DEV": spec.dev,
        "CHK": spec.chk,
        "MATERIAL": list(spec.material),
        "NAME": list(spec.name),
        "DESIGNATION_01": spec.code,
        "WARNINGS": list(result.warnings),
        "ALIGN_GOLDEN": matches_golden(part),
    }
    return CastingDraft(
        profile="koleso",
        designation=spec.code,
        params=params,
        provenance={k: d.source for k, d in decisions.items()},
        warnings=list(result.warnings),
        questions=list(part.questions),
    )
