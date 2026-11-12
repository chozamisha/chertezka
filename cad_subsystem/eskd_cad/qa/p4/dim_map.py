# -*- coding: utf-8 -*-
"""P4.3 DRW-016: карта feature с measure_kind и привязкой к окну вида.

Агрегат всегда NOT_CHECKED до association DIMENSION↔ребро OCP.
sheet_span ≠ OCP-проверка.
Scale только из ViewLayout.k (ViewTransform) — без перебора.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ...geom.view_types import ViewResult
from ...model.document import DrawingDocument
from ...model.entities import DimLinear
from ...spec.casting_spec import CastingSpec
from .status import CheckStatus
from .view_layout import ViewLayout

Point = Tuple[float, float]


@dataclass
class FeatureDimRow:
    feature_id: str
    casting_param: str
    casting_value: float
    ocp_geometry: str
    drawing_view: str
    dxf_dimension_text: Optional[str]
    measured_value: Optional[float]
    tolerance: float
    verification_status: str
    measure_kind: str  # ocp_bbox | ocp_section | sheet_span | unavailable
    view_id: Optional[str] = None
    k: Optional[float] = None
    sheet_span: Optional[float] = None
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DimMapReport:
    rows: List[FeatureDimRow] = field(default_factory=list)
    aggregate_status: str = CheckStatus.NOT_CHECKED.value
    aggregate_reason: str = (
        "полная ассоциация DIMENSION↔ребро OCP не реализована; "
        "агрегат DRW-016 = NOT_CHECKED даже при PASS всех стартовых строк"
    )

    def as_dict(self) -> Dict[str, Any]:
        c: Dict[str, int] = {}
        for r in self.rows:
            c[r.verification_status] = c.get(r.verification_status, 0) + 1
        return {
            "rows": [r.as_dict() for r in self.rows],
            "aggregate_status": self.aggregate_status,
            "aggregate_reason": self.aggregate_reason,
            "row_status_counts": c,
        }


def _parse_dim_number(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"[\d]+(?:[.,][\d]+)?", text.replace(",", "."))
    return float(m.group(0)) if m else None


def _span(p1: Point, p2: Point) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _bbox_w(views: Optional[Dict[str, ViewResult]], key: str) -> Optional[float]:
    if not views or key not in views:
        return None
    bb = views[key].bbox()
    return None if not bb else float(bb[2] - bb[0])


def _bind_dim_to_view(
    dim: DimLinear, layouts: Dict[str, ViewLayout]
) -> Optional[ViewLayout]:
    """Однозначная привязка mid → окно вида. 0 или >1 → None (NOT_CHECKED)."""
    mid = ((dim.p1[0] + dim.p2[0]) / 2.0, (dim.p1[1] + dim.p2[1]) / 2.0)
    hits = [L for L in layouts.values() if L.contains(mid[0], mid[1])]
    if len(hits) == 1:
        return hits[0]
    return None


def _find_dims_for_text(dims: List[DimLinear], want_text: str) -> List[DimLinear]:
    return [d for d in dims if d.text == want_text]


def build_dim_map(
    *,
    doc: DrawingDocument,
    spec: CastingSpec,
    views: Optional[Dict[str, ViewResult]] = None,
    view_layouts: Optional[Dict[str, ViewLayout]] = None,
) -> DimMapReport:
    dims = [e for e in doc.entities if isinstance(e, DimLinear)]
    layouts = view_layouts or {}
    aa_w = _bbox_w(views, "AA")
    lbb_w = _bbox_w(views, "local_BB")

    # feature_id, param, value, ocp_note, preferred_view, want_text, ocp_measure, tol
    specs: List[Tuple[str, str, float, str, str, str, Optional[float], float]] = [
        (
            "rim_od",
            "C_OUT",
            float(spec.c_out),
            # P4.3.1 A7: не утверждать, что это изолированный наружный обод
            "AA section ViewResult.bbox() width (полный габарит сечения, "
            "не изолированный solid наружного обода; ≠ dim↔edge)",
            "AA",
            f"⌀{int(spec.c_out)}",
            aa_w,
            5.0,
        ),
        (
            "boss_od",
            "C_BOSS",
            float(spec.c_boss),
            "нет изолированного OCP bbox бобышки",
            "AA",
            f"⌀{int(spec.c_boss)}",
            None,
            2.0,
        ),
        (
            "hub_od",
            "C_HUB",
            float(spec.c_hub),
            "нет изолированного OCP bbox ступицы",
            "AA",
            f"⌀{int(spec.c_hub)}",
            None,
            2.0,
        ),
        (
            "body_height",
            "H_BODY",
            float(spec.h_body),
            "AA bbox height включает прибыль ≠ H_BODY",
            "AA",
            f"{int(spec.h_body)}",
            None,
            2.0,
        ),
        (
            "riser_od",
            "D_RISER",
            float(spec.d_riser),
            "нет изолированного OCP bbox прибыли",
            "AA",
            f"⌀{int(spec.d_riser)}",
            None,
            2.0,
        ),
        (
            "riser_height",
            "H_RISER",
            float(spec.h_riser),
            "нет изолированного OCP measure высоты прибыли",
            "AA",
            f"{int(spec.h_riser)}",
            None,
            2.0,
        ),
        (
            "channel_height",
            "C_H_CH",
            float(spec.c_h_ch),
            "нет изолированного OCP measure канала",
            "AA",
            f"{int(spec.c_h_ch)}",
            None,
            2.0,
        ),
        (
            "print_length",
            "L_PRINT",
            float(spec.l_print),
            f"local_BB bbox_width={lbb_w} (включает rim; не равен L_PRINT)",
            "local_BB",
            f"{int(spec.l_print)}",
            None,
            2.0,
        ),
    ]

    rows: List[FeatureDimRow] = []
    for feature_id, param, value, ocp_note, pref_view, want_text, ocp_m, tol in specs:
        cands = _find_dims_for_text(dims, want_text)
        text_ok_any = any(
            (_parse_dim_number(d.text) is not None)
            and abs(_parse_dim_number(d.text) - value) <= tol
            for d in cands
        )

        # выбрать размер, однозначно лежащий в preferred view window
        dim: Optional[DimLinear] = None
        layout: Optional[ViewLayout] = None
        if not layouts:
            rows.append(
                FeatureDimRow(
                    feature_id=feature_id,
                    casting_param=param,
                    casting_value=value,
                    ocp_geometry=ocp_note,
                    drawing_view=pref_view,
                    dxf_dimension_text=cands[0].text if cands else None,
                    measured_value=None,
                    tolerance=tol,
                    verification_status=CheckStatus.NOT_CHECKED.value,
                    measure_kind="unavailable",
                    detail="нет view_layouts — scale/вид недоступны (без угадывания)",
                )
            )
            continue

        pref_layout = layouts.get(pref_view)
        matched: List[Tuple[DimLinear, ViewLayout]] = []
        for d in cands:
            L = _bind_dim_to_view(d, layouts)
            if L is None:
                continue
            if pref_layout and L.view_id != pref_view:
                continue
            matched.append((d, L))

        if len(matched) == 1:
            dim, layout = matched[0]
        elif len(matched) > 1:
            rows.append(
                FeatureDimRow(
                    feature_id=feature_id,
                    casting_param=param,
                    casting_value=value,
                    ocp_geometry=ocp_note,
                    drawing_view=pref_view,
                    dxf_dimension_text=want_text,
                    measured_value=None,
                    tolerance=tol,
                    verification_status=CheckStatus.NOT_CHECKED.value,
                    measure_kind="unavailable",
                    detail="несколько DimLinear в окне вида — неоднозначно",
                )
            )
            continue
        else:
            # нет однозначной привязки к preferred view
            # проверить, есть ли dim с неоднозначным окном
            ambiguous = False
            for d in cands:
                mid = ((d.p1[0] + d.p2[0]) / 2.0, (d.p1[1] + d.p2[1]) / 2.0)
                hits = [L for L in layouts.values() if L.contains(mid[0], mid[1])]
                if len(hits) != 1:
                    ambiguous = True
            rows.append(
                FeatureDimRow(
                    feature_id=feature_id,
                    casting_param=param,
                    casting_value=value,
                    ocp_geometry=ocp_note,
                    drawing_view=pref_view,
                    dxf_dimension_text=cands[0].text if cands else None,
                    measured_value=None,
                    tolerance=tol,
                    verification_status=CheckStatus.NOT_CHECKED.value,
                    measure_kind="unavailable",
                    detail=(
                        "неоднозначная или отсутствующая привязка DimLinear к окну вида; "
                        "ближайший вид не выбирается; scale не угадывается"
                        + ("; ambiguous_windows" if ambiguous else "")
                    ),
                )
            )
            continue

        assert dim is not None and layout is not None
        k = float(layout.k)
        sheet_span = _span(dim.p1, dim.p2)
        measured_sheet = sheet_span * k
        text_val = _parse_dim_number(dim.text)
        text_ok = text_val is not None and abs(text_val - value) <= tol
        ocp_ok = ocp_m is not None and abs(ocp_m - value) <= tol
        span_ok = abs(measured_sheet - value) <= tol

        parts = [
            f"view_id={layout.view_id}",
            f"k={k}",
            f"sheet_span={sheet_span:.4f}",
            f"sheet_span×k={measured_sheet:.4f}",
            f"dxf_text={dim.text!r}",
        ]
        if ocp_m is not None:
            parts.append(f"ocp_bbox={ocp_m:.4f}")

        if ocp_ok and (span_ok or text_ok):
            status = CheckStatus.PASS.value
            measure_kind = "ocp_bbox"
            measured = ocp_m
            if feature_id == "rim_od":
                parts.append(
                    "OCP AA section bbox width ≈ CastingSpec.C_OUT; "
                    "это НЕ доказательство изолированного обода / dim↔edge "
                    "(P4.3.1 A7 limitation)"
                )
            else:
                parts.append(
                    "OCP bbox согласован с CastingSpec (не путать с sheet_span)"
                )
            if span_ok:
                parts.append("sheet_span×k также согласован (аннотация листа)")
        elif span_ok and text_ok:
            status = CheckStatus.PASS.value
            measure_kind = "sheet_span"
            measured = measured_sheet
            parts.append(
                "PASS только как геометрия размерной аннотации листа "
                "(measure_kind=sheet_span; НЕ OCP-проверка)"
            )
        elif span_ok and not text_ok:
            status = CheckStatus.WARNING.value
            measure_kind = "sheet_span"
            measured = measured_sheet
            parts.append("sheet_span×k ≈ CastingSpec, подпись не совпала")
        elif text_ok and not span_ok and not ocp_ok:
            status = CheckStatus.NOT_CHECKED.value
            measure_kind = "unavailable"
            measured = None
            parts.append("только текст == CastingSpec — недостаточно для PASS")
        elif ocp_m is not None and not ocp_ok:
            status = CheckStatus.FAIL.value
            measure_kind = "ocp_bbox"
            measured = ocp_m
            parts.append("OCP bbox противоречит CastingSpec")
        elif not span_ok and not text_ok:
            status = CheckStatus.FAIL.value
            measure_kind = "sheet_span"
            measured = measured_sheet
            parts.append("аннотация листа не согласована с CastingSpec")
        else:
            status = CheckStatus.NOT_CHECKED.value
            measure_kind = "unavailable"
            measured = None
            parts.append("неполная цепочка")

        rows.append(
            FeatureDimRow(
                feature_id=feature_id,
                casting_param=param,
                casting_value=value,
                ocp_geometry=ocp_note,
                drawing_view=layout.view_id,
                dxf_dimension_text=dim.text,
                measured_value=measured,
                tolerance=tol,
                verification_status=status,
                measure_kind=measure_kind,
                view_id=layout.view_id,
                k=k,
                sheet_span=sheet_span,
                detail="; ".join(parts),
            )
        )

    report = DimMapReport(rows=rows)
    report.aggregate_status = CheckStatus.NOT_CHECKED.value
    if any(r.verification_status == CheckStatus.FAIL.value for r in rows):
        report.aggregate_reason += "; присутствуют FAIL в feature-строках"
    return report
