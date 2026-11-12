# -*- coding: utf-8 -*-
"""Вход: DXF/JSON детали → PartSpec → CastingDraft (+ опциональный рендер Корпуса)."""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .part_spec import CastingDraft, PartSpec
from .profiles import korpus


def load_part_json(path: str | Path) -> PartSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    readings = data.get("readings") or []
    from .part_spec import DimensionReading

    return PartSpec(
        part_id=data["part_id"],
        designation=data.get("designation", ""),
        name=list(data.get("name") or []),
        material=list(data.get("material") or []),
        mass_kg=data.get("mass_kg"),
        scale=data.get("scale"),
        profile=data.get("profile", "generic"),
        dimensions=dict(data.get("dimensions") or {}),
        readings=[DimensionReading(**r) for r in readings],
        questions=list(data.get("questions") or []),
        process_hints=dict(data.get("process_hints") or {}),
        source_path=data.get("source_path", str(path)),
    )


def part_from_input(
    path: str | Path,
    *,
    profile: str = "auto",
    allow_golden_fill: bool = True,
) -> PartSpec:
    path = Path(path)
    if path.suffix.lower() == ".json":
        return load_part_json(path)
    if path.suffix.lower() != ".dxf":
        raise ValueError(f"Поддержаны .dxf и PartSpec .json, получено: {path.suffix}")

    # авто-профиль по обозначению / эвристике (MVP: только korpus)
    if profile not in ("auto", "korpus"):
        raise ValueError(f"Неизвестный profile={profile!r}; доступны auto|korpus")

    part = korpus.part_from_dxf(str(path), allow_golden_fill=allow_golden_fill)
    if profile == "korpus":
        return part
    if part.designation.startswith("ПП-062215009") or part.profile == "korpus":
        return part
    raise ValueError(
        "Не удалось выбрать профиль. Сейчас реализован только korpus "
        "(ПП-062215009 или --profile korpus). Передайте PartSpec JSON."
    )


def build_casting(part: PartSpec, **kwargs: Any) -> CastingDraft:
    if part.profile == "korpus":
        return korpus.build_casting(part, **kwargs)
    raise ValueError(f"Нет to_casting для profile={part.profile!r}")


def write_json(obj: Dict[str, Any] | PartSpec | CastingDraft, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.as_dict() if hasattr(obj, "as_dict") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def inject_korpus_module(params: Dict[str, Any]) -> types.ModuleType:
    """Подменить/создать модуль korpus_data для drawings/draw_otl.py."""
    mod = types.ModuleType("korpus_data")
    for k, v in params.items():
        setattr(mod, k, v)

    # casting_mass_kg как в эталоне
    def casting_mass_kg() -> float:
        return float(params.get("MASS_CAST_CALC", params.get("MASS_CAST", 0.0)))

    mod.casting_mass_kg = casting_mass_kg  # type: ignore[attr-defined]
    sys.modules["korpus_data"] = mod
    return mod


def render_korpus_otlivka(
    draft: CastingDraft,
    *,
    drawings_dir: Optional[Path] = None,
    out_dir: Optional[Path] = None,
) -> Tuple[Path, Path, Path]:
    """
    Сгенерировать лист отливки через существующий drawings/draw_otl.py.

    Возвращает пути (png, pdf, dxf).
    """
    if draft.profile != "korpus":
        raise ValueError("render_korpus_otlivka только для profile=korpus")

    # pipeline.py → part → eskd_cad → cad_subsystem → repo root
    root = Path(__file__).resolve().parents[3]
    drawings_dir = drawings_dir or (root / "drawings")
    out_dir = out_dir or (root / "cad_subsystem" / "out" / "part_to_casting")
    out_dir.mkdir(parents=True, exist_ok=True)

    inject_korpus_module(draft.params)

    # drawings/ imports cad.py and korpus_data from its own directory
    sys.path.insert(0, str(drawings_dir))
    try:
        import importlib

        # Force reload of draw_otl against injected korpus_data
        if "korpus_data" in sys.modules:
            pass  # already injected
        if "draw_otl" in sys.modules:
            del sys.modules["draw_otl"]
        if "cad" in sys.modules:
            # keep cad if already loaded from drawings
            pass

        import draw_otl  # type: ignore

        importlib.reload(draw_otl)
        # Point outputs into out_dir
        draw_otl.OUT = out_dir
        draw_otl.main()
    finally:
        if sys.path and sys.path[0] == str(drawings_dir):
            sys.path.pop(0)

    stem = "ПП-062215009-01_Korpus_Otlivka"
    return out_dir / f"{stem}.png", out_dir / f"{stem}.pdf", out_dir / f"{stem}.dxf"


def run(
    input_path: str | Path,
    *,
    out_dir: str | Path,
    profile: str = "auto",
    render: bool = False,
    allow_golden_fill: bool = True,
) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    part = part_from_input(input_path, profile=profile, allow_golden_fill=allow_golden_fill)
    draft = build_casting(part)

    part_path = out / "part_spec.json"
    draft_path = out / "casting_draft.json"
    write_json(part, part_path)
    write_json(draft, draft_path)

    result: Dict[str, Any] = {
        "part_spec": str(part_path),
        "casting_draft": str(draft_path),
        "questions": draft.questions,
        "warnings": draft.warnings,
        "designation": draft.designation,
    }

    if render:
        png, pdf, dxf = render_korpus_otlivka(draft, out_dir=out)
        result.update({"png": str(png), "pdf": str(pdf), "dxf": str(dxf)})

    return result
