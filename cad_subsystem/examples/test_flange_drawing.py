# -*- coding: utf-8 -*-
"""
Тестовый инженерный чертёж (этап 5–6):
  вид спереди + разрез А-А + размеры + штриховка + выноска + ТТ + штамп
  → DXF (редактируемый) + PDF.

Запуск из корня cad_subsystem:
  python3 -m examples.test_flange_drawing
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eskd_cad.export import export_dxf, export_pdf
from eskd_cad.model.document import DrawingDocument
from eskd_cad.model.entities import (
    LAYER_AXIS,
    LAYER_DIM,
    LAYER_HATCH,
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
from eskd_cad.model.sheet_gost import apply_frame
from eskd_cad.qa.validate_dxf import validate

OUT = ROOT / "out"


def build() -> DrawingDocument:
    doc = DrawingDocument(fmt="A3", landscape=True)
    apply_frame(
        doc,
        name_lines=["Фланец", "(тест CAD)"],
        code="TEST-CAD-0001",
        material="СЧ15 ГОСТ 1412-85",
        mass="2,4",
        scale="1:1",
        dev="Агент",
        chk="—",
    )

    # --- geometry (model mm placed on sheet) ---
    # Front view (left): OD 120, ID 40, PCD 90, 4×⌀14
    ox, oy = 130.0, 170.0  # center of front view
    od, id_, pcd, hole = 60.0, 20.0, 45.0, 7.0

    doc.add(Circle((ox, oy), od, layer=LAYER_MAIN))
    doc.add(Circle((ox, oy), id_, layer=LAYER_MAIN))
    doc.add(Circle((ox, oy), pcd, layer=LAYER_AXIS))
    # axes
    doc.add(Line((ox - od - 8, oy), (ox + od + 8, oy), layer=LAYER_AXIS))
    doc.add(Line((ox, oy - od - 8), (ox, oy + od + 8), layer=LAYER_AXIS))
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        cx = ox + pcd * math.cos(a)
        cy = oy + pcd * math.sin(a)
        doc.add(Circle((cx, cy), hole, layer=LAYER_MAIN))

    # dimensions on front view
    doc.add(
        DimLinear(
            p1=(ox - od, oy),
            p2=(ox + od, oy),
            offset=-od - 18,
            text="⌀120",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=(ox - id_, oy),
            p2=(ox + id_, oy),
            offset=id_ + 14,
            text="⌀40",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        Leader(
            tip=(ox + pcd * math.cos(math.radians(45)) + hole * 0.7,
                 oy + pcd * math.sin(math.radians(45)) + hole * 0.7),
            knee=(ox + od + 35, oy + od + 25),
            text="4 отв. ⌀14",
            layer=LAYER_THIN,
        )
    )
    doc.add(Text((ox, oy - od - 28), "Вид спереди", height=3.5, halign="center", layer=LAYER_TEXT))

    # --- Section A-A (right): flange thickness profile ---
    sx, sy = 310.0, 170.0
    # half-section rectangle body + bore
    # outer profile points (closed for hatch of material)
    t = 18.0
    hub_h = 28.0
    # right half section outline (material)
    # x local: 0 at axis
    def S(x, y):
        return (sx + x, sy + y)

    # full section contour (symmetric)
    body = [
        S(-od, -t / 2),
        S(od, -t / 2),
        S(od, t / 2),
        S(id_ + 8, t / 2),
        S(id_ + 8, hub_h / 2),
        S(id_, hub_h / 2),
        S(id_, -hub_h / 2),
        S(id_ + 8, -hub_h / 2),
        S(id_ + 8, -t / 2),
        S(-od, -t / 2),  # will close via left side properly below
    ]
    # Better closed contour for solid of revolution cut:
    contour = [
        S(-od, -t / 2),
        S(-id_ - 8, -t / 2),
        S(-id_ - 8, -hub_h / 2),
        S(-id_, -hub_h / 2),
        S(-id_, hub_h / 2),
        S(-id_ - 8, hub_h / 2),
        S(-id_ - 8, t / 2),
        S(-od, t / 2),
        S(-od, -t / 2),
    ]
    # right half material (for hatch) excluding bore
    right_mat = [
        S(id_, -hub_h / 2),
        S(id_ + 8, -hub_h / 2),
        S(id_ + 8, -t / 2),
        S(od, -t / 2),
        S(od, t / 2),
        S(id_ + 8, t / 2),
        S(id_ + 8, hub_h / 2),
        S(id_, hub_h / 2),
    ]
    left_mat = [
        S(-id_, hub_h / 2),
        S(-id_ - 8, hub_h / 2),
        S(-id_ - 8, t / 2),
        S(-od, t / 2),
        S(-od, -t / 2),
        S(-id_ - 8, -t / 2),
        S(-id_ - 8, -hub_h / 2),
        S(-id_, -hub_h / 2),
    ]
    doc.add(Polyline(points=right_mat, closed=True, layer=LAYER_MAIN))
    doc.add(Polyline(points=left_mat, closed=True, layer=LAYER_MAIN))
    doc.add(
        Hatch(
            path=right_mat,
            pattern="ANSI31",
            scale=0.8,
            angle=45,
            layer=LAYER_HATCH,
        )
    )
    doc.add(
        Hatch(
            path=left_mat,
            pattern="ANSI31",
            scale=0.8,
            angle=45,
            layer=LAYER_HATCH,
        )
    )
    # hole edges as arcs? use vertical lines at bore
    doc.add(Line(S(-id_, -hub_h / 2), S(-id_, hub_h / 2), layer=LAYER_MAIN))
    doc.add(Line(S(id_, -hub_h / 2), S(id_, hub_h / 2), layer=LAYER_MAIN))
    # axis of section
    doc.add(Line(S(0, -hub_h / 2 - 12), S(0, hub_h / 2 + 12), layer=LAYER_AXIS))
    # fillet-like arcs on hub (decorative real ARC entities)
    doc.add(Arc(S(id_ + 8, t / 2), 4, 180, 270, layer=LAYER_MAIN))
    doc.add(Arc(S(-id_ - 8, t / 2), 4, 270, 360, layer=LAYER_MAIN))

    doc.add(
        DimLinear(
            p1=S(-od, t / 2),
            p2=S(od, t / 2),
            offset=22,
            text="⌀120",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=S(od, -t / 2),
            p2=S(od, t / 2),
            offset=14,
            text="18",
            layer=LAYER_DIM,
        )
    )
    doc.add(
        DimLinear(
            p1=S(id_, -hub_h / 2),
            p2=S(id_, hub_h / 2),
            offset=-20,
            text="28",
            layer=LAYER_DIM,
        )
    )
    doc.add(Text((sx, sy - od - 20), "А-А", height=5, halign="center", layer=LAYER_TEXT))

    # cutting plane markers on front view
    doc.add(Line((ox - od - 15, oy), (ox - od - 5, oy), layer=LAYER_THIN))
    doc.add(Line((ox + od + 5, oy), (ox + od + 15, oy), layer=LAYER_THIN))
    doc.add(Text((ox - od - 18, oy + 3), "А", height=5, layer=LAYER_TEXT))
    doc.add(Text((ox + od + 16, oy + 3), "А", height=5, layer=LAYER_TEXT))

    # Technical requirements
    doc.add(
        MText(
            position=(250, 95),
            content=(
                "Технические требования\n"
                "1 Неуказанные предельные отклонения размеров h14, H14, ±IT14/2.\n"
                "2 *Размеры для справок.\n"
                "3 Чертёж — тест CAD-подсистемы (Linux, ezdxf)."
            ),
            height=3.5,
            width=150,
            layer=LAYER_TEXT,
        )
    )
    return doc


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = build()
    dxf = OUT / "TEST_FLANGE.dxf"
    pdf = OUT / "TEST_FLANGE.pdf"
    export_dxf(doc, dxf)
    export_pdf(doc, pdf, dpi=180)
    print("wrote", dxf)
    print("wrote", pdf)
    print("wrote", pdf.with_suffix(".png"))
    issues = validate(dxf)
    for it in issues:
        print("ISSUE:", it)
    if issues:
        print("TEST FAILED")
        return 1
    print("TEST OK — editable DXF + PDF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
