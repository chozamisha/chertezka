# -*- coding: utf-8 -*-
import numpy as np, math
from shapely.geometry import box, Point, Polygon, LineString
from shapely.ops import unary_union
from cad import *
from geom import *
from geom import _cavity
from mould import *

MC = round(volume(True) * RHO, 1); MD = round(volume(False) * RHO, 1)
LP = lps_calc(MC); RI = riser_calc()
sh = Sheet('A2')
K = 2.5
F = View(sh, 150, 308, K)      # главный вид - разрез по плоскости симметрии (= плоскость разъёма)
Tv = View(sh, 150, 75, K)      # вид сверху: верх формы (+z) - вверх листа
C = casting(); D = detail()

# ================= ГЛАВНЫЙ ВИД =================
F.hatch(D, angle=45, step=3.0)
F.geom(D, 'main')
F.geom(C.boundary.difference(D.boundary.buffer(0.25)), 'thin')         # припуски
for hb in hole_boxes():                                                 # незалитые отверстия
    x0, y0, x1, y1 = hb.bounds
    F.seg(x0 + 0.5, y0, x1 - 0.5, min(y1, Y_TOP), 'thin')
for yy in (T_D, -T_D):
    F.seg(-R_SEAT, yy, R_SEAT, yy, 'main')
for sx in (-1, 1):
    for sy in (-1, 1):
        F.axis(sx * (X_FB - 6), sy * R_BC, sx * (L2 + 6), sy * R_BC)
    F.axis(sx * R_STUD, Y_TOP - STUD_DEPTH - 6, sx * R_STUD, Y_TOP + 6)

# ---- стержень ст.1 ----
core_in = box(-XF, Y_BOT - 5, XF, YT).difference(C).intersection(_cavity(R_SEAT_C, R_NI).buffer(1.0))
core_in = unary_union([p for p in polys(core_in) if p.area > 500])
PRL = box(-XF - PRINT_L, -R_CH, -XF + 0.5, R_CH)
PRR = box(XF - 0.5, -R_CH, XF + PRINT_L, R_CH)
PRT = box(-R_NI, YT - 0.5, R_NI, YT + PRINT_L)
core = unary_union([core_in, PRL, PRR, PRT]).buffer(0.01)
F.geom(core, 'thin')
F.hatch(core.difference(core.buffer(-9.0)), angle=135, step=3.0)
sh.text(*F.P(-30, -58), 'ст.1', h=5, ha='center')

# ---- ВГ ----
for s in (-1, 1):
    p0 = F.P(s * (XF + PRINT_L), 0)
    sh.seg(*p0, *(p0 + [s * 11, 0]), 'thin'); sh.arrow(p0 + [s * 11, 0], [s, 0])
    sh.text(*(p0 + [s * 5.5, 1.0]), 'ВГ', h=3.5, ha='center')
p0 = F.P(-40, YT + PRINT_L)
sh.seg(*p0, *(p0 + [0, 11]), 'thin'); sh.arrow(p0 + [0, 11], [0, 1])
sh.text(*(p0 + [-1.0, 5.5]), 'ВГ', h=3.5, ha='center', va='bottom', rot=90)

# ---- ЛПС в плане (в нижней полуформе, по разъёму) ----
yk1, yk0 = YS + RUN_W1 / 2, YS - RUN_W1 / 2
xk0 = -X_R2 - FEED_W / 2 - 8
F.pl([(XS - D_ST1 / 2 * 0.0, yk1), (xk0, yk1), (xk0, yk0), (XS, yk0)], 'thin')
for s in (-1, 1):
    a, b = s * X_R2 - FEED_W / 2, s * X_R2 + FEED_W / 2
    F.pl([(a, yk1), (a, -R_FL)], 'thin'); F.pl([(b, yk1), (b, -R_FL)], 'thin')
