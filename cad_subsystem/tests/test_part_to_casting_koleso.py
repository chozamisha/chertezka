# -*- coding: utf-8 -*-
"""Колесо: PartSpec с исходника → CastingDraft → лист foundry."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eskd_cad.part.pipeline import build_casting, part_from_input, run  # noqa: E402
from eskd_cad.part.profiles import koleso  # noqa: E402

SPEC = ROOT / "examples" / "koleso_part_spec.json"


class TestKolesoFromSource(unittest.TestCase):
    def test_part_spec_matches_golden_geometry(self):
        part = part_from_input(SPEC, profile="koleso")
        self.assertEqual(part.designation, "КП-062215009-01")
        self.assertEqual(part.mass_kg, 340.0)
        self.assertTrue(koleso.matches_golden(part))
        errors, _ = koleso.validate(part)
        self.assertEqual(errors, [])

    def test_build_and_render(self):
        part = part_from_input(SPEC, profile="koleso")
        draft = build_casting(part, confirm_all=True)
        self.assertEqual(draft.designation, "КП-062215009-01")
        self.assertEqual(draft.params["C_HUB"], 248.0)
        self.assertEqual(draft.params["C_BORE"], 132.0)
        self.assertEqual(draft.params["H_BODY"], 464.0)
        self.assertEqual(draft.params["MASS_CAST"], 420.0)
        with tempfile.TemporaryDirectory() as tmp:
            result = run(SPEC, out_dir=tmp, profile="koleso", render=True, confirm_all=True)
            self.assertEqual(result["status"], "final", msg=result.get("qa_issues"))
            self.assertTrue(Path(result["pdf"]).is_file())
            self.assertTrue(Path(result["dxf"]).is_file())


if __name__ == "__main__":
    unittest.main()
