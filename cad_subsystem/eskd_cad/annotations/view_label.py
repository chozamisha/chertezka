# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple

from ..model.document import DrawingDocument
from ..model.entities import LAYER_TEXT, Text

Point = Tuple[float, float]


def add_view_label(
    doc: DrawingDocument,
    center: Point,
    title: str,
    *,
    scale: Optional[str] = None,
    height: float = 5.0,
) -> None:
    doc.add(Text(center, title, height=height, halign="center", layer=LAYER_TEXT))
    if scale:
        doc.add(
            Text(
                (center[0], center[1] - height - 2),
                scale,
                height=3.5,
                halign="center",
                layer=LAYER_TEXT,
            )
        )
