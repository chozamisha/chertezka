# -*- coding: utf-8 -*-
"""
Мост system-python → OCP8 worker (subprocess).

Не импортирует OCP в системный интерпретатор — совместимо с ezdxf/shapely.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .view_types import ViewResult

_HERE = Path(__file__).resolve().parent
_WORKER = _HERE / "ocp_worker.py"


def python_ocp8() -> str:
    for cand in (
        os.environ.get("PYTHON_OCP8"),
        shutil.which("python-ocp8"),
        str(Path.home() / ".local/bin/python-ocp8"),
        str(Path.home() / ".local/cad/venv-ocp8/bin/python"),
    ):
        if cand and Path(cand).is_file():
            return cand
    raise FileNotFoundError(
        "python-ocp8 не найден (~/.local/cad/venv-ocp8). "
        "Геометрические операции P2 требуют OCP8 venv."
    )


def ocp_available() -> bool:
    try:
        python_ocp8()
        return _WORKER.is_file()
    except FileNotFoundError:
        return False


def run_ocp_job(payload: Dict[str, Any], *, timeout_s: float = 120.0) -> ViewResult:
    """Выполнить одну операцию worker'а и вернуть ViewResult."""
    proc = subprocess.run(
        [python_ocp8(), str(_WORKER)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"ocp_worker failed ({proc.returncode}): {err}")
    data = json.loads(proc.stdout)
    if "error" in data:
        raise RuntimeError(f"ocp_worker error: {data['error']}")
    return ViewResult.from_dict(data)


def project_hlr(solid: Dict[str, Any], **kwargs: Any) -> ViewResult:
    payload = {"solid": solid, "operation": "hlr_projection", **kwargs}
    return run_ocp_job(payload)


def section_plane(solid: Dict[str, Any], **kwargs: Any) -> ViewResult:
    payload = {"solid": solid, "operation": "plane_section", **kwargs}
    return run_ocp_job(payload)


def run_intersection_check(payload: Dict[str, Any], *, timeout_s: float = 180.0) -> ViewResult:
    """payload уже содержит operation=intersection_check и solids/pairs."""
    if payload.get("operation") != "intersection_check":
        payload = {**payload, "operation": "intersection_check"}
    return run_ocp_job(payload, timeout_s=timeout_s)
