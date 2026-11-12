# -*- coding: utf-8 -*-
"""Лист 00. Корпус (деталь) — А3, М 1:2. Новый скрипт через cad.py."""
import math
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon

from cad import Sheet, View
import korpus_data as D

OUT = Path(__file__).resolve().parent
ART = Path("/opt/cursor/artifacts")
ART.mkdir(parents=True, exist_ok=True)
K = 2.0


def fmt(v, n=0):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.*f" % (n, v)).replace(".", ",")


def draw_section(F, sh):
    yb, ybt = 0.0, D.T_BOT_PART
    ytb, yt = D.H_PART - D.T_TOP_PART, D.H_PART
    left = [
        (-D.D_BOT / 2, yb), (-D.R_IN_BOT, yb), (-D.R_IN_BOT, ybt), (-D.R_IN_TOP, ytb),
        (-D.R_IN_TOP, yt), (-D.D_TOP / 2, yt), (-D.D_TOP / 2, ytb), (-D.R_OUT_TOP, ytb),
        (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    right = [
        (D.D_BOT / 2, yb), (D.R_IN_BOT, yb), (D.R_IN_BOT, ybt), (D.R_IN_TOP, ytb),
        (D.R_IN_TOP, yt), (D.D_TOP / 2, yt), (D.D_TOP / 2, ytb), (D.R_OUT_TOP, ytb),
        (D.R_OUT_BOT, ybt), (D.D_BOT / 2, ybt),
    ]
    F.hatch(Polygon(left), angle=45, step=2.8)
    F.hatch(Polygon(right), angle=45, step=2.8)
    F.pl([
        (-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), (D.D_BOT / 2, ybt),
        (D.R_OUT_BOT, ybt), (D.R_OUT_TOP, ytb), (D.D_TOP / 2, ytb),
        (D.D_TOP / 2, yt), (-D.D_TOP / 2, yt), (-D.D_TOP / 2, ytb),
        (-D.R_OUT_TOP, ytb), (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ], "main", close=True)
    F.pl([
        (-D.R_IN_BOT, yb), (-D.R_IN_BOT, ybt), (-D.R_IN_TOP, ytb),
        (-D.R_IN_TOP, yt), (D.R_IN_TOP, yt), (D.R_IN_TOP, ytb),
        (D.R_IN_BOT, ybt), (D.R_IN_BOT, yb),
    ], "main", close=True)

    rib_y = ybt + 0.45 * (ytb - ybt)
    t = (rib_y - ybt) / (ytb - ybt)
    rx = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * t
    F.pl([(D.R_OUT_BOT, ybt), (rx, rib_y), (D.D_BOT / 2 - 22, ybt)], "main")
    F.pl([(-D.R_OUT_BOT, ybt), (-rx, rib_y), (-(D.D_BOT / 2 - 22), ybt)], "main")

    for s in (-1, 1):
        x = s * D.PCD_OUTER / 2
        F.pl([(x - D.D_THRU / 2, yb), (x - D.D_THRU / 2, ybt),
              (x + D.D_THRU / 2, ybt), (x + D.D_THRU / 2, yb)], "main", close=True)
        F.pl([(x - D.D_CB / 2, yb), (x - D.D_CB / 2, yb + D.CB_DEPTH),
              (x + D.D_CB / 2, yb + D.CB_DEPTH), (x + D.D_CB / 2, yb)], "main", close=True)

    F.axis(0, -8, 0, D.H_PART + 10)

    F.dim((-D.R_IN_TOP, yt), (D.R_IN_TOP, yt), 10 * K, "⌀%s" % fmt(D.D_BORE_TOP), tpos=0.30)
    F.dim((-D.D_TOP / 2, yt), (D.D_TOP / 2, yt), (10 + 7) * K, "⌀%s" % fmt(D.D_TOP), tpos=0.70)
    F.dim((-D.R_IN_BOT, yb), (D.R_IN_BOT, yb), -10 * K, "⌀%s" % fmt(D.D_BORE_BOT), tpos=0.30)
    F.dim((-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), -(10 + 7) * K, "⌀%s" % fmt(D.D_BOT), tpos=0.70)
    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, ybt), -10 * K, fmt(D.T_BOT_PART), tpos=0.55)
    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, yt), -(10 + 7) * K, fmt(D.H_PART), tpos=0.55)
    F.dim((-D.D_TOP / 2, ytb), (-D.D_TOP / 2, yt), 10 * K, fmt(D.T_TOP_PART), tpos=0.55)

    mid = ybt + 0.55 * (ytb - ybt)
    t = (mid - ybt) / (ytb - ybt)
    ro = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * t
    tip = F.P(ro + 1, mid)
    sh.leader(tip, tip + np.array([16, 8]), fmt(D.WALL), arrow=True)
    tip = F.P(-D.R_OUT_BOT, ybt)
    sh.leader(tip, tip + np.array([-14, 10]), "R%s" % fmt(D.R_FILLET), side="left", arrow=True)

    tip = F.P(-48, yt)
    sh.rough_leader(tip, tip + np.array([-14, 11]), "Ra 6,3", side="left")
    tip = F.P(60, yb)
    sh.rough_leader(tip, tip + np.array([12, -12]), "Ra 6,3")

    sh.text(*F.P(0, yt + (10 + 7) * K + 11), "А-А", h=5, ha="center")


