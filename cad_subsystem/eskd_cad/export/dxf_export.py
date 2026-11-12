# -*- coding: utf-8 -*-
"""Экспорт сцены в редактируемый DXF (настоящие CAD-объекты)."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment
from ezdxf.math import Vec2

from ..model.document import DrawingDocument
from ..model.entities import (
    LAYER_ALLOW,
    LAYER_AXIS,
    LAYER_DIM,
    LAYER_HATCH,
    LAYER_HIDDEN,
    LAYER_MAIN,
    LAYER_TEXT,
    LAYER_THIN,
    LAYER_TITLE,
    Arc,
    Circle,
    DimLinear,
    Hatch,
    Leader,
    Line,
    MText,
    Polyline,
    Text,
)

_LAYERS = {
    LAYER_MAIN: dict(color=7, lineweight=70, linetype="CONTINUOUS"),
    LAYER_THIN: dict(color=7, lineweight=25, linetype="CONTINUOUS"),
    LAYER_AXIS: dict(color=7, lineweight=25, linetype="GOST_AXIS"),
    LAYER_HIDDEN: dict(color=7, lineweight=25, linetype="GOST_HIDDEN"),
    LAYER_HATCH: dict(color=7, lineweight=25, linetype="CONTINUOUS"),
    LAYER_DIM: dict(color=7, lineweight=25, linetype="CONTINUOUS"),
    LAYER_TEXT: dict(color=7, lineweight=25, linetype="CONTINUOUS"),
    LAYER_TITLE: dict(color=7, lineweight=50, linetype="CONTINUOUS"),
    LAYER_ALLOW: dict(color=1, lineweight=25, linetype="CONTINUOUS"),  # red
    "Разъем": dict(color=7, lineweight=25, linetype="GOST_AXIS"),
    "Сечение": dict(color=7, lineweight=100, linetype="CONTINUOUS"),
}


def _ensure_styles(doc: ezdxf.document.Drawing) -> None:
    doc.units = units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$LWDISPLAY"] = 1
    if "GOST" not in doc.styles:
        doc.styles.new("GOST", dxfattribs={"font": "OpenGostTypeB-Regular.ttf"})
    if "GOST_AXIS" not in doc.linetypes:
        doc.linetypes.add(
            "GOST_AXIS",
            pattern="A,14.0,-1.5,1.0,-1.5",
            description="Штрихпунктир ГОСТ 2.303",
        )
    if "GOST_HIDDEN" not in doc.linetypes:
        doc.linetypes.add(
            "GOST_HIDDEN",
            pattern="A,5.0,-1.5",
            description="Штриховая ГОСТ 2.303",
        )
    for name, attrs in _LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, **attrs)
    # dimstyle
    if "ESKD" not in doc.dimstyles:
        doc.dimstyles.new(
            "ESKD",
            dxfattribs={
                "dimtxt": 3.5,
                "dimasz": 2.5,
                "dimexe": 1.5,
                "dimexo": 0.0,
                "dimgap": 0.8,
                "dimscale": 1.0,
                "dimtxsty": "GOST",
            },
        )


_HA = {
    ("left", "baseline"): TextEntityAlignment.LEFT,
    ("center", "baseline"): TextEntityAlignment.CENTER,
    ("right", "baseline"): TextEntityAlignment.RIGHT,
    ("left", "bottom"): TextEntityAlignment.LEFT,
    ("center", "bottom"): TextEntityAlignment.CENTER,
    ("right", "bottom"): TextEntityAlignment.RIGHT,
    ("left", "middle"): TextEntityAlignment.MIDDLE_LEFT,
    ("center", "middle"): TextEntityAlignment.MIDDLE_CENTER,
    ("right", "middle"): TextEntityAlignment.MIDDLE_RIGHT,
    ("left", "top"): TextEntityAlignment.TOP_LEFT,
    ("center", "top"): TextEntityAlignment.TOP_CENTER,
    ("right", "top"): TextEntityAlignment.TOP_RIGHT,
}


def _dxf_text(s: str) -> str:
    return (
        s.replace("⌀", "%%c")
        .replace("°", "%%d")
        .replace("±", "%%p")
    )


def export_dxf(drawing: DrawingDocument, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2013", setup=True)
    _ensure_styles(doc)
    msp = doc.modelspace()

    for e in drawing.entities:
        layer = getattr(e, "layer", "0")
        if isinstance(e, Line):
            msp.add_line(e.start, e.end, dxfattribs={"layer": layer})
        elif isinstance(e, Circle):
            msp.add_circle(e.center, e.radius, dxfattribs={"layer": layer})
        elif isinstance(e, Arc):
            msp.add_arc(
                e.center,
                e.radius,
                e.start_angle,
                e.end_angle,
                dxfattribs={"layer": layer},
            )
        elif isinstance(e, Polyline):
            pts = list(e.points)
            if e.closed and pts and pts[0] != pts[-1]:
                pts = pts + [pts[0]]
            msp.add_lwpolyline(
                pts,
                close=e.closed,
                dxfattribs={"layer": layer},
            )
        elif isinstance(e, Hatch):
            h = msp.add_hatch(color=7, dxfattribs={"layer": layer or LAYER_HATCH})
            if e.pattern.upper() == "SOLID":
                h.set_solid_fill()
            else:
                h.set_pattern_fill(e.pattern, scale=e.scale, angle=e.angle)
            h.paths.add_polyline_path(e.path, is_closed=True)
            for hole in e.holes:
                h.paths.add_polyline_path(hole, is_closed=True)
        elif isinstance(e, Text):
            t = msp.add_text(
                _dxf_text(e.content),
                height=e.height,
                rotation=e.rotation,
                dxfattribs={"style": "GOST", "layer": layer or LAYER_TEXT},
            )
            align = _HA.get((e.halign, e.valign), TextEntityAlignment.LEFT)
            t.set_placement(e.position, align=align)
        elif isinstance(e, MText):
            mt = msp.add_mtext(
                _dxf_text(e.content),
                dxfattribs={
                    "style": "GOST",
                    "layer": layer or LAYER_TEXT,
                    "char_height": e.height,
                    "width": e.width,
                    "rotation": e.rotation,
                },
            )
            mt.set_location(e.position, attachment_point=e.attachment)
        elif isinstance(e, DimLinear):
            # true DIMENSION entity
            p1 = Vec2(e.p1)
            p2 = Vec2(e.p2)
            direction = p2 - p1
            if direction.magnitude < 1e-9:
                continue
            normal = direction.orthogonal().normalize()
            # choose normal side by sign of offset
            dist = abs(e.offset)
            # base point for dimension line
            dim = msp.add_linear_dim(
                base=p1 + normal * e.offset,
                p1=p1,
                p2=p2,
                dimstyle="ESKD",
                dxfattribs={"layer": layer or LAYER_DIM},
                text=_dxf_text(e.text) if e.text else None,
                override={"dimtxsty": "GOST"},
            )
            dim.render()
        elif isinstance(e, Leader):
            tip, knee = e.tip, e.knee
            msp.add_line(tip, knee, dxfattribs={"layer": layer or LAYER_THIN})
            # simple arrowhead
            v = Vec2(tip) - Vec2(knee)
            if v.magnitude > 1e-9:
                u = v.normalize()
                n = u.orthogonal()
                a = Vec2(tip) - u * 3.0 + n * 0.9
                b = Vec2(tip) - u * 3.0 - n * 0.9
                msp.add_solid([tip, a, b], dxfattribs={"layer": layer or LAYER_THIN})
            # shelf + text
            tw = max(len(e.text) * e.text_height * 0.7, 10.0)
            if e.side == "right":
                end = (knee[0] + tw, knee[1])
                tx = (knee[0] + 1.0, knee[1] + 1.0)
            else:
                end = (knee[0] - tw, knee[1])
                tx = (knee[0] - tw + 1.0, knee[1] + 1.0)
            msp.add_line(knee, end, dxfattribs={"layer": layer or LAYER_THIN})
            t = msp.add_text(
                _dxf_text(e.text),
                height=e.text_height,
                dxfattribs={"style": "GOST", "layer": LAYER_TEXT},
            )
            t.set_placement(tx, align=TextEntityAlignment.LEFT)

    doc.saveas(path)
    return path
