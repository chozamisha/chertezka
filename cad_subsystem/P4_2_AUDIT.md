# P4.2 — независимый аудит качества P4.1

**Объект:** КП-062215009-01  
**База:** `P4_AUDIT.md`, `P4_1_PLAN.md`, `P4_1_REPORT.md`, `out/KP-062215009-01_*`  
**Режим:** только исследование. Код, расчёты, геометрия, DXF/PDF **не изменялись**.  
**Ветка на момент аудита:** `cursor/p4-1-quality-hardening-666e`

Легенда результата по пункту: **PASS** (корректно) · **ISSUE** (дефект/риск) · **NOT_CHECKED** (нельзя подтвердить без доп. данных).

---

## 1. INP-009a / INP-009b / INP-009c

### Проверенные файлы / функции
- `eskd_cad/qa/p4/inputs.py` — блок INP-009a/b/c  
- `eskd_cad/calc/pipeline.py` — запись provenance `N_*`, `TABLE6_BASE`  
- `eskd_cad/knowledge/calc/koleso_data.py`, `wheel_inputs.py`  
- `out/KP-062215009-01_provenance.json`, `P4_quality.json`

### Фактическая логика
1. Читает `calc.provenance["TABLE6_BASE"]` и `N_TOP` / `N_BOT` / `N_FACE` (не из DXF).  
2. При отсутствии provenance → `NOT_CHECKED`.  
3. Если `val < base` → `WARNING` + `gost_direction=unconfirmed_in_knowledge`.  
4. Если `val >= base` → `NOT_CHECKED` (явный запрет PASS «по ГОСТ»).  
5. `normative_source` = «внутреннее инженерное правило», не «ГОСТ выполнен».

### Доказательства (прогон)
| Параметр | provenance.value | kind | unit | koleso_data | CastingSpec |
|----------|------------------|------|------|-------------|-------------|
| N_TOP | 6.0 | engineer | mm | 6.0 | 6.0 |
| N_BOT | 5.0 | engineer | mm | 5.0 | 5.0 |
| N_FACE | 5.0 | engineer | mm | 5.0 | 5.0 |
| TABLE6_BASE | 5.2 | calculated | mm | — | — |

Статусы отчёта: **009a NOT_CHECKED**, **009b/c WARNING**. Монолитного `INP-009` нет.

### Результат аудита: **PASS**

### Риски
- В provenance pipeline поле `doc_ref` у `N_*` содержит строку «ГОСТ 26645-85 табл.6 + лист расчёта» — это **источник данных P1**, не статус проверки. Статус/detail P4.1 корректно не выдают это за нормативное PASS. Риск путаницы при чтении только provenance JSON — низкий.  
- Отсутствие значения → NOT_CHECKED (проверено по коду) — ложного PASS нет.

### Рекомендация
Не срочно. При желании в следующем этапе уточнить в evidence, что `doc_ref` provenance ≠ вердикт QA.

---

## 2. DRW-006 — классификация дубликатов

### Проверенные файлы / функции
- `eskd_cad/qa/p4/duplicate_lines.py` — `classify_duplicate_lines`, `summarize_duplicates`  
- `eskd_cad/qa/p4/drawing.py` — вызов DRW-006  
- сцена `DrawingDocument` + `out/KP-062215009-01_Otlivka.dxf`

### Фактическая логика
- Ключ: `(sorted(round3(p1), round3(p2)), layer)`, count≥2.  
- Слой ∈ {Невидимая, HIDDEN, Hidden}:  
  - count ≤ 4 → `hlr_coincident`  
  - count > 4 → `ambiguous_same_geom`  
- Слой оформления → `drawing_duplicate`  
- Иначе → `ambiguous_same_geom`  
- WARNING только при `drawing_duplicate` или `ambiguous_*`; HLR в evidence.  
- Геометрия **не удаляется** (только чтение).

