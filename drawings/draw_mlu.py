# -*- coding: utf-8 -*-
"""Лист 02. Корпус. Элементы литейной формы — А3, М 1:2."""
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


def fmt(v, n=1):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.*f" % (n, v)).replace(".", ",")


def cutline(sh, p, d, a, letter, L=8):
    p = np.asarray(p, float)
    d = np.asarray(d, float); d /= np.linalg.norm(d)
    a = np.asarray(a, float); a /= np.linalg.norm(a)
    q = p + d * L
    sh.seg(*p, *q, "cut")
    base = q - d * 1.5
    sh.seg(*base, *(base + a * 7), "thin")
    sh.arrow(base + a * 7, a, L=3.2, W=1.1)
    sh.text(*(base + a * 4.5 + d * 4.5), letter, h=5, ha="center", va="center")


def draw_section(F, sh):
    yb, ybt = 0.0, D.T_BOT_CAST
    ytb, yt = D.H_CAST - D.T_TOP_CAST, D.H_CAST
    left = [
        (-D.D_BOT / 2, yb), (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt),
        (-D.R_IN_TOP_CAST, ytb), (-D.R_IN_TOP_CAST, yt), (-D.D_TOP / 2, yt),
        (-D.D_TOP / 2, ytb), (-D.R_OUT_TOP, ytb), (-D.R_OUT_BOT, ybt), (-D.D_BOT / 2, ybt),
    ]
    right = [
        (D.D_BOT / 2, yb), (D.R_IN_BOT_CAST, yb), (D.R_IN_BOT_CAST, ybt),
        (D.R_IN_TOP_CAST, ytb), (D.R_IN_TOP_CAST, yt), (D.D_TOP / 2, yt),
        (D.D_TOP / 2, ytb), (D.R_OUT_TOP, ytb), (D.R_OUT_BOT, ybt), (D.D_BOT / 2, ybt),
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
        (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, ytb),
        (D.R_IN_BOT_CAST, ybt), (D.R_IN_BOT_CAST, yb),
    ], "main", close=True)

    rib_y = ybt + 0.45 * (ytb - ybt)
    t = (rib_y - ybt) / max(ytb - ybt, 1)
    rx = D.R_OUT_BOT + (D.R_OUT_TOP - D.R_OUT_BOT) * t
    F.pl([(D.R_OUT_BOT, ybt), (rx, rib_y), (D.D_BOT / 2 - 22, ybt)], "main")
    F.axis(0, -D.PRINT_BOT_H - 8, 0, yt + D.PRINT_TOP_H + 18)

    # припуски
    F.seg(-D.D_TOP / 2 + 6, yt - D.ALLOW_TOP, D.D_TOP / 2 - 6, yt - D.ALLOW_TOP, "thin")
    F.seg(-D.D_BOT / 2 + 6, yb + D.ALLOW_BOT, D.D_BOT / 2 - 6, yb + D.ALLOW_BOT, "thin")
    # Ra сверху — полка влево-вниз, отдельно от ⌀200 сверху
    tip = F.P(-D.D_TOP / 2 + 8, yt - D.ALLOW_TOP)
    sh.rough_leader(tip, tip + np.array([-18, -14]), "Ra 6,3", pre=fmt(D.ALLOW_TOP, 0), side="left")
    # Ra снизу — дальше влево-вниз
    tip = F.P(-D.D_BOT / 2 + 25, yb + D.ALLOW_BOT)
    sh.rough_leader(tip, tip + np.array([-30, -20]), "Ra 6,3", pre=fmt(D.ALLOW_BOT, 0), side="left")

    # стержень
    core = [
        (-D.R_IN_BOT_CAST, yb), (-D.R_IN_BOT_CAST, ybt), (-D.R_IN_TOP_CAST, ytb),
        (-D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, yt), (D.R_IN_TOP_CAST, ytb),
        (D.R_IN_BOT_CAST, ybt), (D.R_IN_BOT_CAST, yb),
    ]
    F.pl(core, "thin", close=True)
    rim = Polygon(core).difference(Polygon(core).buffer(-3.0))
    F.hatch(rim, angle=135, step=3.0)
    sh.text(*F.P(0, (ybt + ytb) / 2 - 4), "ст.1", h=5, ha="center")

    zh, zd, gap = D.PRINT_BOT_H, D.D_BORE_BOT_CAST + 14, D.PRINT_GAP
    dx = zh * math.tan(math.radians(D.PRINT_DRAFT_BOT))
    F.pl([(-zd / 2, yb), (-zd / 2 + dx, yb - zh), (zd / 2 - dx, yb - zh), (zd / 2, yb)], "thin")
    F.pl([(-zd / 2 - gap, yb), (-zd / 2 - gap + dx, yb - zh),
          (zd / 2 + gap - dx, yb - zh), (zd / 2 + gap, yb)], "thin")
    sh.leader(F.P(zd / 2 - 3, yb - 4), F.P(zd / 2 - 3, yb - 4) + [22, 12],
              "⌀%s" % fmt(zd, 0), arrow=False, dot=True)
    # зазор — слева от нижнего знака, вдали от В/Г у литника
    sh.leader(F.P(-zd / 2 - gap, yb - zh * 0.55),
              F.P(-zd / 2 - gap, yb - zh * 0.55) + [-26, -12],
              "зазор %s" % fmt(gap, 1), side="left", arrow=False, dot=True)
    sh.leader(F.P(-zd / 2 + 2, yb - zh * 0.35), F.P(-zd / 2 + 2, yb - zh * 0.35) + [-22, 8],
              "%s°" % fmt(D.PRINT_DRAFT_BOT, 0), side="left", arrow=False, dot=True)

    zuh, zud = D.PRINT_TOP_H, D.D_BORE_TOP_CAST + 10
    dxu = zuh * math.tan(math.radians(D.PRINT_DRAFT_TOP))
    F.pl([(-zud / 2, yt), (-zud / 2 - dxu, yt + zuh), (zud / 2 + dxu, yt + zuh), (zud / 2, yt)], "thin")
    F.pl([(-zud / 2 - gap, yt), (-zud / 2 - gap - dxu, yt + zuh),
          (zud / 2 + gap + dxu, yt + zuh), (zud / 2 + gap, yt)], "thin")
    sh.leader(F.P(-zud / 2 - dxu / 2, yt + zuh * 0.55),
              F.P(-zud / 2 - dxu / 2, yt + zuh * 0.55) + [-14, 8],
              "%s°" % fmt(D.PRINT_DRAFT_TOP, 0), side="left", arrow=False, dot=True)

    # вентканал — полка вправо, ниже рамки
    F.pl([(-D.VENT_D / 2, yt + zuh), (-D.VENT_D / 2, yt + zuh + 12)], "hidden")
    F.pl([(D.VENT_D / 2, yt + zuh), (D.VENT_D / 2, yt + zuh + 12)], "hidden")
    tip = F.P(D.VENT_D / 2, yt + zuh + 10)
    sh.leader(tip, tip + np.array([30, 4]), "вентканал", arrow=False, dot=True)

    # выпор слева — полки внутри рамки, отдельно от Ra
    vx = -D.D_TOP / 2 + 26
    F.pl([(vx - D.VENT_RISER_D / 2, yt), (vx - D.VENT_RISER_D / 2, yt + D.VENT_RISER_H),
          (vx + D.VENT_RISER_D / 2, yt + D.VENT_RISER_H), (vx + D.VENT_RISER_D / 2, yt)], "thin")
    sh.leader(F.P(vx - D.VENT_RISER_D / 2, yt + D.VENT_RISER_H * 0.7),
              F.P(vx - D.VENT_RISER_D / 2, yt + D.VENT_RISER_H * 0.7) + [-12, 6],
              "Выпор ⌀%s" % fmt(D.VENT_RISER_D, 0), side="left", arrow=False, dot=True)
    sh.leader(F.P(vx + D.VENT_RISER_D / 2, yt + D.VENT_RISER_H * 0.35),
              F.P(vx + D.VENT_RISER_D / 2, yt + D.VENT_RISER_H * 0.35) + [16, 4],
              "h=%s" % fmt(D.VENT_RISER_H, 0), arrow=False, dot=True)

    # МФ
    xm1 = D.D_BOT / 2 + 55
    F.pl([(-D.D_BOT / 2 - 28, yb), (xm1, yb)], "mf")
    pe = F.P(xm1 + 8, yb)
    sh.seg(pe[0], pe[1] - 9, pe[0], pe[1] + 9, "main")
    sh.arrow((pe[0], pe[1] + 9), (0, 1))
    sh.arrow((pe[0], pe[1] - 9), (0, -1))
    sh.text(pe[0] + 3, pe[1] + 5, "В", h=5)
    sh.text(pe[0] + 3, pe[1] - 6, "Н", h=5)
    sh.text(pe[0] - 10, pe[1] + 2.5, "МФ", h=5, ha="center")

    # литник
    xs = D.D_BOT / 2 + 70
    F.pl([(xs - D.D_CUP / 2, yt + 18), (xs + D.D_CUP / 2, yt + 18),
          (xs + D.D_SPRUE_TOP / 2, yt), (xs - D.D_SPRUE_TOP / 2, yt)], "thin", close=True)
    F.pl([(xs - D.D_SPRUE_TOP / 2, yt), (xs - D.D_SPRUE / 2, yb),
          (xs + D.D_SPRUE / 2, yb), (xs + D.D_SPRUE_TOP / 2, yt)], "thin", close=True)
    F.dim((xs - D.D_CUP / 2, yt + 18), (xs + D.D_CUP / 2, yt + 18), 5, "⌀%s" % fmt(D.D_CUP, 0))
    sh.leader(F.P(xs + 2, yt + 10), F.P(xs + 2, yt + 10) + [14, 8], "Чаша", arrow=False, dot=True)
    # стояк — полка вниз-вправо, ниже колонки ТТ
    sh.leader(F.P(xs + D.D_SPRUE / 2 + 1, yb + (yt - yb) * 0.22),
              F.P(xs + D.D_SPRUE / 2 + 1, yb + (yt - yb) * 0.22) + [14, -16],
              "Стояк ⌀%s" % fmt(D.D_SPRUE, 0), arrow=False, dot=True)

    x_fl = D.D_BOT / 2
    F.pl([(x_fl, yb + D.SLAG_H / 2), (xs - D.D_SPRUE / 2, yb + D.SLAG_H / 2),
          (xs - D.D_SPRUE / 2, yb - D.SLAG_H / 2), (x_fl, yb - D.SLAG_H / 2)], "thin", close=True)
    mid_run = (x_fl + xs - D.D_SPRUE / 2) / 2
    sh.leader(F.P(mid_run, yb + D.SLAG_H / 2), F.P(mid_run, yb + D.SLAG_H / 2) + [8, 22],
              "Шлакоуловитель", arrow=False, dot=True)

    xf = x_fl - 16
    F.pl([(xf - D.FEED_W / 2, yb + D.SLAG_H / 2), (xf + D.FEED_W / 2, yb + D.SLAG_H / 2),
          (xf + D.FEED_W / 2, yb - D.FEED_H), (xf - D.FEED_W / 2, yb - D.FEED_H)], "thin", close=True)
    # питатель — полка влево-вниз, отдельно от букв Г
    sh.leader(F.P(xf - D.FEED_W / 2, yb - D.FEED_H / 2),
              F.P(xf - D.FEED_W / 2, yb - D.FEED_H / 2) + [-28, -10],
              "Питатель  2 шт.", side="left", arrow=False, dot=True)

    # следы Б-Б, В-В, Г-Г
    yb_cut = yb + (yt - yb) * 0.75
    cutline(sh, F.P(xs - D.D_SPRUE_TOP / 2 - 2, yb_cut), [-1, 0], [0, 1], "Б", L=8)
    cutline(sh, F.P(xs + D.D_SPRUE_TOP / 2 + 2, yb_cut), [1, 0], [0, 1], "Б", L=8)
    cutline(sh, F.P(mid_run + 6, yb + D.SLAG_H / 2 + 1), [0, 1], [1, 0], "В", L=7)
    cutline(sh, F.P(mid_run + 6, yb - D.SLAG_H / 2 - 1), [0, -1], [1, 0], "В", L=7)
    # Г-Г — разомкнутая линия со стрелками (как Б-Б / В-В)
    cutline(sh, F.P(xf - D.FEED_W / 2 - 2, yb - D.FEED_H / 2), [-1, 0], [0, -1], "Г", L=10)
    cutline(sh, F.P(xf + D.FEED_W / 2 + 2, yb - D.FEED_H / 2), [1, 0], [0, -1], "Г", L=10)

    F.dim((-D.D_BOT / 2, yb), (D.D_BOT / 2, yb), -(10 + 7) * K, "⌀%s" % fmt(D.D_BOT, 0), tpos=0.28)
    # ⌀200 слева-вверх на полке — отдельно от Ra припуска
    tip = F.P(-D.D_TOP / 2, yt)
    sh.leader(tip, tip + np.array([-10, 20]), "⌀%s" % fmt(D.D_TOP, 0), side="left", arrow=False, dot=True)
    F.dim((-D.D_BOT / 2 - 10, yb), (-D.D_BOT / 2 - 10, yt), 0, fmt(D.H_CAST, 0),
          ext1=False, ext2=False, tpos=0.55)


