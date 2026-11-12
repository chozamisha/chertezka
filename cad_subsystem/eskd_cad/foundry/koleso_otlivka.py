# -*- coding: utf-8 -*-
"""
Построение технологического чертежа отливки «Колесо рабочее»
только из calc/knowledge (koleso_data + лист расчёта). Без приближений.
"""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from ..annotations.cutting_plane import add_cutting_plane
from ..annotations.datums import add_datum
from ..annotations.view_label import add_view_label
from ..model.document import DrawingDocument
from ..spec.casting_spec import CastingSpec
from ..spec.koleso_loader import (
    KOLESO_PART_ID,
    assert_spec_aligned_with_canon,
    spec_as_legacy_ns,
)
from ..spec.registry import register_builder
from ..model.entities import (
    LAYER_ALLOW,
    LAYER_AXIS,
    LAYER_DIM,
    LAYER_HATCH,
    LAYER_HIDDEN,
    LAYER_MAIN,
    LAYER_TEXT,
    LAYER_THIN,
    Arc,
    Circle,
    DimLinear,
    Hatch,
    Leader,
    Line,
    MText,
    Polyline,
    Text,
)
from ..model.sheet_gost import apply_frame
from ..views.transform import ViewTransform

Point = Tuple[float, float]



def _metal_section_polys(D) -> Tuple[List[Point], List[Point]]:
    """Правая и левая половины металла в разрезе А-А (модель, ось X=0)."""
    rh, rb, rbo, rbs, ro = (
        D.C_HUB / 2,
        D.C_BORE / 2,
        D.C_BORE_LO / 2,
        D.C_BOSS / 2,
        D.C_OUT / 2,
    )
    y0, y1, y2, y3, y4 = (
        D.Y_BOT,
        D.Y_DISK_LO_TOP,
        D.Y_DISK_UP_BOT,
        D.Y_DISK_UP_TOP,
        D.Y_HUB_TOP,
    )
    wall = float(D.RIM_WALL)  # толщина обода в разрезе (из draw_koleso_otl)

    def right() -> List[Point]:
        return [
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
            (rbo, y0 + float(D.BORE_STEP_Y)),
            (rb, y0 + float(D.BORE_STEP_Y)),
            (rb, y4),
        ]

    def left() -> List[Point]:
        return [(-x, y) for x, y in right()]

    return right(), left()


def _riser_polys(D) -> Tuple[List[Point], List[Point]]:
    rn, rr = D.D_NECK / 2, D.D_RISER / 2
    y4 = D.Y_HUB_TOP
    neck_h = 28.0
    neck = [(-rn, y4), (rn, y4), (rn, y4 + neck_h), (-rn, y4 + neck_h)]
    riser = [
        (-rr, y4 + neck_h),
        (rr, y4 + neck_h),
        (rr, D.Y_RISER_TOP),
        (-rr, D.Y_RISER_TOP),
    ]
    return neck, riser


