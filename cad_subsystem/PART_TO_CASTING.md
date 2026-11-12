# Деталь → отливка

Пайплайн для профилей:

- **korpus** — полое тело вращения с двумя фланцами (ПП-062215009 и варианты).
- **koleso** — рабочее колесо (КП-062215009-01); геометрия из PartSpec JSON,
  расчёт/рендер через `eskd_cad.calc` + `eskd_cad.foundry` (не `cad_work/draw_otl`).

```
исходный чертёж  →  PartSpec  →  decisions  →  CastingDraft  →  лист PDF
   DXF / JSON         JSON         JSON         JSON       korpus: cad_work
                                                       koleso: eskd_cad.foundry
```

Для korpus канонический рендер — `cad_work/` (`qa_check` + `qa_extra`).  
`drawings/` — архив эталонного комплекта Корпуса, не точка входа.

## Быстрый старт

```bash
cd cad_subsystem
pip install -r requirements.txt   # ezdxf shapely numpy matplotlib pillow
python3 -m examples.part_dxf_to_casting \
    ../drawings/ПП-062215009-00_Korpus.dxf \
    --out out/part_to_casting --render --confirm-all
```

Без `--confirm-all` PDF финальным не считается: в `decisions.json` остаются
неподтверждённые припуски, уклоны, класс точности и т.п.

## Входы

| Вход | Когда |
|------|--------|
| DXF детали | Есть векторный чертёж. Геометрия даёт роли размеров, надписи — значения. |
| PartSpec JSON | Исходник — картинка/PDF: агент читает глазами и заполняет JSON по шаблону. |

Шаблон: `examples/part_spec.template.json`.
Решения: `examples/decisions.template.json` (или то, что пишет `run` в `decisions.json`).

## Что читается из DXF

- Основная надпись (форма 1 ГОСТ 2.104): обозначение, имя, материал, масса, масштаб, Разраб./Пров./орг.
- Разрез: заштрихованный контур → высота, фланцы, отверстия, стенка.
- Вид сверху: концентрические окружности, отверстия по PCD, рёбра.
- Размерные числа привязываются к измеренному (±допуск), а не к эталону «вариант 10».
- Чего нет на чертеже — в `questions`, без тихой подстановки.

## Решения (decisions)

Всё, чего нет на детали: припуски, уклоны, класс точности, термообработка,
масса отливки, угол рёбер относительно секущей. У каждого поля:
`value`, `source`, `confirmed`, `note`.

Пока есть неподтверждённые — статус `draft`, финальный PDF не пишется
(есть `--force-render` для отладки).

Масса отливки по умолчанию: масса детали из штампа + объём припусков +
незалитые отверстия × плотность СЧ. Можно задать `mass_cast_kg` явно.

## Выход

В `--out`:

- `part_spec.json` — прочитанная деталь
- `decisions.json` — технологические решения
- `casting_draft.json` — параметры листа
- `{обозначение}-01.pdf/.png/.dxf` — лист (PDF только при чистой QA и confirmed)

Автопроверка листа: `qa_check.review` + `qa_extra.review` (касание текста и линий).
Замечания самой рамки `cad.py` (графа «Изм.» через фамилии и т.п.) в `qa_extra.tool_defects`
и в сдачу листа не входят: правило запрещает переписывать `cad.py`.

## Колесо с загруженного чертежа

Исходник: `inbox/examples/koleso_rabochee_KP-062215009-01.jpg`.  
Снятый PartSpec: `examples/koleso_part_spec.json`.

```bash
python3 -m examples.part_dxf_to_casting examples/koleso_part_spec.json \
  --profile koleso --out out/koleso_from_source --render --confirm-all
```

Обозначение детали и отливки совпадают (`КП-062215009-01`). Припуски и масса
отливки 420 кг — из листа расчёта; на исходнике проставлены чистовые размеры и Ra 2,5.

## Ограничения

- DXF→PartSpec автоматом только для korpus; koleso — через PartSpec JSON.
- МЛУ (-02) из пайплайна пока не собирается.
- Для korpus таблиц ГОСТ 26645 в репо нет: припуски из эталона, пока не подтвердят.
- OCR растра нет: PNG/PDF детали → PartSpec руками/агентом.