### Доказательства (колесо)
| Метрика | Значение |
|---------|----------|
| dup groups | 20 |
| classification | все `hlr_coincident` |
| count | все = 2 |
| layer | все «Невидимая» |
| Line на «Невидимая» в сцене | 69 |
| count>4 | нет (порог не срабатывал) |
| DRW-006 статус | **PASS** |
| DXF LINE | 206 (файл на диске цел) |

### Результат аудита: **ISSUE** (средний) + частичный **PASS**

**PASS:** классификатор отрабатывает; HLR не вычищается из DXF; диагностика (layer, coords, count, class, reason) пишется в evidence; порог >4 реализован в коде.

**ISSUE:** на слое «Невидимая» при count∈{2,3,4} **любое** совпадение считается допустимым HLR. Реальный дубль оформления, случайно попавший на «Невидимая» с кратностью 2, будет скрыт под `hlr_coincident` и даст PASS. Слой не исключён целиком (как требовалось), но эвристика «слой = HLR ⇒ OK» слабо отличает шум проекции от дефекта.

### Риски
- Ложный PASS DRW-006 при настоящих дублях на «Невидимая» с count≤4.  
- Порог 4 на колесе не проверен живым случаем (нет groups с count>4).

### Рекомендация (не делать в этом аудите)
Усилить признаки HLR (длина сегмента, связность с HLR-кривыми ViewResult, сравнение с meta.n_hidden) прежде чем ставить `hlr_coincident`; при сомнении — `ambiguous_same_geom` → WARNING.

---

## 3. GEO-002 / GEO-002b

### Проверенные файлы / функции
- `eskd_cad/qa/p4/geometry.py` — GEO-002 / GEO-002b  
- `eskd_cad/foundry/ocp_koleso.py` — `run_wheel_intersection_qa`  
- `eskd_cad/geom/assembly_wheel.py` — `intersection_job` (`tol_volume`)  
- `eskd_cad/geom/ocp_worker.py` — `check_intersections` (BRepAlgoAPI_Common, mm³)

### Фактическая логика
- GEO-002: если все `pair.ok` → **PASS**; иначе FAIL.  
- Evidence JSON: `volume_mm3`, `tol_volume_mm3`, `unit=mm3`, `volume_per_metal`, `tol_basis=unconfirmed`, объёмы тел.  
- GEO-002b: всегда **NOT_CHECKED** при отсутствии основания tol в knowledge.  
- `tol_volume` в P3 **не менялся**.

### Доказательства
Повторный live OCP vs `P4_quality.json` evidence — **побитовое совпадение** объёмов:

| Пара | volume_mm3 | tol | expect | ok |
|------|------------|-----|--------|-----|
| metal∩core1 | 30436.065279 | 50000 | disjoint | True |
| metal∩core2 | **0** | 10000 | disjoint | True |
| gating∩core1 | **0** | 20000 | disjoint | True |
| metal∩Хол.1_0 | 12800 | 100 | overlap | True |
| metal∩Хол.2_* | ≈345 | 100 | overlap | True |

Нулевые объёмы обрабатываются корректно (`ok=True` при disjoint). Значения не захардкожены в QA — приходят из OCP meta.

### Результат аудита: **PASS**

### Риски
- Числовой PASS GEO-002 при metal∩core1≈30k < 50k **не** означает обоснованность tol — это явно вынесено в GEO-002b NOT_CHECKED (**соответствует решению P4.1**).  
- Большой абсолютный ∩ при малой доле metal (≈0.038 %) — инженерная тема, не баг статуса.

### Рекомендация
Для закрытия GEO-002b нужны исходные инженерные данные (обоснование tol), не правка «на глаз».

---

## 4. DRW-004 — обозначение баз