F.circle(XS, YS, D_ST1 / 2, 'thin')
F.axis(XS - D_ST1 / 2 - 6, YS, XS + D_ST1 / 2 + 6, YS)
F.axis(XS, YS - D_ST1 / 2 - 6, XS, YS + D_ST1 / 2 + 6)
# секущие плоскости
def cutline(p, d, a, letter, L=8):
    p = np.asarray(p, float); d = np.asarray(d, float); a = np.asarray(a, float)
    q = p + d * L
    sh.seg(*p, *q, 'cut')
    base = q - d * 1.5
    sh.seg(*base, *(base + a * 7), 'thin'); sh.arrow(base + a * 7, a, L=3.5, W=1.2)
    t = base + a * 4 + d * 4.5
    sh.text(*t, letter, h=5, ha='center', va='center')
xb = -100.0
cutline(F.P(xb, yk1) + [0, 2], [0, 1], [1, 0], 'Б', L=6)
cutline(F.P(xb, yk0) - [0, 1.5], [0, -1], [1, 0], 'Б', L=5)
yv = -124.0
cutline(F.P(X_R2 - FEED_W / 2, yv) - [3, 0], [-1, 0], [0, 1], 'В')
cutline(F.P(X_R2 + FEED_W / 2, yv) + [3, 0], [1, 0], [0, 1], 'В')
sh.leader(F.P(-20, YS), F.P(-20, YS) + [6, 9], 'Коллектор', arrow=False, dot=True)
sh.leader(F.P(-X_R2, -124), F.P(-X_R2, -124) + [-8, -20], 'Питатель  2 шт.', side='left', arrow=False, dot=True)
sh.leader(F.P(XS + 12, YS - 14), F.P(XS + 12, YS - 14) + [8, -10], 'Стояк', arrow=False, dot=True)

# ---- размеры детали ----
for s in (-1, 1):
    a, b = sorted((s * X_FB, s * (L2 - RF_H)))
    F.dim((a, R_FL), (b, R_FL), 6, '26', tpos=0.5 + 0.25 * s)
F.dim((-163, -R_BC), (-163, R_BC), 0, '⌀190', ext1=False, ext2=False)
F.dim((-125, -R_CH), (-125, R_CH), 0, '⌀100', ext1=False, ext2=False)
F.dim((125, -R_CH), (125, R_CH), 0, '⌀100', ext1=False, ext2=False)
F.dim((-R_SEAT, -T_D), (R_SEAT, -T_D), -5, '⌀100')
F.dim((-R_BORE, 125), (R_BORE, 125), 0, '⌀150', ext1=False, ext2=False, tpos=0.3)
F.dim((50, Y_BORE), (50, Y_TOP), 0, '50', ext1=False, ext2=False)
sh.seg(*F.P(R_BORE, Y_BORE), *(F.P(50, Y_BORE) + [-2, 0]), 'thin')
F.dim((-92, 0), (-92, Y_TOP), 0, '150', ext1=False, ext2=False, tpos=0.63)
F.dim((-R_BF, Y_BF0), (-R_BF, Y_TOP), 4, '30')
pb = F.P(0, Y_BOT); sh.seg(*(pb + [0.8, 0]), F.P(42, 0)[0] + 2, pb[1], 'thin')
F.dim((42, Y_BOT), (42, 0), 0, '%d' % EO[1], ext1=False, ext2=False, tpos=0.45)
# проточка
pr = F.P(R_REC, Y_TOP - H_REC)
sh.leader(pr, pr + [18, 30], '⌀170, глуб. 4', arrow=True)
a0 = F.P(-X_FB + 1, R_BC + 11); sh.leader(F.P(L2 - 10, R_BC + D_HOLE / 2), F.P(L2, R_BC) + [12, 22], '8 отв. ⌀22', arrow=True)
# припуски (перед знаком шероховатости, ГОСТ 3.1125-88)
sh.rough_leader(F.P(-L2, -62), F.P(-L2, -62) + [-12, -9], 'Ra 6,3', pre='%d' % A_FACE, side='left')
sh.rough_leader(F.P(L2, -62), F.P(L2, -62) + [12, -9], 'Ra 6,3', pre='%d' % A_FACE)
sh.rough_leader(F.P(-124, Y_TOP), F.P(-124, Y_TOP) + [-8, 14], 'Ra 3,2', pre='%d' % A_TOP, side='left')
sh.rough_leader(F.P(R_BORE, 112), F.P(R_BORE, 112) + [-16, -14], 'Ra 3,2', pre='%d' % A_BORE, side='left')
sh.rough_leader(F.P(R_SEAT, 4), F.P(R_SEAT, 4) + [-4, 14], 'Ra 3,2', pre='%d' % A_SEAT, side='left')
# знаки стержня
F.dim((-XF - PRINT_L, R_CH), (-XF, R_CH), 6, '%d' % PRINT_L)
F.dim((XF, R_CH), (XF + PRINT_L, R_CH), 6, '%d' % PRINT_L)
F.dim((-XF - PRINT_L + 14, -R_CH), (-XF - PRINT_L + 14, R_CH), 0, '⌀100', ext1=False, ext2=False)
F.dim((-R_NI, YT + PRINT_L), (R_NI, YT + PRINT_L), 6, '⌀142')
F.dim((R_NI, YT), (R_NI, YT + PRINT_L), -6, '%d' % PRINT_L)
# положение ЛПС
F.dim((0, yk0), (XS, yk0), -17, '%d' % XS, ext1=False)
sh.seg(*F.P(0, -EO[1] - 3), *(F.P(0, yk0) - [0, 19]), 'thin')
F.dim((-X_R2, yk0), (X_R2, yk0), -10, '%d' % (2 * X_R2))
sh.seg(*F.P(XS + D_ST1 / 2 + 2, YS), *(F.P(XS + D_ST1 / 2, YS) + [12, 0]), 'thin')
F.dim((XS + 40, YS), (XS + 40, 0), 0, '%d' % (-YS), ext1=False, ext2=False)
sh.seg(*F.P(XF + PRINT_L + 2, 0), *(F.P(XS + 40, 0) + [2, 0]), 'thin')

