# -*- coding: utf-8 -*-
"""Оркестрация P4: inputs → geometry → drawing → отчёт."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from ...calc.pipeline import CalcResult, build_koleso_casting_result
from ...foundry.koleso_otlivka import build_koleso_otlivka
from ...geom.tech_params import wheel_tech_geom
from ...model.document import DrawingDocument
from ...spec.casting_spec import CastingSpec
from .drawing import run_drawing_checks
from .geometry import run_geometry_checks
from .inputs import run_input_checks
from .status import QualityReport
from .view_layout import wheel_view_layouts


def run_quality_report(
    *,
    spec: Optional[CastingSpec] = None,
    calc: Optional[CalcResult] = None,
    doc: Optional[DrawingDocument] = None,
    use_ocp: bool = True,
) -> QualityReport:
    calc = calc or build_koleso_casting_result()
    spec = spec or calc.spec
    tech = wheel_tech_geom(spec)

    report = QualityReport(part_id=spec.part_id, code=spec.code)
    run_input_checks(report, spec=spec, calc=calc, tech=tech)
    views = run_geometry_checks(report, spec=spec, tech=tech)
    if doc is None:
        doc = build_koleso_otlivka(spec, use_ocp=use_ocp)
    layouts = wheel_view_layouts(spec)
    run_drawing_checks(
        report, doc=doc, spec=spec, views=views, view_layouts=layouts
    )

    # сводка допущений из tech уже в inputs; добавить P3 conditional list
    report.conditional_geometry = list(dict.fromkeys(report.conditional_geometry))
    return report


def write_quality_report(
    report: QualityReport,
    out_dir: Union[str, Path],
    *,
    basename: Optional[str] = None,
) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = basename or f"{report.code}_P4_quality"
    md_path = out_dir / f"{base}.md"
    json_path = out_dir / f"{base}.json"
    md_path.write_text(report.to_markdown(), encoding="utf-8")
    json_path.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path
