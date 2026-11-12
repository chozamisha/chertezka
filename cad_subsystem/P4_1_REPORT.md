# P4.1 — отчёт реализации

**Ветка:** `cursor/p4-1-quality-hardening-666e`  
**База:** `cursor/p4-quality-control-666e`  
**Объект:** КП-062215009-01  
**План:** [`P4_1_PLAN.md`](P4_1_PLAN.md) · аудит [`P4_AUDIT.md`](P4_AUDIT.md)

---

## 1. Что изменено

| Задача | Изменение |
|--------|-----------|
| **1 INP-009** | Монолит заменён на `INP-009a/b/c` (N_TOP/N_BOT/N_FACE) с accepted, TABLE6_BASE, unit, provenance, relation, `gost_direction=unconfirmed`. Прочие pipeline warnings → `INP-009x` (на колесе нет). |
| **2 DRW-006** | Классификатор `duplicate_lines.py`: `hlr_coincident` / `drawing_duplicate` / `ambiguous_same_geom` + диагностика в evidence. |
| **3 GEO-002** | Числовой PASS сохранён; добавлен `GEO-002b` NOT_CHECKED (основание tol); volumes в evidence (mm³). |
| **4 DRW-004** | Паттерн `add_datum` через `datum_detect.py`; без паттерна — NOT_CHECKED (не любой Text). |
| **5 DRW-016** | Карта `dim_map.py` (8 feature); агрегат **всегда NOT_CHECKED**. |
| Док/тесты | `P4_QUALITY.md` (+P4.1), `tests/test_p4_1_quality.py`, правки `test_p4_quality.py` |

### Изменённые / новые файлы

**Новые:** `qa/p4/duplicate_lines.py`, `datum_detect.py`, `dim_map.py`, `tests/test_p4_1_quality.py`, `P4_1_PLAN.md`, `P4_1_REPORT.md`  
**Изменены:** `qa/p4/inputs.py`, `geometry.py`, `drawing.py`, `runner.py`, `tests/test_p4_quality.py`, `P4_QUALITY.md`

---

## 2. Что не изменено

- P1 pipeline / формулы / `N_TOP=6`, `N_BOT=5`, `N_FACE=5`, `TABLE6_BASE=5.2`
- `H_PRINT2=40`, `L_PRINT=60`, `H_BODY=464`, ЛС 12 : 14.4 : 16.8
- P2/P3 геометрия, `tol_volume` в `intersection_job` (в т.ч. metal∩core1 = 5e4)
- `annotations/datums.py`, экспорт DXF/PDF, legacy checklist
- Направление сравнения pipeline `N < base`
- Семантика `fully_verified = ¬FAIL ∧ ¬NOT_CHECKED`

---

## 3. Какие проверки стали точнее

| ID | Было | Стало | Эффект |
|----|------|-------|--------|
| INP-009* | 1 WARNING на все warnings | a NOT_CHECKED; b/c WARNING | нет ложного PASS по N_TOP≥base «как ГОСТ» |
| DRW-006 | WARNING на 20 HLR | PASS + evidence hlr_coincident=20 | нет ложного WARNING на шум проекции |
| GEO-002 | PASS без вопроса о tol | PASS + **GEO-002b NOT_CHECKED** | числовой ok ≠ обоснованный допуск |
| DRW-004 | PASS по любой букве | PASS по паттерну базы | нет ложного PASS от штампа У/В/Н |
| DRW-016 | пустой NOT_CHECKED | карта 8 feature (все PASS по листу) + агрегат NOT_CHECKED | прозрачность без ложного полного PASS |

---

## 4. Результаты прогона КП-062215009-01

```
counts: PASS=27, FAIL=0, WARNING=4, NOT_CHECKED=3
fully_verified: False
```

### WARNING
- INP-007 — лопатки-призмы  
- INP-008 — нет JSON верт. знаков  
- INP-009b — N_BOT=5.0 < 5.2  
- INP-009c — N_FACE=5.0 < 5.2  

### NOT_CHECKED
- INP-009a — N_TOP=6.0 ≥ 5.2 численно; нормативное PASS запрещено  
- GEO-002b — основание tol_volume  
- DRW-016 — нет association DIMENSION↔ребро OCP  

### DRW-016 feature-строки (все PASS по span×scale / OCP bbox width для C_OUT)

| feature_id | param | status | measured |
|------------|-------|--------|----------|
| rim_od | C_OUT | PASS | 825 |
| boss_od | C_BOSS | PASS | 346 |
| hub_od | C_HUB | PASS | 248 |
| body_height | H_BODY | PASS | 464 |
| riser_od | D_RISER | PASS | 300 |
| riser_height | H_RISER | PASS | 300 |
| channel_height | C_H_CH | PASS | 115 |
| print_length | L_PRINT | PASS | 60 |

Агрегат DRW-016 = **NOT_CHECKED** (решение согласования §3).

### GEO-002 evidence (фрагмент)
- metal∩core1 ≈ 30436 mm³, tol=50000 mm³, unit=mm³, ok=True  
- metal ≈ 8.05×10⁷ mm³ → ∩ ≈ 0.038 %  
- `tol_basis=unconfirmed` → GEO-002b NOT_CHECKED  

---

## 5. Какие проблемы остались

1. Направление сравнения N_* vs табл.6 не подтверждено текстом ГОСТ в knowledge.  
2. `tol_volume` без инженерного обоснования в knowledge.  
3. Нет association DimLinear ↔ ребро BRep.  
4. INP-008: нет JSON/`sterzhni_raschet.md` для H_PRINT2.  
5. INP-007: нет гидравлического шаблона лопаток.  
6. Детектор баз нашёл полным паттерном букву «А» (Б может быть partial — не блокирует PASS при ≥1).

---

## 6. Какие проверки всё ещё NOT_CHECKED

- INP-009a  
- GEO-002b  
- DRW-016 (агрегат)  

`fully_verified` **намеренно False** — не поднимался искусственно.

---

## 7. Данные для следующих этапов

| Нужно | Зачем |
|-------|-------|
| Текст/выписка ГОСТ 26645-85 табл.6 (название, «не более»/назначение) | закрыть нормативный статус INP-009* |
| Обоснование tol_volume (или формула от габарита/допуска сетки) | GEO-002b → PASS/WARNING с основанием |
| Семантическая привязка dim→edge/feature_id в модели | DRW-016 агрегат |
| JSON верт. знаков ГОСТ 3212 (+ файл sterzhni_raschet) | INP-008 |
| Шаблон лопатки | INP-007 |

---

## 8. Регрессия

```bash
PYTHONPATH=. python3 -m unittest \
  tests.test_p0_parity tests.test_p1_calc_integration \
  tests.test_p2_ocp_geometry tests.test_p3_geometry \
  tests.test_p4_quality tests.test_p4_1_quality -v
# → 44 tests OK

PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
# → DXF/PDF + P4_quality.md|.json; checklist 10/10; auditor OK
```

Расчётные golden-значения совпали с P0/P1.
