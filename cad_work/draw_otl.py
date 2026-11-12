# -*- coding: utf-8 -*-
"""Лист отливки «Корпус» ПП-062215009-01, А3, 1:2."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cad import Sheet, View  # noqa: E402
import korpus_data as D  # noqa: E402
from common import DIA, fix_stamp_two_line_cells, write_tt  # noqa: E402
from qa_check import review, require_clean  # noqa: E402

OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
K = 2.0


def fmt(v, n=0):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.*f" % (n, v)).replace(".", ",")


def cast_polys():
    yb, ybt = 0.0, D.T_BOT_CAST
    ytb, yt = D.H_CAST - D.T_TOP_CAST, D.H_CAST
    outer = [
        (-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), (D.D_BOT / 2, ybt),
        (D.R_OUT_BOT, ybt), (D.R_OUT_TOP, ytb), (D.D_TOP / 2, ytb),
        (D.D_TOP / 2, yt), (-D.D_TOP / 2, yt), (-D.D_TOP / 2, ytb),
        (-D.R_OUT_TOP, ytb), (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    body = Polygon(outer)
    inner = Polygon([
        (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, ytb),
        (D.R_IN_BOT_CAST, ybt), (D.R_IN_BOT_CAST, yb),
    ])
    return body.difference(inner), yb, ybt, ytb, yt


def detail_thin(F):
    y0 = D.ALLOW_BOT
    y1 = y0 + D.T_BOT_PART
    y2 = y0 + D.H_PART - D.T_TOP_PART
    y3 = y0 + D.H_PART
    F.pl([
        (-D.D_BOT / 2, y0), (D.D_BOT / 2, y0), (D.D_BOT / 2, y1),
        (D.R_OUT_BOT, y1), (D.R_OUT_TOP, y2), (D.D_TOP / 2, y2),
        (D.D_TOP / 2, y3), (-D.D_TOP / 2, y3), (-D.D_TOP / 2, y2),
        (-D.R_OUT_TOP, y2), (-D.R_OUT_BOT, y1), (-D.D_BOT / 2, y1),
    ], "thin", close=True)
    F.pl([
        (-D.R_IN_BOT, y0), (-D.R_IN_BOT, y1), (-D.R_IN_TOP, y2),
        (-D.R_IN_TOP, y3), (D.R_IN_TOP, y3), (D.R_IN_TOP, y2),
        (D.R_IN_BOT, y1), (D.R_IN_BOT, y0),
    ], "thin", close=True)


def draw_section(F, sh):
    body, yb, ybt, ytb, yt = cast_polys()
    F.geom(body, "main")
    F.hatch(body, angle=45, step=2.8)
    # рёбра вдоль — без штриховки (не в плоскости А-А через отверстия: только контур сбоку не рисуем;
    # на отливке рёбра в плане; в разрезе через отверстия — симметрия без рёбер)
    detail_thin(F)
    F.axis(0, -8, 0, D.H_CAST + 10)

    F.dim((-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), 10, f"{DIA}{fmt(D.D_BORE_TOP_CAST)}", tpos=0.28)
    F.dim((-D.D_TOP / 2, yt), (D.D_TOP / 2, yt), 17, f"{DIA}{fmt(D.D_TOP)}", tpos=0.72)
    F.dim((-D.R_IN_BOT_CAST, yb), (D.R_IN_BOT_CAST, yb), -10, f"{DIA}{fmt(D.D_BORE_BOT_CAST)}", tpos=0.28)
    F.dim((-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), -17, f"{DIA}{fmt(D.D_BOT)}", tpos=0.72)
    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, ybt), 10, fmt(D.T_BOT_CAST), tpos=0.5)
    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, yt), 17, fmt(D.H_CAST), tpos=0.55)
    F.dim((-D.D_TOP / 2, ytb), (-D.D_TOP / 2, yt), -10, fmt(D.T_TOP_CAST), tpos=0.5)

    mid = ybt + 0.55 * (ytb - ybt)
    t = (mid - ybt) / max(ytb - ybt, 1)
    ro = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * t
    tip = F.P(ro + 0.5, mid)
    sh.leader(tip, tip + np.array([18, 10]), fmt(D.WALL), arrow=True)

    tip = F.P(-40, yt)
    sh.rough_leader(tip, tip + np.array([-16, 12]), "Ra 6,3", side="left")
    tip = F.P(90, yb)
    sh.rough_leader(tip, tip + np.array([18, -14]), "Ra 6,3")

    sh.text(*F.P(0, yt + 28), "А-А", h=5, ha="center")


def draw_plan(Tv, sh):
    Tv.circle(0, 0, D.D_BOT / 2)
    Tv.circle(0, 0, D.D_TOP / 2)
    Tv.circle(0, 0, D.R_IN_TOP_CAST)
    Tv.circle(0, 0, D.R_IN_TOP, "thin")
    Tv.circle(0, 0, D.R_OUT_BOT, "thin")
    Tv.circle(0, 0, D.R_IN_BOT_CAST, "thin")
    Tv.axis(-D.D_BOT / 2 - 8, 0, D.D_BOT / 2 + 8, 0)
    Tv.axis(0, -D.D_BOT / 2 - 8, 0, D.D_BOT / 2 + 8)

    for i in range(D.N_RIBS):
        ang = math.radians(30 + i * 60)
        cax, cay = math.cos(ang), math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        hw = D.RIB_W / 2
        r1, r2 = D.D_TOP / 2 + 2, D.D_BOT / 2 - 6
        Tv.pl([
            (cax * r1 + nx * hw, cay * r1 + ny * hw),
            (cax * r2 + nx * hw, cay * r2 + ny * hw),
            (cax * r2 - nx * hw, cay * r2 - ny * hw),
            (cax * r1 - nx * hw, cay * r1 - ny * hw),
        ], "main", close=True)

    Tv.circle(0, 0, D.PCD_OUTER / 2, "axis")
    Tv.circle(0, 0, D.PCD_INNER / 2, "axis")
    for i in range(D.N_OUTER):
        a = math.radians(i * 60)
        cx, cy = (D.PCD_OUTER / 2) * math.cos(a), (D.PCD_OUTER / 2) * math.sin(a)
        Tv.axis(cx - 8, cy, cx + 8, cy)
        Tv.axis(cx, cy - 8, cx, cy + 8)
    for i in range(D.N_INNER):
        a = math.radians(i * 90)
        cx, cy = (D.PCD_INNER / 2) * math.cos(a), (D.PCD_INNER / 2) * math.sin(a)
        Tv.axis(cx - 6, cy, cx + 6, cy)
        Tv.axis(cx, cy - 6, cx, cy + 6)

    Tv.dim((-D.PCD_OUTER / 2, 0), (D.PCD_OUTER / 2, 0), 14, f"{DIA}{fmt(D.PCD_OUTER)}", tpos=0.75)
    Tv.dim((0, -D.PCD_INNER / 2), (0, D.PCD_INNER / 2), -12, f"{DIA}{fmt(D.PCD_INNER)}", tpos=0.8)

    R = D.D_BOT / 2
    for s in (-1, 1):
        p0 = Tv.P(s * (R + 3), 0)
        p1 = Tv.P(s * (R + 14), 0)
        sh.seg(*p0, *p1, "cut")
        sh.arrow(p0, (0, 1), L=3.2, W=1.1)
        sh.text(p1[0], p1[1] + 6, "А", h=5, ha="center")


def build():
    sh = Sheet("A3")
    F = View(sh, 148, 205, K)
    Tv = View(sh, 138, 92, K)
    draw_section(F, sh)
    draw_plan(Tv, sh)

    TT = [
        "Технические требования",
        "1. Точность отливки 9-7-12-9 ГОСТ 26645-85.",
        "2. Формовочные уклоны по ГОСТ 3212-92:",
        "    наружные 1°30′, внутренние 2°.",
        "3. Неуказанные литейные радиусы R5.",
        "4. Твёрдость НВ 163…229.",
        "5. Термическая обработка: отжиг 500…550 °С.",
        "6. Литейная усадка 1 %.",
        "7. Отверстия ⌀12, цековки и М8 — мехобработкой.",
        "8. Тонкой линией показан контур детали.",
        f"9. ΣFп:Fшл:Fст = 1:1,1:1,2; ΣFп={fmt(D.SIGMA_FP,2)} см².",
    ]
    write_tt(sh, TT, x0=242, y_base=66, step=6)

    sh.rough_corner(368, 270, h=3.5, val="Ra 12,5")
    sh.frame(
        ["Корпус"],
        D.DESIGNATION_01,
        D.MATERIAL,
        D.MASS_STR,
        "1:2",
        org=D.ORG,
        lit="У",
        dev=D.DEV,
        chk=D.CHK,
    )
    fix_stamp_two_line_cells(sh)
    return sh


def main():
    sh = build()
    issues = review(sh, code=D.DESIGNATION_01)
    png, pdf = OUT / "otlivka.png", OUT / "otlivka.pdf"
    rc = require_clean(issues)
    if rc == 0:
        sh.render(str(png), pdf=str(pdf), dpi=180)
        print("saved", pdf)
    else:
        sh.render(str(png), dpi=180)
        print("draft png only", png)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