### Проверенные файлы / функции
- `eskd_cad/qa/p4/datum_detect.py` — `detect_datums`, `datum_check_payload`  
- `eskd_cad/annotations/datums.py` — эталон `add_datum` (**не изменялся**)  
- `eskd_cad/annotations/cutting_plane.py` — буквы сечений  
- `eskd_cad/foundry/ocp_koleso.py` — `add_datum(..., "А")`, `add_datum(..., "Б")`, cutting planes А/В

### Фактическая логика
- Кандидаты: `Text` length=1, upper, layer Текст, **height≥4** (штамп 3.5 отсекается).  
- Рамка: closed Polyline на Тонкая с bbox ≈ квадрат 4…14.  
- Треугольник: прочие closed Polyline на Тонкая (не прошедшие фильтр рамки).  
- full_pattern = буква рядом с рамкой + полка + tip треугольника; иначе partial.  
- DRW-004 PASS при `full_count≥1`, иначе NOT_CHECKED.

### Доказательства
Однобуквенные тексты:
- Штамп `У/В/Н` h=3.5 → **не** кандидаты (правильно).  
- Сечения: `А`,`А`,`В`,`В` h=5; базы: `А` (разрез), `Б` (план).

Hits детектора:
| letter | confidence | комментарий |
|--------|------------|-------------|
| А (148.5, 215.5) | **full_pattern** | база на А-А — ожидаемо |
| А (316.4, 212.0) | **full_pattern** | буква **секущей** плоскости, ложно связана с чужой рамкой/«треугольником» |
| А (483.6, 212.0) | partial | сечение, без tip |
| Б (506.9, 201.5) | **partial** | реальная база плана; tip=None |

**Почему «А» full, а «Б» partial**

1. Эвристика рамки (`4≤w,h≤14`, `|w−h|<3`) захватывает **треугольник** `add_datum` при `size≈6.5`: bbox треугольника ≈7.15×6.5 → классифицируется как **box**, не triangle. Tip для «Б» в список triangles не попадает → `triangle_tip=None` → partial при наличии полки.  
2. Буква секущей «А» (cutting_plane только Line+Text, без своей рамки) находит **чужой** closed polyline поблизости (например box 12×10 у (311.5, 200)) и tip в радиусе 40 → ложный **full_pattern**.

Payload отчёта: `letters=['А']`, `full_count=2` — в PASS входят и истинная база А-А, и ложное срабатывание на сечении.

### Результат аудита: **ISSUE**

### Риски
- **Ложный PASS-вклад** от буквы сечения «А» (статус DRW-004 всё равно PASS из-за настоящей базы, но evidence завышает full_pattern).  
- **Ложный partial** настоящей базы «Б» — при отсутствии любой другой full базы дало бы NOT_CHECKED вместо PASS (на колесе спасает база А-А).  
- Штамп отсекается по height — хорошо.

### Рекомендация (не реализовывать в аудите)
- Не классифицировать треугольники `add_datum` как box (учитывать 4 точки tip-b-a-c / ориентацию).  
- Исключать буквы секущих (слой/связь с ticks «Сечение») из кандидатов баз.  
- Требовать соответствие letter↔конкретный графический кластер, а не «любая буква + любой box в радиусе».

---

## 5. DRW-016 — карта размеров

### Проверенные файлы / функции
- `eskd_cad/qa/p4/dim_map.py` — `build_dim_map`, `_infer_measured`, `_bbox_w`  
- `eskd_cad/qa/p4/drawing.py` — агрегат DRW-016  
- `eskd_cad/foundry/ocp_koleso.py` — размещение DimLinear / масштабы видов

### Способ получения `measured_value` по строкам

