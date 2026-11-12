# Деталь → отливка (MVP)

Цель: **загрузить чертёж детали → получить чертёж отливки**.

## Поток

```
DXF детали (или PartSpec JSON)
        │
        ▼
  extract readings (TEXT/⌀)
        │
        ▼
     PartSpec          ← подтверждение вопросов (разъём, обработка, материал)
        │
        ▼
   CastingDraft        ← припуски / уклоны / ЛС (профиль)
        │
        ▼
  JSON + (опц.) PDF/DXF отливки через drawings/draw_otl.py
```

Сейчас реализован профиль **`korpus`** (ПП-062215009, вариант 10).  
Колесо по-прежнему через `CastingSpec` / `examples.generate_koleso_otlivka` — отдельный контур.

## Команда

```bash
cd cad_subsystem
python3 -m examples.part_dxf_to_casting \
  ../drawings/ПП-062215009-00_Korpus.dxf \
  --out out/part_to_casting --profile korpus --render
```

Без `--render` пишутся только:

- `part_spec.json` — что снято с детали + `questions`
- `casting_draft.json` — параметры отливки + provenance

## Ограничения MVP

1. Вход — **DXF** (не PDF). PDF/скан → OCR позже, отдельный venv.
2. Семантика размеров завязана на профиль `korpus` (сопоставление ⌀120/190/200/300…).
3. При неполном разборе для обозначения `ПП-062215009-*` допускается дозаполнение эталоном (`allow_golden_fill`).
4. Рендер листа идёт существующим `drawings/draw_otl.py` + OpenGost/`cad.py`, не через OCP-колесо.
5. Перед сдачей — `questions` в JSON и правило `.cursor/rules/eskd.mdc` / `qa_check.py`.

## Тест

```bash
cd cad_subsystem
python3 -m unittest tests.test_part_to_casting_korpus -v
```
