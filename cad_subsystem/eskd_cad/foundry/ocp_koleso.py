# -*- coding: utf-8 -*-
"""
OCP-виды/сечения для колеса: CastingSpec → solid → HLR/Section → DrawingDocument.

Размеры, выноски, знаки стержней, ЛС остаются в koleso_otlivka (условные/оформление).
Контуры металла А-А / В-В / плана — реальные OCP-операции.
"""
from __future__ import annotations

from typing import Dict, Tuple

from ..annotations.cutting_plane import add_cutting_plane
from ..annotations.datums import add_datum
from ..annotations.view_label import add_view_label
from ..geom.assembly_wheel import (
    intersection_job,
    local_bb_print_section_job,
    metal_plus_tech_for_views,
)
from ..geom.emit import emit_view
from ..geom.hatch_from_section import closed_loops_from_section
from ..geom.ocp_bridge import project_hlr, run_intersection_check, run_ocp_job, section_plane
from ..geom.qa_views import check_view_result
from ..geom.tech_params import wheel_tech_geom
from ..geom.view_types import CurveKind, ViewResult
from ..model.document import DrawingDocument
from ..model.entities import (
    LAYER_ALLOW,
    LAYER_AXIS,
    LAYER_DIM,
    LAYER_HATCH,
    LAYER_TEXT,
    LAYER_THIN,
    DimLinear,
    Hatch,
    Leader,
    Line,
    Polyline,
    Text,
)
from ..spec.casting_spec import CastingSpec
from ..views.transform import ViewTransform


def build_wheel_views(spec: CastingSpec) -> Dict[str, ViewResult]:
    """P3: металл с лопатками/прибылью (шейка+галтель) → HLR/Section."""
    tech = wheel_tech_geom(spec)
    solid = metal_plus_tech_for_views(spec, tech)
    z_mid = (spec.y_disk_lo_top + spec.y_disk_up_bot) / 2.0
    half = spec.c_out / 2.0 + 80.0

    aa = section_plane(
        solid,
        name="A-A",
        origin=[0.0, 0.0, 0.0],
        normal=[0.0, 1.0, 0.0],
        u_dir=[1.0, 0.0, 0.0],
        v_dir=[0.0, 0.0, 1.0],
        deflection=0.9,
        axes_2d=[{"p1": [0.0, -spec.h_print2 - 20], "p2": [0.0, spec.y_riser_top + 20]}],
    )
    plan = project_hlr(
        solid,
        name="plan",
        look_dir="+z",
        up_dir="+y",
        deflection=1.2,
        axes_2d=[
            {"p1": [-half, 0.0], "p2": [half, 0.0]},
            {"p1": [0.0, -half], "p2": [0.0, half]},
        ],
    )
    bb = section_plane(
        solid,
        name="B-B",
        origin=[0.0, 0.0, float(z_mid)],
        normal=[0.0, 0.0, 1.0],
        u_dir=[1.0, 0.0, 0.0],
        v_dir=[0.0, 1.0, 0.0],
        deflection=0.9,
        axes_2d=[
            {"p1": [-half, 0.0], "p2": [half, 0.0]},
            {"p1": [0.0, -half], "p2": [0.0, half]},
        ],
    )
    local_bb = run_ocp_job(local_bb_print_section_job(spec, tech))
    return {"AA": aa, "plan": plan, "BB": bb, "local_BB": local_bb}


def run_wheel_intersection_qa(spec: CastingSpec) -> ViewResult:
    tech = wheel_tech_geom(spec)
    return run_intersection_check(intersection_job(spec, tech))