| feature_id | CastingSpec | Вид (заявлен) | OCP bbox / section | Sheet span×scale | Чем обоснован PASS строки |
|------------|-------------|---------------|--------------------|------------------|---------------------------|
| rim_od | C_OUT=825 | AA | **да**: AA bbox width=825 | span 165 ×5 =825 | OCP bbox **+** лист |
| boss_od | C_BOSS=346 | AA | нет | 69.2 ×5 | **только лист** (span×scale + текст) |
| hub_od | C_HUB=248 | AA | нет | 49.6 ×5 | только лист |
| body_height | H_BODY=464 | AA | нет (AA height ≠ H_BODY) | 92.8 ×5 | только лист |
| riser_od | D_RISER=300 | AA | нет | 60 ×5 | только лист |
| riser_height | H_RISER=300 | AA | нет | 60 ×5 | только лист |
| channel_height | C_H_CH=115 | AA | нет | 23 ×5 | только лист |
| print_length | L_PRINT=60 | local_BB | bbox_width есть, но **не** используется как measure (=L_PRINT) | 30 ×**2** (inferred) | только лист; scale **подобран** из {1,2,5} |

Агрегат: `aggregate_status=NOT_CHECKED` при 8/8 PASS строк — **подтверждено**.

### Допуски
- C_OUT: ±5 mm; остальные стартовые: ±2 mm.  
- Выбор первого DimLinear с данным `text`: для ⌀825 первый — вид А-А (span 165) — согласован с feature rim_od. План/В-В (165 и 103.125) **отдельными строками карты не проверяются**.

### Результат аудита: **ISSUE** (низкий/средний) + **PASS** по агрегату

**PASS:** запрет PASS только по тексту соблюдён; агрегат NOT_CHECKED; rim_od имеет реальное OCP-измерение.

**ISSUE:**
1. Семь из восьми PASS — это согласованность **аннотации листа** (p1–p2 · scale) с CastingSpec, **не** измерение ребра/сечения OCP. В отчёте это сказано в detail, но заголовок «карта feature→OCP» легко перечитать как более сильную верификацию.  
2. `print_length`: scale=2 **угадан** перебором, тогда как подпись вида «1:1» — расхождение документации вида и фактического transform; PASS геометрически согласован, но scale не взят из метаданных вида.  
3. `_find_dim` не привязан к view bbox — при перестановке порядка сущностей rim_od мог бы взять ⌀825 с В-В (другой scale).

### Рекомендация
- В evidence явно маркировать `measure_kind=ocp_bbox|sheet_span`.  
- Scale брать из ViewTransform / метаданных вида, не из перебора.  
- Привязку DimLinear к view — по положению mid относительно окна вида.

---

## 6. Общая логика P4

### Проверенные файлы / функции
- `eskd_cad/qa/p4/status.py` — `counts`, `fully_verified`  
- `out/KP-062215009-01_P4_quality.json`

### Доказательства
```
counts = {PASS: 27, FAIL: 0, WARNING: 4, NOT_CHECKED: 3}
sum = 34 = len(checks)
fully_verified = False
```

Формула: `fully_verified ⇔ ¬FAIL ∧ ¬NOT_CHECKED` — соблюдена.  
NOT_CHECKED: INP-009a, GEO-002b, DRW-016.  
WARNING: INP-007, INP-008, INP-009b, INP-009c — **не** входят в PASS.  
WARNING не блокирует fully_verified (by design) и не переименовывается в PASS.

### Результат аудита: **PASS**

### Риски
- Путаница «27 PASS ⇒ почти полностью проверен» при 3 NOT_CHECKED — снята явным `fully_verified=False`.  
- DRW-004 PASS при частичном ложном full_pattern — см. §4 (не ломает формулу статусов, но ослабляет смысл PASS).

---

## 7. Артефакты DXF / PDF / golden

### Проверено
- `out/KP-062215009-01_Otlivka.dxf` — открывается (ezdxf); типы: LINE 206, LWPOLYLINE 74, DIMENSION 10, HATCH 2, TEXT 60, …  
- PDF/PNG присутствуют; визуально: виды А-А / план HLR / В-В / Б-Б, прибыль, ЛС, штамп КП-062215009-01, ТТ со ссылками calc — структура чертежа на месте.  
- Golden: TABLE6_BASE=5.2, C_HUB=248, H_BODY=464, L_PRINT=60, H_PRINT2=40, F 12:14.4:16.8 — совпадают с P0/P1.  
- P4.1 не переписывает геометрию при QA: удалений Line нет; generate после P4.1 отрабатывает checklist 10/10.