def draw_section_aa(doc: DrawingDocument, V: ViewTransform, D) -> None:
    """Продольный разрез А-А через ось."""
    right, left = _metal_section_polys(D)
    for poly in (right, left):
        sp = V.pts(poly)
        doc.add(Polyline(points=sp, closed=True, layer=LAYER_MAIN))
        doc.add(Hatch(path=sp, pattern="ANSI31", scale=1.2, angle=45, layer=LAYER_HATCH))

    neck, riser = _riser_polys(D)
    for poly, ang in ((neck, -45.0), (riser, -45.0)):
        sp = V.pts(poly)
        doc.add(Polyline(points=sp, closed=True, layer=LAYER_MAIN))
        doc.add(Hatch(path=sp, pattern="ANSI31", scale=1.4, angle=ang, layer=LAYER_HATCH))

    # галтель шейки прибыли (настоящие дуги)
    y4 = D.Y_HUB_TOP
    rn, rr = D.D_NECK / 2, D.D_RISER / 2
    doc.add(Arc(V.P(rn + 8, y4 + 28), V.r(8), 180, 270, layer=LAYER_MAIN))
    doc.add(Arc(V.P(-rn - 8, y4 + 28), V.r(8), 270, 360, layer=LAYER_MAIN))

    # тонкий контур детали / припуски (слой Припуск — редактируемый)
    y3, y4 = D.Y_DISK_UP_TOP, D.Y_HUB_TOP
    dh, db = D.D_HUB / 2, D.D_BORE / 2
    doc.add(Line(V.P(-dh, y3), V.P(-dh, y4 - D.N_TOP), layer=LAYER_ALLOW))
    doc.add(Line(V.P(dh, y3), V.P(dh, y4 - D.N_TOP), layer=LAYER_ALLOW))
    doc.add(Line(V.P(-dh, y4 - D.N_TOP), V.P(dh, y4 - D.N_TOP), layer=LAYER_ALLOW))
    doc.add(Line(V.P(-db, D.Y_BOT + float(D.BORE_STEP_Y)), V.P(-db, y4 - D.N_TOP), layer=LAYER_ALLOW))
    doc.add(Line(V.P(db, D.Y_BOT + float(D.BORE_STEP_Y)), V.P(db, y4 - D.N_TOP), layer=LAYER_ALLOW))
    # низ с припуском N_BOT
    ro = D.C_OUT / 2
    doc.add(Line(V.P(-ro + 5, D.N_BOT), V.P(ro - 5, D.N_BOT), layer=LAYER_ALLOW))

    # канал (стержневая полость)
    ro = D.C_OUT / 2
    y1, y2 = D.Y_DISK_LO_TOP, D.Y_DISK_UP_BOT
    ch = V.pts(
        [(-ro + 25, y1), (ro - 25, y1), (ro - 25, y2), (-ro + 25, y2)]
    )
    doc.add(Polyline(points=ch, closed=True, layer=LAYER_THIN))

    # МФ
    y_mf = (y1 + y2) / 2
    doc.add(Line(V.P(-ro - 35, y_mf), V.P(ro + 35, y_mf), layer="Разъем"))
    p = V.P(ro + 42, y_mf)
    doc.add(Text((p[0] + 2, p[1] + 6), "МФ", height=3.5, layer=LAYER_TEXT))
    doc.add(Text((p[0] + 2, p[1] - 2), "В", height=3.5, layer=LAYER_TEXT))
    doc.add(Text((p[0] + 2, p[1] - 14), "Н", height=3.5, layer=LAYER_TEXT))

    # Ст.2 вертикальный знак снизу
    rb = D.C_BORE / 2
    st2 = V.pts(
        [(-rb, 0), (-rb, -D.H_PRINT2), (rb, -D.H_PRINT2), (rb, 0)]
    )
    doc.add(Polyline(points=st2, closed=True, layer=LAYER_THIN))
    doc.add(
        Leader(
            tip=V.P(rb, -D.H_PRINT2 / 2),
            knee=V.P(rb + 90, -90),
            text="Ст. 2",
            layer=LAYER_THIN,
        )
    )

    # Хол. 1
    rh = D.C_HUB / 2
    chill = V.pts(
        [(rh + 3, y3 - 8), (rh + 43, y3 - 8), (rh + 43, y3 + 32), (rh + 3, y3 + 32)]
    )
    doc.add(Polyline(points=chill, closed=True, layer=LAYER_THIN))
    doc.add(
        Leader(
            tip=V.P(rh + 43, y3 + 12),
            knee=V.P(rh + 130, y3 + 60),
            text="Хол. 1",
            layer=LAYER_THIN,
        )
    )

    # прибыль выноска
    rr = D.D_RISER / 2
    doc.add(
        Leader(
            tip=V.P(rr, (y4 + D.Y_RISER_TOP) / 2),
            knee=V.P(rr + 100, (y4 + D.Y_RISER_TOP) / 2 + 40),
            text="Прибыль 1",
            layer=LAYER_THIN,
        )
    )
    rn = D.D_NECK / 2
    doc.add(
        Leader(
            tip=V.P(-rn, y4 + 14),
            knee=V.P(-rn - 110, y4 + 70),
            text=f"⌀{int(D.D_NECK)} шейка",
            side="left",
            layer=LAYER_THIN,
        )
    )

    # оси
    doc.add(
        Line(
            V.P(0, -D.H_PRINT2 - 20),
            V.P(0, D.Y_RISER_TOP + 20),
            layer=LAYER_AXIS,
        )
    )

    # размеры из calc
    ro = D.C_OUT / 2
    rbs = D.C_BOSS / 2
    doc.add(
        DimLinear(
            p1=V.P(-ro, -25),
            p2=V.P(ro, -25),
            offset=-12,
            text=f"⌀{int(D.C_OUT)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=V.P(-rbs, -55),
            p2=V.P(rbs, -55),
            offset=-10,
            text=f"⌀{int(D.C_BOSS)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=V.P(-rh, y4 + 10),
            p2=V.P(rh, y4 + 10),
            offset=16,
            text=f"⌀{int(D.C_HUB)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=V.P(-rr, D.Y_RISER_TOP + 12),
            p2=V.P(rr, D.Y_RISER_TOP + 12),
            offset=14,
            text=f"⌀{int(D.D_RISER)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=V.P(ro + 30, 0),
            p2=V.P(ro + 30, y4),
            offset=0,
            text=f"{int(D.H_BODY)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=V.P(ro + 55, y4),
            p2=V.P(ro + 55, D.Y_RISER_TOP),
            offset=0,
            text=f"{int(D.H_RISER)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=V.P(ro + 12, y1),
            p2=V.P(ro + 12, y2),
            offset=0,
            text=f"{int(D.C_H_CH)}",
            layer=LAYER_DIM,
        )
    )

    # база А на низе отливки + подпись разреза
    add_datum(doc, V.P(0, 0), letter="А", outward=(0.0, -1.0), size=7.0)
    add_view_label(
        doc,
        (V.ox, V.oy - (D.C_OUT / 2) / V.k - 32),
        "А-А",
        scale=f"1:{int(D.SCALE_K)}",
    )


