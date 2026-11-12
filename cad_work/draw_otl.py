# -*- coding: utf-8 -*-
"""Лист отливки корпуса (два фланца, конусная полость), А3.

build(D) принимает любой объект с атрибутами как у korpus_data: по умолчанию
эталон ПП-062215009, из пайплайна «деталь → отливка» — параметры CastingDraft.
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
import korpus_data  # noqa: E402
from common import DIA, fix_stamp_two_line_cells, write_tt  # noqa: E402
import qa_extra  # noqa: E402
from qa_check import review, require_clean  # noqa: E402

OUT = ROOT / "out"
SCALES = (1.0, 2.0)  # ГОСТ 2.302, без 1:1,5 и 1:1,75
FRAME_L, FRAME_B, FRAME_T = 20.0, 5.0, 292.0
TT_X0 = 242.0
SIDE = 24.0  # место сбоку от плана под знак секущей и букву


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
    """Масштаб и опорные точки видов. ValueError, если лист не вмещает отливку."""
    for k in SCALES:
        rp = max(D.D_BOT, D.D_TOP) / 2 / k
        hc = D.H_CAST / k
        yp = FRAME_B + 14 + rp
        ys = yp + rp + 4 + 8 + 19
        top = ys + hc + 17 + 16
        xc_min = FRAME_L + 1 + rp + SIDE
        xc_max = TT_X0 - 2 - rp - SIDE
        if top <= FRAME_T - 2 and xc_min <= xc_max:
            return k, (xc_min + xc_max) / 2, ys, yp
    raise ValueError(
        "Отливка не помещается на А3 в масштабах 1:1 и 1:2 "
        f"(⌀{fmt(max(D.D_BOT, D.D_TOP))}, высота {fmt(D.H_CAST, 1)})"
    )


def cast_polys(D):
    yb, ybt = 0.0, D.T_BOT_CAST
    ytb, yt = D.H_CAST - D.T_TOP_CAST, D.H_CAST
    outer = [
        (-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), (D.D_BOT / 2, ybt),
        (D.R_OUT_BOT, ybt), (D.R_OUT_TOP, ytb), (D.D_TOP / 2, ytb),
        (D.D_TOP / 2, yt), (-D.D_TOP / 2, yt), (-D.D_TOP / 2, ytb),
        (-D.R_OUT_TOP, ytb), (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    inner = Polygon([
        (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, ytb),
        (D.R_IN_BOT_CAST, ybt), (D.R_IN_BOT_CAST, yb),
    ])
    return Polygon(outer).difference(inner), yb, ybt, ytb, yt


def detail_thin(F, D):
    """Контур детали после обработки тонкой линией (ГОСТ 3.1125-88)."""
    y0 = D.ALLOW_BOT
    y1 = y0 + D.T_BOT_PART
    y2 = y0 + D.H_PART - D.T_TOP_PART
    y3 = y0 + D.H_PART
    for s in (-1, 1):
        F.seg(s * D.R_IN_BOT, y0, s * D.D_BOT / 2, y0, "thin")
        F.seg(s * D.R_IN_TOP, y3, s * D.D_TOP / 2, y3, "thin")
        F.pl([(s * D.R_IN_BOT, y0), (s * D.R_IN_BOT, y1),
              (s * D.R_IN_TOP, y2), (s * D.R_IN_TOP, y3)], "thin")


def vdim(F, x, y0, y1, off, txt, k, tpos=0.5):
    """Вертикальный размер; при коротком участке стрелки снаружи."""
    F.dim((x, y0), (x, y1), off, txt, tpos=tpos, out=(y1 - y0) / k < 9.0)


def draw_section(F, sh, D, k):
    body, yb, ybt, ytb, yt = cast_polys(D)
    F.geom(body, "main")
    F.hatch(body, angle=45, step=2.8)
    detail_thin(F, D)
    F.axis(0, -4 * k, 0, D.H_CAST + 4 * k)

    F.dim((-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), 10,
          f"{DIA}{fmt(D.D_BORE_TOP_CAST)}", tpos=0.30)
    F.dim((-D.D_TOP / 2, yt), (D.D_TOP / 2, yt), 17, f"{DIA}{fmt(D.D_TOP)}", tpos=0.70)
    F.dim((-D.R_IN_BOT_CAST, yb), (D.R_IN_BOT_CAST, yb), -10,
          f"{DIA}{fmt(D.D_BORE_BOT_CAST)}", tpos=0.30)
    F.dim((-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), -17, f"{DIA}{fmt(D.D_BOT)}", tpos=0.70)

    xr = max(D.D_BOT, D.D_TOP) / 2
    vdim(F, D.D_BOT / 2, yb, ybt, -10 - (xr - D.D_BOT / 2) / k, fmt(D.T_BOT_CAST), k)
    vdim(F, xr, yb, yt, -17, fmt(D.H_CAST), k, tpos=0.55)
    if D.D_TOP < D.D_BOT:
        F.seg(D.D_TOP / 2 + k, yt, xr, yt, "thin")
    elif D.D_BOT < D.D_TOP:
        F.seg(D.D_BOT / 2 + k, yb, xr, yb, "thin")
    vdim(F, -D.D_TOP / 2, ytb, yt, 10, fmt(D.T_TOP_CAST), k)

    mid = ybt + 0.55 * (ytb - ybt)
    ro = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * (mid - ybt) / max(ytb - ybt, 1e-9)
    tip = F.P(ro, mid)
    sh.leader(tip, tip + np.array([14, 9]), fmt(D.WALL), arrow=True)
    tip = F.P(-D.R_OUT_BOT, ybt)
    sh.leader(tip, tip + np.array([-14, 9]), f"R{fmt(D.R_FILLET)}", side="left", arrow=True)

    # припуск перед знаком шероховатости обрабатываемой поверхности (ГОСТ 3.1125-88);
    # знаки стоят на выносных линиях торцов, а не на размерных
    ra = opt(D, "RA_FACES", "Ra 6,3")
    if D.D_TOP < D.D_BOT:
        sh.rough(F.P(D.D_TOP / 2, yt) + np.array([11.0, 0.0]), (0, 1), ra, pre=fmt(D.ALLOW_TOP, 1))
    else:
        tip = F.P(-(D.R_IN_TOP_CAST + D.D_TOP / 2) / 2, yt)
        sh.rough_leader(tip, tip + np.array([-30, 30]), ra, pre=fmt(D.ALLOW_TOP, 1), side="left")
    tip = F.P(xr, yb) + np.array([5.0, 0.0])
    sh.rough_leader(tip, tip + np.array([8, -12]), ra, pre=fmt(D.ALLOW_BOT, 1))

    sh.text(*(F.P(0, yt) + np.array([0, 26])), "А-А", h=5, ha="center")


def draw_plan(Tv, sh, D, k):
    Tv.circle(0, 0, D.D_BOT / 2)
    Tv.circle(0, 0, D.D_TOP / 2)
    Tv.circle(0, 0, D.R_IN_TOP_CAST)
    Tv.circle(0, 0, D.R_IN_TOP, "thin")
    rmax = max(D.D_BOT, D.D_TOP) / 2
    Tv.axis(-rmax - 4 * k, 0, rmax + 4 * k, 0)
    Tv.axis(0, -rmax - 4 * k, 0, rmax + 4 * k)

    hw = D.RIB_W / 2
    r1 = D.D_TOP / 2
    r2 = opt(D, "RIB_R_OUT", D.D_BOT / 2 - 6)
    step = 360.0 / D.N_RIBS
    a0 = opt(D, "RIB_ANGLE0", step / 2)
    rib_visible = D.N_RIBS > 0 and r2 > r1 > hw
    if rib_visible:
        x1 = math.sqrt(r1 * r1 - hw * hw)
        for i in range(D.N_RIBS):
            ang = math.radians(a0 + i * step)
            c, s = math.cos(ang), math.sin(ang)
            Tv.pl([(c * u - s * v, s * u + c * v)
                   for u, v in ((x1, hw), (r2, hw), (r2, -hw), (x1, -hw))], "main")

    # линия сопряжения конуса с нижним фланцем видна сверху между рёбрами
    rj = D.R_OUT_BOT
    if rj > D.D_TOP / 2:
        if rib_visible and r2 > rj:
            da = math.degrees(math.asin(hw / rj))
            for i in range(D.N_RIBS):
                Tv.circle(0, 0, rj, "main", a0 + i * step + da, a0 + (i + 1) * step - da)
        else:
            Tv.circle(0, 0, rj)

    # отверстия не льются: только оси будущих отверстий
    for pcd, n, ang0, half in (
        (D.PCD_OUTER, D.N_OUTER, opt(D, "PCD_OUTER_ANGLE0", 0.0), 4.0),
        (D.PCD_INNER, D.N_INNER, opt(D, "PCD_INNER_ANGLE0", 45.0), 3.0),
    ):
        if not n:
            continue
        Tv.circle(0, 0, pcd / 2, "axis")
        for i in range(n):
            a = math.radians(ang0 + i * 360.0 / n)
            cx, cy = pcd / 2 * math.cos(a), pcd / 2 * math.sin(a)
            Tv.axis(cx - half * k, cy, cx + half * k, cy)
            Tv.axis(cx, cy - half * k, cx, cy + half * k)

    # размеры ⌀ осевых окружностей: цифры в свободном поле литого отверстия
    rb = D.R_IN_TOP_CAST / k
    for pcd, n, ang, side in ((D.PCD_OUTER, D.N_OUTER, 15.0, 1), (D.PCD_INNER, D.N_INNER, -15.0, -1)):
        if not n:
            continue
        txt = f"{DIA}{fmt(pcd)}"
        a = math.radians(ang)
        c, s = math.cos(a), math.sin(a)
        r_sheet = pcd / 2 / k
        reach = 7.0 + text_width(txt, 3.5)
        if rb >= reach + 3.0:
            tpos = 0.5 + side * (7.0 + text_width(txt, 3.5) / 2) / (2 * r_sheet)
            Tv.dim((-pcd / 2 * c, -pcd / 2 * s), (pcd / 2 * c, pcd / 2 * s), 0, txt,
                   ext1=False, ext2=False, tpos=tpos)
        else:
            tip = Tv.P(side * pcd / 2 * math.cos(math.radians(75)), -pcd / 2 * math.sin(math.radians(75)))
            knee = np.array([tip[0] + side * 10, Tv.P(0, -rmax)[1] - 7])
            sh.leader(tip, knee, txt, side="right" if side > 0 else "left", arrow=True)

    # секущая плоскость А-А: стрелка взгляда упирается в штрих
    r_sheet = rmax / k
    for sgn in (-1, 1):
        p0 = Tv.P(0, 0) + np.array([sgn * (r_sheet + 6), 0.0])
        p1 = Tv.P(0, 0) + np.array([sgn * (r_sheet + 16), 0.0])
        sh.seg(*p0, *p1, "cut")
        xa = p1[0] - sgn * 2.5
        sh.seg(xa, p1[1] - 9.5, xa, p1[1] - 3.5, "thin")
        sh.arrow((xa, p1[1] - 0.55), (0, 1), L=3.2, W=1.1)
        sh.text(p1[0] + sgn * 3.5, p1[1] - 9.5, "А", h=5, ha="center")


def tt_lines(D):
    """Технические требования отливки из параметров, без чисел «с потолка»."""
    body = [
        f"Точность отливки {opt(D, 'ACCURACY', '9-7-12-9')} ГОСТ 26645-85.",
        ("Формовочные уклоны по ГОСТ 3212-92:",
         f"наружные {fmt_deg(D.DRAFT_EXT)}, внутренние {fmt_deg(D.DRAFT_INT)}."),
        f"Неуказанные литейные радиусы R{fmt(D.R_FILLET)}.",
    ]
    hardness = opt(D, "HARDNESS", "НВ 163…229")
    if hardness:
        body.append(f"Твёрдость {hardness}.")
    heat = opt(D, "HEAT_TREATMENT", "отжиг 500…550 °С")
    if heat:
        body.append(f"Термическая обработка: {heat}.")
    body.append(f"Литейная усадка {fmt(D.SHRINKAGE, 1)} %.")
    machined = opt(D, "MACHINED_NOTE", f"Отверстия {DIA}{fmt(D.D_THRU)}, цековки и М8 — мехобработкой.")
    if machined:
        body.append(machined)
    body.append("Тонкой линией показан контур детали.")
    body.append(f"Припуск на обработку отверстия {fmt(D.ALLOW_BORE, 1)} мм на сторону.")
    body.append(f"ΣFп:Fшл:Fст = 1:1,1:1,2; ΣFп={fmt(D.SIGMA_FP, 2)} см².")

    lines = ["Технические требования"]
    for i, item in enumerate(body, 1):
        if isinstance(item, tuple):
            lines.append(f"{i}. {item[0]}")
            lines.extend(f"    {extra}" for extra in item[1:])
        else:
            lines.append(f"{i}. {item}")
    return lines


def build(D=None):
    D = korpus_data if D is None else D
    k, xc, ys, yp = layout(D)
    sh = Sheet("A3")
    draw_section(View(sh, xc, ys, k), sh, D, k)
    draw_plan(View(sh, xc, yp, k), sh, D, k)
    write_tt(sh, opt(D, "TT", None) or tt_lines(D), x0=TT_X0, y_base=66, step=6)

    sh.rough_corner(368, 270, h=3.5, val=opt(D, "RA_GENERAL", "Ra 12,5"))
    material = list(D.MATERIAL)
    org = tuple(opt(D, "ORG", ("СФУ ИЦМ", "гр. ЗЦМ22-01Б")))
    sh.frame(
        list(opt(D, "NAME", ["Корпус"])),
        D.DESIGNATION_01,
        material,
        D.MASS_STR,
        f"1:{fmt(k)}",
        org=org,
        lit=opt(D, "LIT", "У"),
        dev=D.DEV,
        chk=D.CHK,
    )
    fix_stamp_two_line_cells(sh, material=material, org=org)
    return sh


def check(sh, D=None):
    """Все автопроверки листа: qa_check + касание текста и линий."""
    D = korpus_data if D is None else D
    return review(sh, code=D.DESIGNATION_01, dev=D.DEV, chk=D.CHK) + qa_extra.review(sh)


def main():
    OUT.mkdir(exist_ok=True)
    sh = build()
    png, pdf = OUT / "otlivka.png", OUT / "otlivka.pdf"
    rc = require_clean(check(sh))
    if rc == 0:
        sh.render(str(png), pdf=str(pdf), dpi=180)
        print("saved", pdf)
    else:
        sh.render(str(png), dpi=180)
        print("draft png only", png)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
