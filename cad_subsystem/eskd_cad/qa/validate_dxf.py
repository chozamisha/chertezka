# -*- coding: utf-8 -*-
"""Проверка DXF: открытие ezdxf + наличие обязательных типов."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import ezdxf


REQUIRED_ANY = [
    {"LWPOLYLINE", "LINE", "POLYLINE"},
    {"CIRCLE", "ARC"},
    {"HATCH"},
    {"DIMENSION"},
    {"TEXT", "MTEXT"},
]


def validate(path: str | Path) -> list[str]:
    path = Path(path)
    issues = []
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        doc = ezdxf.readfile(path)
    except Exception as e:
        return [f"ezdxf cannot open: {e}"]
    msp = doc.modelspace()
    counts = Counter(e.dxftype() for e in msp)
    for group in REQUIRED_ANY:
        if not any(counts.get(t, 0) > 0 for t in group):
            issues.append(f"missing entity type from {sorted(group)}; have {dict(counts)}")
    if sum(counts.values()) < 20:
        issues.append(f"too few entities: {sum(counts.values())}")
    layers = {l.dxf.name for l in doc.layers}
    for need in ("Основная", "Размеры", "Штриховка", "Текст"):
        if need not in layers:
            issues.append(f"missing layer: {need}")
    print("entities:", dict(sorted(counts.items())))
    print("layers:", sorted(layers))
    return issues


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("dxf")
    args = p.parse_args(argv)
    issues = validate(args.dxf)
    for it in issues:
        print("ISSUE:", it)
    if issues:
        print("validate_dxf FAILED")
        return 1
    print("validate_dxf OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
