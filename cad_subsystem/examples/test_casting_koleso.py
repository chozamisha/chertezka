# -*- coding: utf-8 -*-
"""
Технологический чертёж отливки «Колесо рабочее» (сложная деталь):
  разрез А-А, план, местный разрез Б-Б знака, стержни, ЛС, прибыль, холодильники.
Размеры только из knowledge/calc (koleso_data + лист расчёта).

  python3 -m examples.test_casting_koleso
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401 — registry
from eskd_cad.export import export_dxf, export_pdf
from eskd_cad.qa.geometry_check import check_document, check_dxf_file
from eskd_cad.qa.quality_checklist import (
    check_dxf_requirements,
    check_scene_requirements,
    report,
)
from eskd_cad.qa.validate_dxf import validate
from eskd_cad.spec import build_drawing, load_koleso_spec

OUT = ROOT / "out"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = build_drawing(load_koleso_spec())

    geom_issues = check_document(doc)
    for it in geom_issues:
        print("GEOM:", it)
    if geom_issues:
        print("geometry_check FAILED")
        return 1
    print("geometry_check OK")

    bad, txt = report(check_scene_requirements(doc))
    print(txt)
    if bad:
        print(f"quality_checklist scene FAILED ({bad})")
        return 1
    print("quality_checklist scene OK")

    dxf = OUT / "KP-062215009-01_Otlivka.dxf"
    pdf = OUT / "KP-062215009-01_Otlivka.pdf"
    export_dxf(doc, dxf)
    export_pdf(doc, pdf, dpi=160)
    print("wrote", dxf)
    print("wrote", pdf)

    issues = validate(dxf)
    issues += check_dxf_file(dxf)
    for it in issues:
        print("ISSUE:", it)
    if issues:
        print("DXF validate FAILED")
        return 1
    print("DXF validate OK")

    bad, txt = report(check_dxf_requirements(dxf))
    print(txt)
    if bad:
        print(f"quality_checklist dxf FAILED ({bad})")
        return 1
    print("quality_checklist dxf OK")

    # LibreCAD open/print proof
    lc_pdf = OUT / "KP-062215009-01_Otlivka_librecad.pdf"
    # LibreCAD writes alongside source name; copy strategy
    cmd = ["librecad", "dxf2pdf", "-a", "-p", "594x420", str(dxf.name)]
    r = subprocess.run(cmd, cwd=str(OUT), capture_output=True, text=True, timeout=120)
    print(r.stdout[-400:] if r.stdout else "")
    print(r.stderr[-400:] if r.stderr else "")
    produced = OUT / "KP-062215009-01_Otlivka.pdf"
    # dxf2pdf may overwrite our mpl pdf — restore naming
    if produced.exists() and produced.stat().st_size < 5000:
        print("WARN: LibreCAD pdf suspiciously small")
    # re-export mpl pdf under clear name if overwritten
    export_pdf(doc, OUT / "KP-062215009-01_Otlivka_mpl.pdf", dpi=160)
    if (OUT / "KP-062215009-01_Otlivka.pdf").exists():
        # keep librecad result as separate if different
        pass
    # rename libre output if it replaced
    lib_candidate = OUT / "KP-062215009-01_Otlivka.pdf"
    # Always regenerate canonical mpl pdf last
    export_pdf(doc, pdf, dpi=160)
    # Run dxf2pdf to sibling via copy
    import shutil

    tmp_dxf = OUT / "_lc_in.dxf"
    shutil.copy(dxf, tmp_dxf)
    subprocess.run(
        ["librecad", "dxf2pdf", "-a", "-p", "594x420", tmp_dxf.name],
        cwd=str(OUT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if (OUT / "_lc_in.pdf").exists():
        shutil.move(str(OUT / "_lc_in.pdf"), str(lc_pdf))
        tmp_dxf.unlink(missing_ok=True)
        print("LibreCAD OK →", lc_pdf, lc_pdf.stat().st_size)
    else:
        print("LibreCAD pdf not found; stdout/stderr above")
        return 1

    print("TEST CASTING OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
