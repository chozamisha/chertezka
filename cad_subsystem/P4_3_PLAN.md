# P4.3 — план точечного исправления эвристик QA

**Статус:** согласован и реализован — см. [`P4_3_REPORT.md`](P4_3_REPORT.md).  
**База:** `P4_2_AUDIT.md` (ISSUE: DRW-004, DRW-006, DRW-016)  
**Объект:** КП-062215009-01  
**Ветка:** `cursor/p4-3-qa-heuristics-666e` ← `cursor/p4-1-quality-hardening-666e`

---

## Цель

Исправить три эвристики контроля **без** изменения P1–P3, расчётов, `tol_volume`, геометрии отливки, экспорта DXF/PDF и формулы `fully_verified`.  
Не раздувать PASS искусственно; агрегат DRW-016 остаётся `NOT_CHECKED`.

---

## Ограничения (жёсткие)

| Запрещено | Разрешено |
|-----------|-----------|
| Менять `pipeline` / `koleso_data` / OCP solids / `intersection_job.tol_volume` | Править только `eskd_cad/qa/p4/*` (+ тесты, MD) |
| Менять `annotations/datums.py`, `cutting_plane.py` | Читать их как эталон паттернов |
| Удалять/править геометрию ради QA | Только классификация и evidence |
| Угадывание scale перебором `{1,2,5}` | Scale только из `ViewTransform.k` (или явный layout registry) |
| `fully_verified=True` при NOT_CHECKED | Сохранить семантику P4 |

---

## Контекст: эталонная геометрия (без правок)

### `add_datum` (`annotations/datums.py`)
```
Polyline closed points=[tip, b, a, c]  layer=Тонкая   # «треугольник» (4 вершины)
Line shelf0=a → shelf1=a+outward*12     layer=Тонкая
Polyline closed box axis-aligned s=7    layer=Тонкая
Text letter height=5 center in box      layer=Текст
```
Ключевые отличия triangle vs box:
- **box:** 4 угла прямоугольника, стороны || осям, `s≈7`, opposite edges equal.
- **triangle poly:** `tip` — остриё к поверхности; `a = tip + n̂·size`; `b,c` симметричны относительно `n̂`; это **не** прямоугольник (диагонали/углы иные).

### `add_cutting_plane` (`annotations/cutting_plane.py`)
```
Line p1–p2          layer=Тонкая
Line tick           layer=Сечение   # на каждом конце
Text letter h=5     layer=Текст     # рядом с tick; БЕЗ рамки/треугольника
```

### Виды листа (из `build_koleso_otlivka`, не менять)
| view_id | ox, oy | k (`ViewTransform`) | подпись scale (не авторитет) |
|---------|--------|---------------------|------------------------------|
| AA | 145, 235 | `spec.scale_k` (=5) | 1:5 |
| plan | 400, 200 | `spec.scale_k` | 1:5 |
| BB | 520, 300 | `spec.scale_k * 1.6` | 1:8 |
| local_BB | 120, 55 | **2.0** | подпись «1:1» ≠ k |

`sheet = model / k` ⇒ `model = sheet_span * k`.  
**P4.3 использует `k` из layout/ViewTransform, не текст подписи.**

### HLR
`emit_curve`: `CurveKind.HIDDEN` → layer `Невидимая`, linetype HIDDEN.  
`ViewResult.meta["n_hidden"]` — счётчик; кривые hidden доступны в `views["plan"].curves`.

---

## Задача 1. DRW-004 — детектор баз

### Файлы
| Файл | Действие |
|------|----------|
| `eskd_cad/qa/p4/datum_detect.py` | **переписать** классификацию poly + кластеризацию |
| `eskd_cad/qa/p4/drawing.py` | тонкая правка detail/evidence DRW-004 при необходимости |
| `tests/test_p4_3_datums.py` | **новый** |
| `annotations/datums.py` | **не трогать** |

### Алгоритм (замена bbox-only)

1. **`classify_closed_poly(pl) → box | datum_triangle | other`**
   - `box`: 4 вершины; рёбра попарно ортогональны / axis-aligned; стороны ≈ квадрат (`|w−h|<ε`, `w∈[5,9]` под `s=7`); углы ≈90°.
   - `datum_triangle`: 4 вершины `[tip,b,a,c]`;  
     - `|b−tip| ≈ |c−tip|` (симметрия);  
     - `a` дальше от tip вдоль биссектрисы `(b+c)/2`;  
     - mid(b,c) близко к tip + t·(a−tip) с малым t;  
     - **отклонить**, если фигура проходит тест прямоугольника.
   - Иначе `other` (не использовать как рамку/треугольник базы).

