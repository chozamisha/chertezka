# P4.5 — аудит инженерных данных и нормативной базы

**База кода:** `cursor/p4-3-1-qa-hardening-666e` @ `386695a`  
**Режим:** только инвентаризация и проверка источников. Код P0–P4.3.1, расчёты, геометрия, DXF/PDF **не изменялись**.  
**Контрольная точка QA:** PASS=27, FAIL=0, WARNING=4, NOT_CHECKED=3, `fully_verified=False`.

### Область поиска

| Область | Результат |
|---------|-----------|
| Git-репозиторий `gidproject` (`cad_subsystem/eskd_cad/knowledge/`, calc, geom, qa, docs/, content/) | Проверено |
| Внешний пакет агента `/tmp/eskd_agent_pack/knowledge/` (tables, sources/files PDF/TXT, classics) | **Найден на VM, не входит в git tree проекта** |
| `apps/`, `packages/`, `content/vn/**` | CAD/литейных таблиц нет |

**Важно:** материалы pack **нельзя** считать «уже в проекте» до явного переноса/вендоринга в `eskd_cad/knowledge/` с provenance. Ниже для каждого источника указано: **repo** | **pack-only**.

Легенда достоверности: **CONFIRMED** · **PLAUSIBLE** · **UNVERIFIED** · **MISSING**.

---

## 1. INP-007 — профиль лопаток

### Таблица аудита

| Параметр | Результат |
|----------|-----------|
| Что требуется проверить | Можно ли восстановить гидравлический профиль лопаток КП-062215009-01 из имеющихся данных; что нужно для PASS INP-007 |
| Найденные материалы | Метод. карточка колёс/насосов; runtime призматические лопатки; TT «профиль по шаблону»; calc.md «4 лопатки» |
| Точный путь к файлу | **repo:** `eskd_cad/geom/tech_params.py` (`BladeParams`, `wheel_tech_geom`); `geom/assembly_wheel.py`; `geom/ocp_worker.py` (`radial_blade`); `qa/p4/inputs.py` (INP-007); `knowledge/calc/KP-062215009-01_calc.md`; `P3_GEOMETRY_COMPLETENESS.md`. **pack-only:** `/tmp/eskd_agent_pack/knowledge/tables/kolesa_nasosy.md`; `sources/files/Cyberleninka_nasosnoe_koleso_chugun.txt`; `patent_RU2733963_koleso.txt` |
| Страница/раздел/таблица | `kolesa_nasosy.md` §1 (особенности), §1.1 (два узла питания) — **без координат профиля** |
| Содержание источника | Метод: лопатки часто «по шаблону»; на отливке — ТТ + сечения. Нет таблиц координат, β₁/β₂, закона толщины |
| Есть ли реализация в коде | Да: 4× `radial_blade` (призма), `thickness_mm=14`, `start_angle_deg=15`, `is_hydraulic_profile=False` |
| Используется ли в runtime | Да: `wheel_tech_geom` → `metal_plus_tech_for_views` / `build_wheel_assembly` → OCP Fuse; QA INP-007 WARNING |
| Чего не хватает | Полилиния/координаты шаблона; закон толщины; углы входа/выхода; кромки; provenance толщины 14 мм; файл `kolesa_nasosy.md` **в repo**; исходный чертёж детали/шаблон |
| Достоверность вывода | **CONFIRMED** (код + отсутствие данных). Метод. текст pack — **PLAUSIBLE**, не нормативный профиль |
| Следующий шаг | Получить шаблон с чертежа детали / гидрорасчёта; не аппроксимировать произвольными кривыми. Статус: **BLOCKED** |

### Разделение слоёв

| Утверждение | Класс |
|-------------|-------|
| TT: «Лопатки 4 шт.… профиль по шаблону» | требование чертежа |
| INP-007 WARNING при `is_hydraulic_profile=False` | внутреннее правило QA |
| N=4, height=`C_H_CH` | из calc/spec |
| thickness=14, angle=15°, призмы | **инженерная модель / допущение** |
| Гидравлический профиль по `kolesa_nasosy.md` | **нет** — файл не содержит координат |

