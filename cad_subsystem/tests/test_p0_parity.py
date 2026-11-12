# -*- coding: utf-8 -*-
"""
P0 паритет: CastingSpec ↔ canonical koleso_data ↔ DXF ключевые размеры.
Не меняет геометрию — только проверяет отсутствие незаметного сдвига чисел.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401
from eskd_cad.export import export_dxf
from eskd_cad.knowledge.calc import koleso_data as KD
from eskd_cad.spec import build_drawing, load_koleso_spec
from eskd_cad.spec.casting_spec import compare_to_module
from eskd_cad.spec.koleso_loader import assert_spec_aligned_with_canon

# Эталон из листа расчёта / koleso_data — зафиксирован, не «на глаз»
GOLDEN = {
    "D_OUT": 825.0,
    "C_HUB": 248.0,
    "C_BORE": 132.0,
    "C_BORE_LO": 172.0,
    "C_BOSS": 346.0,
    "C_OUT": 825.0,
    "H_BODY": 464.0,
    "D_RISER": 300.0,
    "D_NECK": 240.0,
    "H_RISER": 300.0,
    "L_PRINT": 60.0,
    "H_PRINT2": 40.0,
    "F_PIT": 12.0,
    "F_SLAG": 14.4,
    "F_SPRUE": 16.8,
    "MASS_STAMP": 420,
    "SCALE_K": 5.0,
    "CODE": "КП-062215009-01",
}


class TestP0Parity(unittest.TestCase):
    def test_single_source_alignment(self):
        spec = load_koleso_spec()
        issues = assert_spec_aligned_with_canon(spec)
        self.assertEqual(issues, [], msg=issues)
        issues2 = compare_to_module(spec, KD)
        self.assertEqual(issues2, [], msg=issues2)

    def test_golden_params_unchanged(self):
        spec = load_koleso_spec()
        kp = spec.key_params()
        for k, want in GOLDEN.items():
            got = kp[k]
            if isinstance(want, float):
                self.assertAlmostEqual(float(got), want, places=9, msg=k)
            else:
                self.assertEqual(got, want, msg=k)

    def test_legacy_module_matches_golden(self):
        for k, want in GOLDEN.items():
            got = getattr(KD, k)
            if isinstance(want, float):
                self.assertAlmostEqual(float(got), want, places=9, msg=k)
            else:
                self.assertEqual(got, want, msg=k)

    def test_dxf_contains_key_dimensions(self):
        spec = load_koleso_spec()
        doc = build_drawing(spec)
        out = ROOT / "out" / "_parity_KP.dxf"
        out.parent.mkdir(parents=True, exist_ok=True)
        export_dxf(doc, out)

        import ezdxf

        dxf = ezdxf.readfile(out)
        texts = []
        for e in dxf.modelspace():
            if e.dxftype() == "TEXT":
                texts.append(e.dxf.text)
            elif e.dxftype() == "MTEXT":
                texts.append(e.text)
            elif e.dxftype() == "DIMENSION":
                t = getattr(e.dxf, "text", None) or ""
                texts.append(str(t))
        blob = "\n".join(texts)
        # ezdxf may store %%c for diameter
        normalized = blob.replace("%%c", "⌀").replace("\\U+2205", "⌀")

        must = [
            "⌀825",
            "⌀300",
            "⌀240",
            "⌀248",
            "464",
            "300",
            "115",
            "КП-062215009-01",
            "А-А",
            "В-В",
        ]
        missing = [m for m in must if m not in normalized and m not in blob]
        # 825 may appear as %%c825
        if "⌀825" in missing and ("%%c825" in blob or "825" in blob):
            missing = [m for m in missing if m != "⌀825"]
        if "⌀300" in missing and ("%%c300" in blob or "300" in blob):
            missing = [m for m in missing if m != "⌀300"]
        if "⌀240" in missing and ("%%c240" in blob or "240" in blob):
            missing = [m for m in missing if m != "⌀240"]
        if "⌀248" in missing and ("%%c248" in blob or "248" in blob):
            missing = [m for m in missing if m != "⌀248"]
        self.assertEqual(missing, [], msg=f"missing {missing}; sample={blob[:500]}")

        # DIMENSION count
        dims = [e for e in dxf.modelspace() if e.dxftype() == "DIMENSION"]
        self.assertGreaterEqual(len(dims), 5)

    def test_registry_extensible_api(self):
        from eskd_cad.spec.registry import registered_parts

        self.assertIn("koleso_rabochee", registered_parts())


if __name__ == "__main__":
    unittest.main()
