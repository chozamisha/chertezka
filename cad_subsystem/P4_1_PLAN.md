# P4.1 — план корректировки инженерного контроля качества

**База:** `P4_AUDIT.md` + отчёт `out/KP-062215009-01_P4_quality.*`  
**Ветка (после согласования):** `cursor/p4-1-quality-hardening-666e` ← `cursor/p4-quality-control-666e`  
**Статус:** согласован и реализован — см. [`P4_1_REPORT.md`](P4_1_REPORT.md).

---

## Ограничения (жёсткие)

| Нельзя | Почему |
|--------|--------|
| Переписывать P1 / P2 / P3 / ядро P4 | ТЗ P4.1 |
| Менять расчётные формулы, `N_*`, `TABLE6_BASE`, `H_PRINT2`, площади ЛС | без отдельного подтверждения |
| Менять `tol_volume` в `intersection_job` «на глаз» | задача 3 |
| Удалять геометрию / чистить HLR ради DRW-006 | задача 2 |
| Ставить PASS DRW-016 только по тексту = CastingSpec | задача 5 / аудит |
| Объявлять `fully_verified=True` при оставшихся NOT_CHECKED | ТЗ |

**Можно:** уточнять **логику отчёта P4** (`qa/p4/*`), добавлять диагностику, тесты, `P4_1_*.md`.  
P3 `intersection_job` / `add_datum` / pipeline сравнения `N_* < base` — **читать и использовать**, не переписывать формулы.

---

## Что уже работает (не дублировать)

- Статусы + `fully_verified = ¬FAIL ∧ ¬NOT_CHECKED` (`status.py`)
- INP-001…008, GEO-001/003…006, DRW-001…003/005/007…015
- Pipeline warning `N_* < TABLE6_BASE` (направление сравнения **не трогаем**)
- OCP intersection check с парами expect/tol (`assembly_wheel.intersection_job` + `ocp_worker`)
- `add_datum`: треугольник + полка + рамка + буква (`annotations/datums.py`)
- GEO-005 bbox А-А ≈ C_OUT; DRW-005 — текстовое наличие размеров

P4.1 усиливает **отчётность и точность статусов**, а не заменяет эти блоки.

---

## Задача 1. INP-009 → INP-009a/b/c

### Проблема
`inputs.py` сваливает **все** `calc.warnings` в один `INP-009`.

### План
Не менять `pipeline.py`. В P4:

1. Читать provenance `N_TOP` / `N_BOT` / `N_FACE` и `TABLE6_BASE`.
2. Для каждого параметра отдельный check:
   - `INP-009a` — N_TOP  
   - `INP-009b` — N_BOT  
   - `INP-009c` — N_FACE  
3. В `detail`/`evidence` фиксировать: accepted, TABLE6_BASE, unit=`mm`, provenance.kind/source/detail/doc_ref, условие сравнения (`val < base` → WARNING, иначе PASS при наличии base), текст причины.
4. Норматив: `ГОСТ 26645-85 табл.6` + явное примечание: **направление сравнения — внутреннее правило pipeline/P1; нормативная трактовка «не более» vs «не меньше» не подтверждена текстом ГОСТ в репозитории → при `val < base` остаётся WARNING, не FAIL/PASS «по ГОСТ»**.
5. Прочие `calc.warnings` (если появятся) — отдельный `INP-009x` WARNING/список, **не** смешивать с N_*.
6. Старый монолитный `INP-009` убрать из отчёта (заменить тройкой), чтобы не дублировать.

### Файлы
- `eskd_cad/qa/p4/inputs.py` — основная правка
- `tests/test_p4_quality.py` — ожидания ID/статусов для колеса
- `P4_QUALITY.md` — строка каталога (ссылка на P4.1)

---

## Задача 2. DRW-006 — классификация дубликатов

### Факты с колеса
20 дублей ключей `(p1,p2,layer)`, **все на слое «Невидимая»** (HLR plan). Геометрию не трогаем.

