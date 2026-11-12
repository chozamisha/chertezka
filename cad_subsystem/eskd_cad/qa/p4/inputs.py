# -*- coding: utf-8 -*-
"""P4 задача 1: контроль исходных данных и provenance."""
from __future__ import annotations

from typing import List, Optional

from ...calc.pipeline import CalcResult, build_koleso_casting_result
from ...calc.provenance import ParamKind
from ...geom.tech_params import TechGeomParams, wheel_tech_geom
from ...spec.casting_spec import CastingSpec
from .status import CheckResult, CheckStatus, QualityReport


def _ok(cid, title, condition, detail="", **kw) -> CheckResult:
    return CheckResult(
        id=cid,
        title=title,
        category="inputs",
        status=CheckStatus.PASS,
        condition=condition,
        detail=detail,
        **kw,
    )


def _fail(cid, title, condition, detail, **kw) -> CheckResult:
    return CheckResult(
        id=cid,
        title=title,
        category="inputs",
        status=CheckStatus.FAIL,
        condition=condition,
        detail=detail,
        **kw,
    )


def _warn(cid, title, condition, detail, **kw) -> CheckResult:
    return CheckResult(
        id=cid,
        title=title,
        category="inputs",
        status=CheckStatus.WARNING,
        condition=condition,
        detail=detail,
        **kw,
    )


