# -*- coding: utf-8 -*-
"""Мост из системного python3 (cad.py) к OCP8 через python-ocp8."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Sequence, Tuple

Point = Tuple[float, float]

_HERE = Path(__file__).resolve().parent
_OFFSET_SCRIPT = _HERE / "occ_offset.py"


def _python_ocp8() -> str:
    for cand in (
        os.environ.get("PYTHON_OCP8"),
        shutil.which("python-ocp8"),
        str(Path.home() / ".local/bin/python-ocp8"),
        str(Path.home() / ".local/cad/venv-ocp8/bin/python"),
    ):
        if cand and Path(cand).exists():
            return cand
    raise FileNotFoundError(
        "python-ocp8 not found; install OCP8 venv at ~/.local/cad/venv-ocp8"
    )


def offset_closed_polyline(points: Sequence[Point], amount: float) -> List[Point]:
    """Замкнутый параллельный контур через OpenCascade (OCP 8)."""
    payload = json.dumps(
        {"points": [[float(x), float(y)] for x, y in points], "amount": float(amount)}
    )
    proc = subprocess.run(
        [_python_ocp8(), str(_OFFSET_SCRIPT)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"occ offset failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout}"
        )
    data = json.loads(proc.stdout)
    return [(float(x), float(y)) for x, y in data["points"]]


def engine_paths() -> dict:
    home = Path.home()
    return {
        "python_ocp8": _python_ocp8(),
        "python_cq": str(
            shutil.which("python-cq")
            or home / ".local/cad/venv-cq/bin/python"
        ),
        "freecadcmd": str(
            shutil.which("freecadcmd")
            or home / ".local/cad/freecad/squashfs-root/usr/bin/freecadcmd"
        ),
        "freecad_appimage": str(home / ".local/cad/freecad/FreeCAD.AppImage"),
        "autocad": None,
    }
