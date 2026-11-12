# -*- coding: utf-8 -*-
"""Геометрия листа детали из DXF: разрез, план, штамп.

Роли размеров определяет геометрия (заштрихованное сечение, концентрические
окружности, ячейки основной надписи), а не совпадение чисел с эталоном.
Координаты здесь в мм листа; перевод в мм детали делает профиль через масштаб.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import polygonize, unary_union

THICK_LW = 50  # 0,5 мм: основная линия по ГОСТ 2.303 толще
STAMP_W, STAMP_H = 185.0, 55.0  # форма 1 ГОСТ 2.104


@dataclass
class TextItem:
    text: str
    x: float
    y: float
    h: float = 3.5
    rot: float = 0.0


@dataclass
class Seg:
    x1: float
    y1: float
    x2: float
    y2: float
    weight: int = -1

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1)) % 180.0

    @property
    def mid(self) -> Tuple[float, float]:
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2


@dataclass
class Circle:
    cx: float
    cy: float
    r: float
    weight: int = -1


@dataclass
class Drawing:
    segs: List[Seg] = field(default_factory=list)
    circles: List[Circle] = field(default_factory=list)
    texts: List[TextItem] = field(default_factory=list)
    hatch_polys: List[Polygon] = field(default_factory=list)
    closed_polys: List[List[Tuple[float, float]]] = field(default_factory=list)


def _weight(doc, e) -> int:
    lw = e.dxf.get("lineweight", -1)
    if lw is not None and lw >= 0:
        return int(lw)
    try:
        lw = doc.layers.get(e.dxf.layer).dxf.get("lineweight", -1)
    except Exception:
        lw = -1
    return int(lw) if lw is not None and lw >= 0 else -1


def _dimension_text(e) -> Optional[TextItem]:
    """Размерное число из DIMENSION: переопределённый текст или измеренное значение."""
    try:
        measured = float(e.get_measurement())
    except Exception:
        return None
    try:
        measured *= float(e.get_dim_style().dxf.get("dimlfac", 1.0) or 1.0)
    except Exception:
        pass
    value = ("%.3f" % measured).rstrip("0").rstrip(".")
    kind = e.dxf.get("dimtype", 0) & 7
    prefix = "%%c" if kind == 3 else "R" if kind == 4 else ""
    override = (e.dxf.get("text", "") or "").strip()
    text = override.replace("<>", value) if override else prefix + value
    p = e.dxf.get("text_midpoint", None)
    if p is None:
        return None
    return TextItem(text, float(p[0]), float(p[1]), 3.5, 0.0)


def _walk(doc, e, dr: Drawing, depth: int = 0) -> None:
    t = e.dxftype()
    if t == "LINE":
        dr.segs.append(Seg(e.dxf.start[0], e.dxf.start[1], e.dxf.end[0], e.dxf.end[1], _weight(doc, e)))
    elif t in ("LWPOLYLINE", "POLYLINE"):
        from ezdxf import path as ezpath

        w = _weight(doc, e)
        pts = [(v[0], v[1]) for v in ezpath.make_path(e).flattening(0.05)]
        closed = bool(e.closed) if t == "LWPOLYLINE" else bool(e.is_closed)
        if closed and pts and pts[0] != pts[-1]:
            pts.append(pts[0])
        if len(pts) >= 4 and math.dist(pts[0], pts[-1]) < 1e-6:
            closed = True
        for a, b in zip(pts, pts[1:]):
            if a != b:
                dr.segs.append(Seg(a[0], a[1], b[0], b[1], w))
        if closed and len(pts) >= 4:
            dr.closed_polys.append(pts[:-1])
    elif t == "CIRCLE":
        dr.circles.append(Circle(e.dxf.center[0], e.dxf.center[1], e.dxf.radius, _weight(doc, e)))
    elif t == "ARC":
        from ezdxf import path as ezpath

        w = _weight(doc, e)
        pts = [(v[0], v[1]) for v in ezpath.make_path(e).flattening(0.05)]
        for a, b in zip(pts, pts[1:]):
            dr.segs.append(Seg(a[0], a[1], b[0], b[1], w))
    elif t == "TEXT":
        _, p1, _ = e.get_placement()
        dr.texts.append(TextItem(str(e.dxf.text or ""), p1[0], p1[1], e.dxf.height, e.dxf.get("rotation", 0.0)))
    elif t == "MTEXT":
        p = e.dxf.insert
        dr.texts.append(TextItem(e.plain_text().replace("\n", " "), p[0], p[1],
                                 e.dxf.get("char_height", 3.5), e.dxf.get("rotation", 0.0)))
    elif t == "HATCH":
        if e.dxf.get("solid_fill", 0):
            return
        from ezdxf import path as ezpath

        for p in ezpath.from_hatch(e):
            pts = [(v[0], v[1]) for v in p.flattening(0.05)]
            if len(pts) >= 3:
                poly = Polygon(pts)
                if poly.is_valid and poly.area > 0:
                    dr.hatch_polys.append(poly)
    elif t == "DIMENSION":
        item = _dimension_text(e)
        if item:
            dr.texts.append(item)
    elif t == "INSERT" and depth < 4:
        for v in e.virtual_entities():
            _walk(doc, v, dr, depth + 1)


def load_drawing(path: str | Path) -> Drawing:
    try:
        import ezdxf
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Нужен пакет ezdxf: pip install ezdxf") from exc
    doc = ezdxf.readfile(str(path))
    dr = Drawing()
    for e in doc.modelspace():
        _walk(doc, e, dr)
    for t in dr.texts:
        t.text = t.text.strip()
    dr.texts = [t for t in dr.texts if t.text]
    return dr


# ---------------------------------------------------------------- штамп

_SCALE = re.compile(r"^(?:М\s*)?(\d+(?:[.,]\d+)?)\s*:\s*(\d+(?:[.,]\d+)?)$")
_NUMBER = re.compile(r"^\d+(?:[.,]\d+)?$")
_DESIGNATION = re.compile(r"^[A-ZА-ЯЁ0-9]{1,8}[-.][0-9A-ZА-ЯЁ.\-]{3,}$")
STAMP_LABELS = {
    "изм", "лист", "№ докум", "подп", "дата", "разраб", "пров", "т.контр", "н.контр", "утв",
    "лит", "масса", "масштаб", "листов", "копировал", "формат",
}


def _norm(s: str) -> str:
    return s.strip().rstrip(".").lower()


def _is_label(s: str) -> bool:
    n = _norm(s)
    return n in STAMP_LABELS or n.startswith(("лист ", "листов ", "формат "))


@dataclass
class Stamp:
    designation: str = ""
    name: List[str] = field(default_factory=list)
    material: List[str] = field(default_factory=list)
    org: List[str] = field(default_factory=list)
    mass_kg: Optional[float] = None
    scale: Optional[str] = None
    scale_k: Optional[float] = None
    lit: str = ""
    dev: str = ""
    chk: str = ""
    box: Optional[Tuple[float, float, float, float]] = None


def read_stamp(texts: Sequence[TextItem]) -> Stamp:
    """Основная надпись по подписям граф и ячейкам формы 1 ГОСТ 2.104."""
    st = Stamp()
    flat = [t for t in texts if abs(t.rot) < 1.0]

    def label(name: str) -> Optional[TextItem]:
        hits = [t for t in flat if _norm(t.text) == name]
        return min(hits, key=lambda t: t.y) if hits else None

    def below(lab: Optional[TextItem], pattern=None) -> Optional[TextItem]:
        if lab is None:
            return None
        hits = [t for t in flat if 2.0 < lab.y - t.y <= 22.0 and abs(t.x - lab.x) <= 9.0
                and not _is_label(t.text) and (pattern is None or pattern.match(t.text))]
        return min(hits, key=lambda t: lab.y - t.y) if hits else None

    def right_of(lab: Optional[TextItem]) -> str:
        if lab is None:
            return ""
        hits = [t for t in flat if abs(t.y - lab.y) <= 1.5 and 5.0 < t.x - lab.x <= 45.0
                and not _is_label(t.text)]
        return min(hits, key=lambda t: t.x).text if hits else ""

    sc = below(label("масштаб"), _SCALE)
    if sc:
        m = _SCALE.match(sc.text)
        a, b = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
        st.scale, st.scale_k = f"{m.group(1)}:{m.group(2)}", b / a
    mass = below(label("масса"), _NUMBER)
    if mass:
        st.mass_kg = float(mass.text.replace(",", "."))
    lit = below(label("лит"))
    if lit and len(lit.text) <= 3:
        st.lit = lit.text
    st.dev = right_of(label("разраб"))
    st.chk = right_of(label("пров"))

    dev, utv, scale_lab = label("разраб"), label("утв"), label("масштаб")
    x0 = y0 = None
    if dev is not None and utv is not None:
        x0, y0 = dev.x - 0.8, utv.y - 1.3
    elif scale_lab is not None:
        x0, y0 = scale_lab.x - 176.0, scale_lab.y - 36.3
    if x0 is not None:
        st.box = (x0, y0, x0 + STAMP_W, y0 + STAMP_H)

        def cell(xa, xb, ya, yb):
            hits = [t for t in flat if x0 + xa - 1 <= t.x <= x0 + xb + 1 and y0 + ya - 1 <= t.y <= y0 + yb + 1
                    and not _is_label(t.text)]
            return sorted(hits, key=lambda t: -t.y)

        code = cell(65, 185, 40, 55)
        if code:
            st.designation = max(code, key=lambda t: t.h).text
        st.name = [t.text for t in cell(65, 135, 16, 39) if t.h >= 3.4]
        st.material = _split_material([t.text for t in cell(65, 135, 0, 14)])
        st.org = [t.text for t in cell(135, 185, 0, 14)]
    if not st.designation:
        cands = [t for t in flat if _DESIGNATION.match(t.text)]
        if cands:
            st.designation = max(cands, key=lambda t: t.h).text
    return st


def _split_material(lines: List[str]) -> List[str]:
    out: List[str] = []
    for s in lines:
        m = re.match(r"^(.*?)\s+(ГОСТ\s.+)$", s)
        out.extend([m.group(1), m.group(2)] if m and m.group(1) else [s])
    return out


def in_box(t: TextItem, box: Optional[Tuple[float, float, float, float]], pad: float = 1.0) -> bool:
    return bool(box) and box[0] - pad <= t.x <= box[2] + pad and box[1] - pad <= t.y <= box[3] + pad


# ---------------------------------------------------------------- разрез

@dataclass
class Section:
    region: object  # shapely (Multi)Polygon, мм листа
    axis_x: float
    y0: float
    y1: float
    asymmetry: float
    source: str  # hatch_entity | hatch_lines


def _hatch_lines(dr: Drawing) -> List[Seg]:
    """Линии штриховки: самая многочисленная семья наклонных тонких отрезков."""
    fam: Dict[int, List[Seg]] = defaultdict(list)
    for s in dr.segs:
        a = s.angle
        if min(a, 180 - a) < 3 or abs(a - 90) < 3 or s.weight >= THICK_LW or s.length < 0.3:
            continue
        fam[int(round(a)) % 180].append(s)
    if not fam:
        return []
    best = max(fam.values(), key=len)
    return best if len(best) >= 12 else []


def find_section(dr: Drawing) -> Optional[Section]:
    """Материал в разрезе: границы HATCH либо грани контура, внутри которых лежит штриховка."""
    if dr.hatch_polys:
        region, source = unary_union(dr.hatch_polys), "hatch_entity"
    else:
        hatch = _hatch_lines(dr)
        if not hatch:
            return None
        xs = [x for s in hatch for x in (s.x1, s.x2)]
        ys = [y for s in hatch for y in (s.y1, s.y2)]
        bx0, bx1, by0, by1 = min(xs) - 5, max(xs) + 5, min(ys) - 5, max(ys) + 5
        known = any(s.weight >= 0 for s in dr.segs)
        skip = {id(s) for s in hatch}
        lines = []
        for s in dr.segs:
            if (known and s.weight < THICK_LW) or id(s) in skip:
                continue
            if max(s.x1, s.x2) < bx0 or min(s.x1, s.x2) > bx1 or max(s.y1, s.y2) < by0 or min(s.y1, s.y2) > by1:
                continue
            lines.append(LineString([(s.x1, s.y1), (s.x2, s.y2)]))
        if not lines:
            return None
        strokes = unary_union([LineString([(s.x1, s.y1), (s.x2, s.y2)]) for s in hatch])
        faces = list(polygonize(unary_union(lines)))
        picked = [f for f in faces if f.intersection(strokes).length > 0.2]
        if not picked:
            return None
        region, source = unary_union(picked), "hatch_lines"
    region = region.buffer(0)
    if region.is_empty:
        return None
    x0, y0, x1, y1 = region.bounds
    axis = (x0 + x1) / 2
    from shapely import affinity

    mirror = affinity.scale(region, xfact=-1, origin=(axis, 0))
    asym = region.symmetric_difference(mirror).area / max(region.area, 1e-9)
    return Section(region, axis, y0, y1, asym, source)


def _span(region, axis: float, y: float, xmax: float) -> Optional[Tuple[float, float]]:
    """Ближняя и дальняя от оси границы материала на высоте y (правая половина)."""
    hit = region.intersection(LineString([(axis, y), (xmax + 1.0, y)]))
    if hit.is_empty:
        return None
    b = hit.bounds
    return b[0] - axis, b[2] - axis


def section_profile(sec: Section) -> Tuple[List[Tuple[float, float, float, float]], List[Tuple[float, float, float, float]]]:
    """Образующие тела вращения: наружная и внутренняя, участки (y0, y1, r0, r1) от низа разреза."""
    polys = sec.region.geoms if isinstance(sec.region, MultiPolygon) else [sec.region]
    ys = sorted({round(y, 4) for p in polys for _, y in list(p.exterior.coords)
                 + [c for ring in p.interiors for c in ring.coords]})
    xmax = sec.region.bounds[2]
    outer, inner = [], []
    for ya, yb in zip(ys, ys[1:]):
        if yb - ya < 1e-3:
            continue
        span = yb - ya
        d = span / 50
        a, b = _span(sec.region, sec.axis_x, ya + d, xmax), _span(sec.region, sec.axis_x, yb - d, xmax)
        if a is None or b is None:
            continue
        # значения на границах участка: линейная экстраполяция от внутренних точек
        ext = d / (span - 2 * d)
        inner.append((ya - sec.y0, yb - sec.y0, a[0] - (b[0] - a[0]) * ext, b[0] + (b[0] - a[0]) * ext))
        outer.append((ya - sec.y0, yb - sec.y0, a[1] - (b[1] - a[1]) * ext, b[1] + (b[1] - a[1]) * ext))
    return _merge(outer), _merge(inner)


def _merge(parts, tol: float = 0.02):
    """Склеить соседние участки, лежащие на одной прямой."""
    out: List[List[float]] = []
    for y0, y1, r0, r1 in parts:
        if out:
            py0, py1, pr0, pr1 = out[-1]
            slope_prev = (pr1 - pr0) / (py1 - py0)
            slope = (r1 - r0) / (y1 - y0)
            if abs(pr1 - r0) < tol and abs(slope_prev - slope) < 1e-3:
                out[-1] = [py0, y1, pr0, r1]
                continue
        out.append([y0, y1, r0, r1])
    return [tuple(p) for p in out]


# ---------------------------------------------------------------- план

@dataclass
class HoleGroup:
    pcd: float  # ⌀ окружности центров, мм листа
    n: int
    angle0: float
    diameters: List[float]  # ⌀ окружностей в одном центре, по возрастанию, мм листа


@dataclass
class Ribs:
    n: int
    width: float
    angle0: float
    r_in: float
    r_out: float


@dataclass
class Plan:
    cx: float
    cy: float
    radii: List[float]
    holes: List[HoleGroup] = field(default_factory=list)
    ribs: Optional[Ribs] = None


def find_plan(dr: Drawing, axis_x: Optional[float] = None) -> Optional[Plan]:
    """Вид сверху: семейство концентрических окружностей, отверстия по окружностям, рёбра."""
    groups: Dict[Tuple[float, float], List[Circle]] = defaultdict(list)
    for c in dr.circles:
        groups[(round(c.cx, 1), round(c.cy, 1))].append(c)
    cands = [(k, v) for k, v in groups.items() if len(v) >= 2]
    if not cands:
        return None

    def score(item):
        (cx, _), v = item
        off = 0.0 if axis_x is None else abs(cx - axis_x)
        return (len(v) - off, max(c.r for c in v))

    (cx, cy), fam = max(cands, key=score)
    radii = sorted({round(c.r, 3) for c in fam})
    rmax = radii[-1]
    plan = Plan(cx, cy, radii)

    by_centre: Dict[Tuple[float, float], List[float]] = defaultdict(list)
    for c in dr.circles:
        d = math.hypot(c.cx - cx, c.cy - cy)
        if 0.5 < d <= rmax + 0.5 and c.r < rmax / 3:
            by_centre[(round(c.cx, 1), round(c.cy, 1))].append(c.r)
    rings: Dict[Tuple[float, Tuple[float, ...]], List[Tuple[float, float]]] = defaultdict(list)
    for (x, y), rs in by_centre.items():
        key = (round(math.hypot(x - cx, y - cy), 1), tuple(sorted({round(r, 2) for r in rs})))
        rings[key].append((x, y))
    for (dist, rs), pts in sorted(rings.items(), key=lambda kv: -kv[0][0]):
        n = len(pts)
        step = 360.0 / n
        angs = sorted(math.degrees(math.atan2(y - cy, x - cx)) % step for x, y in pts)
        a0 = angs[0] if angs[-1] - angs[0] < 1.0 else min(angs, key=lambda a: min(a, step - a))
        a0 = 0.0 if min(a0, step - a0) < 0.5 else a0
        plan.holes.append(HoleGroup(2 * dist, n, round(a0, 1), [2 * r for r in rs]))

    ribs = []
    for pts in dr.closed_polys:
        if len(pts) != 4:
            continue
        sides = [math.dist(pts[i], pts[(i + 1) % 4]) for i in range(4)]
        if abs(sides[0] - sides[2]) > 0.05 or abs(sides[1] - sides[3]) > 0.05:
            continue
        i = 0 if sides[0] >= sides[1] else 1
        long_len, width = sides[i], sides[i + 1]
        if long_len < 2 * width or width < 0.3:
            continue
        mx = sum(p[0] for p in pts) / 4 - cx
        my = sum(p[1] for p in pts) / 4 - cy
        rc = math.hypot(mx, my)
        if rc < 1 or rc > rmax:
            continue
        ux, uy = pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1]
        if abs(ux * my - uy * mx) / (long_len * rc) > 0.02:  # длинная сторона не радиальна
            continue
        ribs.append((math.degrees(math.atan2(my, mx)) % 360.0, width, rc - long_len / 2, rc + long_len / 2))
    if len(ribs) >= 2:
        n = len(ribs)
        step = 360.0 / n
        a0 = min(a % step for a, *_ in ribs)
        a0 = 0.0 if min(a0, step - a0) < 0.5 else a0
        plan.ribs = Ribs(n, sum(r[1] for r in ribs) / n, round(a0, 1),
                         sum(r[2] for r in ribs) / n, sum(r[3] for r in ribs) / n)
    return plan
