# P2 — OCP-проекции и сечения

## 1. Технический план и изменения архитектуры

### Цель

Заменить условные 2D-заготовки контуров видов/сечений на **реальные** операции OpenCascade (OCP 8): HLR-проекции и пересечения секущих плоскостей с BRep-телом.

### Сохраняемый поток

```
P1 calc → CastingSpec → QA(spec)
              ↓
     solid declaration (JSON)
              ↓
     python-ocp8 / ocp_worker   ← HLRBRep / BRepAlgoAPI_Section
              ↓
     ViewResult (visible|hidden|outline|section|axis)
              ↓
     emit → DrawingDocument (слои ЕСКД)
              ↓
     eskd_cad export → DXF / PDF
```

### Архитектурные решения

| Решение | Почему |
|---------|--------|
| OCP только в `venv-ocp8` через subprocess | Не смешивать OCP8 с system Python / ezdxf |
| Декларативное тело (`kind` + params), не импорт OCP в foundry | Детали разной формы: `box_with_bore`, `flange`, `revolve_profile` |
| `ViewResult` + provenance `meta.real_ocp=True` | Нельзя выдать условный 2D за «реальное сечение» |
| Legacy `draw_section_aa` / `draw_plan` / `draw_section_bb_transverse` сохранены | `use_ocp=False` — запасной путь; legacy не удалён |
| P1 calc не трогаем | CastingSpec совместим |

### Модули

- `eskd_cad/geom/ocp_worker.py` — BRep build / HLR / Section (только OCP8)
- `eskd_cad/geom/ocp_bridge.py` — system → subprocess
- `eskd_cad/geom/solids.py` — декларации тел, в т.ч. из CastingSpec
- `eskd_cad/geom/emit.py` — кривые → Line/Polyline на слоях
- `eskd_cad/geom/qa_views.py` — проверка ViewResult
- `eskd_cad/foundry/ocp_koleso.py` — подключение к колесу
- `engines/occ_bridge.py` — прежний offset-мост (vendored)

---

## 2. Какие геометрические операции реализованы

| Операция | API OCP | Выход |
|----------|---------|--------|
| Построение тела | `BRepPrimAPI_MakeBox/Cylinder/Revol`, `Cut`/`Fuse` | TopoDS solid |
| Ортогональная проекция | `HLRBRep_Algo` + `HLRBRep_HLRToShape` | visible / hidden / outline polylines |
| Сечение плоскостью | `BRepAlgoAPI_Section` + face of `gp_Pln` | section edge polylines в базисе плоскости |
| Дискретизация рёбер | `GCPnts_QuasiUniformDeflection` | точки → 2D |
| Оси | задаются в job (`axes_2d`) | слой «Осевая» |
| Штриховка из сечения | shapely `polygonize` по section-рёбрам (если кольца склеились) | Hatch |

---

## 3. Что реально выполняется через OCP

Подтверждено `meta.real_ocp=True` и `engine=ocp8`:

1. **Прототип `box_with_bore`**: HLR front (`look=-Y`), section `Y=0`.
2. **Прототип `flange`**: HLR plan (`look=+Z`), section `Z=mid`.
3. **Колесо (осесимметричное revolve CastingSpec + цилиндр прибыли)**:
   - **А-А**: `plane_section`, normal=`+Y`, u=`+X`, v=`+Z` → меридиональное сечение тела+прибыли.
   - **План**: `hlr_projection`, look=`+Z`.
   - **В-В**: `plane_section` на середине канала (`z = (Y_DISK_LO_TOP+Y_DISK_UP_BOT)/2`).

Габарит А-А: ширина ≈ **825** мм (= C_OUT), высота ≈ тело+прибыль (**764**).

---

## 4. Виды и сечения

| Вид | Источник контура | Подпись на листе |
|-----|------------------|------------------|
| Продольный разрез | OCP Section | «А-А (OCP)» |
| Вид сверху | OCP HLR | «Вид сверху (OCP HLR)» |
| Поперечный разрез | OCP Section | «В-В (OCP)» |
| Местный разрез знака Ст.1 | оформление (не тело) | «Б-Б (знак Ст.1)» |

Слои/размеры/выноски/штамп/DXF DIMENSION+HATCH — прежняя система `eskd_cad`.

---

## 5. Что пока остаётся условным (честно)

| Элемент | Статус |
|---------|--------|
| Лопатки на плане | условные hidden-полилинии (нет в осесимм. теле) |
| Знаки стержней Ст.1 / Ст.2 | оформление по CastingSpec, не BRep знаков |
| Холодильники, ЛС на плане | условная схема |
| Контур детали / припуски (слой «Припуск») | тонкие линии оформления |
| Местный разрез Б-Б знака | 2D-оформление |
| Шейка прибыли (галтель) | в теле — упрощённый цилиндр D_RISER, без галтели |
| Неосесимметричные полости | не моделируются в P2 |
| Растровые изображения | **не используются** |

**Не утверждается**, что лопатки/знаки/ЛС получены сечением OCP — только контуры осесимметричного металла и прибыли.

---

## 6. Ограничения

- Тело колеса = **revolve** меридионального профиля CastingSpec (+ цилиндр прибыли), не полный CAD с лопатками.
- HLR отдаёт дискретизированные полилинии, не нативные CIRCLE (на плане круги — кусочно-линейные).
- `polygonize` штриховки может дать 0 колец на сложных сечениях — тогда Hatch только из местного Б-Б / удачных колец.
- Требуется `~/.local/cad/venv-ocp8` (`python-ocp8`). Без него — `use_ocp=False` (legacy 2D).
- Offset припусков через `engines/occ_offset` в поток чертежа колеса пока не вшит (доступен отдельно).

---

## 7. Результаты тестов

```bash
cd cad_subsystem
PYTHONPATH=. python3 -m examples.test_p2_ocp_prototype
PYTHONPATH=. python3 -m unittest tests.test_p2_ocp_geometry tests.test_p1_calc_integration tests.test_p0_parity -v
PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
```

| Проверка | Результат |
|----------|-----------|
| Прототип box/flange HLR+Section | OK, `real_ocp` |
| QA ViewResult | OK |
| Колесо А-А width ≈ 825 | OK |
| `use_ocp=True` vs legacy | оба строят документ |
| P0 + P1 регрессия | OK (28 tests) |
| Generate колеса, checklist 10/10 | OK |
| DXF auditor / DIMENSION / HATCH / слои | OK |

---

## 8. Примеры DXF/PDF

| Файл | Содержание |
|------|------------|
| `out/P2_ocp_prototype.dxf` / `.pdf` | тестовые тела, подписи HLR/Section |
| `out/P2_prototype_report.json` | meta операций |
| `out/KP-062215009-01_Otlivka.dxf` / `.pdf` | колесо: OCP-контуры + оформление |

---

## 9. Дальше (не P2)

- Полное тело с лопатками / знаками как BRep
- CIRCLE-fitting для HLR окружностей
- Section faces → гарантированная штриховка
- Подключение `occ_offset` к слою припусков