### Результат аудита: **PASS**

### Риски
- scene Line (188) ≠ DXF LINE (206): экспорт добавляет примитивы (оформление/SOLID→и т.п.) — не признак повреждения P4.1.

---

## Сводная таблица

| ID / тема | Результат аудита | Суть |
|-----------|------------------|------|
| INP-009a/b/c | **PASS** | Источники верны; нет ложного ГОСТ-PASS |
| DRW-006 | **ISSUE** | HLR count≤4 может скрыть реальный дубль на «Невидимая» |
| GEO-002 | **PASS** | Объёмы из OCP; нули ок |
| GEO-002b | **PASS** (статус NOT_CHECKED корректен) | Числовой PASS ≠ обоснование tol |
| DRW-004 | **ISSUE** | Ложный full на сечении «А»; база «Б» partial из-за box/triangle heuristic |
| DRW-016 строки | **ISSUE** (мягкий) | 7/8 — sheet span, не OCP edge; scale L_PRINT inferred |
| DRW-016 агрегат | **PASS** | NOT_CHECKED сохранён |
| counts / fully_verified | **PASS** | Формула и подсчёт верны |
| DXF/PDF / golden | **PASS** | Чертёж и расчёты не повреждены |

---

## Общий вердикт

### 1. Можно ли считать P4.1 технически устойчивым?
**Да, с оговорками.** Ядро статусов, разделение числового/нормативного для припусков, GEO-002/002b, агрегат DRW-016 и неизменность расчётов/DXF выглядят устойчиво. Детектор баз и «доверие» к HLR-дублям — слабые места эвристик, не поломка пайплайна.

### 2. Есть ли ложные PASS или ложные WARNING?
| Тип | Есть? | Где |
|-----|-------|-----|
| Ложный PASS (строгий) | **Частично** | DRW-004: в evidence full_pattern на букве сечения «А»; статус PASS при этом ещё и от истинной базы А-А. DRW-006: потенциальный ложный PASS при реальном дубле на «Невидимая» count≤4 (на колесе не доказан дефект, но логика допускает). DRW-016 feature PASS ≠ «проверено ребро OCP» (7/8). |
| Ложный WARNING | **Нет** на колесе | DRW-006 больше не WARN на чистый HLR; INP-009b/c WARNING осознанны. |
| Ложный NOT_CHECKED | Нет | INP-009a / GEO-002b / DRW-016 — по решению P4.1. |

### 3. Какие проблемы действительно требуют исправления?
1. **DRW-004:** разделение triangle vs box; исключение букв секущих плоскостей.  
2. **DRW-006 (желательно):** не считать любой count≤4 на «Невидимая» автоматически `hlr_coincident`.  
3. **DRW-016 (желательно):** явный `measure_kind`; scale из метаданных вида; привязка dim→view.

### 4. Какие проблемы требуют исходных инженерных данных?
- Текст ГОСТ 26645-85 табл.6 → закрытие нормативного статуса INP-009*.  
- Обоснование `tol_volume` → GEO-002b.  
- JSON/таблица верт. знаков → INP-008.  
- Шаблон лопаток → INP-007.  
- Семантика dim↔edge BRep → перевод агрегата DRW-016 из NOT_CHECKED.

### 5. Можно ли переходить к следующему этапу?
**Да** — к этапу, который либо (a) закрывает инженерные gaps данными, либо (b) точечно чинит эвристики DRW-004/006/016 **после** явного ТЗ на исправления.  
**Не** объявлять чертёж `fully_verified` и не считать P4.1 «закрывшим» association размеров с OCP.

---

*Конец аудита P4.2. Исправления не выполнялись.*