def draw_plan_one(Tv, ox):
    for d, kind in ((D.D_BOT, "main"), (D.D_TOP, "main"), (D.R_IN_TOP_CAST * 2, "main"),
                    (D.R_OUT_BOT * 2, "thin")):
        a = np.linspace(0, 2 * math.pi, 56, endpoint=False)
        r = d / 2
        Tv.pl([(ox + r * math.cos(t), r * math.sin(t)) for t in a], kind, close=True)
    Tv.axis(ox - D.D_BOT / 2 - 5, 0, ox + D.D_BOT / 2 + 5, 0)
    Tv.axis(ox, -D.D_BOT / 2 - 5, ox, D.D_BOT / 2 + 5)
    for i in range(D.N_RIBS):
        ang = math.radians(i * 60.0)
        cax, cay = math.cos(ang), math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        hw = D.RIB_W / 2
        r1, r2 = D.R_OUT_TOP, D.D_BOT / 2 - 2
        Tv.pl([
            (ox + cax * r1 + nx * hw, cay * r1 + ny * hw),
            (ox + cax * r2 + nx * hw, cay * r2 + ny * hw),
            (ox + cax * r2 - nx * hw, cay * r2 - ny * hw),
            (ox + cax * r1 - nx * hw, cay * r1 - ny * hw),
        ], "main", close=True)


