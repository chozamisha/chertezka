# -*- coding: utf-8 -*-
"""Лист отливки «Колесо рабочее» по Рисунку 1 (⌀280), А3.

Не использует геометрию/файл КП-062215009. Только koleso_r1_data + cad.py.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cad import Sheet, View, text_width  # noqa: E402
import koleso_r1_data as D0  # noqa: E402
from common import DIA, fix_stamp_two_line_cells, write_tt  # noqa: E402
import qa_extra  # noqa: E402
from qa_check import review, require_clean  # noqa: E402

OUT = ROOT / "out"
SCALES = (1.0, 2.0)
FRAME_L, FRAME_B, FRAME_T = 20.0, 5.0, 292.0
TT_X0 = 248.0


def fmt(v, n=0):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.*f" % (n, v)).replace(".", ",")


def fmt_deg(v):
    deg = int(v)
    minutes = int(round((v - deg) * 60))
    return f"{deg}°" if minutes == 0 else f"{deg}°{minutes:02d}′"


def opt(D, name, default):
    return getattr(D, name, default)


def layout(D):
    for k in SCALES:
        rp = D.D_OUT / 2 / k
        hc = D.H_CAST / k
        yp = FRAME_B + 16 + rp
        ys = yp + rp + 22 + 8  # запас под подписи плана
        top = ys + hc + 20
        xc_min = FRAME_L + 8 + rp + 20
        xc_max = TT_X0 - 8 - rp - 20
        if top <= FRAME_T - 2 and xc_min <= xc_max:
            return k, (xc_min + xc_max) / 2, ys, yp
    raise ValueError("Отливка не помещается на А3 в 1:1 / 1:2")


def _ys(D):
    """Опорные высоты отливки: низ = 0."""
    yb = 0.0
    y1 = D.T_BOT_CAST
    y2 = y1 + D.H_CH_CAST
    y3 = y2 + D.T_TOP_CAST
    y4 = y3 + D.H_HUB_CAST
    return yb, y1, y2, y3, y4


def cast_poly(D):
    """Правая половина металла в разрезе А-А (без лопастей)."""
    yb, y1, y2, y3, y4 = _ys(D)
    ro = D.D_OUT / 2
    rh = D.D_HUB_CAST / 2
    rs = D.D_SHOULDER_CAST / 2
    rb = D.D_BORE_CAST / 2
    rr = max(D.D_RECESS_CAST / 2, rb + 1)
    rbot = D.D_BOT_CAST / 2
    wall = 18.0  # обод в канале
    # ступень плеча на верхе диска
    y_sh = y3 - min(D.SHOULDER_H + D.ALLOW_FACE * 0.2, D.T_TOP_CAST - 1)
    outer = [
        (rb, y4),
        (rh, y4),
        (rh, y3),
        (rs, y3),
        (rs, y_sh),
        (ro, y_sh),
        (ro, y2),
        (ro - wall, y2),
        (ro - wall, y1),
        (ro, y1),
        (ro, yb),
        (rbot, yb),
        (rbot, y1),
        (rb, y1 + 8),
        (rb, y4 - D.RECESS_DEPTH - 1),
        (rr, y4 - D.RECESS_DEPTH - 1),
        (rr, y4 - 0.5),
        (rb, y4 - 0.5),
        (rb, y4),
    ]
    return Polygon(outer)


def detail_thin(F, D):
    """Тонкий контур детали (припуски)."""
    ab, at, af, abo = D.ALLOW_BOT, D.ALLOW_TOP, D.ALLOW_FACE, D.ALLOW_BORE
    y0 = ab
    y1 = y0 + D.T_BOT
    y2 = y1 + D.H_CH
    y3 = y2 + D.T_TOP
    y4 = y3 + D.H_HUB
    for s in (-1, 1):
        F.seg(s * D.D_OUT / 2, y0, s * D.D_OUT / 2, y1, "thin")
        F.seg(s * D.D_OUT / 2, y2, s * D.D_OUT / 2, y3, "thin")
        F.seg(s * D.D_BOT / 2, y0, s * D.D_OUT / 2, y0, "thin")
        F.seg(s * D.D_HUB / 2, y3, s * D.D_HUB / 2, y4, "thin")
        F.seg(s * D.D_HUB / 2, y4, s * D.D_BORE / 2, y4, "thin")
        F.pl([
            (s * D.D_BORE / 2, y4 - D.RECESS_DEPTH),
            (s * D.D_RECESS / 2, y4 - D.RECESS_DEPTH),
            (s * D.D_RECESS / 2, y4),
        ], "thin")
        F.pl([
            (s * D.D_BORE / 2, y4 - D.RECESS_DEPTH),
            (s * D.D_BORE / 2, y0 + (D.H_PART - D.H_HUB - D.BORE_DEPTH)),
        ], "thin")


def draw_section(F, sh, D, k):
    body = cast_poly(D)
    # зеркалим в полный контур
    from shapely.affinity import scale as shp_scale
    full = body.union(shp_scale(body, xfact=-1, origin=(0, 0)))
    F.geom(full, "main")
    F.hatch(full, angle=45, step=2.8)
    detail_thin(F, D)
    yb, y1, y2, y3, y4 = _ys(D)
    F.axis(0, -6 * k, 0, y4 + 6 * k)

    # размеры
    F.dim((-D.D_OUT / 2, yb), (D.D_OUT / 2, yb), -14, f"{DIA}{fmt(D.D_OUT)}")
    F.dim((-D.D_HUB_CAST / 2, y4), (D.D_HUB_CAST / 2, y4), 10, f"{DIA}{fmt(D.D_HUB_CAST)}")
    F.dim((-D.D_BORE_CAST / 2, y4), (D.D_BORE_CAST / 2, y4), 17, f"{DIA}{fmt(D.D_BORE_CAST)}", tpos=0.35)
    F.dim((D.D_OUT / 2, yb), (D.D_OUT / 2, y1), -10, fmt(D.T_BOT_CAST), tpos=0.55)
    F.dim((D.D_OUT / 2, y1), (D.D_OUT / 2, y2), -10, fmt(D.H_CH_CAST), tpos=0.55)
    F.dim((D.D_OUT / 2, y2), (D.D_OUT / 2, y3), -10, fmt(D.T_TOP_CAST), tpos=0.55)
    F.dim((D.D_OUT / 2, yb), (D.D_OUT / 2, y4), -28, fmt(D.H_CAST, 1), tpos=0.62)

    tip = F.P(-(D.D_OUT / 2 - 9), (y1 + y2) / 2)
    sh.leader(tip, tip + np.array([-16, 10]), fmt(D.ALLOW_FACE, 1), side="left", arrow=True)
    tip = F.P(D.D_HUB_CAST / 2, y4)
    sh.rough(tip + np.array([8, 0]), (0, 1), D.RA_FACES, pre=fmt(D.ALLOW_TOP, 1))
    tip = F.P(D.D_OUT / 2, yb) + np.array([4, 0])
    sh.rough_leader(tip, tip + np.array([10, -12]), D.RA_FACES, pre=fmt(D.ALLOW_BOT, 1))
    tip = F.P(D.D_BORE_CAST / 2, (y3 + y4) / 2)
    sh.rough_leader(tip, tip + np.array([-22, 18]), D.RA_BORE, pre=fmt(D.ALLOW_BORE, 1), side="left")

    sh.text(*(F.P(0, y4) + np.array([0, 28])), "А-А", h=5, ha="center")


def _vane_poly(ang0_deg, r_hub, r_tip, r_out, r_in, half_w=4.0):
    """Упрощённый контур лопасти: дуги R_out/R_in между ступицей и ободом."""
    a0 = math.radians(ang0_deg)
    # хорда вдоль радиали с изгибом
    pts = []
    for i in range(8):
        t = i / 7
        r = r_hub + (r_tip - r_hub) * t
        bend = math.radians(18) * math.sin(t * math.pi)
        a = a0 + bend
        pts.append((r * math.cos(a) - half_w * math.sin(a),
                    r * math.sin(a) + half_w * math.cos(a)))
    for i in range(8):
        t = 1 - i / 7
        r = r_hub + (r_tip - r_hub) * t
        bend = math.radians(18) * math.sin(t * math.pi)
        a = a0 + bend
        pts.append((r * math.cos(a) + half_w * math.sin(a),
                    r * math.sin(a) - half_w * math.cos(a)))
    return pts


def draw_plan(Tv, sh, D, k):
    Tv.circle(0, 0, D.D_OUT / 2)
    Tv.circle(0, 0, D.D_HUB_CAST / 2)
    Tv.circle(0, 0, D.D_SHOULDER_CAST / 2, "thin")
    Tv.circle(0, 0, D.D_BORE_CAST / 2)
    rmax = D.D_OUT / 2
    Tv.axis(-rmax - 4 * k, 0, rmax + 4 * k, 0)
    Tv.axis(0, -rmax - 4 * k, 0, rmax + 4 * k)

    r_hub = D.D_HUB_CAST / 2 + 2
    r_tip = D.D_OUT / 2 - 8
    for i in range(D.N_VANES):
        ang = i * 360.0 / D.N_VANES + 20.0
        Tv.pl(_vane_poly(ang, r_hub, r_tip, D.R_VANE_OUT, D.R_VANE_IN), "main", close=True)

    # оси отверстий (не льются); сдвиг 30°, чтобы не совпадать с А-А
    Tv.circle(0, 0, D.PCD / 2, "axis")
    for i in range(D.N_HOLES):
        a = math.radians(30.0 + i * 360.0 / D.N_HOLES)
        cx, cy = D.PCD / 2 * math.cos(a), D.PCD / 2 * math.sin(a)
        Tv.axis(cx - 5 * k, cy, cx + 5 * k, cy)
        Tv.axis(cx, cy - 5 * k, cx, cy + 5 * k)

    # подписи плана — над видом, чтобы не пересекать секущую А-А справа
    c = Tv.P(0, 0)
    y_lab = c[1] + rmax / k + 8
    sh.text(c[0] - 55, y_lab, f"{DIA}{fmt(D.D_OUT)}", h=3.5)
    sh.text(c[0] - 10, y_lab, f"{DIA}{fmt(D.PCD)}", h=3.5)
    sh.text(c[0] + 35, y_lab, f"{D.N_HOLES} отв. {DIA}{fmt(D.D_HOLE)}", h=3.5)

    # секущая А-А
    for sgn in (-1, 1):
        p0 = Tv.P(0, 0) + np.array([sgn * (rmax / k + 6), 0.0])
        p1 = Tv.P(0, 0) + np.array([sgn * (rmax / k + 16), 0.0])
        sh.seg(*p0, *p1, "cut")
        xa = p1[0] - sgn * 2.5
        sh.seg(xa, p1[1] - 9.5, xa, p1[1] - 3.5, "thin")
        sh.arrow((xa, p1[1] - 0.55), (0, 1), L=3.2, W=1.1)
        sh.text(p1[0] + sgn * 3.5, p1[1] - 9.5, "А", h=5, ha="center")


def tt_lines(D):
    return [
        "Технические требования",
        f"1. Точность отливки {D.ACCURACY} ГОСТ 26645-85.",
        f"2. Формовочные уклоны по ГОСТ 3212-92: наружные {fmt_deg(D.DRAFT_EXT)},",
        f"    внутренние {fmt_deg(D.DRAFT_INT)}.",
        f"3. Неуказанные литейные радиусы R{fmt(D.R_FILLET)}…R{fmt(D.R_NOSE)}.",
        f"4. Литейная усадка {fmt(D.SHRINKAGE, 1)} % (12Х18Н9ТЛ).",
        f"5. Лопасти {D.N_VANES} шт., расположены равномерно.",
        f"6. Отверстия {DIA}{fmt(D.D_HOLE)} на {DIA}{fmt(D.PCD)} — мехобработкой.",
        "7. Тонкой линией показан контур детали.",
        f"8. Припуск на отверстие {fmt(D.ALLOW_BORE, 1)} мм на сторону.",
        f"9. ΣFп:Fшл:Fст = 1:1,2:1,4; ΣFп={fmt(D.SIGMA_FP, 2)} см².",
        "10. Обозначение КР-Рис1-* временное: на исходнике штампа не было.",
    ]


def build(D=None):
    D = D0 if D is None else D
    k, xc, ys, yp = layout(D)
    sh = Sheet("A3")
    draw_section(View(sh, xc, ys, k), sh, D, k)
    draw_plan(View(sh, xc, yp, k), sh, D, k)
    write_tt(sh, opt(D, "TT", None) or tt_lines(D), x0=TT_X0, y_base=66, step=6)
    sh.rough_corner(368, 270, h=3.5, val=D.RA_GENERAL)
    material = list(D.MATERIAL)
    org = tuple(D.ORG)
    sh.frame(
        list(D.NAME),
        D.DESIGNATION_01,
        material,
        D.MASS_STR,
        f"1:{fmt(k)}",
        org=org,
        lit=D.LIT,
        dev=D.DEV,
        chk=D.CHK,
    )
    fix_stamp_two_line_cells(sh, material=material, org=org)
    return sh


def check(sh, D=None):
    D = D0 if D is None else D
    return review(sh, code=D.DESIGNATION_01, dev=D.DEV, chk=D.CHK) + qa_extra.review(sh)


def main():
    OUT.mkdir(exist_ok=True)
    sh = build()
    png, pdf = OUT / "koleso_r1_otlivka.png", OUT / "koleso_r1_otlivka.pdf"
    issues = check(sh)
    for i in issues:
        print("ISSUE", i)
    rc = require_clean(issues)
    if rc == 0:
        sh.render(str(png), pdf=str(pdf), dpi=180)
        sh.to_dxf(str(OUT / "koleso_r1_otlivka.dxf"))
        print("saved", pdf)
    else:
        sh.render(str(png), dpi=180)
        print("draft png only", png)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
