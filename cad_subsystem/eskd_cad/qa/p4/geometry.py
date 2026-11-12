# -*- coding: utf-8 -*-
"""P4 задача 2: геометрический контроль (CastingSpec + OCP)."""
from __future__ import annotations

from typing import Dict, Optional

from ...foundry.ocp_koleso import assert_wheel_views_ok, build_wheel_views, run_wheel_intersection_qa
from ...geom.assembly_wheel import metal_plus_tech_for_views
from ...geom.ocp_bridge import ocp_available, run_ocp_job
from ...geom.tech_params import TechGeomParams, wheel_tech_geom
from ...geom.view_types import ViewResult
from ...spec.casting_spec import CastingSpec
from .status import CheckResult, CheckStatus, QualityReport


def run_geometry_checks(
    report: QualityReport,
    *,
    spec: CastingSpec,
    tech: Optional[TechGeomParams] = None,
    views: Optional[Dict[str, ViewResult]] = None,
) -> Optional[Dict[str, ViewResult]]:
    tech = tech or wheel_tech_geom(spec)

    if not ocp_available():
        for cid, title, cond in (
            (
                "GEO-001",
                "OCP доступен для геометрических проверок",
                "python-ocp8 / venv-ocp8",
            ),
            (
                "GEO-002",
                "Пересечения металл/стержни/ЛС/хол.",
                "intersection QA ok",
            ),
            (
                "GEO-002b",
                "Инженерное основание tol_volume пересечений",
                "tol_volume подтверждён в knowledge",
            ),
            (
                "GEO-003",
                "Валидность объёма металла",
                "volume_mm3 > 0",
            ),
            (
                "GEO-004",
                "Галтель шейки прибыли",
                "fillet изменяет объём vs fillet_r=0",
            ),
            (
                "GEO-005",
                "Проекции/сечения соответствуют телу",
                "assert_wheel_views_ok",
            ),
        ):
            report.add(
                CheckResult(
                    id=cid,
                    title=title,
                    category="geometry",
                    status=CheckStatus.NOT_CHECKED,
                    condition=cond,
                    detail="OCP8 недоступен",
                    normative_source="внутреннее инженерное правило",
                    normative_point="P2/P3 OCP",
                )
            )
        return None

    report.add(
        CheckResult(
            id="GEO-001",
            title="OCP доступен для геометрических проверок",
            category="geometry",
            status=CheckStatus.PASS,
            condition="python-ocp8 / venv-ocp8",
            normative_source="внутреннее инженерное правило",
            normative_point="P2 ocp_bridge",
        )
    )

    # объём металла
    metal = metal_plus_tech_for_views(spec, tech)
    try:
        vol = run_ocp_job({"solid": metal, "operation": "volume", "name": "metal"}).meta[
            "volume_mm3"
        ]
        if vol > 1.0:
            report.add(
                CheckResult(
                    id="GEO-003",
                    title="Валидность объёма металла",
                    category="geometry",
                    status=CheckStatus.PASS,
                    condition="volume_mm3 > 0 после Cut/Fuse",
                    detail=f"volume_mm3={vol:.3f}",
                    normative_source="внутреннее инженерное правило",
                    normative_point="P3 assembly_wheel / BRep",
                )
            )
        else:
            report.add(
                CheckResult(
                    id="GEO-003",
                    title="Валидность объёма металла",
                    category="geometry",
                    status=CheckStatus.FAIL,
                    condition="volume_mm3 > 0 после Cut/Fuse",
                    detail=f"volume_mm3={vol}",
                    normative_source="внутреннее инженерное правило",
                )
            )
    except Exception as exc:  # noqa: BLE001
        report.add(
            CheckResult(
                id="GEO-003",
                title="Валидность объёма металла",
                category="geometry",
                status=CheckStatus.FAIL,
                condition="volume_mm3 > 0 после Cut/Fuse",
                detail=str(exc),
                normative_source="внутреннее инженерное правило",
            )
        )

    # пересечения (P4.1: GEO-002 числовой PASS; GEO-002b tol basis NOT_CHECKED)
    try:
        import json as _json

        inter = run_wheel_intersection_qa(spec)
        results = inter.meta.get("results") or []
        volumes = inter.meta.get("volumes") or {}
        metal_v = float(volumes.get("metal") or 0.0)
        evidence_pairs = []
        for r in results:
            v = float(r.get("volume_mm3") or 0.0)
            tol = float(r.get("tol_volume") or 0.0)
            entry = {
                "a": r.get("a"),
                "b": r.get("b"),
                "expect": r.get("expect"),
                "volume_mm3": v,
                "tol_volume_mm3": tol,
                "unit": "mm3",
                "ok": bool(r.get("ok")),
                "volume_per_metal": (v / metal_v) if metal_v > 0 else None,
                "tol_basis": "unconfirmed",
            }
            evidence_pairs.append(entry)
        evidence_blob = _json.dumps(
            {"pairs": evidence_pairs, "solid_volumes_mm3": volumes, "metal_mm3": metal_v},
            ensure_ascii=False,
        )
        if inter.meta.get("ok"):
            report.add(
                CheckResult(
                    id="GEO-002",
                    title="Пересечения металл/стержни/ЛС/хол.",
                    category="geometry",
                    status=CheckStatus.PASS,
                    condition="пары disjoint/overlap по expect и tol_volume (числовая)",
                    detail=str(results),
                    evidence=evidence_blob,
                    normative_source="внутреннее инженерное правило",
                    normative_point="P3 intersection_job / STOP_GATES (геометрия); tol не изменялся",
                )
            )
        else:
            report.add(
                CheckResult(
                    id="GEO-002",
                    title="Пересечения металл/стержни/ЛС/хол.",
                    category="geometry",
                    status=CheckStatus.FAIL,
                    condition="пары disjoint/overlap по expect и tol_volume (числовая)",
                    detail="; ".join(inter.meta.get("issues") or []),
                    evidence=evidence_blob,
                    normative_source="внутреннее инженерное правило",
                    normative_point="P3 intersection_job",
                )
            )
        report.add(
            CheckResult(
                id="GEO-002b",
                title="Инженерное основание tol_volume пересечений",
                category="geometry",
                status=CheckStatus.NOT_CHECKED,
                condition="tol_volume для каждой пары подтверждён в knowledge / расчёте",
                detail=(
                    "tol_volume в intersection_job (напр. metal∩core1=5e4 mm³) "
                    "без документированного инженерного основания в knowledge; "
                    "значения tol не изменялись (P4.1)"
                ),
                evidence=evidence_blob,
                normative_source="внутреннее инженерное правило",
                normative_point="P4.1: числовой ok ≠ подтверждённый допуск",
            )
        )
    except Exception as exc:  # noqa: BLE001
        report.add(
            CheckResult(
                id="GEO-002",
                title="Пересечения металл/стержни/ЛС/хол.",
                category="geometry",
                status=CheckStatus.FAIL,
                condition="пары disjoint/overlap по expect и tol_volume (числовая)",
                detail=str(exc),
                normative_source="внутреннее инженерное правило",
            )
        )
        report.add(
            CheckResult(
                id="GEO-002b",
                title="Инженерное основание tol_volume пересечений",
                category="geometry",
                status=CheckStatus.NOT_CHECKED,
                condition="tol_volume для каждой пары подтверждён в knowledge / расчёте",
                detail=f"intersection QA не выполнен: {exc}",
                normative_source="внутреннее инженерное правило",
            )
        )

    # галтель: сравнение объёмов
    try:
        r = tech.riser
        assert r is not None
        base = {
            "kind": "riser_neck_fillet",
            "d_neck": r.d_neck_mm,
            "d_riser": r.d_riser_mm,
            "h_neck": r.h_neck_mm,
            "h_riser": r.h_riser_mm,
            "z0": r.z_seat_mm,
        }
        v_f = run_ocp_job(
            {
                "solid": {**base, "fillet_r": r.fillet_r_mm},
                "operation": "volume",
                "name": "rf",
            }
        ).meta["volume_mm3"]
        v_0 = run_ocp_job(
            {"solid": {**base, "fillet_r": 0.0}, "operation": "volume", "name": "r0"}
        ).meta["volume_mm3"]
        if abs(v_f - v_0) > 1.0:
            report.add(
                CheckResult(
                    id="GEO-004",
                    title="Галтель шейки прибыли",
                    category="geometry",
                    status=CheckStatus.PASS,
                    condition="|V(fillet)-V(0)| > 1 мм³",
                    detail=f"V_f={v_f:.1f} V_0={v_0:.1f}",
                    normative_source="внутреннее инженерное правило",
                    normative_point="pribyli_sheyka.md (переход галтелью); R engineer",
                )
            )
        else:
            report.add(
                CheckResult(
                    id="GEO-004",
                    title="Галтель шейки прибыли",
                    category="geometry",
                    status=CheckStatus.WARNING,
                    condition="|V(fillet)-V(0)| > 1 мм³",
                    detail=f"объёмы почти равны V_f={v_f:.1f} V_0={v_0:.1f} — fillet мог не примениться",
                    normative_source="внутреннее инженерное правило",
                    normative_point="pribyli_sheyka.md",
                )
            )
    except Exception as exc:  # noqa: BLE001
        report.add(
            CheckResult(
                id="GEO-004",
                title="Галтель шейки прибыли",
                category="geometry",
                status=CheckStatus.NOT_CHECKED,
                condition="|V(fillet)-V(0)| > 1 мм³",
                detail=str(exc),
                normative_source="внутреннее инженерное правило",
            )
        )

    # виды / проекции
    try:
        views = views or build_wheel_views(spec)
        assert_wheel_views_ok(views)
        aa = views["AA"].bbox()
        report.add(
            CheckResult(
                id="GEO-005",
                title="Проекции/сечения соответствуют телу",
                category="geometry",
                status=CheckStatus.PASS,
                condition="assert_wheel_views_ok; А-А width≈C_OUT",
                detail=f"AA bbox={aa}; plan_hidden={views['plan'].meta.get('n_hidden')}",
                evidence="HLRBRep / BRepAlgoAPI_Section",
                normative_source="внутреннее инженерное правило",
                normative_point="P2/P3 ViewResult.meta.real_ocp",
            )
        )
        if not views["AA"].meta.get("real_ocp") or not views["plan"].meta.get("real_ocp"):
            report.add(
                CheckResult(
                    id="GEO-006",
                    title="Флаг real_ocp на видах",
                    category="geometry",
                    status=CheckStatus.FAIL,
                    condition="meta.real_ocp=True для А-А и плана",
                    detail="обнаружен вид без real_ocp",
                    normative_source="внутреннее инженерное правило",
                    normative_point="P2_GEOMETRY.md",
                )
            )
        else:
            report.add(
                CheckResult(
                    id="GEO-006",
                    title="Флаг real_ocp на видах",
                    category="geometry",
                    status=CheckStatus.PASS,
                    condition="meta.real_ocp=True для А-А и плана",
                    normative_source="внутреннее инженерное правило",
                    normative_point="P2_GEOMETRY.md",
                )
            )
        return views
    except Exception as exc:  # noqa: BLE001
        report.add(
            CheckResult(
                id="GEO-005",
                title="Проекции/сечения соответствуют телу",
                category="geometry",
                status=CheckStatus.FAIL,
                condition="assert_wheel_views_ok",
                detail=str(exc),
                normative_source="внутреннее инженерное правило",
            )
        )
        report.add(
            CheckResult(
                id="GEO-006",
                title="Флаг real_ocp на видах",
                category="geometry",
                status=CheckStatus.NOT_CHECKED,
                condition="meta.real_ocp=True",
                detail="виды не построены",
                normative_source="внутреннее инженерное правило",
            )
        )
        return None
