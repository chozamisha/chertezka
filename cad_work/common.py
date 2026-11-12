# -*- coding: utf-8 -*-
"""Общие хелперы листов ЕСКД."""
from __future__ import annotations

import cad
from cad import text_width

DIA = "\u2300"


def fix_stamp_two_line_cells(sh, by=5.0, material=("СЧ15", "ГОСТ 1412-85"),
                             org=("СФУ ИЦМ", "гр. ЗЦМ22-01Б")):
    """Переставить двухстрочные тексты в графах материала/организации,
    чтобы bbox не пересекались при обязательных двух строках орг."""
    material = [material] if isinstance(material, str) else list(material)
    org = list(org)
    drop = set(material) | set(org) | {" ".join(material)}
    keep = []
    for e in sh.ents:
        if e[0] != "text":
            keep.append(e)
            continue
        (x, y), s, h, ha, va, rot = e[1:]
        if rot == 0 and 5.0 <= y <= 20.5 and x >= 295 and h >= 3.0 and s in drop:
            continue
        keep.append(e)
    sh.ents = keep
    # материал одной строкой по центру графы
    sh.text(230 + 65 + 35, by + 7.5, " ".join(material), h=3.5, ha="center", va="center")
    # организация: две строки с шагом 6.5 мм
    if len(org) == 1:
        sh.text(230 + 65 + 70 + 25, by + 7.5, org[0], h=3.5, ha="center", va="center")
    else:
        sh.text(230 + 65 + 70 + 25, by + 11.0, org[0], h=3.5, ha="center", va="center")
        sh.text(230 + 65 + 70 + 25, by + 4.5, org[1], h=3.5, ha="center", va="center")


def cbo_glyph(sh, x, y, h=3.5):
    w = 0.80 * h
    sh.seg(x, y + 0.85 * h, x, y, "thin")
    sh.seg(x, y, x + w, y, "thin")
    sh.seg(x + w, y, x + w, y + 0.85 * h, "thin")
    return w


def leader_cbo(sh, tip, knee, depth, h=3.5):
    """6 отв. ⌀12, ⌴⌀24 / depth."""
    import numpy as np

    tip = np.asarray(tip, float)
    knee = np.asarray(knee, float)
    sh.seg(*tip, *knee, "thin")
    sh.arrow(tip, tip - knee)
    pref = f"6 отв. {DIA}12, "
    w_pref = text_width(pref, h)
    w_dia = text_width(f"{DIA}24", h)
    w_cbo = 0.80 * h + 0.25
    total = w_pref + w_cbo + w_dia + 2.0
    sh.seg(knee[0], knee[1], knee[0] + total, knee[1], "thin")
    sh.text(knee[0] + 1, knee[1] + 1.0, pref, h)
    cx = knee[0] + 1 + w_pref
    cbo_glyph(sh, cx, knee[1] + 0.35, h)
    sh.text(cx + w_cbo, knee[1] + 1.0, f"{DIA}24", h)
    sh.text(cx + w_cbo * 0.45, knee[1] - 1.2, str(int(depth)), h, ha="center", va="top")


def write_tt(sh, lines, x0=248.0, y_base=66.0, step=6.0):
    """ТТ над штампом, шаг базовых линий 6 мм."""
    for i, s in enumerate(reversed(lines)):
        sh.text(x0, y_base + i * step, s, h=3.5, va="baseline")
