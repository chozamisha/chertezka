# -*- coding: utf-8 -*-
"""Ошибки расчётного контура — без подстановки выдуманных значений."""
from __future__ import annotations


class CalcDataError(ValueError):
    """Базовая ошибка: данных недостаточно или они недопустимы."""


class MissingInputError(CalcDataError):
    """Обязательный исходный параметр отсутствует."""


class OutOfRangeError(CalcDataError):
    """Значение вне допустимого диапазона / таблицы."""


class UnitError(CalcDataError):
    """Неверная или несовместимая единица измерения."""
