# -*- coding: utf-8 -*-
import numpy as np, math
from shapely.geometry import box, Point
from cad import *
from geom import *

MC = round(volume(True) * RHO, 1)
sh = Sheet('A2')
K = 2.0
F = View(sh, 180, 282, K)      # главный вид - фронтальный разрез
Lv = View(sh, 420, 282, K)     # вид слева (проекционная связь по высоте)
Tv = View(sh, 180, 120, K)     # вид сверху (проекционная связь по длине)
C = casting(); D = detail(holes=False)

# ---------- главный вид ----------
F.hatch(C, angle=45, step=2.5)
F.geom(C, 'main')
F.geom(D.boundary.difference(C.boundary.buffer(0.3)), 'thin')     # контур детали
for yy in (T_D, -T_D):                                             # кромки отверстия седла за плоскостью
    F.seg(-R_SEAT_C, yy, R_SEAT_C, yy, 'main')
F.axis(-XF - 8, 0, XF + 8, 0)
F.axis(0, Y_BOT - 8, 0, YT + 8)

F.dim((-XF, -R_FL), (XF, -R_FL), -12, '360')
for s in (-1, 1):
    a, b = sorted((s * XF, s * X_FB))
    F.dim((a, R_FL), (b, R_FL), 7, '34')
F.dim((-XF, -R_FL), (-XF, R_FL), 10, '⌀230')
F.dim((-125, -R_PO), (-125, R_PO), 0, '⌀132', ext1=False, ext2=False)
F.dim((-160, -R_CH), (-160, R_CH), 0, '⌀100', ext1=False, ext2=False)
F.dim((160, -R_CH), (160, R_CH), 0, '⌀100', ext1=False, ext2=False)
F.dim((-R_BF, YT), (R_BF, YT), 18, '⌀260')
F.dim((-R_NI, YT), (R_NI, YT), 8, '⌀142')
F.dim((-R_NO, 104), (R_NO, 104), 0, '⌀174', ext1=False, ext2=False, tpos=0.5)
F.dim((-R_SEAT_C, -T_D), (R_SEAT_C, -T_D), -5, '⌀92')
# высоты от оси прохода
F.dim((-105, 0), (-105, YT), 0, '155', ext1=False, ext2=False, tpos=0.6)
F.dim((-R_BF, Y_BF0), (-R_BF, YT), 4, '35')
p2 = F.P(R_BF, YT); sh.seg(*(p2 + [1, 0]), F.P(XF, 0)[0] + 16, p2[1], 'thin')
xr2 = F.P(XF, 0)[0] + 14
sh.dim((xr2, F.P(0, -R_FL)[1]), (xr2, F.P(0, YT)[1]), 0, '%d*' % (YT + R_FL), ext1=False, ext2=False)
pb = F.P(XF, -R_FL); sh.seg(*(pb + [1, 0]), xr2 + 2, pb[1], 'thin')
# глубина корпуса от оси прохода
pb = F.P(0, Y_BOT); sh.seg(*(pb + [0.8, 0]), F.P(42, 0)[0] + 2, pb[1], 'thin')
F.dim((42, Y_BOT), (42, 0), 0, '%d' % EO[1], ext1=False, ext2=False, tpos=0.45)
# стенки
F.dim((-R_NO, 60), (-R_NI, 60), 0, '16', ext1=False, ext2=False, out=True)      # перегородка/горловина
F.dim((XW_I, -45), (XW_O, -45), 0, '16', ext1=False, ext2=False, out=True)
F.dim((-60, -T_D), (-60, T_D), 0, '', ext1=False, ext2=False, out=True)
sh.text(*(F.P(-60, -T_D) + [-1.0, -7.5]), '20', h=3.5, ha='center')
xw = -12.0
yi = -EI[1] * math.sqrt(1 - (xw / EI[0])**2); yo = -EO[1] * math.sqrt(1 - (xw / EO[0])**2)
F.dim((xw, yi), (xw, yo), 0, '', ext1=False, ext2=False, out=True)
pt = F.P(xw, yi)
sh.text(pt[0] - 1.5, pt[1] + 4.5, '16', h=3.5, ha='right')
# ---------- вид слева ----------
Lv.circle(0, 0, R_FL)
Lv.circle(0, 0, R_CH)
yn0 = math.sqrt(R_FL**2 - R_NO**2)      # горловина видна выше обода фланца
for zz in (-R_NO, R_NO):
    Lv.seg(zz, yn0, zz, Y_BF0)