### План
Расширить проверку в `drawing.py` (хелпер рядом, напр. `qa/p4/duplicate_lines.py`):

1. Группировать совпадающие `Line` (как сейчас, round 3).
2. Классификатор **без исключения всего слоя «Невидимая»**:
   - `hlr_coincident` — слой Невидимая/скрытые сегменты HLR, кратность ≤ порога, короткие сегменты проекции → **допустимо** (не поднимает WARNING);
   - `drawing_duplicate` — Основная/Тонкая/Осевая/Припуск/… → **реальный дубль оформления** → WARNING;
   - `ambiguous_same_geom` — совпадение координат, но разные соседние контексты / неоднозначность → WARNING с пометкой «требует разбора».
3. Диагностика в `detail` (и при необходимости JSON-поле evidence): layer, coords, entity=`Line`, count, class, reason.
4. Итог DRW-006:
   - PASS, если нет `drawing_duplicate` / `ambiguous_*`;
   - WARNING, если есть оформлениеные/ambiguous;
   - HLR-совпадения перечисляются в evidence как **принятые**, не как PASS «тишиной».

Порог HLR и правила класса — **внутреннее инженерное правило**, задокументировать в отчёте; не называть ГОСТ.

### Файлы
- `eskd_cad/qa/p4/drawing.py`
- **новый** `eskd_cad/qa/p4/duplicate_lines.py`
- `tests/test_p4_quality.py` (+ точечный unit на классификатор)

---

## Задача 3. GEO-002 — прозрачность допусков пересечений

### Факты (КП-062215009-01, без смены tol)
| Пара | V∩ мм³ | tol_volume мм³ | expect | ok сейчас |
|------|--------|----------------|--------|-----------|
| metal∩core1 | ≈ 30436 | **50000** | disjoint | True |
| metal∩core2 | 0 | 10000 | disjoint | True |
| gating∩core1 | 0 | 20000 | disjoint | True |
| metal∩Хол.* | >100 | 100 | overlap | True |

- Размерность tol: **мм³** (коммент в `ocp_worker.check_intersections`).
- Metal ≈ 8.05×10⁷ мм³ → ∩core1 ≈ **0.038 %** объёма металла; характерный размер ∛V ≈ 31 мм.
- В коде **нет** provenance/обоснования почему именно `5.0e4` (только комментарий «не должны сильно пересекать»).

### План
**Не менять** `tol_volume` в `assembly_wheel.intersection_job` (P3).

В `geometry.py` для GEO-002:

1. Для каждой пары писать в detail/evidence: V_mm3, tol_mm3, unit, V/V_metal (если есть), expect, ok_vs_tol.
2. Ввести явное поле/флаг `tol_basis = "unconfirmed"` пока нет документированного инженерного основания в knowledge.
3. Статус:
   - если pair.ok==False → **FAIL** (как сейчас);
   - если все ok, но есть disjoint-пара с `V > 0` и `tol_basis=unconfirmed` → **WARNING** (не «полностью подтверждённый PASS»): факт «уложились в число» ≠ «допуск обоснован»;
   - опционально отдельный `GEO-002b` NOT_CHECKED «обоснование tol» — только если не раздуваем каталог; предпочтительно один GEO-002 со статусом WARNING + прозрачный detail.
4. Не объявлять через GEO-002 вклад в `fully_verified` сверх текущих правил (WARNING не блокирует; это ОК).

### Файлы
- `eskd_cad/qa/p4/geometry.py`
- `tests/test_p4_quality.py`
- `P4_1_REPORT.md` — численные факты колеса

*Не трогать:* `assembly_wheel.py`, `ocp_worker.py` (кроме чтения meta).

---

## Задача 4. DRW-004 — базы без ложного PASS

### Проблема
Сейчас: любой `Text` длины 1 (А/Б/В/У/Н…) → PASS. На листе есть буквы штампа и секущих плоскостей.