**Вывод:** восстановить профиль КП-062215009-01 по текущим данным **нельзя**. Статус направления: **BLOCKED**.

---

## 2. INP-008 — вертикальные стержневые знаки (ГОСТ 3212-92)

### Таблица аудита

| Параметр | Результат |
|----------|-----------|
| Что требуется проверить | Есть ли таблицы вертикальных знаков; можно ли подключить без смены формул `H_PRINT2` |
| Найденные материалы | Horiz JSON в repo (runtime); vert таблица в MD pack; PDF ГОСТ 3212-92; Михальцов гл.5; Василевский гл.II |
| Точный путь к файлу | **repo:** `knowledge/calc/sterzhni_horiz_syroe.json`; `calc/core_prints.py` (`load_horiz_syroe`, `check_horiz_print`); `calc/pipeline.py` (H_PRINT2 engineer); `qa/p4/inputs.py` INP-006/008; `wheel_inputs.py` `h_print2=40`. **pack-only:** `knowledge/tables/sterzhni_raschet.md` §2; `sources/files/GOST_3212-92.pdf`; `GOST_3212-92_sterzhni_section.txt`; `Mikhaltsov_2011_glava5_sterzhni.txt`; `Vasilevsky_1974_glava2_znaki_sterzhnej.txt`; `classics/STERZHNI_ISTOCHNIKI.md` |
| Страница/раздел/таблица | ГОСТ 3212-92 PDF: **с.7–8** (в pdftotext — pages 8–9): п.2.3 + **Таблица 7** — высота нижних вертикальных знаков, «не более»; п.2.3.3 верхний ≥0.5 нижнего. MD §2 = сетка Михальцов 5.2 |
| Содержание источника | Horiz: l_max по D×L (сырое). Vert: hн_max по сечению×высоте стержня; часть ячеек — диапазоны / «—» |
| Есть ли реализация в коде | Horiz — да. Vert JSON/loader/check — **нет** |
| Используется ли в runtime | Horiz → INP-006 PASS. `H_PRINT2=40` идёт в геометрию **без** table gate; INP-008 WARNING («JSON не подключена») |
| Чего не хватает | `sterzhni_vert_*.json` в repo; loader `vert_print_h_max`; входы D и **L Ст.2** (сейчас section/core_length — Ст.1); вендоринг `sterzhni_raschet.md`; политика range-ячеек |
| Достоверность вывода | Существование табл.7 в PDF — **CONFIRMED**. Поклеточная сверка MD↔PDF — **PLAUSIBLE** (OCR шумный). `H_PRINT2=40` ↔ конкретная ячейка — **UNVERIFIED** (нет L Ст.2) |
| Следующий шаг | Вендорить MD/PDF extract → JSON; check-only gate как у horiz; зафиксировать L Ст.2. Статус: **PARTIALLY_READY** |

### Подключение без смены расчётной логики

Да, **параллельный check-only**: не пересчитывать `H_PRINT2`, только STOP/WARN если `H_PRINT2 > h_max(D,L)`. Нужны новые lookup-входы для Ст.2 и решение по range/пустым ячейкам.

---

## 3. INP-009a — припуски ГОСТ 26645-85 табл.6

### Таблица аудита

