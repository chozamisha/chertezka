# -*- coding: utf-8 -*-
"""Геометрическая проверка проекций/сечений (ViewResult), не визуальная."""
from __future__ import annotations

from typing import List, Optional, Tuple

from .view_types import CurveKind, ViewResult


def check_view_result(
    view: ViewResult,
    *,
    require_operation: Optional[str] = None,
    min_curves: int = 1,
    expect_kinds: Optional[Tuple[CurveKind, ...]] = None,
    bbox_min_span: float = 1.0,
) -> List[str]:
    issues: List[str] = []
    if view.engine != "ocp8":
        issues.append(f"{view.name}: engine={view.engine!r}, ожидается ocp8")
    if not view.meta.get("real_ocp", False):
        issues.append(f"{view.name}: meta.real_ocp не True — нельзя считать реальной OCP-операцией")
    if require_operation and view.operation != require_operation:
        issues.append(
            f"{view.name}: operation={view.operation!r}, ожидается {require_operation!r}"
        )
    if len(view.curves) < min_curves:
        issues.append(f"{view.name}: слишком мало кривых ({len(view.curves)} < {min_curves})")

    for i, c in enumerate(view.curves):
        if len(c.points) < 2:
            issues.append(f"{view.name}/curve[{i}]: <2 точек")
            continue
        # нулевая длина
        length = 0.0
        for (x0, y0), (x1, y1) in zip(c.points, c.points[1:]):
            length += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        if length < 1e-9:
            issues.append(f"{view.name}/curve[{i}]: нулевая длина")

    bb = view.bbox()
    if bb is None:
        issues.append(f"{view.name}: пустой bbox")
    else:
        span = max(bb[2] - bb[0], bb[3] - bb[1])
        if span < bbox_min_span:
            issues.append(f"{view.name}: bbox span {span} < {bbox_min_span}")

    if expect_kinds:
        present = {c.kind for c in view.curves}
        for k in expect_kinds:
            if k not in present:
                issues.append(f"{view.name}: нет кривых kind={k.value}")

    # сечение не должно быть пустым при plane_section
    if view.operation == "plane_section":
        n_sec = len(view.curves_of(CurveKind.SECTION))
        if n_sec < 1:
            issues.append(f"{view.name}: plane_section без section-кривых")

    if view.operation == "hlr_projection":
        n_vis = len(view.curves_of(CurveKind.VISIBLE)) + len(view.curves_of(CurveKind.OUTLINE))
        if n_vis < 1:
            issues.append(f"{view.name}: HLR без visible/outline")

    return issues
