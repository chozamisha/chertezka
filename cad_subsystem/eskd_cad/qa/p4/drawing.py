# -*- coding: utf-8 -*-
"""P4 задача 3–4: контроль чертежа (+ P4.1/P4.3 эвристики)."""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from ...geom.view_types import ViewResult
from ...model.document import DrawingDocument
from ...model.entities import (
    DimLinear,
    Hatch,
    Leader,
    Line,
    MText,
    Polyline,
    Text,
)
from ...spec.casting_spec import CastingSpec
from ..geometry_check import check_document
from .datum_detect import datum_check_payload
from .dim_map import build_dim_map
from .duplicate_lines import classify_duplicate_lines, summarize_duplicates
from .status import CheckResult, CheckStatus, QualityReport
from .view_layout import ViewLayout, wheel_view_layouts


def _blob(doc: DrawingDocument) -> str:
    parts: List[str] = []
    for e in doc.entities:
        if isinstance(e, Text):
            parts.append(e.content)
        elif isinstance(e, MText):
            parts.append(e.content)
        elif isinstance(e, Leader):
            parts.append(e.text)
        elif isinstance(e, DimLinear) and e.text:
            parts.append(e.text)
    return "\n".join(parts)


def run_drawing_checks(
    report: QualityReport,
    *,
    doc: DrawingDocument,
    spec: CastingSpec,
    views: Optional[Dict[str, ViewResult]] = None,
    view_layouts: Optional[Dict[str, ViewLayout]] = None,
) -> None:
    blob = _blob(doc)
    layouts = view_layouts if view_layouts is not None else wheel_view_layouts(spec)
    layers = {getattr(e, "layer", "0") for e in doc.entities}
    n_hatch = sum(1 for e in doc.entities if isinstance(e, Hatch))
    n_dim = sum(1 for e in doc.entities if isinstance(e, DimLinear))
    n_leader = sum(1 for e in doc.entities if isinstance(e, Leader))
    n_poly = sum(1 for e in doc.entities if isinstance(e, Polyline))
    n_line = sum(1 for e in doc.entities if isinstance(e, Line))

    # DRW-001 виды / сечения по подписям (ГОСТ 2.305 — наличие обозначений разрезов)
    has_aa = "А-А" in blob or "A-A" in blob
    has_bb = "В-В" in blob or "B-B" in blob
    has_local = "Б-Б" in blob
    if has_aa and has_bb:
        report.add(
            CheckResult(
                id="DRW-001",
                title="Обозначения разрезов А-А и В-В",
                category="drawing",
                status=CheckStatus.PASS,
                condition="в тексте есть «А-А» и «В-В»",
                normative_source="ГОСТ 2.305",
                normative_point="обозначение разрезов (см. annotations/cutting_plane.py)",
            )
        )
    else:
        report.add(
            CheckResult(
                id="DRW-001",
                title="Обозначения разрезов А-А и В-В",
                category="drawing",
                status=CheckStatus.FAIL,
                condition="в тексте есть «А-А» и «В-В»",
                detail=f"А-А={has_aa} В-В={has_bb}",
                normative_source="ГОСТ 2.305",
            )
        )

    report.add(
        CheckResult(
            id="DRW-002",
            title="Местный разрез Б-Б",
            category="drawing",
            status=CheckStatus.PASS if has_local else CheckStatus.FAIL,
            condition="в тексте есть «Б-Б»",
            detail=f"present={has_local}",
            normative_source="ГОСТ 2.305",
            normative_point="местные разрезы / выносные элементы",
        )
    )

    # оси
    has_axis = any(getattr(e, "layer", "") == "Осевая" for e in doc.entities)
    report.add(
        CheckResult(
            id="DRW-003",
            title="Осевые линии",
            category="drawing",
            status=CheckStatus.PASS if has_axis else CheckStatus.FAIL,
            condition="есть объекты на слое «Осевая»",
            normative_source="ГОСТ 2.303",
            normative_point="штрихпунктирная / осевая (тип линии CENTER в экспорте)",
        )
    )

    # базы — структурный кластер add_datum (P4.3); секущие исключены
    datum_payload = datum_check_payload(doc)
    full_n = int(datum_payload["full_count"])
    if full_n >= 1:
        report.add(
            CheckResult(
                id="DRW-004",
                title="Обозначение баз",
                category="drawing",
                status=CheckStatus.PASS,
                condition="полный кластер add_datum (box+shelf+triangle+letter)",
                detail=(
                    f"letters={datum_payload['letters']}; "
                    f"partial={len(datum_payload.get('partial_clusters') or [])}; "
                    f"excluded_cutting={len(datum_payload.get('excluded_cutting_letters') or [])}"
                ),
                evidence=json.dumps(datum_payload, ensure_ascii=False),
                normative_source="ГОСТ 2.308",
                normative_point="annotations/datums.py эталон; P4.3 структурный кластер",
            )
        )
    else:
        report.add(
            CheckResult(
                id="DRW-004",
                title="Обозначение баз",
                category="drawing",
                status=CheckStatus.NOT_CHECKED,
                condition="полный кластер add_datum (box+shelf+triangle+letter)",
                detail=(
                    "полный кластер не распознан; "
                    "буквы секущих/штампа не считаются базами (P4.3)"
                ),
                evidence=json.dumps(datum_payload, ensure_ascii=False),
                normative_source="ГОСТ 2.308",
                normative_point="P4.3: NOT_CHECKED при отсутствии полного кластера",
            )
        )

    # согласованность ключевых размеров на листе с CastingSpec
    need_dims = [
        f"⌀{int(spec.c_out)}",
        f"⌀{int(spec.d_riser)}",
        f"{int(spec.h_body)}",
        f"{int(spec.l_print)}",
    ]
    # %%c может быть в DXF, в сцене обычно ⌀
    missing_dims = [d for d in need_dims if d not in blob and d.replace("⌀", "") not in blob]
    # h_body as bare number might false-positive; require at least OD and L_PRINT
    critical = [f"⌀{int(spec.c_out)}", f"{int(spec.l_print)}"]
    miss_c = [d for d in critical if d not in blob]
    if not miss_c:
        status = CheckStatus.PASS if not missing_dims else CheckStatus.WARNING
        report.add(
            CheckResult(
                id="DRW-005",
                title="Согласованность размеров с CastingSpec",
                category="drawing",
                status=status,
                condition="на листе есть ⌀C_OUT, L_PRINT (и желательно прибыль/H_BODY)",
                detail=f"missing_optional={missing_dims}" if missing_dims else "ok",
                normative_source="ГОСТ 2.307",
                normative_point="простановка размеров; значения — из CastingSpec (P1)",
            )
        )
    else:
        report.add(
            CheckResult(
                id="DRW-005",
                title="Согласованность размеров с CastingSpec",
                category="drawing",
                status=CheckStatus.FAIL,
                condition="на листе есть ⌀C_OUT и L_PRINT",
                detail=f"нет: {miss_c}",
                normative_source="ГОСТ 2.307",
            )
        )

    # дубли — HLR только при match ViewResult×ViewTransform (P4.3)
    dup_groups = classify_duplicate_lines(
        doc, views=views, view_layouts=layouts
    )
    dup_summary = summarize_duplicates(dup_groups)
    drawing_dups = [g for g in dup_groups if g.classification == "drawing_duplicate"]
    ambiguous = [g for g in dup_groups if g.classification == "ambiguous_same_geom"]
    hlr_ok = [g for g in dup_groups if g.classification == "hlr_coincident"]
    if drawing_dups or ambiguous:
        report.add(
            CheckResult(
                id="DRW-006",
                title="Дублирующиеся отрезки",
                category="drawing",
                status=CheckStatus.WARNING,
                condition=(
                    "нет drawing_duplicate / ambiguous; "
                    "hlr_coincident только при подтверждённом HLR-match"
                ),
                detail=(
                    f"drawing_duplicate={len(drawing_dups)} ambiguous={len(ambiguous)} "
                    f"hlr_coincident={len(hlr_ok)} total_groups={dup_summary['total_groups']}"
                ),
                evidence=json.dumps(dup_summary, ensure_ascii=False),
                normative_source="внутреннее инженерное правило",
                normative_point="P4.3 HLR-match after ViewTransform",
            )
        )
    else:
        report.add(
            CheckResult(
                id="DRW-006",
                title="Дублирующиеся отрезки",
                category="drawing",
                status=CheckStatus.PASS,
                condition=(
                    "нет drawing_duplicate / ambiguous; "
                    "hlr_coincident только при подтверждённом HLR-match"
                ),
                detail=(
                    f"hlr_coincident={len(hlr_ok)} total_groups={dup_summary['total_groups']} "
                    f"(геометрия не удалялась)"
                ),
                evidence=json.dumps(dup_summary, ensure_ascii=False),
                normative_source="внутреннее инженерное правило",
                normative_point="P4.3 HLR-match after ViewTransform",
            )
        )

    # штриховка сечений
    report.add(
        CheckResult(
            id="DRW-007",
            title="Штриховка сечений",
            category="drawing",
            status=CheckStatus.PASS if n_hatch >= 1 else CheckStatus.FAIL,
            condition="Hatch ≥ 1 на сечениях",
            detail=f"hatch={n_hatch}",
            normative_source="ГОСТ 2.306",
            normative_point="графическое обозначение материалов (штриховка); факт наличия",
        )
    )

    # технологические обозначения
    tech_marks = ["Ст.", "Прибыль", "Хол.", "МФ", "питатель", "стояк", "шлак"]
    found = [m for m in tech_marks if m.lower() in blob.lower() or m in blob]
    report.add(
        CheckResult(
            id="DRW-008",
            title="Технологические обозначения",
            category="drawing",
            status=CheckStatus.PASS if len(found) >= 3 else CheckStatus.WARNING,
            condition="есть подписи стержней/прибыли/хол./ЛС/МФ",
            detail=f"найдено={found}",
            normative_source="ГОСТ 3.1125-88",
            normative_point="элементы литейной формы на чертеже отливки (gost_cards)",
        )
    )

    # основная надпись
    has_stamp = "Штамп" in layers or "Разраб" in blob or spec.code in blob
    report.add(
        CheckResult(
            id="DRW-009",
            title="Основная надпись",
            category="drawing",
            status=CheckStatus.PASS if has_stamp and spec.code in blob else CheckStatus.FAIL,
            condition="штамп/код присутствуют на листе",
            detail=f"code_in_blob={spec.code in blob}",
            normative_source="ГОСТ 2.104",
            normative_point="основная надпись форма 1",
        )
    )

    # ТТ
    has_tt = "Технические требования" in blob
    has_gost_tt = "26645" in blob or "3212" in blob
    report.add(
        CheckResult(
            id="DRW-010",
            title="Технические требования",
            category="drawing",
            status=CheckStatus.PASS if has_tt and has_gost_tt else CheckStatus.FAIL,
            condition="блок ТТ + ссылки на 26645/3212",
            detail=f"TT={has_tt} gost_refs={has_gost_tt}",
            normative_source="ГОСТ 26645-85 / ГОСТ 3212-92",
            normative_point="указание в ТТ точности и уклонов (учебная практика / calc.md)",
        )
    )

    # слои ЕСКД
    need_layers = {"Основная", "Тонкая", "Осевая", "Размеры", "Штриховка", "Текст"}
    missing_l = sorted(need_layers - layers)
    report.add(
        CheckResult(
            id="DRW-011",
            title="Слои по типам линий",
            category="drawing",
            status=CheckStatus.PASS if not missing_l else CheckStatus.FAIL,
            condition=f"слои ⊇ {sorted(need_layers)}",
            detail=f"missing={missing_l}",
            normative_source="ГОСТ 2.303",
            normative_point="типы линий; имена слоёв проекта eskd_cad",
        )
    )

    # припуск тонкой — ГОСТ 3.1125
    has_allow = any(getattr(e, "layer", "") == "Припуск" for e in doc.entities)
    report.add(
        CheckResult(
            id="DRW-012",
            title="Контур детали / припуск тонкой линией",
            category="drawing",
            status=CheckStatus.PASS if has_allow else CheckStatus.WARNING,
            condition="есть объекты на слое «Припуск»",
            normative_source="ГОСТ 3.1125-88",
            normative_point="припуски сплошной тонкой линией (gost_cards)",
        )
    )

    # формат
    report.add(
        CheckResult(
            id="DRW-013",
            title="Формат листа",
            category="drawing",
            status=CheckStatus.PASS if spec.fmt in {"A4", "A3", "A2", "A1"} else CheckStatus.FAIL,
            condition="fmt ∈ {A4,A3,A2,A1}",
            detail=f"fmt={spec.fmt} scale=1:{spec.scale_k}",
            normative_source="ГОСТ 2.301 / ГОСТ 2.302",
            normative_point="форматы; масштабы (учебный 1:5 для колеса — calc §5)",
        )
    )

    # геометрия сцены (не только счётчик)
    geom_issues = check_document(doc)
    report.add(
        CheckResult(
            id="DRW-014",
            title="Валидность примитивов сцены",
            category="drawing",
            status=CheckStatus.PASS if not geom_issues else CheckStatus.FAIL,
            condition="check_document без issues (полигоны/длины/рамка)",
            detail=str(geom_issues[:3]) if geom_issues else "ok",
            normative_source="внутреннее инженерное правило",
            normative_point="qa/geometry_check.py",
        )
    )

    # плотность контуров — информативно, не PASS по счёту
    report.add(
        CheckResult(
            id="DRW-015",
            title="Наличие векторных контуров видов",
            category="drawing",
            status=CheckStatus.PASS if (n_poly + n_line) >= 10 else CheckStatus.FAIL,
            condition="полилинии+линии ≥ 10 (индикатор наличия геометрии, не замена инженерной QA)",
            detail=f"polylines={n_poly} lines={n_line} dims={n_dim} leaders={n_leader}",
            normative_source="внутреннее инженерное правило",
            normative_point="не ГОСТ; дополняет GEO-*",
        )
    )

    # условная геометрия на листе (из P3)
    report.conditional_geometry.extend(
        [
            "Слой «Припуск» — оформление, не OCP offset",
            "2D-схема знаков/ЛС на плане может дублировать OCP-тела (P3)",
            "Выноски/МФ — аннотации",
        ]
    )

    # DRW-016: карта feature (P4.3 measure_kind); агрегат всегда NOT_CHECKED
    dim_map = build_dim_map(
        doc=doc, spec=spec, views=views, view_layouts=layouts
    )
    report.add(
        CheckResult(
            id="DRW-016",
            title="Привязка DIMENSION к геометрии (карта feature)",
            category="drawing",
            status=CheckStatus.NOT_CHECKED,
            condition=(
                "каждый DimLinear ассоциирован с ребром OCP; "
                "до этого агрегат = NOT_CHECKED даже при PASS стартовых строк"
            ),
            detail=dim_map.aggregate_reason
            + f"; rows={dim_map.as_dict()['row_status_counts']}",
            evidence=json.dumps(dim_map.as_dict(), ensure_ascii=False),
            normative_source="ГОСТ 2.307",
            normative_point="P4.3 dim_map measure_kind; association↔ребро — gap",
        )
    )