def draw_plan(Tv, sh):
    Tv.circle(0, 0, D.D_BOT / 2)
    Tv.circle(0, 0, D.D_TOP / 2)
    Tv.circle(0, 0, D.R_IN_TOP)
    Tv.circle(0, 0, D.R_OUT_BOT, "thin")
    Tv.circle(0, 0, D.R_IN_BOT, "thin")
    Tv.axis(-D.D_BOT / 2 - 8, 0, D.D_BOT / 2 + 8, 0)
    Tv.axis(0, -D.D_BOT / 2 - 8, 0, D.D_BOT / 2 + 8)

    for i in range(D.N_RIBS):
        ang = math.radians(i * 60.0)
        cax, cay = math.cos(ang), math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        hw = D.RIB_W / 2
        r1, r2 = D.R_OUT_TOP, D.D_BOT / 2 - 2
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
        Tv.circle(cx, cy, D.D_CB / 2)
        Tv.circle(cx, cy, D.D_THRU / 2)
        Tv.axis(cx - 5, cy, cx + 5, cy)
        Tv.axis(cx, cy - 5, cx, cy + 5)
    for i in range(D.N_INNER):
        a = math.radians(45 + 90 * i)
        cx, cy = (D.PCD_INNER / 2) * math.cos(a), (D.PCD_INNER / 2) * math.sin(a)
        Tv.circle(cx, cy, 3.4)
        Tv.axis(cx - 4, cy, cx + 4, cy)
        Tv.axis(cx, cy - 4, cx, cy + 4)

    tip = Tv.P(D.PCD_OUTER / 2 * math.cos(math.radians(25)),
               D.PCD_OUTER / 2 * math.sin(math.radians(25)))
    sh.leader(tip, tip + np.array([18, 14]), "⌀%s" % fmt(D.PCD_OUTER), arrow=False, dot=True)
    tip = Tv.P(D.PCD_INNER / 2 * math.cos(math.radians(120)),
               D.PCD_INNER / 2 * math.sin(math.radians(120)))
    sh.leader(tip, tip + np.array([-16, 12]), "⌀%s" % fmt(D.PCD_INNER), side="left", arrow=False, dot=True)

    tip = Tv.P(D.PCD_OUTER / 2 * math.cos(math.radians(-20)),
               D.PCD_OUTER / 2 * math.sin(math.radians(-20)))
    sh.leader(tip, tip + np.array([24, -18]),
              "6 отв. ⌀12, цек. ⌀24×%s" % fmt(D.CB_DEPTH), arrow=True)
    tip = Tv.P(D.PCD_INNER / 2 * math.cos(math.radians(155)),
               D.PCD_INNER / 2 * math.sin(math.radians(155)))
    sh.leader(tip, tip + np.array([-22, 16]), "4 отв. М8-7Н", side="left", arrow=True)

    R = D.D_BOT / 2
    for sgn in (-1, 1):
        p0 = Tv.P(sgn * (R + 3), 0)
        p1 = Tv.P(sgn * (R + 3 + 9), 0)
        sh.seg(*p0, *p1, "cut")
        mid = p0 + (p1 - p0) * 0.4
        sh.seg(mid[0], mid[1], mid[0], mid[1] + 6.5, "thin")
        sh.arrow((mid[0], mid[1] + 6.5), (0, 1), L=3.0, W=1.0)
        sh.text(mid[0], mid[1] + 9.5, "А", h=5, ha="center")


def main():
    sh = Sheet("A3")
    F = View(sh, 140, 185, K)
    Tv = View(sh, 140, 80, K)
    draw_section(F, sh)
    draw_plan(Tv, sh)

    TT = [
        "1. Неуказанные предельные отклонения размеров",
        "    отверстий H14, валов h14, остальных ±IT14/2.",
        "2. Неуказанные радиусы R3…R5.",
        "3. Неуказанные литейные уклоны по ГОСТ 3212-92.",
        "4. Твёрдость НВ 163…229.",
        "5. * Размеры для справок.",
    ]
    tx0, step = 230, 7
    ty0 = 62 + len(TT) * step
    for i, t in enumerate(TT):
        sh.text(tx0, ty0 - i * step, t, h=3.5)

    sh.rough_corner(355, 275, h=3.5, val="Ra 12,5")
    sh.frame(
        ["Корпус"], D.DESIGNATION_00, D.MATERIAL, D.MASS_PART_STR, "1:2",
        org=D.ORG, sheet="1", sheets="1", lit="У", dev=D.DEV, chk=D.CHK,
    )

    png = OUT / "ПП-062215009-00_Korpus.png"
    pdf = OUT / "ПП-062215009-00_Korpus.pdf"
    dxf = OUT / "ПП-062215009-00_Korpus.dxf"
    col = sh.render(str(png), str(pdf), dpi=200, check_collisions=True)
    sh.to_dxf(str(dxf))
    for dst in (ART / "00_Korpus.pdf", ART / "00_Korpus.png", ART / "ПП-062215009-00_Корпус.pdf"):
        dst.write_bytes((pdf if dst.suffix == ".pdf" else png).read_bytes())
    print("ok 00", D.DESIGNATION_00, D.DEV, D.MASS_PART_STR, "col", len(col))
    for c in col[:20]:
        print(" ", c)
    return col


if __name__ == "__main__":
    main()
