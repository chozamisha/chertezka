# -*- coding: utf-8 -*-
"""P3: лопатки/стержни/ЛС/прибыль/хол./Б-Б — реальный OCP + intersection QA."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401
from eskd_cad.calc import build_koleso_casting_result
from eskd_cad.export import export_dxf
from eskd_cad.foundry.koleso_otlivka import build_koleso_otlivka
from eskd_cad.foundry.ocp_koleso import (
    assert_wheel_views_ok,
    build_wheel_views,
    run_wheel_intersection_qa,
)
from eskd_cad.geom import ocp_available
from eskd_cad.geom.assembly_wheel import metal_plus_tech_for_views
from eskd_cad.geom.ocp_bridge import run_ocp_job
from eskd_cad.geom.tech_params import MissingTechDataError, wheel_tech_geom
from eskd_cad.qa.geometry_check import check_document


@unittest.skipUnless(ocp_available(), "OCP8 venv not available")
class TestP3TechParams(unittest.TestCase):
    def test_wheel_tech_notes_missing_blade_profile(self):
        spec = build_koleso_casting_result().spec
        tech = wheel_tech_geom(spec)
        self.assertFalse(tech.blades.is_hydraulic_profile)
        self.assertEqual(tech.blades.count, 4)
        self.assertTrue(any("шаблон" in n for n in tech.notes))


@unittest.skipUnless(ocp_available(), "OCP8 venv not available")
class TestP3SolidsAndQA(unittest.TestCase):
    def test_metal_volume_has_blades_channel_cut(self):
        spec = build_koleso_casting_result().spec
        tech = wheel_tech_geom(spec)
        metal = metal_plus_tech_for_views(spec, tech)
        self.assertTrue(metal["meta"].get("channel_cut"))
        self.assertEqual(metal["meta"]["blades"], 4)
        vol = run_ocp_job({"solid": metal, "operation": "volume", "name": "m"}).meta[
            "volume_mm3"
        ]
        self.assertGreater(vol, 1e6)

    def test_intersection_qa_ok(self):
        spec = build_koleso_casting_result().spec
        res = run_wheel_intersection_qa(spec)
        self.assertTrue(res.meta.get("real_ocp"))
        self.assertTrue(res.meta.get("ok"), msg=res.meta.get("issues"))

    def test_views_include_local_bb_print(self):
        spec = build_koleso_casting_result().spec
        views = build_wheel_views(spec)
        assert_wheel_views_ok(views)
        self.assertIn("local_BB", views)
        self.assertEqual(views["local_BB"].operation, "plane_section")
        self.assertTrue(views["local_BB"].meta.get("real_ocp"))
        # лопатки на плане: больше hidden-кривых, чем у осесимметрии без лопаток
        self.assertGreaterEqual(views["plan"].meta.get("n_hidden", 0), 20)

    def test_build_drawing_p3(self):
        spec = build_koleso_casting_result().spec
        doc = build_koleso_otlivka(spec, use_ocp=True)
        self.assertEqual(check_document(doc), [])
        blob = " ".join(
            getattr(e, "content", "") or getattr(e, "text", "") or ""
            for e in doc.entities
        )
        self.assertIn("Б-Б", blob)
        self.assertIn("OCP", blob)
        out = ROOT / "out" / "_p3_koleso.dxf"
        out.parent.mkdir(parents=True, exist_ok=True)
        export_dxf(doc, out)
        self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
