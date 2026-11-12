# -*- coding: utf-8 -*-
"""Рамка и основная надпись формы 1 (упрощённо, мм листа)."""
from __future__ import annotations

from typing import List, Sequence, Tuple

from .document import DrawingDocument
from .entities import (
    LAYER_MAIN,
    LAYER_TEXT,
    LAYER_THIN,
    LAYER_TITLE,
    Line,
    Polyline,
    Text,
)


def apply_frame(
    doc: DrawingDocument,
    *,
    name_lines: Sequence[str],
    code: str,
    material: str,
    mass: str,
    scale: str,
    org: Tuple[str, str] = ("СФУ ИЦМ", "гр. ЗЦМ22-01Б"),
    sheet: str = "1",
    sheets: str = "1",
    lit: str = "У",
    dev: str = "Агент",
    chk: str = "—",
) -> None:
    W, H = doc.width, doc.height
    x0, y0, x1, y1 = 20.0, 5.0, W - 5.0, H - 5.0
    doc.add(
        Polyline(
            points=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
            closed=True,
            layer=LAYER_MAIN,
        )
    )

    # title block 185×55
    bx, by = x1 - 185.0, y0
    doc.add(
        Polyline(
            points=[(bx, by), (x1, by), (x1, by + 55), (bx, by + 55)],
            closed=True,
            layer=LAYER_TITLE,
        )
    )
    # verticals
    for c in (7, 17, 40, 55, 65):
        doc.add(Line((bx + c, by), (bx + c, by + 55), layer=LAYER_TITLE))
    for i in range(1, 11):
        yy = by + 5 * i
        kind = LAYER_TITLE if i in (6, 7) else LAYER_THIN
        doc.add(Line((bx, yy), (bx + 65, yy), layer=kind))

    labels = ["Разраб.", "Пров.", "Т.контр.", "", "Н.контр.", "Утв."]
    names = [dev, chk, "", "", "", ""]
    for i, (lb, nm) in enumerate(zip(labels, names)):
        yy = by + 25 - 5 * i + (2.2 if i == 5 else 1.3)
        if lb:
            doc.add(Text((bx + 7.4, yy), lb, height=2.2, layer=LAYER_TEXT))
        if nm:
            doc.add(Text((bx + 17.8, yy), nm, height=2.5, layer=LAYER_TEXT))

    for c0, c1, s in zip(
        [0, 7, 17, 40, 55],
        [7, 17, 40, 55, 65],
        ["Изм.", "Лист", "№ докум.", "Подп.", "Дата"],
    ):
        doc.add(
            Text(
                (bx + (c0 + c1) / 2, by + 31.3),
                s,
                height=2.5,
                halign="center",
                layer=LAYER_TEXT,
            )
        )

    rx = bx + 65
    doc.add(Line((rx, by + 40), (x1, by + 40), layer=LAYER_TITLE))
    doc.add(Line((rx, by + 15), (x1, by + 15), layer=LAYER_TITLE))
    mx = rx + 70
    doc.add(Line((mx, by), (mx, by + 40), layer=LAYER_TITLE))
    doc.add(Line((mx, by + 35), (x1, by + 35), layer=LAYER_TITLE))
    doc.add(Line((mx, by + 20), (x1, by + 20), layer=LAYER_TITLE))
    doc.add(Line((mx + 15, by + 20), (mx + 15, by + 40), layer=LAYER_TITLE))
    doc.add(Line((mx + 32, by + 20), (mx + 32, by + 40), layer=LAYER_TITLE))
    doc.add(Line((mx + 20, by + 15), (mx + 20, by + 20), layer=LAYER_TITLE))

    def T(x, y, s, h=2.5, ha="left"):
        doc.add(Text((x, y), s, height=h, halign=ha, layer=LAYER_TEXT))

    T(mx + 7.5, by + 36.3, "Лит.", ha="center")
    T(mx + 23.5, by + 36.3, "Масса", ha="center")
    T(mx + 41, by + 36.3, "Масштаб", ha="center")
    T(mx + 7.5, by + 26, lit, h=3.5, ha="center")
    T(mx + 23.5, by + 26, mass, h=3.5, ha="center")
    T(mx + 41, by + 26, scale, h=3.5, ha="center")
    T(mx + 1, by + 16.3, "Лист " + sheet)
    T(mx + 21, by + 16.3, "Листов " + sheets)
    T(rx + 60, by + 47.5, code, h=7, ha="center")
    n = len(name_lines)
    for i, s in enumerate(name_lines):
        T(
            rx + 35,
            by + 27.5 + (n - 1) * 3.2 - i * 6.4,
            s,
            h=5 if i == 0 else 3.5,
            ha="center",
        )
    T(rx + 35, by + 8, material, h=3.5, ha="center")
    T((bx + rx) / 2, by + 8, org[0], h=3.5, ha="center")
    T((bx + rx) / 2, by + 3.5, org[1], h=2.5, ha="center")

    # left inventory strip (simplified)
    for i, s in enumerate(
        ["Инв. № подл.", "Подп. и дата", "Взам. инв. №", "Инв. № дубл."]
    ):
        doc.add(
            Text(
                (7.0, y0 + 20 + i * 35),
                s,
                height=2.5,
                rotation=90,
                layer=LAYER_TEXT,
            )
        )

    doc.title = {
        "code": code,
        "name": list(name_lines),
        "material": material,
        "mass": mass,
        "scale": scale,
    }
