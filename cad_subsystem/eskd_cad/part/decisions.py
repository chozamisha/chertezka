# -*- coding: utf-8 -*-
"""Технологические решения по отливке: значение, откуда взято, подтверждено ли.

Всё, чего нет на исходном чертеже детали (припуски, уклоны, класс точности,
масса отливки), попадает сюда явно. Пока хотя бы одно решение не подтверждено,
лист выпускается только как черновик.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .part_spec import PartSpec

ENGINEER = "задано в файле решений"


@dataclass
class Decision:
    value: Any
    source: str
    confirmed: bool = False
    note: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def default_decisions(part: PartSpec) -> Dict[str, Decision]:
    if part.profile == "korpus":
        from .profiles import korpus
        return korpus.default_decisions(part)
    if part.profile == "koleso":
        from .profiles import koleso
        return koleso.default_decisions(part)
    raise ValueError(f"Нет decisions для profile={part.profile!r}")


def load_overrides(path: str | Path) -> Dict[str, Decision]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: Dict[str, Decision] = {}
    for key, item in data.items():
        if isinstance(item, dict) and "value" in item and set(item) <= {"value", "source", "confirmed", "note"}:
            out[key] = Decision(item["value"], item.get("source", ENGINEER),
                                bool(item.get("confirmed", False)), item.get("note", ""))
        else:
            out[key] = Decision(item, ENGINEER, True)
    return out


def resolve(part: PartSpec, overrides: Optional[Dict[str, Decision]] = None,
            confirm_all: bool = False) -> Dict[str, Decision]:
    out = default_decisions(part)
    unknown = sorted(set(overrides or {}) - set(out))
    if unknown:
        raise ValueError("Неизвестные решения: " + ", ".join(unknown))
    out.update(overrides or {})
    if confirm_all:
        for dec in out.values():
            if not dec.confirmed:
                dec.confirmed = True
                dec.source += "; подтверждено инженером"
    return out


def unconfirmed(decisions: Dict[str, Decision]) -> List[str]:
    return [k for k, v in decisions.items() if not v.confirmed]


def dump(decisions: Dict[str, Decision]) -> Dict[str, Any]:
    return {k: v.as_dict() for k, v in decisions.items()}
