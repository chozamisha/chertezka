# chertezka

Репозиторий ЕСКД-чертежей и CAD-пайплайна (без гида/бота).

## Содержимое

| Путь | Назначение |
|------|------------|
| `cad_subsystem/` | Пайплайн **деталь→отливка** + CastingSpec / колесо |
| `cad_work/` | Канонический рендер ЕСКД (`cad.py`, `draw_otl.py`, `qa_check`) |
| `drawings/` | Архив эталонного комплекта «Корпус» ПП-062215009 |
| `.cursor/rules/eskd.mdc` | Оформление листов |
| `.cursor/rules/part-to-casting.mdc` | Как гонять деталь → отливку |

## Деталь → отливка

```bash
cd cad_subsystem
python3 -m examples.part_dxf_to_casting \
  ../drawings/ПП-062215009-00_Korpus.dxf \
  --out out/part_to_casting --render --confirm-all
```

Без `--confirm-all` лист остаётся черновиком, пока инженер не подтвердит припуски/уклоны.
Подробности: [`cad_subsystem/PART_TO_CASTING.md`](cad_subsystem/PART_TO_CASTING.md).
