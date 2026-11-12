# -*- coding: utf-8 -*-
"""Происхождение параметра: формула / таблица / норматив / ручной ввод."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ParamKind(str, Enum):
    """Классификация относительно процесса расчёта."""

    SOURCE = "source"  # исходные данные детали / ТТ
    CALCULATED = "calculated"  # получено вызовом таблицы/формулы/гейта
    ENGINEER = "engineer"  # задано инженером вручную (принятое)


@dataclass(frozen=True)
class ParamProvenance:
    name: str
    value: Any
    kind: ParamKind
    unit: str
    source: str  # формула | таблица | ГОСТ/ТУ | ручной ввод | …
    detail: str = ""
    doc_ref: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d
