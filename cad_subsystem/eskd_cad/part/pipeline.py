# -*- coding: utf-8 -*-
"""Вход: DXF/JSON детали → PartSpec → решения → CastingDraft → лист отливки."""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional

from . import decisions as decisions_mod
from .part_spec import CastingDraft, PartSpec
from .profiles import korpus

REPO = Path(__file__).resolve().parents[3]
CAD_WORK = REPO / "cad_work"


def load_part_json(path: str | Path) -> PartSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PartSpec.from_dict(data, source_path=str(path))


def part_from_input(path: str | Path, *, profile: str = "auto") -> PartSpec:
    path = Path(path)
    if path.suffix.lower() == ".json":
        part = load_part_json(path)
    elif path.suffix.lower() == ".dxf":
        if profile not in ("auto", "korpus"):
            raise ValueError(f"Неизвестный profile={profile!r}; доступны auto|korpus")
        part = korpus.part_from_dxf(str(path))
    else:
        raise ValueError(f"Поддержаны .dxf и PartSpec .json, получено: {path.suffix}")

    if profile == "korpus" or part.profile == "korpus":
        return part
    if profile == "auto" and part.profile == "korpus":
        return part
    raise ValueError(
        f"Профиль {part.profile!r} не поддержан. Сейчас работает только korpus "
        "(полое тело вращения с двумя фланцами). Передайте PartSpec JSON с profile=korpus."
    )


def build_casting(
    part: PartSpec,
    *,
    decisions_path: str | Path | None = None,
    confirm_all: bool = False,
) -> CastingDraft:
    overrides = decisions_mod.load_overrides(decisions_path) if decisions_path else None
    resolved = decisions_mod.resolve(part, overrides, confirm_all=confirm_all)
    if part.profile != "korpus":
        raise ValueError(f"Нет to_casting для profile={part.profile!r}")
    draft = korpus.build_casting(part, resolved)
    open_qs = decisions_mod.unconfirmed(resolved)
    if open_qs:
        draft.questions = list(draft.questions) + [
            "Неподтверждённые решения (лист будет черновиком): " + ", ".join(open_qs)
        ]
    draft.params["_decisions"] = decisions_mod.dump(resolved)
    draft.params["_unconfirmed"] = open_qs
    return draft


def write_json(obj: Dict[str, Any] | PartSpec | CastingDraft, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = obj.as_dict() if hasattr(obj, "as_dict") else obj
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _params_module(params: Dict[str, Any]) -> types.SimpleNamespace:
    clean = {k: v for k, v in params.items() if not k.startswith("_")}
    return types.SimpleNamespace(**clean)


def _load_cad_work_draw_otl():
    """Импорт cad_work/draw_otl без конфликтов с drawings/cad.py."""
    for name in ("draw_otl", "cad", "common", "qa_check", "qa_extra", "korpus_data"):
        mod = sys.modules.get(name)
        if mod is not None and "drawings" in str(getattr(mod, "__file__", "")):
            del sys.modules[name]
    if str(CAD_WORK) not in sys.path:
        sys.path.insert(0, str(CAD_WORK))
    import draw_otl  # type: ignore

    return importlib.reload(draw_otl)


def render_korpus_otlivka(
    draft: CastingDraft,
    *,
    out_dir: Path,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Лист отливки через cad_work/draw_otl.build.

    Без force PDF пишется только если qa_check+qa_extra чисты и все решения
    подтверждены. Иначе — PNG черновика и список замечаний.
    """
    if draft.profile != "korpus":
        raise ValueError("render_korpus_otlivka только для profile=korpus")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    draw_otl = _load_cad_work_draw_otl()
    D = _params_module(draft.params)
    sh = draw_otl.build(D)
    issues = draw_otl.check(sh, D)

    stem = draft.designation or "otlivka"
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    dxf = out_dir / f"{stem}.dxf"
    unconfirmed = list(draft.params.get("_unconfirmed") or [])
    clean = not issues and not unconfirmed

    sh.render(str(png), dpi=180)
    sh.to_dxf(str(dxf))
    result = {
        "png": str(png),
        "dxf": str(dxf),
        "qa_issues": issues,
        "unconfirmed": unconfirmed,
        "final": False,
    }
    if clean or force:
        sh.render(str(png), pdf=str(pdf), dpi=180)
        result["pdf"] = str(pdf)
        result["final"] = clean and not force
        if force and (issues or unconfirmed):
            result["forced"] = True
    return result


def run(
    input_path: str | Path,
    *,
    out_dir: str | Path,
    profile: str = "auto",
    render: bool = False,
    decisions_path: str | Path | None = None,
    confirm_all: bool = False,
    force_render: bool = False,
) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    part = part_from_input(input_path, profile=profile)
    errors, warnings = korpus.validate(part) if part.profile == "korpus" else ([], [])
    part.warnings = list(dict.fromkeys(list(part.warnings) + warnings))
    write_json(part, out / "part_spec.json")

    result: Dict[str, Any] = {
        "part_spec": str(out / "part_spec.json"),
        "questions": list(part.questions),
        "warnings": list(part.warnings),
        "errors": errors,
        "designation": None,
    }
    if errors:
        result["status"] = "part_invalid"
        return result

    draft = build_casting(part, decisions_path=decisions_path, confirm_all=confirm_all)
    write_json(draft, out / "casting_draft.json")
    write_json(draft.params.get("_decisions") or {}, out / "decisions.json")

    result.update({
        "casting_draft": str(out / "casting_draft.json"),
        "decisions": str(out / "decisions.json"),
        "questions": draft.questions,
        "warnings": list(dict.fromkeys(list(part.warnings) + draft.warnings)),
        "designation": draft.designation,
        "unconfirmed": draft.params.get("_unconfirmed") or [],
        "status": "draft" if draft.params.get("_unconfirmed") else "ready",
    })

    if render:
        rendered = render_korpus_otlivka(draft, out_dir=out, force=force_render)
        result.update(rendered)
        if rendered.get("final"):
            result["status"] = "final"
        elif rendered.get("qa_issues"):
            result["status"] = "qa_failed"
    return result
