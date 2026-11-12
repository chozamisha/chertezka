# P0 — унификация контуров

## Схема

```
koleso_data.py  (ЕДИНСТВЕННЫЙ источник чисел)
        │
        ▼
  CastingSpec  ←── load_koleso_spec() + validate_derived/compare
        │
        ▼
  registry.build_drawing(spec)  →  koleso builder
        │
        ▼
  DrawingDocument
        │
   ┌────┴────┐
   ▼         ▼
 DXF       PDF     ← основной путь (eskd_cad)

Legacy (резерв): tool/cad_work/draw_koleso_otl.py + cad.py
  import koleso_data  → SHIM → тот же канон
```

## Не сделано в P0 (намеренно)

- Runtime-расчёт табл.6 / F / стержней → **сделано в P1** (`P1_INTEGRATION.md`)
- OCP-сечения вместо 2D-заготовок → **сделано в P2** (`P2_GEOMETRY.md`; legacy 2D сохранён)
- OCR входа детали (P3)
- Удаление legacy (запрещено)
