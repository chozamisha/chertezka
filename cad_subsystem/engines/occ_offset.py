# -*- coding: utf-8 -*-
"""2D offset замкнутых полилиний через build123d / OCP 8.
Запускать только через python-ocp8."""
from __future__ import annotations

import json
import sys
from typing import List, Sequence, Tuple

Point = Tuple[float, float]


def _ordered_wire_points(wire) -> List[Point]:
    edges = list(wire.edges())
    if not edges:
        return []
    pts: List[Point] = []
    for e in edges:
        sp = e.start_point()
        pts.append((float(sp.X), float(sp.Y)))
    ep = edges[-1].end_point()
    last = (float(ep.X), float(ep.Y))
    if not pts or abs(pts[0][0] - last[0]) > 1e-7 or abs(pts[0][1] - last[1]) > 1e-7:
        pts.append(last)
    else:
        pts.append(pts[0])
    return pts


def offset_closed(points: Sequence[Point], amount: float) -> List[Point]:
    """Параллельный контур. amount > 0 — наружу (для CCW), < 0 — внутрь."""
    from build123d import BuildSketch, Polygon, offset

    clean = [(float(x), float(y)) for x, y in points]
    if len(clean) >= 2 and clean[0] == clean[-1]:
        clean = clean[:-1]
    if len(clean) < 3:
        raise ValueError("need >= 3 points")

    with BuildSketch() as sk:
        Polygon(*clean)
        offset(amount=float(amount))

    faces = list(sk.faces())
    if not faces:
        raise RuntimeError("offset produced no faces")
    # largest face by area
    face = max(faces, key=lambda f: f.area)
    return _ordered_wire_points(face.outer_wire())


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        data = json.load(sys.stdin)
    else:
        data = json.loads(argv[0])
    pts = [(float(x), float(y)) for x, y in data["points"]]
    amount = float(data["amount"])
    result = offset_closed(pts, amount)
    json.dump({"points": result}, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
