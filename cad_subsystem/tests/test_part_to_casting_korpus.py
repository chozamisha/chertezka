# -*- coding: utf-8 -*-
"""Деталь → отливка: геометрия DXF, PartSpec JSON, лист через cad_work."""
from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eskd_cad.part import decisions as decisions_mod  # noqa: E402
from eskd_cad.part.pipeline import build_casting, part_from_input, render_korpus_otlivka, run  # noqa: E402
from eskd_cad.part.part_spec import HoleGroup, PartSpec, Ribs  # noqa: E402
from eskd_cad.part.profiles import korpus  # noqa: E402

REF_DXF = REPO / "drawings" / "ПП-062215009-00_Korpus.dxf"
REF_DIMS = {
    "h_part": 100.0,
    "t_top_part": 15.0,
    "t_bot_part": 20.0,
    "d_top": 200.0,
    "d_bot": 300.0,
    "d_bore_top": 120.0,
    "d_bore_bot": 190.0,
    "wall": 15.0,
}


def _variant_part() -> PartSpec:
    """Другие размеры, та же топология — не эталон ПП-062215009."""
    return PartSpec(
        part_id="VAR-90-00",
        designation="VAR-90-00",
        name=["Корпус"],
        material=["СЧ15", "ГОСТ 1412-85"],
        mass_kg=12.0,
        scale="1:2",
        profile="korpus",
        dimensions={
            "h_part": 90.0,
            "t_top_part": 12.0,
            "t_bot_part": 18.0,
            "d_top": 180.0,
            "d_bot": 260.0,
            "d_bore_top": 100.0,
            "d_bore_bot": 160.0,
            "wall": 12.0,
        },
        holes=[
            HoleGroup(pcd=220.0, n=6, d=10.0, angle0=0.0, kind="cbore", d_cb=20.0, cb_depth=12.0,
                      label="6 отв. ⌀10, цек. ⌀20×12"),
            HoleGroup(pcd=140.0, n=4, d=6.0, angle0=45.0, kind="thread", label="4 отв. М6"),
        ],
        ribs=Ribs(n=6, width=8.0, angle0=30.0, r_out=124.0),
        roughness={"top": "Ra 6,3", "bottom": "Ra 6,3", "general": "Ra 12,5"},
        stamp={"dev": "Шевцов", "chk": "Степанова", "org": ["СФУ ИЦМ", "гр. ЗЦМ22-01Б"], "lit": "У"},
        provenance={k: "тест" for k in REF_DIMS},
    )


class TestExtractReference(unittest.TestCase):
    def test_dxf_geometry_matches_reference(self):
        part = part_from_input(REF_DXF, profile="korpus")
        self.assertEqual(part.designation, "ПП-062215009-00")
        self.assertEqual(part.mass_kg, 15.0)
        self.assertEqual(part.material, ["СЧ15", "ГОСТ 1412-85"])
        self.assertEqual(part.stamp["dev"], "Шевцов")
        for key, want in REF_DIMS.items():
            self.assertAlmostEqual(part.dimensions[key], want, places=1, msg=key)
        self.assertEqual(len(part.holes), 2)
        outer, inner = part.holes
        self.assertEqual((outer.n, outer.d, outer.d_cb, outer.cb_depth), (6, 12.0, 24.0, 16.0))
        self.assertEqual((inner.n, inner.kind, inner.d), (4, "thread", 8.0))
        self.assertIsNotNone(part.ribs)
        self.assertEqual(part.ribs.n, 6)
        self.assertAlmostEqual(part.ribs.width, 10.0, places=1)
        self.assertEqual(part.roughness.get("top"), "Ra 6,3")
        self.assertEqual(part.questions, [])
        # числа пришли с размерных надписей, а не из захардкоженного эталона
        self.assertIn("размерное число", part.provenance["d_bot"])
        self.assertIn("геометрия", part.provenance["d_bot"])

    def test_validate_flags_mass_vs_geometry(self):
        part = part_from_input(REF_DXF, profile="korpus")
        errors, warnings = korpus.validate(part)
        self.assertEqual(errors, [])
        self.assertTrue(any("штампе" in w for w in warnings))


class TestDecisionsAndCasting(unittest.TestCase):
    def test_unconfirmed_blocks_final(self):
        part = part_from_input(REF_DXF, profile="korpus")
        draft = build_casting(part)
        self.assertTrue(draft.params["_unconfirmed"])
        self.assertTrue(any("Неподтверждённые" in q for q in draft.questions))

    def test_confirm_all_builds_casting(self):
        part = part_from_input(REF_DXF, profile="korpus")
        draft = build_casting(part, confirm_all=True)
        self.assertEqual(draft.designation, "ПП-062215009-01")
        self.assertEqual(draft.params["H_CAST"], 107.0)
        self.assertEqual(draft.params["T_TOP_CAST"], 19.0)
        self.assertEqual(draft.params["T_BOT_CAST"], 23.0)
        self.assertEqual(draft.params["D_BORE_TOP_CAST"], 116.0)
        self.assertEqual(draft.params["_unconfirmed"], [])
        # масса = штамп детали + припуски + незалитые отверстия
        self.assertAlmostEqual(draft.params["MASS_CAST"], 17.6, places=1)

    def test_decision_override_file(self):
        part = part_from_input(REF_DXF, profile="korpus")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dec.json"
            path.write_text(json.dumps({"mass_cast_kg": 16.5, "allow_top": 5.0}), encoding="utf-8")
            draft = build_casting(part, decisions_path=path, confirm_all=True)
        self.assertEqual(draft.params["MASS_CAST"], 16.5)
        self.assertEqual(draft.params["ALLOW_TOP"], 5.0)
        self.assertEqual(draft.params["H_CAST"], 108.0)  # 100+5+3