| Параметр | Результат |
|----------|-----------|
| Что требуется проверить | Смысл `TABLE6_BASE=5.2`; можно ли нормативный PASS для N_TOP/BOT/FACE |
| Найденные материалы | Vendored JSON табл.6; lookup Python; calc.md; PDF/fulltext ГОСТ 26645; lookup MD |
| Точный путь к файлу | **repo:** `knowledge/calc/gost_26645_table6_full.json` (source meta: meganorm); `calc/gost26645_table6.py` (`allowance_mm`); `calc/pipeline.py` (`TABLE6_BASE`); `calc/wheel_inputs.py` (N_*=6/5/5); `qa/p4/inputs.py` INP-009a/b/c; `KP-062215009-01_calc.md` §1. **pack-only:** `sources/files/GOST_26645-85.pdf`; `GOST_26645-85_fulltext.txt`; `tables/gost_26645_table6_lookup.md`; `gost_26645_tables_5_6_excerpt.md`; `gost_26645_table5_min_pripus.json` |
| Страница/раздел/таблица | PDF ГОСТ 26645-85: примечание о допустимости **уменьшенных** припусков vs табл.6 — **с.10**; **Таблица 6** — **с.11** (pdftotext page index 11). Заголовок: «Общий припуск на сторону, мм, **не более**, для ряда припуска отливки» |
| Содержание источника | Ячейка для T∈(2.40; 2.80], Чистовая, ряд 11 → **5.2** (подтверждено `allowance_mm(2.8,"Чистовая",11)`). JSON meaning совпадает с PDF («не более») |
| Есть ли реализация в коде | Да: lookup → `TABLE6_BASE`; N_* engineer; warn если N_* < base |
| Используется ли в runtime | Да (P1 provenance + INP-004 PASS lookup; INP-009*). Геометрия использует **N_***, не TABLE6_BASE |
| Чего не хватает | Вендоринг PDF/extract в repo knowledge; нормативные правила верх/низ формы для N_TOP vs N_BOT; явное разрешение конфликта «не более» (потолок) vs pipeline floor; обоснование ряда 11 / finish |
| Достоверность вывода | Значение ячейки 5.2 и формулировка «не более» в PDF — **CONFIRMED** (pack PDF). Использование 5.2 как **нижней** границы N_* — **внутреннее правило**, **не** доказанный «shall» ГОСТ → **SOURCE_UNVERIFIED** для нормативного PASS |
| Следующий шаг | Зафиксировать в knowledge: табл.6 = max; N_* = engineer с отдельным основанием; INP-009a не PASS по `N≥base`. Статус: **PARTIALLY_READY** / для нормативного PASS — **SOURCE_UNVERIFIED** |

### Разделение

| Величина | Класс |
|----------|-------|
| `GENERAL_TOLERANCE=2.8`, lookup → 5.2 | calculated / table cell |
| `FINISH`, `ALLOWANCE_ROW=11` | engineer (+ учебный +1 в комментариях) |
| `N_TOP=6`, `N_BOT=5`, `N_FACE=5` | engineer (calc sheet) |
| `N < TABLE6_BASE → WARNING` | внутреннее правило pipeline |
| INP-009a NOT_CHECKED | корректно при отсутствии нормативного PASS |

---

## 4. GEO-002b — tol_volume пересечений

### Таблица аудита

| Параметр | Результат |
|----------|-----------|
| Что требуется проверить | Откуда 50000 / 10000 / 20000 / 100; отличие kernel tol / численной ошибки / техн. пересечения |
| Найденные материалы | Hardcode в `intersection_job`; QA GEO-002/002b; комментарии «сильно»/«небольшой»; construction offsets −0.2/+0.4 |
| Точный путь к файлу | **repo:** `geom/assembly_wheel.py` `intersection_job` (пары tol_volume); `geom/ocp_worker.py` `check_intersections` (default 500); `qa/p4/geometry.py` GEO-002b (`tol_basis=unconfirmed`); `P4_1_PLAN.md` / `P4_2_AUDIT.md`. **pack:** `STOP_GATES.md` — про calc gates, **не** mm³ пересечений OCP |
| Страница/раздел/таблица | Нет нормативной таблицы mm³ в knowledge |
| Содержание источника | Qualitative comments only |
| Есть ли реализация в коде | Да: числовой gate GEO-002; GEO-002b всегда NOT_CHECKED |
| Используется ли в runtime | Да (build stop если GEO-002 fail; на колесе PASS) |
| Чего не хватает | Методика: mm construction clearance → mm³ budget; или цель disjoint∩→0 + малый numerical tol; семантика gating (comment «overlap» vs `expect=disjoint`) |
| Достоверность вывода | Числа — **UNVERIFIED** knobs. metal∩core1≈30436 мм³ — макропересечение модели (**CONFIRMED** измерением), не OCC noise |
| Следующий шаг | Инженерное обоснование или ужесточение solids; tol не менять «на глаз». Статус: **BLOCKED** |