### План
Распознавать **графический паттерн `add_datum`**:
- закрытый `Polyline` (треугольник) на «Тонкая»;
- `Line` полки;
- закрытый `Polyline` рамки;
- `Text` буквы (height≈5, layer Текст) рядом с рамкой.

Статусы:

| Ситуация | Статус |
|----------|--------|
| ≥1 полный паттерн базы | PASS (+ список букв) |
| Буквы есть, паттерна нет / неоднозначно | NOT_CHECKED |
| Нет ни паттерна, ни связанных сущностей | FAIL или NOT_CHECKED (предпочтительно NOT_CHECKED при сомнении; FAIL только если базы обязательны по внутренней политике чертежа отливки и паттерн точно отсутствует) |

Связь с размером/ребром: если явной association нет → не выдумывать; в detail «связь с геометрией: NOT_CHECKED».

Норматив: ГОСТ 2.308 + «упрощённая реализация annotations/datums.py»; не приписывать ГОСТ то, что проверяет только локальный паттерн.

### Файлы
- `eskd_cad/qa/p4/drawing.py`
- **новый** `eskd_cad/qa/p4/datum_detect.py` (опционально, если разрастётся)
- `tests/test_p4_quality.py`
- *Не менять* `annotations/datums.py` (использовать как эталон паттерна)

---

## Задача 5. Подготовка DRW-016 — карта feature → dimension

### Цель этапа
Структура + **частичная** верификация для списка параметров; агрегат DRW-016 **не PASS целиком**.

### Карта (новый модуль)

```text
feature_id
  → casting_param (CastingSpec)
  → ocp_measure (bbox / section span / None)
  → view_id (AA | plan | BB | local_BB)
  → dxf_dim (DimLinear match by text+view heur.)
  → measured_value (span · view_scale_model)
  → tolerance
  → status (PASS | FAIL | WARNING | NOT_CHECKED)
```

Стартовый набор:

| feature_id | CastingSpec | OCP / вид (если доступно) |
|------------|-------------|---------------------------|
| rim_od | C_OUT | AA bbox width; plan/BB dims |
| boss_od | C_BOSS | AA dim / радиус тела |
| hub_od | C_HUB | AA |
| body_height | H_BODY | AA vertical |
| riser_od | D_RISER | AA |
| riser_height | H_RISER | AA |
| channel_height | C_H_CH | AA |
| print_length | L_PRINT | local_BB span |

Правила статуса per-feature:

1. Текст размера == CastingSpec **и** нет геометрического measure → **не PASS** (максимум промежуточный evidence; в карте NOT_CHECKED «нет OCP/span measure»).
2. Есть measure (bbox/span·scale) согласован с CastingSpec в tol → PASS по этой строке.
3. Measure противоречит CastingSpec или подписи → FAIL по строке.
4. Нет DimLinear / неподдерживаемый тип → NOT_CHECKED.

Агрегат **DRW-016**:
- FAIL, если любая строка FAIL;
- иначе NOT_CHECKED, пока есть незакрытые строки или нет полной association с ребром;
- PASS всего блока **не ставить** в P4.1 (даже если 8 стартовых строк зелёные) — в отчёте явно: «карта подготовлена; полное покрытие DIMENSION↔ребро не достигнуто».

Это сохраняет `fully_verified=False`.

### Файлы
- **новый** `eskd_cad/qa/p4/dim_map.py` — структура + измерение
- `eskd_cad/qa/p4/drawing.py` — вызов карты, статус DRW-016
- `eskd_cad/qa/p4/runner.py` — при необходимости передать views из geometry
- `tests/test_p4_quality.py` / **новый** `tests/test_p4_1_dim_map.py`

---

## Задача 6. Регрессия

После реализации (по согласованию):