def draw_gating_sections(sh, sx=378):
    # справа вверху, с запасом от рамки (y1=292) и между сечениями
    sh.text(sx, 278, "Б-Б", h=4.5, ha="center")
    cy = 258
    sh.circle(sx, cy, D.D_SPRUE / 2, "main")
    sh.seg(sx - D.D_SPRUE / 2 - 2, cy, sx + D.D_SPRUE / 2 + 2, cy, "axis")
    sh.seg(sx, cy - D.D_SPRUE / 2 - 2, sx, cy + D.D_SPRUE / 2 + 2, "axis")
    sh.dim((sx - D.D_SPRUE / 2, cy), (sx + D.D_SPRUE / 2, cy), 6, "⌀%s" % fmt(D.D_SPRUE, 0))
    sh.text(sx, cy - D.D_SPRUE / 2 - 7, "Fст=%s" % fmt(D.F_SPRUE, 2), h=3.5, ha="center")

    # ширина шлаковика — снизу фигуры, чтобы не пересечь заголовок В-В
    sh.text(sx, 220, "В-В", h=4.5, ha="center")
    by0 = 183
    tr = [(sx - D.SLAG_W1 / 2, by0 + D.SLAG_H), (sx + D.SLAG_W1 / 2, by0 + D.SLAG_H),
          (sx + D.SLAG_W0 / 2, by0), (sx - D.SLAG_W0 / 2, by0)]
    sh.pl(tr, "main", close=True)
    sh.dim(tr[3], tr[2], -5, fmt(D.SLAG_W0, 0))
    sh.dim((sx + D.SLAG_W1 / 2, by0), (sx + D.SLAG_W1 / 2, by0 + D.SLAG_H), -6, fmt(D.SLAG_H, 1))
    sh.text(sx, by0 - 12, "Fшл=%s" % fmt(D.F_SLAG, 2), h=3.5, ha="center")

    # ширина питателя — снизу, заголовок Г-Г выше с зазором
    sh.text(sx, 158, "Г-Г", h=4.5, ha="center")
    vy0 = 128
    rc = [(sx - D.FEED_W / 2, vy0), (sx + D.FEED_W / 2, vy0),
          (sx + D.FEED_W / 2, vy0 + D.FEED_H), (sx - D.FEED_W / 2, vy0 + D.FEED_H)]
    sh.pl(rc, "main", close=True)
    sh.dim(rc[0], rc[1], -5, fmt(D.FEED_W, 0))
    sh.dim(rc[1], rc[2], -6, fmt(D.FEED_H, 1))
    # площади — слева от сечения Г-Г (правее рамки нельзя)
    sh.text(sx - D.FEED_W / 2 - 3, vy0 + D.FEED_H / 2 + 4, "Fп=%s×2" % fmt(D.F_ONE_FEED, 2), h=3.5, ha="right")
    sh.text(sx - D.FEED_W / 2 - 3, vy0 + D.FEED_H / 2 - 3, "ΣFп=%s" % fmt(D.SIGMA_FP, 2), h=3.5, ha="right")
    sh.text(sx - D.FEED_W / 2 - 3, vy0 + D.FEED_H / 2 - 10, "1:1,1:1,2", h=3.5, ha="right")


