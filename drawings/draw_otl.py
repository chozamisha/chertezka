# -*- coding: utf-8 -*-
"""Лист 01. Корпус. Отливка — А3, М 1:2."""
import math
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon

from cad import Sheet, View
import korpus_data as D

OUT = Path(__file__).resolve().parent
ART = Path("/opt/cursor/artifacts")
ART.mkdir(parents=True, exist_ok=True)
K = 2.0  # М 1:2


def fmt(v, n=0):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.*f" % (n, v)).replace(".", ",")


def cast_metal():
    yb, ybt = 0.0, D.T_BOT_CAST
    ytb, yt = D.H_CAST - D.T_TOP_CAST, D.H_CAST
    left = [
        (-D.D_BOT / 2, yb), (-D.R_IN_BOT_CAST, yb),
        (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (-D.D_TOP / 2, yt),
        (-D.D_TOP / 2, ytb), (-D.R_OUT_TOP, ytb),
        (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    right = [(abs(x) if x < 0 else x, y) for x, y in
             [(D.D_BOT / 2, yb), (D.R_IN_BOT_CAST, yb), (D.R_IN_BOT_CAST, ybt),
              (D.R_IN_TOP_CAST, ytb), (D.R_IN_TOP_CAST, yt), (D.D_TOP / 2, yt),
              (D.D_TOP / 2, ytb), (D.R_OUT_TOP, ytb), (D.R_OUT_BOT, ybt), (D.D_BOT / 2, ybt)]]
    return left, right, yb, ybt, ytb, yt


def detail_thin(F):
    """Контур детали после обработки — тонкая сплошная (ГОСТ 3.1125)."""
    # отливка низ y=0; деталь начинается с ALLOW_BOT
    y0 = D.ALLOW_BOT
    y1 = y0 + D.T_BOT_PART
    y2 = y0 + D.H_PART - D.T_TOP_PART
    y3 = y0 + D.H_PART
    outer = [
        (-D.D_BOT / 2, y0), (D.D_BOT / 2, y0), (D.D_BOT / 2, y1),
        (D.R_OUT_BOT, y1), (D.R_OUT_TOP, y2), (D.D_TOP / 2, y2),
        (D.D_TOP / 2, y3), (-D.D_TOP / 2, y3), (-D.D_TOP / 2, y2),
        (-D.R_OUT_TOP, y2), (-D.R_OUT_BOT, y1), (-D.D_BOT / 2, y1),
    ]
    F.pl(outer, "thin", close=True)
    inner = [
        (-D.R_IN_BOT, y0), (-D.R_IN_BOT, y1), (-D.R_IN_TOP, y2),
        (-D.R_IN_TOP, y3), (D.R_IN_TOP, y3), (D.R_IN_TOP, y2),
        (D.R_IN_BOT, y1), (D.R_IN_BOT, y0),
    ]
    F.pl(inner, "thin", close=True)


def draw_section(F, sh):
    left, right, yb, ybt, ytb, yt = cast_metal()
    F.hatch(Polygon(left), angle=45, step=2.8)
    F.hatch(Polygon(right), angle=45, step=2.8)

    outer = [
        (-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), (D.D_BOT / 2, ybt),
        (D.R_OUT_BOT, ybt), (D.R_OUT_TOP, ytb), (D.D_TOP / 2, ytb),
        (D.D_TOP / 2, yt), (-D.D_TOP / 2, yt), (-D.D_TOP / 2, ytb),
        (-D.R_OUT_TOP, ytb), (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    F.pl(outer, "main", close=True)
    inner = [
        (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, ytb),
        (D.R_IN_BOT_CAST, ybt), (D.R_IN_BOT_CAST, yb),
    ]
    F.pl(inner, "main", close=True)

    # рёбра без штриховки
    rib_y = ybt + 0.45 * (ytb - ybt)
    t = (rib_y - ybt) / (ytb - ybt)
    rx = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * t
    F.pl([(D.R_OUT_BOT, ybt), (rx, rib_y), (D.D_BOT / 2 - 22, ybt)], "main")
    F.pl([(-D.R_OUT_BOT, ybt), (-rx, rib_y), (-(D.D_BOT / 2 - 22), ybt)], "main")

    detail_thin(F)
    F.axis(0, -8, 0, D.H_CAST + 10)

    # размеры: литые (с припуском на отверстия)
    F.dim((-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), 10 * K, "⌀%s" % fmt(D.D_BORE_TOP_CAST), tpos=0.30)
    F.dim((-D.D_TOP / 2, yt), (D.D_TOP / 2, yt), (10 + 7) * K, "⌀%s" % fmt(D.D_TOP), tpos=0.70)
    F.dim((-D.R_IN_BOT_CAST, yb), (D.R_IN_BOT_CAST, yb), -10 * K, "⌀%s" % fmt(D.D_BORE_BOT_CAST), tpos=0.30)
    F.dim((-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), -(10 + 7) * K, "⌀%s" % fmt(D.D_BOT), tpos=0.70)

    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, ybt), -10 * K, fmt(D.T_BOT_CAST), tpos=0.55)
    F.dim((D.D_BOT / 2, yb), (D.D_BOT / 2, yt), -(10 + 7) * K, fmt(D.H_CAST), tpos=0.55)
    F.dim((-D.D_TOP / 2, ytb), (-D.D_TOP / 2, yt), 10 * K, fmt(D.T_TOP_CAST), tpos=0.55)

    mid = ybt + 0.55 * (ytb - ybt)
    t = (mid - ybt) / (ytb - ybt)
    ro = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * t
    tip = F.P(ro + 1, mid)
    sh.leader(tip, tip + np.array([20, 8]), fmt(D.WALL), arrow=True)

    tip = F.P(-D.R_OUT_BOT, ybt)
    sh.leader(tip, tip + np.array([-16, 10]), "R%s" % fmt(D.R_FILLET), side="left", arrow=True)

    # Ra на полках, не на размерных линиях
    tip = F.P(-55, yt)
    sh.rough_leader(tip, tip + np.array([-18, 12]), "Ra 6,3", side="left")
    tip = F.P(70, yb)
    sh.rough_leader(tip, tip + np.array([16, -14]), "Ra 6,3")

    sh.text(*F.P(0, yt + (10 + 7) * K + 12), "А-А", h=5, ha="center")


def draw_plan(Tv, sh):
    Tv.circle(0, 0, D.D_BOT / 2)
    Tv.circle(0, 0, D.D_TOP / 2)
    Tv.circle(0, 0, D.R_IN_TOP_CAST)  # литое отверстие
    Tv.circle(0, 0, D.R_IN_TOP, "thin")  # чистовое тонкой
    Tv.circle(0, 0, D.R_OUT_BOT, "thin")
    Tv.circle(0, 0, D.R_IN_BOT_CAST, "thin")
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

    # только оси будущих отверстий (не готовые)
    Tv.circle(0, 0, D.PCD_OUTER / 2, "axis")
    Tv.circle(0, 0, D.PCD_INNER / 2, "axis")
    for i in range(D.N_OUTER):
        a = math.radians(i * 60)
        cx, cy = (D.PCD_OUTER / 2) * math.cos(a), (D.PCD_OUTER / 2) * math.sin(a)
        Tv.axis(cx - 5, cy, cx + 5, cy)
        Tv.axis(cx, cy - 5, cx, cy + 5)
    for i in range(D.N_INNER):
        a = math.radians(45 + 90 * i)
        cx, cy = (D.PCD_INNER / 2) * math.cos(a), (D.PCD_INNER / 2) * math.sin(a)
        Tv.axis(cx - 4, cy, cx + 4, cy)
        Tv.axis(cx, cy - 4, cx, cy + 4)

    a = math.radians(35)
    c, s = math.cos(a), math.sin(a)
    Tv.dim((-D.PCD_INNER / 2 * c, -D.PCD_INNER / 2 * s),
           (D.PCD_INNER / 2 * c, D.PCD_INNER / 2 * s),
           0, "⌀%s" % fmt(D.PCD_INNER), ext1=False, ext2=False, tpos=0.72)
    a = math.radians(-28)
    c, s = math.cos(a), math.sin(a)
    Tv.dim((-D.PCD_OUTER / 2 * c, -D.PCD_OUTER / 2 * s),
           (D.PCD_OUTER / 2 * c, D.PCD_OUTER / 2 * s),
           0, "⌀%s" % fmt(D.PCD_OUTER), ext1=False, ext2=False, tpos=0.28)

    R = D.D_BOT / 2
    for sgn in (-1, 1):
        p0 = Tv.P(sgn * (R + 3), 0)
        p1 = Tv.P(sgn * (R + 3 + 10), 0)
        sh.seg(*p0, *p1, "cut")
        mid = p0 + (p1 - p0) * 0.4
        sh.seg(mid[0], mid[1], mid[0], mid[1] + 7, "thin")
        sh.arrow((mid[0], mid[1] + 7), (0, 1), L=3.2, W=1.1)
        sh.text(mid[0], mid[1] + 10, "А", h=5, ha="center")


def main():
    sh = Sheet("A3")
    F = View(sh, 145, 188, K)
    Tv = View(sh, 145, 82, K)

    draw_section(F, sh)
    draw_plan(Tv, sh)

    TT = [
        "1. Точность отливки 9-7-12-9 ГОСТ 26645-85.",
        "2. Формовочные уклоны по ГОСТ 3212-92:",
        "    наружные 1°30′, внутренние 2°.",
        "3. Неуказанные литейные радиусы R3…R5.",
        "4. Твёрдость НВ 163…229.",
        "5. Термическая обработка: отжиг 500…550 °С.",
        "6. Контроль: ВИК — 100 %.",
        "7. Литейная усадка 1 %.",
        "8. Отверстия ⌀12, цековки и М8 выполнять",
        "    механической обработкой.",
        "9. Тонкой линией показан контур детали.",
        "10. * Размеры для справок.",
    ]
    tx0 = 230
    ty0 = 62 + len(TT) * 7
    for i, t in enumerate(TT):
        sh.text(tx0, ty0 - i * 7, t, h=3.5)

    sh.rough_corner(355, 275, h=3.5, val="Ra 6,3")

    sh.frame(
        ["Корпус.", "Отливка"], D.DESIGNATION_01, D.MATERIAL, D.MASS_STR, "1:2",
        org=D.ORG, sheet="1", sheets="1", lit="У", dev=D.DEV, chk=D.CHK,
    )

    png = OUT / "ПП-062215009-01_Korpus_Otlivka.png"
    pdf = OUT / "ПП-062215009-01_Korpus_Otlivka.pdf"
    dxf = OUT / "ПП-062215009-01_Korpus_Otlivka.dxf"
    col = sh.render(str(png), str(pdf), dpi=200, check_collisions=True)
    sh.to_dxf(str(dxf))
    for dst in (ART / "01_Korpus_Otlivka.pdf", ART / "01_Korpus_Otlivka.png",
                ART / "ПП-062215009-01_Корпус_Отливка.pdf"):
        dst.write_bytes((pdf if dst.suffix == ".pdf" else png).read_bytes())
    print("ok 01", D.MASS_STR, "gap", round(188 - (82 + D.D_BOT / 2 / K), 1), "col", len(col))
    for c in col[:15]:
        print(" ", c)
    return col


if __name__ == "__main__":
    main()