### Четыре понятия (не смешивать)

| Понятие | В проекте |
|---------|-----------|
| Kernel geometric tolerance | OCC defaults; Fuzzy не задан |
| Численная погрешность Boolean | ожидаемый масштаб ≪ 30k mm³ |
| Допустимое техн. пересечение | chillers `expect=overlap` min 100 |
| Запрещённое / capped | metal/core* `disjoint` + upper tol |

---

## 5. DRW-016 — ассоциация размеров ↔ OCP

### Таблица аудита

| Параметр | Результат |
|----------|-----------|
| Что требуется проверить | Цепочка Feature → OCP → projected edge/section → DIMENSION |
| Найденные материалы | `dim_map`, ViewResult/HLR/Section, assembly named solids, `_edges_of`, ViewTransform, DRW-006 ends-match precedent |
| Точный путь к файлу | **repo:** `qa/p4/dim_map.py`; `qa/p4/view_layout.py`; `qa/p4/duplicate_lines.py`; `geom/view_types.py`; `geom/ocp_worker.py` (`plane_section`, `hlr_projection`, `_edges_of`); `geom/assembly_wheel.py` (`local_bb_print_section_job`, solids); `geom/solids.py` `casting_axisymmetric_profile`; `foundry/ocp_koleso.py`; `views/transform.py`; `model/entities.py` `DimLinear` |
| Страница/раздел/таблица | n/a (архитектура кода) |
| Содержание источника | 8 feature-строк; rim_od=`ocp_bbox` (полный AA width); остальные `sheet_span`; агрегат всегда NOT_CHECKED |
| Есть ли реализация в коде | Частичная карта + честные measure_kind; **нет** dim↔edge |
| Используется ли в runtime | Да (DRW-016 NOT_CHECKED) |
| Чего не хватает | Feature-scoped solids/edge filters; поля связи на DimLinear; inverse ViewTransform check; строки для bore ID / gating dims |
| Достоверность вывода | Архитектурная готовность к поэтапной ассоциации — **CONFIRMED**. Готовых edge-links — **MISSING** |
| Следующий шаг | Пилот: `print_length` на solid `print0`; затем OD по AA edge bands. Статус: **PARTIALLY_READY** |

### По типам размеров

| Тип | OCP доступен | Измерение | Match Dim | Однозначность | Почему NOT_CHECKED |
|-----|--------------|-----------|-----------|---------------|-------------------|
| OD обода | AA section | сейчас full bbox; нужно ±C_OUT/2 edges | ⌀825 + AA | bbox≠rim-only | нет edge link |
| OD ступицы/бобышки | AA edges по z-band | не реализовано | ⌀248/⌀346 | нужен z-filter | sheet_span only |
| ID расточки | profile + core2 | нет DimLinear | — | — | вне карты |
| Высоты | AA edges / riser solid | bbox включает прибыль | 464/300/115 | нужен z-interval | sheet_span |
| L_PRINT | `print0` solid | bbox local_BB включает rim | «60» + local_BB | solid print — лучший кандидат | sheet_span |
| ЛС F | gating solids/meta | нет DIMENSION | Leaders | — | вне карты |

---

## 6. Сводная таблица

| Направление | Данные найдены | Проверены по источнику | Есть runtime | Остаточный пробел | Статус |
|-------------|----------------|------------------------|--------------|-------------------|--------|
| INP-007 | Метод. текст (pack); код призм | Метод без координат | WARNING + призмы | Шаблон/координаты/углы/толщина | **BLOCKED** |
| INP-008 | Vert табл. MD+PDF табл.7 (pack); horiz JSON (repo) | PDF с.7–8 CONFIRMED; MD↔PDF PLAUSIBLE | Horiz yes; vert no | Vert JSON + L Ст.2 + loader | **PARTIALLY_READY** |
| INP-009a | JSON+lookup (repo); PDF табл.6 с.11 (pack) | Ячейка 5.2 + «не более» CONFIRMED | Lookup + N_* | Норм. PASS / floor vs ceiling / верх-низ | **PARTIALLY_READY** / PASS→**SOURCE_UNVERIFIED** |
| GEO-002b | Hardcode tol | Нет методики | GEO-002 numeric | Обоснование mm³ | **BLOCKED** |
| DRW-016 | Архитектура OCP/views/dim_map | Ограничения A7 CONFIRMED | Карта + NOT_CHECKED | Edge/feature association | **PARTIALLY_READY** |

