# -*- coding: utf-8 -*-
"""P4.3 / P4.3.1: read-only зеркало окон видов листа колеса (без изменений foundry API).

Константы должны совпадать с build_koleso_otlivka:
  Vsec = ViewTransform(ox=145, oy=235, k=SCALE_K)
  Vpln = ViewTransform(ox=400, oy=200, k=SCALE_K)
  Vbb  = ViewTransform(ox=520, oy=300, k=SCALE_K*1.6)
  Vloc = ViewTransform(ox=120, oy=55,  k=2.0)

P4.3.1 A6: окна hit-test **пересекаются** (AA∩local_BB, plan∩BB, plan∩local_BB).
Привязка DimLinear: 0 или >1 попаданий → NOT_CHECKED; ближайший вид не выбирается.
"""
from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...spec.casting_spec import CastingSpec
from ...views.transform import ViewTransform

# --- builder mirror constants (sheet mm / k) ---
AA_OX, AA_OY = 145.0, 235.0
PLAN_OX, PLAN_OY = 400.0, 200.0
BB_OX, BB_OY = 520.0, 300.0
BB_K_FACTOR = 1.6
LOCAL_OX, LOCAL_OY, LOCAL_K = 120.0, 55.0, 2.0

# окна hit-test DimLinear midpoint (sheet mm half-extents).
# local_BB: знак у OD → mid размера L_PRINT ~ (341, 50) при ox=120 → half_w≥230.
# Пересечения окон намеренны (см. window_overlap_report); не сужать ради PASS.
_WINDOWS = {
    "AA": (110.0, 165.0),
    "plan": (130.0, 130.0),
    "BB": (55.0, 80.0),  # уже, чтобы ⌀825 В-В не пересекался с plan слишком сильно
    "local_BB": (240.0, 60.0),
}

_BUILDER_SRC = (
    Path(__file__).resolve().parents[2] / "foundry" / "koleso_otlivka.py"
)


@dataclass(frozen=True)
class ViewLayout:
    view_id: str
    ox: float
    oy: float
    k: float
    half_w: float
    half_h: float

    def transform(self) -> ViewTransform:
        return ViewTransform(ox=self.ox, oy=self.oy, k=self.k)

    def contains(self, x: float, y: float) -> bool:
        return abs(x - self.ox) <= self.half_w and abs(y - self.oy) <= self.half_h

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def wheel_view_layouts(spec: CastingSpec) -> Dict[str, ViewLayout]:
    """Реестр видов листа для QA (scale = ViewTransform.k, не текст подписи)."""
    sk = float(spec.scale_k)
    out: Dict[str, ViewLayout] = {}
    for vid, ox, oy, k in (
        ("AA", AA_OX, AA_OY, sk),
        ("plan", PLAN_OX, PLAN_OY, sk),
        ("BB", BB_OX, BB_OY, sk * BB_K_FACTOR),
        ("local_BB", LOCAL_OX, LOCAL_OY, LOCAL_K),
    ):
        hw, hh = _WINDOWS[vid]
        out[vid] = ViewLayout(
            view_id=vid, ox=ox, oy=oy, k=k, half_w=hw, half_h=hh
        )
    return out


def builder_layout_constants(scale_k: float) -> Dict[str, Dict[str, float]]:
    """Внутреннее зеркало констант модуля (НЕ независимый эталон builder).

    Для независимого drift-теста используйте parse_builder_view_transforms().
    """
    sk = float(scale_k)
    return {
        "AA": {"ox": AA_OX, "oy": AA_OY, "k": sk},
        "plan": {"ox": PLAN_OX, "oy": PLAN_OY, "k": sk},
        "BB": {"ox": BB_OX, "oy": BB_OY, "k": sk * BB_K_FACTOR},
        "local_BB": {"ox": LOCAL_OX, "oy": LOCAL_OY, "k": LOCAL_K},
    }


def _eval_builder_expr(expr: str, *, scale_k: float) -> float:
    """Безопасно вычислить ox/oy/k литерал builder при известном SCALE_K."""
    src = expr.strip()
    src = re.sub(r"\bD\.SCALE_K\b", repr(float(scale_k)), src)
    src = re.sub(r"\bSCALE_K\b", repr(float(scale_k)), src)
    tree = ast.parse(src, mode="eval")
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.UAdd,
        ast.Pow,
    )
    for node in ast.walk(tree):
        if isinstance(node, allowed) or type(node).__name__ == "Num":
            continue
        raise ValueError(f"недопустимое выражение builder ViewTransform: {expr!r}")
    # AST whitelist: только арифметика над константами
    return float(eval(compile(tree, "<builder_k>", "eval"), {"__builtins__": {}}))  # noqa: S307


def parse_builder_view_transforms(
    *,
    scale_k: float,
    source_path: Path | None = None,
) -> Dict[str, Dict[str, float]]:
    """Независимый эталон: литералы ViewTransform из foundry/koleso_otlivka.py.

    Не использует константы view_layout.py — читает исходник builder.
    Порядок на листе колеса: AA, plan, BB, local_BB.
    """
    path = source_path or _BUILDER_SRC
    text = path.read_text(encoding="utf-8")
    pats = re.findall(
        r"ViewTransform\(\s*ox\s*=\s*([^,]+)\s*,\s*oy\s*=\s*([^,]+)\s*,\s*k\s*=\s*([^)]+)\)",
        text,
    )
    if len(pats) < 4:
        raise ValueError(
            f"ожидалось ≥4 ViewTransform в {path}, найдено {len(pats)}"
        )
    names = ("AA", "plan", "BB", "local_BB")
    out: Dict[str, Dict[str, float]] = {}
    for name, (ox_e, oy_e, k_e) in zip(names, pats[:4]):
        out[name] = {
            "ox": _eval_builder_expr(ox_e, scale_k=scale_k),
            "oy": _eval_builder_expr(oy_e, scale_k=scale_k),
            "k": _eval_builder_expr(k_e, scale_k=scale_k),
        }
    return out


def window_overlap_report(
    layouts: Dict[str, ViewLayout] | None = None,
    *,
    spec: CastingSpec | None = None,
) -> List[Dict[str, Any]]:
    """Фактические пересечения окон hit-test (P4.3.1 A6, документирование)."""
    if layouts is None:
        if spec is None:
            raise ValueError("нужен layouts или spec")
        layouts = wheel_view_layouts(spec)
    ids = list(layouts.keys())
    overlaps: List[Dict[str, Any]] = []
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            La, Lb = layouts[a], layouts[b]
            ax0, ax1 = La.ox - La.half_w, La.ox + La.half_w
            ay0, ay1 = La.oy - La.half_h, La.oy + La.half_h
            bx0, bx1 = Lb.ox - Lb.half_w, Lb.ox + Lb.half_w
            by0, by1 = Lb.oy - Lb.half_h, Lb.oy + Lb.half_h
            ox = max(0.0, min(ax1, bx1) - max(ax0, bx0))
            oy = max(0.0, min(ay1, by1) - max(ay0, by0))
            area = ox * oy
            if area > 0:
                overlaps.append({"a": a, "b": b, "overlap_area": area})
    return overlaps
