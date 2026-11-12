# -*- coding: utf-8 -*-
"""Лист детали «Корпус» ПП-062215009-00, А3, 1:2."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cad import Sheet, View  # noqa: E402
import korpus_data as D  # noqa: E402
from common import DIA, fix_stamp_two_line_cells, leader_cbo, write_tt  # noqa: E402
from qa_check import review, require_clean  # noqa: E402

OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
K = 2.0


def fmt(v):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.1f" % v).replace(".", ",")


def section_body():
    """Симметричный разрез А-А через отверстия: без рёбер в плоскости."""
    yb, ybt = 0.0, D.T_BOT_PART
    ytb, yt = D.H_PART - D.T_TOP_PART, D.H_PART
    outer = [
        (-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), (D.D_BOT / 2, ybt),
        (D.R_OUT_BOT, ybt), (D.R_OUT_TOP, ytb), (D.D_TOP / 2, ytb),
        (D.D_TOP / 2, yt), (-D.D_TOP / 2, yt), (-D.D_TOP / 2, ytb),
        (-D.R_OUT_TOP, ytb), (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    body = Polygon(outer)
    # внутренняя полость
    inner = Polygon([
        (-D.R_IN_BOT, yb), (-D.R_IN_BOT, ybt), (-D.R_IN_TOP, ytb),
        (-D.R_IN_TOP, yt), (D.R_IN_TOP, yt), (D.R_IN_TOP, ytb),
        (D.R_IN_BOT, ybt), (D.R_IN_BOT, yb),
    ])
    body = body.difference(inner)
    # отверстия ⌀12 + цековка ⌀24×16 сверху фланца (симметрично)
    for s in (-1.0, 1.0):
        cx = s * D.PCD_OUTER / 2
        body = body.difference(box(cx - D.D_THRU / 2, yb, cx + D.D_THRU / 2, ybt))
        body = body.difference(
            box(cx - D.D_CB / 2, ybt - D.CB_DEPTH, cx + D.D_CB / 2, ybt + 0.01)
        )
    # М8 на 0°/180° в верхней полке
    m8w = 6.8
    for s in (-1.0, 1.0):
        cx = s * D.PCD_INNER / 2
        body = body.difference(box(cx - m8w / 2, ytb - 0.01, cx + m8w / 2, yt + 0.01))
    return body


def draw_section(F: View, sh: Sheet):
    body = section_body()
    F.geom(body, "main")
    F.hatch(body, angle=45, step=2.8)
    F.axis(0, -6, 0, D.H_PART + 6)
    for s in (-1, 1):
        cx = s * D.PCD_OUTER / 2
        F.axis(cx, -3, cx, D.T_BOT_PART + 5)
        cx2 = s * D.PCD_INNER / 2
        F.axis(cx2, D.H_PART - D.T_TOP_PART - 3, cx2, D.H_PART + 3)

    yb, ybt, yt = 0.0, D.T_BOT_PART, D.H_PART
    ytb = yt - D.T_TOP_PART

    # диаметры сверху / снизу — шахматные tpos, отступ 10 затем +7
    F.dim((-D.R_IN_TOP, yt), (D.R_IN_TOP, yt), 10, f"{DIA}{fmt(D.D_BORE_TOP)}", tpos=0.28)
    F.dim((-D.D_TOP / 2, yt), (D.D_TOP / 2, yt), 17, f"{DIA}{fmt(D.D_TOP)}", tpos=0.72)
    F.dim((-D.R_IN_BOT, yb), (D.R_IN_BOT, yb), -10, f"{DIA}{fmt(D.D_BORE_BOT)}", tpos=0.28)
    F.dim((-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), -17, f"{DIA}{fmt(D.D_BOT)}", tpos=0.72)

    # вертикали справа: 20 ближе, 100 дальше
    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, ybt), 10, fmt(D.T_BOT_PART), tpos=0.5)
    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, yt), 17, fmt(D.H_PART), tpos=0.55)
    # 16 — глубина цековки слева (от верха фланца вниз)
    F.dim((-D.D_BOT / 2, ybt - D.CB_DEPTH), (-D.D_BOT / 2, ybt), -10, fmt(D.CB_DEPTH), tpos=0.5)
    # 15 верхняя полка
    F.dim((-D.D_TOP / 2, ytb), (-D.D_TOP / 2, yt), -10, fmt(D.T_TOP_PART), tpos=0.5)

    # толщина стенки 15 — выноска, НЕ на штриховке
    mid = ybt + 0.55 * (ytb - ybt)
    t = (mid - ybt) / (ytb - ybt)
    ro = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * t
    tip = F.P(ro + 0.5, mid)
    sh.leader(tip, tip + np.array([18, 10]), fmt(D.WALL), arrow=True)

    # Ra 6,3 — полки и внутренняя поверхность (как на исходнике), не на размерных линиях
    tip = F.P(-40, yt)
    sh.rough_leader(tip, tip + np.array([-16, 12]), "Ra 6,3", side="left")
    tip = F.P(95, yb)
    sh.rough_leader(tip, tip + np.array([22, -16]), "Ra 6,3")
    tip = F.P(-125, ybt)
    sh.rough_leader(tip, tip + np.array([-18, 14]), "Ra 6,3", side="left")
    # внутренняя конусная поверхность
    tip = F.P(-D.R_IN_TOP - 2, ytb - 8)
    sh.rough_leader(tip, tip + np.array([-20, -8]), "Ra 6,3", side="left")

    sh.text(*F.P(0, yt + 28), "А-А", h=5, ha="center")


def draw_plan(Tv: View, sh: Sheet, ox: float, oy: float):
    Tv.circle(0, 0, D.D_BOT / 2)
    Tv.circle(0, 0, D.D_TOP / 2)
    Tv.circle(0, 0, D.R_IN_TOP)
    Tv.circle(0, 0, D.R_IN_BOT, "thin")
    Tv.circle(0, 0, D.R_OUT_BOT, "thin")
    Tv.axis(-D.D_BOT / 2 - 8, 0, D.D_BOT / 2 + 8, 0)
    Tv.axis(0, -D.D_BOT / 2 - 8, 0, D.D_BOT / 2 + 8)

    # рёбра между отверстиями (30°+60°k)
    for i in range(D.N_RIBS):
        ang = math.radians(30 + i * 60)
        cax, cay = math.cos(ang), math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        hw = D.RIB_W / 2
        # рёбра только между ⌀200 и ⌀300 — не накрывать М8 на верхней полке
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
        cx = (D.PCD_OUTER / 2) * math.cos(a)
        cy = (D.PCD_OUTER / 2) * math.sin(a)
        Tv.circle(cx, cy, D.D_CB / 2)
        Tv.circle(cx, cy, D.D_THRU / 2)
        Tv.axis(cx - 12, cy, cx + 12, cy)
        Tv.axis(cx, cy - 12, cx, cy + 12)

    # М8 на 0°+90°k (в плоскости А-А)
    for i in range(D.N_INNER):
        a = math.radians(i * 90)
        cx = (D.PCD_INNER / 2) * math.cos(a)
        cy = (D.PCD_INNER / 2) * math.sin(a)
        Tv.circle(cx, cy, 4.0)
        Tv.circle(cx, cy, 3.3, "thin")
        Tv.axis(cx - 8, cy, cx + 8, cy)
        Tv.axis(cx, cy - 8, cx, cy + 8)

    # толщина ребра 10 на ребре 150°
    a = math.radians(150)
    ca, sa = math.cos(a), math.sin(a)
    r_m = 128.0
    px, py = -sa, ca
    p1 = (r_m * ca - 5 * px, r_m * sa - 5 * py)
    p2 = (r_m * ca + 5 * px, r_m * sa + 5 * py)
    Tv.dim(p1, p2, 10, "10", tpos=0.5)

    # PCD внутри рамки
    Tv.dim((-D.PCD_OUTER / 2, 0), (D.PCD_OUTER / 2, 0), 14, f"{DIA}{fmt(D.PCD_OUTER)}", tpos=0.78)
    Tv.dim((0, -D.PCD_INNER / 2), (0, D.PCD_INNER / 2), -12, f"{DIA}{fmt(D.PCD_INNER)}", tpos=0.82)

    # выноски
    tip = Tv.P(
        (D.PCD_OUTER / 2) * math.cos(math.radians(60)),
        (D.PCD_OUTER / 2) * math.sin(math.radians(60)),
    )
    knee = np.array([ox + 98, oy + 48])
    leader_cbo(sh, tip, knee, D.CB_DEPTH)

    tip2 = Tv.P(0, D.PCD_INNER / 2)
    knee2 = np.array([ox + 70, oy + 78])
    sh.leader(tip2, knee2, "4 отв. М8-7Н", h=3.5, side="right")

    # секущая А-А: стрелки вверх (вид сверху → разрез над планом)
    x_ext = D.D_BOT / 2 + 14
    for s in (-1, 1):
        p0 = Tv.P(s * x_ext, 0)
        p1 = Tv.P(s * (x_ext + 12), 0)
        sh.seg(*p0, *p1, "cut")
        sh.arrow(p0, (0, 1), L=3.2, W=1.1)
        sh.text(p1[0], p1[1] + 6, "А", h=5, ha="center")


def build():
    sh = Sheet("A3")
    F = View(sh, 148, 205, K)
    Tv = View(sh, 138, 92, K)
    draw_section(F, sh)
    draw_plan(Tv, sh, ox=138, oy=92)

    TT = [
        "Технические требования",
        "1. Неуказанные предельные отклонения:",
        "    отверстия H14, валы h14, остальные ±IT14/2.",
        "2. Неуказанные литейные радиусы R5.",
        "3. Формовочные уклоны по ГОСТ 3212-92.",
        "4. Твёрдость НВ 163…229.",
    ]
    write_tt(sh, TT, x0=248, y_base=66, step=6)

    sh.rough_corner(368, 270, h=3.5, val="Ra 12,5")
    sh.frame(
        ["Корпус"],
        D.DESIGNATION_00,
        D.MATERIAL,
        D.MASS_PART_STR,
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
    issues = review(sh, code=D.DESIGNATION_00)
    png = OUT / "detal.png"
    pdf = OUT / "detal.pdf"
    # PDF только после OK
    rc = require_clean(issues)
    if rc == 0:
        sh.render(str(png), pdf=str(pdf), dpi=180)
        print("saved", pdf)
    else:
        sh.render(str(png), dpi=180)
        print("draft png only:", png)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
