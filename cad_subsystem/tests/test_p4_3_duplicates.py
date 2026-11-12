# -*- coding: utf-8 -*-
"""P4.3 DRW-006: классификация дубликатов с HLR-match."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad.geom.view_types import Curve2D, CurveKind, ViewResult
from eskd_cad.model.document import DrawingDocument
from eskd_cad.model.entities import LAYER_HIDDEN, LAYER_MAIN, Line
from eskd_cad.qa.p4.duplicate_lines import classify_duplicate_lines
from eskd_cad.qa.p4.view_layout import ViewLayout
from eskd_cad.views.transform import ViewTransform


def _layout(vid="plan", ox=400.0, oy=200.0, k=5.0) -> ViewLayout:
    return ViewLayout(view_id=vid, ox=ox, oy=oy, k=k, half_w=130.0, half_h=130.0)


class TestP43Duplicates(unittest.TestCase):
    def test_confirmed_hlr_coincident(self):
        # model segment (0,0)-(10,0) → sheet via k=5, ox=400, oy=200
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        p1, p2 = V.P(0.0, 0.0), V.P(10.0, 0.0)
        doc = DrawingDocument()
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[
                Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (10.0, 0.0))),
            ],
            meta={"n_hidden": 1},
        )
        groups = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": _layout()}
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].classification, "hlr_coincident")
        self.assertTrue(groups[0].hlr_match)

    def test_real_duplicate_on_hidden_layer(self):
        doc = DrawingDocument()
        # произвольный дубль не из HLR
        doc.add(Line((10.0, 10.0), (20.0, 10.0), layer=LAYER_HIDDEN))
        doc.add(Line((10.0, 10.0), (20.0, 10.0), layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[
                Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (1.0, 0.0))),
            ],
            meta={"n_hidden": 1},
        )
        groups = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": _layout()}
        )
        self.assertEqual(groups[0].classification, "ambiguous_same_geom")
        self.assertFalse(groups[0].hlr_match)

    def test_duplicate_on_main_layer(self):
        doc = DrawingDocument()
        doc.add(Line((0.0, 0.0), (5.0, 0.0), layer=LAYER_MAIN))
        doc.add(Line((0.0, 0.0), (5.0, 0.0), layer=LAYER_MAIN))
        groups = classify_duplicate_lines(doc, views=None, view_layouts=None)
        self.assertEqual(groups[0].classification, "drawing_duplicate")

    def test_ambiguous_without_evidence(self):
        doc = DrawingDocument()
        doc.add(Line((1.0, 1.0), (2.0, 1.0), layer=LAYER_HIDDEN))
        doc.add(Line((1.0, 1.0), (2.0, 1.0), layer=LAYER_HIDDEN))
        groups = classify_duplicate_lines(doc, views=None, view_layouts=None)
        self.assertEqual(groups[0].classification, "ambiguous_same_geom")
        self.assertIn("insufficient_hlr_evidence", groups[0].reason)

    def test_count_above_threshold(self):
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        p1, p2 = V.P(0.0, 0.0), V.P(10.0, 0.0)
        doc = DrawingDocument()
        for _ in range(5):
            doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (10.0, 0.0)))],
            meta={"n_hidden": 1},
        )
        groups = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": _layout()}
        )
        self.assertEqual(groups[0].classification, "ambiguous_same_geom")
        self.assertTrue(groups[0].hlr_match)

    def test_missing_n_hidden_but_curves_ok(self):
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        p1, p2 = V.P(0.0, 0.0), V.P(8.0, 0.0)
        doc = DrawingDocument()
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (8.0, 0.0)))],
            meta={},  # no n_hidden
        )
        groups = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": _layout()}
        )
        self.assertEqual(groups[0].classification, "hlr_coincident")

    def test_view_without_hidden_curves(self):
        doc = DrawingDocument()
        doc.add(Line((1.0, 1.0), (2.0, 2.0), layer=LAYER_HIDDEN))
        doc.add(Line((1.0, 1.0), (2.0, 2.0), layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[Curve2D(kind=CurveKind.VISIBLE, points=((0.0, 0.0), (1.0, 0.0)))],
            meta={"n_hidden": 0},
        )
        groups = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": _layout()}
        )
        self.assertEqual(groups[0].classification, "ambiguous_same_geom")


if __name__ == "__main__":
    unittest.main()
