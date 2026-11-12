# -*- coding: utf-8 -*-
"""Отливка «Колесо рабочее» по Рисунку 1 (⌀280), сталь 12Х18Н9ТЛ.

Исходник детали: inbox/examples/koleso_rabochee_risunok1.jpg
Не КП-062215009.
"""
from __future__ import annotations

import math

# ---------- деталь (чистовые) ----------
D_OUT = 280.0
D_HUB = 100.0
D_SHOULDER = 180.0
D_BORE = 30.0
D_RECESS = 50.0
RECESS_H = 2.5
BORE_DEPTH = 34.0
D_INLET = 85.0
PCD = 120.0
D_HOLE = 10.0
N_HOLES = 6
T_TOP = 15.0
H_CH = 30.0
T_BOT = 15.0
H_HUB = 42.0
SHOULDER_H = 5.0
R_SHROUD = 90.0       # наружный обвод нижнего диска
R_FILLET_TOP = 65.0   # переход верхнего диска к ступице
R_NOSE = 10.0
R_FILLET = 5.0
N_VANES = 4
R_VANE_OUT = 100.0
R_VANE_IN = 80.0
R_VANE_ROOT = 5.0
VANE_R_REF = 80.0     # размер «80» на плане исходника

H_PART = T_BOT + H_CH + T_TOP + H_HUB  # 102

# ---------- припуски (сталь ~⌀280, чистовая; учебные) ----------
N_TOP = 4.0
N_BOT = 3.5
N_FACE = 3.5
N_HUB_OD = 3.0
N_BORE = 3.0
N_SHOULDER = 3.0

# ---------- отливка ----------
C_OUT = D_OUT
C_HUB = D_HUB + 2 * N_HUB_OD          # 106
C_SHOULDER = D_SHOULDER + 2 * N_SHOULDER  # 186
C_BORE = D_BORE - 2 * N_BORE          # 24
C_RECESS = D_RECESS - 2 * N_BORE      # 44
C_INLET = D_INLET - 2 * N_BORE        # 79
C_T_TOP = T_TOP + N_FACE              # 18.5
C_T_BOT = T_BOT + N_FACE              # 18.5
C_H_CH = H_CH                         # 30 (стержень)
C_H_HUB = H_HUB + N_TOP               # 46

# ось Y: низ тела отливки = 0 (без прибыли)
Y_BOT = 0.0
Y_DISK_LO = C_T_BOT                   # 18.5
Y_DISK_UP_BOT = C_T_BOT + C_H_CH      # 48.5
Y_DISK_UP_TOP = Y_DISK_UP_BOT + C_T_TOP  # 67
Y_HUB_TOP = Y_DISK_UP_TOP + C_H_HUB   # 113
H_BODY = Y_HUB_TOP

# центры дуг меридиана (модель отливки, низ = 0)
# R90: наружный обвод нижнего диска; центр на оси ≈ (50, Y_DISK_LO) в масштабе детали → сдвиг с припуском
C90_X = 50.0
C90_Y = Y_DISK_LO
# R65: галтель верхнего диска к ступице
C65_X = C_HUB / 2 + R_FILLET_TOP      # ≈118
C65_Y = Y_DISK_UP_BOT
# R10 носик входа
C10_X = C_INLET / 2 + R_NOSE
C10_Y = R_NOSE + N_BOT * 0.0  # носик над низом детали; на отливке чуть выше N_BOT при отрисовке детали

# прибыль (сталь)
D_RISER = 120.0
D_NECK = 95.0
H_RISER = 65.0
Y_RISER_TOP = H_BODY + H_RISER
H_PRINT2 = 20.0
L_PRINT = 30.0

DRAFT_EXT = 1.5
DRAFT_INT = 2.0
SHRINKAGE = 2.0
ACCURACY = "9-7-12-9"

MATERIAL = ["12Х18Н9ТЛ", "ГОСТ 2176-77"]
MASS_PART = 25.0
MASS_CAST = 25.0
MASS_STR = ("%.1f" % MASS_CAST).replace(".", ",")

DESIGNATION_00 = "КР-Рис1-00"
DESIGNATION_01 = "КР-Рис1-01"
NAME = ["Колесо рабочее"]
DEV = "Пономарев"
CHK = "Степанова"
ORG = ("СФУ ИЦМ", "гр. ЗЦМ22-01Б")
LIT = "У"

RA_FACES = "Ra 6,3"
RA_BORE = "Ra 2,5"
RA_GENERAL = "Ra 12,5"

# ЛС ориентир
G_CAST = MASS_CAST
TAU_FILL = round(1.5 * math.sqrt(G_CAST), 1)
SIGMA_FP = round(G_CAST / (7200 * 0.4 * TAU_FILL * math.sqrt(2 * 9.81 * 0.15)) * 1e4, 2)
F_SLAG = round(SIGMA_FP * 1.2, 2)
F_SPRUE = round(SIGMA_FP * 1.4, 2)
