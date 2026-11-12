# -*- coding: utf-8 -*-
"""P4.3 DRW-004: детектор баз."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad.annotations.cutting_plane import add_cutting_plane
from eskd_cad.annotations.datums import add_datum
from eskd_cad.model.document import DrawingDocument
from eskd_cad.model.entities import LAYER_TEXT, LAYER_THIN, Polyline, Text
from eskd_cad.qa.p4.datum_detect import datum_check_payload, detect_datums_report


def _empty_doc() -> DrawingDocument:
    return DrawingDocument()


class TestP43Datums(unittest.TestCase):
    def test_real_datum_A(self):
        doc = _empty_doc()
        add_datum(doc, (100.0, 100.0), letter="А", outward=(0.0, -1.0), size=7.0)
        r = detect_datums_report(doc)
        self.assertGreaterEqual(r.full_count, 1)
        self.assertIn("А", r.letters)

    def test_real_datum_B(self):
        doc = _empty_doc()
        add_datum(doc, (200.0, 150.0), letter="Б", outward=(1.0, 0.0), size=6.5)
        r = detect_datums_report(doc)
        self.assertGreaterEqual(r.full_count, 1)
        self.assertIn("Б", r.letters)
        full = [c for c in r.full_clusters if c.letter == "Б"]
        self.assertTrue(full)
        self.assertEqual(full[0].confidence, "full_pattern")

    def test_cutting_plane_letters_excluded(self):
        doc = _empty_doc()
        add_cutting_plane(doc, (0.0, 0.0), (100.0, 0.0), letter="А", tick=9)
        add_cutting_plane(doc, (50.0, -50.0), (50.0, 50.0), letter="В", tick=9)
        # чужая рамка рядом с буквой сечения
        doc.add(
            Polyline(
                points=[(108.0, 8.0), (115.0, 8.0), (115.0, 15.0), (108.0, 15.0)],
                closed=True,
                layer=LAYER_THIN,
            )
        )
        r = detect_datums_report(doc)
        self.assertEqual(r.full_count, 0)
        self.assertTrue(r.excluded_cutting_letters)
        letters = {e.letter for e in r.excluded_cutting_letters}
        self.assertTrue({"А", "В"} & letters)

    def test_stamp_letters_excluded(self):
        doc = _empty_doc()
        doc.add(Text((10.0, 10.0), "У", height=3.5, layer=LAYER_TEXT))
        r = detect_datums_report(doc)
        self.assertEqual(r.full_count, 0)
        self.assertEqual(r.partial_clusters, [])

    def test_partial_pattern(self):
        doc = _empty_doc()
        # только рамка + буква, без треугольника/полки
        box = [(50.0, 50.0), (57.0, 50.0), (57.0, 57.0), (50.0, 57.0)]
        doc.add(Polyline(points=box, closed=True, layer=LAYER_THIN))
        doc.add(Text((53.5, 51.5), "А", height=5, halign="center", layer=LAYER_TEXT))
        r = detect_datums_report(doc)
        self.assertEqual(r.full_count, 0)
        self.assertTrue(r.partial_clusters)

    def test_foreign_box_near_cutting_letter(self):
        doc = _empty_doc()
        add_cutting_plane(doc, (0.0, 0.0), (80.0, 0.0), letter="А", tick=9)
        # рамка рядом с буквой сечения
        doc.add(
            Polyline(
                points=[(85.0, 5.0), (92.0, 5.0), (92.0, 12.0), (85.0, 12.0)],
                closed=True,
                layer=LAYER_THIN,
            )
        )
        r = detect_datums_report(doc)
        self.assertEqual(r.full_count, 0)
        self.assertTrue(any(e.letter == "А" for e in r.excluded_cutting_letters))

    def test_multiple_datums(self):
        doc = _empty_doc()
        add_datum(doc, (0.0, 0.0), letter="А", outward=(0.0, -1.0), size=7.0)
        add_datum(doc, (120.0, 40.0), letter="Б", outward=(1.0, 0.0), size=6.5)
        r = detect_datums_report(doc)
        self.assertGreaterEqual(r.full_count, 2)
        self.assertTrue({"А", "Б"} <= set(r.letters))
        payload = datum_check_payload(doc)
        self.assertIn("full_clusters", payload)
        self.assertIn("excluded_cutting_letters", payload)


if __name__ == "__main__":
    unittest.main()
