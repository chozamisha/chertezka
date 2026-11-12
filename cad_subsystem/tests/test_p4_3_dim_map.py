# -*- coding: utf-8 -*-
"""P4.3 DRW-016: measure_kind, view binding, no scale guess."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad.geom.view_types import Curve2D, CurveKind, ViewResult
from eskd_cad.model.document import DrawingDocument
from eskd_cad.model.entities import DimLinear
from eskd_cad.qa.p4.dim_map import build_dim_map
from eskd_cad.qa.p4.view_layout import (
    ViewLayout,
    builder_layout_constants,
    parse_builder_view_transforms,
    wheel_view_layouts,
    window_overlap_report,
)
from eskd_cad.spec.casting_spec import CastingSpec
from eskd_cad.views.transform import ViewTransform


def _mini_spec(**kw) -> CastingSpec:
    from eskd_cad.calc import build_koleso_casting_result

    return build_koleso_casting_result().spec


class TestP43ViewLayout(unittest.TestCase):
    def test_layout_k_matches_builder_constants(self):
        """Внутренняя согласованность модуля (не независимый drift)."""
        spec = _mini_spec()
        layouts = wheel_view_layouts(spec)
        expected = builder_layout_constants(spec.scale_k)
        for vid, exp in expected.items():
            L = layouts[vid]
            self.assertAlmostEqual(L.ox, exp["ox"])
            self.assertAlmostEqual(L.oy, exp["oy"])
            self.assertAlmostEqual(L.k, exp["k"])
        self.assertEqual(layouts["local_BB"].k, 2.0)

    def test_layout_matches_independent_builder_source(self):
        """P4.3.1 A3: сверка с литералами foundry/koleso_otlivka.py."""
        spec = _mini_spec()
        layouts = wheel_view_layouts(spec)
        builder = parse_builder_view_transforms(scale_k=spec.scale_k)
        for vid, exp in builder.items():
            L = layouts[vid]
            self.assertAlmostEqual(L.ox, exp["ox"], places=9, msg=vid)
            self.assertAlmostEqual(L.oy, exp["oy"], places=9, msg=vid)
            self.assertAlmostEqual(L.k, exp["k"], places=9, msg=vid)

    def test_independent_parser_detects_artificial_drift(self):
        """Искусственное расхождение layout vs parser → assert fails (A3)."""
        spec = _mini_spec()
        builder = parse_builder_view_transforms(scale_k=spec.scale_k)
        # подмена: как если бы QA-константа уехала
        drifted = dict(builder["AA"])
        drifted["ox"] = builder["AA"]["ox"] + 1.0
        self.assertNotAlmostEqual(drifted["ox"], builder["AA"]["ox"])
        layouts = wheel_view_layouts(spec)
        self.assertAlmostEqual(layouts["AA"].ox, builder["AA"]["ox"])
        self.assertNotAlmostEqual(drifted["ox"], layouts["AA"].ox)

    def test_window_overlaps_documented(self):
        """P4.3.1 A6: пересечения окон существуют и документируются."""
        spec = _mini_spec()
        overlaps = window_overlap_report(spec=spec)
        self.assertTrue(overlaps)
        pairs = {(o["a"], o["b"]) for o in overlaps}
        self.assertTrue(pairs & {("AA", "local_BB"), ("plan", "BB"), ("plan", "local_BB")})


class TestP43DimMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = _mini_spec()
        cls.layouts = wheel_view_layouts(cls.spec)

    def test_measure_kind_ocp_bbox_for_c_out(self):
        spec = self.spec
        L = self.layouts["AA"]
        V = L.transform()
        doc = DrawingDocument()
        # dim spanning C_OUT in AA window
        ro = spec.c_out / 2.0
        doc.add(
            DimLinear(
                p1=V.P(-ro, -25),
                p2=V.P(ro, -25),
                text=f"⌀{int(spec.c_out)}",
            )
        )
        views = {
            "AA": ViewResult(
                name="AA",
                operation="plane_section",
                engine="test",
                curves=[
                    Curve2D(
                        kind=CurveKind.SECTION,
                        points=((-ro, 0.0), (ro, 0.0), (ro, 10.0), (-ro, 10.0)),
                        closed=True,
                    )
                ],
                meta={},
            )
        }
        m = build_dim_map(
            doc=doc, spec=spec, views=views, view_layouts=self.layouts
        )
        rim = next(r for r in m.rows if r.feature_id == "rim_od")
        self.assertEqual(rim.measure_kind, "ocp_bbox")
        self.assertEqual(rim.verification_status, "PASS")
        self.assertEqual(m.aggregate_status, "NOT_CHECKED")

    def test_measure_kind_sheet_span_not_called_ocp(self):
        spec = self.spec
        L = self.layouts["AA"]
        V = L.transform()
        doc = DrawingDocument()
        rh = spec.c_hub / 2.0
        doc.add(
            DimLinear(
                p1=V.P(-rh, 10),
                p2=V.P(rh, 10),
                text=f"⌀{int(spec.c_hub)}",
            )
        )
        m = build_dim_map(
            doc=doc, spec=spec, views=None, view_layouts=self.layouts
        )
        hub = next(r for r in m.rows if r.feature_id == "hub_od")
        self.assertEqual(hub.measure_kind, "sheet_span")
        self.assertEqual(hub.verification_status, "PASS")
        self.assertIn("НЕ OCP", hub.detail)
        self.assertEqual(hub.k, L.k)
        self.assertIsNotNone(hub.sheet_span)

    def test_no_scale_bruteforce(self):
        spec = self.spec
        doc = DrawingDocument()
        doc.add(DimLinear(p1=(0.0, 0.0), p2=(30.0, 0.0), text="60"))
        m = build_dim_map(doc=doc, spec=spec, views=None, view_layouts=None)
        pl = next(r for r in m.rows if r.feature_id == "print_length")
        self.assertEqual(pl.verification_status, "NOT_CHECKED")
        self.assertEqual(pl.measure_kind, "unavailable")

    def test_dim_bound_to_view_window(self):
        spec = self.spec
        # dim far from all windows (local_BB covers large +X near OD)
        doc = DrawingDocument()
        doc.add(
            DimLinear(
                p1=(-500.0, -500.0),
                p2=(-500.0 + spec.l_print / 2.0, -500.0),
                text=f"{int(spec.l_print)}",
            )
        )
        m = build_dim_map(
            doc=doc, spec=spec, views=None, view_layouts=self.layouts
        )
        pl = next(r for r in m.rows if r.feature_id == "print_length")
        self.assertEqual(pl.verification_status, "NOT_CHECKED")
        self.assertEqual(pl.measure_kind, "unavailable")

    def test_ambiguous_view_membership(self):
        # enlarge windows overlap: put dim at midpoint shared — use custom layouts
        spec = self.spec
        layouts = {
            "AA": ViewLayout("AA", 100.0, 100.0, 5.0, 80.0, 80.0),
            "plan": ViewLayout("plan", 140.0, 100.0, 5.0, 80.0, 80.0),
            "BB": ViewLayout("BB", 500.0, 500.0, 8.0, 10.0, 10.0),
            "local_BB": ViewLayout("local_BB", 120.0, 55.0, 2.0, 70.0, 55.0),
        }
        # mid at (120,100) is in both AA and plan
        doc = DrawingDocument()
        half = spec.c_hub / 2.0 / 5.0  # sheet half for hub at k=5
        doc.add(
            DimLinear(
                p1=(120.0 - half, 100.0),
                p2=(120.0 + half, 100.0),
                text=f"⌀{int(spec.c_hub)}",
            )
        )
        m = build_dim_map(doc=doc, spec=spec, views=None, view_layouts=layouts)
        hub = next(r for r in m.rows if r.feature_id == "hub_od")
        self.assertEqual(hub.verification_status, "NOT_CHECKED")
        self.assertEqual(hub.measure_kind, "unavailable")

    def test_print_length_uses_layout_k_2(self):
        spec = self.spec
        L = self.layouts["local_BB"]
        self.assertEqual(L.k, 2.0)
        V = L.transform()
        od = spec.c_out / 2.0
        doc = DrawingDocument()
        doc.add(
            DimLinear(
                p1=V.P(od, -10),
                p2=V.P(od + spec.l_print, -10),
                text=f"{int(spec.l_print)}",
            )
        )
        m = build_dim_map(
            doc=doc, spec=spec, views=None, view_layouts=self.layouts
        )
        pl = next(r for r in m.rows if r.feature_id == "print_length")
        self.assertEqual(pl.k, 2.0)
        self.assertEqual(pl.view_id, "local_BB")
        self.assertEqual(pl.measure_kind, "sheet_span")
        self.assertEqual(pl.verification_status, "PASS")
        self.assertAlmostEqual(pl.measured_value or 0.0, 60.0, places=5)

    def test_aggregate_always_not_checked(self):
        spec = self.spec
        # empty doc — all NOT_CHECKED rows, aggregate still NOT_CHECKED
        m = build_dim_map(
            doc=DrawingDocument(),
            spec=spec,
            views=None,
            view_layouts=self.layouts,
        )
        self.assertEqual(m.aggregate_status, "NOT_CHECKED")


if __name__ == "__main__":
    unittest.main()