def main():
    sh = Sheet("A3")
    F = View(sh, 112, 208, K)
    # план: низ ⌀300 выше штампа (y>60); ТТ справа у сечения, левее Б/В/Г
    Tv = View(sh, 178, 148, K)
    pitch = 320.0

    draw_section(F, sh)
    draw_plan_one(Tv, -pitch / 2)
    draw_plan_one(Tv, pitch / 2)

    a = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    for r in (D.D_CUP / 2, D.D_SPRUE / 2):
        Tv.pl([(r * math.cos(t), r * math.sin(t)) for t in a], "thin", close=True)
    hw = D.SLAG_W1 / 2
    Tv.pl([(-pitch / 2 + D.D_BOT / 2, -hw), (pitch / 2 - D.D_BOT / 2, -hw),
           (pitch / 2 - D.D_BOT / 2, hw), (-pitch / 2 + D.D_BOT / 2, hw)], "thin", close=True)
    for s in (-1, 1):
        x0 = s * (pitch / 2 - D.D_BOT / 2)
        Tv.pl([(x0, -D.FEED_W / 2), (x0 - s * 18, -D.FEED_W / 2),
               (x0 - s * 18, D.FEED_W / 2), (x0, D.FEED_W / 2)], "thin", close=True)

    fl, fw = 312.0, 78.0  # casting bottom ≈70 > штамп; левее колонки Г-Г
    Tv.pl([(-fl, -fw), (fl, -fw), (fl, fw), (-fl, fw)], "thin", close=True)
    sh.text(*Tv.P(-fl + 12, -fw + 8), "Опока", h=3.5)

    # МФ справа за опокой; В/Н разведены; не заходить в колонку Г-Г (x≈360)
    mf_end = fl + 2
    Tv.pl([(-fl - 6, 0), (mf_end, 0)], "mf")
    pe = Tv.P(mf_end, 0)
    sh.seg(pe[0], pe[1] - 12, pe[0], pe[1] + 12, "main")
    sh.arrow(pe + [0, 12], [0, 1])
    sh.arrow(pe - [0, 12], [0, -1])
    sh.text(pe[0] - 3, pe[1] + 10, "В", h=5, ha="right")
    sh.text(pe[0] - 3, pe[1] - 11, "Н", h=5, ha="right")
    sh.text(pe[0] - 10, pe[1] + 2.2, "МФ", h=5, ha="right")

    # подписи стояк/шлаковик ЗА контуром отливок, на полках
    p_st = Tv.P(-pitch / 2 - 8, D.D_BOT / 2 + 20)
    sh.seg(*Tv.P(0, D.D_CUP / 2), *p_st, "thin")
    sh.circle_fill(Tv.P(0, D.D_CUP / 2), 0.45)
    sh.seg(p_st[0] - 14, p_st[1], p_st[0] + 4, p_st[1], "thin")
    sh.text(p_st[0] - 13, p_st[1] + 1.0, "Стояк", h=3.5)

    p_sl = Tv.P(pitch / 2 + 8, -D.D_BOT / 2 - 18)
    sh.seg(*Tv.P(24, 0), *p_sl, "thin")
    sh.circle_fill(Tv.P(24, 0), 0.45)
    sh.seg(p_sl[0] - 4, p_sl[1], p_sl[0] + 28, p_sl[1], "thin")
    sh.text(p_sl[0] + 1, p_sl[1] + 1.0, "Шлакоуловитель", h=3.5)

    draw_gating_sections(sh, sx=372)

    TT = [
        "1. ПГС; 2 отливки в форме.",
        "2. Разъём — по ⌀300 (МФ).",
        "3. Ст.1 — 5°/12°; зазор 0,5.",
        "4. Точность 9-7-12-9 ГОСТ 26645-85.",
        "5. Уклоны ГОСТ 3212-92; усадка 1%.",
        "6. Противопригарное покрытие.",
        "7. Tзал 1340…1380 °С; τ≈%s с." % fmt(D.TAU_FILL, 1),
        "8. ΣFп:Fшл:Fст = 1:1,1:1,2.",
        "9. Масса отл. %s; ЛПС %s." % (D.MASS_STR, fmt(D.MASS_GATING, 1)),
        "10. Выход годного ≈ %s %%." % fmt(D.YIELD, 0),
    ]
    # ТТ справа у сечения (между планом и Б-Б), левее колонки сечений
    tx0, step = 268, 7
    ty0 = 188 + (len(TT) - 1) * step
    for i, t in enumerate(TT):
        sh.text(tx0, ty0 - i * step, t, h=3.5)

    sh.frame(
        ["Корпус.", "Элементы литейной формы"],
        D.DESIGNATION_02, D.MATERIAL, D.MASS_STR, "1:2",
        org=D.ORG, sheet="1", sheets="1", lit="У", dev=D.DEV, chk=D.CHK,
    )

    png = OUT / "ПП-062215009-02_Korpus_MLU.png"
    pdf = OUT / "ПП-062215009-02_Korpus_MLU.pdf"
    dxf = OUT / "ПП-062215009-02_Korpus_MLU.dxf"
    col = sh.render(str(png), str(pdf), dpi=200, check_collisions=True)
    sh.to_dxf(str(dxf))
    for dst in (ART / "02_Korpus_MLU.pdf", ART / "02_Korpus_MLU.png",
                ART / "ПП-062215009-02_Корпус_МЛУ.pdf"):
        dst.write_bytes((pdf if dst.suffix == ".pdf" else png).read_bytes())
    print("ok 02", D.DESIGNATION_02, D.DEV, D.MASS_STR, "col", len(col))
    for c in col[:20]:
        print(" ", c)
    return col


if __name__ == "__main__":
    main()
