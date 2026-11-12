# -*- coding: utf-8 -*-
"""
P1: pipeline вызывает таблицы/гейты; CastingSpec = golden; fail on missing data.
"""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad import foundry  # noqa: F401
from eskd_cad.calc import (
    CalcDataError,
    MissingInputError,
    OutOfRangeError,
    ParamKind,
    UnitError,
    build_casting_from_inputs,
    build_koleso_casting_result,
)
from eskd_cad.calc.core_prints import horiz_print_l_max
from eskd_cad.calc.gost26645_table6 import allowance_mm
from eskd_cad.calc.ls_ratios import areas_from_pit, get_ls_ratio
from eskd_cad.calc.riser_gates import check_riser
from eskd_cad.calc.wheel_inputs import koleso_casting_inputs
from eskd_cad.export import export_dxf
from eskd_cad.knowledge.calc import koleso_data as KD
from eskd_cad.spec import build_drawing
from eskd_cad.spec.casting_spec import compare_to_module
from eskd_cad.spec.koleso_loader import assert_spec_aligned_with_canon

GOLDEN = {
    "D_OUT": 825.0,
    "C_HUB": 248.0,
    "C_BORE": 132.0,
    "C_BORE_LO": 172.0,
    "C_BOSS": 346.0,
    "H_BODY": 464.0,
    "D_RISER": 300.0,
    "D_NECK": 240.0,
    "H_RISER": 300.0,
    "L_PRINT": 60.0,
    "H_PRINT2": 40.0,
    "F_PIT": 12.0,
    "F_SLAG": 14.4,
    "F_SPRUE": 16.8,
    "N_TOP": 6.0,
    "N_BOT": 5.0,
    "N_FACE": 5.0,
    "MASS_STAMP": 420,
    "CODE": "КП-062215009-01",
}


class TestP1TablesCallable(unittest.TestCase):
    def test_table6_wheel_value(self):
        self.assertEqual(allowance_mm(2.8, "Чистовая", 11), 5.2)

    def test_ls_ichx_ratios(self):
        row = get_ls_ratio("ICHX_academic_default")
        fp, fs, fsp = areas_from_pit(12.0, row)
        self.assertAlmostEqual(fp, 12.0)
        self.assertAlmostEqual(fs, 14.4)
        self.assertAlmostEqual(fsp, 16.8)

    def test_horiz_print_l_max_wheel(self):
        l_max, row, col = horiz_print_l_max(115.0, 200.0)
        self.assertEqual(row, "100-160")
        self.assertEqual(col, "160-250")
        self.assertEqual(l_max, 60.0)

    def test_riser_gate_ok_and_fail(self):
        self.assertEqual(check_riser(300, 248), [])
        bad = check_riser(200, 248)
        self.assertTrue(bad)


class TestP1PipelineWheel(unittest.TestCase):
    def test_pipeline_matches_golden_and_canon(self):
        result = build_koleso_casting_result()
        spec = result.spec
        self.assertEqual(result.table6_base_mm, 5.2)
        self.assertEqual(result.l_print_max_mm, 60.0)
        self.assertEqual(result.ls_ratio_case, "ICHX_academic_default")

        kp = spec.key_params()
        for k, want in GOLDEN.items():
            got = kp[k]
            if isinstance(want, float):
                self.assertAlmostEqual(float(got), want, places=9, msg=k)
            else:
                self.assertEqual(got, want, msg=k)

        self.assertEqual(assert_spec_aligned_with_canon(spec), [])
        self.assertEqual(compare_to_module(spec, KD), [])

    def test_provenance_kinds_present(self):
        result = build_koleso_casting_result()
        p = result.provenance
        self.assertEqual(p["TABLE6_BASE"].kind, ParamKind.CALCULATED)
        self.assertEqual(p["TABLE6_BASE"].source, "таблица")
        self.assertEqual(p["F_SLAG"].kind, ParamKind.CALCULATED)
        self.assertEqual(p["F_PIT"].kind, ParamKind.ENGINEER)
        self.assertEqual(p["D_OUT"].kind, ParamKind.SOURCE)
        self.assertEqual(p["C_HUB"].kind, ParamKind.CALCULATED)
        self.assertEqual(p["C_HUB"].source, "формула")
        self.assertEqual(p["L_PRINT"].kind, ParamKind.ENGINEER)
        self.assertEqual(p["L_PRINT_MAX"].kind, ParamKind.CALCULATED)
        self.assertEqual(p["RISER_GATES"].value, "OK")

    def test_dxf_from_pipeline_has_ls_and_dims(self):
        result = build_koleso_casting_result()
        doc = build_drawing(result.spec)
        out = ROOT / "out" / "_p1_pipeline_KP.dxf"
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
        blob = "\n".join(texts)
        # ЛС из расчёта, не «старые константы» в обход pipeline
        compact = blob.replace(" ", "")
        self.assertIn("ΣFп=12", compact)
        self.assertTrue("14.4" in blob or "14,4" in blob)
        self.assertTrue("16.8" in blob or "16,8" in blob)
        self.assertIn("1:1.2:1.4", compact)
        self.assertIn("КП-062215009-01", blob)


