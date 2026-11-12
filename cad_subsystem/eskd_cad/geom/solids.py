# -*- coding: utf-8 -*-
"""
Декларативные тела для OCP worker.

Форма задаётся параметрами / CastingSpec — без дублирования P1-расчётов.
Тела различной формы: box_with_bore, flange, revolve_profile (осесимметрия).
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from ..spec.casting_spec import CastingSpec

Point2 = Tuple[float, float]


def solid_box_with_bore(
    size: Tuple[float, float, float] = (80.0, 80.0, 30.0),
    bore_d: float = 24.0,
    center: Tuple[float, float, float] | None = None,
) -> Dict[str, Any]:
    sx, sy, sz = size
    return {
        "kind": "box_with_bore",
        "size": [sx, sy, sz],
        "bore_d": float(bore_d),
        "center": list(center) if center else [0.0, 0.0, sz / 2.0],
    }


def solid_flange(
    od: float,
    id_: float,
    thickness: float,
    hub_od: float = 0.0,
    hub_h: float = 0.0,
) -> Dict[str, Any]:
    return {
        "kind": "flange",
        "od": float(od),
        "id": float(id_),
        "thickness": float(thickness),
        "hub_od": float(hub_od),
        "hub_h": float(hub_h),
    }


def solid_revolve_profile(
    profile_xz: Sequence[Point2],
    *,
    add_cylinders: Sequence[Dict[str, float]] | None = None,
    sub_cylinders: Sequence[Dict[str, float]] | None = None,
) -> Dict[str, Any]:
    return {
        "kind": "revolve_profile",
        "profile_xz": [[float(x), float(z)] for x, z in profile_xz],
        "add_cylinders": [dict(c) for c in (add_cylinders or ())],
        "sub_cylinders": [dict(c) for c in (sub_cylinders or ())],
    }


def _close_profile(pts: List[Point2]) -> List[Point2]:
    if not pts:
        return pts
    if abs(pts[0][0] - pts[-1][0]) > 1e-9 or abs(pts[0][1] - pts[-1][1]) > 1e-9:
        return pts + [pts[0]]
    return pts


def casting_axisymmetric_profile(spec: CastingSpec) -> List[Point2]:
    """Правый меридианный контур металла отливки в плоскости XZ (x≥0).

    Совпадает по формулам с половиной `_metal_section_polys` (foundry),
    но строится из CastingSpec — без копирования чисел вручную.
    Ось отливки = Z; низ = z=0.
    """
    rh = spec.c_hub / 2.0
    rb = spec.c_bore / 2.0
    rbo = spec.c_bore_lo / 2.0
    rbs = spec.c_boss / 2.0
    ro = spec.c_out / 2.0
    wall = float(spec.rim_wall)
    y0 = spec.y_bot
    y1 = spec.y_disk_lo_top
    y2 = spec.y_disk_up_bot
    y3 = spec.y_disk_up_top
    y4 = spec.y_hub_top
    step = float(spec.bore_step_y)

    # Контур CCW вокруг металла (для face → revolve)
    pts: List[Point2] = [
        (rb, y4),
        (rh, y4),
        (rh, y3),
        (ro, y3),
        (ro, y2),
        (ro - wall, y2),
        (ro - wall, y1),
        (ro, y1),
        (ro, y0),
        (rbs, y0),
        (rbs, y1),
        (rbo, y1),
        (rbo, y0 + step),
        (rb, y0 + step),
        (rb, y4),
    ]
    return _close_profile(pts)


def solid_from_casting_spec(spec: CastingSpec, *, include_riser: bool = True) -> Dict[str, Any]:
    """Осесимметричное тело отливки (+ опционально цилиндр прибыли).

    Лопатки канала, знаки стержней и ЛС в тело не входят (см. P2_GEOMETRY.md).
    """
    profile = casting_axisymmetric_profile(spec)
    adds = []
    if include_riser:
        # шейка + тело прибыли упрощённо одним цилиндром D_RISER от Y_HUB_TOP
        adds.append(
            {
                "d": float(spec.d_riser),
                "h": float(spec.h_riser),
                "z0": float(spec.y_hub_top),
            }
        )
    # отверстие ступицы уже в профиле (внутренний радиус rb);
    # доп. вычитаний не требуется для осесимметрии
    return solid_revolve_profile(profile, add_cylinders=adds)
