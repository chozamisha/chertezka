# -*- coding: utf-8 -*-
"""MVP: DXF/эталон Корпуса → PartSpec → CastingDraft ≡ drawings/korpus_data."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eskd_cad.part.pipeline import build_casting, part_from_input, run  # noqa: E402
from eskd_cad.part.profiles import korpus  # noqa: E402


def _load_korpus_data():
    path = REPO / "drawings" / "korpus_data.py"
    spec = importlib.util.spec_from_file_location("korpus_data_golden", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestPartToCastingKorpus(unittest.TestCase):
    def test_golden_part_matches_korpus_data(self):
        part = korpus.part_from_golden()
        draft = build_casting(part)
        issues = korpus.assert_matches_korpus_data(draft, _load_korpus_data())
        self.assertEqual(issues, [], msg=issues)

    def test_dxf_extract_builds_casting(self):
        dxf = REPO / "drawings" / "ПП-062215009-00_Korpus.dxf"
        self.assertTrue(dxf.is_file(), f"нет файла {dxf}")
        part = part_from_input(dxf, profile="korpus")
        self.assertEqual(part.profile, "korpus")
        self.assertEqual(part.designation, "ПП-062215009-00")
        for key in korpus.REQUIRED_DIMS:
            self.assertIn(key, part.dimensions, msg=key)
        draft = build_casting(part)
        issues = korpus.assert_matches_korpus_data(draft, _load_korpus_data())
        self.assertEqual(issues, [], msg=issues)

    def test_run_writes_json(self):
        dxf = REPO / "drawings" / "ПП-062215009-00_Korpus.dxf"
        out = ROOT / "out" / "test_part_to_casting"
        result = run(dxf, out_dir=out, profile="korpus", render=False)
        self.assertTrue(Path(result["part_spec"]).is_file())
        self.assertTrue(Path(result["casting_draft"]).is_file())
        self.assertEqual(result["designation"], "ПП-062215009-01")


if __name__ == "__main__":
    unittest.main()
