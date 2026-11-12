# -*- coding: utf-8 -*-
"""Мост к расчётному модулю / базе знаний. Не подставляет приближения."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def default_knowledge_root() -> Path:
    # pack knowledge if present; else local stub
    candidates = [
        Path("/tmp/eskd_agent_pack/knowledge"),
        Path(__file__).resolve().parents[2] / "knowledge",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def load_json_table(name: str, root: Optional[Path] = None) -> Any:
    root = root or default_knowledge_root()
    path = root / "tables" / name
    if not path.exists():
        raise FileNotFoundError(
            f"Таблица {name} не найдена в {root / 'tables'}. "
            "Нельзя подставлять приближённые значения."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def require_calc_module(module_path: Path):
    if not module_path.exists():
        raise FileNotFoundError(
            f"Расчётный модуль отсутствует: {module_path}. "
            "Инженерные размеры только из calc/knowledge."
        )
    return module_path
