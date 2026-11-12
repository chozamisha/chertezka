# -*- coding: utf-8 -*-
"""Литниковые соотношения из ls_ratios_all.csv — без переписывания таблиц."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .errors import MissingInputError, OutOfRangeError


def _csv_path() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge" / "calc" / "ls_ratios_all.csv"


@dataclass(frozen=True)
class LsRatioRow:
    alloy_or_case: str
    f_pit: float
    f_slag: float
    f_sprue: float
    system_type: str
    source_note: str


def load_ls_ratios(path: Optional[Path] = None) -> List[LsRatioRow]:
    path = path or _csv_path()
    if not path.is_file():
        raise MissingInputError(f"Файл соотношений ЛС не найден: {path}")
    rows: List[LsRatioRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            # Пропускаем строки с диапазонами вида "1.0-1.5" — не однозначный lookup
            try:
                fp = float(raw["F_pit"])
                fs = float(raw["F_slag"])
                fsp = float(raw["F_sprue"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append(
                LsRatioRow(
                    alloy_or_case=raw["alloy_or_case"].strip(),
                    f_pit=fp,
                    f_slag=fs,
                    f_sprue=fsp,
                    system_type=raw.get("system_type", "").strip(),
                    source_note=raw.get("source_note", "").strip(),
                )
            )
    if not rows:
        raise MissingInputError(f"В {path} нет однозначных числовых строк соотношений")
    return rows


def get_ls_ratio(alloy_or_case: str, path: Optional[Path] = None) -> LsRatioRow:
    if not alloy_or_case or not str(alloy_or_case).strip():
        raise MissingInputError(
            "Не указан alloy_or_case для ls_ratios_all.csv "
            "(например ICHX_academic_default)."
        )
    key = alloy_or_case.strip()
    by_name: Dict[str, LsRatioRow] = {r.alloy_or_case: r for r in load_ls_ratios(path)}
    if key not in by_name:
        known = ", ".join(sorted(by_name))
        raise OutOfRangeError(
            f"Соотношение ЛС '{key}' отсутствует в ls_ratios_all.csv. "
            f"Доступно: {known}"
        )
    return by_name[key]


def areas_from_pit(f_pit_cm2: float, ratio: LsRatioRow) -> tuple[float, float, float]:
    """ΣFп → Fшл, Fст по относительным коэффициентам строки CSV.

    Не вводит новых формул: F_i = F_pit * (ratio_i / ratio_pit).
    """
    if f_pit_cm2 is None:
        raise MissingInputError("F_PIT (см²) обязателен для расчёта ЛС")
    if f_pit_cm2 <= 0:
        raise OutOfRangeError(f"F_PIT должен быть > 0 см², получено {f_pit_cm2}")
    if ratio.f_pit <= 0:
        raise OutOfRangeError(f"В таблице F_pit-коэффициент ≤ 0 для {ratio.alloy_or_case}")
    scale = f_pit_cm2 / ratio.f_pit
    # только устранение двоичного шума (12*1.2), не округление «на глаз»
    def _exactish(x: float) -> float:
        return float(f"{x:.12g}")

    return (
        _exactish(f_pit_cm2),
        _exactish(scale * ratio.f_slag),
        _exactish(scale * ratio.f_sprue),
    )
