# -*- coding: utf-8 -*-
"""Отливка «Колесо рабочее» по Рисунку 1 (не КП-062215009).

Исходник: inbox/examples/koleso_rabochee_risunok1.jpg
Материал / штамп / масса — от инженера 2026-11-12.
"""
from __future__ import annotations

import math

# Деталь (чистовые)
D_OUT = 280.0
D_HUB = 100.0
D_SHOULDER = 180.0
D_BORE = 30.0
D_RECESS = 50.0
RECESS_DEPTH = 2.5
BORE_DEPTH = 34.0
D_BOT = 85.0
PCD = 120.0
D_HOLE = 10.0
N_HOLES = 6
T_TOP = 15.0
H_CH = 30.0
T_BOT = 15.0
H_HUB = 42.0  # над верхним диском
SHOULDER_H = 5.0
R_IN = 65.0
R_OUT = 90.0
R_FILLET = 5.0
R_NOSE = 10.0
N_VANES = 4
R_VANE_OUT = 100.0
R_VANE_IN = 80.0
R_VANE_ROOT = 5.0

H_PART = T_BOT + H_CH + T_TOP + H_HUB  # 102

# Припуски (сталь 12Х18Н9ТЛ, габарит ~280, чистовая; инженер не задал — учебные)
ALLOW_TOP = 4.0
ALLOW_BOT = 3.5
ALLOW_FACE = 3.5  # торцы дисков
ALLOW_BORE = 3.0  # на сторону
ALLOW_HUB_OD = 3.0

# Отливка
H_CAST = H_PART + ALLOW_TOP + ALLOW_BOT
T_TOP_CAST = T_TOP + ALLOW_FACE
T_BOT_CAST = T_BOT + ALLOW_FACE
H_CH_CAST = H_CH  # канал стержнем
H_HUB_CAST = H_HUB + ALLOW_TOP
D_BORE_CAST = D_BORE - 2 * ALLOW_BORE  # 24
D_RECESS_CAST = D_RECESS - 2 * ALLOW_BORE
D_HUB_CAST = D_HUB + 2 * ALLOW_HUB_OD
D_SHOULDER_CAST = D_SHOULDER + 2 * ALLOW_HUB_OD
D_OUT_CAST = D_OUT  # наружный обод без припуска (Ra на торцах)
D_BOT_CAST = D_BOT - 2 * ALLOW_BORE

DRAFT_EXT = 1.5
DRAFT_INT = 2.0
SHRINKAGE = 2.0  # % ориентир для 12Х18Н9ТЛ
ACCURACY = "9-7-12-9"

MATERIAL = ["12Х18Н9ТЛ", "ГОСТ 2176-77"]
MASS_PART = 25.0
MASS_CAST = 25.0  # по указанию инженера (штамп отливки)
MASS_STR = ("%.1f" % MASS_CAST).replace(".", ",")

# Обозначения на исходнике не было — временные, пока инженер не даст табельные
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

# ЛС (кратко, учебный ориентир по массе)
G_CAST = MASS_CAST
TAU_FILL = round(1.5 * math.sqrt(G_CAST), 1)
SIGMA_FP = round(G_CAST / (7200 * 0.4 * TAU_FILL * math.sqrt(2 * 9.81 * 0.15)) * 1e4, 2)
F_SLAG = round(SIGMA_FP * 1.2, 2)
F_SPRUE = round(SIGMA_FP * 1.4, 2)