Lv.pl([(-R_BF, Y_BF0), (R_BF, Y_BF0), (R_BF, YT), (-R_BF, YT)], close=True)
Lv.axis(-R_FL - 8, 0, R_FL + 8, 0)
Lv.axis(0, Y_BOT - 8, 0, YT + 8)
Lv.dim((-R_SO, -R_SO * 0 - 0), (R_SO, 0), 0, '', ext1=False, ext2=False) if False else None
# ---------- вид сверху ----------
Tv.circle(0, 0, R_BF)
Tv.circle(0, 0, R_NI)
Tv.circle(0, 0, R_SEAT_C)
xn = math.sqrt(R_BF**2 - R_PO**2)
for s in (-1, 1):
    Tv.pl([(s * X_FB, -R_FL), (s * XF, -R_FL), (s * XF, R_FL), (s * X_FB, R_FL)], close=True)
    for zz in (-R_PO, R_PO):
        Tv.seg(s * xn, zz, s * X_FB, zz)
Tv.axis(-XF - 8, 0, XF + 8, 0)
Tv.axis(0, -R_BF - 8, 0, R_BF + 8)
Tv.dim((XF, -R_FL), (XF, R_FL), -9, '230')

TT = ['1. Отливка 3-й группы по ГОСТ 977-88.',
      '2. Точность отливки 10-6-14-10 ГОСТ 26645-85.',
      '3. Формовочные уклоны по ГОСТ 3212-92 (табл. 2, комплект',
      '    деревянный, ХТС): h 25...40 мм - 1°30\'; h 40...63 мм - 1°05\';',
      '    h 63...100 мм - 0°45\'; h 100...160 мм - 0°35\'; выполнять',
      '    за счёт увеличения размеров отливки.',
      '4. Неуказанные литейные радиусы: наружные R3, внутренние R8.',
      '5. Неуказанная толщина стенок 16 мм. Наружная поверхность',
      '    корпуса - эллипсоид вращения с полуосями 125 и 112 мм.',
      '6. Термическая обработка: нормализация 880...900 °С,',
      '    отпуск 600...650 °С.',
      '7. Механические свойства: σ0,2 ≥ 275 МПа, σв ≥ 540 МПа,',
      '    δ5 ≥ 18 %, ψ ≥ 25 %, KCU ≥ 491 кДж/м².',
      '8. Контроль: ВИК - 100 %; РК зон сопряжения перегородки',
      '    со стенками и фланцев с патрубками; МПД после',
      '    механической обработки.',
      '9. Остатки прибылей и питателей на обрабатываемых',
      '    поверхностях - не более 3 мм, на необрабатываемых -',
      '    зачистить заподлицо.',
      '10. Тонкой линией показан контур детали.',
      '11. * Размер для справок.']
for i, t in enumerate(TT):
    sh.text(372, 203 - i * 6.6, t, h=3.5)
rough_sign_only(sh, 568, 398)
sh.frame(['Корпус клапана', 'Отливка'], 'ПП-062215009-01', ['Сталь 20ГЛ', 'ГОСТ 977-88'],
         ('%.1f' % MC).replace('.', ','), '1:2')
sh.render('/tmp/rust95/otlivka.png', '/tmp/rust95/otlivka.pdf', dpi=200)
sh.to_dxf('/tmp/rust95/otlivka.dxf')
print('ok', MC)
