# -*- coding: utf-8 -*-
"""P2: OCP-проекции и сечения → DrawingDocument."""
from __future__ import annotations

from .emit import emit_curve, emit_view
from .ocp_bridge import ocp_available, project_hlr, section_plane
from .qa_views import check_view_result
from .solids import (
    solid_box_with_bore,
    solid_flange,
    solid_from_casting_spec,
    solid_revolve_profile,
)
from .view_types import Curve2D, CurveKind, ViewResult

__all__ = [
    "Curve2D",
    "CurveKind",
    "ViewResult",
    "check_view_result",
    "emit_curve",
    "emit_view",
    "ocp_available",
    "project_hlr",
    "section_plane",
    "solid_box_with_bore",
    "solid_flange",
    "solid_from_casting_spec",
    "solid_revolve_profile",
]
