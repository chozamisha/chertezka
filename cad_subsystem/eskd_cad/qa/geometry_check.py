# -*- coding: utf-8 -*-
"""Геометрическая проверка сцены и DXF (не визуальная)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List

import ezdxf
from ezdxf import recover
from shapely.geometry import LineString, Polygon
from shapely.validation import explain_validity

from ..model.document import DrawingDocument
from ..model.entities import Arc, Circle, DimLinear, Hatch, Line, Polyline


def _poly_issues(pts, closed: bool, tag: str) -> List[str]:
    out = []
    if len(pts) < 2:
        return [f"{tag}: too few points"]
    if any(len(p) != 2 for p in pts):
        return [f"{tag}: bad point"]
    try:
        if closed and len(pts) >= 3:
            ring = list(pts)
            if ring[0] != ring[-1]:
                ring = ring + [ring[0]]
            g = Polygon(ring)
            if not g.is_valid:
                out.append(f"{tag}: invalid polygon: {explain_validity(g)}")
            if g.area < 1e-6:
                out.append(f"{tag}: zero area")
        else:
            g = LineString(pts)
            if not g.is_valid:
                out.append(f"{tag}: invalid linestring")
            if g.length < 1e-9:
                out.append(f"{tag}: zero length")
    except Exception as e:
        out.append(f"{tag}: shapely error {e}")
    return out


def check_document(doc: DrawingDocument) -> List[str]:
    issues: List[str] = []
    W, H = doc.width, doc.height
    # frame margins roughly
    x0, y0, x1, y1 = 20.0, 5.0, W - 5.0, H - 5.0
    n_hatch = n_dim = n_main = 0
    for i, e in enumerate(doc.entities):
        tag = f"ent[{i}:{type(e).__name__}]"
        if isinstance(e, Line):
            issues += _poly_issues([e.start, e.end], False, tag)
            n_main += 1 if e.layer == "Основная" else 0
        elif isinstance(e, Polyline):
            issues += _poly_issues(e.points, e.closed, tag)
        elif isinstance(e, Hatch):
            n_hatch += 1
            issues += _poly_issues(e.path, True, tag + "/hatch")
            for j, hole in enumerate(e.holes):
                issues += _poly_issues(hole, True, f"{tag}/hole{j}")
        elif isinstance(e, Circle):
            if e.radius <= 0:
                issues.append(f"{tag}: non-positive radius")
        elif isinstance(e, Arc):
            if e.radius <= 0:
                issues.append(f"{tag}: non-positive radius")
        elif isinstance(e, DimLinear):
            n_dim += 1
            if abs(e.p1[0] - e.p2[0]) < 1e-12 and abs(e.p1[1] - e.p2[1]) < 1e-12:
                issues.append(f"{tag}: zero-length dimension")
        # out of sheet (loose)
        pts = []
        if isinstance(e, Line):
            pts = [e.start, e.end]
        elif isinstance(e, Polyline):
            pts = e.points
        elif isinstance(e, Circle):
            cx, cy = e.center
            pts = [(cx - e.radius, cy), (cx + e.radius, cy), (cx, cy - e.radius), (cx, cy + e.radius)]
        for x, y in pts:
            if x < -2 or y < -2 or x > W + 2 or y > H + 2:
                issues.append(f"{tag}: outside sheet ({x:.1f},{y:.1f})")
                break

    if n_hatch < 1:
        issues.append("no hatch entities")
    if n_dim < 1:
        issues.append("no dimensions")
    return issues


def check_dxf_file(path: str | Path) -> List[str]:
    path = Path(path)
    issues: List[str] = []
    if not path.exists():
        return [f"missing {path}"]
    doc, auditor = recover.readfile(path)
    for err in auditor.errors:
        issues.append(f"auditor: {err}")
    msp = doc.modelspace()
    counts = Counter(e.dxftype() for e in msp)
    need = [
        ({"LINE", "LWPOLYLINE"}, "lines/polylines"),
        ({"CIRCLE", "ARC"}, "circles/arcs"),
        ({"HATCH"}, "hatch"),
        ({"DIMENSION"}, "dimensions"),
        ({"TEXT", "MTEXT"}, "text"),
    ]
    for group, name in need:
        if not any(counts.get(t, 0) for t in group):
            issues.append(f"DXF missing {name}; have {dict(counts)}")
    layers = {l.dxf.name for l in doc.layers}
    for need_l in ("Основная", "Размеры", "Штриховка", "Текст", "Осевая"):
        if need_l not in layers:
            issues.append(f"DXF missing layer {need_l}")
    # hatch validity via shapely where possible
    for e in msp.query("HATCH"):
        for path in e.paths:
            # polyline paths
            try:
                verts = [(v[0], v[1]) for v in path.vertices]
                if len(verts) >= 3:
                    issues += _poly_issues(verts, True, "dxf-hatch")
            except Exception:
                pass
    return issues