2. **Исключение букв секущих (`is_cutting_plane_letter(text)`)**
   - Признаки (достаточно одного сильного):  
     - существует `Line` на слое **«Сечение»**, конец которой в радиусе R_tick от позиции буквы;  
     - и/или буква лежит у конца thin-line секущей без соседнего `box`+`triangle` кластера.  
   - Такие Text **не** входят в кандидаты баз.

3. **Исключение штампа**
   - Сохранить `height ≥ 4` (штамп 3.5). Дополнительно: layer≠Штамп / вне рамки основной надписи — по желанию, если нужно.

4. **Кластер `build_datum_cluster(box)`**
   - От **рамки** (не от буквы):  
     a. Найти `Text` с центром внутри/у bbox рамки (не дальше `max_letter_in_box`).  
     b. Найти `Line` полки: один конец у рамки, другой — у вершины `a` треугольника.  
     c. Найти `datum_triangle`, у которого вершина `a` (или tip→a) стыкуется с полкой; tip в стороне поверхности.  
   - Кластер валиден только если **все четыре** элемента связаны в одной локальной цепочке (диаметр кластера ≤ порога, например 50–60 sheet mm).  
   - **Запрет:** буква + «любой box в радиусе 18» без полки/треугольника той же цепи.

5. **Статусы DRW-004** (как P4.1 решение)
   - ≥1 полный кластер → PASS (+ список букв полных кластеров).  
   - Только partial / ничего достоверного → NOT_CHECKED.  
   - FAIL — только при доказанном отсутствии обязательного обозначения (в P4.3 по умолчанию не вводим новый FAIL на колесе).

### Ожидаемый эффект на колесе
- База А-А → full.  
- База «Б» → full (треугольник больше не box).  
- Буквы секущих А/В → исключены.  
- Штамп У/В/Н → исключены.

### Тесты `tests/test_p4_3_datums.py`
Синтетические `DrawingDocument` (без OCP):

1. `test_real_datum_A` — один `add_datum(..., "А")` → full, letter А.  
2. `test_real_datum_B` — `add_datum(..., "Б", size=6.5)` → full, letter Б.  
3. `test_cutting_plane_letters_excluded` — `add_cutting_plane` А/В → 0 datum hits.  
4. `test_stamp_letters_excluded` — Text h=3.5 «У» → не кандидат.  
5. `test_partial_pattern` — только box+letter без triangle → partial / не full.  
6. `test_foreign_box_near_letter` — cutting letter рядом с чужим квадратом → не full.  
7. `test_multiple_datums` — А и Б на одном doc → letters ⊇ {А,Б}, full_count≥2.

Интеграционно: на колесе `datum_check_payload` содержит «Б» в full letters (и не считает сечение А за базу).

---

## Задача 2. DRW-006 — классификация дубликатов

### Файлы
| Файл | Действие |
|------|----------|
| `eskd_cad/qa/p4/duplicate_lines.py` | расширить API: опционально `views`, `view_layout` |
| `eskd_cad/qa/p4/drawing.py` | передать views/layout в классификатор |
| `eskd_cad/qa/p4/runner.py` | при необходимости прокинуть layout |
| `tests/test_p4_3_duplicates.py` | **новый** |

### Алгоритм

Сигнатура:
```python
classify_duplicate_lines(
    doc,
    *,
    views: dict[str, ViewResult] | None = None,
    view_layouts: dict[str, ViewLayout] | None = None,  # ox,oy,k + window window
) -> list[DupGroup]
```

Для каждой группы совпадающих `Line` (как сейчас: round3 + layer):

1. **Слой оформления** (`Основная`, `Тонкая`, …) → `drawing_duplicate` (без изменений по смыслу).

2. **Слой «Невидимая» / HIDDEN** — **недостаточно** layer+count≤4:
   - Построить множество эталонных HLR-сегментов листа:  
     для каждого view с HLR (как минимум `plan`):  
     `CurveKind.HIDDEN` → точки через `ViewTransform(ox,oy,k).P` → отрезки sheet.  
   - Сегмент группы **подтверждён HLR**, если существует эталон с совпадением концов (tol ~0.05…0.5 sheet mm) или покрытием по длине.  
   - Дополнительно: длина сегмента ≤ порога короткого HLR-фрагмента **или** согласована с типичной длиной эталона.  
   - `meta.n_hidden` (если есть): информативно в evidence; если `n_hidden==0`, а дубли на Невидимая есть → не `hlr_coincident`.

