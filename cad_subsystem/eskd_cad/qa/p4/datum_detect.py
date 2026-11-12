# -*- coding: utf-8 -*-
"""P4.3 DRW-004: детектор баз — структура poly + локальный кластер (не bbox-only).

Эталон: annotations/datums.add_datum — НЕ изменяется.
Исключение букв секущих: annotations/cutting_plane (слой «Сечение»).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ...model.document import DrawingDocument
from ...model.entities import LAYER_TEXT, LAYER_THIN, Line, Polyline, Text

Point = Tuple[float, float]


@dataclass
class PolyClass:
    kind: str  # box | datum_triangle | other
    poly: Polyline
    tip: Optional[Point] = None
    apex: Optional[Point] = None  # a in add_datum
    center: Optional[Point] = None


@dataclass
class DatumCluster:
    letter: str
    confidence: str  # full_pattern | partial
    text_pos: Point
    box_center: Point
    triangle_tip: Optional[Point]
    shelf_ok: bool
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExcludedLetter:
    letter: str
    position: Point
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DatumDetectReport:
    full_clusters: List[DatumCluster] = field(default_factory=list)
    partial_clusters: List[DatumCluster] = field(default_factory=list)
    excluded_cutting_letters: List[ExcludedLetter] = field(default_factory=list)
    excluded_other: List[ExcludedLetter] = field(default_factory=list)

    @property
    def full_count(self) -> int:
        return len(self.full_clusters)

    @property
    def letters(self) -> List[str]:
        return sorted({c.letter for c in self.full_clusters})

    def as_dict(self) -> Dict[str, Any]:
        return {
            "full_clusters": [c.as_dict() for c in self.full_clusters],
            "partial_clusters": [c.as_dict() for c in self.partial_clusters],
            "excluded_cutting_letters": [e.as_dict() for e in self.excluded_cutting_letters],
            "excluded_other": [e.as_dict() for e in self.excluded_other],
            "full_count": self.full_count,
            "letters": self.letters,
            # backward-compatible aliases for older tests
            "hits": [
                {
                    "letter": c.letter,
                    "text_pos": c.text_pos,
                    "box_center": c.box_center,
                    "triangle_tip": c.triangle_tip,
                    "confidence": c.confidence,
                }
                for c in self.full_clusters + self.partial_clusters
            ],
        }


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _centroid(pts: Sequence[Point]) -> Point:
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _is_axis_aligned_rect(pts: Sequence[Point], *, side_lo=5.0, side_hi=9.5) -> bool:
    """Рамка add_datum: axis-aligned square ~s=7."""
    if len(pts) < 4:
        return False
    xs = [p[0] for p in pts[:4]]
    ys = [p[1] for p in pts[:4]]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if not (side_lo <= w <= side_hi and side_lo <= h <= side_hi):
        return False
    if abs(w - h) > 1.5:
        return False
    # все углы на границах bbox (axis-aligned)
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    for x, y in pts[:4]:
        on_v = abs(x - xmin) < 1e-6 or abs(x - xmax) < 1e-6
        on_h = abs(y - ymin) < 1e-6 or abs(y - ymax) < 1e-6
        if not (on_v and on_h):
            return False
    return True


def _is_rectangle_any_orient(pts: Sequence[Point], *, ang_tol_deg: float = 12.0) -> bool:
    """Прямоугольник/квадрат в любой ориентации (по сторонам и углам).

    P4.3.1 A1: повёрнутый квадрат не должен становиться datum_triangle.
    """
    if len(pts) < 4:
        return False
    # ровно 4 уникальных угла (доп. вершины → не rect здесь)
    p = list(pts[:4])
    sides = [_dist(p[i], p[(i + 1) % 4]) for i in range(4)]
    if min(sides) < 1e-6:
        return False
    # противоположные стороны ≈ равны
    if abs(sides[0] - sides[2]) > 0.12 * max(sides[0], sides[2]):
        return False
    if abs(sides[1] - sides[3]) > 0.12 * max(sides[1], sides[3]):
        return False
    # углы ≈ 90° (скалярное произведение соседних рёбер ≈ 0)
    cos_tol = abs(math.cos(math.radians(90.0 - ang_tol_deg)))
    for i in range(4):
        a, b, c = p[i], p[(i + 1) % 4], p[(i + 2) % 4]
        v1 = (a[0] - b[0], a[1] - b[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        n1 = math.hypot(*v1) or 1.0
        n2 = math.hypot(*v2) or 1.0
        cos_a = abs((v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2))
        if cos_a > cos_tol:
            return False
    # диагонали ≈ равны
    d1 = _dist(p[0], p[2])
    d2 = _dist(p[1], p[3])
    if abs(d1 - d2) > 0.12 * max(d1, d2):
        return False
    return True


def _is_datum_triangle(pts: Sequence[Point]) -> Optional[Tuple[Point, Point]]:
    """
    add_datum: points=[tip, b, a, c].
    tip — остриё; a — «вершина» вдоль outward; b,c симметричны.
    Не должен проходить тест прямоугольника (в т.ч. повёрнутого).
    """
    if len(pts) < 4:
        return None
    if _is_axis_aligned_rect(pts, side_lo=4.0, side_hi=14.0):
        return None
    if _is_rectangle_any_orient(pts):
        return None
    tip, b, a, c = pts[0], pts[1], pts[2], pts[3]
    db, dc = _dist(tip, b), _dist(tip, c)
    da = _dist(tip, a)
    if da < 1e-6 or db < 1e-6 or dc < 1e-6:
        return None
    # симметрия b/c относительно tip→a
    if abs(db - dc) > 0.35 * max(db, dc):
        return None
    # mid(b,c) близко к оси tip→a
    mid = ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2)
    # проекция mid на tip→a
    ax, ay = a[0] - tip[0], a[1] - tip[1]
    L2 = ax * ax + ay * ay
    t = ((mid[0] - tip[0]) * ax + (mid[1] - tip[1]) * ay) / L2
    proj = (tip[0] + t * ax, tip[1] + t * ay)
    if _dist(mid, proj) > 0.25 * da:
        return None
    # a дальше tip, чем b/c
    if da < max(db, dc) * 0.85:
        return None
    return tip, a


def classify_closed_poly(pl: Polyline) -> PolyClass:
    """box (AA-рамка) | datum_triangle | other.

    Лишние вершины / повёрнутый прямоугольник / неоднозначность → other (не угадывать).
    """
    if len(pl.points) != 4:
        return PolyClass(
            kind="other",
            poly=pl,
            center=_centroid(pl.points) if pl.points else None,
        )
    pts = list(pl.points)
    if _is_axis_aligned_rect(pts):
        return PolyClass(kind="box", poly=pl, center=_centroid(pts))
    # повёрнутый прямоугольник — не база и не треугольник
    if _is_rectangle_any_orient(pts):
        return PolyClass(kind="other", poly=pl, center=_centroid(pts))
    tri = _is_datum_triangle(pts)
    if tri is not None:
        tip, apex = tri
        return PolyClass(
            kind="datum_triangle", poly=pl, tip=tip, apex=apex, center=_centroid(pts)
        )
    return PolyClass(kind="other", poly=pl, center=_centroid(pts))


def _section_tick_lines(doc: DrawingDocument) -> List[Line]:
    return [
        e
        for e in doc.entities
        if isinstance(e, Line) and getattr(e, "layer", "") == "Сечение"
    ]


def is_cutting_plane_letter(
    text: Text, ticks: List[Line], *, max_dist: float = 16.0
) -> bool:
    """Буква секущей: рядом с концом Line на слое «Сечение»."""
    pos = (float(text.position[0]), float(text.position[1]))
    for ln in ticks:
        if _dist(pos, (ln.start[0], ln.start[1])) <= max_dist:
            return True
        if _dist(pos, (ln.end[0], ln.end[1])) <= max_dist:
            return True
    return False


def detect_datums(doc: DrawingDocument) -> List[DatumCluster]:
    """Совместимость: список кластеров (full+partial)."""
    r = detect_datums_report(doc)
    return r.full_clusters + r.partial_clusters


def detect_datums_report(doc: DrawingDocument) -> DatumDetectReport:
    report = DatumDetectReport()
    ticks = _section_tick_lines(doc)

    thin_closed = [
        e
        for e in doc.entities
        if isinstance(e, Polyline) and e.closed and getattr(e, "layer", "") == LAYER_THIN
    ]
    thin_lines = [
        e for e in doc.entities if isinstance(e, Line) and getattr(e, "layer", "") == LAYER_THIN
    ]
    letters = [
        e
        for e in doc.entities
        if isinstance(e, Text)
        and len(e.content) == 1
        and e.content.isalpha()
        and e.content.isupper()
        and getattr(e, "layer", "") == LAYER_TEXT
        and e.height >= 4.0
    ]

    boxes: List[PolyClass] = []
    triangles: List[PolyClass] = []
    for pl in thin_closed:
        cls = classify_closed_poly(pl)
        if cls.kind == "box":
            boxes.append(cls)
        elif cls.kind == "datum_triangle":
            triangles.append(cls)

    # исключённые секущие
    candidates: List[Text] = []
    for t in letters:
        if is_cutting_plane_letter(t, ticks):
            report.excluded_cutting_letters.append(
                ExcludedLetter(
                    letter=t.content,
                    position=(float(t.position[0]), float(t.position[1])),
                    reason="рядом с Line на слое «Сечение» (add_cutting_plane tick)",
                )
            )
        else:
            candidates.append(t)

    # P4.3.1 A2: резервирование box / letter / triangle после назначения
    used_box_ids: set[int] = set()
    used_letter_ids: set[int] = set()
    used_tri_ids: set[int] = set()

    def _letter_candidates_near(box_center: Point) -> List[Tuple[float, Text]]:
        hits: List[Tuple[float, Text]] = []
        for t in candidates:
            if id(t) in used_letter_ids:
                continue
            pos = (float(t.position[0]), float(t.position[1]))
            d = _dist(pos, box_center)
            if d <= 8.0:
                hits.append((d, t))
        hits.sort(key=lambda x: x[0])
        return hits

    def _triangle_shelf_matches(
        box_center: Point,
    ) -> List[Tuple[PolyClass, Line]]:
        """Все валидные (triangle, shelf) для рамки; без first-wins."""
        found: List[Tuple[PolyClass, Line]] = []
        seen_tri: set[int] = set()
        for ln in thin_lines:
            ends = [(ln.start[0], ln.start[1]), (ln.end[0], ln.end[1])]
            near_box = min(_dist(e, box_center) for e in ends)
            if near_box > 14.0:
                continue
            for tri in triangles:
                tid = id(tri.poly)
                if tid in used_tri_ids or tid in seen_tri:
                    continue
                if tri.apex is None or tri.tip is None:
                    continue
                if any(_dist(e, tri.apex) <= 4.0 for e in ends):
                    found.append((tri, ln))
                    seen_tri.add(tid)
        # альтернатива: apex в радиусе + Line
        for tri in triangles:
            tid = id(tri.poly)
            if tid in used_tri_ids or tid in seen_tri:
                continue
            if tri.apex is None:
                continue
            if _dist(tri.apex, box_center) > 30.0:
                continue
            for ln in thin_lines:
                ends = [(ln.start[0], ln.start[1]), (ln.end[0], ln.end[1])]
                if (
                    min(_dist(e, box_center) for e in ends) <= 14.0
                    and min(_dist(e, tri.apex) for e in ends) <= 4.0
                ):
                    found.append((tri, ln))
                    seen_tri.add(tid)
                    break
        return found

    for box in boxes:
        assert box.center is not None
        if id(box.poly) in used_box_ids:
            continue

        letter_hits = _letter_candidates_near(box.center)
        if not letter_hits:
            continue
        # неоднозначность букв: две на почти одинаковом расстоянии
        if len(letter_hits) >= 2 and abs(letter_hits[0][0] - letter_hits[1][0]) <= 0.5:
            report.excluded_other.append(
                ExcludedLetter(
                    letter=",".join(sorted({t.content for _, t in letter_hits[:2]})),
                    position=box.center,
                    reason=(
                        "ambiguous_letter_near_box: несколько букв на сопоставимом "
                        "расстоянии — произвольный выбор запрещён (P4.3.1 A2)"
                    ),
                )
            )
            continue
        letter_hit = letter_hits[0][1]

        matches = _triangle_shelf_matches(box.center)
        if len(matches) > 1:
            report.partial_clusters.append(
                DatumCluster(
                    letter=letter_hit.content,
                    confidence="partial",
                    text_pos=(
                        float(letter_hit.position[0]),
                        float(letter_hit.position[1]),
                    ),
                    box_center=box.center,
                    triangle_tip=matches[0][0].tip,
                    shelf_ok=True,
                    detail=(
                        f"ambiguous_triangle_shelf: {len(matches)} конкурирующих "
                        "треугольников — произвольный выбор запрещён (P4.3.1 A2)"
                    ),
                )
            )
            # резервируем рамку/букву, чтобы не переиспользовать в другом full
            used_box_ids.add(id(box.poly))
            used_letter_ids.add(id(letter_hit))
            continue

        tri_hit: Optional[PolyClass] = None
        shelf: Optional[Line] = None
        if len(matches) == 1:
            tri_hit, shelf = matches[0]

        pos = (float(letter_hit.position[0]), float(letter_hit.position[1]))
        if tri_hit is not None and shelf is not None:
            tip = tri_hit.tip
            assert tip is not None
            if _dist(tip, box.center) > 55.0:
                report.partial_clusters.append(
                    DatumCluster(
                        letter=letter_hit.content,
                        confidence="partial",
                        text_pos=pos,
                        box_center=box.center,
                        triangle_tip=tip,
                        shelf_ok=True,
                        detail="элементы слишком далеко для одного кластера",
                    )
                )
                used_box_ids.add(id(box.poly))
                used_letter_ids.add(id(letter_hit))
                used_tri_ids.add(id(tri_hit.poly))
            else:
                report.full_clusters.append(
                    DatumCluster(
                        letter=letter_hit.content,
                        confidence="full_pattern",
                        text_pos=pos,
                        box_center=box.center,
                        triangle_tip=tip,
                        shelf_ok=True,
                        detail="box+letter+shelf+datum_triangle",
                    )
                )
                used_box_ids.add(id(box.poly))
                used_letter_ids.add(id(letter_hit))
                used_tri_ids.add(id(tri_hit.poly))
        else:
            report.partial_clusters.append(
                DatumCluster(
                    letter=letter_hit.content,
                    confidence="partial",
                    text_pos=pos,
                    box_center=box.center,
                    triangle_tip=tri_hit.tip if tri_hit else None,
                    shelf_ok=shelf is not None,
                    detail=(
                        f"incomplete: shelf={shelf is not None} "
                        f"triangle={tri_hit is not None}"
                    ),
                )
            )
            used_box_ids.add(id(box.poly))
            used_letter_ids.add(id(letter_hit))
            if tri_hit is not None:
                used_tri_ids.add(id(tri_hit.poly))

    return report


def datum_check_payload(doc: DrawingDocument) -> Dict[str, Any]:
    return detect_datums_report(doc).as_dict()
