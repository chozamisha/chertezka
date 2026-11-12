# -*- coding: utf-8 -*-
"""P4.5.1: вертикальные стержневые знаки ГОСТ 3212 табл.7."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad.calc.core_prints import (
    check_horiz_print,
    check_vert_print_lower,
    check_vert_print_upper,
    horiz_print_l_max,
    load_vert_lower,
    vert_print_h_max,
)
from eskd_cad.calc.pipeline import build_koleso_casting_result
from eskd_cad.geom.tech_params import wheel_tech_geom
from eskd_cad.qa.p4.runner import run_quality_report


class TestVertTableLoader(unittest.TestCase):
    def test_load_meta(self):
        t = load_vert_lower()
        self.assertEqual(t["standard"], "GOST 3212-92")
        self.assertEqual(t["table"], 7)
        self.assertIn("2.3", t["clause"])
        self.assertEqual(len(t["columns_L"]), 8)

    def test_known_verified_cell_100_160_x_250_400(self):
        # Михальцов/MD: 100–160 × 250–400 → 50
        r = vert_print_h_max(132.0, 300.0)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.value_mm, 50.0)
        self.assertEqual(r.row_key, "100-160")
        self.assertEqual(r.col_key, "250-400")

    def test_wheel_cell_unavailable(self):
        # D=C_BORE=132, L=H_BODY=464 → 100-160 × 400-630 → —
        r = vert_print_h_max(132.0, 464.0)
        self.assertEqual(r.status, "unavailable")
        self.assertIsNone(r.value_mm)

    def test_boundary_D_and_L(self):
        r = vert_print_h_max(160.0, 400.0)  # hi edges of ranges
        self.assertEqual(r.row_key, "100-160")
        self.assertEqual(r.col_key, "250-400")
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.value_mm, 50.0)

    def test_missing_inputs(self):
        r = vert_print_h_max(None, 100.0)
        self.assertEqual(r.status, "missing_input")
        r2 = vert_print_h_max(100.0, None)
        self.assertEqual(r2.status, "missing_input")
        r3 = vert_print_h_max(0.0, 100.0)
        self.assertEqual(r3.status, "missing_input")

    def test_out_of_range(self):
        r = vert_print_h_max(5000.0, 100.0)
        self.assertEqual(r.status, "out_of_range")

    def test_unverified_cell_not_numeric(self):
        # row 40-63 has verified=false cells
        r = vert_print_h_max(50.0, 20.0)
        self.assertIn(r.status, {"unverified", "unavailable"})
        self.assertIsNone(r.value_mm)

    def test_no_interpolation_gap(self):
        # 63-100 × 100-160 is unavailable — must not invent from neighbors
        r = vert_print_h_max(80.0, 120.0)
        self.assertEqual(r.status, "unavailable")
        self.assertIsNone(r.value_mm)


class TestVertNormativeChecks(unittest.TestCase):
    def test_h_print2_less_than_max(self):
        c = check_vert_print_lower(40.0, 132.0, 300.0)
        self.assertEqual(c["status"], "PASS")
        self.assertTrue(c["comparison"]["ok"])

    def test_h_print2_equal_max(self):
        c = check_vert_print_lower(50.0, 132.0, 300.0)
        self.assertEqual(c["status"], "PASS")

    def test_h_print2_greater_than_max(self):
        c = check_vert_print_lower(60.0, 132.0, 300.0)
        self.assertEqual(c["status"], "WARNING")
        self.assertFalse(c["comparison"]["ok"])

    def test_missing_D_L_H(self):
        self.assertEqual(check_vert_print_lower(40.0, None, 300.0)["status"], "NOT_CHECKED")
        self.assertEqual(check_vert_print_lower(40.0, 132.0, None)["status"], "NOT_CHECKED")
        self.assertEqual(check_vert_print_lower(None, 132.0, 300.0)["status"], "NOT_CHECKED")

    def test_unavailable_cell_not_checked(self):
        c = check_vert_print_lower(40.0, 132.0, 464.0)
        self.assertEqual(c["status"], "NOT_CHECKED")

    def test_upper_rule_ok(self):
        u = check_vert_print_upper(25.0, 40.0, upper_present=True)
        self.assertEqual(u["status"], "PASS")

    def test_upper_rule_fail(self):
        u = check_vert_print_upper(10.0, 40.0, upper_present=True)
        self.assertEqual(u["status"], "WARNING")

    def test_upper_absent_not_checked(self):
        u = check_vert_print_upper(None, 40.0, upper_present=False)
        self.assertEqual(u["status"], "NOT_CHECKED")
        self.assertIn("отсутствует", u["detail"])


class TestVertIntegration(unittest.TestCase):
    def test_horiz_unchanged(self):
        l_max, row, col = horiz_print_l_max(115.0, 200.0)
        self.assertEqual(l_max, 60.0)
        _, issues = check_horiz_print(60.0, 115.0, 200.0)
        self.assertEqual(issues, [])

    def test_pipeline_provenance_and_wheel_not_checked(self):
        r = build_koleso_casting_result()
        self.assertEqual(r.spec.h_print2, 40.0)
        self.assertEqual(r.spec.c_bore, 132.0)
        self.assertEqual(r.spec.h_body, 464.0)
        self.assertIsNone(r.h_print2_max_mm)
        self.assertIsNotNone(r.vert_print_check)
        self.assertEqual(r.vert_print_check["status"], "NOT_CHECKED")
        self.assertEqual(r.vert_print_check["lookup"]["status"], "unavailable")
        self.assertIn("H_PRINT2", r.provenance)
        self.assertIn("H_PRINT2_MAX", r.provenance)
        self.assertIn("CORE2_D", r.provenance)
        self.assertIn("CORE2_L", r.provenance)
        # engineer origin of H_PRINT2 preserved
        self.assertEqual(r.provenance["H_PRINT2"].kind.value, "engineer")
        # geometry params unchanged
        tech = wheel_tech_geom(r.spec)
        self.assertEqual(tech.core2.print_h_mm, 40.0)
        self.assertEqual(tech.core2.diameter_mm, 132.0)
        self.assertEqual(tech.core2.height_mm, 464.0)

    def test_inp008_not_checked_on_wheel(self):
        r = build_koleso_casting_result()
        q = run_quality_report(spec=r.spec, calc=r, use_ocp=True)
        inp8 = next(c for c in q.checks if c.id == "INP-008")
        self.assertEqual(inp8.status.value, "NOT_CHECKED")
        self.assertIn("h_max", inp8.condition)
        self.assertIn("табл.7", inp8.title)
        self.assertTrue(inp8.evidence)
        # counts: still WARNING from other items; INP-008 no longer WARNING
        # fully_verified still False
        self.assertFalse(q.fully_verified)


if __name__ == "__main__":
    unittest.main()
