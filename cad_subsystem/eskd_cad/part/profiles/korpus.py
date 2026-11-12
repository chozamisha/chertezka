# -*- coding: utf-8 -*-
"""Профиль korpus: полое тело вращения с двумя фланцами и стенкой между ними.

Сюда подходит учебный «Корпус» (ПП-062215009) и любая деталь той же топологии
с другими размерами: стенка коническая или цилиндрическая, отверстия по
окружностям, радиальные рёбра.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from shapely.geometry import Polygon

from .. import dxf_geom
from ..decisions import Decision
from ..dxf_extract import Snapper, parse_hole_note, readings_from_texts, tt_lines
from ..part_spec import CastingDraft, HoleGroup, PartSpec, Ribs

REQUIRED_DIMS = [
    "h_part", "t_top_part", "t_bot_part", "d_top", "d_bot",
    "d_bore_top", "d_bore_bot", "wall",
]
DIM_LABELS = {
    "h_part": "высота детали",
    "t_top_part": "толщина верхнего фланца",
    "t_bot_part": "толщина нижнего фланца",
    "d_top": "⌀ верхнего фланца",
    "d_bot": "⌀ нижнего фланца",
    "d_bore_top": "⌀ отверстия вверху",
    "d_bore_bot": "⌀ отверстия внизу",
    "wall": "толщина стенки по горизонтали",
}
STANDARD_K = (1.0, 2.0, 2.5, 4.0, 5.0, 10.0, 0.5, 0.4, 0.25, 0.2)  # ГОСТ 2.302
GREY_IRON_DENSITY = 7.2e-6  # кг/мм³


def fmt(v: float, n: int = 1) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.*f" % (n, v)).replace(".", ",")


def default_decisions(part: PartSpec) -> Dict[str, Decision]:
    """Решения по умолчанию для korpus. Неподтверждённые требуют ответа инженера."""
    kit = "эталонный комплект «Корпус» в репозитории, не исходный чертёж"
    rule = "правило .cursor/rules/eskd.mdc"
    source = "исходный чертёж детали"
    rough, stamp = part.roughness, part.stamp
    out: Dict[str, Decision] = {}

    code = part.designation
    if code.endswith("-00"):
        out["designation_casting"] = Decision(code[:-3] + "-01", f"{rule}: деталь -00, отливка -01", True)
    else:
        out["designation_casting"] = Decision(
            f"{code}-01" if code else "", "суффикс -01 к обозначению детали", False,
            "обозначение детали не оканчивается на -00")

    out["mold_position"] = Decision(
        "верхний фланец вверху формы, разъём по плоскости нижнего фланца", kit, False,
        "от положения в форме зависит, какой торец получает больший припуск")

    for key, face, label in (("machined_top", "top", "верхний торец"),
                             ("machined_bottom", "bottom", "нижний торец")):
        if rough.get(face):
            out[key] = Decision(True, f"{source}: знак {rough[face]} на поверхности «{label}»", True)
        else:
            out[key] = Decision(True, kit, False, f"знак шероховатости на поверхности «{label}» не найден")
    if rough.get("bore"):
        out["machined_bore"] = Decision(True, f"{source}: знак {rough['bore']} на отверстии", True)
    else:
        out["machined_bore"] = Decision(True, kit, False,
                                        "на исходном чертеже знака на центральном отверстии нет")

    gost = "ГОСТ 26645-85; таблиц допусков в репозитории нет, значение взято из эталонного комплекта"
    out["allow_top"] = Decision(4.0, gost, False, "мм, верхний торец")
    out["allow_bottom"] = Decision(3.0, gost, False, "мм, нижний торец")
    out["allow_bore"] = Decision(2.0, gost, False, "мм на сторону, центральное отверстие")
    out["accuracy"] = Decision("9-7-12-9", gost, False, "класс точности отливки для ТТ")
    out["draft_ext"] = Decision(1.5, f"ГОСТ 3212-92; {kit}", False, "градусы, наружные поверхности")
    out["draft_int"] = Decision(2.0, f"ГОСТ 3212-92; {kit}", False, "градусы, внутренние поверхности")
    out["shrinkage"] = Decision(1.0, f"{rule}: усадка 1 %", True)
    out["r_fillet"] = Decision(5.0, kit, False,
                               "мм; в ТТ детали: " + part.notes["radii"] if part.notes.get("radii") else "мм")

    faces = rough.get("top") or rough.get("bottom")
    out["ra_faces"] = (Decision(faces, f"{source}: знак на торце", True) if faces
                       else Decision("Ra 6,3", kit, False))
    out["ra_general"] = (Decision(rough["general"], f"{source}: знак в правом верхнем углу", True)
                         if rough.get("general") else Decision("Ra 12,5", kit, False))
    out["hardness"] = (Decision(part.notes["hardness"], f"{source}: технические требования", True)
                       if part.notes.get("hardness") else Decision(None, "на исходном чертеже не указана", True))
    out["heat_treatment"] = Decision("отжиг 500…550 °С", kit, False, "пункт ТТ; null, если не нужен")
    out["mass_cast_kg"] = Decision(None, f"{rule}: масса детали плюс припуски", False,
                                   "null: считать как масса детали из штампа + припуски и напуски по геометрии")

    if part.ribs:
        step = 360.0 / part.ribs.n
        a0 = part.ribs.angle0 % step
        in_plane = min(a0, step - a0) < 1.0 or any(
            abs((ang - a0 + step / 2) % step - step / 2) < 1.0 for ang in (0.0, 180.0))
        if in_plane:
            out["rib_angle0"] = Decision(
                step / 2, f"{rule}: рёбра не в секущей плоскости А-А", False,
                f"на исходном чертеже рёбра показаны под {a0:g}°, то есть в плоскости разреза")
        else:
            out["rib_angle0"] = Decision(a0, source, True)

    for key, label in (("dev", "Разраб."), ("chk", "Пров."), ("lit", "Лит.")):
        if stamp.get(key):
            out[key] = Decision(stamp[key], f"{source}: графа «{label}»", True)
        else:
            out[key] = Decision("", f"графа «{label}» не прочитана", False)
    if stamp.get("org"):
        out["org"] = Decision(list(stamp["org"]), f"{source}: графа организации", True)
    else:
        out["org"] = Decision([], "графа организации не прочитана", False)

    out["gating"] = Decision(
        {"tau_coeff": 1.8, "h_met_m": 0.18, "mu": 0.4, "rho_liquid": 6900.0, "n_feeders": 2},
        f"{rule}: ΣFп:Fшл:Fст = 1:1,1:1,2; коэффициенты из расчёта эталонного комплекта", False,
        "τ = k·√G, ΣFп = G / (ρ·μ·τ·√(2gH))")
    return out


# ---------------------------------------------------------------- DXF → PartSpec

def _choose_scale(stamp, measures: List[Tuple[float, str]], snapper: Snapper, part: PartSpec) -> float:
    def hits(k: float) -> int:
        return sum(snapper.score(m * k, kind) for m, kind in measures)

    best = max(STANDARD_K, key=hits)
    if stamp.scale_k:
        k = stamp.scale_k
        if hits(best) > hits(k) and hits(k) < 2:
            part.warnings.append(
                f"Масштаб в штампе {stamp.scale}, но размерные числа лучше сходятся с геометрией "
                f"при 1:{fmt(best)} ({hits(best)} совпадений против {hits(k)}).")
        part.provenance["scale"] = "основная надпись DXF"
        return k
    if hits(best) >= 3:
        part.scale = f"1:{fmt(best)}" if best >= 1 else f"{fmt(1 / best)}:1"
        part.provenance["scale"] = f"подобран по {hits(best)} размерным числам, в штампе не найден"
        return best
    part.questions.append("Масштаб не найден в штампе и не подбирается по размерным числам; принят 1:1.")
    part.scale = "1:1"
    return 1.0


def _const(piece, tol: float) -> bool:
    return abs(piece[2] - piece[3]) <= tol


def _read_section(sec, k: float, snapper: Snapper, part: PartSpec) -> Optional[Dict[str, float]]:
    """Размеры профиля из образующих разреза. None, если топология не та."""
    outer, inner = dxf_geom.section_profile(sec)
    outer = [tuple(v * k for v in p) for p in outer]
    inner = [tuple(v * k for v in p) for p in inner]
    tol = 0.05 * k
    if len(outer) != 3 or not _const(outer[0], tol) or not _const(outer[2], tol):
        part.questions.append(
            "Сечение не похоже на профиль korpus (нижний фланец, стенка, верхний фланец): "
            f"наружный контур состоит из {len(outer)} участков. Нужен другой профиль или PartSpec вручную.")
        return None
    h = outer[-1][1]
    t_bot, t_top = outer[0][1], outer[2][1] - outer[2][0]
    r_in_bot, r_in_top = inner[0][2], inner[-1][3]

    def r_in_model(y: float) -> float:
        if y <= t_bot:
            return r_in_bot
        if y >= h - t_top:
            return r_in_top
        return r_in_bot + (r_in_top - r_in_bot) * (y - t_bot) / (h - t_top - t_bot)

    for y0, y1, r0, r1 in inner:
        if abs(r_in_model(y0) - r0) > 2 * tol or abs(r_in_model(y1) - r1) > 2 * tol:
            part.questions.append(
                "Внутренний контур в разрезе сложнее, чем у профиля korpus (цилиндр в пределах "
                "фланцев и конус между ними). Нужен другой профиль или PartSpec вручную.")
            return None
    wall_bot, wall_top = outer[1][2] - r_in_bot, outer[1][3] - r_in_top
    if abs(wall_bot - wall_top) > 2 * tol:
        part.questions.append(
            f"Стенка переменной толщины (внизу {fmt(wall_bot, 2)}, вверху {fmt(wall_top, 2)} мм): "
            "профиль korpus рисует только постоянную.")
        return None

    measured = {
        "h_part": (h, "linear"), "t_bot_part": (t_bot, "linear"), "t_top_part": (t_top, "linear"),
        "d_bot": (2 * outer[0][2], "diameter"), "d_top": (2 * outer[2][2], "diameter"),
        "d_bore_bot": (2 * r_in_bot, "diameter"), "d_bore_top": (2 * r_in_top, "diameter"),
        "wall": (wall_bot, "linear"),
    }
    dims = {}
    for name, (value, kind) in measured.items():
        dims[name], part.provenance[name] = snapper.snap(value, kind, name)
    return dims


def _read_holes(plan, k: float, snapper: Snapper, part: PartSpec) -> None:
    notes = [n for n in (parse_hole_note(r.raw_text) for r in part.readings if r.kind == "holes") if n]
    for g in plan.holes:
        pcd, src = snapper.snap(g.pcd * k, "diameter", "pcd")
        d_geom = [round(d * k, 2) for d in g.diameters]
        note = next((n for n in notes if n["n"] == g.n and "d" in n and (
            abs(n["d"] - d_geom[0]) <= 0.5 or ("thread" in n and 0.75 * n["d"] <= d_geom[0] <= 1.02 * n["d"])
        )), None)
        hole = HoleGroup(pcd=pcd, n=g.n, d=d_geom[0], angle0=g.angle0)
        if len(d_geom) > 1:
            hole.kind, hole.d_cb = "cbore", d_geom[-1]
        if note:
            notes.remove(note)
            hole.d, hole.label = note["d"], note["label"]
            if "thread" in note:
                hole.kind = "thread"
            if "d_cb" in note:
                hole.kind, hole.d_cb = "cbore", note["d_cb"]
            hole.cb_depth = note.get("cb_depth")
            part.provenance[f"holes ⌀{fmt(pcd)}"] = f"окружности на виде сверху + выноска «{note['label']}»; {src}"
        else:
            part.provenance[f"holes ⌀{fmt(pcd)}"] = f"окружности на виде сверху, выноска не найдена; {src}"
            part.questions.append(
                f"Для {g.n} отверстий ⌀{fmt(hole.d, 2)} на окружности ⌀{fmt(pcd)} не найдена выноска: "
                "резьба, цековка и глубина неизвестны.")
        if hole.kind == "cbore" and hole.cb_depth is None:
            part.questions.append(
                f"Глубина цековки ⌀{fmt(hole.d_cb)} не указана (влияет только на массу отливки).")
        part.holes.append(hole)
    for n in notes:
        part.questions.append(f"Выноска «{n['label']}» не сопоставлена с окружностями на виде сверху.")


def _read_roughness(sec, plan, part: PartSpec) -> None:
    x0, _, x1, _ = sec.region.bounds
    for r in part.readings:
        if r.kind != "roughness" or r.x is None:
            continue
        if not x0 - 25 <= r.x <= x1 + 25:
            part.roughness.setdefault("general", r.raw_text)
            r.used_for = "общая шероховатость"
        elif r.y >= sec.y1 - 1.0:
            part.roughness["top"], r.used_for = r.raw_text, "верхний торец"
        elif r.y <= sec.y0 + 1.0 and (plan is None or r.y > plan.cy + plan.radii[-1]):
            part.roughness["bottom"], r.used_for = r.raw_text, "нижний торец"
        else:
            part.questions.append(
                f"Знак {r.raw_text} в точке ({r.x:g}; {r.y:g}) листа не привязан к поверхности.")


def part_from_dxf(dxf_path: str) -> PartSpec:
    """DXF листа детали → PartSpec. Что не прочитано, уходит в questions, а не подставляется."""
    dr = dxf_geom.load_drawing(dxf_path)
    stamp = dxf_geom.read_stamp(dr.texts)
    part = PartSpec(
        part_id=stamp.designation or "part",
        designation=stamp.designation,
        name=stamp.name,
        material=stamp.material,
        mass_kg=stamp.mass_kg,
        scale=stamp.scale,
        profile="korpus",
        stamp={"dev": stamp.dev, "chk": stamp.chk, "org": stamp.org, "lit": stamp.lit},
        readings=readings_from_texts(dr.texts, stamp.box),
        source_path=str(dxf_path),
    )
    for key, value in (("designation", stamp.designation), ("name", stamp.name),
                       ("material", stamp.material), ("mass_kg", stamp.mass_kg)):
        if value:
            part.provenance[key] = "основная надпись DXF"

    for line in tt_lines(dr.texts, stamp.box):
        m = re.search(r"Тв[её]рдость\s+(.+?)\.?$", line)
        if m:
            part.notes["hardness"] = m.group(1)
        m = re.search(r"радиусы\s+(R[^.]+)", line)
        if m:
            part.notes["radii"] = m.group(1)

    sec = dxf_geom.find_section(dr)
    if sec is None:
        part.questions.append("На листе не найден заштрихованный разрез: размеры профиля снять не с чего.")
        return part
    if sec.asymmetry > 0.02:
        part.warnings.append(f"Разрез несимметричен относительно оси: расхождение {sec.asymmetry:.0%} площади.")
    plan = dxf_geom.find_plan(dr, sec.axis_x)
    snapper = Snapper(part.readings)

    outer, _ = dxf_geom.section_profile(sec)
    measures = [(sec.y1 - sec.y0, "linear")] + [(2 * p[2], "diameter") for p in outer]
    if plan:
        measures += [(2 * r, "diameter") for r in plan.radii]
    k = _choose_scale(stamp, measures, snapper, part)

    dims = _read_section(sec, k, snapper, part)
    if dims:
        part.dimensions.update(dims)
    _read_roughness(sec, plan, part)

    if plan is None:
        part.questions.append("Вид сверху не найден: отверстия и рёбра не прочитаны.")
        return part
    if abs(plan.cx - sec.axis_x) > 0.5:
        part.warnings.append("Центр вида сверху не лежит на оси разреза: проекционной связи нет.")
    if dims:
        on_plan = [2 * r * k for r in plan.radii]
        for name in ("d_bot", "d_top"):
            if not any(abs(v - dims[name]) <= 0.5 for v in on_plan):
                part.warnings.append(
                    f"{DIM_LABELS[name]} {fmt(dims[name])} из разреза не найден среди окружностей вида сверху.")
    _read_holes(plan, k, snapper, part)
    if plan.ribs:
        width, src = snapper.snap(plan.ribs.width * k, "linear", "rib_w")
        part.ribs = Ribs(plan.ribs.n, width, plan.ribs.angle0, round(plan.ribs.r_out * k, 2))
        part.provenance["ribs"] = f"прямоугольники рёбер на виде сверху; ширина: {src}"
    return part


# ---------------------------------------------------------------- проверка

def _half_section(d: Dict[str, float], allow_top: float = 0.0, allow_bot: float = 0.0,
                  allow_bore: float = 0.0) -> Polygon:
    """Правая половина сечения в координатах (r, y) с припусками."""
    t_bot, t_top = d["t_bot_part"] + allow_bot, d["t_top_part"] + allow_top
    h = d["h_part"] + allow_top + allow_bot
    ri_b, ri_t = d["d_bore_bot"] / 2 - allow_bore, d["d_bore_top"] / 2 - allow_bore
    ro_b, ro_t = d["d_bore_bot"] / 2 + d["wall"], d["d_bore_top"] / 2 + d["wall"]
    return Polygon([
        (ri_b, 0), (d["d_bot"] / 2, 0), (d["d_bot"] / 2, t_bot), (ro_b, t_bot),
        (ro_t, h - t_top), (d["d_top"] / 2, h - t_top), (d["d_top"] / 2, h),
        (ri_t, h), (ri_t, h - t_top), (ri_b, t_bot),
    ])


def _revolve(poly: Polygon) -> float:
    return 2 * math.pi * poly.centroid.x * poly.area  # теорема Паппа — Гульдина


def _hole_flange(d: Dict[str, float], hole: HoleGroup) -> Optional[str]:
    """На каком фланце помещается группа отверстий."""
    r, half = hole.pcd / 2, max(hole.d, hole.d_cb or 0.0) / 2
    if d["d_bore_bot"] / 2 + d["wall"] <= r - hole.d / 2 and r + half <= d["d_bot"] / 2:
        return "bottom"
    if d["d_bore_top"] / 2 <= r - hole.d / 2 and r + half <= d["d_top"] / 2:
        return "top"
    return None


def holes_volume(d: Dict[str, float], holes: List[HoleGroup]) -> float:
    total = 0.0
    for hole in holes:
        flange = _hole_flange(d, hole)
        depth = hole.depth or (d["t_bot_part"] if flange == "bottom" else d["t_top_part"])
        v = math.pi / 4 * hole.d ** 2 * depth
        if hole.d_cb and hole.cb_depth:
            v += math.pi / 4 * (hole.d_cb ** 2 - hole.d ** 2) * min(hole.cb_depth, depth)
        total += v * hole.n
    return total


def validate(part: PartSpec) -> Tuple[List[str], List[str]]:
    """(ошибки, предупреждения). С ошибками лист не строится."""
    errors: List[str] = []
    warnings: List[str] = []
    d = part.dimensions
    missing = part.missing_dimensions(REQUIRED_DIMS)
    if missing:
        errors.append("Нет размеров: " + ", ".join(f"{k} ({DIM_LABELS[k]})" for k in missing))
    if not part.designation:
        errors.append("Нет обозначения детали.")
    if not part.material:
        errors.append("Нет материала.")
    elif not part.material[0].upper().startswith("СЧ"):
        warnings.append(f"Материал {part.material[0]}: уклоны, усадка и расчёт литниковой системы заданы для серого чугуна.")
    if not part.name:
        errors.append("Нет наименования детали.")
    if missing:
        return errors, warnings

    for k in REQUIRED_DIMS:
        if d[k] <= 0:
            errors.append(f"{k} ({DIM_LABELS[k]}) должен быть больше нуля, получено {d[k]:g}.")
    if errors:
        return errors, warnings
    if d["t_top_part"] + d["t_bot_part"] >= d["h_part"]:
        errors.append("Сумма толщин фланцев не меньше высоты детали.")
    for bore, flange in (("d_bore_top", "d_top"), ("d_bore_bot", "d_bot")):
        if d[bore] / 2 + d["wall"] > d[flange] / 2 + 1e-9:
            errors.append(f"{DIM_LABELS[flange]} {d[flange]:g} меньше, чем отверстие {d[bore]:g} плюс две стенки.")
    for hole in part.holes:
        if hole.n < 1 or hole.d <= 0 or hole.pcd <= 0:
            errors.append(f"Группа отверстий задана неверно: {hole.as_dict()}")
        elif not errors and _hole_flange(d, hole) is None:
            errors.append(f"{hole.n} отв. ⌀{hole.d:g} на окружности ⌀{hole.pcd:g} не помещаются ни на одном фланце.")
    if part.ribs:
        if part.ribs.n < 2 or part.ribs.width <= 0:
            errors.append("Рёбра заданы неверно: нужно n ≥ 2 и ширина > 0.")
        elif part.ribs.r_out and part.ribs.r_out > max(d["d_bot"], d["d_top"]) / 2 + 1e-9:
            errors.append("Рёбра выходят за наибольший фланец.")
    if errors:
        return errors, warnings

    if part.mass_kg is None:
        errors.append("Нет массы детали (графа «Масса»).")
    elif part.material and part.material[0].upper().startswith("СЧ"):
        geom = (_revolve(_half_section(d)) - holes_volume(d, part.holes)) * GREY_IRON_DENSITY
        if abs(geom - part.mass_kg) > 0.15 * part.mass_kg:
            warnings.append(
                f"Масса по геометрии без рёбер ≈ {geom:.1f} кг, в штампе {part.mass_kg:g} кг. "
                "Расчёт массы отливки опирается на штамп.")
    return errors, warnings


# ---------------------------------------------------------------- PartSpec → отливка

def _machined_note(holes: List[HoleGroup]) -> Optional[str]:
    items = []
    for hole in holes:
        if hole.kind == "thread":
            items.append(hole.label.split("отв.")[-1].strip().split("-")[0] or f"М{fmt(hole.d)}")
        elif hole.kind == "cbore" and hole.d_cb:
            items.append(f"⌀{fmt(hole.d)} с цековкой ⌀{fmt(hole.d_cb)}")
        else:
            items.append(f"⌀{fmt(hole.d)}")
    return f"Отверстия {', '.join(items)} — мехобработкой." if items else None


def build_casting(part: PartSpec, decisions: Dict[str, Decision]) -> CastingDraft:
    """PartSpec + решения → параметры листа отливки."""
    errors, _ = validate(part)
    if errors:
        raise ValueError("PartSpec не годится для отливки: " + " ".join(errors))
    d = part.dimensions
    val = {k: v.value for k, v in decisions.items()}
    warnings: List[str] = []

    allow_top = float(val["allow_top"]) if val["machined_top"] else 0.0
    allow_bot = float(val["allow_bottom"]) if val["machined_bottom"] else 0.0
    allow_bore = float(val["allow_bore"]) if val["machined_bore"] else 0.0
    if d["d_bore_top"] - 2 * allow_bore <= 0:
        raise ValueError("Припуск на отверстие больше его радиуса.")

    v_allow = _revolve(_half_section(d, allow_top, allow_bot, allow_bore)) - _revolve(_half_section(d))
    v_holes = holes_volume(d, part.holes)
    mass_part = float(part.mass_kg)
    mass_calc = mass_part + (v_allow + v_holes) * GREY_IRON_DENSITY
    if val.get("mass_cast_kg") is None:
        mass_cast = round(mass_calc, 1)
        mass_src = (f"масса детали {fmt(mass_part, 2)} кг + припуски {v_allow * GREY_IRON_DENSITY:.2f} кг "
                    f"+ незалитые отверстия {v_holes * GREY_IRON_DENSITY:.2f} кг")
    else:
        mass_cast = float(val["mass_cast_kg"])
        mass_src = decisions["mass_cast_kg"].source
        if abs(mass_cast - mass_calc) > 0.05 * mass_calc:
            warnings.append(f"Заданная масса отливки {mass_cast:g} кг расходится с расчётом {mass_calc:.1f} кг.")

    g = val["gating"]
    tau = round(g["tau_coeff"] * math.sqrt(mass_cast), 1)
    sigma_fp = round(mass_cast / (g["rho_liquid"] * g["mu"] * tau * math.sqrt(2 * 9.81 * g["h_met_m"])) * 1e4, 2)
    f_slag, f_sprue = round(sigma_fp * 1.1, 2), round(sigma_fp * 1.2, 2)

    ribs = part.ribs
    r_big = max(d["d_bot"], d["d_top"]) / 2
    params: Dict[str, Any] = {
        "NAME": list(part.name),
        "MATERIAL": list(part.material),
        "DESIGNATION_00": part.designation,
        "DESIGNATION_01": val["designation_casting"],
        "MASS_PART": mass_part,
        "MASS_CAST": mass_cast,
        "MASS_STR": ("%.1f" % mass_cast).replace(".", ","),
        "DEV": val["dev"], "CHK": val["chk"], "ORG": list(val["org"]), "LIT": val["lit"],
        # деталь
        "H_PART": d["h_part"], "T_TOP_PART": d["t_top_part"], "T_BOT_PART": d["t_bot_part"],
        "D_TOP": d["d_top"], "D_BOT": d["d_bot"],
        "D_BORE_TOP": d["d_bore_top"], "D_BORE_BOT": d["d_bore_bot"], "WALL": d["wall"],
        "R_IN_TOP": d["d_bore_top"] / 2, "R_IN_BOT": d["d_bore_bot"] / 2,
        "R_OUT_TOP": d["d_bore_top"] / 2 + d["wall"], "R_OUT_BOT": d["d_bore_bot"] / 2 + d["wall"],
        "N_RIBS": ribs.n if ribs else 0,
        "RIB_W": ribs.width if ribs else 0.0,
        "RIB_ANGLE0": float(val["rib_angle0"]) if ribs else 0.0,
        "RIB_R_OUT": (ribs.r_out or r_big - 6.0) if ribs else 0.0,
        "HOLE_GROUPS": [[h.pcd, h.n, h.angle0] for h in part.holes],
        # отливка
        "ALLOW_TOP": allow_top, "ALLOW_BOT": allow_bot, "ALLOW_BORE": allow_bore,
        "H_CAST": d["h_part"] + allow_top + allow_bot,
        "T_TOP_CAST": d["t_top_part"] + allow_top, "T_BOT_CAST": d["t_bot_part"] + allow_bot,
        "D_BORE_TOP_CAST": d["d_bore_top"] - 2 * allow_bore,
        "D_BORE_BOT_CAST": d["d_bore_bot"] - 2 * allow_bore,
        "R_IN_TOP_CAST": d["d_bore_top"] / 2 - allow_bore, "R_IN_BOT_CAST": d["d_bore_bot"] / 2 - allow_bore,
        "DRAFT_EXT": float(val["draft_ext"]), "DRAFT_INT": float(val["draft_int"]),
        "SHRINKAGE": float(val["shrinkage"]), "R_FILLET": float(val["r_fillet"]),
        "ACCURACY": val["accuracy"], "RA_FACES": val["ra_faces"], "RA_GENERAL": val["ra_general"],
        "HARDNESS": val["hardness"], "HEAT_TREATMENT": val["heat_treatment"],
        "MACHINED_NOTE": _machined_note(part.holes),
        # литниковая система
        "G_CAST": mass_cast, "TAU_FILL": tau, "SIGMA_FP": sigma_fp, "F_SLAG": f_slag, "F_SPRUE": f_sprue,
        "N_FEEDERS": g["n_feeders"], "F_ONE_FEED": round(sigma_fp / g["n_feeders"], 2),
    }
    provenance = {k: v.source for k, v in decisions.items()}
    provenance["mass_cast_kg"] = mass_src
    provenance["geometry"] = "PartSpec.dimensions, см. PartSpec.provenance"
    return CastingDraft(
        profile="korpus",
        designation=val["designation_casting"],
        params=params,
        provenance=provenance,
        warnings=warnings,
        questions=list(part.questions),
    )