# ================= ВИД СВЕРХУ =================
Tv.circle(0, 0, R_BF); Tv.circle(0, 0, R_REC); Tv.circle(0, 0, R_BORE); Tv.circle(0, 0, R_SEAT)
Tv.circle(0, 0, R_STUD, 'axis')
for i in range(8):
    a = math.radians(22.5 + 45 * i)
    cx, cz = R_STUD * math.cos(a), R_STUD * math.sin(a)
    Tv.circle(cx, cz, STUD_DR / 2, 'main')
    Tv.circle(cx, cz, 10.0, 'thin', a0=math.degrees(a) + 100, a1=math.degrees(a) + 370)
    Tv.seg(cx - 7, cz - 7, cx + 7, cz + 7, 'thin')
xn = math.sqrt(R_BF**2 - R_PO**2)
for s in (-1, 1):
    Tv.pl([(s * X_FB, -R_FL), (s * (L2 - RF_H), -R_FL), (s * (L2 - RF_H), R_FL), (s * X_FB, R_FL)], close=True)
    Tv.pl([(s * (L2 - RF_H), -R_RF), (s * L2, -R_RF), (s * L2, R_RF), (s * (L2 - RF_H), R_RF)])
    Tv.seg(s * XF, -R_FL, s * XF, R_FL, 'thin')                # припуск на торце
    Tv.seg(s * (L2 - RF_H), -R_FL, s * XF, -R_FL, 'thin'); Tv.seg(s * (L2 - RF_H), R_FL, s * XF, R_FL, 'thin')
    for zz in (-R_PO, R_PO):
        Tv.seg(s * xn, zz, s * X_FB, zz)
    # знаки стержня
    Tv.pl([(s * XF, -R_CH), (s * (XF + PRINT_L), -R_CH), (s * (XF + PRINT_L), R_CH), (s * XF, R_CH)], 'thin')
# МФ
xm0, xm1 = -XF - PRINT_L - 22, XS + D_CUP / 2 + 40
Tv.pl([(xm0, 0), (xm1, 0)], 'mf')
pe = Tv.P(xm1, 0)
sh.seg(pe[0], pe[1] - 9, pe[0], pe[1] + 9, 'main')
sh.arrow(pe + [0, 9], [0, 1]); sh.arrow(pe - [0, 9], [0, -1])
sh.text(pe[0] + 2.5, pe[1] + 4.5, 'В', h=5, va='center')
sh.text(pe[0] + 2.5, pe[1] - 4.5, 'Н', h=5, va='center')
sh.text(pe[0] - 8, pe[1] + 1.5, 'МФ', h=5, ha='center')
Tv.axis(0, -R_BF - 6, 0, R_BF + 6)