def draw_plan(doc: DrawingDocument, V: ViewTransform, D) -> None:
    """Вид сверху (план формы) + местный разрез знака Ст.1."""
    ro, rh, rbs, rb = D.C_OUT / 2, D.C_HUB / 2, D.C_BOSS / 2, D.C_BORE / 2
    doc.add(Circle(V.P(0, 0), V.r(ro), layer=LAYER_MAIN))
    doc.add(Circle(V.P(0, 0), V.r(rbs), layer=LAYER_THIN))
    doc.add(Circle(V.P(0, 0), V.r(rh), layer=LAYER_MAIN))
    doc.add(Circle(V.P(0, 0), V.r(rb), layer=LAYER_THIN))
    doc.add(Circle(V.P(0, 0), V.r(D.D_RISER / 2), layer=LAYER_THIN))
    doc.add(Circle(V.P(0, 0), V.r(D.D_NECK / 2), layer=LAYER_THIN))

    # лопатки hidden
    for i in range(4):
        a0 = math.radians(i * 90 + 15)
        a1 = math.radians(i * 90 + 75)
        pts = []
        for t in range(15):
            u = t / 14
            a = a0 + (a1 - a0) * u
            r = 130 + u * (ro - 50 - 130)
            pts.append(V.P(r * math.cos(a), r * math.sin(a)))
        doc.add(Polyline(points=pts, closed=False, layer=LAYER_HIDDEN))

    # Ст.1 горизонтальные знаки (L_PRINT из calc)
    for ang in (0.0, 180.0):
        a = math.radians(ang)
        c, s = math.cos(a), math.sin(a)
        p0x, p0y = ro * c, ro * s
        tx, ty = -s, c
        nx, ny = c, s
        w, Lp = 50.0, D.L_PRINT
        corners = [
            (p0x - tx * w / 2, p0y - ty * w / 2),
            (p0x - tx * w / 2 + nx * Lp, p0y - ty * w / 2 + ny * Lp),
            (p0x + tx * w / 2 + nx * Lp, p0y + ty * w / 2 + ny * Lp),
            (p0x + tx * w / 2, p0y + ty * w / 2),
        ]
        doc.add(Polyline(points=V.pts(corners), closed=True, layer=LAYER_THIN))
    doc.add(
        Leader(
            tip=V.P(ro + D.L_PRINT, 0),
            knee=V.P(ro + D.L_PRINT + 40, 50),
            text="Ст. 1",
            layer=LAYER_THIN,
        )
    )

    # Хол. 2 на ободе
    for ang in (90.0, 270.0):
        a = math.radians(ang)
        c, s = math.cos(a), math.sin(a)
        p0x, p0y = (ro - 8) * c, (ro - 8) * s
        tx, ty = -s, c
        nx, ny = c, s
        corners = [
            (p0x - tx * 22, p0y - ty * 22),
            (p0x - tx * 22 + nx * 28, p0y - ty * 22 + ny * 28),
            (p0x + tx * 22 + nx * 28, p0y + ty * 22 + ny * 28),
            (p0x + tx * 22, p0y + ty * 22),
        ]
        doc.add(Polyline(points=V.pts(corners), closed=True, layer=LAYER_THIN))
    doc.add(
        Leader(
            tip=V.P(0, ro + 28),
            knee=V.P(-55, ro + 80),
            text="Хол. 2",
            side="left",
            layer=LAYER_THIN,
        )
    )

    # Литниковая система (площади из calc)
    sx = -ro - 130
    doc.add(Circle(V.P(sx, 0), V.r(23), layer=LAYER_MAIN))  # стояк
    slag = V.pts(
        [(sx + 23, -16), (-ro - 8, -16), (-ro - 8, 16), (sx + 23, 16)]
    )
    doc.add(Polyline(points=slag, closed=True, layer=LAYER_THIN))
    for yy in (-100.0, 100.0):
        pit = V.pts(
            [(-ro - 8, yy - 10), (-ro, yy - 10), (-ro, yy + 10), (-ro - 8, yy + 10)]
        )
        doc.add(Polyline(points=pit, closed=True, layer=LAYER_THIN))
    doc.add(Leader(tip=V.P(sx, 23), knee=V.P(sx - 45, 95), text="стояк", side="left", layer=LAYER_THIN))
    doc.add(Leader(tip=V.P(-ro - 50, 16), knee=V.P(-ro - 100, -75), text="шлаковик", side="left", layer=LAYER_THIN))
    doc.add(Leader(tip=V.P(-ro - 4, 100), knee=V.P(-ro - 75, 160), text="питатель", side="left", layer=LAYER_THIN))

    # оси + размер
    doc.add(Line(V.P(-ro - D.L_PRINT - 20, 0), V.P(ro + D.L_PRINT + 20, 0), layer=LAYER_AXIS))
    doc.add(Line(V.P(0, -ro - 40), V.P(0, ro + D.L_PRINT + 40), layer=LAYER_AXIS))
    doc.add(
        DimLinear(
            p1=V.P(-ro, -ro - 25),
            p2=V.P(ro, -ro - 25),
            offset=-10,
            text=f"⌀{int(D.C_OUT)}",
            layer=LAYER_DIM,
        )
    )

    # секущие А-А (гориз.) и В-В (верт.) по ГОСТ 2.305
    add_cutting_plane(doc, V.P(-ro - 18, 0), V.P(ro + 18, 0), letter="А", tick=9)
    add_cutting_plane(doc, V.P(0, -ro - 18), V.P(0, ro + 18), letter="В", tick=9)

    # база Б — ось на плане
    add_datum(doc, V.P(ro + 2, 0), letter="Б", outward=(1.0, 0.0), size=6.5)
    add_view_label(doc, (V.ox, V.oy - V.r(ro) - 36), "Вид сверху", scale=f"1:{int(D.SCALE_K)}")

    # местный разрез Б-Б знака Ст.1 (выносной)
    lx, ly = V.ox + 100, V.oy + 118
    pw, ph = D.L_PRINT / V.k, 50 / V.k
    local = [
        (lx, ly),
        (lx + pw, ly),
        (lx + pw, ly + ph),
        (lx, ly + ph),
    ]
    doc.add(Polyline(points=local, closed=True, layer=LAYER_MAIN))
    doc.add(Hatch(path=local, pattern="ANSI31", scale=0.7, angle=45, layer=LAYER_HATCH))
    # скругления знака — дуги
    doc.add(Arc((lx + 2, ly + 2), 2.0, 180, 270, layer=LAYER_MAIN))
    doc.add(Arc((lx + pw - 2, ly + 2), 2.0, 270, 360, layer=LAYER_MAIN))
    add_view_label(doc, (lx + pw / 2, ly - 10), "Б-Б (знак Ст.1)", scale="1:1")
    doc.add(
        DimLinear(
            p1=(lx, ly - 4),
            p2=(lx + pw, ly - 4),
            offset=-8,
            text=f"{int(D.L_PRINT)}",
            layer=LAYER_DIM,
        )
    )


