# Чертежи «Корпус» вариант 10 (СЧ15)

Основа оформления — `cad.py` из образца ЕСКД (рамка, штамп формы 1, линии, размеры, шрифт OpenGost Type B).

## Сборка

```bash
python3 draw_otl.py   # Лист 1 — Корпус. Отливка
python3 draw_mlu.py   # Лист 2 — Корпус. Элементы литейной формы
python3 qa_crops.py   # кропы для самопроверки → /opt/cursor/artifacts/
```

## Выходные файлы

- `ПП-062215009-01_Korpus_Otlivka.pdf` / `.png` / `.dxf`
- `ПП-062215009-02_Korpus_MLU.pdf` / `.png` / `.dxf`

Шрифт: `fonts/OpenGostTypeB-Regular.ttf`  
Данные: `korpus_data.py`  
Чек-лист: `checklist.md`
