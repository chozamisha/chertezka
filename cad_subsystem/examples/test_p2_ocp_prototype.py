# -*- coding: utf-8 -*-
"""
P2 прототип на тестовой геометрии (не колесо):
  box_with_bore + flange → HLR + plane_section → DrawingDocument → DXF/PDF

  PYTHONPATH=. python3 -m examples.test_p2_ocp_prototype
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad.export import export_dxf, export_pdf
from eskd_cad.geom import (
    check_view_result,
    emit_view,
    ocp_available,
    project_hlr,
    section_plane,
    solid_box_with_bore,
    solid_flange,
    CurveKind,
)
from eskd_cad.geom.hatch_from_section import closed_loops_from_section
from eskd_cad.model.document import DrawingDocument
from eskd_cad.model.entities import LAYER_HATCH, LAYER_TEXT, Hatch, Text
from eskd_cad.model.sheet_gost import apply_frame
from eskd_cad.views.transform import ViewTransform

OUT = ROOT / "out"


def main() -> int:
    if not ocp_available():
        print("OCP8 unavailable — P2 prototype cannot run")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)

    doc = DrawingDocument(fmt="A3", landscape=True)
    apply_frame(
        doc,
        name_lines=["P2 OCP prototype", "box + flange"],
        code="P2-PROTO-01",
        material="test solid",
        mass="—",
        scale="1:2",
        org=("eskd_cad", "geom"),
        lit="У",
        dev="agent",
        chk="QA",
    )

    # --- box with bore: front HLR + longitudinal section ---
    box = solid_box_with_bore((80, 80, 30), bore_d=24)
    front = project_hlr(box, name="box_front", look_dir="-y", up_dir="+z", deflection=0.25)
    sec = section_plane(
        box,
        name="box_AA",
        origin=[0, 0, 0],
        normal=[0, 1, 0],
        u_dir=[1, 0, 0],
        v_dir=[0, 0, 1],
        deflection=0.25,
        axes_2d=[{"p1": [0, -5], "p2": [0, 35]}],
    )
    for v, need in (
        (front, "hlr_projection"),
        (sec, "plane_section"),
    ):
        issues = check_view_result(v, require_operation=need)
        if issues:
            print("QA FAIL", v.name, issues)
            return 1

    V1 = ViewTransform(ox=90, oy=180, k=2.0)
    V2 = ViewTransform(ox=250, oy=180, k=2.0)
    emit_view(doc, V1, front)
    emit_view(doc, V2, sec)
    for loop in closed_loops_from_section(sec):
        doc.add(Hatch(path=V2.pts(loop), pattern="ANSI31", scale=0.8, angle=45, layer=LAYER_HATCH))
    doc.add(Text((V1.ox - 30, V1.oy + 55), "HLR front (OCP)", height=3.5, layer=LAYER_TEXT))
    doc.add(Text((V2.ox - 30, V2.oy + 55), "Section Y=0 (OCP)", height=3.5, layer=LAYER_TEXT))

    # --- flange: plan HLR + transverse mid-height section ---
    fl = solid_flange(od=100, id_=30, thickness=12, hub_od=50, hub_h=20)
    plan = project_hlr(fl, name="flange_plan", look_dir="+z", up_dir="+y", deflection=0.3)
    mid = section_plane(
        fl,
        name="flange_mid",
        origin=[0, 0, 6],
        normal=[0, 0, 1],
        u_dir=[1, 0, 0],
        v_dir=[0, 1, 0],
        deflection=0.3,
    )
    for v, need in ((plan, "hlr_projection"), (mid, "plane_section")):
        issues = check_view_result(v, require_operation=need)
        if issues:
            print("QA FAIL", v.name, issues)
            return 1
    V3 = ViewTransform(ox=90, oy=60, k=2.0)
    V4 = ViewTransform(ox=250, oy=60, k=2.0)
    emit_view(doc, V3, plan)
    emit_view(doc, V4, mid)
    doc.add(Text((V3.ox - 25, V3.oy + 60), "Flange HLR +Z", height=3.5, layer=LAYER_TEXT))
    doc.add(Text((V4.ox - 25, V4.oy + 60), "Flange section Z=6", height=3.5, layer=LAYER_TEXT))

    report = {
        "engine": "ocp8",
        "operations": [
            front.as_dict()["meta"] | {"name": front.name, "n": len(front.curves)},
            sec.as_dict()["meta"] | {"name": sec.name, "n": len(sec.curves)},
            plan.as_dict()["meta"] | {"name": plan.name, "n": len(plan.curves)},
            mid.as_dict()["meta"] | {"name": mid.name, "n": len(mid.curves)},
        ],
    }
    (OUT / "P2_prototype_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    dxf = OUT / "P2_ocp_prototype.dxf"
    pdf = OUT / "P2_ocp_prototype.pdf"
    export_dxf(doc, dxf)
    export_pdf(doc, pdf, dpi=140)
    print("wrote", dxf)
    print("wrote", pdf)
    print("report", OUT / "P2_prototype_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
