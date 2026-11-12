# P3 — полнота технологической геометрии

План: [`P3_PLAN.md`](P3_PLAN.md).  
Архитектура OCP: [`P2_GEOMETRY.md`](P2_GEOMETRY.md).  
P1 calc **не изменялся**.

Поток:

```
CastingSpec + TechGeomParams
  → assembly_wheel (декларации тел)
  → ocp_worker (Cut/Fuse/HLR/Section/Common)
  → ViewResult → DrawingDocument → DXF/PDF
  → intersection QA
```

**P3 не объявляется «полностью завершённым»** только из‑за успешного DXF: ниже — честная классификация.

---

## 1. Полностью реализованные (OCP + тесты)

| Элемент | OCP-операции | Подтверждение |
|---------|--------------|---------------|
| Полость канала в теле | `BRepAlgoAPI_Cut` annulus | `channel_cut` в meta; metal∩core1 в tol |
| Ст.2 (отверстие + нижний знак) | Cylinder fuse | `metal∩core2` volume=0 |
| Прибыль: шейка + тело | `riser_neck_fillet` (Cylinder fuse + Fillet) | А-А height≥700; сечение |
| Холодильники Хол.1 / Хол.2 | Box + rot_z; overlap с металлом | intersection `expect=overlap` OK |
| Местное Б-Б знака Ст.1 | `plane_section` тела знака+обода | `local_BB` real_ocp; label «Б-Б … OCP» |
| Intersection QA | `BRepAlgoAPI_Common` + volume | `run_wheel_intersection_qa` ok=True |
| Проверка видов | HLR / Section + bbox | `assert_wheel_views_ok` |

Тесты: `tests/test_p3_geometry.py`, регрессия P2/P1/P0.

---

## 2. Реализованные частично

| Элемент | Что реально в OCP | Чего не хватает / ограничение |
|---------|-------------------|-------------------------------|
| **Лопатки** | 4× `radial_blade` Fuse в канал (призмы thickness=14 мм) | **Нет полилинии шаблона** — не гидравлический профиль (`is_hydraulic_profile=False`). Толщина — engineer. |
| **Ст.1** | Annulus канала − лопатки + box-знаки L_PRINT | Ширина знака 50 мм — с чертежа, не из ГОСТ-таблицы ячейкой |
| **ЛС** | Стояк (⌀ из Fст), шлаковик, 2 питателя из Fп/Fшл/Fст P1 | Траектория в опоке — engineer layout; не полная 3D-сеть с чашей |
| **Галтель шейки** | `BRepFilletAPI_MakeFillet` при успехе | R=8 engineer/legacy; при сбое fillet — стык без галтели (без silent fake) |
| **План** | HLR металла с лопатками | Контуры знаков/ЛС на плане ещё **дублируются** 2D-схемой (параметры те же) |

---

## 3. Условные (на листе, не выдаются за OCP-сечение)

| Элемент | Комментарий |
|---------|-------------|
| Слой «Припуск» (контур детали) | Тонкие линии оформления |
| Выноски / МФ / базы | Аннотации |
| CIRCLE стояка на плане | Схематическая привязка рядом с OCP-ЛС |
| 2D-прямоугольники знаков на плане | Согласованы с L_PRINT, но не HLR стержня |

---

## 4. Не реализованные

| Элемент | Причина |
|---------|---------|
| Гидравлический профиль лопаток | Нет координат шаблона во входе/calc |
| Полный HLR стержней/ЛС как отдельных видов | Сделаны тела + QA; отдельный вид стержня не выведен |
| CIRCLE-fitting HLR | Полилинии |
| Offset припусков OCP в чертеже | `engines/occ_offset` не вшит |
| Внутренние холодильники сложных форм | Только наружные бруски по a из calc |

### Недостающие данные (для полной лопатки)

1. Полилиния профиля лопатки (шаблон) в мм  
2. Закон толщины / углы входа и выхода  
3. Положение входной/выходной кромки по радиусу  

Без этого P3 строит **призмы** и явно пишет это в `TechGeomParams.notes` / отчёт.

---

## 5. Проверки P3

| Проверка | Статус |
|----------|--------|
| metal ∩ core1 ≈ disjoint (tol) | OK |
| metal ∩ core2 disjoint | OK |
| gating ∩ core1 disjoint | OK (шлак не пересекает знак) |
| metal ∩ холодильники overlap | OK |
| Геометрия ≡ параметрам (L_PRINT на Б-Б, ⌀825 на А-А) | OK |
| Сечение через техэлементы (Б-Б знак, А-А прибыль) | OK |
| DXF/PDF + checklist 10/10 | OK (не единственный критерий) |

---

## 6. Команды

```bash
cd cad_subsystem
PYTHONPATH=. python3 -m unittest tests.test_p3_geometry tests.test_p2_ocp_geometry -v
PYTHONPATH=. python3 -m examples.generate_koleso_otlivka
```

Примеры: `out/KP-062215009-01_Otlivka.dxf` / `.pdf`.

---

## 7. Модули P3

- `eskd_cad/geom/tech_params.py` — TechGeomParams / MissingTechDataError  
- `eskd_cad/geom/assembly_wheel.py` — сборка тел и intersection job  
- `eskd_cad/geom/ocp_worker.py` — blade, annulus, riser_neck_fillet, assembly, Common  
- `eskd_cad/foundry/ocp_koleso.py` — виды + local BB + QA  
- `tests/test_p3_geometry.py`
