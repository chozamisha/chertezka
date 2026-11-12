# -*- coding: utf-8 -*-
"""Чертёж отливки «Колесо рабочее» по Рисунку 1 (⌀280), А3.

Ступица + два диска + канал + вход ⌀85, глухая расточка, R65/R90 в контуре,
прибыль, МФ, стержни. Не КП-062215009.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cad import Sheet, View  # noqa: E402
import koleso_r1_data as D0  # noqa: E402
from common import DIA, fix_stamp_two_line_cells, write_tt  # noqa: E402
import qa_extra  # noqa: E402
from qa_check import review, require_clean  # noqa: E402

OUT = ROOT / "out"
SCALES = (2.0, 1.0)
FRAME_L, FRAME_B, FRAME_T = 20.0, 5.0, 292.0
TT_X0 = 252.0


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


def arc_pts(cx, cy, r, a0, a1, n=24):
    return [
        (cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
         cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
        for i in range(n + 1)
    ]


def layout(D):
    for k in SCALES:
        rp = D.C_OUT / 2 / k
        yp = FRAME_B + 12 + rp
        gap = 24.0
        ys = yp + rp + gap
        if ys - D.H_PRINT2 / k < FRAME_B + 2:
            continue
        top = ys + D.Y_RISER_TOP / k + 12
        xc_min = FRAME_L + 20 + rp + 14
        xc_max = TT_X0 - 12 - rp - 6
        if top <= FRAME_T - 2 and xc_min <= xc_max:
            return k, (xc_min + xc_max) / 2, ys, yp
    raise ValueError("Отливка с прибылью не помещается на А3 в 1:1 / 1:2")


def _r65_cut(sign, D):
    rh, y2 = D.C_HUB / 2, D.Y_DISK_UP_BOT
    cx, cy, r = sign * (rh + D.R_FILLET_TOP), y2, D.R_FILLET_TOP
    a0, a1 = (180, 208) if sign > 0 else (0, -28)
    return make_valid(Polygon(arc_pts(cx, cy, r, a0, a1, 12) + [(sign * rh, y2)]))


def _r90_lens(sign, D):
    rh, ro, y1 = D.C_HUB / 2, D.C_OUT / 2, D.Y_DISK_LO
    cx, cy, r = sign * 80.0, y1 - 70.0, 78.0
    pts = []
    for a in range(70, 110):
        ang = a if sign > 0 else 180 - a
        x = cx + r * math.cos(math.radians(ang))
        y = cy + r * math.sin(math.radians(ang))
        if rh + 5 < abs(x) < ro - 2 and y > y1:
            pts.append((x, y))
    if len(pts) < 3:
        return None
    pts = sorted(pts, key=lambda p: p[0] * sign)
    return make_valid(Polygon(pts + [(pts[-1][0], y1), (pts[0][0], y1)]))


def _corner_cut(sign, D):
    ro = D.C_OUT / 2
    cx, cy, r = sign * (ro - 18), 18.0, 18.0
    if sign > 0:
        pts = [(ro + 1, -1), (ro + 1, 18)] + arc_pts(cx, cy, r, 0, -90, 8) + [(ro + 1, -1)]
    else:
        pts = [(-ro - 1, -1), (-ro - 1, 18)] + arc_pts(cx, cy, r, 180, 270, 8) + [(-ro - 1, -1)]
    return make_valid(Polygon(pts))


def cast_body(D):
    y0, y1, y2, y3, y4 = D.Y_BOT, D.Y_DISK_LO, D.Y_DISK_UP_BOT, D.Y_DISK_UP_TOP, D.Y_HUB_TOP
    ro, rh, rs = D.C_OUT / 2, D.C_HUB / 2, D.C_SHOULDER / 2
    rb, rr, ri = D.C_BORE / 2, D.C_RECESS / 2, D.C_INLET / 2
    y_sh = y3 - min(D.SHOULDER_H, D.C_T_TOP - 2)
    body = unary_union([
        box(-rh, y3, rh, y4),
        box(-rs, y_sh, rs, y3),
        box(-ro, y2, ro, y_sh),
        box(-ro, y0, ro, y1),
        box(-rh, y1, rh, y2),
    ])
    body = body.difference(box(-ri, -5, ri, y1 - 0.05))
    for s in (1, -1):
        body = body.difference(_r65_cut(s, D))
        lens = _r90_lens(s, D)
        if lens is not None and lens.is_valid and lens.area > 10:
            body = body.difference(lens)
        body = body.difference(_corner_cut(s, D))
    bore = box(-rb, y4 - D.BORE_DEPTH, rb, y4 + 1)
    rec = box(-rr, y4 - max(D.RECESS_H, 2.0), rr, y4 + 1)
    body = make_valid(body.difference(unary_union([bore, rec])))
    if body.is_empty:
        raise RuntimeError("пустое тело отливки")
    return body


def riser_poly(D):
    rn, rr = D.D_NECK / 2, D.D_RISER / 2
    y4, yt = D.Y_HUB_TOP, D.Y_RISER_TOP
    neck_h = 22.0
    return unary_union([box(-rn, y4, rn, y4 + neck_h), box(-rr, y4 + neck_h, rr, yt)])


def detail_thin(F, D):
    y0 = D.N_BOT
    y1 = y0 + D.T_BOT
    y2 = y1 + D.H_CH
    y3 = y2 + D.T_TOP
    ro, rh, rb, ri = D.D_OUT / 2, D.D_HUB / 2, D.D_BORE / 2, D.D_INLET / 2
    y4p = D.Y_HUB_TOP - D.N_TOP
    for s in (-1, 1):
        F.seg(s * rh, y3, s * rh, y4p, "thin")
        F.seg(s * ro, y0, s * ro, y1, "thin")
        F.seg(s * ro, y2, s * ro, y3, "thin")
        F.seg(s * rb, y4p, s * rb, y4p - D.BORE_DEPTH + D.RECESS_H, "thin")
        F.seg(s * ri, y0, s * ri, y1 - 1, "thin")
    F.seg(-rh, y4p, rh, y4p, "thin")
    F.seg(-ro + 6, y0, -ri - 2, y0, "thin")
    F.seg(ri + 2, y0, ro - 6, y0, "thin")


def _vane_poly(ang0_deg, r_hub, r_tip):
    a0 = math.radians(ang0_deg)
    mid = []
    for i in range(14):
        t = i / 13
        r = r_hub + (r_tip - r_hub) * t
        bend = math.radians(24) * math.sin(t * math.pi)
        a = a0 + bend
        mid.append((r * math.cos(a), r * math.sin(a)))
    pts = []
    for i, (x, y) in enumerate(mid):
        dx, dy = (mid[i + 1][0] - x, mid[i + 1][1] - y) if i < len(mid) - 1 else (x - mid[i - 1][0], y - mid[i - 1][1])
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L * 4.0, dx / L * 4.0
        pts.append((x + nx, y + ny))
    for i, (x, y) in enumerate(reversed(mid)):
        j = len(mid) - 1 - i
        dx, dy = (mid[j][0] - mid[j - 1][0], mid[j][1] - mid[j - 1][1]) if j > 0 else (mid[1][0] - mid[0][0], mid[1][1] - mid[0][1])
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L * 4.0, dx / L * 4.0
        pts.append((x - nx, y - ny))
    return pts


def draw_section(F, sh, D, k):
    body = cast_body(D)
    riser = riser_poly(D)
    F.geom(body, "main")
    F.hatch(body, angle=45, step=2.6)
    F.geom(riser, "main")
    F.hatch(riser, angle=-45, step=3.0)
    detail_thin(F, D)

    y0, y1, y2, y3, y4 = D.Y_BOT, D.Y_DISK_LO, D.Y_DISK_UP_BOT, D.Y_DISK_UP_TOP, D.Y_HUB_TOP
    ro, rh, rb, ri = D.C_OUT / 2, D.C_HUB / 2, D.C_BORE / 2, D.C_INLET / 2
    rr = D.D_RISER / 2

    F.axis(0, -D.H_PRINT2 - 8, 0, D.Y_RISER_TOP + 8)
    y_mf = (y1 + y2) / 2
    F.seg(-ro - 6, y_mf, ro + 6, y_mf, "axis")
    tip = F.P(ro + 48, y_mf)
    sh.text(tip[0], tip[1] + 4, "МФ", h=3.5)
    sh.text(tip[0], tip[1] - 4, "В", h=3.5)
    sh.text(tip[0], tip[1] - 12, "Н", h=3.5)

    F.pl([(-rb, 0), (-rb, -D.H_PRINT2), (rb, -D.H_PRINT2), (rb, 0)], "thin", close=True)
    tip = F.P(rb, -D.H_PRINT2 / 2)
    sh.leader(tip, tip + np.array([18, -12]), "Ст. 2", arrow=True)
    tip = F.P(rr + 55, y4 + D.H_RISER * 0.5)
    sh.text(*tip, "Прибыль 1", h=3.5)

    F.dim((-ro, y0), (ro, y0), -9, f"{DIA}{fmt(D.C_OUT)}", tpos=0.82)
    F.dim((-ro, y0), (-ro, y4), 20, fmt(D.H_BODY, 1), tpos=0.6)
    F.dim((-ro, y4), (-ro, D.Y_RISER_TOP), 20, fmt(D.H_RISER), tpos=0.6)
    F.dim((ro, y1), (ro, y2), -14, fmt(D.C_H_CH), tpos=0.6)

    tip = F.P(ro + 22, y4 + 12)
    sh.text(*tip, f"{DIA}{fmt(D.C_HUB)}", h=3.5)
    tip = F.P(ro + 22, D.Y_RISER_TOP + 8)
    sh.text(*tip, f"{DIA}{fmt(D.D_RISER)}", h=3.5)
    tip = F.P(-ro - 8, y4 - 8)
    sh.text(*tip, f"{DIA}{fmt(D.C_BORE)}", h=3.5, ha="right")
    tip = F.P(-ri, y0)
    sh.leader(tip, tip + np.array([-30, -14]), f"{DIA}{fmt(D.C_INLET, 1)}", side="left", arrow=False, dot=True)

    sh.text(*(F.P(0, D.Y_RISER_TOP) + np.array([0, 12])), "А-А", h=5, ha="center")
    tip = F.P(ro, y0) + np.array([3, 0])
    sh.rough_leader(tip, tip + np.array([14, -14]), D.RA_FACES, pre=fmt(D.N_BOT, 1))


def draw_plan(Tv, sh, D, k):
    ro = D.C_OUT / 2
    rh, rs, rb = D.C_HUB / 2, D.C_SHOULDER / 2, D.C_BORE / 2
    Tv.circle(0, 0, ro)
    Tv.circle(0, 0, rh)
    Tv.circle(0, 0, rs, "thin")
    Tv.circle(0, 0, rb, "thin")
    Tv.circle(0, 0, D.C_INLET / 2, "thin")
    Tv.circle(0, 0, D.D_RISER / 2, "thin")
    Tv.axis(-ro - 4 * k, 0, ro + 4 * k, 0)
    Tv.axis(0, -ro - 4 * k, 0, ro + 4 * k)

    for i in range(D.N_VANES):
        Tv.pl(_vane_poly(25.0 + i * 90.0, rh + 4, ro - 6), "main", close=True)

    Tv.circle(0, 0, D.PCD / 2, "axis")
    for i in range(D.N_HOLES):
        a = math.radians(30.0 + i * 60.0)
        cx, cy = D.PCD / 2 * math.cos(a), D.PCD / 2 * math.sin(a)
        Tv.axis(cx - 4 * k, cy, cx + 4 * k, cy)
        Tv.axis(cx, cy - 4 * k, cx, cy + 4 * k)

    for ang in (0.0, 180.0):
        a = math.radians(ang)
        c_, s_ = math.cos(a), math.sin(a)
        p0x, p0y = ro * c_, ro * s_
        tx, ty = -s_, c_
        w, Lp = 18.0, D.L_PRINT
        Tv.pl([
            (p0x - tx * w / 2, p0y - ty * w / 2),
            (p0x - tx * w / 2 + c_ * Lp, p0y - ty * w / 2 + s_ * Lp),
            (p0x + tx * w / 2 + c_ * Lp, p0y + ty * w / 2 + s_ * Lp),
            (p0x + tx * w / 2, p0y + ty * w / 2),
        ], "thin", close=True)
    tip = Tv.P(-(ro + D.L_PRINT), 0)
    sh.leader(tip, tip + np.array([-14, 12]), "Ст. 1", side="left", arrow=True)

    c = Tv.P(0, 0)
    sh.text(c[0] - ro / k - 18, c[1] + 22, f"{DIA}{fmt(D.C_OUT)}", h=3.5, ha="right")
    sh.text(c[0] - ro / k - 18, c[1] + 14, f"{DIA}{fmt(D.PCD)}", h=3.5, ha="right")

    for sgn in (-1, 1):
        p0 = c + np.array([sgn * (ro / k + 5), 0.0])
        p1 = c + np.array([sgn * (ro / k + 12), 0.0])
        sh.seg(*p0, *p1, "cut")
        xa = p1[0] - sgn * 2.5
        sh.seg(xa, p1[1] - 9, xa, p1[1] - 3, "thin")
        sh.arrow((xa, p1[1] - 0.5), (0, 1), L=3, W=1)
        sh.text(p1[0] + sgn * 4, p1[1] - 11, "А", h=5, ha="center")


def tt_lines(D):
    return [
        "Технические требования",
        f"1. Точность отливки {D.ACCURACY} ГОСТ 26645-85.",
        f"2. Уклоны ГОСТ 3212-92: нар. {fmt_deg(D.DRAFT_EXT)}, вн. {fmt_deg(D.DRAFT_INT)}.",
        f"3. Радиусы канала R{fmt(D.R_FILLET_TOP)}, R{fmt(D.R_SHROUD)}, R{fmt(D.R_NOSE)}; прочие R{fmt(D.R_FILLET)}.",
        f"4. Усадка {fmt(D.SHRINKAGE, 1)} % (12Х18Н9ТЛ).",
        f"5. Лопасти {D.N_VANES} шт., R{fmt(D.R_VANE_OUT)}/R{fmt(D.R_VANE_IN)}.",
        f"6. Отв. {DIA}{fmt(D.D_HOLE)} на {DIA}{fmt(D.PCD)} — мехобр.",
        "7. Тонкой линией — контур детали.",
        f"8. Припуски: верх {fmt(D.N_TOP, 1)}, низ {fmt(D.N_BOT, 1)}, отв. {fmt(D.N_BORE, 1)} на сторону.",
        f"9. ΣFп:Fшл:Fст=1:1,2:1,4; ΣFп={fmt(D.SIGMA_FP, 2)} см².",
        "10. КР-Рис1-* временно (штампа на исходнике не было).",
    ]


def build(D=None):
    D = D0 if D is None else D
    k, xc, ys, yp = layout(D)
    sh = Sheet("A3")
    draw_section(View(sh, xc, ys, k), sh, D, k)
    draw_plan(View(sh, xc, yp, k), sh, D, k)
    write_tt(sh, opt(D, "TT", None) or tt_lines(D), x0=TT_X0, y_base=66, step=6.2)
    sh.rough_corner(368, 270, h=3.5, val=D.RA_GENERAL)
    material = list(D.MATERIAL)
    org = tuple(D.ORG)
    sh.frame(
        ["Колесо рабочее"],
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
