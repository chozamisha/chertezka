# -*- coding: utf-8 -*-
"""Данные детали / отливки «Корпус вариант 10», СЧ15."""
from __future__ import annotations

import math

# Деталь (чистовые размеры)
H_PART = 100.0
T_TOP_PART = 15.0
T_BOT_PART = 20.0
D_TOP = 200.0
D_BOT = 300.0
D_BORE_TOP = 120.0
D_BORE_BOT = 190.0
WALL = 15.0
RIB_W = 10.0
PCD_OUTER = 250.0
PCD_INNER = 168.0
D_THRU = 12.0
D_CB = 24.0
CB_DEPTH = 16.0  # по исходному чертежу
N_OUTER = 6
N_INNER = 4
N_RIBS = 6

R_OUT_TOP = D_BORE_TOP / 2 + WALL  # 75
R_OUT_BOT = D_BORE_BOT / 2 + WALL  # 110
R_IN_TOP = D_BORE_TOP / 2
R_IN_BOT = D_BORE_BOT / 2

# Припуски ГОСТ 26645-85 (9-7-12-9)
ALLOW_TOP = 4.0
ALLOW_BOT = 3.0
ALLOW_CB = 2.5
ALLOW_BORE = 2.0  # на сторону для обрабатываемых отверстий

# Отливка
H_CAST = H_PART + ALLOW_TOP + ALLOW_BOT  # 107
T_TOP_CAST = T_TOP_PART + ALLOW_TOP      # 19
T_BOT_CAST = T_BOT_PART + ALLOW_BOT      # 23
D_BORE_TOP_CAST = D_BORE_TOP - 2 * ALLOW_BORE  # 116
D_BORE_BOT_CAST = D_BORE_BOT - 2 * ALLOW_BORE  # 186
R_IN_TOP_CAST = D_BORE_TOP_CAST / 2
R_IN_BOT_CAST = D_BORE_BOT_CAST / 2

DRAFT_EXT = 1.5
DRAFT_INT = 2.0
SHRINKAGE = 1.0
R_FILLET = 5.0

MATERIAL = ["СЧ15", "ГОСТ 1412-85"]
MASS_PART = 15.0
DENSITY = 7.2e-6
DESIGNATION_00 = "ПП-062215009-00"
DESIGNATION_01 = "ПП-062215009-01"
DESIGNATION_02 = "ПП-062215009-02"
MASS_PART_STR = "15"
DEV = "Шевцов"
CHK = "Степанова"
ORG = ("СФУ ИЦМ", "гр. ЗЦМ22-01Б")


def casting_mass_kg() -> float:
    v_top = math.pi / 4 * (D_TOP**2 - D_BORE_TOP**2) * ALLOW_TOP
    v_bot = math.pi / 4 * (D_BOT**2 - D_BORE_BOT**2) * ALLOW_BOT
    v_bore = math.pi / 4 * ((D_BORE_TOP**2 - D_BORE_TOP_CAST**2) * (H_PART - T_BOT_PART)
                            + (D_BORE_BOT**2 - D_BORE_BOT_CAST**2) * T_BOT_PART) * 0.5
    return round(MASS_PART + (v_top + v_bot + max(v_bore, 0)) * DENSITY, 1)


MASS_CAST = casting_mass_kg()
MASS_STR = ("%.1f" % MASS_CAST).replace(".", ",")

# Литниковая система
G_CAST = MASS_CAST
TAU_FILL = round(1.8 * math.sqrt(G_CAST), 1)
H_MET = 0.18
MU = 0.4
RHO = 6900.0
_sigma = G_CAST / (RHO * MU * TAU_FILL * math.sqrt(2 * 9.81 * H_MET))
SIGMA_FP = round(_sigma * 1e4, 2)
F_SLAG = round(SIGMA_FP * 1.1, 2)
F_SPRUE = round(SIGMA_FP * 1.2, 2)
N_FEEDERS = 2
F_ONE_FEED = round(SIGMA_FP / N_FEEDERS, 2)
D_SPRUE = int(round(2 * math.sqrt(F_SPRUE / math.pi) * 10))
D_SPRUE_TOP = D_SPRUE + 4
D_CUP = 50
H_CUP = 40
SLAG_W1, SLAG_W0, SLAG_H = 22.0, 18.0, round(F_SLAG * 100 / ((22 + 18) / 2), 1)
FEED_W, FEED_H = 14.0, round(F_ONE_FEED * 100 / 14.0, 1)
MASS_GATING = round(0.12 * G_CAST + 0.4, 1)
MASS_MOLD_METAL = round(G_CAST + MASS_GATING, 1)
YIELD = round(100.0 * G_CAST / MASS_MOLD_METAL)
N_CASTINGS = 2
MASS_MOLD_TOTAL = round(MASS_MOLD_METAL * N_CASTINGS, 1)

PRINT_BOT_H = 25.0
PRINT_TOP_H = 15.0
PRINT_DRAFT_BOT = 5.0
PRINT_DRAFT_TOP = 12.0
PRINT_GAP = 0.5
VENT_D = 6.0
VENT_RISER_D = 20.0
VENT_RISER_H = 40.0
FLASK_L = 680.0
FLASK_W = 280.0
