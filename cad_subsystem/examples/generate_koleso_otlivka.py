# -*- coding: utf-8 -*-
"""
Основной путь генерации (P1+P2+P3+P4):
  CastingInputs → calc → CastingSpec → OCP → DrawingDocument → DXF/PDF
  + отчёт качества P4 (NOT_CHECKED ≠ PASS).

  python3 -m examples.generate_koleso_otlivka
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401 — регистрирует builder колеса
from eskd_cad.calc import build_koleso_casting_result
from eskd_cad.export import export_dxf, export_pdf
from eskd_cad.qa.geometry_check import check_document, check_dxf_file
from eskd_cad.qa.p4 import run_quality_report, write_quality_report
from eskd_cad.qa.quality_checklist import (
    check_dxf_requirements,
    check_scene_requirements,
    report,
)
from eskd_cad.qa.validate_dxf import validate
from eskd_cad.spec import build_drawing
from eskd_cad.spec.koleso_loader import assert_spec_aligned_with_canon

OUT = ROOT / "out"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    result = build_koleso_casting_result()
    spec = result.spec
    align = assert_spec_aligned_with_canon(spec)
    if align:
        print("ALIGN FAIL (pipeline vs koleso_data)")
        for a in align:
            print(" ", a)
        return 1
    print("P1 pipeline → CastingSpec aligned with canonical koleso_data")
    print(
        f"  TABLE6_BASE={result.table6_base_mm} mm; "
        f"L_PRINT_MAX={result.l_print_max_mm} mm; "
        f"LS={result.ls_ratio_case}; "
        f"F_PIT:F_SLAG:F_SPRUE="
        f"{spec.f_pit:g}:{spec.f_slag:g}:{spec.f_sprue:g}"
    )
    if result.warnings:
        print("WARNINGS:")
        for w in result.warnings:
            print(" ", w)

    prov_path = OUT / "KP-062215009-01_provenance.json"
    prov_path.write_text(
        json.dumps(result.provenance_report(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("wrote", prov_path)

    doc = build_drawing(spec)
    geom = check_document(doc)
    if geom:
        print("geometry_check FAILED")
        for g in geom:
            print(" ", g)
        return 1

    bad, txt = report(check_scene_requirements(doc))
    print(txt)
    if bad:
        return 1

    # P4 engineering quality report (does not replace checklist)
    q = run_quality_report(spec=spec, calc=result, doc=doc, use_ocp=True)
    md, js = write_quality_report(q, OUT, basename="KP-062215009-01_P4_quality")
    print("P4 quality:", q.counts(), "fully_verified=", q.fully_verified)
    print("wrote", md)
    print("wrote", js)
    if q.has_fail:
        print("P4 FAIL:")
        for e in q.errors:
            print(" ", e)
        return 1
    if q.has_not_checked:
        print("P4 NOT_CHECKED (чертёж не считается полностью проверенным):")
        for c in q.checks:
            if c.status.value == "NOT_CHECKED":
                print(" ", c.id, c.title)

    dxf = OUT / "KP-062215009-01_Otlivka.dxf"
    pdf = OUT / "KP-062215009-01_Otlivka.pdf"
    export_dxf(doc, dxf)
    export_pdf(doc, pdf, dpi=160)
    print("PRIMARY wrote", dxf)
    print("PRIMARY wrote", pdf)

    issues = validate(dxf) + check_dxf_file(dxf)
    if issues:
        for i in issues:
            print("ISSUE:", i)
        return 1
    bad, txt = report(check_dxf_requirements(dxf))
    print(txt)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
