# P4.5.1 — отчёт: вертикальные стержневые знаки ГОСТ 3212-92

**Ветка:** `cursor/p4-5-1-vert-signs-666e`  
**База:** `cursor/p4-5-data-audit-666e` ← `p4-3-1` @ `386695a`  
**Принцип:** check-only — `H_PRINT2=40` и геометрия Ст.1/Ст.2 не менялись.

---

## 1. Проверенные страницы и положения ГОСТ

| Положение | PDF | Содержание |
|-----------|-----|------------|
| п.2.3 | С.7 | Вертикальные знаки; табл.7 |
| Таблица 7 | С.7 | Высота нижнего вертикального знака, мм, **не более**; входы D или (a+b)/2 и L (высота рабочей части) |
| п.2.3.3 | С.8 | Высота верхнего знака ≥ 0,5 высоты нижнего |
| п.2.4.1 | С.8 | +50 % нижнего при отсутствии верхнего — **не** автоприменяется в P4.5.1 |

Внешний пакет: `/tmp/eskd_agent_pack/knowledge/sources/files/GOST_3212-92.pdf` (не в git).

---

## 2. Сверка Markdown с PDF

- OCR PDF С.7 шумный; полная поклеточная OCR-сверка не завершена.
- Рабочая оцифровка: **Михальцов табл.5.2** (цитирует ГОСТ 3212) + `sterzhni_raschet.md` §2, выборочно согласованные с читаемыми фрагментами PDF.
- Приоритет: непроверенные/спорные ячейки → `verified=false` или `unavailable`; в runtime числовой `h_max` только при `kind=max` **и** `verified=true`.
- Символ «—» → `kind=unavailable` (число не возвращается).
- Интерполяция запрещена.

---

## 3. Перенесённые verified numeric ячейки (40)

См. `eskd_cad/knowledge/calc/sterzhni_vert_lower.json`. Примеры:

| row D | col L | value | unit | table | page |
|-------|-------|-------|------|-------|------|
| 100-160 | 250-400 | 50 | mm | 7 | С.7 |
| 250-400 | 400-630 | 60 | mm | 7 | С.7 |
| 63-100 | 400-630 | 80 | mm | 7 | С.7 |
| … | … | … | mm | 7 | С.7 |

Полный список — все ячейки с `verified=true` и `kind=max` в JSON (40 шт.).

---

## 4. Непроверенные / недоступные ячейки

| Категория | Кол-во | Политика |
|-----------|--------|----------|
| `verified=false` (OCR ambiguous, в основном ряд 40-63) | 4 numeric + часть unavailable | `status=unverified` → NOT_CHECKED |
| `unavailable` («—» / MD empty / не нормировано) | 28 | `status=unavailable` → NOT_CHECKED |
| Столбцы L>1000 из PDF | не включены | out of scope этой версии |

**Ячейка колеса:** D∈100-160 × L∈400-630 → `unavailable` (подтверждено Михальцов/MD).

---

## 5. Параметры D и L Ст.2

| Параметр | Значение | Источник provenance |
|----------|----------|---------------------|
| D | 132 mm | `CastingSpec.c_bore` = `Core2Params.diameter_mm` (не сечение Ст.1) |
| L | 464 mm | `CastingSpec.h_body` = `Core2Params.height_mm` — **рабочая высота** отверстия Ст.2, не высота знака |
| H_PRINT2 | 40 mm | engineer `CorePrintInputs.h_print2` (kind=engineer) |
| Верхний знак | отсутствует | схема A → п.2.3.3 NOT_CHECKED |

Не путать с `CORE_SECTION`/`CORE_LENGTH` Ст.1 (гориз. знаки).

---

## 6. Изменённые файлы

| Файл | Роль |
|------|------|
| `knowledge/calc/sterzhni_vert_lower.json` | табл.7 + upper_sign_rule |
| `knowledge/calc/STERZHNI_VERT_README.md` | краткая документация |
| `calc/core_prints.py` | `vert_print_h_max`, `check_vert_print_lower/upper` |
| `calc/pipeline.py` | check-only + provenance CORE2_*/H_PRINT2_MAX |
| `calc/inputs.py`, `wheel_inputs.py` | комментарии provenance |
| `qa/p4/inputs.py` | INP-008 evidence из `vert_print_check` |
| `tests/test_p4_5_1_vert_signs.py` | unit + integration |
| `P4_5_1_PLAN.md`, `P4_5_1_REPORT.md` | план/отчёт |

**Не менялись:** OCP solids/Boolean, DXF/PDF builders, гориз. JSON/loader, формулы H_PRINT2, геометрия Ст.1/Ст.2.

---

## 7. Новые функции и точки подключения

1. `load_vert_lower()` / `vert_print_h_max(D, L)` → `VertPrintLookup`  
2. `check_vert_print_lower(H_PRINT2, D, L)` → PASS / WARNING / NOT_CHECKED  
3. `check_vert_print_upper(...)` → п.2.3.3  
4. `build_casting_from_inputs` пишет `vert_print_check`, provenance  
5. `run_input_checks` INP-008 читает `calc.vert_print_check`

---

## 8. Статусы QA до и после

| | До (P4.5 audit) | После P4.5.1 |
|--|-----------------|--------------|
| PASS | 27 | 27 |
| FAIL | 0 | 0 |
| WARNING | 4 | **3** |
| NOT_CHECKED | 3 | **4** |
| fully_verified | False | False |

INP-008: WARNING («JSON не подключена») → **NOT_CHECKED** (ячейка табл.7 «—» для D=132, L=464). Искусственный PASS не выставлялся.

---

## 9. Результаты тестирования

```
PYTHONPATH=. python3 -m unittest discover -s tests
→ Ran 109 tests … OK
```

В т.ч. 19 тестов `test_p4_5_1_vert_signs`: verified cells, границы D/L, unavailable/unverified, H_PRINT2 ≶ h_max, missing inputs, upper 0.5, horiz unchanged, pipeline/INP-008.

---

## 10. Регрессия generate_koleso_otlivka

| Контроль | База | Факт |
|----------|------|------|
| TABLE6_BASE | 5.2 | 5.2 |
| C_HUB | 248 | 248 |
| H_BODY | 464 | 464 |
| L_PRINT | 60 | 60 |
| H_PRINT2 | 40 | 40 |
| ЛС | 12:14.4:16.8 | 12:14.4:16.8 |
| tol_volume metal∩core1 | 50000 | 50000 (не трогали) |
| DXF LINE / DIMENSION / HATCH | 206 / 10 / 2 | 206 / 10 / 2 |
| PDF | OK | OK |
| Ст.1 / Ст.2 геометрия | — | без изменений |
| Горизонт. знаки INP-006 | PASS | PASS |

---

## 11. Остаточные ограничения

1. Полная OCR-сверка всех ячеек PDF табл.7 не завершена; ряд 40–63 и часть 400–630×коротких L — unverified/unavailable.  
2. Столбцы L>1000 не оцифрованы.  
3. п.2.4.1 (+50 % без верхнего знака) не применяется автоматически.  
4. Для колеса INP-008 остаётся **NOT_CHECKED** из‑за ячейки «—» — корректный нормативный исход, не дефект pipeline.  
5. PASS по табл.7 возможен только при verified ячейке и выполнимом `H_PRINT2 ≤ h_max`.

---

## Вердикт

P4.5.1 выполнен безопасно: таблица вендорена с provenance, lookup без интерполяции, gate check-only, INP-008 с evidence, геометрия и гориз. знаки неизменны. Нормативный PASS для колеса **не** форсирован.
