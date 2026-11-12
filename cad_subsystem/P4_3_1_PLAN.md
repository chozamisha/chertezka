# P4.3.1 — план точечного устранения замечаний P4.4

**База:** `cursor/p4-3-qa-heuristics-666e` @ `f073fce`  
**Аудит:** `P4_4_AUDIT.md` → `P4_3_ACCEPTED_WITH_LIMITATIONS`  
**Ветка:** `cursor/p4-3-1-qa-hardening-666e`

## Границы

Только `eskd_cad/qa/p4/*` + тесты + MD. Не трогать P0–P3, calc, OCP solids, tol_volume, export geometry.

## Задачи

| ID | Действие | Файлы | Статус-цель |
|----|----------|-------|-------------|
| A3 | Независимый drift: парсинг литералов `koleso_otlivka.py` ↔ `wheel_view_layouts` | `view_layout.py` (helper parse), `tests/test_p4_3_dim_map.py` / `test_p4_3_1_*.py` | FIXED |
| A1 | Rect с поворотом ≠ triangle; ambiguous → `other` | `datum_detect.py`, тесты | FIXED |
| A2 | Consume box/letter/triangle; неоднозначность без произвольного выбора | `datum_detect.py`, тесты | FIXED |
| A4 | Dedup HLR segs; consume; length check; competing → ambiguous | `duplicate_lines.py`, тесты | FIXED |
| A5 | Исследовать микросегменты; документировать; без произвольного фильтра | report + evidence note | DOCUMENTED |
| A6 | Документировать overlaps; тесты 0/1/many hits | `view_layout.py` doc, `dim_map` tests | DOCUMENTED (+ tests) |
| A7 | Честный evidence rim_od (AA section bbox width ≠ isolated rim) | `dim_map.py` | FIXED (wording) |

## Порядок

A3 → A1 → A2 → A4 → A5/A6/A7 → регрессия → `P4_3_1_REPORT.md`.