def draw_section_bb_transverse(doc: DrawingDocument, V: ViewTransform, D) -> None:
    """Поперечный разрез В-В через канал (плоскость Y = середина H_CH)."""
    # В плане канала: кольцо металла обода + ступица; штриховка сечений
    ro, rh, rb = D.C_OUT / 2, D.C_HUB / 2, D.C_BORE / 2
    wall = 25.0
    # outer ring metal (annulus approximated as two closed polys for hatch)
    # Right half ring simplified as trapezoid strip
    outer = []
    inner = []
    for i in range(25):
        a = math.radians(i * 360 / 24)
        outer.append((ro * math.cos(a), ro * math.sin(a)))
    for i in range(25):
        a = math.radians(i * 360 / 24)
        inner.append(((ro - wall) * math.cos(a), (ro - wall) * math.sin(a)))
    # draw contours
    doc.add(Circle(V.P(0, 0), V.r(ro), layer=LAYER_MAIN))
    doc.add(Circle(V.P(0, 0), V.r(ro - wall), layer=LAYER_MAIN))
    doc.add(Circle(V.P(0, 0), V.r(rh), layer=LAYER_MAIN))
    doc.add(Circle(V.P(0, 0), V.r(rb), layer=LAYER_THIN))
    # hatch ring via polygon approximation
    ring = outer[:-1] + list(reversed(inner[:-1]))
    doc.add(Hatch(path=V.pts(ring), pattern="ANSI31", scale=1.0, angle=-45, layer=LAYER_HATCH))
    # hub metal disk
    hub = []
    for i in range(25):
        a = math.radians(i * 360 / 24)
        hub.append((rh * math.cos(a), rh * math.sin(a)))
    bore = []
    for i in range(25):
        a = math.radians(i * 360 / 24)
        bore.append((rb * math.cos(a), rb * math.sin(a)))
    hub_poly = hub[:-1] + list(reversed(bore[:-1]))
    doc.add(Hatch(path=V.pts(hub_poly), pattern="ANSI31", scale=1.0, angle=45, layer=LAYER_HATCH))
    doc.add(Line(V.P(-ro - 15, 0), V.P(ro + 15, 0), layer=LAYER_AXIS))
    doc.add(Line(V.P(0, -ro - 15), V.P(0, ro + 15), layer=LAYER_AXIS))
    doc.add(
        DimLinear(
            p1=V.P(-ro, -ro - 18),
            p2=V.P(ro, -ro - 18),
            offset=-8,
            text=f"⌀{int(D.C_OUT)}",
            layer=LAYER_DIM,
        )
    )
    add_view_label(doc, (V.ox, V.oy - V.r(ro) - 24), "В-В", scale=f"1:{int(D.SCALE_K * 1.6)}")