def assert_wheel_views_ok(views: Dict[str, ViewResult]) -> None:
    issues = []
    issues += check_view_result(
        views["AA"], require_operation="plane_section", expect_kinds=(CurveKind.SECTION,)
    )
    issues += check_view_result(
        views["plan"], require_operation="hlr_projection", min_curves=1
    )
    issues += check_view_result(
        views["BB"], require_operation="plane_section", expect_kinds=(CurveKind.SECTION,)
    )
    if "local_BB" in views:
        issues += check_view_result(
            views["local_BB"], require_operation="plane_section", expect_kinds=(CurveKind.SECTION,)
        )
        lbb = views["local_BB"].bbox()
        if lbb:
            # знак: от OD−rim до OD+L_PRINT
            if lbb[2] - lbb[0] < 50:
                issues.append(f"local BB span {lbb[2]-lbb[0]} too small for print+rim")
            if lbb[2] < 450:
                issues.append(f"local BB x_max={lbb[2]} — ожидается конец знака ≥~450")
    # габарит А-А ≈ C_OUT и тело+шейка+прибыль
    bb = views["AA"].bbox()
    if bb:
        width = bb[2] - bb[0]
        height = bb[3] - bb[1]
        if abs(width - 825.0) > 5.0:
            issues.append(f"AA width {width} != 825±5")
        if height < 700:
            issues.append(f"AA height {height} too small (ожидается тело+прибыль)")
    if issues:
        raise ValueError("OCP wheel views QA failed:\n- " + "\n- ".join(issues))


def _emit_section_hatches(doc: DrawingDocument, V: ViewTransform, view: ViewResult, angle: float) -> int:
    loops = closed_loops_from_section(view)
    n = 0
    for loop in loops:
        if len(loop) < 4:
            continue
        doc.add(
            Hatch(
                path=V.pts(loop),
                pattern="ANSI31",
                scale=1.2,
                angle=angle,
                layer=LAYER_HATCH,
            )
        )
        n += 1
    return n


