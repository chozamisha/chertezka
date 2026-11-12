# -*- coding: utf-8 -*-
"""
Сборка foundry-геометрии колеса: металл+лопатки+прибыль, стержни, ЛС, холодильники.

Все тела — декларации для ocp_worker (реальный OCP). P1 не меняется.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from ..spec.casting_spec import CastingSpec
from .solids import casting_axisymmetric_profile, solid_revolve_profile
from .tech_params import TechGeomParams, wheel_tech_geom


def _metal_with_blades_and_riser(spec: CastingSpec, tech: TechGeomParams) -> Dict[str, Any]:
    """Осесимметрия → вырез канала → fuse лопаток → прибыль с шейкой/галтелью.

    Меридиональный профиль P2 заливает канал; для P3 полость канала
    вырезается annulus (реальный OCP Cut), затем вплавляются лопатки.
    """
    tech.require("blades")
    tech.require("riser")
    b = tech.blades
    r = tech.riser
    assert b is not None and r is not None

    profile = casting_axisymmetric_profile(spec)
    base = solid_revolve_profile(profile, add_cylinders=[], sub_cylinders=[])

    # полость канала: от ~ступицы до внутренней поверхности обода
    channel_d_out = 2.0 * b.r_outer_mm - 0.2
    channel_d_in = 2.0 * max(b.r_inner_mm - 1.0, spec.c_bore / 2.0 + 1.0)

    parts: List[Dict[str, Any]] = [
        {"name": "body", "solid": base, "op": "fuse"},
        {
            "name": "channel_void",
            "op": "cut",
            "solid": {
                "kind": "annulus",
                "d_out": channel_d_out,
                "d_in": channel_d_in,
                "h": float(spec.c_h_ch),
                "z0": float(spec.y_disk_lo_top),
            },
        },
    ]
    step = 360.0 / b.count
    for i in range(b.count):
        ang = b.start_angle_deg + i * step
        parts.append(
            {
                "name": f"blade_{i}",
                "op": "fuse",
                "solid": {
                    "kind": "radial_blade",
                    "r_inner": b.r_inner_mm,
                    "r_outer": b.r_outer_mm,
                    "thickness": b.thickness_mm,
                    "z0": b.z0_mm,
                    "height": b.height_mm,
                    "angle_deg": ang,
                },
            }
        )
    parts.append(
        {
            "name": "riser",
            "op": "fuse",
            "solid": {
                "kind": "riser_neck_fillet",
                "d_neck": r.d_neck_mm,
                "d_riser": r.d_riser_mm,
                "h_neck": r.h_neck_mm,
                "h_riser": r.h_riser_mm,
                "z0": r.z_seat_mm,
                "fillet_r": r.fillet_r_mm,
            },
        }
    )
    return {
        "kind": "assembly",
        "parts": parts,
        "meta": {
            "blades": b.count,
            "blade_hydraulic_profile": b.is_hydraulic_profile,
            "blade_provenance": b.provenance,
            "riser_provenance": r.provenance,
            "channel_cut": True,
        },
    }


def _core1_solid(tech: TechGeomParams) -> Dict[str, Any]:
    tech.require("core1")
    tech.require("blades")
    c = tech.core1
    b = tech.blades
    assert c is not None and b is not None
    # кольцо канала (до внутр. обода) минус лопатки
    parts: List[Dict[str, Any]] = [
        {
            "name": "channel",
            "op": "fuse",
            "solid": {
                "kind": "annulus",
                "d_out": 2.0 * c.r_outer_mm,
                "d_in": 2.0 * c.r_inner_mm,
                "h": c.height_mm,
                "z0": c.z0_mm,
            },
        }
    ]
    step = 360.0 / b.count
    for i in range(b.count):
        ang = b.start_angle_deg + i * step
        parts.append(
            {
                "name": f"cut_blade_{i}",
                "op": "cut",
                "solid": {
                    "kind": "radial_blade",
                    "r_inner": b.r_inner_mm,
                    "r_outer": c.r_outer_mm - 0.5,
                    "thickness": b.thickness_mm + 0.4,
                    "z0": c.z0_mm - 0.2,
                    "height": c.height_mm + 0.4,
                    "angle_deg": ang,
                },
            }
        )
    # знаки — от наружного ⌀ отливки (OD) наружу; OD передаётся в meta/печати через length от casting
    # r_print0 = длина от оси: берём r_outer канала + rim → фактически casting OD = print corner x
    # caller кладёт OD в prints через assembly: используем r_outer_mm + (типичный wall) из length start
    # Здесь: уголной box начинается на OD = r_outer + wall_estimate; wall = передадим через print
    # Для колеса OD известен как r_outer_blade + rim_wall; восстановим: prints стартуют на OD из поля
    # `print_attach_r` если задан в meta prints — иначе r_outer + 25.
    attach_r = float(c.prints.attach_r_mm) if c.prints.attach_r_mm > 0 else (c.r_outer_mm + 25.0)
    for ang in c.prints.angles_deg:
        parts.append(
            {
                "name": f"print_{ang}",
                "op": "fuse",
                "solid": {
                    "kind": "box",
                    "corner": [
                        attach_r,
                        -c.prints.width_mm / 2.0,
                        c.z0_mm,
                    ],
                    "size": [
                        c.prints.length_mm,
                        c.prints.width_mm,
                        c.prints.height_mm,
                    ],
                    "rot_z_deg": float(ang),
                },
            }
        )
    return {
        "kind": "assembly",
        "parts": parts,
        "meta": {"provenance": c.provenance, "print_attach_r": attach_r},
    }


def _core2_solid(tech: TechGeomParams) -> Dict[str, Any]:
    tech.require("core2")
    c = tech.core2
    assert c is not None
    # цилиндр отверстия + нижний знак (цилиндр того же ⌀ вниз на print_h)
    return {
        "kind": "assembly",
        "parts": [
            {
                "name": "bore",
                "op": "fuse",
                "solid": {
                    "kind": "cylinder",
                    "d": c.diameter_mm,
                    "h": c.height_mm,
                    "z0": c.z0_mm,
                },
            },
            {
                "name": "print_bot",
                "op": "fuse",
                "solid": {
                    "kind": "cylinder",
                    "d": c.diameter_mm,
                    "h": c.print_h_mm,
                    "z0": c.z0_mm - c.print_h_mm,
                },
            },
        ],
        "meta": {"provenance": c.provenance},
    }


def _gating_solid(spec: CastingSpec, tech: TechGeomParams) -> Dict[str, Any]:
    tech.require("gating")
    g = tech.gating
    assert g is not None
    # площади см² → мм²
    f_sprue = g.f_sprue_cm2 * 100.0
    f_slag = g.f_slag_cm2 * 100.0
    f_pit = g.f_pit_cm2 * 100.0
    r_sprue = math.sqrt(f_sprue / math.pi)
    # шлаковик: прямоугольник высота slag_height, ширина = F/h
    slag_w = f_slag / g.slag_height_mm
    pit_area = f_pit / max(g.n_pit, 1)
    pit_h = g.slag_height_mm
    pit_w = pit_area / pit_h

    ro = spec.c_out / 2.0
    # стояк слева: центр (-sprue_offset, 0), от z_mf-50 вверх
    sx = -g.sprue_offset_mm
    z0 = g.z_mf_mm - 50.0
    h_sprue = 100.0
    parts: List[Dict[str, Any]] = [
        {
            "name": "sprue",
            "op": "fuse",
            "solid": {
                "kind": "cylinder",
                "d": 2.0 * r_sprue,
                "h": h_sprue,
                "z0": z0,
                "x0": sx,
                "y0": 0.0,
            },
        },
        {
            "name": "slag",
            "op": "fuse",
            "solid": {
                "kind": "box",
                # не пересекать гориз. знак Ст.1 на −X (OD−L_PRINT…OD):
                # шлаковик заканчивается за кончиком знака
                "corner": [sx, -slag_w / 2.0, g.z_mf_mm - g.slag_height_mm / 2.0],
                "size": [
                    (-ro - float(spec.l_print) - 5.0) - sx,
                    slag_w,
                    g.slag_height_mm,
                ],
                "rot_z_deg": 0.0,
            },
        },
    ]
    # питатели сверху/снизу к ободу
    ys = []
    if g.n_pit == 1:
        ys = [0.0]
    elif g.n_pit >= 2:
        ys = [-100.0, 100.0][: g.n_pit]
    for i, yy in enumerate(ys):
        parts.append(
            {
                "name": f"pit_{i}",
                "op": "fuse",
                "solid": {
                    "kind": "box",
                    "corner": [
                        -ro - g.pit_length_mm,
                        yy - pit_w / 2.0,
                        g.z_mf_mm - pit_h / 2.0,
                    ],
                    "size": [g.pit_length_mm + 8.0, pit_w, pit_h],
                    "rot_z_deg": 0.0,
                },
            }
        )
    return {
        "kind": "assembly",
        "parts": parts,
        "meta": {
            "provenance": g.provenance,
            "r_sprue_mm": r_sprue,
            "slag_w_mm": slag_w,
            "pit_w_mm": pit_w,
            "areas_mm2": {"sprue": f_sprue, "slag": f_slag, "pit_sum": f_pit},
        },
    }


def _chill_solids(tech: TechGeomParams) -> List[Tuple[str, Dict[str, Any]]]:
    out: List[Tuple[str, Dict[str, Any]]] = []
    for ch in tech.chills:
        for ang in ch.center_angles_deg:
            # радиальный брусок a×a×height у r_inner
            name = f"{ch.name}_{ang:g}"
            out.append(
                (
                    name,
                    {
                        "kind": "box",
                        "corner": [ch.r_inner_mm, -ch.a_mm / 2.0, ch.z0_mm],
                        "size": [ch.a_mm, ch.a_mm, ch.height_mm],
                        "rot_z_deg": float(ang),
                    },
                )
            )
    return out


def build_wheel_foundry_solids(
    spec: CastingSpec, tech: TechGeomParams | None = None
) -> Dict[str, Dict[str, Any]]:
    """Именованные тела для видов и QA."""
    tech = tech or wheel_tech_geom(spec)
    solids: Dict[str, Dict[str, Any]] = {
        "metal": _metal_with_blades_and_riser(spec, tech),
        "core1": _core1_solid(tech),
        "core2": _core2_solid(tech),
        "gating": _gating_solid(spec, tech),
    }
    for name, decl in _chill_solids(tech):
        solids[name] = decl
    return solids


def metal_plus_tech_for_views(
    spec: CastingSpec, tech: TechGeomParams | None = None
) -> Dict[str, Any]:
    """Одно тело для HLR/сечений: металл+лопатки+прибыль (+ опц. знаки не включаем — отдельно)."""
    tech = tech or wheel_tech_geom(spec)
    return _metal_with_blades_and_riser(spec, tech)


def intersection_job(spec: CastingSpec, tech: TechGeomParams | None = None) -> Dict[str, Any]:
    tech = tech or wheel_tech_geom(spec)
    solids_map = build_wheel_foundry_solids(spec, tech)
    solids_list = [{"name": n, "solid": d} for n, d in solids_map.items()]
    pairs = [
        # стержни не должны сильно пересекать металл (полости)
        {"a": "metal", "b": "core1", "expect": "disjoint", "tol_volume": 5.0e4},
        {"a": "metal", "b": "core2", "expect": "disjoint", "tol_volume": 1.0e4},
        # питатели/шлак могут касаться обода — допускаем небольшой overlap
        {"a": "gating", "b": "core1", "expect": "disjoint", "tol_volume": 2.0e4},
    ]
    # холодильники — overlap с металлом ожидаем небольший (контакт)
    for n in solids_map:
        if n.startswith("Хол"):
            pairs.append(
                {"a": "metal", "b": n, "expect": "overlap", "tol_volume": 100.0}
            )
    return {
        "operation": "intersection_check",
        "name": "wheel_tech_intersections",
        "solids": solids_list,
        "pairs": pairs,
    }


def local_bb_print_section_job(
    spec: CastingSpec, tech: TechGeomParams | None = None
) -> Dict[str, Any]:
    """Местное сечение Б-Б: только знак Ст.1 при 0° (OCP Section), без всего диаметра."""
    tech = tech or wheel_tech_geom(spec)
    tech.require("core1")
    c = tech.core1
    assert c is not None
    attach = float(c.prints.attach_r_mm) if c.prints.attach_r_mm > 0 else c.r_outer_mm + 25.0
    # тело знака + тонкий фрагмент обода у OD для контекста
    solid = {
        "kind": "assembly",
        "parts": [
            {
                "name": "print0",
                "op": "fuse",
                "solid": {
                    "kind": "box",
                    "corner": [
                        attach,
                        -c.prints.width_mm / 2.0,
                        c.z0_mm,
                    ],
                    "size": [
                        c.prints.length_mm,
                        c.prints.width_mm,
                        c.prints.height_mm,
                    ],
                    "rot_z_deg": 0.0,
                },
            },
            {
                "name": "rim_bit",
                "op": "fuse",
                "solid": {
                    "kind": "box",
                    "corner": [
                        attach - float(spec.rim_wall),
                        -c.prints.width_mm / 2.0,
                        c.z0_mm,
                    ],
                    "size": [
                        float(spec.rim_wall),
                        c.prints.width_mm,
                        c.prints.height_mm,
                    ],
                    "rot_z_deg": 0.0,
                },
            },
        ],
    }
    return {
        "solid": solid,
        "operation": "plane_section",
        "name": "B-B_print",
        "origin": [0.0, 0.0, 0.0],
        "normal": [0.0, 1.0, 0.0],
        "u_dir": [1.0, 0.0, 0.0],
        "v_dir": [0.0, 0.0, 1.0],
        "deflection": 0.35,
        "axes_2d": [],
    }
