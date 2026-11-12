# P4.3.1 — отчёт точечного устранения замечаний P4.4

**Ветка:** `cursor/p4-3-1-qa-hardening-666e` ← `cursor/p4-3-qa-heuristics-666e` @ `f073fce`  
**План:** [`P4_3_1_PLAN.md`](P4_3_1_PLAN.md) · аудит [`P4_4_AUDIT.md`](P4_4_AUDIT.md)  
**Объект:** КП-062215009-01

---

## 1. Изменённые файлы

| Файл | Суть |
|------|------|
| `eskd_cad/qa/p4/view_layout.py` | A3: `parse_builder_view_transforms`; A6: `window_overlap_report` + doc |
| `eskd_cad/qa/p4/datum_detect.py` | A1: `_is_rectangle_any_orient`; A2: consume box/letter/triangle |
| `eskd_cad/qa/p4/duplicate_lines.py` | A4: dedup HLR, length gate, exclusive consume; A5: micro stats |
| `eskd_cad/qa/p4/dim_map.py` | A7: честный evidence rim_od |
| `tests/test_p4_3_dim_map.py` | A3/A6 тесты |
| `tests/test_p4_3_1_hardening.py` | новые тесты A1–A7 |
| `P4_3_1_PLAN.md`, `P4_3_1_REPORT.md` | план/отчёт |

P0–P3 / calc / foundry geometry / export / golden — **не менялись**.

---

## 2. Статусы замечаний A1–A7

| ID | Статус | Что сделано |
|----|--------|-------------|
| **A1** | **FIXED** | Повёрнутый квадрат/прямоугольник → `other`, не `datum_triangle`. Тесты: AA square, 15°, rotated rect, triangle, perturbed, extra vertex; колесо А+Б full. |
| **A2** | **FIXED** | Резервирование box/letter/triangle; конкурирующие буквы → `excluded_other` ambiguous; несколько треугольников → partial ambiguous (без произвольного выбора). |
| **A3** | **FIXED** | `parse_builder_view_transforms` читает литералы `foundry/koleso_otlivka.py`; тест сверки + тест искусственного дрейфа. |
| **A4** | **FIXED** | Дедуп HLR-сегментов; ends+length; только эксклюзивный seg (`claim_count==1`); конкуренция → `ambiguous_same_geom`. DXF не чистится. |
| **A5** | **DOCUMENTED** | Микросегменты — артефакты HLR-тесселяции; в `summarize_duplicates` счётчик `micro_segment_groups_lt_0_05mm` + note; **без** фильтрации/удаления (нет инж. обоснования). |
| **A6** | **DOCUMENTED** (+ tests) | `window_overlap_report`; правило 0/1/many hits сохранено; виды не сдвигались. |
| **A7** | **FIXED** (wording) | rim_od evidence явно: AA section bbox width ≠ изолированный обод / dim↔edge; агрегат NOT_CHECKED. Feature-specific bbox — отдельный этап. |

---

## 3. Что осталось и почему

| Тема | Почему |
|------|--------|
| A5 микросегменты в PASS-evidence | Безопасное удаление/фильтр без обоснования запрещено ТЗ |
| A6 пересечение окон | Сдвиг видов = правка листа; mitigated NOT_CHECKED |
| A7 нет isolated rim bbox | Нет надёжного feature-solid в текущем OCP QA API |
| INP-009a / GEO-002b / dim↔edge | Инженерные gaps P4.1–P4.3; не scope P4.3.1 |
| `fully_verified=False` | Намеренно |

---

## 4. Добавленные тесты

- `tests/test_p4_3_1_hardening.py` — A1–A7 (classify, reservation, HLR consume, micro note, rim evidence, zero hits)
- `tests/test_p4_3_dim_map.py` — independent builder parse, artificial drift, window overlaps

---

## 5. Результаты полного тестирования

```text
PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py'
→ Ran 90 tests — OK

PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
→ checklist 10/10; DXF auditor OK
→ P4: PASS=27 FAIL=0 WARNING=4 NOT_CHECKED=3
→ fully_verified=False
→ LINE=206 DIMENSION=10 HATCH=2
```

---

## 6. Сравнение QA-статистики P4.3 → P4.3.1

| Метрика | P4.3 | P4.3.1 | Комментарий |
|---------|------|--------|-------------|
| PASS | 27 | 27 | без подгонки |
| FAIL | 0 | 0 | |
| WARNING | 4 | 4 | |
| NOT_CHECKED | 3 | 3 | INP-009a, GEO-002b, DRW-016 |
| fully_verified | False | False | |
| DRW-004 letters | А,Б | А,Б | full=2, excluded_cutting=4 |
| DRW-006 | 20 hlr_coincident | 20 hlr_coincident | после dedup+consume |
| DRW-016 aggregate | NOT_CHECKED | NOT_CHECKED | |

Статистика **не изменилась** — ожидаемо: исправления усиливают доказательства/устойчивость, не меняют вердикты на колесе.

---

## 7–9. Сохранность P0–P3 / golden / DXF-PDF

| Контроль | Факт |
|----------|------|
| TABLE6_BASE | 5.2 |
| C_HUB / H_BODY / L_PRINT / H_PRINT2 | 248 / 464 / 60 / 40 |
| ЛС | 12:14.4:16.8 |
| tol_volume metal∩core1 | 50000 |
| DXF LINE/DIM/HATCH | 206 / 10 / 2 |
| PDF primary | generated OK |
| Diff scope | только qa/p4 + tests + MD |

---

## 10. Остаточные ограничения и риски

1. Микросегменты HLR (~0.01 mm) остаются в evidence как `hlr_coincident` с явной статистикой A5.  
2. Окна видов пересекаются; неоднозначный mid → NOT_CHECKED (A6).  
3. `rim_od` PASS по section bbox width — честно ограничен (A7); association dim↔edge — будущее.  
4. Drift-тест зависит от стабильного текстового формата `ViewTransform(...)` в builder.

---

## Вердикт

P4.3.1 закрывает безопасно исправимые замечания P4.4 (A1–A4, A7 wording) и документирует A5/A6.  
Чертёж **не** объявляется полностью проверенным.
