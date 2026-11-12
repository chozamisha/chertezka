# chertezka

Репозиторий ЕСКД-чертежей и CAD-пайплайна (без гида/бота).

## Содержимое

| Путь | Назначение |
|------|------------|
| `cad_subsystem/` | Пайплайн отливки (CastingSpec / колесо) + MVP **деталь→отливка** |
| `drawings/` | Комплект «Корпус» ПП-062215009 (DXF/PDF + `cad.py`) |
| `cad_work/` | Рабочий стек ЕСКД + `qa_check.py` |
| `.cursor/rules/eskd.mdc` | Правило оформления чертежей |

## Деталь → отливка

```bash
cd cad_subsystem
python3 -m examples.part_dxf_to_casting \
  ../drawings/ПП-062215009-00_Korpus.dxf \
  --out out/part_to_casting --profile korpus --render
```

Подробности: [`cad_subsystem/PART_TO_CASTING.md`](cad_subsystem/PART_TO_CASTING.md).
