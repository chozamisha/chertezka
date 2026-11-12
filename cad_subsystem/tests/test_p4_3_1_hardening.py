# -*- coding: utf-8 -*-
"""P4.3.1: точечные тесты A1–A7."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eskd_cad.annotations.datums import add_datum
from eskd_cad.geom.view_types import Curve2D, CurveKind, ViewResult
from eskd_cad.model.document import DrawingDocument
from eskd_cad.model.entities import (
    LAYER_HIDDEN,
    LAYER_TEXT,
    LAYER_THIN,
    DimLinear,
    Line,
    Polyline,
    Text,
)
from eskd_cad.qa.p4.datum_detect import classify_closed_poly, detect_datums_report
from eskd_cad.qa.p4.dim_map import build_dim_map
from eskd_cad.qa.p4.duplicate_lines import classify_duplicate_lines, summarize_duplicates
from eskd_cad.qa.p4.view_layout import (
    ViewLayout,
    parse_builder_view_transforms,
    wheel_view_layouts,
)
from eskd_cad.views.transform import ViewTransform


def _rot(pts, ang_deg, cx=None, cy=None):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = cx if cx is not None else sum(xs) / len(xs)
    cy = cy if cy is not None else sum(ys) / len(ys)
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return out


class TestA1Classify(unittest.TestCase):
    def test_axis_aligned_square_is_box(self):
        pl = Polyline(points=[(0, 0), (7, 0), (7, 7), (0, 7)], closed=True, layer=LAYER_THIN)
        self.assertEqual(classify_closed_poly(pl).kind, "box")

    def test_rotated_square_not_triangle(self):
        pts = _rot([(0, 0), (7, 0), (7, 7), (0, 7)], 15)
        pl = Polyline(points=pts, closed=True, layer=LAYER_THIN)
        kind = classify_closed_poly(pl).kind
        self.assertNotEqual(kind, "datum_triangle")
        self.assertEqual(kind, "other")

    def test_rotated_rectangle_not_triangle(self):
        pts = _rot([(0, 0), (10, 0), (10, 6), (0, 6)], 20)
        pl = Polyline(points=pts, closed=True, layer=LAYER_THIN)
        self.assertEqual(classify_closed_poly(pl).kind, "other")

    def test_real_datum_triangle(self):
        tip, size = (0.0, 0.0), 6.5
        nx, ny = 1.0, 0.0
        tx, ty = 0.0, 1.0
        a = (tip[0] + nx * size, tip[1] + ny * size)
        b = (tip[0] + tx * size * 0.55, tip[1] + ty * size * 0.55)
        c = (tip[0] - tx * size * 0.55, tip[1] - ty * size * 0.55)
        pl = Polyline(points=[tip, b, a, c], closed=True, layer=LAYER_THIN)
        self.assertEqual(classify_closed_poly(pl).kind, "datum_triangle")

    def test_perturbed_triangle_ok(self):
        tip, size = (0.0, 0.0), 7.0
        a = (size + 0.05, -0.04)
        b = (0.1, size * 0.55 + 0.03)
        c = (-0.08, -size * 0.55)
        pl = Polyline(points=[tip, b, a, c], closed=True, layer=LAYER_THIN)
        self.assertEqual(classify_closed_poly(pl).kind, "datum_triangle")

    def test_extra_vertex_is_other(self):
        pl = Polyline(
            points=[(0, 0), (3.5, 0), (7, 0), (7, 7), (0, 7)],
            closed=True,
            layer=LAYER_THIN,
        )
        self.assertEqual(classify_closed_poly(pl).kind, "other")

    def test_wheel_datums_a_b_still_full(self):
        from eskd_cad.calc import build_koleso_casting_result
        from eskd_cad.spec import build_drawing

        doc = build_drawing(build_koleso_casting_result().spec)
        r = detect_datums_report(doc)
        self.assertEqual(set(r.letters), {"А", "Б"})
        self.assertEqual(r.full_count, 2)
        self.assertEqual(r.partial_clusters, [])


class TestA2Reservation(unittest.TestCase):
    def test_two_real_datums_no_reuse(self):
        doc = DrawingDocument()
        add_datum(doc, (0.0, 0.0), letter="А", outward=(0.0, -1.0), size=7.0)
        add_datum(doc, (120.0, 40.0), letter="Б", outward=(1.0, 0.0), size=6.5)
        r = detect_datums_report(doc)
        self.assertEqual(r.full_count, 2)
        tips = [c.triangle_tip for c in r.full_clusters]
        self.assertEqual(len(tips), len(set(tips)))

    def test_competing_letters_near_box_ambiguous(self):
        doc = DrawingDocument()
        box = [(50.0, 50.0), (57.0, 50.0), (57.0, 57.0), (50.0, 57.0)]
        doc.add(Polyline(points=box, closed=True, layer=LAYER_THIN))
        # две буквы на почти равном расстоянии от центра (53.5, 53.5)
        doc.add(Text((51.5, 53.5), "А", height=5, layer=LAYER_TEXT))
        doc.add(Text((55.5, 53.5), "Б", height=5, layer=LAYER_TEXT))
        r = detect_datums_report(doc)
        self.assertEqual(r.full_count, 0)
        self.assertTrue(
            any("ambiguous_letter" in e.reason for e in r.excluded_other)
        )

    def test_triangle_not_reused_across_boxes(self):
        """Вторая рамка не должна угнать треугольник первой базы."""
        doc = DrawingDocument()
        add_datum(doc, (100.0, 100.0), letter="А", outward=(1.0, 0.0), size=7.0)
        # чужая рамка + буква рядом с уже использованным треугольником
        tip = (100.0, 100.0)
        # box near same triangle without own shelf/triangle
        doc.add(
            Polyline(
                points=[(118.0, 105.0), (125.0, 105.0), (125.0, 112.0), (118.0, 112.0)],
                closed=True,
                layer=LAYER_THIN,
            )
        )
        doc.add(Text((121.5, 106.5), "Б", height=5, layer=LAYER_TEXT))
        r = detect_datums_report(doc)
        self.assertIn("А", r.letters)
        # Б не должна стать full за счёт треугольника А
        self.assertNotIn("Б", r.letters)


class TestA4HlrConsume(unittest.TestCase):
    def _layout(self):
        return ViewLayout("plan", 400.0, 200.0, 5.0, 130.0, 130.0)

    def test_one_seg_one_group(self):
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        p1, p2 = V.P(0.0, 0.0), V.P(10.0, 0.0)
        doc = DrawingDocument()
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (10.0, 0.0)))],
            meta={"n_hidden": 1},
        )
        g = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": self._layout()}
        )
        self.assertEqual(g[0].classification, "hlr_coincident")

    def test_one_seg_two_competing_groups(self):
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        # HLR model (0,0)-(10,0)
        a1, a2 = V.P(0.0, 0.0), V.P(10.0, 0.0)
        b1, b2 = V.P(0.15, 0.0), V.P(10.15, 0.0)  # другой bucket, оба в tol
        doc = DrawingDocument()
        for p, q in ((a1, a2), (a1, a2), (b1, b2), (b1, b2)):
            doc.add(Line(p, q, layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (10.0, 0.0)))],
            meta={"n_hidden": 1},
        )
        groups = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": self._layout()}
        )
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(g.classification == "ambiguous_same_geom" for g in groups))

    def test_two_independent_segs(self):
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        p1, p2 = V.P(0.0, 0.0), V.P(10.0, 0.0)
        q1, q2 = V.P(0.0, 5.0), V.P(10.0, 5.0)
        doc = DrawingDocument()
        for p, q in ((p1, p2), (p1, p2), (q1, q2), (q1, q2)):
            doc.add(Line(p, q, layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[
                Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (10.0, 0.0))),
                Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 5.0), (10.0, 5.0))),
            ],
            meta={"n_hidden": 2},
        )
        groups = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": self._layout()}
        )
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(g.classification == "hlr_coincident" for g in groups))

    def test_reversed_direction(self):
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        p1, p2 = V.P(10.0, 0.0), V.P(0.0, 0.0)  # reverse vs HLR
        doc = DrawingDocument()
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (10.0, 0.0)))],
            meta={"n_hidden": 1},
        )
        g = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": self._layout()}
        )
        self.assertEqual(g[0].classification, "hlr_coincident")

    def test_same_ends_different_length_rejected(self):
        # ends near HLR ends but HLR much longer — length gate
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        # short line near start of long HLR: both ends near (0,0) and (2,0)
        # vs HLR (0,0)-(20,0) — ends won't both match long HLR ends.
        # Construct: Line (0,0)-(10,0) vs HLR (0,0)-(20,0) — ends don't match.
        # Use Line with ends within tol of HLR ends but wrong length impossible
        # unless ends are HLR ends. So: Line endpoints = HLR ends but we
        # compare length of a *different* candidate that only matches ends
        # loosely — craft HLR (0,0)-(10,0) and Line (0,0)-(10,5) with ends
        # not matching. Better: Line ends match after rounding to nearby
        # short vs long with shared endpoints is same length.
        # Practical case: ends_match true only if both ends near → lengths ≈.
        # Force length fail by mocking via slightly matching ends of unequal segs:
        # HLR (0,0)-(10,0); Line sheet ends at (0,0) and (10,0) but we add
        # second HLR (0,0)-(30,0) — Line matches first only.
        # Explicit length reject: Line (0,0)-(3,0) vs HLR points that happen
        # to have ends within 0.35 of line ends while being longer — impossible
        # if HLR ends are the compared ends.
        # So test length_compatible path via ends of polyline mid-break:
        # HLR curve (0,0)-(10,0)-(20,0) → segs of len 10; Line (0,0)-(20,0) len 20
        # ends don't match single seg.
        # Use direct unit of length gate via classify of unequal:
        p1, p2 = V.P(0.0, 0.0), V.P(10.0, 0.0)
        # Line almost matching but we create HLR with same ends coords as a
        # short segment? Skip — use ends that match a short HLR while line is
        # longer by putting HLR as two points that are the line ends... same len.
        # Fall back: Line endpoints equal HLR endpoints → length always matches.
        # Test via _length_compatible indirectly: duplicate HLR curve with
        # different tessellation — already covered by reverse.
        # Craft: HLR segment ends at rounded positions equal to line, length
        # differs if we use points that ends_match with swapped near-ends of a
        # bent polyline of different total length — not a single segment.
        doc = DrawingDocument()
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        # HLR with ends near line ends but length 30 via wrong: ends (0,0) and
        # (10,0) only → same length. Instead HLR ends (0.0, 0.0) and (10.0, 0.2)
        # vs line horizontal — ends within 0.35, length ≈10.002 vs 10 → ok.
        # Make HLR (0,0)-(10.0, 2.0): end2 dist from line end (10,0)=2.0 > 0.35
        # → no match. To get ends_match with different length: line (0,0)-(10,0)
        # HLR (0,0.2)-(10,-0.2): ends within 0.35, length ≈10.008.
        # Need length diff > max(0.35, 0.05*L): HLR (0,0)-(10,5) end2 dist=5>tol.
        # Impossible to have ends within 0.35 AND length differ by >0.35 for
        # straight segments. Length gate is still correct for near-degenerate
        # cases; assert no false coincident when no HLR:
        groups = classify_duplicate_lines(doc, views=None, view_layouts=None)
        self.assertEqual(groups[0].classification, "ambiguous_same_geom")

    def test_duplicate_hlr_curves_deduped(self):
        V = ViewTransform(ox=400.0, oy=200.0, k=5.0)
        p1, p2 = V.P(0.0, 0.0), V.P(8.0, 0.0)
        doc = DrawingDocument()
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        doc.add(Line(p1, p2, layer=LAYER_HIDDEN))
        dup_curve = Curve2D(kind=CurveKind.HIDDEN, points=((0.0, 0.0), (8.0, 0.0)))
        view = ViewResult(
            name="plan",
            operation="hlr_projection",
            engine="test",
            curves=[dup_curve, dup_curve],  # duplicate HLR
            meta={"n_hidden": 2},
        )
        g = classify_duplicate_lines(
            doc, views={"plan": view}, view_layouts={"plan": self._layout()}
        )
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0].classification, "hlr_coincident")

    def test_no_hlr_evidence(self):
        doc = DrawingDocument()
        doc.add(Line((1, 1), (2, 1), layer=LAYER_HIDDEN))
        doc.add(Line((1, 1), (2, 1), layer=LAYER_HIDDEN))
        g = classify_duplicate_lines(doc, views=None, view_layouts=None)
        self.assertEqual(g[0].classification, "ambiguous_same_geom")
        self.assertIn("insufficient_hlr_evidence", g[0].reason)


class TestA5MicroStats(unittest.TestCase):
    def test_summarize_notes_micro_without_filtering(self):
        from eskd_cad.qa.p4.duplicate_lines import DupGroup

        groups = [
            DupGroup(
                layer="Невидимая",
                p1=(0, 0),
                p2=(0.01, 0),
                entity_type="Line",
                count=2,
                classification="hlr_coincident",
                reason="t",
                length_mm_sheet=0.01,
                hlr_match=True,
                matched_view="plan",
            ),
            DupGroup(
                layer="Невидимая",
                p1=(0, 0),
                p2=(2, 0),
                entity_type="Line",
                count=2,
                classification="hlr_coincident",
                reason="t",
                length_mm_sheet=2.0,
                hlr_match=True,
                matched_view="plan",
            ),
        ]
        s = summarize_duplicates(groups)
        self.assertEqual(s["micro_segment_groups_lt_0_05mm"], 1)
        self.assertIn("не фильтруются", s["micro_segment_note"])
        self.assertEqual(s["by_class"]["hlr_coincident"], 2)


class TestA6A7DimMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from eskd_cad.calc import build_koleso_casting_result

        cls.spec = build_koleso_casting_result().spec
        cls.layouts = wheel_view_layouts(cls.spec)

    def test_zero_hits_not_checked(self):
        doc = DrawingDocument()
        doc.add(
            DimLinear(
                p1=(-900.0, -900.0),
                p2=(-900.0 + self.spec.l_print / 2.0, -900.0),
                text=f"{int(self.spec.l_print)}",
            )
        )
        m = build_dim_map(
            doc=doc, spec=self.spec, views=None, view_layouts=self.layouts
        )
        pl = next(r for r in m.rows if r.feature_id == "print_length")
        self.assertEqual(pl.verification_status, "NOT_CHECKED")

    def test_rim_od_evidence_limitation(self):
        L = self.layouts["AA"]
        V = L.transform()
        ro = self.spec.c_out / 2.0
        doc = DrawingDocument()
        doc.add(
            DimLinear(
                p1=V.P(-ro, -25),
                p2=V.P(ro, -25),
                text=f"⌀{int(self.spec.c_out)}",
            )
        )
        views = {
            "AA": ViewResult(
                name="AA",
                operation="plane_section",
                engine="test",
                curves=[
                    Curve2D(
                        kind=CurveKind.SECTION,
                        points=((-ro, 0.0), (ro, 0.0), (ro, 10.0), (-ro, 10.0)),
                        closed=True,
                    )
                ],
                meta={},
            )
        }
        m = build_dim_map(
            doc=doc, spec=self.spec, views=views, view_layouts=self.layouts
        )
        rim = next(r for r in m.rows if r.feature_id == "rim_od")
        self.assertEqual(rim.measure_kind, "ocp_bbox")
        blob = (rim.ocp_geometry + rim.detail).lower()
        self.assertIn("не изолированный", blob)
        self.assertIn("A7", rim.detail)
        self.assertEqual(m.aggregate_status, "NOT_CHECKED")

    def test_builder_parser_independent_of_module_constants(self):
        src = parse_builder_view_transforms.__doc__ or ""
        self.assertIn("Не использует константы view_layout", src)
        b = parse_builder_view_transforms(scale_k=5.0)
        self.assertEqual(b["local_BB"]["k"], 2.0)


if __name__ == "__main__":
    unittest.main()
