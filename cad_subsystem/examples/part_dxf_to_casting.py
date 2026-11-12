# -*- coding: utf-8 -*-
"""
CLI: чертёж детали (DXF или PartSpec JSON) → PartSpec + решения + лист отливки.

  cd cad_subsystem
  python3 -m examples.part_dxf_to_casting \\
      ../drawings/ПП-062215009-00_Korpus.dxf \\
      --out out/part_to_casting --render --confirm-all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eskd_cad.part.pipeline import run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Деталь DXF/JSON → отливка (профиль korpus)")
    p.add_argument("input", help="DXF детали или PartSpec JSON")
    p.add_argument("--out", default="out/part_to_casting", help="каталог артефактов")
    p.add_argument("--profile", default="auto", choices=["auto", "korpus", "koleso"])
    p.add_argument("--decisions", help="JSON с переопределениями технологических решений")
    p.add_argument("--render", action="store_true",
                   help="собрать лист (korpus→cad_work, koleso→eskd_cad.foundry)")
    p.add_argument(
        "--confirm-all",
        action="store_true",
        help="считать все решения подтверждёнными (для эталона и тестов)",
    )
    p.add_argument(
        "--force-render",
        action="store_true",
        help="писать PDF даже при замечаниях QA / неподтверждённых решениях",
    )
    p.add_argument("--ocp", action="store_true", help="для koleso: контуры через OCP8, если есть venv")
    args = p.parse_args(argv)

    result = run(
        args.input,
        out_dir=args.out,
        profile=args.profile,
        render=args.render,
        decisions_path=args.decisions,
        confirm_all=args.confirm_all,
        force_render=args.force_render,
        use_ocp=args.ocp,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "qa_issues"},
                     ensure_ascii=False, indent=2))
    if result.get("qa_issues"):
        print("--- qa ---")
        for issue in result["qa_issues"]:
            print("*", issue)
    print("--- questions ---")
    for q in result.get("questions") or []:
        print("*", q)
    if result.get("errors"):
        print("--- errors ---")
        for e in result["errors"]:
            print("*", e)
        return 2
    if result.get("status") == "qa_failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
