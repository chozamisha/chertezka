# -*- coding: utf-8 -*-
"""Гейты прибыли — тот же код, что в tool/cad_work/qa_check.py (без импорта cad).
Не менять формулы/пороги; при правках синхронизировать с qa_check.
"""
from __future__ import annotations

def check_riser(d_riser: float, d_node: float, min_ratio: float = 1.15) -> list[str]:
    """Техгейт: прибыль не меньше узла (ошибка Колеса)."""
    if d_node <= 0:
        return ["D_узла должен быть > 0"]
    ratio = d_riser / d_node
    if ratio < min_ratio:
        return [
            f"Прибыль меньше узла: D_пр={d_riser} / D_узла={d_node} = {ratio:.3f} "
            f"< {min_ratio}. STOP (см. STOP_GATES G3)."
        ]
    return []


def check_riser_neck(
    d_neck: float,
    d_seat_metal: float,
    d_riser: float | None = None,
    d_node: float | None = None,
) -> list[str]:
    """Шейка/основание ≤ металла посадки; опционально полный check_riser.

    См. knowledge/tables/pribyli_sheyka.md — запрет «шляпки».
    """
    issues: list[str] = []
    if d_seat_metal <= 0:
        return ["D_посадочного металла должен быть > 0"]
    if d_neck <= 0:
        return ["d_ш (шейка/основание) должен быть > 0"]
    if d_neck > d_seat_metal + 1e-6:
        issues.append(
            f"Шейка/основание шире металла посадки: d_ш={d_neck} > D_мет={d_seat_metal}. "
            "STOP (шляпка). Нужен напуск на ступицу или меньше основание — pribyli_sheyka.md."
        )
    if d_riser is not None and d_node is not None:
        issues.extend(check_riser(d_riser, d_node))
    return issues


def check_riser_core_scheme(scheme: str) -> list[str]:
    """Стык прибыль↔стержень отверстия: обязателен вариант A/B/C."""
    s = (scheme or "").strip().upper()
    if s in {"A", "B", "C"}:
        return []
    return [
        "Не выбран вариант стыка прибыль↔стержень (A/B/C) из pribyli_sheyka.md. STOP."
    ]