def draw_ls_callouts(doc: DrawingDocument, D) -> None:
    """Сечения ЛС с площадями строго из calc."""
    x0, y0 = 35.0, 400.0
    # Fп rectangle ~ proportional sketch
    doc.add(
        Polyline(
            points=[(x0, y0), (x0 + 14, y0), (x0 + 14, y0 + 8), (x0, y0 + 8)],
            closed=True,
            layer=LAYER_THIN,
        )
    )
    doc.add(
        Text(
            (x0 + 16, y0 + 2),
            f"Fп={D.F_PIT / D.N_PIT:g} см² ×{D.N_PIT}; ΣFп={D.F_PIT:g}",
            height=3.0,
            layer=LAYER_TEXT,
        )
    )
    doc.add(
        Polyline(
            points=[(x0, y0 - 28), (x0 + 18, y0 - 28), (x0 + 16, y0 - 16), (x0 + 2, y0 - 16)],
            closed=True,
            layer=LAYER_THIN,
        )
    )
    doc.add(Text((x0 + 20, y0 - 24), f"Fшл={D.F_SLAG:g} см²", height=3.0, layer=LAYER_TEXT))
    doc.add(Circle((x0 + 7, y0 - 50), 5.5, layer=LAYER_THIN))
    doc.add(Text((x0 + 16, y0 - 52), f"Fст={D.F_SPRUE:g} см²", height=3.0, layer=LAYER_TEXT))
    ratio = f"1:{D.F_SLAG / D.F_PIT:g}:{D.F_SPRUE / D.F_PIT:g}"
    doc.add(Text((x0, y0 + 16), f"Fп:Fшл:Fст = {ratio}", height=3.0, layer=LAYER_TEXT))