def rounded_top(x0, x1, z0, z1, r):
    p = box(x0, z0 - r, x1, z1).buffer(-r, join_style=1).buffer(r, join_style=1)
    return p.difference(box(-BIG, -BIG, BIG, z0)).union(box(x0, z0, x1, z0 + r))
# прибыль 1 - на ободе фланца под крышку
nw, nh = NECK[1], NECK[2]; bw, bh = BODY[1], BODY[2]
arc = [(x, math.sqrt(R_BF**2 - x**2)) for x in np.linspace(-nw / 2, nw / 2, 40)]
zn1 = R_BF + nh
Tv.pl([(-nw / 2, zn1)] + arc + [(nw / 2, zn1)], 'thin')
Tv.geom(rounded_top(-bw / 2, bw / 2, zn1, zn1 + bh, 20).boundary, 'thin')
# прибыли 2 - на ободах фланцев патрубков
nw2, bw2 = NECK[0], BODY[0]
zn2 = R_FL + nh
for s in (-1, 1):
    xc = s * X_R2
    Tv.pl([(xc - nw2 / 2, R_FL), (xc - nw2 / 2, zn2)], 'thin'); Tv.pl([(xc + nw2 / 2, R_FL), (xc + nw2 / 2, zn2)], 'thin')
    Tv.geom(rounded_top(xc - bw2 / 2, xc + bw2 / 2, zn2, zn2 + bh, 12).boundary, 'thin')
# холодильники
for s in (-1, 1):
    ch = box(s * X_R2 - 10, -R_FL - CH_T, s * X_R2 + 10, -R_FL)
    Tv.geom(ch, 'thin'); Tv.hatch(ch, angle=45, step=2.0)
chb = Polygon([(x, -math.sqrt(R_BF**2 - x**2)) for x in np.linspace(-40, 40, 40)] + [(40, -R_BF - CH_T), (-40, -R_BF - CH_T)])
Tv.geom(chb, 'thin'); Tv.hatch(chb, angle=45, step=2.0)
# стояк, чаша, коллектор, питатели
zst0 = -RUN_H
Tv.pl([(XS - D_ST1 / 2, Z_TOP), (XS - D_ST0 / 2, 0), (XS - D_ST0 / 2, zst0)], 'thin')
Tv.pl([(XS + D_ST1 / 2, Z_TOP), (XS + D_ST0 / 2, 0), (XS + D_ST0 / 2, zst0 - SUMP), (XS - D_ST0 / 2, zst0 - SUMP), (XS - D_ST0 / 2, zst0)], 'thin')
Tv.pl([(XS - D_ST1 / 2, Z_TOP), (XS - D_CUP / 2, Z_TOP + H_CUP), (XS + D_CUP / 2, Z_TOP + H_CUP), (XS + D_ST1 / 2, Z_TOP)], 'thin')
Tv.pl([(XS - D_ST0 / 2, 0), (xk0, 0), (xk0, -RUN_H), (XS - D_ST0 / 2, -RUN_H)], 'hidden')
for s in (-1, 1):
    Tv.pl([(s * X_R2 - FEED_W / 2, -FEED_H), (s * X_R2 + FEED_W / 2, -FEED_H)], 'hidden')
Tv.axis(XS, -RUN_H - SUMP - 6, XS, Z_TOP + H_CUP + 6)
cutline(Tv.P(XS - D_ST0 / 2, 10) - [3, 0], [-1, 0], [0, 1], 'А', L=6)
cutline(Tv.P(XS + D_ST0 / 2, 10) + [3, 0], [1, 0], [0, 1], 'А', L=6)
# обозначения
sh.leader(Tv.P(-20, zn1 + 70), Tv.P(-20, zn1 + 70) + [-30, 14], 'Прибыль 1', side='left', arrow=False, dot=True,
          below='%dx%d, H %d' % (BODY[0], BODY[1], NECK[2] + BODY[2]))
