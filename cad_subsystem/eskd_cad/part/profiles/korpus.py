# -*- coding: utf-8 -*-
"""Профиль «Корпус» (вариант 10 / ПП-062215009): PartSpec ↔ параметры отливки."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from ..dxf_extract import (
    diameter_values,
    extract_readings,
    linear_values,
    pick_designation,
    pick_materials,
)
from ..part_spec import CastingDraft, DimensionReading, PartSpec

REQUIRED_DIMS = [
    "h_part",
    "t_top_part",
    "t_bot_part",
    "d_top",
    "d_bot",
    "d_bore_top",
    "d_bore_bot",
    "wall",
    "rib_w",
    "pcd_outer",
    "pcd_inner",
    "d_thru",
    "d_cb",
    "cb_depth",
]

# Эталонные значения эталонного листа -00 (для сопоставления извлечённых чисел).
GOLDEN_DIMS = {
    "h_part": 100.0,
    "t_top_part": 15.0,
    "t_bot_part": 20.0,
    "d_top": 200.0,
    "d_bot": 300.0,
    "d_bore_top": 120.0,
    "d_bore_bot": 190.0,
    "wall": 15.0,
    "rib_w": 10.0,
    "pcd_outer": 250.0,
    "pcd_inner": 168.0,
    "d_thru": 12.0,
    "d_cb": 24.0,
    "cb_depth": 16.0,
    "n_outer": 6.0,
    "n_inner": 4.0,
    "n_ribs": 6.0,
}

DEFAULT_ALLOW = {
    "allow_top": 4.0,
    "allow_bot": 3.0,
    "allow_cb": 2.5,
    "allow_bore": 2.0,
    "draft_ext": 1.5,
    "draft_int": 2.0,
    "shrinkage": 1.0,
    "r_fillet": 5.0,
}


def _assign_known_diameters(diams: List[float], dims: Dict[str, float], prov: Dict[str, str]) -> None:
    """Сопоставить диаметры эталону Корпуса, если набор совпадает."""
    want = {
        300.0: "d_bot",
        250.0: "pcd_outer",
        200.0: "d_top",
        190.0: "d_bore_bot",
        168.0: "pcd_inner",
        120.0: "d_bore_top",
        24.0: "d_cb",
        12.0: "d_thru",
    }
    for d in diams:
        key = want.get(d)
        if key and key not in dims:
            dims[key] = d
            prov[key] = "dxf_text:diameter_match"


def _assign_known_linears(linears: List[float], dims: Dict[str, float], prov: Dict[str, str]) -> None:
    mapping = {
        100.0: "h_part",
        20.0: "t_bot_part",
        16.0: "cb_depth",
        15.0: "t_top_or_wall",  # ambiguous
        10.0: "rib_w",
        5.0: "r_fillet_part",
    }
    counts = {v: linears.count(v) for v in set(linears)}
    for v, key in mapping.items():
        if v not in linears:
            continue
        if key == "t_top_or_wall":
            # на эталоне 15 встречается дважды: t_top и wall
            if "t_top_part" not in dims:
                dims["t_top_part"] = 15.0
                prov["t_top_part"] = "dxf_text:linear_15"
            if "wall" not in dims:
                dims["wall"] = 15.0
                prov["wall"] = "dxf_text:linear_15"
            continue
        if key not in dims:
            dims[key] = v
            prov[key] = f"dxf_text:linear_{v:g}"


def interpret_korpus(
    readings: List[DimensionReading],
    *,
    source_path: str = "",
    allow_golden_fill: bool = True,
) -> PartSpec:
    """Собрать PartSpec профиля korpus из readings."""
    dims: Dict[str, float] = {}
    prov: Dict[str, str] = {}
    questions: List[str] = []

    designation = pick_designation(readings)
    materials = list(pick_materials(readings))
    name = ["Корпус"]
    for r in readings:
        if r.hint == "name" and r.raw_text == "Корпус":
            name = ["Корпус"]

    diams = diameter_values(readings)
    linears = linear_values(readings)
    _assign_known_diameters(diams, dims, prov)
    _assign_known_linears(linears, dims, prov)

    # отверстия / цековка из hint
    for r in readings:
        if r.hint.startswith("holes n="):
            # holes n=6 d=12.0 cb=24.0x16.0
            parts = r.hint.split()
            try:
                dims["n_outer"] = float(parts[1].split("=")[1])
                prov["n_outer"] = "dxf_text:hole_note"
            except (IndexError, ValueError):
                pass

    mass = None
    # На эталонном штампе масса «15» — голое число среди linears; без OCR позиций
    # берём 15 только если есть designation ПП-062215009 или явный reading mass.
    mass_readings = [r.value_mm for r in readings if r.kind == "mass" and r.value_mm is not None]
    linears_all = linear_values(readings)
    if mass_readings:
        mass = mass_readings[0]
        if len(set(mass_readings)) > 1:
            questions.append(f"Подтвердите массу детали: кандидаты {mass_readings}")
    elif designation.startswith("ПП-062215009") and 15.0 in linears_all:
        mass = 15.0
        prov["mass_kg"] = "dxf_text:linear_15_stamp_heuristic"
    else:
        questions.append("Масса детали не определена — укажите mass_kg в PartSpec.")

    if not materials:
        questions.append("Материал не найден на штампе — укажите (ожидается СЧ15 ГОСТ 1412-85).")
        if allow_golden_fill:
            materials = ["СЧ15", "ГОСТ 1412-85"]
            prov["material"] = "profile_default"
    elif "СЧ15" in materials and "ГОСТ 1412-85" not in materials:
        materials.append("ГОСТ 1412-85")

    is_ref = designation.startswith("ПП-062215009")
    missing = [k for k in REQUIRED_DIMS if k not in dims]
    if missing and allow_golden_fill and is_ref:
        for k in missing:
            dims[k] = GOLDEN_DIMS[k]
            prov[k] = "profile_default:golden_korpus_v10"
        questions.append(
            "Часть размеров дополнена эталоном ПП-062215009 (вариант 10). "
            "Проверьте: " + ", ".join(missing)
        )
    elif missing:
        questions.append("Не хватает размеров: " + ", ".join(missing))

    # неоднозначные линейные без эталона
    if not is_ref and "t_top_part" in dims and "wall" in dims and dims["t_top_part"] == dims["wall"]:
        questions.append("Размеры t_top_part и wall совпали (15) — подтвердите оба.")

    questions.extend(
        [
            "Подтвердите плоскость разъёма: горизонтальный по нижнему фланцу Ø%d."
            % int(dims.get("d_bot", 0) or 0),
            "Подтвердите обрабатываемые поверхности: торцы, полость, отв. Ø12/цековки/М8 — механообработка.",
        ]
    )

    process_hints = {
        "parting": "horizontal_bottom_flange",
        "cores": "one_central_on_taper_bore",
        "allowance_class": "9-7-12-9",
        "no_riser_for_grey_iron_training": True,
        "dimension_provenance": prov,
    }

    part_id = designation or "korpus_unknown"
    return PartSpec(
        part_id=part_id,
        designation=designation,
        name=name,
        material=materials,
        mass_kg=mass,
        scale="1:2",
        profile="korpus",
        dimensions=dims,
        readings=readings,
        questions=questions,
        process_hints=process_hints,
        source_path=source_path,
    )


def part_from_dxf(dxf_path: str, *, allow_golden_fill: bool = True) -> PartSpec:
    readings = extract_readings(dxf_path)
    return interpret_korpus(readings, source_path=str(dxf_path), allow_golden_fill=allow_golden_fill)


def part_from_golden() -> PartSpec:
    """Эталонный PartSpec без DXF (для тестов и ручного входа)."""
    readings = [
        DimensionReading("ПП-062215009-00", "designation", confidence=1.0, source="engineer"),
        DimensionReading("СЧ15", "material", confidence=1.0, source="engineer"),
        DimensionReading("ГОСТ 1412-85", "material", confidence=1.0, source="engineer"),
    ]
    for k, v in GOLDEN_DIMS.items():
        kind = "diameter" if k.startswith("d_") or k.startswith("pcd_") else "linear"
        readings.append(
            DimensionReading(
                raw_text=str(v),
                kind=kind,
                value_mm=v,
                confidence=1.0,
                source="engineer",
                hint=k,
            )
        )
    # interpret will also golden-fill; seed dimensions directly
    spec = interpret_korpus(readings, source_path="<golden>", allow_golden_fill=True)
    spec.dimensions = dict(GOLDEN_DIMS)
    spec.mass_kg = 15.0
    spec.questions = [
        "Эталонный PartSpec (инженерный ввод). Подтвердите разъём и припуски перед серией.",
    ]
    return spec


def build_casting(
    part: PartSpec,
    *,
    allowances: Optional[Dict[str, float]] = None,
    mass_cast_stamp: float = 16.5,
) -> CastingDraft:
    """PartSpec → параметры отливки Корпуса (формулы как в drawings/korpus_data.py)."""
    if part.profile != "korpus":
        raise ValueError(f"ожидался profile=korpus, получено {part.profile!r}")
    miss = part.missing_dimensions(REQUIRED_DIMS)
    if miss:
        raise ValueError("PartSpec неполный, нет: " + ", ".join(miss))

    a = dict(DEFAULT_ALLOW)
    if allowances:
        a.update(allowances)

    d = part.dimensions
    h_part = d["h_part"]
    t_top = d["t_top_part"]
    t_bot = d["t_bot_part"]
    d_top = d["d_top"]
    d_bot = d["d_bot"]
    d_bore_top = d["d_bore_top"]
    d_bore_bot = d["d_bore_bot"]
    wall = d["wall"]

    allow_top = a["allow_top"]
    allow_bot = a["allow_bot"]
    allow_bore = a["allow_bore"]

    h_cast = h_part + allow_top + allow_bot
    t_top_cast = t_top + allow_top
    t_bot_cast = t_bot + allow_bot
    d_bore_top_cast = d_bore_top - 2 * allow_bore
    d_bore_bot_cast = d_bore_bot - 2 * allow_bore

    r_out_top = d_bore_top / 2 + wall
    r_out_bot = d_bore_bot / 2 + wall
    r_in_top = d_bore_top / 2
    r_in_bot = d_bore_bot / 2
    r_in_top_cast = d_bore_top_cast / 2
    r_in_bot_cast = d_bore_bot_cast / 2

    mass_part = float(part.mass_kg if part.mass_kg is not None else 15.0)
    density = 7.2e-6
    v_top = math.pi / 4 * (d_top**2 - d_bore_top**2) * allow_top
    v_bot = math.pi / 4 * (d_bot**2 - d_bore_bot**2) * allow_bot
    v_bore = (
        math.pi
        / 4
        * (
            (d_bore_top**2 - d_bore_top_cast**2) * (h_part - t_bot)
            + (d_bore_bot**2 - d_bore_bot_cast**2) * t_bot
        )
        * 0.5
    )
    mass_cast_calc = round(mass_part + (v_top + v_bot + max(v_bore, 0)) * density, 1)

    # ЛС — как в korpus_data
    g_cast = mass_cast_stamp
    tau_fill = round(1.8 * math.sqrt(g_cast), 1)
    h_met, mu, rho = 0.18, 0.4, 6900.0
    sigma = g_cast / (rho * mu * tau_fill * math.sqrt(2 * 9.81 * h_met))
    sigma_fp = round(sigma * 1e4, 2)
    f_slag = round(sigma_fp * 1.1, 2)
    f_sprue = round(sigma_fp * 1.2, 2)
    n_feeders = 2
    f_one_feed = round(sigma_fp / n_feeders, 2)
    d_sprue = int(round(2 * math.sqrt(f_sprue / math.pi) * 10))
    d_sprue_top = d_sprue + 4
    slag_w1, slag_w0 = 22.0, 18.0
    slag_h = round(f_slag * 100 / ((slag_w1 + slag_w0) / 2), 1)
    feed_w, feed_h = 14.0, round(f_one_feed * 100 / 14.0, 1)
    mass_gating = round(0.12 * g_cast + 0.4, 1)
    mass_mold_metal = round(g_cast + mass_gating, 1)
    yield_pct = round(100.0 * g_cast / mass_mold_metal)
    n_castings = 2
    mass_mold_total = round(mass_mold_metal * n_castings, 1)

    designation_00 = part.designation or "ПП-062215009-00"
    if designation_00.endswith("-00"):
        designation_01 = designation_00[:-3] + "-01"
        designation_02 = designation_00[:-3] + "-02"
    else:
        designation_01 = designation_00 + "-01"
        designation_02 = designation_00 + "-02"

    params: Dict[str, Any] = {
        # деталь
        "H_PART": h_part,
        "T_TOP_PART": t_top,
        "T_BOT_PART": t_bot,
        "D_TOP": d_top,
        "D_BOT": d_bot,
        "D_BORE_TOP": d_bore_top,
        "D_BORE_BOT": d_bore_bot,
        "WALL": wall,
        "RIB_W": d["rib_w"],
        "PCD_OUTER": d["pcd_outer"],
        "PCD_INNER": d["pcd_inner"],
        "D_THRU": d["d_thru"],
        "D_CB": d["d_cb"],
        "CB_DEPTH": d["cb_depth"],
        "N_OUTER": int(d.get("n_outer", 6)),
        "N_INNER": int(d.get("n_inner", 4)),
        "N_RIBS": int(d.get("n_ribs", 6)),
        "R_OUT_TOP": r_out_top,
        "R_OUT_BOT": r_out_bot,
        "R_IN_TOP": r_in_top,
        "R_IN_BOT": r_in_bot,
        # припуски
        "ALLOW_TOP": allow_top,
        "ALLOW_BOT": allow_bot,
        "ALLOW_CB": a["allow_cb"],
        "ALLOW_BORE": allow_bore,
        # отливка
        "H_CAST": h_cast,
        "T_TOP_CAST": t_top_cast,
        "T_BOT_CAST": t_bot_cast,
        "D_BORE_TOP_CAST": d_bore_top_cast,
        "D_BORE_BOT_CAST": d_bore_bot_cast,
        "R_IN_TOP_CAST": r_in_top_cast,
        "R_IN_BOT_CAST": r_in_bot_cast,
        "DRAFT_EXT": a["draft_ext"],
        "DRAFT_INT": a["draft_int"],
        "SHRINKAGE": a["shrinkage"],
        "R_FILLET": a["r_fillet"],
        "MATERIAL": list(part.material) if part.material else ["СЧ15", "ГОСТ 1412-85"],
        "MASS_PART": mass_part,
        "DENSITY": density,
        "DESIGNATION_00": designation_00,
        "DESIGNATION_01": designation_01,
        "DESIGNATION_02": designation_02,
        "MASS_PART_STR": str(int(mass_part)) if abs(mass_part - int(mass_part)) < 1e-9 else str(mass_part),
        "DEV": "Шевцов",
        "CHK": "Степанова",
        "ORG": ("СФУ ИЦМ", "гр. ЗЦМ22-01Б"),
        "MASS_CAST_CALC": mass_cast_calc,
        "MASS_CAST": mass_cast_stamp,
        "MASS_STR": ("%.1f" % mass_cast_stamp).replace(".", ","),
        # ЛС
        "G_CAST": g_cast,
        "TAU_FILL": tau_fill,
        "H_MET": h_met,
        "MU": mu,
        "RHO": rho,
        "SIGMA_FP": sigma_fp,
        "F_SLAG": f_slag,
        "F_SPRUE": f_sprue,
        "N_FEEDERS": n_feeders,
        "F_ONE_FEED": f_one_feed,
        "D_SPRUE": d_sprue,
        "D_SPRUE_TOP": d_sprue_top,
        "D_CUP": 50,
        "H_CUP": 40,
        "SLAG_W1": slag_w1,
        "SLAG_W0": slag_w0,
        "SLAG_H": slag_h,
        "FEED_W": feed_w,
        "FEED_H": feed_h,
        "MASS_GATING": mass_gating,
        "MASS_MOLD_METAL": mass_mold_metal,
        "YIELD": yield_pct,
        "N_CASTINGS": n_castings,
        "MASS_MOLD_TOTAL": mass_mold_total,
        "PRINT_BOT_H": 25.0,
        "PRINT_TOP_H": 15.0,
        "PRINT_DRAFT_BOT": 5.0,
        "PRINT_DRAFT_TOP": 12.0,
        "PRINT_GAP": 0.5,
        "VENT_D": 6.0,
        "VENT_RISER_D": 20.0,
        "VENT_RISER_H": 40.0,
        "FLASK_L": 680.0,
        "FLASK_W": 280.0,
    }

    provenance = {
        "geometry": "PartSpec.dimensions",
        "allowances": "DEFAULT_ALLOW (ГОСТ 26645 9-7-12-9, как учебный Корпус)",
        "mass_cast_stamp": "engineer_stamp_default_16.5",
        "gating": "formulas_from_korpus_data",
    }
    warnings: List[str] = []
    if abs(mass_cast_calc - mass_cast_stamp) > 0.5:
        warnings.append(
            f"Масса по припускам {mass_cast_calc} кг ≠ штамп {mass_cast_stamp} кг "
            "(штамп остаётся инженерным назначением)."
        )

    questions = list(part.questions)
    questions.append("Перед сдачей прогоните drawings/draw_otl.py / qa_check по ЕСКД-правилу.")

    return CastingDraft(
        profile="korpus",
        designation=designation_01,
        params=params,
        provenance=provenance,
        warnings=warnings,
        questions=questions,
    )


def assert_matches_korpus_data(draft: CastingDraft, module: Any, tol: float = 1e-9) -> List[str]:
    """Сравнить ключевые поля с drawings/korpus_data.py."""
    keys = [
        "H_CAST",
        "T_TOP_CAST",
        "T_BOT_CAST",
        "D_BORE_TOP_CAST",
        "D_BORE_BOT_CAST",
        "ALLOW_TOP",
        "ALLOW_BOT",
        "ALLOW_BORE",
        "MASS_CAST",
        "D_TOP",
        "D_BOT",
        "H_PART",
        "SIGMA_FP",
        "F_SLAG",
        "F_SPRUE",
        "D_SPRUE",
    ]
    issues = []
    for k in keys:
        want = draft.params[k]
        got = getattr(module, k)
        if isinstance(want, float):
            if abs(float(got) - float(want)) > tol:
                issues.append(f"{k}: module={got} draft={want}")
        else:
            if got != want:
                issues.append(f"{k}: module={got!r} draft={want!r}")
    return issues
