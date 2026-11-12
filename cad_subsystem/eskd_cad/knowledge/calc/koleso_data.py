# -*- coding: utf-8 -*-
"""Геометрия отливки «Колесо рабочее» КП-062215009-01 — новая сборка."""
# Деталь
D_OUT = 825.0
D_HUB = 240.0
D_BORE = 140.0
D_BORE_LO = 180.0
D_BOSS = 340.0
H_HUB = 253.0          # выступ ступицы над верхним диском
T_DISK = 40.0
H_CH = 115.0           # канал между дисками
H_STEP = 38.0          # ступенька отверстия

# Припуски (calc: ряд 11, чистовая)
N_TOP = 6.0
N_BOT = 5.0
N_FACE = 5.0
N_HUB_OD = 4.0
N_BORE = 4.0
N_BOSS = 3.0

# Отливка
C_HUB = D_HUB + 2 * N_HUB_OD          # 248
C_BORE = D_BORE - 2 * N_BORE          # 132
C_BORE_LO = D_BORE_LO - 2 * N_BORE    # 172
C_BOSS = D_BOSS + 2 * N_BOSS          # 346
C_OUT = D_OUT                         # 825
C_H_HUB = H_HUB + N_TOP               # 259
C_T_TOP = T_DISK + N_FACE             # 45
C_T_BOT = T_DISK + N_FACE             # 45
C_H_CH = H_CH                         # 115

# Ось Y: низ отливки = 0 (без прибыли)
Y_BOT = 0.0
Y_DISK_LO_TOP = C_T_BOT
Y_DISK_UP_BOT = C_T_BOT + C_H_CH
Y_DISK_UP_TOP = Y_DISK_UP_BOT + C_T_TOP
Y_HUB_TOP = Y_DISK_UP_TOP + C_H_HUB
H_BODY = Y_HUB_TOP                    # 464

# Прибыль
D_RISER = 300.0
D_NECK = 240.0
H_RISER = 300.0
Y_RISER_TOP = H_BODY + H_RISER

# Стержни
L_PRINT = 60.0          # гориз. знак Ст.1
H_PRINT2 = 40.0         # верт. знак Ст.2 снизу

# ЛС
F_PIT = 12.0            # см² суммарно
N_PIT = 2
F_SLAG = 14.4
F_SPRUE = 16.8

RHO = 7.46e-6           # кг/мм³ ИЧХ
MASS_STAMP = 420
SCALE_K = 5.0
FMT = 'A2'
CODE = 'КП-062215009-01'
NAME = ['Колесо рабочее', 'Отливка']
MAT = ['Чугун ИЧХ28Н2', 'ТУ 26-06-1484-87']
DEV, CHK = 'Шарабуров', 'Степанова'