sh.leader(Tv.P(-X_R2, zn2 + 60), Tv.P(-X_R2, zn2 + 60) + [-12, 22], 'Прибыль 2  2 шт.', side='left', arrow=False, dot=True,
          below='%dx%d, H %d' % (BODY[0], BODY[1], NECK[2] + BODY[2]))
sh.leader(Tv.P(X_R2 + 4, -R_FL - 10), Tv.P(X_R2 + 4, -R_FL - 10) + [6, -10], 'Холодильник  3 шт.', arrow=False, dot=True)
# размеры вида сверху
Tv.dim((-L2, -R_RF), (L2, -R_RF), 0, '', ext1=False, ext2=False) if False else None
for s in (-1, 1):
    sh.seg(*Tv.P(s * L2, -R_RF - 2), *(Tv.P(s * L2, -R_BF - CH_T - 8) - [0, 2]), 'thin')
sh.dim(Tv.P(-L2, -R_BF - CH_T - 8), Tv.P(L2, -R_BF - CH_T - 8), 0, '350', ext1=False, ext2=False, tpos=0.3)
Tv.dim((L2 - RF_H, -R_FL), (L2 - RF_H, R_FL), -16, '⌀230')
Tv.dim((L2, -R_RF), (L2, R_RF), -8, '⌀158')
Tv.dim((-R_BF * math.cos(math.radians(35)), -R_BF * math.sin(math.radians(35))),
       (R_BF * math.cos(math.radians(35)), R_BF * math.sin(math.radians(35))), 0, '⌀260', ext1=False, ext2=False, tpos=0.66)
a = math.radians(202.5)
pa = Tv.P(R_STUD * math.cos(a), R_STUD * math.sin(a))
sh.leader(pa + [-2.0, -1.0], np.array([78.0, 40.0]), '8 отв. М20-7Н', side='left', below='на ⌀215, глуб. 22')
# прибыли: размеры
Tv.dim((-bw / 2, zn1 + bh), (bw / 2, zn1 + bh), 5, '%d' % bw)
Tv.dim((bw / 2, zn1), (bw / 2, zn1 + bh), -5, '%d' % bh)
Tv.dim((X_R2 - bw2 / 2, zn2 + bh), (X_R2 + bw2 / 2, zn2 + bh), 5, '%d' % bw2)
Tv.dim((X_R2 + bw2 / 2, zn2), (X_R2 + bw2 / 2, zn2 + bh), -5, '%d' % bh)
Tv.dim((X_R2 - nw2 / 2, R_FL), (X_R2 + nw2 / 2, R_FL), -0.0, '', ext1=False, ext2=False) if False else None
Tv.dim((X_R2 - bw2 / 2, R_FL), (X_R2 - bw2 / 2, zn2), 4, '%d' % NECK[2], out=True)
Tv.dim((XS - D_CUP / 2, Z_TOP + H_CUP), (XS + D_CUP / 2, Z_TOP + H_CUP), 5, '⌀%d' % D_CUP)
Tv.dim((XS + D_CUP / 2, Z_TOP), (XS + D_CUP / 2, Z_TOP + H_CUP), -5, '%d' % H_CUP)
Tv.dim((XS - D_ST1 / 2, Z_TOP - 20), (XS + D_ST1 / 2, Z_TOP - 20), 0, '⌀%d' % D_ST1, ext1=False, ext2=False, out=True)

# ================= СЕЧЕНИЯ ЛПС (М 1:1) =================
def title(x, y, s):
    sh.text(x, y, s, h=5, ha='center')