3. **Решение класса для «Невидимая»:**
   | Условие | classification |
   |---------|----------------|
   | HLR-match подтверждён, count≤4 | `hlr_coincident` |
   | HLR-match подтверждён, count>4 | `ambiguous_same_geom` |
   | layer Невидимая, **нет** HLR-match (или нет views) | `ambiguous_same_geom` (не silent PASS) |
   | явное оформление (если когда-либо на Невидимая рисуют вручную дубль без HLR) | то же → ambiguous / при желании отдельный subclass в reason |

4. **Нет `views` / нет layout / нет `n_hidden`:**  
   все не-drawing совпадения → `ambiguous_same_geom` + reason `insufficient_hlr_evidence` → DRW-006 **WARNING** (не PASS).

5. Геометрию **не** удалять.

### Ожидаемый эффект на колесе
- При передаче `views["plan"]` + layout plan: текущие 20 групп с match → `hlr_coincident`, DRW-006 PASS.  
- Искусственный дубль на Невидимая вне HLR → WARNING.

### Тесты `tests/test_p4_3_duplicates.py`
1. `test_confirmed_hlr_coincident` — doc с Line, совпадающей с transformed hidden curve → hlr_coincident.  
2. `test_real_duplicate_on_hidden_layer` — две Line на Невидимая **без** HLR-match → ambiguous, DRW-006 WARNING.  
3. `test_duplicate_on_main_layer` — дубль на Основная → drawing_duplicate, WARNING.  
4. `test_ambiguous_without_evidence` — Невидимая, views=None → ambiguous.  
5. `test_count_above_threshold` — 5 совпадений даже с HLR-match → ambiguous.  
6. `test_missing_n_hidden` — view без meta.n_hidden, но с hidden curves → всё ещё можно PASS по match кривых; view без curves → ambiguous.

---

## Задача 3. DRW-016 — карта размеров

### Файлы
| Файл | Действие |
|------|----------|
| `eskd_cad/qa/p4/dim_map.py` | measure_kind, view binding, запрет infer scale |
| `eskd_cad/qa/p4/view_layout.py` | **новый** — реестр окон видов колеса (зеркало констант builder) |
| `eskd_cad/qa/p4/drawing.py` / `runner.py` | передать layout+views |
| `tests/test_p4_3_dim_map.py` | **новый** |
| `tests/test_p4_1_quality.py` | обновить ожидания detail/measure_kind при необходимости |

### Структура `ViewLayout`
```python
@dataclass(frozen=True)
class ViewLayout:
    view_id: str          # AA | plan | BB | local_BB
    ox: float
    oy: float
    k: float              # ViewTransform.k — единственный источник scale
    half_w: float         # окно для hit-test DimLinear midpoint
    half_h: float
```

`wheel_view_layouts(spec) -> dict[str, ViewLayout]` — константы как в `build_koleso_otlivka` (145/235/k=scale_k, …, local k=2.0).  
Тест `test_layout_k_matches_builder_constants` фиксирует числа, чтобы дрейф builder был заметен.

### Алгоритм привязки DimLinear → view
1. Midpoint размера `(p1+p2)/2`.  
2. Вид, в чьём окне `[ox±half_w]×[oy±half_h]` лежит mid.  
3. Если 0 или >1 вид → размер **неоднозначен** → строка `NOT_CHECKED`, `measure_kind=unavailable`.  
4. Scale строки = `layout.k` выбранного вида (**запрещён** перебор).

### `measure_kind` (обязателен в evidence каждой строки)
| kind | Когда | Можно ли PASS строки |
|------|-------|----------------------|
| `ocp_bbox` | есть bbox ViewResult и согласован с CastingSpec | да (как rim_od width) |
| `ocp_section` | зарезервировано; пока не используем без явного section measure API | — |
| `sheet_span` | `‖p2−p1‖ * layout.k ≈ casting_value` + text_ok | да, но **явно не OCP** |
| `unavailable` | нет вида / нет scale / нет dim / только текст | NOT_CHECKED, не PASS |

