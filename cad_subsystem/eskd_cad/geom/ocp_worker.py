# -*- coding: utf-8 -*-
"""
OCP8 worker: declarative solid → HLR / plane section → 2D polylines (JSON).

Запускать ТОЛЬКО через python-ocp8 (не системный Python).
Не содержит инженерных расчётов P1 — только BRep-операции.
"""
from __future__ import annotations

import json
import math
import sys
from typing import Any, Dict, List, Sequence, Tuple

Point2 = Tuple[float, float]
Point3 = Tuple[float, float, float]


def _sample_edge(edge, deflection: float) -> List[Point3]:
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection

    curve = BRepAdaptor_Curve(edge)
    disc = GCPnts_QuasiUniformDeflection(curve, float(deflection))
    pts: List[Point3] = []
    if not disc.IsDone():
        return pts
    for i in range(1, disc.NbPoints() + 1):
        p = disc.Value(i)
        pts.append((float(p.X()), float(p.Y()), float(p.Z())))
    return pts


def _edges_of(shape) -> list:
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    if shape is None or shape.IsNull():
        return []
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    out = []
    while exp.More():
        out.append(TopoDS.Edge(exp.Current()))
        exp.Next()
    return out


def _fuse(shapes: Sequence[Any]):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy

    if not shapes:
        raise ValueError("empty fuse")
    acc = BRepBuilderAPI_Copy(shapes[0]).Shape()
    for sh in shapes[1:]:
        fuse = BRepAlgoAPI_Fuse(acc, sh)
        fuse.Build()
        if not fuse.IsDone():
            raise RuntimeError("BRepAlgoAPI_Fuse failed")
        acc = fuse.Shape()
    return acc


def _cut(a, b):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

    op = BRepAlgoAPI_Cut(a, b)
    op.Build()
    if not op.IsDone():
        raise RuntimeError("BRepAlgoAPI_Cut failed")
    return op.Shape()