```bash
cd cad_subsystem
PYTHONPATH=. python3 -m unittest \
  tests.test_p0_parity \
  tests.test_p1_calc_integration \
  tests.test_p2_ocp_geometry \
  tests.test_p3_geometry \
  tests.test_p4_quality \
  tests.test_p4_1_*   # новые
PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
```

Контроль неизменности расчётов: TABLE6_BASE=5.2, C_HUB=248, H_BODY=464, L_PRINT=60, H_PRINT2=40, F_PIT:F_SLAG:F_SPRUE=12:14.4:16.8 (как P1 golden).  
Артефакты: DXF/PDF + `_P4_quality.md|.json` + `P4_1_REPORT.md`.

---

## Перечень затрагиваемых файлов

### Новые
| Файл | Назначение |
|------|------------|
| `cad_subsystem/P4_1_PLAN.md` | этот план |
| `cad_subsystem/P4_1_REPORT.md` | отчёт после реализации |
| `eskd_cad/qa/p4/duplicate_lines.py` | классификация дублей |
| `eskd_cad/qa/p4/dim_map.py` | карта DRW-016 |
| `eskd_cad/qa/p4/datum_detect.py` | опционально, детектор баз |
| `tests/test_p4_1_*.py` | тесты P4.1 |

### Изменяемые (только QA-слой)
| Файл | Задачи |
|------|--------|
| `eskd_cad/qa/p4/inputs.py` | 1 |
| `eskd_cad/qa/p4/geometry.py` | 3 |
| `eskd_cad/qa/p4/drawing.py` | 2, 4, 5 |
| `eskd_cad/qa/p4/runner.py` | 5 (views → dim_map) |
| `eskd_cad/qa/p4/__init__.py` | экспорты при необходимости |
| `tests/test_p4_quality.py` | 1–5, 6 |
| `P4_QUALITY.md` | краткая отсылка к P4.1 |

### Не изменяемые
| Область | Файлы |
|---------|-------|
| P1 calc | `pipeline.py`, `gost26645_table6.py`, `wheel_inputs.py`, `koleso_data.py`, knowledge JSON |
| P2/P3 geom | `ocp_*.py`, `assembly_wheel.py` (tol!), `tech_params.py`, `foundry/ocp_koleso.py` builders |
| Аннотации | `annotations/datums.py` (только чтение паттерна) |
| Экспорт | `dxf_export.py`, `pdf_export.py` |

---

## Ожидаемый эффект на статусы колеса (прогноз)

| ID | Было | Ожидается после P4.1 |
|----|------|----------------------|
| INP-009 | 1× WARNING (все warnings) | INP-009a PASS; 009b/009c WARNING; без смены N_* |
| DRW-006 | WARNING (20 HLR) | PASS или WARNING только при drawing_duplicate; HLR в evidence |
| GEO-002 | PASS | WARNING (tol без основания) **или** PASS+отдельный NOT_CHECKED — по согласованию ниже |
| DRW-004 | PASS (ложный риск) | PASS по паттерну `add_datum` **или** NOT_CHECKED |
| DRW-016 | NOT_CHECKED | NOT_CHECKED (карта + частичные строки; блок не PASS) |
| fully_verified | False | **False** |

---

## Решения согласования (зафиксировано)

1. **GEO-002:** PASS при pair.ok; **GEO-002b NOT_CHECKED** до подтверждения tol; volumes в evidence.  
2. **DRW-004:** без паттерна → NOT_CHECKED; FAIL только при доказанном отсутствии.  
3. **DRW-016:** агрегат NOT_CHECKED даже при PASS всех 8 строк.  
4. **P4_QUALITY.md:** описание P4.1 разрешено; семантика P4 сохранена.  
5. **INP-009:** не ставить PASS по `N_TOP >= TABLE6_BASE` как ГОСТ; разделить числовой факт и нормативное подтверждение; N_* не менять.

Реализация и результаты — в `P4_1_REPORT.md`.
