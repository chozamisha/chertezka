# -*- coding: utf-8 -*-
"""Реестр builders: другие детали подключаются без копирования логики колеса."""
from __future__ import annotations

from typing import Callable, Dict

from ..model.document import DrawingDocument
from .casting_spec import CastingSpec

Builder = Callable[[CastingSpec], DrawingDocument]

_BUILDERS: Dict[str, Builder] = {}


def register_builder(part_id: str, fn: Builder | None = None):
    """Регистрация builder. Можно как @register_builder(id) или register_builder(id, fn)."""

    def deco(f: Builder) -> Builder:
        _BUILDERS[part_id] = f
        return f

    if fn is not None:
        return deco(fn)
    return deco


def build_drawing(spec: CastingSpec) -> DrawingDocument:
    if spec.part_id not in _BUILDERS:
        known = ", ".join(sorted(_BUILDERS)) or "(пусто)"
        raise KeyError(
            f"Нет builder для part_id={spec.part_id!r}. Зарегистрированы: {known}"
        )
    return _BUILDERS[spec.part_id](spec)


def registered_parts() -> list[str]:
    return sorted(_BUILDERS)