class TestP1MissingAndBounds(unittest.TestCase):
    def test_missing_f_pit(self):
        base = koleso_casting_inputs()
        bad_gating = replace(base.gating, f_pit_cm2=0.0)
        bad = replace(base, gating=bad_gating)
        with self.assertRaises(OutOfRangeError):
            build_casting_from_inputs(bad)

    def test_missing_ls_case(self):
        base = koleso_casting_inputs()
        bad = replace(base, gating=replace(base.gating, ls_ratio_case=""))
        with self.assertRaises(MissingInputError):
            build_casting_from_inputs(bad)

    def test_unknown_ls_case(self):
        base = koleso_casting_inputs()
        bad = replace(base, gating=replace(base.gating, ls_ratio_case="NO_SUCH_ALLOY"))
        with self.assertRaises(OutOfRangeError):
            build_casting_from_inputs(bad)

    def test_wrong_unit(self):
        base = koleso_casting_inputs()
        bad = replace(base, geometry=replace(base.geometry, unit="inch"))
        with self.assertRaises(UnitError):
            build_casting_from_inputs(bad)

    def test_allowance_row_out_of_range(self):
        base = koleso_casting_inputs()
        bad = replace(base, allowance=replace(base.allowance, allowance_row=99))
        with self.assertRaises(OutOfRangeError):
            build_casting_from_inputs(bad)

    def test_table6_no_row_does_not_invent(self):
        base = koleso_casting_inputs()
        # огромный допуск вне таблицы — None от allowance_mm → OutOfRange
        bad = replace(
            base,
            allowance=replace(base.allowance, general_tolerance_mm=1e9),
        )
        with self.assertRaises(OutOfRangeError) as ctx:
            build_casting_from_inputs(bad)
        self.assertIn("табл.6", str(ctx.exception))

    def test_riser_too_small_stops(self):
        base = koleso_casting_inputs()
        bad = replace(base, riser=replace(base.riser, d_riser=200.0))
        with self.assertRaises(CalcDataError) as ctx:
            build_casting_from_inputs(bad)
        self.assertIn("Прибыль", str(ctx.exception))

    def test_l_print_above_table_max(self):
        base = koleso_casting_inputs()
        bad = replace(base, cores=replace(base.cores, l_print=120.0))
        with self.assertRaises(CalcDataError) as ctx:
            build_casting_from_inputs(bad)
        self.assertIn("L_PRINT", str(ctx.exception))

    def test_empty_core_scheme(self):
        base = koleso_casting_inputs()
        bad = replace(base, riser=replace(base.riser, core_scheme=""))
        with self.assertRaises((MissingInputError, CalcDataError)):
            build_casting_from_inputs(bad)

    def test_boundary_l_print_equals_max_ok(self):
        base = koleso_casting_inputs()
        # ровно l_max=60
        ok = replace(base, cores=replace(base.cores, l_print=60.0))
        result = build_casting_from_inputs(ok)
        self.assertEqual(result.spec.l_print, 60.0)


if __name__ == "__main__":
    unittest.main()
