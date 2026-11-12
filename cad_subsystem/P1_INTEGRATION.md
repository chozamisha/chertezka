# P1 — интеграция расчётов → CastingSpec → eskd_cad

## Цель

Подключить **существующие** таблицы и гейты к runtime-процессу формирования технологического чертежа.  
Формулы не переписывались, приближения не вводились, расчётная логика не перенесена в CAD-модуль построения видов.

## Схема (после P1)

```
CastingInputs (source + engineer)
        │
        ▼
  eskd_cad/calc/pipeline.py
    ├─ gost26645_table6.allowance_mm   → TABLE6_BASE
    ├─ ls_ratios_all.csv               → F_SLAG, F_SPRUE
    ├─ sterzhni_horiz_syroe.json       → L_PRINT_MAX; check L_PRINT
    ├─ riser_gates (qa_check)          → STOP при нарушении
    └─ формулы C_*/Y_* (как koleso_data)
        │
        ▼
  CastingSpec + provenance (source|calculated|engineer)
        │
        ▼
  registry.build_drawing(spec)  →  foundry (геометрия без изменений)
        │
   DXF / PDF
```

Golden `knowledge/calc/koleso_data.py` остаётся эталоном регрессии; generate вызывает **pipeline**, а не только чтение констант.

## Подключённые расчёты (вызываются в generate)

| Блок | Модуль / данные | Что вызывается в runtime | Результат в CastingSpec |
|------|-----------------|--------------------------|-------------------------|
| Припуски ГОСТ 26645 табл.6 | `calc/gost26645_table6.py` + `gost_26645_table6_full.json` | `allowance_mm(2.8,"Чистовая",11)` | `TABLE6_BASE=5.2` (provenance); принятые `N_*` — engineer |
| Прибыль | `calc/riser_gates.py` (= `qa_check.check_riser*`) | `check_riser`, `check_riser_neck`, `check_riser_core_scheme` | `D_RISER/D_NECK/H_RISER` после OK; иначе STOP |
| Литниковая | `knowledge/calc/ls_ratios_all.csv` | `get_ls_ratio("ICHX_academic_default")` + `areas_from_pit` | `F_PIT=12`, `F_SLAG=14.4`, `F_SPRUE=16.8` |
| Стержни (гориз. знак) | `sterzhni_horiz_syroe.json` | `horiz_print_l_max` / `check_horiz_print` | `L_PRINT_MAX=60`; `L_PRINT=60` ≤ max |
| Геометрия отливки | формулы как в `koleso_data` | `C_*`, `Y_*`, `H_BODY`, `Y_RISER_TOP` | совпадают с golden |

**Не объявлено подключённым (честно):**

| Блок | Статус | Почему |
|------|--------|--------|
| Вертикальный знак `H_PRINT2` | только engineer + provenance | JSON-таблицы нижних верт. знаков нет; есть markdown `sterzhni_raschet.md` — lookup не вызывается |
| τзал / G / δ (Дубицкий) | не вызывается | нет callable-модуля; в листе — текстовый расчёт; `F_PIT` задаётся инженером |
| Холодильники размеры | не в CastingSpec | не влияют на текущий DXF-контур |
| OCR / вход с чертежа детали | P3 | — |
| Смена алгоритмов видов/сечений | P2 | намеренно не трогали |

## Provenance (разделение данных)

Для каждого параметра в `CalcResult.provenance`:

- **source** — исходные данные детали / ТТ (`D_OUT`, материал, …)
- **calculated** — таблица / формула / гейт (`TABLE6_BASE`, `F_SLAG`, `C_HUB`, `L_PRINT_MAX`, …)
- **engineer** — ручной ввод / принятое (`N_*`, `D_RISER`, `F_PIT`, `L_PRINT`, `H_PRINT2`, …)

Поле `source` provenance: `формула` | `таблица` | `ручной ввод` | `нормативный документ / …`  
При generate пишется `out/KP-062215009-01_provenance.json`.

## Единицы и валидация

- Геометрия / припуски / прибыль / знаки: **mm**
- Площади ЛС: **cm²**
- Несовпадение единицы → `UnitError` (пересчёт не делается)
- Нет обязательного поля / пустой ключ CSV → `MissingInputError`
- Вне диапазона таблицы / гейта → `OutOfRangeError` / `CalcDataError`
- Нет строки табл.6 → ошибка, **без** подстановки «на глаз»

## Результаты тестов

Команда:

```bash
cd cad_subsystem
PYTHONPATH=. python3 -m unittest tests.test_p1_calc_integration tests.test_p0_parity -v
PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
```

| Проверка | Результат |
|----------|-----------|
| `allowance_mm(2.8, Чистовая, 11) == 5.2` | OK |
| ЛС ICHX 12 → 14.4 / 16.8 | OK |
| `horiz_print_l_max(115, 200) == 60` | OK |
| Pipeline ≡ golden `koleso_data` / GOLDEN | OK |
| DXF содержит ΣFп=12, 14.4, 16.8, 1:1.2:1.4 | OK |
| Нет F_PIT / неверный unit / row=99 | понятная ошибка |
| Табл.6 tolerance вне таблицы | STOP, без выдумки |
| D_RISER=200 | STOP (гейт прибыли) |
| L_PRINT=120 > l_max | STOP |
| L_PRINT=60 = l_max | OK |
| P0 parity (5 тестов) | OK |
| Generate → DXF/PDF + checklist 10/10 | OK |

### Сравнение с проверенными значениями колеса

| Параметр | Golden | Pipeline |
|----------|--------|----------|
| TABLE6_BASE | 5.2 (calc.md) | 5.2 |
| C_HUB / H_BODY | 248 / 464 | 248 / 464 |
| D_RISER / D_NECK / H_RISER | 300 / 240 / 300 | то же |
| L_PRINT / H_PRINT2 | 60 / 40 | то же |
| F_PIT : F_SLAG : F_SPRUE | 12 : 14.4 : 16.8 | то же |

## Предупреждения (не STOP)

При `N_BOT=5` и `N_FACE=5` при `TABLE6_BASE=5.2` pipeline выдаёт warning: принятый припуск меньше табличного. Так в листе расчёта (округление / низ формы); значения **не** подменяются на 5.2.

## Оставшиеся проблемы / следующий этап

1. JSON для **вертикальных** знаков (из `sterzhni_raschet.md` §2) — чтобы `H_PRINT2` проверялся таблицей, а не только ручным вводом.
2. Callable для τзал / массы формы — если появится модуль, подключить к назначению `F_PIT` (сейчас engineer).
3. Холодильники в CastingSpec / на чертеже.
4. P2: геометрия видов/сечений из 3D (OCP) — **не** начато; 2D-builders без изменений.
5. Строки CSV с диапазонами (`1.0-1.5`) пропускаются lookup’ом — однозначные numeric-only.

## Файлы

- `eskd_cad/calc/` — pipeline, provenance, table6, ls, cores, riser_gates, wheel_inputs
- `eskd_cad/knowledge/calc/ls_ratios_all.csv` — vendored
- `examples/generate_koleso_otlivka.py` — основной путь через pipeline
- `tests/test_p1_calc_integration.py`
