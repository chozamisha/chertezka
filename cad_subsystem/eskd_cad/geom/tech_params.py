# -*- coding: utf-8 -*-
"""
Параметры технологической геометрии (P3) — отдельно от P1-расчётов.

Числа либо из CastingSpec / листа расчёта, либо явно engineer с provenance.
Не дублирует формулы припусков/ЛС-соотношений.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..spec.casting_spec import CastingSpec


class MissingTechDataError(ValueError):
    """Недостаточно параметров для реальной (не условной) геометрии элемента."""


@dataclass(frozen=True)
class BladeParams:
    """Призматические радиальные лопатки в канале (не профиль по шаблону)."""

    count: int
    thickness_mm: float
    r_inner_mm: float
    r_outer_mm: float
    z0_mm: float
    height_mm: float
    start_angle_deg: float = 0.0
    provenance: str = ""
    # True только если задан реальный гидравлический профиль (полилиния) — в P3 нет
    is_hydraulic_profile: bool = False


@dataclass(frozen=True)
class CorePrintHoriz:
    """Горизонтальный знак стержня на ободе."""

    length_mm: float
    width_mm: float
    height_mm: float
    angles_deg: Tuple[float, ...]
    attach_r_mm: float = 0.0  # радиус крепления знака (обычно OD отливки)
    provenance: str = ""


@dataclass(frozen=True)
class Core1Params:
    """Ст.1 — канал между дисками (+ знаки)."""

    r_inner_mm: float
    r_outer_mm: float
    z0_mm: float
    height_mm: float
    prints: CorePrintHoriz
    provenance: str = ""


@dataclass(frozen=True)
class Core2Params:
    """Ст.2 — отверстие ступицы + нижний вертикальный знак."""

    diameter_mm: float
    z0_mm: float
    height_mm: float
    print_h_mm: float
    provenance: str = ""


@dataclass(frozen=True)
class GatingParams:
    """ЛС из площадей P1 (см²) → сечения каналов."""

    f_pit_cm2: float
    f_slag_cm2: float
    f_sprue_cm2: float
    n_pit: int
    # положение на плане (мм модели): стояк слева от обода
    sprue_offset_mm: float
    slag_height_mm: float  # высота прямоугольного шлаковика
    pit_length_mm: float
    z_mf_mm: float  # плоскость разъёма
    provenance: str = ""


@dataclass(frozen=True)
class RiserGeomParams:
    d_riser_mm: float
    d_neck_mm: float
    h_riser_mm: float
    h_neck_mm: float
    fillet_r_mm: float
    z_seat_mm: float
    provenance: str = ""


@dataclass(frozen=True)
class ChillParams:
    name: str
    a_mm: float  # поперечный размер из calc
    arc_deg: float
    # положение: цилиндрическая оболочка у поверхности
    r_inner_mm: float
    z0_mm: float
    height_mm: float
    center_angles_deg: Tuple[float, ...]
    provenance: str = ""


@dataclass(frozen=True)
class TechGeomParams:
    """Полный пакет техгеометрии для сборки foundry."""

    blades: Optional[BladeParams]
    core1: Optional[Core1Params]
    core2: Optional[Core2Params]
    gating: Optional[GatingParams]
    riser: Optional[RiserGeomParams]
    chills: Tuple[ChillParams, ...] = ()
    notes: Tuple[str, ...] = ()

    def require(self, name: str) -> None:
        if getattr(self, name) is None:
            raise MissingTechDataError(
                f"TechGeomParams.{name} отсутствует — нельзя строить реальную геометрию этого элемента"
            )


def wheel_tech_geom(spec: CastingSpec) -> TechGeomParams:
    """Пакет для КП-062215009-01 из CastingSpec + явные engineer-параметры листа.

    Лопатки: призмы (не шаблон). Толщина — engineer (в calc нет).
    """
    notes: List[str] = []
    # --- blades ---
    # Недостаёт: профиль по шаблону. Строим радиальные пластины.
    blade_t = 14.0  # мм, engineer geometric model
    notes.append(
        "Лопатки: нет полилинии шаблона в calc — OCP-призмы thickness=14 мм (engineer), "
        "не гидравлический профиль."
    )
    r_in = spec.c_hub / 2.0 + 2.0
    r_out = spec.c_out / 2.0 - float(spec.rim_wall)
    if r_out <= r_in:
        raise MissingTechDataError("r_outer лопатки ≤ r_inner — проверьте C_HUB/C_OUT/rim_wall")
    blades = BladeParams(
        count=4,
        thickness_mm=blade_t,
        r_inner_mm=r_in,
        r_outer_mm=r_out,
        z0_mm=float(spec.y_disk_lo_top),
        height_mm=float(spec.c_h_ch),
        start_angle_deg=15.0,
        provenance="TT: 4 шт.; height=C_H_CH; thickness=engineer 14 мм (шаблон отсутствует)",
        is_hydraulic_profile=False,
    )

    # --- core 1: fills channel annulus (metal blades occupy slots) ---
    print_w = 50.0  # как на legacy чертеже
    notes.append("Ширина знака Ст.1 = 50 мм — с legacy-чертежа / практика, не из табл. ГОСТ напрямую.")
    # Канал (полость) до внутренней поверхности обода; знаки крепятся с OD наружу.
    core1 = Core1Params(
        r_inner_mm=r_in,
        r_outer_mm=r_out,  # = C_OUT/2 - rim_wall — не пересекать металл обода
        z0_mm=float(spec.y_disk_lo_top),
        height_mm=float(spec.c_h_ch),
        prints=CorePrintHoriz(
            length_mm=float(spec.l_print),
            width_mm=print_w,
            height_mm=float(spec.c_h_ch),
            angles_deg=(0.0, 180.0),
            attach_r_mm=float(spec.c_out) / 2.0,
            provenance="L_PRINT из CastingSpec; width=50 engineer/drawing; attach=OD",
        ),
        provenance="канал до внутр. обода + знаки от OD (calc §4)",
    )

    core2 = Core2Params(
        diameter_mm=float(spec.c_bore),
        z0_mm=0.0,
        height_mm=float(spec.h_body),
        print_h_mm=float(spec.h_print2),
        provenance="C_BORE + H_PRINT2 CastingSpec; схема A",
    )

    z_mf = (spec.y_disk_lo_top + spec.y_disk_up_bot) / 2.0
    gating = GatingParams(
        f_pit_cm2=float(spec.f_pit),
        f_slag_cm2=float(spec.f_slag),
        f_sprue_cm2=float(spec.f_sprue),
        n_pit=int(spec.n_pit),
        sprue_offset_mm=spec.c_out / 2.0 + 130.0,
        slag_height_mm=32.0,
        pit_length_mm=40.0,
        z_mf_mm=z_mf,
        provenance="площади из P1 CastingSpec; высота шлаковика/длина питателя — engineer layout",
    )

    riser = RiserGeomParams(
        d_riser_mm=float(spec.d_riser),
        d_neck_mm=float(spec.d_neck),
        h_riser_mm=float(spec.h_riser),
        h_neck_mm=28.0,
        fillet_r_mm=8.0,
        z_seat_mm=float(spec.y_hub_top),
        provenance="D/H из CastingSpec; h_neck=28, fillet_r=8 — как legacy-чертёж / практика",
    )

    rh = spec.c_hub / 2.0
    chill1 = ChillParams(
        name="Хол.1",
        a_mm=40.0,
        arc_deg=90.0,
        r_inner_mm=rh + 3.0,
        z0_mm=float(spec.y_disk_up_top) - 8.0,
        height_mm=40.0,
        center_angles_deg=(0.0,),
        provenance="calc §2: a=40, дуга~90° у стыка ступица–диск",
    )
    chill2 = ChillParams(
        name="Хол.2",
        a_mm=30.0,
        arc_deg=40.0,
        r_inner_mm=spec.c_out / 2.0 - 8.0 - 30.0,
        z0_mm=float(spec.y_disk_lo_top),
        height_mm=float(spec.c_h_ch),
        center_angles_deg=(90.0, 270.0),
        provenance="calc §2: a=30, 2 шт. симм. на ободе",
    )

    return TechGeomParams(
        blades=blades,
        core1=core1,
        core2=core2,
        gating=gating,
        riser=riser,
        chills=(chill1, chill2),
        notes=tuple(notes),
    )
