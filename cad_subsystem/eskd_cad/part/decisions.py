# -*- coding: utf-8 -*-
"""Технологические решения по отливке: значение, откуда взято, подтверждено ли.

Всё, чего нет на исходном чертеже детали (припуски, уклоны, класс точности,
масса отливки), попадает сюда явно. Пока хотя бы одно решение не подтверждено,
лист выпускается только как черновик.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .part_spec import PartSpec

KIT = "эталонный комплект «Корпус» в репозитории, не исходный чертёж"
RULE = "правило .cursor/rules/eskd.mdc"
SOURCE = "исходный чертёж детали"
ENGINEER = "задано в файле решений"


@dataclass
class Decision:
    value: Any
    source: str
    confirmed: bool = False
    note: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _casting_designation(code: str) -> Decision:
    if code.endswith("-00"):
        return Decision(code[:-3] + "-01", f"{RULE}: деталь -00, отливка -01", True)
    return Decision(f"{code}-01" if code else "", "суффикс -01 к обозначению детали", False,
                    "обозначение детали не оканчивается на -00")


def default_decisions(part: PartSpec) -> Dict[str, Decision]:
    """Решения по умолчанию для профиля korpus. Неподтверждённые требуют ответа инженера."""
    d = part.dimensions
    rough, stamp = part.roughness, part.stamp
    out: Dict[str, Decision] = {}

    out["designation_casting"] = _casting_designation(part.designation)
    out["mold_position"] = Decision(
        "верхний фланец вверху формы, разъём по плоскости нижнего фланца", KIT, False,
        "от положения в форме зависит, какой торец получает больший припуск")

    for key, face, label in (("machined_top", "top", "верхний торец"), ("machined_bottom", "bottom", "нижний торец")):
        if rough.get(face):
            out[key] = Decision(True, f"{SOURCE}: знак {rough[face]} на поверхности «{label}»", True)
        else:
            out[key] = Decision(True, KIT, False, f"знак шероховатости на поверхности «{label}» не найден")
    if rough.get("bore"):
        out["machined_bore"] = Decision(True, f"{SOURCE}: знак {rough['bore']} на отверстии", True)
    else:
        out["machined_bore"] = Decision(True, KIT, False,
                                        "на исходном чертеже знака на центральном отверстии нет")

    gost = "ГОСТ 26645-85; таблиц допусков в репозитории нет, значение взято из эталонного комплекта"
    out["allow_top"] = Decision(4.0, gost, False, "мм, верхний торец")
    out["allow_bottom"] = Decision(3.0, gost, False, "мм, нижний торец")
    out["allow_bore"] = Decision(2.0, gost, False, "мм на сторону, центральное отверстие")
    out["accuracy"] = Decision("9-7-12-9", gost, False, "класс точности отливки для ТТ")
    out["draft_ext"] = Decision(1.5, f"ГОСТ 3212-92; {KIT}", False, "градусы, наружные поверхности")
    out["draft_int"] = Decision(2.0, f"ГОСТ 3212-92; {KIT}", False, "градусы, внутренние поверхности")
    out["shrinkage"] = Decision(1.0, f"{RULE}: усадка 1 %", True)
    out["r_fillet"] = Decision(5.0, KIT, False,
                               "мм; в ТТ детали: " + part.notes["radii"] if part.notes.get("radii") else "мм")

    faces = rough.get("top") or rough.get("bottom")
    out["ra_faces"] = (Decision(faces, f"{SOURCE}: знак на торце", True) if faces
                       else Decision("Ra 6,3", KIT, False))
    out["ra_general"] = (Decision(rough["general"], f"{SOURCE}: знак в правом верхнем углу", True)
                         if rough.get("general") else Decision("Ra 12,5", KIT, False))
    out["hardness"] = (Decision(part.notes["hardness"], f"{SOURCE}: технические требования", True)
                       if part.notes.get("hardness") else Decision(None, "на исходном чертеже не указана", True))
    out["heat_treatment"] = Decision("отжиг 500…550 °С", KIT, False, "пункт ТТ; null, если не нужен")

    out["mass_cast_kg"] = Decision(None, f"{RULE}: масса детали плюс припуски", False,
                                   "null: считать как масса детали из штампа + припуски и напуски по геометрии")

    if part.ribs:
        step = 360.0 / part.ribs.n
        a0 = part.ribs.angle0 % step
        in_plane = min(a0, step - a0) < 1.0 or any(
            abs((ang - a0 + step / 2) % step - step / 2) < 1.0 for ang in (0.0, 180.0))
        if in_plane:
            out["rib_angle0"] = Decision(
                step / 2, f"{RULE}: рёбра не в секущей плоскости А-А", False,
                f"на исходном чертеже рёбра показаны под {a0:g}°, то есть в плоскости разреза")
        else:
            out["rib_angle0"] = Decision(a0, SOURCE, True)

    for key, label in (("dev", "Разраб."), ("chk", "Пров."), ("lit", "Лит.")):
        if stamp.get(key):
            out[key] = Decision(stamp[key], f"{SOURCE}: графа «{label}»", True)
        else:
            out[key] = Decision("", f"графа «{label}» не прочитана", False)
    if stamp.get("org"):
        out["org"] = Decision(list(stamp["org"]), f"{SOURCE}: графа организации", True)
    else:
        out["org"] = Decision([], "графа организации не прочитана", False)

    out["gating"] = Decision(
        {"tau_coeff": 1.8, "h_met_m": 0.18, "mu": 0.4, "rho_liquid": 6900.0, "n_feeders": 2},
        f"{RULE}: ΣFп:Fшл:Fст = 1:1,1:1,2; коэффициенты из расчёта эталонного комплекта", False,
        "τ = k·√G, ΣFп = G / (ρ·μ·τ·√(2gH))")
    return out


def load_overrides(path: str | Path) -> Dict[str, Decision]:
    """Файл решений: {"allow_top": 4} или {"allow_top": {"value": 4, "confirmed": true, …}}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: Dict[str, Decision] = {}
    for key, item in data.items():
        if isinstance(item, dict) and "value" in item and set(item) <= {"value", "source", "confirmed", "note"}:
            out[key] = Decision(item["value"], item.get("source", ENGINEER),
                                bool(item.get("confirmed", False)), item.get("note", ""))
        else:
            out[key] = Decision(item, ENGINEER, True)
    return out


def resolve(part: PartSpec, overrides: Optional[Dict[str, Decision]] = None,
            confirm_all: bool = False) -> Dict[str, Decision]:
    out = default_decisions(part)
    unknown = sorted(set(overrides or {}) - set(out))
    if unknown:
        raise ValueError("Неизвестные решения: " + ", ".join(unknown))
    out.update(overrides or {})
    if confirm_all:
        for dec in out.values():
            if not dec.confirmed:
                dec.confirmed = True
                dec.source += "; подтверждено инженером"
    return out


def unconfirmed(decisions: Dict[str, Decision]) -> List[str]:
    return [k for k, v in decisions.items() if not v.confirmed]


def dump(decisions: Dict[str, Decision]) -> Dict[str, Any]:
    return {k: v.as_dict() for k, v in decisions.items()}