class TestVariantNotBoundToGolden(unittest.TestCase):
    def test_variant_json_casting_and_qa(self):
        part = _variant_part()
        errors, _ = korpus.validate(part)
        self.assertEqual(errors, [])
        draft = build_casting(part, confirm_all=True)
        self.assertEqual(draft.designation, "VAR-90-01")
        self.assertEqual(draft.params["H_CAST"], 97.0)  # 90+4+3
        self.assertEqual(draft.params["D_BOT"], 260.0)
        self.assertNotEqual(draft.params["D_BOT"], REF_DIMS["d_bot"])
        with tempfile.TemporaryDirectory() as tmp:
            rendered = render_korpus_otlivka(draft, out_dir=Path(tmp))
            self.assertEqual(rendered["qa_issues"], [], msg=rendered["qa_issues"])
            self.assertTrue(rendered["final"])
            self.assertTrue(Path(rendered["pdf"]).is_file())


class TestRun(unittest.TestCase):
    def test_run_writes_json_without_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(REF_DXF, out_dir=tmp, profile="korpus", confirm_all=True)
            self.assertEqual(result["status"], "ready")
            self.assertTrue(Path(result["part_spec"]).is_file())
            self.assertTrue(Path(result["casting_draft"]).is_file())
            self.assertTrue(Path(result["decisions"]).is_file())
            self.assertEqual(result["designation"], "ПП-062215009-01")

    def test_run_render_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(REF_DXF, out_dir=tmp, profile="korpus", render=True, confirm_all=True)
            self.assertEqual(result.get("qa_issues"), [], msg=result.get("qa_issues"))
            self.assertEqual(result["status"], "final")
            self.assertTrue(Path(result["pdf"]).is_file())


class TestVariantDxfRoundtrip(unittest.TestCase):
    """Собрать DXF детали с другими размерами и прочитать его без эталона."""

    def test_generated_detail_dxf(self):
        drawings = REPO / "drawings"
        # минимальный набор констант, который читает drawings/draw_detal.py
        vals = {
            "H_PART": 90.0, "T_TOP_PART": 12.0, "T_BOT_PART": 18.0,
            "D_TOP": 180.0, "D_BOT": 260.0, "D_BORE_TOP": 100.0, "D_BORE_BOT": 160.0,
            "WALL": 12.0, "RIB_W": 8.0, "PCD_OUTER": 220.0, "PCD_INNER": 140.0,
            "D_THRU": 10.0, "D_CB": 20.0, "CB_DEPTH": 12.0,
            "N_OUTER": 6, "N_INNER": 4, "N_RIBS": 6, "R_FILLET": 5.0,
            "R_OUT_TOP": 50.0 + 12.0, "R_OUT_BOT": 80.0 + 12.0,
            "R_IN_TOP": 50.0, "R_IN_BOT": 80.0,
            "MATERIAL": ["СЧ15", "ГОСТ 1412-85"],
            "MASS_PART": 12.0, "MASS_PART_STR": "12",
            "DESIGNATION_00": "VAR-90-00", "DESIGNATION_01": "VAR-90-01", "DESIGNATION_02": "VAR-90-02",
            "DEV": "Шевцов", "CHK": "Степанова", "ORG": ("СФУ ИЦМ", "гр. ЗЦМ22-01Б"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            # drawings/draw_detal.py пишет рядом с собой — подменим OUT и ART
            sys.path.insert(0, str(drawings))
            for name in ("draw_detal", "cad", "korpus_data"):
                sys.modules.pop(name, None)
            mod = types.ModuleType("korpus_data")
            for k, v in vals.items():
                setattr(mod, k, v)
            sys.modules["korpus_data"] = mod
            import draw_detal  # type: ignore

            draw_detal.OUT = out
            draw_detal.ART = out / "art"
            draw_detal.ART.mkdir()
            draw_detal.D = mod
            draw_detal.main()
            dxf = out / "ПП-062215009-00_Korpus.dxf"
            # draw_detal hardcodes filename; rename conceptually by reading that path
            self.assertTrue(dxf.is_file())
            # исправим обозначение в DXF текстах: draw_detal пишет DESIGNATION_00 из модуля
            part = korpus.part_from_dxf(str(dxf))
            sys.path.remove(str(drawings))
            for name in ("draw_detal", "cad", "korpus_data"):
                sys.modules.pop(name, None)

        self.assertEqual(part.designation, "VAR-90-00")
        self.assertAlmostEqual(part.dimensions["h_part"], 90.0, places=0)
        self.assertAlmostEqual(part.dimensions["d_bot"], 260.0, places=0)
        self.assertAlmostEqual(part.dimensions["d_top"], 180.0, places=0)
        self.assertAlmostEqual(part.dimensions["wall"], 12.0, places=0)
        self.assertNotEqual(part.dimensions["d_bot"], REF_DIMS["d_bot"])
        draft = build_casting(part, confirm_all=True)
        self.assertEqual(draft.params["H_CAST"], 97.0)


if __name__ == "__main__":
    unittest.main()
