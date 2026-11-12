# P4 — инженерный контроль качества чертежа

План: [`P4_PLAN.md`](P4_PLAN.md).  
P4.1: [`P4_1_PLAN.md`](P4_1_PLAN.md) / [`P4_1_REPORT.md`](P4_1_REPORT.md).  
P4.2 аудит: [`P4_2_AUDIT.md`](P4_2_AUDIT.md).  
P4.3 эвристики: [`P4_3_PLAN.md`](P4_3_PLAN.md) / [`P4_3_REPORT.md`](P4_3_REPORT.md).  
P4.4 аудит: [`P4_4_AUDIT.md`](P4_4_AUDIT.md).  
P4.3.1 hardening: [`P4_3_1_PLAN.md`](P4_3_1_PLAN.md) / [`P4_3_1_REPORT.md`](P4_3_1_REPORT.md).  
P1/P2/P3 **не переписывались**. Расчётные значения не менялись.

## Архитектура

```
CastingSpec + CalcResult + TechGeomParams + DrawingDocument
        │
        ▼
  eskd_cad/qa/p4/
    inputs.py    → INP-*
    geometry.py  → GEO-*  (OCP Common / volume / views)
    drawing.py   → DRW-*  (виды, ЕСКД-основания)
    runner.py    → QualityReport → MD/JSON
```

Статусы: **PASS | FAIL | WARNING | NOT_CHECKED**.  
`fully_verified = ¬FAIL ∧ ¬NOT_CHECKED`.  
**NOT_CHECKED никогда не считается PASS.**

Legacy checklist (`quality_checklist.py`) сохранён как поверхностный слой; P4 — инженерный.

---

## Нормативные основания (без выдуманных пунктов)

| Проверки | Источник | Как обозначено |
|----------|----------|----------------|
| INP-004 | ГОСТ 26645-85 табл.6 | lookup P1 |
| INP-009a/b/c | табл.6 value via P1; направление сравнения | **внутреннее правило pipeline**; не PASS «по ГОСТ» (P4.1) |
| GEO-002b | основание tol_volume | NOT_CHECKED до подтверждения (P4.1) |
| INP-006, INP-008 | ГОСТ 3212-92 | JSON гориз. / верт. markdown |
| DRW-001, DRW-002 | ГОСТ 2.305 | обозначения разрезов |
| DRW-003, DRW-011 | ГОСТ 2.303 | линии / слои |
| DRW-004 | ГОСТ 2.308 | базы (упрощ. реализация) |
| DRW-005, DRW-016 | ГОСТ 2.307 | размеры |
| DRW-007 | ГОСТ 2.306 | штриховка (факт наличия) |
| DRW-008, DRW-012 | ГОСТ 3.1125-88 | графика отливки (gost_cards) |
| DRW-009 | ГОСТ 2.104 | основная надпись |
| DRW-010 | ГОСТ 26645 / 3212 в ТТ | учебная практика calc |
| DRW-013 | ГОСТ 2.301 / 2.302 | формат / масштаб |
| GEO-*, пересечения, галтель, STOP | **внутреннее инженерное правило** | не выдаётся за пункт ГОСТ |
| pribyli_sheyka / STOP_GATES G3 | справочник / внутреннее | не ГОСТ |

Если основание не найдено в knowledge — только «внутреннее инженерное правило».

---

## Пример прогона (колесо КП-062215009-01)

```bash
cd cad_subsystem
PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
# → out/KP-062215009-01_P4_quality.md|.json
```

Счётчики после **P4.1** — см. актуальный `out/KP-062215009-01_P4_quality.md` и `P4_1_REPORT.md`.  
Исторически P4 давал ~26 PASS / 4 WARNING / 1 NOT_CHECKED; P4.1 дробит проверки и добавляет NOT_CHECKED (норматив припусков, tol, карта размеров).

### WARNING (пример, P4.1)

- INP-007 — лопатки не гидравлический профиль  
- INP-008 — H_PRINT2 без JSON верт. таблицы  
- INP-009b / INP-009c — N_BOT / N_FACE < TABLE6_BASE (сигнал pipeline, не подтверждённый ГОСТ)

### NOT_CHECKED (P4.1)

- **INP-009a** — N_TOP ≥ base численно, но нормативное PASS запрещено  
- **GEO-002b** — основание `tol_volume` не подтверждено  
- **DRW-016** — агрегат: нет association DIMENSION↔ребро OCP (даже при PASS feature-строк)

`fully_verified` остаётся **False**. Историческая семантика P4 (`NOT_CHECKED ≠ PASS`) сохранена.

### Условная геометрия (в отчёте)

- слой «Припуск» без OCP-offset  
- 2D-схема знаков/ЛС на плане  
- выноски / МФ  

### Неподтверждённые допущения

- толщина лопаток 14 мм (engineer)  
- ширина знака 50 мм  
- H_PRINT2 без runtime lookup верт. табл.  

Полный перечень — в `out/KP-062215009-01_P4_quality.md`.

---

## Модули

| Файл | Роль |
|------|------|
| `eskd_cad/qa/p4/status.py` | CheckStatus, QualityReport |
| `eskd_cad/qa/p4/inputs.py` | INP-* (+ P4.1 INP-009a/b/c) |
| `eskd_cad/qa/p4/geometry.py` | GEO-* (+ GEO-002b) |
| `eskd_cad/qa/p4/drawing.py` | DRW-* |
| `eskd_cad/qa/p4/duplicate_lines.py` | DRW-006 (+ P4.3 HLR-match) |
| `eskd_cad/qa/p4/datum_detect.py` | DRW-004 (+ P4.3 кластер) |
| `eskd_cad/qa/p4/dim_map.py` | DRW-016 (+ P4.3 measure_kind) |
| `eskd_cad/qa/p4/view_layout.py` | P4.3 окна видов / k |
| `eskd_cad/qa/p4/runner.py` | оркестрация + запись отчёта |
| `tests/test_p4_quality.py` | семантика статусов P4 |
| `tests/test_p4_1_quality.py` | регрессия P4.1 |
| `tests/test_p4_3_*.py` | эвристики P4.3 |

---

## Ограничения P4

1. Нет автоматической привязки размер↔ребро 3D (NOT_CHECKED).  
2. Штриховка проверяется наличием Hatch, не соответствием ГОСТ-таблице материалов построчно.  
3. Полный текст ГОСТ не парсится — только известные ссылки из knowledge/gost_cards и кода.  
4. Checklist из 10 пунктов остаётся; P4 его не подменяет подсчётом сущностей как «инженерной» истиной.