def draw_tt(doc: DrawingDocument, D) -> None:
    content = (
        "Технические требования\n"
        "1 Неуказанные литейные радиусы R5...R10.\n"
        "2 Точность отливки 10-10-5-3 ГОСТ 26645-85.\n"
        "3 Уклоны ГОСТ 3212-92: нар. 1°30′, внут. 2° (увеличением).\n"
        "4 Усадка линейная 1,9 % (ИЧХ28Н2).\n"
        "5 Твёрдость рабочих поверхностей HB 500...550.\n"
        "6 Лопатки 4 шт., равномерно; профиль по шаблону.\n"
        f"7 Литниковая Fп:Fшл:Fст = 1:{D.F_SLAG/D.F_PIT:g}:{D.F_SPRUE/D.F_PIT:g} (ветка ИЧХ).\n"
        f"8 Прибыль 1: шейка ⌀{int(D.D_NECK)} на металле ступицы; стык со Ст.2 — схема A.\n"
        "9 Остатки прибыли/питателей на обрабатываемых не более 3 мм.\n"
        "10 Тонкой линией показан контур детали.\n"
        "11 Источник размеров: calc pipeline (табл.6/ЛС/стержни) + лист KP-062215009-01_calc.\n"
        "12 Контуры А-А / плана / В-В: OCP HLR/Section (осесимм. тело); лопатки/знаки/ЛС — оформление."
    )
    doc.add(
        MText(
            position=(300, 105),
            content=content,
            height=2.8,
            width=200,
            layer=LAYER_TEXT,
        )
    )


@register_builder(KOLESO_PART_ID)
def build_koleso_otlivka(
    spec: CastingSpec | None = None,
    *,
    use_ocp: bool | None = None,
) -> DrawingDocument:
    """Основной путь: CastingSpec → DrawingDocument (eskd_cad).

    Если spec не передан — P1 pipeline (таблицы/гейты → CastingSpec).
    P2: при use_ocp=True (по умолчанию, если доступен OCP8) контуры
    А-А / плана / В-В строятся через OpenCascade; legacy 2D-функции сохранены.
    """
    if spec is None:
        from ..calc.pipeline import build_koleso_casting_result

        spec = build_koleso_casting_result().spec
    if spec.part_id != KOLESO_PART_ID:
        raise ValueError(f"builder колеса получил part_id={spec.part_id!r}")
    align = assert_spec_aligned_with_canon(spec)
    if align:
        raise ValueError(
            "CastingSpec не совпадает с koleso_data / формулами:\n" + "\n".join(align)
        )
    D = spec_as_legacy_ns(spec)

    from ..geom.ocp_bridge import ocp_available

    if use_ocp is None:
        use_ocp = ocp_available()

    doc = DrawingDocument(fmt=D.FMT, landscape=True)
    apply_frame(
        doc,
        name_lines=list(D.NAME),
        code=D.CODE,
        material=", ".join(D.MAT) if isinstance(D.MAT, (list, tuple)) else str(D.MAT),
        mass=str(D.MASS_STAMP),
        scale=f"1:{int(D.SCALE_K)}",
        org=("СФУ ИЦМ", "гр. ЗЦМ22-01Б"),
        lit="У",
        dev=D.DEV,
        chk=D.CHK,
    )

    # layout from calc note: section ~(155,250), plan ~(420,200) on A2
    Vsec = ViewTransform(ox=145.0, oy=235.0, k=D.SCALE_K)
    Vpln = ViewTransform(ox=400.0, oy=200.0, k=D.SCALE_K)
    Vbb = ViewTransform(ox=520.0, oy=300.0, k=D.SCALE_K * 1.6)

    if use_ocp:
        from .ocp_koleso import (
            assert_wheel_views_ok,
            build_wheel_views,
            draw_local_bb_ocp,
            draw_plan_ocp,
            draw_section_aa_ocp,
            draw_section_bb_ocp,
            run_wheel_intersection_qa,
        )

        views = build_wheel_views(spec)
        assert_wheel_views_ok(views)
        inter = run_wheel_intersection_qa(spec)
        if not inter.meta.get("ok", False):
            raise ValueError(
                "P3 intersection QA failed:\n- "
                + "\n- ".join(inter.meta.get("issues") or ["unknown"])
            )
        draw_section_aa_ocp(doc, Vsec, spec, views["AA"])
        draw_plan_ocp(doc, Vpln, spec, views["plan"])
        draw_section_bb_ocp(doc, Vbb, spec, views["BB"])
        # местный Б-Б: только знак у +X; масштаб 1:2
        Vloc = ViewTransform(ox=120.0, oy=55.0, k=2.0)
        draw_local_bb_ocp(doc, Vloc, spec, views["local_BB"])
    else:
        draw_section_aa(doc, Vsec, D)
        draw_plan(doc, Vpln, D)
        draw_section_bb_transverse(doc, Vbb, D)
    draw_ls_callouts(doc, D)
    draw_tt(doc, D)
    return doc