def run_input_checks(
    report: QualityReport,
    *,
    spec: CastingSpec,
    calc: Optional[CalcResult] = None,
    tech: Optional[TechGeomParams] = None,
) -> None:
    calc = calc or build_koleso_casting_result()
    tech = tech or wheel_tech_geom(spec)

    # обязательные поля CastingSpec
    required = [
        "d_out",
        "d_hub",
        "d_bore",
        "h_ch",
        "n_top",
        "n_face",
        "d_riser",
        "d_neck",
        "h_riser",
        "l_print",
        "f_pit",
        "f_slag",
        "f_sprue",
        "code",
    ]
    missing = [n for n in required if getattr(spec, n, None) in (None, "")]
    if missing:
        report.add(
            _fail(
                "INP-001",
                "Обязательные параметры CastingSpec",
                "все required присутствуют и непусты",
                f"нет: {missing}",
                normative_source="внутреннее инженерное правило",
                normative_point="P1 CastingSpec / STOP_GATES G0",
            )
        )
    else:
        report.add(
            _ok(
                "INP-001",
                "Обязательные параметры CastingSpec",
                "все required присутствуют и непусты",
                normative_source="внутреннее инженерное правило",
                normative_point="P1 CastingSpec / STOP_GATES G0",
            )
        )

    # единицы: mm / cm2 зафиксированы в pipeline validate
    report.add(
        _ok(
            "INP-002",
            "Единицы измерения входного пакета",
            "geometry/allowance/riser/cores = mm; gating = cm2",
            detail="контролируется calc.validate.require_unit при pipeline",
            normative_source="внутреннее инженерное правило",
            normative_point="P1 validate.py",
        )
    )

    # provenance: каждый ключ CastingSpec key_params должен быть в provenance
    # (не все имена совпадают — проверяем критический набор)
    need_prov = [
        "D_OUT",
        "TABLE6_BASE",
        "N_TOP",
        "C_HUB",
        "D_RISER",
        "F_PIT",
        "F_SLAG",
        "L_PRINT",
        "L_PRINT_MAX",
    ]
    prov = calc.provenance
    missing_p = [k for k in need_prov if k not in prov]
    if missing_p:
        report.add(
            _fail(
                "INP-003",
                "Provenance ключевых параметров",
                "для ключевых параметров задан ParamProvenance",
                f"нет provenance: {missing_p}",
                normative_source="внутреннее инженерное правило",
                normative_point="P1 provenance / ParamKind",
            )
        )
    else:
        kinds = {k: prov[k].kind.value for k in need_prov}
        report.add(
            _ok(
                "INP-003",
                "Provenance ключевых параметров",
                "для ключевых параметров задан ParamProvenance",
                detail=str(kinds),
                normative_source="внутреннее инженерное правило",
                normative_point="P1 provenance / ParamKind",
            )
        )

    # TABLE6 calculated
    t6 = prov.get("TABLE6_BASE")
    if t6 and t6.kind == ParamKind.CALCULATED and t6.value is not None:
        report.add(
            CheckResult(
                id="INP-004",
                title="Припуск табл.6 получен lookup'ом",
                category="inputs",
                status=CheckStatus.PASS,
                condition="TABLE6_BASE kind=calculated и value не None",
                detail=f"value={t6.value}",
                normative_source="ГОСТ 26645-85",
                normative_point="табл.6 (gost_26645_table6_full.json)",
                evidence=t6.detail,
            )
        )
    else:
        report.add(
            _fail(
                "INP-004",
                "Припуск табл.6 получен lookup'ом",
                "TABLE6_BASE kind=calculated и value не None",
                "TABLE6_BASE отсутствует или не calculated",
                normative_source="ГОСТ 26645-85",
                normative_point="табл.6",
            )
        )

    # расчётные C_* vs формулы CastingSpec
    derived = spec.validate_derived()
    if derived:
        report.add(
            _fail(
                "INP-005",
                "Соответствие расчётных C_*/Y_* формулам",
                "CastingSpec.validate_derived() пуст",
                "; ".join(derived[:5]),
                normative_source="внутреннее инженерное правило",
                normative_point="CastingSpec.validate_derived / koleso_data",
            )
        )
    else:
        report.add(
            _ok(
                "INP-005",
                "Соответствие расчётных C_*/Y_* формулам",
                "CastingSpec.validate_derived() пуст",
                normative_source="внутреннее инженерное правило",
                normative_point="CastingSpec.validate_derived",
            )
        )

    # L_PRINT ≤ table max (ГОСТ 3212 через JSON)
    if calc.l_print_max_mm is not None:
        if spec.l_print - 1e-9 <= calc.l_print_max_mm:
            report.add(
                CheckResult(
                    id="INP-006",
                    title="L_PRINT ≤ l_max таблицы знаков",
                    category="inputs",
                    status=CheckStatus.PASS,
                    condition="L_PRINT ≤ L_PRINT_MAX",
                    detail=f"{spec.l_print} ≤ {calc.l_print_max_mm}",
                    normative_source="ГОСТ 3212-92",
                    normative_point="знаки гориз. / sterzhni_horiz_syroe.json (Михальцов 5.1)",
                )
            )
        else:
            report.add(
                _fail(
                    "INP-006",
                    "L_PRINT ≤ l_max таблицы знаков",
                    "L_PRINT ≤ L_PRINT_MAX",
                    f"{spec.l_print} > {calc.l_print_max_mm}",
                    normative_source="ГОСТ 3212-92",
                    normative_point="sterzhni_horiz_syroe.json",
                )
            )
    else:
        report.add(
            CheckResult(
                id="INP-006",
                title="L_PRINT ≤ l_max таблицы знаков",
                category="inputs",
                status=CheckStatus.NOT_CHECKED,
                condition="L_PRINT ≤ L_PRINT_MAX",
                detail="l_print_max не вычислен pipeline",
                normative_source="ГОСТ 3212-92",
                normative_point="sterzhni_horiz_syroe.json",
            )
        )

    # неподтверждённые допущения TechGeom
    for note in tech.notes:
        report.assumptions.append(note)
    if tech.blades and not tech.blades.is_hydraulic_profile:
        report.assumptions.append(
            f"Лопатки: призмы t={tech.blades.thickness_mm} мм; "
            f"{tech.blades.provenance}"
        )
        report.add(
            _warn(
                "INP-007",
                "Профиль лопаток не гидравлический",
                "is_hydraulic_profile == True при наличии шаблона",
                "шаблон отсутствует — используются призмы (P3)",
                normative_source="внутреннее инженерное правило",
                normative_point="P3 TechGeomParams / kolesa_nasosy.md (профиль по шаблону)",
            )
        )
    else:
        report.add(
            _ok(
                "INP-007",
                "Профиль лопаток",
                "гидравлический профиль задан либо лопаток нет",
                normative_source="внутреннее инженерное правило",
            )
        )

    # INP-008: вертикальный нижний знак Ст.2 vs табл.7 (P4.5.1 check-only)
    import json as _json

    vert = getattr(calc, "vert_print_check", None)
    if not isinstance(vert, dict):
        report.add(
            CheckResult(
                id="INP-008",
                title="Вертикальный знак H_PRINT2 (Ст.2)",
                category="inputs",
                status=CheckStatus.NOT_CHECKED,
                condition="H_PRINT2 ≤ h_max(D,L) по ГОСТ 3212-92 табл.7",
                detail="vert_print_check отсутствует в CalcResult",
                normative_source="ГОСТ 3212-92",
                normative_point="п.2.3 табл.7; п.2.3.3",
            )
        )
    else:
        st = vert.get("status") or "NOT_CHECKED"
        evidence = _json.dumps(vert, ensure_ascii=False)
        title = "Вертикальный знак H_PRINT2 (Ст.2, табл.7)"
        cond = "H_PRINT2 ≤ h_max(D_Ст.2, L_Ст.2); верхний знак — п.2.3.3 при наличии"
        if st == "PASS":
            report.add(
                _ok(
                    "INP-008",
                    title,
                    cond,
                    vert.get("detail") or "",
                    normative_source="ГОСТ 3212-92",
                    normative_point="п.2.3 табл.7 (не более)",
                    evidence=evidence,
                )
            )
        elif st == "WARNING":
            report.add(
                _warn(
                    "INP-008",
                    title,
                    cond,
                    vert.get("detail") or "",
                    normative_source="ГОСТ 3212-92",
                    normative_point="п.2.3 табл.7 (не более)",
                    evidence=evidence,
                )
            )
            report.assumptions.append(
                "H_PRINT2 engineer; превышение h_max табл.7 — геометрия не менялась"
            )
        else:
            report.add(
                CheckResult(
                    id="INP-008",
                    title=title,
                    category="inputs",
                    status=CheckStatus.NOT_CHECKED,
                    condition=cond,
                    detail=vert.get("detail") or "lookup/параметры недостаточны",
                    normative_source="ГОСТ 3212-92",
                    normative_point="п.2.3 табл.7; ячейка unavailable/unverified → NOT_CHECKED",
                    evidence=evidence,
                )
            )
            report.assumptions.append(
                "INP-008 NOT_CHECKED: нет достоверного h_max для (D,L) Ст.2 "
                "или отсутствует параметр (P4.5.1)"
            )

    # INP-009a/b/c: числовое сравнение N_* vs TABLE6_BASE (P4.1).
    # Направление «N < base → замечание» — внутреннее правило pipeline; НЕ выдаём за подтверждённый ГОСТ.
    # PASS по «N >= base = соответствует ГОСТ» запрещён, пока текст ГОСТ 26645 табл.6 не в knowledge.
    t6 = prov.get("TABLE6_BASE")
    base = float(t6.value) if t6 and t6.value is not None else None
    for cid, pname in (
        ("INP-009a", "N_TOP"),
        ("INP-009b", "N_BOT"),
        ("INP-009c", "N_FACE"),
    ):
        p = prov.get(pname)
        if p is None or base is None:
            report.add(
                CheckResult(
                    id=cid,
                    title=f"Числовое сравнение {pname} vs TABLE6_BASE",
                    category="inputs",
                    status=CheckStatus.NOT_CHECKED,
                    condition="есть provenance параметра и TABLE6_BASE",
                    detail=f"{pname} или TABLE6_BASE отсутствует",
                    normative_source="внутреннее инженерное правило",
                    normative_point="P4.1 / pipeline; направление vs ГОСТ 26645 табл.6 не подтверждено",
                )
            )
            continue
        val = float(p.value)
        lt = val + 1e-9 < base
        evidence = (
            f"accepted={val} {p.unit}; TABLE6_BASE={base} mm; "
            f"relation={'<' if lt else '>='}; "
            f"provenance={{kind={p.kind.value}, source={p.source!r}, detail={p.detail!r}, "
            f"doc_ref={p.doc_ref!r}}}; "
            f"comparison_basis=внутреннее правило pipeline (val < TABLE6_BASE → сигнал); "
            f"gost_direction=unconfirmed_in_knowledge"
        )
        if lt:
            # совпадает с pipeline warning; значения N_* не меняем
            report.add(
                CheckResult(
                    id=cid,
                    title=f"Числовое сравнение {pname} vs TABLE6_BASE",
                    category="inputs",
                    status=CheckStatus.WARNING,
                    condition="зафиксировать accepted vs TABLE6_BASE (мм); без нормативного PASS/FAIL",
                    detail=(
                        f"{pname}={val} mm < TABLE6_BASE={base} mm — сигнал pipeline; "
                        f"не подтверждено как требование ГОСТ 26645-85 в knowledge"
                    ),
                    evidence=evidence,
                    normative_source="внутреннее инженерное правило",
                    normative_point=(
                        "pipeline N_* vs табл.6 base; "
                        "ГОСТ 26645-85 табл.6 — lookup значения base, направление сравнения не подтверждено"
                    ),
                )
            )
        else:
            # N_TOP=6 >= 5.2: числовой факт есть, но PASS «по ГОСТ» запрещён
            report.add(
                CheckResult(
                    id=cid,
                    title=f"Числовое сравнение {pname} vs TABLE6_BASE",
                    category="inputs",
                    status=CheckStatus.NOT_CHECKED,
                    condition=(
                        f"нормативное соответствие {pname} табл.6 подтверждено текстом ГОСТ в knowledge"
                    ),
                    detail=(
                        f"{pname}={val} mm >= TABLE6_BASE={base} mm (числовой факт); "
                        f"нормативное PASS не выставляется — направление сравнения не подтверждено"
                    ),
                    evidence=evidence,
                    normative_source="внутреннее инженерное правило",
                    normative_point=(
                        "P4.1: разделение числового факта и нормативного подтверждения; "
                        "не выдавать pipeline за ГОСТ"
                    ),
                )
            )

    # прочие pipeline warnings (не N_TOP/BOT/FACE) — отдельно, без смешения
    n_prefix = ("N_TOP=", "N_BOT=", "N_FACE=")
    other_w = [w for w in (calc.warnings or []) if not any(w.startswith(p) for p in n_prefix)]
    for w in calc.warnings or []:
        if w not in report.warnings:
            report.warnings.append(w)
    if other_w:
        report.add(
            _warn(
                "INP-009x",
                "Прочие предупреждения calc.pipeline",
                "не N_TOP/N_BOT/N_FACE",
                "; ".join(other_w),
                normative_source="внутреннее инженерное правило",
                normative_point="P4.1 / CalcResult.warnings",
            )
        )