Правила статуса строки:
- text-only → NOT_CHECKED (`measure_kind=unavailable` или отдельный detail).  
- sheet_span PASS допустим как «геометрия аннотации листа», с `measure_kind=sheet_span` в evidence.  
- Противоречие measure vs CastingSpec → FAIL.  
- **Агрегат DRW-016 = NOT_CHECKED всегда** (даже 8×PASS).

### `print_length`
- View = `local_BB`, **k=2.0** из layout (не «1:1» из label, не перебор).  
- `sheet_span * 2.0` должно дать 60 на колесе.  
- OCP local_BB bbox width **не** выдавать за L_PRINT (как сейчас в note); `measure_kind=sheet_span` пока нет отдельного OCP print-length measure.

### Ожидаемый эффект
- Прозрачность: в JSON видно, что 7/8 — `sheet_span`, 1 — `ocp_bbox`.  
- Нет угадывания scale.  
- Неверный view → NOT_CHECKED, не ложный PASS.

### Тесты `tests/test_p4_3_dim_map.py`
1. `test_measure_kind_ocp_bbox_for_c_out` — rim_od → ocp_bbox (+ sheet_span опционально).  
2. `test_measure_kind_sheet_span_not_called_ocp` — hub_od → sheet_span.  
3. `test_no_scale_bruteforce` — отсутствие layout.k ⇒ NOT_CHECKED (не подбор из списка).  
4. `test_dim_bound_to_view_window` — DimLinear вне окон → NOT_CHECKED.  
5. `test_ambiguous_view_membership` — mid на стыке двух окон → NOT_CHECKED.  
6. `test_print_length_uses_layout_k_2` — k=2, meas=60.  
7. `test_aggregate_always_not_checked` — даже все строки PASS.

---

## Проводки в runner / drawing

```
run_geometry_checks → views
wheel_view_layouts(spec) → layouts
run_drawing_checks(..., views=views, view_layouts=layouts)
  → classify_duplicate_lines(doc, views=views, view_layouts=layouts)
  → build_dim_map(doc, spec, views=views, view_layouts=layouts)
  → datum_check_payload(doc)  # без views
```

Новых зависимостей от изменения foundry API **нет** (layout зеркалирует константы builder).

---

## Регрессия (после реализации)

```bash
cd cad_subsystem
PYTHONPATH=. python3 -m unittest \
  tests.test_p0_parity \
  tests.test_p1_calc_integration \
  tests.test_p2_ocp_geometry \
  tests.test_p3_geometry \
  tests.test_p4_quality \
  tests.test_p4_1_quality \
  tests.test_p4_3_datums \
  tests.test_p4_3_duplicates \
  tests.test_p4_3_dim_map -v

PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
```

Контроль неизменности: TABLE6_BASE=5.2, N_*=6/5/5, H_BODY=464, L_PRINT=60, H_PRINT2=40, ЛС 12:14.4:16.8; `tol_volume` metal∩core1=5e4; entity counts DXF без намеренного удаления Line.

---

## Документы результата (после кода)

| Файл | Содержание |
|------|------------|
| `P4_3_PLAN.md` | этот план |
| `P4_3_REPORT.md` | что исправлено из P4.2; остатки; новые правила; тесты; статусы P4.1 vs P4.3; доказательство неизменности P1–P3 |
| `P4_QUALITY.md` | краткая ссылка на P4.3 (семантика P4 без ломки) |

---

## Прогноз статусов колеса (не цель «больше PASS»)

| ID | P4.1 | Ожидание P4.3 |
|----|------|----------------|
| DRW-004 | PASS (letters=['А'], ложный full на сечении) | PASS с letters ⊇ {А,Б}; сечение исключено |
| DRW-006 | PASS (20 hlr по имени слоя) | PASS только при HLR-match; иначе WARNING |
| DRW-016 | NOT_CHECKED; 8 feature PASS без measure_kind | NOT_CHECKED; feature с явным measure_kind; без scale-guess |
| fully_verified | False | **False** |

---

## Вопросы на согласование

1. **Layout registry в `qa/p4/view_layout.py`** (зеркало констант builder) — ОК? Альтернатива: крошечный read-only getter в foundry (чуть трогает foundry API).  
2. **DRW-006 без views:** всегда WARNING через ambiguous — ОК?  
3. **sheet_span PASS** оставляем как допустимый статус строки (с честным measure_kind), верно?  
4. Имя ветки: коммит в текущий PR #95 или новая `cursor/p4-3-qa-heuristics-666e`?

После ответа / «согласовано» — реализация задач 1→3, регрессия, `P4_3_REPORT.md`.