def draw_section_aa_ocp(
    doc: DrawingDocument, V: ViewTransform, spec: CastingSpec, view: ViewResult
) -> None:
    """Продольный разрез А-А: контуры из OCP Section + оформление."""
    emit_view(doc, V, view, hatch_section=False)
    _emit_section_hatches(doc, V, view, angle=45.0)

    D = spec  # shorthand via attributes below — use fields
    # припуски / МФ / знаки / выноски / размеры — как в legacy (оформление)
    y1, y2 = spec.y_disk_lo_top, spec.y_disk_up_bot
    y3, y4 = spec.y_disk_up_top, spec.y_hub_top
    ro = spec.c_out / 2.0
    rh = spec.c_hub / 2.0
    rb = spec.c_bore / 2.0
    rr = spec.d_riser / 2.0
    rn = spec.d_neck / 2.0

    # тонкий контур детали (условный слой припуска)
    doc.add(Line(V.P(-spec.d_hub / 2, y3), V.P(-spec.d_hub / 2, y4 - spec.n_top), layer=LAYER_ALLOW))
    doc.add(Line(V.P(spec.d_hub / 2, y3), V.P(spec.d_hub / 2, y4 - spec.n_top), layer=LAYER_ALLOW))
    doc.add(Line(V.P(-spec.d_hub / 2, y4 - spec.n_top), V.P(spec.d_hub / 2, y4 - spec.n_top), layer=LAYER_ALLOW))
    doc.add(Line(V.P(-ro + 5, spec.n_bot), V.P(ro - 5, spec.n_bot), layer=LAYER_ALLOW))

    y_mf = (y1 + y2) / 2.0
    doc.add(Line(V.P(-ro - 35, y_mf), V.P(ro + 35, y_mf), layer="Разъем"))
    p = V.P(ro + 42, y_mf)
    doc.add(Text((p[0] + 2, p[1] + 6), "МФ", height=3.5, layer=LAYER_TEXT))
    doc.add(Text((p[0] + 2, p[1] - 2), "В", height=3.5, layer=LAYER_TEXT))
    doc.add(Text((p[0] + 2, p[1] - 14), "Н", height=3.5, layer=LAYER_TEXT))

    st2 = V.pts([(-rb, 0), (-rb, -spec.h_print2), (rb, -spec.h_print2), (rb, 0)])
    doc.add(Polyline(points=st2, closed=True, layer=LAYER_THIN))
    doc.add(Leader(tip=V.P(rb, -spec.h_print2 / 2), knee=V.P(rb + 90, -90), text="Ст. 2", layer=LAYER_THIN))

    chill = V.pts([(rh + 3, y3 - 8), (rh + 43, y3 - 8), (rh + 43, y3 + 32), (rh + 3, y3 + 32)])
    doc.add(Polyline(points=chill, closed=True, layer=LAYER_THIN))
    doc.add(Leader(tip=V.P(rh + 43, y3 + 12), knee=V.P(rh + 130, y3 + 60), text="Хол. 1", layer=LAYER_THIN))
    doc.add(
        Leader(
            tip=V.P(rr, (y4 + spec.y_riser_top) / 2),
            knee=V.P(rr + 100, (y4 + spec.y_riser_top) / 2 + 40),
            text="Прибыль 1",
            layer=LAYER_THIN,
        )
    )
    doc.add(
        Leader(
            tip=V.P(-rn, y4 + 14),
            knee=V.P(-rn - 110, y4 + 70),
            text=f"⌀{int(spec.d_neck)} шейка",
            side="left",
            layer=LAYER_THIN,
        )
    )

    rbs = spec.c_boss / 2.0
    doc.add(DimLinear(p1=V.P(-ro, -25), p2=V.P(ro, -25), offset=-12, text=f"⌀{int(spec.c_out)}", layer=LAYER_DIM))
    doc.add(DimLinear(p1=V.P(-rbs, -55), p2=V.P(rbs, -55), offset=-10, text=f"⌀{int(spec.c_boss)}", layer=LAYER_DIM))
    doc.add(DimLinear(p1=V.P(-rh, y4 + 10), p2=V.P(rh, y4 + 10), offset=16, text=f"⌀{int(spec.c_hub)}", layer=LAYER_DIM))
    doc.add(
        DimLinear(
            p1=V.P(-rr, spec.y_riser_top + 12),
            p2=V.P(rr, spec.y_riser_top + 12),
            offset=14,
            text=f"⌀{int(spec.d_riser)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(DimLinear(p1=V.P(ro + 30, 0), p2=V.P(ro + 30, y4), offset=0, text=f"{int(spec.h_body)}", layer=LAYER_DIM))
    doc.add(
        DimLinear(
            p1=V.P(ro + 55, y4),
            p2=V.P(ro + 55, spec.y_riser_top),
            offset=0,
            text=f"{int(spec.h_riser)}",
            layer=LAYER_DIM,
        )
    )
    doc.add(DimLinear(p1=V.P(ro + 12, y1), p2=V.P(ro + 12, y2), offset=0, text=f"{int(spec.c_h_ch)}", layer=LAYER_DIM))

    add_datum(doc, V.P(0, 0), letter="А", outward=(0.0, -1.0), size=7.0)
    add_view_label(doc, (V.ox, V.oy - (spec.c_out / 2) / V.k - 32), "А-А (OCP)", scale=f"1:{int(spec.scale_k)}")


def draw_plan_ocp(
    doc: DrawingDocument, V: ViewTransform, spec: CastingSpec, view: ViewResult
) -> None:
    """План: HLR металла с лопатками; знаки/ЛС/хол. — отдельные OCP-тела на листе как оформление привязки."""
    emit_view(doc, V, view, hatch_section=False, skip_kinds=set())

    import math

    ro = spec.c_out / 2.0
    # лопатки больше не рисуем условно — они в HLR (meta.real_ocp)
    for ang in (0.0, 180.0):
        a = math.radians(ang)
        c, s = math.cos(a), math.sin(a)
        p0x, p0y = ro * c, ro * s
        tx, ty = -s, c
        nx, ny = c, s
        w, Lp = 50.0, spec.l_print
        corners = [
            (p0x - tx * w / 2, p0y - ty * w / 2),
            (p0x - tx * w / 2 + nx * Lp, p0y - ty * w / 2 + ny * Lp),
            (p0x + tx * w / 2 + nx * Lp, p0y + ty * w / 2 + ny * Lp),
            (p0x + tx * w / 2, p0y + ty * w / 2),
        ]
        doc.add(Polyline(points=V.pts(corners), closed=True, layer=LAYER_THIN))
    doc.add(
        Leader(
            tip=V.P(ro + spec.l_print, 0),
            knee=V.P(ro + spec.l_print + 40, 50),
            text="Ст. 1",
            layer=LAYER_THIN,
        )
    )

    # Хол. 2 (условные) + ЛС
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

    sx = -ro - 130
    from ..model.entities import Circle

    doc.add(Circle(V.P(sx, 0), V.r(23), layer="Основная"))
    slag = V.pts([(sx + 23, -16), (-ro - 8, -16), (-ro - 8, 16), (sx + 23, 16)])
    doc.add(Polyline(points=slag, closed=True, layer=LAYER_THIN))
    for yy in (-100.0, 100.0):
        pit = V.pts([(-ro - 8, yy - 10), (-ro, yy - 10), (-ro, yy + 10), (-ro - 8, yy + 10)])
        doc.add(Polyline(points=pit, closed=True, layer=LAYER_THIN))
    doc.add(Leader(tip=V.P(sx, 23), knee=V.P(sx - 45, 95), text="стояк", side="left", layer=LAYER_THIN))
    doc.add(
        Leader(
            tip=V.P(-ro - 50, 16),
            knee=V.P(-ro - 100, -75),
            text="шлаковик",
            side="left",
            layer=LAYER_THIN,
        )
    )
    doc.add(
        Leader(
            tip=V.P(-ro - 4, 100),
            knee=V.P(-ro - 75, 160),
            text="питатель",
            side="left",
            layer=LAYER_THIN,
        )
    )

    doc.add(
        DimLinear(
            p1=V.P(-ro, -ro - 25),
            p2=V.P(ro, -ro - 25),
            offset=-10,
            text=f"⌀{int(spec.c_out)}",
            layer=LAYER_DIM,
        )
    )
    add_cutting_plane(doc, V.P(-ro - 18, 0), V.P(ro + 18, 0), letter="А", tick=9)
    add_cutting_plane(doc, V.P(0, -ro - 18), V.P(0, ro + 18), letter="В", tick=9)
    add_datum(doc, V.P(ro + 2, 0), letter="Б", outward=(1.0, 0.0), size=6.5)
    add_view_label(doc, (V.ox, V.oy - V.r(ro) - 36), "Вид сверху (OCP HLR)", scale=f"1:{int(spec.scale_k)}")

    # местный разрез Б-Б — контуры из OCP Section знака; позиция выносного вида
    # (вызывающий передаёт local view через draw_local_bb_ocp)


def draw_section_bb_ocp(
    doc: DrawingDocument, V: ViewTransform, spec: CastingSpec, view: ViewResult
) -> None:
    emit_view(doc, V, view, hatch_section=False)
    _emit_section_hatches(doc, V, view, angle=-45.0)
    ro = spec.c_out / 2.0
    doc.add(
        DimLinear(
            p1=V.P(-ro, -ro - 18),
            p2=V.P(ro, -ro - 18),
            offset=-8,
            text=f"⌀{int(spec.c_out)}",
            layer=LAYER_DIM,
        )
    )
    add_view_label(
        doc,
        (V.ox, V.oy - V.r(ro) - 24),
        "В-В (OCP)",
        scale=f"1:{int(spec.scale_k * 1.6)}",
    )


def draw_local_bb_ocp(
    doc: DrawingDocument, V: ViewTransform, spec: CastingSpec, view: ViewResult
) -> None:
    """Местное сечение Б-Б знака Ст.1 — реальный OCP Section."""
    emit_view(doc, V, view, hatch_section=False)
    _emit_section_hatches(doc, V, view, angle=45.0)
    # размер L_PRINT по габариту знака (OD … OD+L)
    od = spec.c_out / 2.0
    doc.add(
        DimLinear(
            p1=V.P(od, -10),
            p2=V.P(od + spec.l_print, -10),
            offset=-8,
            text=f"{int(spec.l_print)}",
            layer=LAYER_DIM,
        )
    )
    add_view_label(doc, (V.ox, V.oy - 40), "Б-Б (знак Ст.1, OCP)", scale="1:1")