sx = 330
title(sx, 398, 'А-А (1:1)')
sh.circle(sx, 368, D_ST0 / 2, 'main')
sh.seg(sx - D_ST0 / 2 - 3, 368, sx + D_ST0 / 2 + 3, 368, 'axis'); sh.seg(sx, 368 - D_ST0 / 2 - 3, sx, 368 + D_ST0 / 2 + 3, 'axis')
sh.dim((sx - D_ST0 / 2 * math.cos(0.6), 368 - D_ST0 / 2 * math.sin(0.6)), (sx + D_ST0 / 2 * math.cos(0.6), 368 + D_ST0 / 2 * math.sin(0.6)), 0, '⌀%d' % D_ST0, ext1=False, ext2=False, tpos=0.75)
sh.text(sx, 336, 'Fст = %s см²' % ('%.1f' % LP['Fst']).replace('.', ','), h=3.5, ha='center')
title(sx, 326, 'Б-Б (1:1)')
by0 = 276
tr = [(sx - RUN_W1 / 2, by0 + RUN_H), (sx + RUN_W1 / 2, by0 + RUN_H), (sx + RUN_W0 / 2, by0), (sx - RUN_W0 / 2, by0)]
sh.pl(tr, 'main', close=True)
sh.dim(tr[0], tr[1], 5, '%d' % RUN_W1); sh.dim(tr[3], tr[2], -5, '%d' % RUN_W0)
sh.dim((sx + RUN_W1 / 2, by0), (sx + RUN_W1 / 2, by0 + RUN_H), -5, '%d' % RUN_H)
sh.seg(sx + RUN_W0 / 2, by0, sx + RUN_W1 / 2 + 2, by0, 'thin')
sh.text(sx, by0 - 16, 'Fкол = %s см²' % ('%.1f' % LP['Fk']).replace('.', ','), h=3.5, ha='center')
title(sx, 240, 'В-В (1:1)')
vy0 = 205
rc = [(sx - FEED_W / 2, vy0), (sx + FEED_W / 2, vy0), (sx + FEED_W / 2, vy0 + FEED_H), (sx - FEED_W / 2, vy0 + FEED_H)]
sh.pl(rc, 'main', close=True)
sh.dim(rc[3], rc[2], 5, '%d' % FEED_W); sh.dim(rc[1], rc[2], -5, '%d' % FEED_H)
sh.text(sx, vy0 - 9, 'Fп = %s см²; 2 шт.' % ('%.2f' % LP['Fp']).replace('.', ','), h=3.5, ha='center')
sh.text(sx, vy0 - 16, 'ΣFп = %s см²' % ('%.1f' % LP['Fsum_acc']).replace('.', ','), h=3.5, ha='center')

fmt = lambda v, n=1: ('%.*f' % (n, v)).replace('.', ',')
TT = ['1. Форму и стержень изготовлять из ХТС на фурановой смоле;',
      '    у перегородки, седла и фланцев - облицовочная смесь',
      '    на хромитовом песке.',
      '2. Разъём формы - по плоскости симметрии отливки (оси',
      '    патрубков и горловины); главный вид - в плоскости разъёма.',
      '3. Точность отливки 10-6-14-10 ГОСТ 26645-85.',
      '4. Формовочные уклоны по ГОСТ 3212-92 (табл. 2): h 63...100 мм -',
      '    0°45\', h 100...160 мм - 0°35\'; на увеличение размеров отливки.',
      '5. Литейная усадка 1,8 %.',
      '6. Стержень ст.1 - на три горизонтальных знака; зазоры в',
      '    знаках по ГОСТ 3212-92.',
      '7. Покрытие формы и стержня - циркониевое на спиртовой основе.',
      '8. Прибыли закрытые, в теплоизоляционных вкладышах;',
      '    шейка прибылей %dx%d, h %d. Холодильники наружные стальные.' % (NECK[0], NECK[1], NECK[2]),
      '9. Температура заливки 1560...1590 °С, время заливки 12...13 с.',
      '10. Масса, кг: отливки %s, прибылей %s, ЛПС %s;' % (fmt(MC), fmt(LP['m_ris']), fmt(LP['m_lps'])),
      '    металла на форму %d.' % round(LP['G']),
      '11. Неуказанная толщина стенок 16 мм.']
for i, t in enumerate(TT):
    sh.text(380, 405 - i * 6.6, t, h=3.5)
sh.frame(['Корпус клапана.', 'Элементы литейной формы'], 'ПП-062215009-02', ['Сталь 20ГЛ', 'ГОСТ 977-88'],
         fmt(MD), '1:2,5')
sh.render('/tmp/rust95/mlu.png', '/tmp/rust95/mlu.pdf', dpi=200)
sh.to_dxf('/tmp/rust95/mlu.dxf')
print('ok', MC, MD, round(LP['G'], 1))
