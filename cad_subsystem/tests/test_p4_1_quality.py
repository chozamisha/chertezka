# -*- coding: utf-8 -*-
"""P4.1: усиление QA — split INP-009, DRW-006/004/016, GEO-002b."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401
from eskd_cad.calc import build_koleso_casting_result
from eskd_cad.foundry.koleso_otlivka import build_koleso_otlivka
from eskd_cad.geom import ocp_available
from eskd_cad.qa.p4 import CheckStatus, run_quality_report
from eskd_cad.qa.p4.datum_detect import detect_datums
from eskd_cad.qa.p4.dim_map import build_dim_map
from eskd_cad.qa.p4.duplicate_lines import classify_duplicate_lines


@unittest.skipUnless(ocp_available(), "OCP8 venv not available")
class TestP41Wheel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calc = build_koleso_casting_result()
        cls.spec = cls.calc.spec
        cls.doc = build_koleso_otlivka(cls.spec, use_ocp=True)
        cls.q = run_quality_report(spec=cls.spec, calc=cls.calc, doc=cls.doc)

    def _by_id(self, cid: str):
        for c in self.q.checks:
            if c.id == cid:
                return c
        self.fail(f"missing check {cid}")

    def test_calc_values_unchanged(self):
        self.assertEqual(self.calc.table6_base_mm, 5.2)
        self.assertEqual(self.spec.n_top, 6.0)
        self.assertEqual(self.spec.n_bot, 5.0)
        self.assertEqual(self.spec.n_face, 5.0)
        self.assertEqual(self.spec.h_body, 464.0)
        self.assertEqual(self.spec.l_print, 60.0)
        self.assertEqual(self.spec.h_print2, 40.0)
        self.assertEqual((self.spec.f_pit, self.spec.f_slag, self.spec.f_sprue), (12.0, 14.4, 16.8))

    def test_inp009_split_no_gost_pass(self):
        a = self._by_id("INP-009a")
        b = self._by_id("INP-009b")
        c = self._by_id("INP-009c")
        # N_TOP=6 >= 5.2 — NOT_CHECKED (не PASS по ГОСТ)
        self.assertEqual(a.status, CheckStatus.NOT_CHECKED)
        self.assertIn("gost_direction=unconfirmed", a.evidence)
        # N_BOT/N_FACE < base — WARNING, не FAIL и не «ГОСТ PASS»
        self.assertEqual(b.status, CheckStatus.WARNING)
        self.assertEqual(c.status, CheckStatus.WARNING)
        self.assertIn("внутреннее", b.normative_source.lower())
        # монолитного INP-009 больше нет
        self.assertFalse(any(x.id == "INP-009" for x in self.q.checks))

    def test_geo002_pass_and_002b_not_checked(self):
        g2 = self._by_id("GEO-002")
        g2b = self._by_id("GEO-002b")
        self.assertEqual(g2.status, CheckStatus.PASS)
        self.assertEqual(g2b.status, CheckStatus.NOT_CHECKED)
        ev = json.loads(g2.evidence)
        self.assertIn("pairs", ev)
        self.assertTrue(any(p["a"] == "metal" and p["b"] == "core1" for p in ev["pairs"]))
        for p in ev["pairs"]:
            self.assertEqual(p["unit"], "mm3")
            self.assertIn("volume_mm3", p)

    def test_drw006_classifies_hlr(self):
        groups = classify_duplicate_lines(self.doc)
        self.assertTrue(groups)
        self.assertTrue(all(g.classification for g in groups))
        d6 = self._by_id("DRW-006")
        # на колесе дубли только HLR → PASS с диагностикой
        self.assertEqual(d6.status, CheckStatus.PASS)
        ev = json.loads(d6.evidence)
        self.assertGreaterEqual(ev["by_class"].get("hlr_coincident", 0), 1)

    def test_drw004_datum_pattern(self):
        from eskd_cad.qa.p4.datum_detect import detect_datums_report

        r = detect_datums_report(self.doc)
        self.assertGreaterEqual(r.full_count, 1)
        self.assertIn("Б", r.letters)
        d4 = self._by_id("DRW-004")
        self.assertEqual(d4.status, CheckStatus.PASS)

    def test_drw016_aggregate_not_checked(self):
        d16 = self._by_id("DRW-016")
        self.assertEqual(d16.status, CheckStatus.NOT_CHECKED)
        ev = json.loads(d16.evidence)
        self.assertEqual(ev["aggregate_status"], "NOT_CHECKED")
        self.assertEqual(len(ev["rows"]), 8)
        # даже если все строки PASS — агрегат NOT_CHECKED
        if all(r["verification_status"] == "PASS" for r in ev["rows"]):
            self.assertEqual(ev["aggregate_status"], "NOT_CHECKED")

    def test_dim_map_no_text_only_pass(self):
        m = build_dim_map(doc=self.doc, spec=self.spec, views=None)
        for r in m.rows:
            if "только текст" in r.detail:
                self.assertEqual(r.verification_status, "NOT_CHECKED")

    def test_fully_verified_false(self):
        self.assertFalse(self.q.has_fail)
        self.assertTrue(self.q.has_not_checked)
        self.assertFalse(self.q.fully_verified)


if __name__ == "__main__":
    unittest.main()