---

## 7. Повторы и альтернативы источников

| Тема | Repo | Pack-only (дубликат/богаче) |
|------|------|------------------------------|
| табл.6 JSON | `knowledge/calc/gost_26645_table6_full.json` | тот же JSON + PDF + lookup MD + table5 |
| стержни horiz | `sterzhni_horiz_syroe.json` | + `sterzhni_raschet.md` §1–3 |
| стержни vert | — | MD §2 + ГОСТ PDF табл.7 |
| лопатки | код + TT | `kolesa_nasosy.md` (без координат) |
| STOP_GATES | calc riser gates | `STOP_GATES.md` (не tol_volume) |

Рекомендация: перед реализацией — **вендорить** в repo минимум: GOST PDF extracts / `sterzhni_raschet.md` / `kolesa_nasosy.md` / table6 lookup MD с явным `source` provenance. Не создавать новые таблицы вместо переноса уже найденных.

---

## 8. План подэтапов реализации (только предложение)

Не объединять пять направлений.

### P4.5.1 — INP-008 vertical signs (check-only)

- **Цель:** JSON vert + lookup; INP-008 PASS/WARN/STOP без смены `H_PRINT2` формулы.  
- **Файлы:** `knowledge/calc/sterzhni_vert_lower.json` (из pack MD+PDF); `calc/core_prints.py`; `pipeline.py` provenance; `qa/p4/inputs.py`; тесты.  
- **Входы:** D и L Ст.2 (зафиксировать источник).  
- **Приёмка:** table test vs PDF табл.7 sample cells; wheel H_PRINT2=40 vs h_max; DXF неизменен.  
- **Ограничения:** не менять геометрию знака; пустые ячейки → STOP.

### P4.5.2 — INP-009 knowledge freeze

- **Цель:** вендор PDF/extract табл.6; документировать «не более»; развести floor-rule vs ГОСТ; INP-009a остаётся NOT_CHECKED или WARNING с явной семантикой.  
- **Файлы:** `knowledge/calc/*26645*`; `qa/p4/inputs.py` evidence text; тесты на ячейку 5.2.  
- **Не:** ставить нормативный PASS по `N≥5.2`.

### P4.5.3 — DRW-016 pilot `print_length`

- **Цель:** measure_kind `ocp_feature`/`ocp_section` для print solid only; агрегат всё ещё NOT_CHECKED пока не покрыты все dims.  
- **Файлы:** `dim_map.py`, `assembly_wheel.local_bb_print_section_job`, тесты.  
- **Не:** nearest-edge; не PASS агрегата.

### P4.5.4 — GEO-002b methodology

- **Цель:** документ в knowledge: либо mm³ budget от construction offsets, либо план сведения ∩→0.  
- **Не:** менять tol без утверждённой методики.

### P4.5.5 — INP-007 (после внешних данных)

- **Цель:** подключить шаблон, когда появятся координаты.  
- **Блокер:** внешние данные; до них — оставить WARNING.

---

## 9. Критерий завершения P4.5 AUDIT

| Критерий | Статус |
|----------|--------|
| Проверены материалы repo + pack | да |
| Выявлены дубликаты repo/pack | да §7 |
| Установлено runtime-подключение | да по каждому направлению |
| Реальные пробелы зафиксированы | да |
| Норматив отделён от допущений | да |
| Отчёт со ссылками на пути/страницы | да |
| Поэтапный план | да §8 |
| Код/геометрия/DXF не менялись | да |

**Главный принцип соблюдён:** сначала использовать и проверить уже имеющиеся знания (включая pack), не изобретать новые таблицы вместо них.
