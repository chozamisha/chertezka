# -*- coding: utf-8 -*-
"""PDF из той же сцены (matplotlib, мм листа). DXF остаётся основным CAD-файлом."""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc as MArc
from matplotlib.patches import Circle as MCircle
from matplotlib.patches import FancyArrowPatch, Polygon
from matplotlib.patches import Rectangle

from ..model.document import DrawingDocument
from ..model.entities import (
    Arc,
    Circle,
    DimLinear,
    Hatch,
    Leader,
    Line,
    MText,
    Polyline,
    Text,
)

MM2PT = 72 / 25.4


def _hatch_lines(path, angle_deg=45.0, step=2.5):
    from shapely.geometry import LineString, MultiLineString, Polygon as SPoly

    poly = SPoly(path)
    if poly.is_empty:
        return []
    minx, miny, maxx, maxy = poly.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    R = math.hypot(maxx - minx, maxy - miny) / 2 + step
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)])
    n = np.array([-d[1], d[0]])
    lines = []
    kk = -R
    while kk <= R:
        p0 = np.array([cx, cy]) + n * kk
        lines.append(LineString([p0 - d * R, p0 + d * R]))
        kk += step
    inter = poly.intersection(MultiLineString(lines))
    geoms = inter.geoms if hasattr(inter, "geoms") else [inter]
    out = []
    for g in geoms:
        if hasattr(g, "coords") and g.length > 0.2:
            out.append(list(g.coords))
    return out


def export_pdf(drawing: DrawingDocument, path: str | Path, dpi: int = 200) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    W, H = drawing.width, drawing.height
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")

    def stroke(pts, lw=0.7, color="k"):
        pts = np.asarray(pts, float)
        ax.plot(
            pts[:, 0],
            pts[:, 1],
            color=color,
            lw=lw * MM2PT / (72 / 72),
            solid_capstyle="round",
            solid_joinstyle="round",
        )

    for e in drawing.entities:
        if isinstance(e, Line):
            stroke([e.start, e.end], 0.7 if e.layer == "Основная" else 0.25)
        elif isinstance(e, Polyline):
            pts = list(e.points)
            if e.closed and pts:
                pts = pts + [pts[0]]
            stroke(pts, 0.7 if e.layer in ("Основная", "Штамп") else 0.25)
        elif isinstance(e, Circle):
            ax.add_patch(
                MCircle(
                    e.center,
                    e.radius,
                    fill=False,
                    ec="k",
                    lw=0.7,
                )
            )
        elif isinstance(e, Arc):
            ax.add_patch(
                MArc(
                    e.center,
                    2 * e.radius,
                    2 * e.radius,
                    angle=0,
                    theta1=e.start_angle,
                    theta2=e.end_angle,
                    color="k",
                    lw=0.7,
                )
            )
        elif isinstance(e, Hatch):
            for seg in _hatch_lines(e.path, angle_deg=e.angle, step=max(1.5, e.scale)):
                stroke(seg, 0.25)
        elif isinstance(e, Text):
            ax.text(
                e.position[0],
                e.position[1],
                e.content,
                fontsize=e.height * MM2PT * 0.85,
                rotation=e.rotation,
                ha=e.halign,
                va={
                    "baseline": "baseline",
                    "bottom": "bottom",
                    "middle": "center",
                    "top": "top",
                }.get(e.valign, "baseline"),
                color="k",
            )
        elif isinstance(e, MText):
            ax.text(
                e.position[0],
                e.position[1],
                e.content,
                fontsize=e.height * MM2PT * 0.85,
                ha="left",
                va="top",
                color="k",
                wrap=True,
            )
        elif isinstance(e, DimLinear):
            p1 = np.array(e.p1, float)
            p2 = np.array(e.p2, float)
            u = p2 - p1
            L = np.linalg.norm(u)
            if L < 1e-9:
                continue
            u = u / L
            n = np.array([-u[1], u[0]])
            q1, q2 = p1 + n * e.offset, p2 + n * e.offset
            stroke([p1, q1 + n * 2], 0.25)
            stroke([p2, q2 + n * 2], 0.25)
            stroke([q1, q2], 0.25)
            # arrows
            for tip, direction in ((q1, -u), (q2, u)):
                base = tip - direction * 3.0
                ortho = np.array([-direction[1], direction[0]])
                ax.add_patch(
                    Polygon(
                        [tip, base + ortho * 0.9, base - ortho * 0.9],
                        closed=True,
                        fc="k",
                        ec="k",
                        lw=0.1,
                    )
                )
            txt = e.text if e.text is not None else f"{L:.0f}"
            mid = (q1 + q2) / 2 + n * 1.2
            ang = math.degrees(math.atan2(u[1], u[0]))
            ax.text(mid[0], mid[1], txt, fontsize=3.5 * MM2PT * 0.85, ha="center", va="bottom", rotation=ang)
        elif isinstance(e, Leader):
            stroke([e.tip, e.knee], 0.25)
            tw = max(len(e.text) * e.text_height * 0.7, 10)
            endx = e.knee[0] + (tw if e.side == "right" else -tw)
            stroke([e.knee, (endx, e.knee[1])], 0.25)
            tx = e.knee[0] + (1 if e.side == "right" else -tw + 1)
            ax.text(tx, e.knee[1] + 1, e.content if hasattr(e, "content") else e.text, fontsize=e.text_height * MM2PT * 0.85)

    fig.savefig(path, dpi=dpi, facecolor="white")
    # also companion PNG
    png = path.with_suffix(".png")
    fig.savefig(png, dpi=dpi, facecolor="white")
    plt.close(fig)
    return path
