# -*- coding: utf-8 -*-
"""P4: статусы PASS/FAIL/WARNING/NOT_CHECKED; NOT_CHECKED ≠ fully_verified."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401
from eskd_cad.calc import build_koleso_casting_result
from eskd_cad.foundry.koleso_otlivka import build_koleso_otlivka
from eskd_cad.qa.p4 import CheckStatus, QualityReport, run_quality_report, write_quality_report
from eskd_cad.qa.p4.status import CheckResult


class TestP4StatusSemantics(unittest.TestCase):
    def test_not_checked_blocks_fully_verified(self):
        r = QualityReport(part_id="x", code="T")
        r.add(
            CheckResult(
                id="A",
                title="a",
                category="inputs",
                status=CheckStatus.PASS,
                condition="c",
            )
        )
        r.add(
            CheckResult(
                id="B",
                title="b",
                category="drawing",
                status=CheckStatus.NOT_CHECKED,
                condition="c",
            )
        )
        self.assertFalse(r.has_fail)
        self.assertTrue(r.has_not_checked)
        self.assertFalse(r.fully_verified)

    def test_fail_blocks_fully_verified(self):
        r = QualityReport(part_id="x", code="T")
        r.add(
            CheckResult(
                id="A",
                title="a",
                category="inputs",
                status=CheckStatus.FAIL,
                condition="c",
                detail="bad",
            )
        )
        self.assertTrue(r.has_fail)
        self.assertFalse(r.fully_verified)
        self.assertTrue(r.errors)


class TestP4WheelReport(unittest.TestCase):
    def test_run_report_wheel(self):
        calc = build_koleso_casting_result()
        doc = build_koleso_otlivka(calc.spec, use_ocp=True)
        q = run_quality_report(spec=calc.spec, calc=calc, doc=doc)
        self.assertGreaterEqual(len(q.checks), 15)
        self.assertFalse(q.has_fail, msg=q.errors)
        # ожидаем NOT_CHECKED (DRW-016 / GEO-002b / INP-009a …) и WARNING
        self.assertTrue(q.has_not_checked)
        self.assertFalse(q.fully_verified)
        statuses = {c.status for c in q.checks}
        self.assertIn(CheckStatus.PASS, statuses)
        self.assertIn(CheckStatus.NOT_CHECKED, statuses)
        ids = {c.id for c in q.checks}
        self.assertIn("INP-009a", ids)
        self.assertIn("GEO-002b", ids)
        self.assertNotIn("INP-009", ids)
        # нормативные поля заполнены
        for c in q.checks:
            self.assertTrue(c.normative_source)
            self.assertTrue(c.condition)
        out = ROOT / "out"
        md, js = write_quality_report(q, out, basename="_p4_test")
        self.assertTrue(md.is_file())
        self.assertTrue(js.is_file())
        text = md.read_text(encoding="utf-8")
        self.assertIn("fully_verified", text)
        self.assertIn("NOT_CHECKED", text)


if __name__ == "__main__":
    unittest.main()
