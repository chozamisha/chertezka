# P4.5.1 — план: вертикальные стержневые знаки ГОСТ 3212-92

**База:** `cursor/p4-5-data-audit-666e` ← `p4-3-1` @ `386695a`  
**Ветка:** `cursor/p4-5-1-vert-signs-666e`

## Принцип

Check-only: **не** менять `H_PRINT2`, геометрию Ст.1/Ст.2, horiz JSON/loader.

## Параметры Ст.2 (инвентаризация)

| Параметр | Источник | Значение на колесе |
|----------|----------|-------------------|
| D | `Core2Params.diameter_mm` = `CastingSpec.c_bore` | 132 |
| L | `Core2Params.height_mm` = `CastingSpec.h_body` (рабочая высота отверстия) | 464 |
| H_PRINT2 | engineer `CorePrintInputs.h_print2` / CastingSpec | 40 |
| Верхний знак | схема A — отсутствует | n/a → правило 2.3.3 NOT_CHECKED |

## Таблица

Первоисточник: ГОСТ 3212-92 PDF с.7–8 (табл.7, п.2.3 / 2.3.3).  
Рабочая оцифровка: Михальцов 5.2 (ссылается на ГОСТ) + `sterzhni_raschet.md` §2, сверенные выборочно с PDF.  
Ячейки вне уверенной сверки → `unavailable` / не включаются как numeric.

Ожидаемый lookup колеса: D∈(100;160], L∈(400;630] → **unavailable** → INP-008 **NOT_CHECKED** (не искусственный PASS).

## Файлы

- `knowledge/calc/sterzhni_vert_lower.json` + краткий MD
- `calc/core_prints.py` — `vert_print_h_max`, `check_vert_print_lower`
- `calc/pipeline.py` — provenance `H_PRINT2_MAX` / check meta
- `qa/p4/inputs.py` — INP-008 evidence
- `tests/test_p4_5_1_vert_signs.py`