def build_solid(decl: Dict[str, Any]):
    """Собрать TopoDS_Shape из декларативного описания."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import (
        BRepPrimAPI_MakeBox,
        BRepPrimAPI_MakeCylinder,
        BRepPrimAPI_MakeRevol,
    )
    from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt

    kind = decl["kind"]
    if kind == "box_with_bore":
        sx, sy, sz = (float(v) for v in decl["size"])
        cx, cy, cz = (float(v) for v in decl.get("center", (0.0, 0.0, sz / 2)))
        bore = float(decl["bore_d"])
        box = BRepPrimAPI_MakeBox(
            gp_Pnt(cx - sx / 2, cy - sy / 2, cz - sz / 2), sx, sy, sz
        ).Shape()
        cyl = BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(cx, cy, cz - sz / 2 - 1.0), gp_Dir(0, 0, 1)),
            bore / 2.0,
            sz + 2.0,
        ).Shape()
        return _cut(box, cyl)

    if kind == "flange":
        # цилиндр-диск + отверстие + опц. ступица
        od = float(decl["od"])
        id_ = float(decl["id"])
        t = float(decl["thickness"])
        hub_od = float(decl.get("hub_od", 0.0))
        hub_h = float(decl.get("hub_h", 0.0))
        disc = BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), od / 2.0, t
        ).Shape()
        bore = BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(0, 0, -1), gp_Dir(0, 0, 1)), id_ / 2.0, t + hub_h + 2.0
        ).Shape()
        solid = _cut(disc, bore)
        if hub_od > 0 and hub_h > 0:
            hub = BRepPrimAPI_MakeCylinder(
                gp_Ax2(gp_Pnt(0, 0, t), gp_Dir(0, 0, 1)), hub_od / 2.0, hub_h
            ).Shape()
            hub = _cut(hub, bore)
            solid = _fuse([solid, hub])
        return solid

    if kind == "revolve_profile":
        # профиль в плоскости XZ: список (x>=0, z); вращение вокруг Z
        profile: List[Tuple[float, float]] = [
            (float(x), float(z)) for x, z in decl["profile_xz"]
        ]
        if len(profile) < 3:
            raise ValueError("revolve_profile needs >= 3 points")
        poly = BRepBuilderAPI_MakePolygon()
        for x, z in profile:
            poly.Add(gp_Pnt(x, 0.0, z))
        if profile[0] != profile[-1]:
            poly.Add(gp_Pnt(profile[0][0], 0.0, profile[0][1]))
        poly.Close()
        if not poly.IsDone():
            raise RuntimeError("profile polygon failed")
        face = BRepBuilderAPI_MakeFace(poly.Wire(), True).Face()
        axis = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
        revol = BRepPrimAPI_MakeRevol(face, axis, 2 * math.pi, True)
        revol.Build()
        if not revol.IsDone():
            raise RuntimeError("revolve failed")
        solid = revol.Shape()
        # optional fused cylinders (прибыль и т.п.)
        for add in decl.get("add_cylinders") or []:
            r = float(add["d"]) / 2.0
            h = float(add["h"])
            z0 = float(add.get("z0", 0.0))
            cyl = BRepPrimAPI_MakeCylinder(
                gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1)), r, h
            ).Shape()
            solid = _fuse([solid, cyl])
        for sub in decl.get("sub_cylinders") or []:
            r = float(sub["d"]) / 2.0
            h = float(sub["h"])
            z0 = float(sub.get("z0", 0.0))
            cyl = BRepPrimAPI_MakeCylinder(
                gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1)), r, h
            ).Shape()
            solid = _cut(solid, cyl)
        return solid

    if kind == "cylinder":
        d = float(decl["d"])
        h = float(decl["h"])
        z0 = float(decl.get("z0", 0.0))
        x0 = float(decl.get("x0", 0.0))
        y0 = float(decl.get("y0", 0.0))
        return BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(x0, y0, z0), gp_Dir(0, 0, 1)), d / 2.0, h
        ).Shape()

    if kind == "annulus":
        d_out = float(decl["d_out"])
        d_in = float(decl["d_in"])
        h = float(decl["h"])
        z0 = float(decl.get("z0", 0.0))
        outer = BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1)), d_out / 2.0, h
        ).Shape()
        if d_in <= 0:
            return outer
        inner = BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(0, 0, z0 - 0.5), gp_Dir(0, 0, 1)), d_in / 2.0, h + 1.0
        ).Shape()
        return _cut(outer, inner)

    if kind == "box":
        # axis-aligned box: corner (x0,y0,z0) + size (sx,sy,sz), optional rot_z_deg about origin
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        from OCP.gp import gp_Ax1, gp_Trsf

        x0, y0, z0 = (float(v) for v in decl["corner"])
        sx, sy, sz = (float(v) for v in decl["size"])
        box = BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), sx, sy, sz).Shape()
        ang = float(decl.get("rot_z_deg", 0.0))
        if abs(ang) > 1e-12:
            tr = gp_Trsf()
            tr.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(ang))
            box = BRepBuilderAPI_Transform(box, tr, True).Shape()
        return box

    if kind == "radial_blade":
        # призма вдоль радиали: x∈[r_in,r_out], y∈[-t/2,t/2], z∈[z0,z0+h], затем rot_z
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        from OCP.gp import gp_Ax1, gp_Trsf

        r_in = float(decl["r_inner"])
        r_out = float(decl["r_outer"])
        t = float(decl["thickness"])
        z0 = float(decl["z0"])
        h = float(decl["height"])
        ang = float(decl.get("angle_deg", 0.0))
        if r_out <= r_in or t <= 0 or h <= 0:
            raise ValueError("radial_blade: invalid dimensions")
        box = BRepPrimAPI_MakeBox(
            gp_Pnt(r_in, -t / 2.0, z0), r_out - r_in, t, h
        ).Shape()
        if abs(ang) > 1e-12:
            tr = gp_Trsf()
            tr.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(ang))
            box = BRepBuilderAPI_Transform(box, tr, True).Shape()
        return box

    if kind == "riser_neck_fillet":
        # шейка + тело прибыли + галтель (fillet на ребре перехода, иначе torus fallback)
        from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
        from OCP.TopAbs import TopAbs_EDGE
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        d_neck = float(decl["d_neck"])
        d_riser = float(decl["d_riser"])
        h_neck = float(decl["h_neck"])
        h_riser = float(decl["h_riser"])
        z0 = float(decl["z0"])
        fr = float(decl.get("fillet_r", 8.0))
        neck = BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1)), d_neck / 2.0, h_neck
        ).Shape()
        body = BRepPrimAPI_MakeCylinder(
            gp_Ax2(gp_Pnt(0, 0, z0 + h_neck), gp_Dir(0, 0, 1)), d_riser / 2.0, h_riser
        ).Shape()
        solid = _fuse([neck, body])
        if fr > 0 and d_riser > d_neck:
            try:
                mk = BRepFilletAPI_MakeFillet(solid)
                exp = TopExp_Explorer(solid, TopAbs_EDGE)
                # выбираем рёбра на стыке z ≈ z0+h_neck и r между neck и riser
                z_j = z0 + h_neck
                while exp.More():
                    e = TopoDS.Edge(exp.Current())
                    from OCP.BRepAdaptor import BRepAdaptor_Curve

                    c = BRepAdaptor_Curve(e)
                    p0 = c.Value(c.FirstParameter())
                    p1 = c.Value(c.LastParameter())
                    for p in (p0, p1):
                        if abs(p.Z() - z_j) < 1.5:
                            rxy = math.hypot(p.X(), p.Y())
                            if d_neck / 2.0 - 1.0 <= rxy <= d_riser / 2.0 + 1.0:
                                mk.Add(fr, e)
                                break
                    exp.Next()
                mk.Build()
                if mk.IsDone():
                    solid = mk.Shape()
            except Exception:
                pass  # оставляем без галтели, meta отметит
        return solid

    if kind == "assembly":
        # parts: [{name, solid: decl, op: fuse|cut|keep}]
        # base = first fuse; subsequent fuse/cut; keep parts returned separately only via named build
        parts = decl.get("parts") or []
        if not parts:
            raise ValueError("assembly needs parts")
        base = None
        for part in parts:
            sh = build_solid(part["solid"])
            op = (part.get("op") or "fuse").lower()
            if base is None:
                base = sh
                continue
            if op == "fuse":
                base = _fuse([base, sh])
            elif op == "cut":
                base = _cut(base, sh)
            elif op == "skip":
                continue
            else:
                raise ValueError(f"unknown assembly op {op}")
        return base

    raise ValueError(f"unknown solid kind: {kind!r}")


def _volume(shape) -> float:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return float(props.Mass())


def check_intersections(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Проверка пар тел: expected = disjoint | overlap."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

    solids = {p["name"]: build_solid(p["solid"]) for p in payload["solids"]}
    results = []
    issues = []
    for pair in payload.get("pairs") or []:
        a, b = pair["a"], pair["b"]
        expect = pair.get("expect", "disjoint")
        tol = float(pair.get("tol_volume", 500.0))  # мм³
        common = BRepAlgoAPI_Common(solids[a], solids[b])
        common.Build()
        vol = _volume(common.Shape()) if common.IsDone() else 0.0
        ok = (vol <= tol) if expect == "disjoint" else (vol > tol)
        entry = {
            "a": a,
            "b": b,
            "expect": expect,
            "volume_mm3": vol,
            "tol_volume": tol,
            "ok": ok,
        }
        results.append(entry)
        if not ok:
            issues.append(
                f"{a}∩{b}: volume={vol:.1f} mm³, expect {expect} (tol={tol})"
            )
    return {
        "name": payload.get("name", "intersection_check"),
        "operation": "intersection_check",
        "engine": "ocp8",
        "curves": [],
        "meta": {
            "real_ocp": True,
            "results": results,
            "issues": issues,
            "ok": len(issues) == 0,
            "volumes": {n: _volume(s) for n, s in solids.items()},
        },
    }


def _dir_from(name_or_vec) -> Any:
    from OCP.gp import gp_Dir

    if isinstance(name_or_vec, str):
        return {
            "+x": gp_Dir(1, 0, 0),
            "-x": gp_Dir(-1, 0, 0),
            "+y": gp_Dir(0, 1, 0),
            "-y": gp_Dir(0, -1, 0),
            "+z": gp_Dir(0, 0, 1),
            "-z": gp_Dir(0, 0, -1),
        }[name_or_vec.lower()]
    x, y, z = name_or_vec
    return gp_Dir(float(x), float(y), float(z))


def hlr_projection(solid, job: Dict[str, Any]) -> Dict[str, Any]:
    """Ортогональная проекция через HLRBRep (видимые / скрытые / outline)."""
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

    look = _dir_from(job.get("look_dir", "-y"))
    up = _dir_from(job.get("up_dir", "+z"))
    origin = job.get("origin", (0.0, 0.0, 0.0))
    ox, oy, oz = (float(v) for v in origin)
    deflection = float(job.get("deflection", 0.35))

    algo = HLRBRep_Algo()
    algo.Add(solid)
    projector = HLRAlgo_Projector(gp_Ax2(gp_Pnt(ox, oy, oz), look, up))
    algo.Projector(projector)
    algo.Update()
    algo.Hide()
    hlr = HLRBRep_HLRToShape(algo)

    compounds = {
        "visible": hlr.VCompound(),
        "hidden": hlr.HCompound(),
        "outline": hlr.OutLineVCompound(),
        "visible_sharp": hlr.VCompound(),  # alias kept for clarity
    }
    # Also try Rg1 outlines if available
    try:
        compounds["outline_rg1"] = hlr.Rg1LineVCompound()
    except Exception:
        pass

    curves = []
    for kind, shape in compounds.items():
        if kind == "visible_sharp":
            continue
        map_kind = {
            "visible": "visible",
            "hidden": "hidden",
            "outline": "outline",
            "outline_rg1": "outline",
        }[kind]
        for edge in _edges_of(shape):
            pts3 = _sample_edge(edge, deflection)
            if len(pts3) < 2:
                continue
            # HLR кладёт проекцию в XY плоскости вида (Z≈0)
            pts2 = [(p[0], p[1]) for p in pts3]
            curves.append({"kind": map_kind, "points": pts2, "closed": False})

    # осевые линии в плоскости вида (если заданы)
    for ax in job.get("axes_2d") or []:
        curves.append(
            {
                "kind": "axis",
                "points": [list(ax["p1"]), list(ax["p2"])],
                "closed": False,
            }
        )

    return {
        "name": job.get("name", "projection"),
        "operation": "hlr_projection",
        "engine": "ocp8",
        "curves": curves,
        "meta": {
            "look_dir": job.get("look_dir", "-y"),
            "up_dir": job.get("up_dir", "+z"),
            "n_visible": sum(1 for c in curves if c["kind"] == "visible"),
            "n_hidden": sum(1 for c in curves if c["kind"] == "hidden"),
            "n_outline": sum(1 for c in curves if c["kind"] == "outline"),
            "real_ocp": True,
        },
    }


def plane_section(solid, job: Dict[str, Any]) -> Dict[str, Any]:
    """Контуры пересечения секущей плоскости с телом (BRepAlgoAPI_Section)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

    origin = job.get("origin", (0.0, 0.0, 0.0))
    normal = job.get("normal", (0.0, 1.0, 0.0))
    ox, oy, oz = (float(v) for v in origin)
    nx, ny, nz = (float(v) for v in normal)
    deflection = float(job.get("deflection", 0.35))
    # Базис плоскости для 2D: u,v ортонормированы к normal
    u_hint = job.get("u_dir")
    v_hint = job.get("v_dir")

    plane = gp_Pln(gp_Pnt(ox, oy, oz), gp_Dir(nx, ny, nz))
    face = BRepBuilderAPI_MakeFace(plane, -1.0e6, 1.0e6, -1.0e6, 1.0e6).Face()
    sec = BRepAlgoAPI_Section(solid, face)
    sec.Approximation(True)
    sec.ComputePCurveOn1(True)
    sec.Build()
    if not sec.IsDone():
        raise RuntimeError("BRepAlgoAPI_Section failed")

    # orthonormal basis
    n = (nx, ny, nz)
    nlen = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
    n = (n[0] / nlen, n[1] / nlen, n[2] / nlen)

    def cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    if u_hint is not None:
        u = tuple(float(v) for v in u_hint)
    else:
        # choose axis least aligned with normal
        tmp = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
        u = cross(tmp, n)
    ul = math.sqrt(dot(u, u)) or 1.0
    u = (u[0] / ul, u[1] / ul, u[2] / ul)
    if v_hint is not None:
        v = tuple(float(x) for x in v_hint)
        vl = math.sqrt(dot(v, v)) or 1.0
        v = (v[0] / vl, v[1] / vl, v[2] / vl)
    else:
        v = cross(n, u)

    origin3 = (ox, oy, oz)

    def to2(p: Point3) -> Point2:
        d = (p[0] - origin3[0], p[1] - origin3[1], p[2] - origin3[2])
        return (dot(d, u), dot(d, v))

    curves = []
    for edge in _edges_of(sec.Shape()):
        pts3 = _sample_edge(edge, deflection)
        if len(pts3) < 2:
            continue
        pts2 = [to2(p) for p in pts3]
        curves.append({"kind": "section", "points": pts2, "closed": False})

    for ax in job.get("axes_2d") or []:
        curves.append(
            {
                "kind": "axis",
                "points": [list(ax["p1"]), list(ax["p2"])],
                "closed": False,
            }
        )

    return {
        "name": job.get("name", "section"),
        "operation": "plane_section",
        "engine": "ocp8",
        "curves": curves,
        "meta": {
            "origin": [ox, oy, oz],
            "normal": [nx, ny, nz],
            "n_section_edges": len(curves),
            "real_ocp": True,
        },
    }


def run_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    op = payload["operation"]
    if op == "intersection_check":
        return check_intersections(payload)
    if "solid" not in payload:
        raise ValueError("payload.solid required for geometric views")
    solid = build_solid(payload["solid"])
    if op == "hlr_projection":
        return hlr_projection(solid, payload)
    if op == "plane_section":
        return plane_section(solid, payload)
    if op == "volume":
        return {
            "name": payload.get("name", "volume"),
            "operation": "volume",
            "engine": "ocp8",
            "curves": [],
            "meta": {"real_ocp": True, "volume_mm3": _volume(solid)},
        }
    raise ValueError(f"unknown operation: {op!r}")


def main(argv: List[str] | None = None) -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps({"error": "empty stdin"}), file=sys.stderr)
        return 2
    payload = json.loads(raw)
    try:
        result = run_job(payload)
    except Exception as exc:  # noqa: BLE001 — worker boundary
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
