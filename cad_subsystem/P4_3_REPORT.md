# P4.3 — отчёт реализации эвристик QA

**Ветка:** `cursor/p4-3-qa-heuristics-666e` ← `cursor/p4-1-quality-hardening-666e`  
**План:** [`P4_3_PLAN.md`](P4_3_PLAN.md) · аудит [`P4_2_AUDIT.md`](P4_2_AUDIT.md)  
**Объект:** КП-062215009-01

---

## 1. Какие проблемы P4.2 исправлены

| ISSUE P4.2 | Исправление P4.3 | Доказательство на колесе |
|------------|------------------|--------------------------|
| DRW-004: triangle→box; ложный full на сечении «А»; «Б» partial | Структурный `classify_closed_poly`; кластер от рамки; exclude слоя «Сечение» | letters=`['А','Б']`; excluded_cutting=4; partial=0 |
| DRW-006: HLR по имени слоя count≤4 | Match Line↔`ViewResult` HIDDEN после **явного** `ViewTransform` | 20× `hlr_coincident`, `hlr_match=True`, `matched_view=plan` |
| DRW-016: sheet без measure_kind; scale guess; без view bind | `measure_kind`; `k` из `view_layout`; окно вида | rim_od=`ocp_bbox`; 7×`sheet_span`; print_length k=2.0; агрегат NOT_CHECKED |

`annotations/datums.py` и `cutting_plane.py` **не менялись**.

---

## 2. Какие остались

| Тема | Статус | Почему |
|------|--------|--------|
| INP-009a / нормаль табл.6 | NOT_CHECKED | нет текста ГОСТ в knowledge |
| GEO-002b tol_volume | NOT_CHECKED | нет обоснования tol |
| DRW-016 агрегат / edge association | NOT_CHECKED | нет dim↔ребро BRep |
| INP-007 / INP-008 | WARNING | шаблон лопаток / JSON верт. знаков |
| INP-009b/c | WARNING | N_BOT/N_FACE < 5.2 (pipeline signal) |
| sheet_span ≠ OCP | by design | честно помечено measure_kind |

`fully_verified=False` — **намеренно**.

---

## 3. Новые правила классификации

### DRW-004
- box = axis-aligned square ~s=7; triangle = `[tip,b,a,c]` с симметрией b/c (не rectangle).
- Кандидат базы — только letter в рамке + shelf Line + datum_triangle в одном кластере.
- Буква у Line слоя «Сечение» → `excluded_cutting_letters` (не база).

### DRW-006
- `hlr_coincident` ⇔ сегмент совпадает с HIDDEN-кривой ViewResult в **sheet** coords через `ViewLayout.transform()` / `ViewTransform.P`.
- Без views / без match → `ambiguous_same_geom` → WARNING.
- Геометрия не удаляется.

### DRW-016
- Обязательные поля evidence: `measure_kind`, `view_id`, `k`, `sheet_span`, `measured_value`.
- Scale = `ViewLayout.k` only; неоднозначное окно → NOT_CHECKED.
- `sheet_span` PASS = только аннотация листа, не OCP.
- Агрегат всегда NOT_CHECKED.

### `view_layout.py`
Read-only зеркало констант `build_koleso_otlivka` (ox/oy/k); тест дрейфа `test_layout_k_matches_builder_constants`.

---

## 4. Результаты тестов

```text
unittest P0 + P1 + P2 + P3 + P4 + P4.1 + P4.3_*
→ 66 tests OK

generate_koleso_otlivka
→ checklist 10/10; DXF auditor OK; LINE=206 (без удаления)
→ P4 counts: PASS=27 FAIL=0 WARNING=4 NOT_CHECKED=3
→ fully_verified=False
```

Новые модули тестов:
- `tests/test_p4_3_datums.py` (7)
- `tests/test_p4_3_duplicates.py` (7)
- `tests/test_p4_3_dim_map.py` (8, вкл. layout drift)

---

## 5. Сравнение статусов / evidence P4.1 → P4.3

| ID | P4.1 | P4.3 | Evidence delta |
|----|------|------|----------------|
| DRW-004 | PASS letters=['А'] (ложный full на сечении) | PASS letters=['А','Б'] | full_clusters; excluded_cutting=4; partial=0 |
| DRW-006 | PASS 20 hlr по слою | PASS 20 hlr_coincident | hlr_match=True, matched_view=plan, ViewTransform |
| DRW-016 | NOT_CHECKED; 8 PASS без kind | NOT_CHECKED; 8 PASS | measure_kind ocp_bbox×1 + sheet_span×7; k/view_id |
| counts | 27/0/4/3 | **27/0/4/3** | те же счётчики; качество evidence выше |
| fully_verified | False | False | без искусственного PASS |

### DRW-016 measure_kind (факт)

| feature | status | measure_kind | k | view |
|---------|--------|--------------|---|------|
| rim_od | PASS | **ocp_bbox** | 5 | AA |
| boss_od … channel_height | PASS | **sheet_span** | 5 | AA |
| print_length | PASS | **sheet_span** | **2.0** | local_BB |

---

## 6. Доказательство неизменности P0–P3

- Регрессия P0–P3 зелёная; golden: TABLE6_BASE=5.2, C_HUB=248, H_BODY=464, L_PRINT=60, H_PRINT2=40, ЛС 12:14.4:16.8.
- `tol_volume` metal∩core1 = 5e4 не менялся; GEO-002 PASS + GEO-002b NOT_CHECKED.
- Foundry / annotations / export / calc pipeline — без правок (только `qa/p4/*` + тесты + MD).
- DXF entity counts стабильны (DIMENSION=10, HATCH=2, LINE=206).

---

## 7. Изменённые файлы

**Новые:** `view_layout.py`; `tests/test_p4_3_{datums,duplicates,dim_map}.py`; `P4_3_REPORT.md`  
**Переписаны/расширены:** `datum_detect.py`, `duplicate_lines.py`, `dim_map.py`  
**Правки:** `drawing.py`, `runner.py`, `test_p4_1_quality.py`, `P4_3_PLAN.md`, `P4_QUALITY.md`

---

## 8. Вердикт

P4.3 закрывает три ISSUE аудита P4.2 на уровне эвристик QA.  
Чертёж **не** объявляется полностью проверенным (`fully_verified=False`).  
Следующие этапы — инженерные данные (ГОСТ/tol/знаки/шаблон) и association dim↔edge.
