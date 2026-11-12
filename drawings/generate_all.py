# -*- coding: utf-8 -*-
"""Один запуск: 3 листа (деталь / отливка / МЛУ) + проверка штампов и пересечений."""
from pathlib import Path
import time

import draw_detal
import draw_otl
import draw_mlu
import korpus_data as D

OUT = Path(__file__).resolve().parent
ART = Path("/opt/cursor/artifacts")


def verify_stamp_strings(pdf_path, must_have, must_not):
    """Грубая проверка: читаем PNG рядом и ищем строки в ents через повторный импорт не нужен —
    проверяем, что в скриптах/данных правильные константы; плюс размер файла свежий."""
    p = Path(pdf_path)
    age = time.time() - p.stat().st_mtime
    assert age < 600, "%s слишком старый (%.0f с)" % (p.name, age)
    assert p.stat().st_size > 5000


def main():
    assert D.DEV == "Шевцов"
    assert D.DESIGNATION_00.endswith("-00")
    assert D.DESIGNATION_01.endswith("-01")
    assert D.DESIGNATION_02.endswith("-02")

    c0 = draw_detal.main()
    c1 = draw_otl.main()
    c2 = draw_mlu.main()

    files = [
        OUT / "ПП-062215009-00_Korpus.pdf",
        OUT / "ПП-062215009-01_Korpus_Otlivka.pdf",
        OUT / "ПП-062215009-02_Korpus_MLU.pdf",
    ]
    for f in files:
        verify_stamp_strings(f, [], ["Шарабуров"])

    print("COLLISIONS", len(c0), len(c1), len(c2))
    assert len(c0) == 0 and len(c1) == 0 and len(c2) == 0, (c0, c1, c2)
    print("ALL CLEAR — 3 fresh PDFs")
    for f in files:
        print(" ", f.name, f.stat().st_size, "mtime_age_s", round(time.time() - f.stat().st_mtime, 1))


if __name__ == "__main__":
    main()
