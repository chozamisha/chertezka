# -*- coding: utf-8 -*-
"""Лист МЛУ «Корпус» ПП-062215009-02, А3, 1:2."""
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


def cutline(sh, p, d, a, letter, L=8):
    p = np.asarray(p, float)
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    a = np.asarray(a, float)
    a = a / np.linalg.norm(a)
    q = p + d * L
    sh.seg(*p, *q, "cut")
    base = q - d * 1.5
    sh.seg(*base, *(base + a * 7), "thin")
    sh.arrow(base + a * 7, a, L=3.2, W=1.1)
    sh.text(*(base + a * 4.5 + d * 4.5), letter, h=5, ha="center", va="center")


def draw_section(F, sh):
    yb, ybt = 0.0, D.T_BOT_CAST
    ytb, yt = D.H_CAST - D.T_TOP_CAST, D.H_CAST
    outer = [
        (-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), (D.D_BOT / 2, ybt),
        (D.R_OUT_BOT, ybt), (D.R_OUT_TOP, ytb), (D.D_TOP / 2, ytb),
        (D.D_TOP / 2, yt), (-D.D_TOP / 2, yt), (-D.D_TOP / 2, ytb),
        (-D.R_OUT_TOP, ytb), (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    body = Polygon(outer).difference(Polygon([
        (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, ytb),
        (D.R_IN_BOT_CAST, ybt), (D.R_IN_BOT_CAST, yb),
    ]))
    F.geom(body, "main")
    F.hatch(body, angle=45, step=2.8)
    F.axis(0, -D.PRINT_BOT_H - 6, 0, yt + D.PRINT_TOP_H + 16)

    # припуски
    F.seg(-D.D_TOP / 2 + 8, yt - D.ALLOW_TOP, D.D_TOP / 2 - 8, yt - D.ALLOW_TOP, "thin")
    F.seg(-D.D_BOT / 2 + 8, yb + D.ALLOW_BOT, D.D_BOT / 2 - 8, yb + D.ALLOW_BOT, "thin")
    tip = F.P(30, yt - D.ALLOW_TOP)
    sh.rough_leader(tip, tip + np.array([22, 8]), "Ra 6,3", pre=fmt(D.ALLOW_TOP))
    tip = F.P(-50, yb + D.ALLOW_BOT)
    sh.rough_leader(tip, tip + np.array([-16, -14]), "Ra 6,3", pre=fmt(D.ALLOW_BOT), side="left")

    # стержень
    core = [
        (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, ytb),
        (D.R_IN_BOT_CAST, ybt), (D.R_IN_BOT_CAST, yb),
    ]
    F.pl(core, "thin", close=True)
    rim = Polygon(core).difference(Polygon(core).buffer(-3.0))
    F.hatch(rim, angle=135, step=3.0)
    sh.text(*F.P(0, (ybt + ytb) / 2), "ст.1", h=5, ha="center")

    # знаки стержня
    zh, zd, gap = D.PRINT_BOT_H, D.D_BORE_BOT_CAST + 14, D.PRINT_GAP
    dx = zh * math.tan(math.radians(D.PRINT_DRAFT_BOT))
    F.pl([(-zd / 2, yb), (-zd / 2 + dx, yb - zh), (zd / 2 - dx, yb - zh), (zd / 2, yb)], "thin")
    F.pl([(-zd / 2 - gap, yb), (-zd / 2 - gap + dx, yb - zh),
          (zd / 2 + gap - dx, yb - zh), (zd / 2 + gap, yb)], "thin")

    zuh, zud = D.PRINT_TOP_H, D.D_BORE_TOP_CAST + 10
    dxu = zuh * math.tan(math.radians(D.PRINT_DRAFT_TOP))
    F.pl([(-zud / 2, yt), (-zud / 2 - dxu, yt + zuh), (zud / 2 + dxu, yt + zuh), (zud / 2, yt)], "thin")

    # выпор
    vx = -D.D_TOP / 2 + 28
    F.pl([(vx - D.VENT_RISER_D / 2, yt), (vx - D.VENT_RISER_D / 2, yt + D.VENT_RISER_H),
          (vx + D.VENT_RISER_D / 2, yt + D.VENT_RISER_H), (vx + D.VENT_RISER_D / 2, yt)], "thin")
    sh.leader(F.P(vx - D.VENT_RISER_D / 2, yt + D.VENT_RISER_H * 0.4),
              F.P(vx - D.VENT_RISER_D / 2, yt + D.VENT_RISER_H * 0.4) + [-20, -8],
              f"Выпор {DIA}{fmt(D.VENT_RISER_D)}", side="left", arrow=False, dot=True)

    # МФ
    xm1 = D.D_BOT / 2 + 48
    F.pl([(-D.D_BOT / 2 - 20, yb), (xm1, yb)], "mf")
    pe = F.P(xm1 + 6, yb)
    sh.seg(pe[0], pe[1] - 8, pe[0], pe[1] + 8, "main")
    sh.arrow((pe[0], pe[1] + 8), (0, 1))
    sh.arrow((pe[0], pe[1] - 8), (0, -1))
    sh.text(pe[0] + 3, pe[1] + 4, "В", h=5)
    sh.text(pe[0] + 3, pe[1] - 5, "Н", h=5)
    sh.text(pe[0] - 8, pe[1] + 2, "МФ", h=5, ha="center")

    # литник справа
    xs = D.D_BOT / 2 + 62
    F.pl([(xs - D.D_CUP / 2, yt + 14), (xs + D.D_CUP / 2, yt + 14),
          (xs + D.D_SPRUE_TOP / 2, yt), (xs - D.D_SPRUE_TOP / 2, yt)], "thin", close=True)
    F.pl([(xs - D.D_SPRUE_TOP / 2, yt), (xs - D.D_SPRUE / 2, yb),
          (xs + D.D_SPRUE / 2, yb), (xs + D.D_SPRUE_TOP / 2, yt)], "thin", close=True)
    sh.leader(F.P(xs + 2, yt + 8), F.P(xs + 2, yt + 8) + [12, 8], "Чаша", arrow=False, dot=True)
    sh.leader(F.P(xs + D.D_SPRUE / 2 + 1, yb + (yt - yb) * 0.25),
              F.P(xs + D.D_SPRUE / 2 + 1, yb + (yt - yb) * 0.25) + [12, -14],
              f"Стояк {DIA}{fmt(D.D_SPRUE)}", arrow=False, dot=True)

    x_fl = D.D_BOT / 2
    F.pl([(x_fl, yb + D.SLAG_H / 2), (xs - D.D_SPRUE / 2, yb + D.SLAG_H / 2),
          (xs - D.D_SPRUE / 2, yb - D.SLAG_H / 2), (x_fl, yb - D.SLAG_H / 2)], "thin", close=True)
    mid_run = (x_fl + xs - D.D_SPRUE / 2) / 2
    sh.leader(F.P(mid_run, yb + D.SLAG_H / 2), F.P(mid_run, yb + D.SLAG_H / 2) + [6, 18],
              "Шлакоуловитель", arrow=False, dot=True)

    xf = x_fl - 14
    F.pl([(xf - D.FEED_W / 2, yb + D.SLAG_H / 2), (xf + D.FEED_W / 2, yb + D.SLAG_H / 2),
          (xf + D.FEED_W / 2, yb - D.FEED_H), (xf - D.FEED_W / 2, yb - D.FEED_H)], "thin", close=True)
    sh.leader(F.P(xf - D.FEED_W / 2, yb - D.FEED_H / 2),
              F.P(xf - D.FEED_W / 2, yb - D.FEED_H / 2) + [-22, -10],
              "Питатель  2 шт.", side="left", arrow=False, dot=True)

    yb_cut = yb + (yt - yb) * 0.7
    cutline(sh, F.P(xs - D.D_SPRUE_TOP / 2 - 2, yb_cut), [-1, 0], [0, 1], "Б", L=7)
    cutline(sh, F.P(xs + D.D_SPRUE_TOP / 2 + 2, yb_cut), [1, 0], [0, 1], "Б", L=7)
    cutline(sh, F.P(mid_run + 4, yb + D.SLAG_H / 2 + 1), [0, 1], [1, 0], "В", L=6)
    cutline(sh, F.P(mid_run + 4, yb - D.SLAG_H / 2 - 1), [0, -1], [1, 0], "В", L=6)
    cutline(sh, F.P(xf - D.FEED_W / 2 - 2, yb - D.FEED_H / 2), [-1, 0], [0, -1], "Г", L=8)
    cutline(sh, F.P(xf + D.FEED_W / 2 + 2, yb - D.FEED_H / 2), [1, 0], [0, -1], "Г", L=8)

    F.dim((-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), -14, f"{DIA}{fmt(D.D_BOT)}", tpos=0.3)
    F.dim((-D.D_BOT / 2 - 8, yb), (-D.D_BOT / 2 - 8, yt), 0, fmt(D.H_CAST),
          ext1=False, ext2=False, tpos=0.55)
    sh.text(*F.P(55, yt + D.PRINT_TOP_H + 18), "А-А", h=5, ha="center")


def draw_plan_one(Tv, ox):
    for d, kind in ((D.D_BOT, "main"), (D.D_TOP, "main"), (D.R_IN_TOP_CAST * 2, "main")):
        a = np.linspace(0, 2 * math.pi, 48, endpoint=False)
        r = d / 2
        Tv.pl([(ox + r * math.cos(t), r * math.sin(t)) for t in a], kind, close=True)
    Tv.axis(ox - D.D_BOT / 2 - 4, 0, ox + D.D_BOT / 2 + 4, 0)
    Tv.axis(ox, -D.D_BOT / 2 - 4, ox, D.D_BOT / 2 + 4)
    for i in range(D.N_RIBS):
        ang = math.radians(30 + i * 60)
        cax, cay = math.cos(ang), math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        hw = D.RIB_W / 2
        r1, r2 = D.D_TOP / 2 + 2, D.D_BOT / 2 - 4
        Tv.pl([
            (ox + cax * r1 + nx * hw, cay * r1 + ny * hw),
            (ox + cax * r2 + nx * hw, cay * r2 + ny * hw),
            (ox + cax * r2 - nx * hw, cay * r2 - ny * hw),
            (ox + cax * r1 - nx * hw, cay * r1 - ny * hw),
        ], "main", close=True)


def draw_gating(sh, sx=372):
    sh.text(sx, 278, "Б-Б", h=4.5, ha="center")
    cy = 258
    sh.circle(sx, cy, D.D_SPRUE / 2, "main")
    sh.dim((sx - D.D_SPRUE / 2, cy), (sx + D.D_SPRUE / 2, cy), 6, f"{DIA}{fmt(D.D_SPRUE)}")
    sh.text(sx, cy - D.D_SPRUE / 2 - 7, f"Fст={fmt(D.F_SPRUE, 2)}", h=3.5, ha="center")

    sh.text(sx, 222, "В-В", h=4.5, ha="center")
    by0 = 186
    tr = [(sx - D.SLAG_W1 / 2, by0 + D.SLAG_H), (sx + D.SLAG_W1 / 2, by0 + D.SLAG_H),
          (sx + D.SLAG_W0 / 2, by0), (sx - D.SLAG_W0 / 2, by0)]
    sh.pl(tr, "main", close=True)
    sh.dim(tr[3], tr[2], -5, fmt(D.SLAG_W0))
    sh.dim((sx + D.SLAG_W1 / 2, by0), (sx + D.SLAG_W1 / 2, by0 + D.SLAG_H), -6, fmt(D.SLAG_H, 1))
    sh.text(sx, by0 - 10, f"Fшл={fmt(D.F_SLAG, 2)}", h=3.5, ha="center")

    sh.text(sx, 160, "Г-Г", h=4.5, ha="center")
    vy0 = 132
    rc = [(sx - D.FEED_W / 2, vy0), (sx + D.FEED_W / 2, vy0),
          (sx + D.FEED_W / 2, vy0 + D.FEED_H), (sx - D.FEED_W / 2, vy0 + D.FEED_H)]
    sh.pl(rc, "main", close=True)
    sh.dim(rc[0], rc[1], -5, fmt(D.FEED_W))
    sh.dim(rc[1], rc[2], -6, fmt(D.FEED_H, 1))
    sh.text(sx - D.FEED_W / 2 - 2, vy0 + D.FEED_H / 2 + 3, f"Fп={fmt(D.F_ONE_FEED, 2)}×2", h=3.5, ha="right")
    sh.text(sx - D.FEED_W / 2 - 2, vy0 + D.FEED_H / 2 - 4, "ΣFп:Fшл:Fст=1:1,1:1,2", h=3.5, ha="right")


def build():
    sh = Sheet("A3")
    # сечение сверху; план снизу — одна отливка в опоке (2-я — по ТТ; иначе ⌀300×2 не влезают в А3 1:2)
    F = View(sh, 118, 212, K)
    fl = D.D_BOT / 2 + 55  # 205
    fw = D.D_BOT / 2 + 18  # 168 — опока охватывает ⌀300
    ox = 24.0 + fl / K  # ≈126.5 — опока справа ≤ ~230, до ТТ
    # oy: низ опоки > рамка/штамп, верх не врезается в сечение
    Tv = View(sh, ox, 5.0 + fw / K + 2.0, K)  # ≈91

    draw_section(F, sh)
    draw_plan_one(Tv, 0.0)

    # литник справа от отливки в плане
    a = np.linspace(0, 2 * math.pi, 36, endpoint=False)
    xs = D.D_BOT / 2 + 40
    for r in (D.D_CUP / 2, D.D_SPRUE / 2):
        Tv.pl([(xs + r * math.cos(t), r * math.sin(t)) for t in a], "thin", close=True)
    hw = D.SLAG_W1 / 2
    Tv.pl([(D.D_BOT / 2, -hw), (xs - D.D_SPRUE / 2, -hw),
           (xs - D.D_SPRUE / 2, hw), (D.D_BOT / 2, hw)], "thin", close=True)
    Tv.pl([(D.D_BOT / 2, -D.FEED_W / 2), (D.D_BOT / 2 - 16, -D.FEED_W / 2),
           (D.D_BOT / 2 - 16, D.FEED_W / 2), (D.D_BOT / 2, D.FEED_W / 2)], "thin", close=True)

    Tv.pl([(-fl, -fw), (fl, -fw), (fl, fw), (-fl, fw)], "thin", close=True)
    sh.text(*Tv.P(-fl + 14, -fw + 8), "Опока", h=3.5)

    Tv.pl([(-fl + 4, 0), (fl - 6, 0)], "mf")
    pe = Tv.P(-D.D_BOT / 2 - 18, 0)
    sh.seg(pe[0], pe[1] - 14, pe[0], pe[1] + 14, "main")
    sh.arrow(pe + [0, 14], [0, 1])
    sh.arrow(pe - [0, 14], [0, -1])
    sh.text(pe[0] + 5, pe[1] + 12, "В", h=5)
    sh.text(pe[0] + 5, pe[1] - 14, "Н", h=5)
    sh.text(pe[0] + 16, pe[1] + 1.5, "МФ", h=5)

    draw_gating(sh, sx=372)

    TT = [
        "Технические требования",
        "1. ПГС; 2 отливки (на плане — 1); метал. плита.",
        "2. Разъём по ⌀300 (МФ).",
        "3. Ст.1 — 5°/12°, зазор 0,5.",
        "4. Точность 9-7-12-9 ГОСТ 26645-85.",
        "5. Уклоны ГОСТ 3212-92; усадка 1 %.",
        f"6. Tзал 1340…1380 °С; τ≈{fmt(D.TAU_FILL, 1)} с.",
        "7. ΣFп:Fшл:Fст = 1:1,1:1,2.",
    ]
    write_tt(sh, TT, x0=248, y_base=66, step=6)

    sh.frame(
        ["Корпус"],
        D.DESIGNATION_02,
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
    issues = review(sh, code=D.DESIGNATION_02)
    png, pdf = OUT / "mlu.png", OUT / "mlu.pdf"
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
