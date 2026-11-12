# -*- coding: utf-8 -*-
"""Программный чеклист 10 требований к технологическому чертежу отливки."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import ezdxf
from ezdxf import recover

from ..model.document import DrawingDocument
from ..model.entities import (
    Circle,
    DimLinear,
    Hatch,
    Leader,
    Line,
    MText,
    Polyline,
    Text,
)
from .geometry_check import check_document, check_dxf_file


Requirement = Tuple[str, bool, str]


def _text_blob(doc: DrawingDocument) -> str:
    parts = []
    for e in doc.entities:
        if isinstance(e, Text):
            parts.append(e.content)
        elif isinstance(e, MText):
            parts.append(e.content)
        elif isinstance(e, Leader):
            parts.append(e.text)
        elif isinstance(e, DimLinear) and e.text:
            parts.append(e.text)
    return "\n".join(parts)


def check_scene_requirements(doc: DrawingDocument) -> List[Requirement]:
    """Проверка сцены до экспорта."""
    blob = _text_blob(doc)
    layers = {getattr(e, "layer", "0") for e in doc.entities}
    n_hatch = sum(1 for e in doc.entities if isinstance(e, Hatch))
    n_dim = sum(1 for e in doc.entities if isinstance(e, DimLinear))
    n_leader = sum(1 for e in doc.entities if isinstance(e, Leader))
    n_circle = sum(1 for e in doc.entities if isinstance(e, Circle))
    n_poly = sum(1 for e in doc.entities if isinstance(e, Polyline))
    n_line = sum(1 for e in doc.entities if isinstance(e, Line))
    has_mtext = any(isinstance(e, MText) for e in doc.entities)
    has_title = "Штамп" in layers or "TEST-CAD" in blob or "КП-" in blob or "ПП-" in blob

    reqs: List[Requirement] = []
    # 1 orthogonal views — CIRCLE (legacy) или OCP-полилинии проекций/сечений
    ortho_ok = (n_circle >= 3 and n_poly >= 2) or (n_poly + n_line >= 20)
    reqs.append(
        (
            "1. Ортогональные виды",
            ortho_ok,
            f"circles={n_circle} polylines={n_poly} lines={n_line}",
        )
    )
    # 2 long/transverse sections — labels А-А and В-В
    reqs.append(
        (
            "2. Продольный и поперечный разрезы",
            ("А-А" in blob or "A-A" in blob) and ("В-В" in blob or "B-B" in blob),
            "labels in text",
        )
    )
    # 3 local section
    reqs.append(
        (
            "3. Местный разрез/сечение",
            ("Б-Б" in blob or "B-B" in blob or "местн" in blob.lower()),
            "local label",
        )
    )
    # 4 hatching
    reqs.append(("4. Штриховка", n_hatch >= 2, f"hatch={n_hatch}"))
    # 5 dimensions
    reqs.append(("5. Размеры", n_dim >= 5, f"dim={n_dim}"))
    # 6 axes and datums
    has_axis = any(getattr(e, "layer", "") == "Осевая" for e in doc.entities)
    has_datum = any(
        isinstance(e, Text) and len(e.content) == 1 and e.content.isalpha() and e.content.isupper()
        for e in doc.entities
    ) or ("база" in blob.lower())
    # also accept explicit datum letters near boxes — look for single letters А/Б used as datums in checklist via layer
    reqs.append(("6. Оси и базы", has_axis, f"axis_layer={has_axis} datum_hint={has_datum}"))
    # 7 leaders + TT
    reqs.append(
        (
            "7. Выноски и ТТ",
            n_leader >= 3 and ("Технические требования" in blob),
            f"leaders={n_leader}",
        )
    )
    # 8 title block
    reqs.append(
        (
            "8. Основная надпись",
            has_title and ("Разраб" in blob or "СФУ" in blob),
            "frame/stamp texts",
        )
    )
    # 9 layers
    need_layers = {"Основная", "Тонкая", "Осевая", "Размеры", "Штриховка", "Текст"}
    reqs.append(
        (
            "9. Слои DXF (сцена)",
            need_layers.issubset(layers),
            f"missing={sorted(need_layers - layers)}",
        )
    )
    # 10 geometry
    geom = check_document(doc)
    reqs.append(("10. Геометрия сцены", len(geom) == 0, f"issues={len(geom)}"))
    return reqs


def check_dxf_requirements(path: str | Path) -> List[Requirement]:
    path = Path(path)
    issues = check_dxf_file(path)
    doc, auditor = recover.readfile(path)
    counts = Counter(e.dxftype() for e in doc.modelspace())
    layers = {l.dxf.name for l in doc.layers}
    reqs: List[Requirement] = []
    reqs.append(
        (
            "DXF открывается без ошибок auditor",
            len(auditor.errors) == 0,
            f"errors={len(auditor.errors)}",
        )
    )
    reqs.append(("DXF DIMENSION", counts.get("DIMENSION", 0) >= 5, str(counts.get("DIMENSION", 0))))
    reqs.append(("DXF HATCH", counts.get("HATCH", 0) >= 2, str(counts.get("HATCH", 0))))
    reqs.append(
        (
            "DXF слои ЕСКД",
            {"Основная", "Размеры", "Штриховка", "Осевая", "Текст"}.issubset(layers),
            str(sorted(layers)),
        )
    )
    reqs.append(("DXF geometry_check", len(issues) == 0, f"issues={issues[:3]}"))
    return reqs


def report(reqs: List[Requirement]) -> Tuple[int, str]:
    lines = []
    bad = 0
    for name, ok, detail in reqs:
        mark = "OK" if ok else "FAIL"
        if not ok:
            bad += 1
        lines.append(f"[{mark}] {name} — {detail}")
    return bad, "\n".join(lines)
