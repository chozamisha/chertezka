# -*- coding: utf-8 -*-
"""P2: реальные OCP HLR/section; прототип + колесо; legacy путь сохранён."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401
from eskd_cad.calc import build_koleso_casting_result
from eskd_cad.export import export_dxf
from eskd_cad.geom import (
    CurveKind,
    check_view_result,
    ocp_available,
    project_hlr,
    section_plane,
    solid_box_with_bore,
    solid_flange,
    solid_from_casting_spec,
)
from eskd_cad.foundry.koleso_otlivka import build_koleso_otlivka
from eskd_cad.foundry.ocp_koleso import assert_wheel_views_ok, build_wheel_views
from eskd_cad.qa.geometry_check import check_document
from eskd_cad.spec import build_drawing


@unittest.skipUnless(ocp_available(), "OCP8 venv not available")
class TestP2Prototype(unittest.TestCase):
    def test_box_hlr_and_section_are_real_ocp(self):
        solid = solid_box_with_bore((80, 80, 30), bore_d=24)
        front = project_hlr(solid, name="front", look_dir="-y", up_dir="+z")
        sec = section_plane(
            solid,
            name="AA",
            origin=[0, 0, 0],
            normal=[0, 1, 0],
            u_dir=[1, 0, 0],
            v_dir=[0, 0, 1],
        )
        self.assertTrue(front.meta.get("real_ocp"))
        self.assertEqual(front.operation, "hlr_projection")
        self.assertEqual(front.engine, "ocp8")
        self.assertEqual(check_view_result(front, require_operation="hlr_projection"), [])
        self.assertGreaterEqual(len(front.curves_of(CurveKind.VISIBLE)), 1)
        self.assertGreaterEqual(len(front.curves_of(CurveKind.HIDDEN)), 1)

        self.assertTrue(sec.meta.get("real_ocp"))
        self.assertEqual(sec.operation, "plane_section")
        self.assertEqual(check_view_result(sec, require_operation="plane_section"), [])
        bb = sec.bbox()
        self.assertIsNotNone(bb)
        self.assertGreater(bb[2] - bb[0], 20)

    def test_flange_kind_independent_of_wheel(self):
        fl = solid_flange(90, 28, 10, hub_od=45, hub_h=15)
        plan = project_hlr(fl, name="plan", look_dir="+z", up_dir="+y")
        self.assertEqual(check_view_result(plan, require_operation="hlr_projection"), [])


@unittest.skipUnless(ocp_available(), "OCP8 venv not available")
class TestP2Wheel(unittest.TestCase):
    def test_wheel_views_bbox(self):
        spec = build_koleso_casting_result().spec
        views = build_wheel_views(spec)
        assert_wheel_views_ok(views)
        aa = views["AA"]
        self.assertEqual(aa.operation, "plane_section")
        self.assertTrue(aa.meta["real_ocp"])
        width = aa.bbox()[2] - aa.bbox()[0]
        self.assertAlmostEqual(width, 825.0, delta=5.0)

    def test_build_drawing_ocp_vs_legacy(self):
        spec = build_koleso_casting_result().spec
        doc_ocp = build_koleso_otlivka(spec, use_ocp=True)
        doc_leg = build_koleso_otlivka(spec, use_ocp=False)
        self.assertEqual(check_document(doc_ocp), [])
        self.assertEqual(check_document(doc_leg), [])
        # оба пути дают текст кода
        blob_o = " ".join(
            getattr(e, "content", "") or getattr(e, "text", "") or ""
            for e in doc_ocp.entities
        )
        self.assertIn("КП-062215009-01", blob_o)
        self.assertIn("OCP", blob_o)

        out = ROOT / "out" / "_p2_koleso_ocp.dxf"
        out.parent.mkdir(parents=True, exist_ok=True)
        export_dxf(doc_ocp, out)
        self.assertTrue(out.is_file())

    def test_registry_build_drawing_uses_ocp_when_available(self):
        spec = build_koleso_casting_result().spec
        doc = build_drawing(spec)
        blob = " ".join(
            getattr(e, "content", "") or getattr(e, "text", "") or ""
            for e in doc.entities
        )
        self.assertIn("OCP", blob)


class TestP2SolidsDecl(unittest.TestCase):
    def test_casting_solid_decl_no_ocp_needed(self):
        spec = build_koleso_casting_result().spec
        decl = solid_from_casting_spec(spec)
        self.assertEqual(decl["kind"], "revolve_profile")
        self.assertGreaterEqual(len(decl["profile_xz"]), 3)
        self.assertTrue(decl["add_cylinders"])


if __name__ == "__main__":
    unittest.main()
