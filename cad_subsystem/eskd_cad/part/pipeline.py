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
from .profiles import koleso, korpus

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
            raise ValueError(
                f"Из DXF сейчас читается только profile=korpus; для koleso передайте PartSpec JSON "
                f"(получено profile={profile!r})"
            )
        part = korpus.part_from_dxf(str(path))
    else:
        raise ValueError(f"Поддержаны .dxf и PartSpec .json, получено: {path.suffix}")

    if profile in ("korpus", "koleso"):
        if part.profile != profile:
            raise ValueError(f"Файл имеет profile={part.profile!r}, запрошен {profile!r}")
        return part
    if profile == "auto":
        if part.profile in ("korpus", "koleso"):
            return part
    raise ValueError(
        f"Профиль {part.profile!r} не поддержан. Доступны korpus и koleso."
    )


def _validate(part: PartSpec):
    if part.profile == "korpus":
        return korpus.validate(part)
    if part.profile == "koleso":
        return koleso.validate(part)
    return [f"нет validate для {part.profile!r}"], []


def build_casting(
    part: PartSpec,
    *,
    decisions_path: str | Path | None = None,
    confirm_all: bool = False,
) -> CastingDraft:
    overrides = decisions_mod.load_overrides(decisions_path) if decisions_path else None
    resolved = decisions_mod.resolve(part, overrides, confirm_all=confirm_all)
    if part.profile == "korpus":
        draft = korpus.build_casting(part, resolved)
    elif part.profile == "koleso":
        draft = koleso.build_casting(part, resolved)
    else:
        raise ValueError(f"Нет to_casting для profile={part.profile!r}")
    open_qs = decisions_mod.unconfirmed(resolved)
    if open_qs:
        draft.questions = list(draft.questions) + [
            "Неподтверждённые решения (лист будет черновиком): " + ", ".join(open_qs)
        ]
    draft.params["_decisions"] = decisions_mod.dump(resolved)
    draft.params["_unconfirmed"] = open_qs
    return draft


def _jsonable(obj: Any) -> Any:
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict, is_dataclass
        if is_dataclass(obj):
            return asdict(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items() if not str(k).startswith("_raw")}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def write_json(obj: Dict[str, Any] | PartSpec | CastingDraft, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, CastingDraft):
        data = {
            "profile": obj.profile,
            "designation": obj.designation,
            "params": {k: _jsonable(v) for k, v in obj.params.items()
                       if k not in ("SPEC", "CALC")},
            "provenance": obj.provenance,
            "warnings": obj.warnings,
            "questions": obj.questions,
        }
        # краткие поля spec для чтения человеком
        spec = obj.params.get("SPEC")
        if spec is not None and hasattr(spec, "key_params"):
            data["params"]["spec_key"] = spec.key_params()
    elif hasattr(obj, "as_dict"):
        data = obj.as_dict()
    else:
        data = _jsonable(obj)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _params_module(params: Dict[str, Any]) -> types.SimpleNamespace:
    clean = {k: v for k, v in params.items() if not k.startswith("_") and k not in ("SPEC", "CALC")}
    return types.SimpleNamespace(**clean)


def _load_cad_work_draw_otl():
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


def render_koleso_otlivka(
    draft: CastingDraft,
    *,
    out_dir: Path,
    force: bool = False,
    use_ocp: bool | None = False,
) -> Dict[str, Any]:
    """Лист отливки колеса через eskd_cad.foundry (DrawingDocument → DXF/PDF)."""
    if draft.profile != "koleso":
        raise ValueError("render_koleso_otlivka только для profile=koleso")
    from eskd_cad import foundry  # noqa: F401
    from eskd_cad.export import export_dxf, export_pdf
    from eskd_cad.foundry.koleso_otlivka import build_koleso_otlivka
    from eskd_cad.qa.geometry_check import check_document

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = draft.params["SPEC"]
    doc = build_koleso_otlivka(spec, use_ocp=bool(use_ocp))
    issues = [str(x) for x in check_document(doc)]
    unconfirmed = list(draft.params.get("_unconfirmed") or [])
    stem = draft.designation or "otlivka"
    dxf = out_dir / f"{stem}_Otlivka.dxf"
    pdf = out_dir / f"{stem}_Otlivka.pdf"
    png = out_dir / f"{stem}_Otlivka.png"
    export_dxf(doc, dxf)
    result = {
        "dxf": str(dxf),
        "qa_issues": issues,
        "unconfirmed": unconfirmed,
        "final": False,
        "renderer": "eskd_cad.foundry.koleso_otlivka",
        "use_ocp": bool(use_ocp),
    }
    clean = not issues and not unconfirmed
    if clean or force:
        export_pdf(doc, pdf)
        result["pdf"] = str(pdf)
        try:
            import fitz
            page = fitz.open(pdf)[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72), alpha=False)
            pix.save(str(png))
            result["png"] = str(png)
        except Exception as exc:  # pragma: no cover
            result["png_error"] = str(exc)
        result["final"] = clean and not force
        if force and (issues or unconfirmed):
            result["forced"] = True
    return result


def render_otlivka(draft: CastingDraft, *, out_dir: Path, force: bool = False,
                   use_ocp: bool | None = False) -> Dict[str, Any]:
    if draft.profile == "korpus":
        return render_korpus_otlivka(draft, out_dir=out_dir, force=force)
    if draft.profile == "koleso":
        return render_koleso_otlivka(draft, out_dir=out_dir, force=force, use_ocp=use_ocp)
    raise ValueError(f"Нет рендера для profile={draft.profile!r}")


def run(
    input_path: str | Path,
    *,
    out_dir: str | Path,
    profile: str = "auto",
    render: bool = False,
    decisions_path: str | Path | None = None,
    confirm_all: bool = False,
    force_render: bool = False,
    use_ocp: bool | None = False,
) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    part = part_from_input(input_path, profile=profile)
    errors, warnings = _validate(part)
    part.warnings = list(dict.fromkeys(list(part.warnings) + warnings))
    write_json(part, out / "part_spec.json")

    result: Dict[str, Any] = {
        "part_spec": str(out / "part_spec.json"),
        "questions": list(part.questions),
        "warnings": list(part.warnings),
        "errors": errors,
        "designation": None,
        "profile": part.profile,
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
        rendered = render_otlivka(draft, out_dir=out, force=force_render, use_ocp=use_ocp)
        result.update(rendered)
        if rendered.get("final"):
            result["status"] = "final"
        elif rendered.get("qa_issues"):
            result["status"] = "qa_failed"
    return result
