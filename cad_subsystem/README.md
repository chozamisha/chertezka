# CAD-подсистема ЕСКД (Linux)

Независимый модуль для **редактируемых** технологических 2D-чертежей отливок.

- **ОС:** только Linux. AutoCAD / COM / pyautocad не используются.
- **Выход:** DXF (векторные CAD-объекты) + PDF.
- **Аудит и план:** [`AUDIT_AND_PLAN.md`](AUDIT_AND_PLAN.md).
- **Деталь → отливка:** [`PART_TO_CASTING.md`](PART_TO_CASTING.md) — `eskd_cad.part` / `examples.part_dxf_to_casting` → лист через `cad_work/draw_otl`.

## Быстрый тест / основной путь (P1+P2)

```bash
cd cad_subsystem
python3 -m examples.generate_koleso_otlivka   # calc→CastingSpec→OCP виды→DXF+PDF
python3 -m examples.test_p2_ocp_prototype     # P2: тестовые тела HLR/Section
python3 -m unittest tests.test_p4_quality tests.test_p3_geometry tests.test_p2_ocp_geometry tests.test_p1_calc_integration tests.test_p0_parity -v
python3 -m examples.test_flange_drawing
python3 -m examples.test_casting_koleso
# → out/*.dxf + *.pdf + provenance.json
```

- P1: таблицы/гейты → `CastingSpec` — [`P1_INTEGRATION.md`](P1_INTEGRATION.md)
- P2: OCP HLR/Section → контуры — [`P2_GEOMETRY.md`](P2_GEOMETRY.md)
- P3: лопатки/стержни/ЛС/прибыль/хол./Б-Б — [`P3_GEOMETRY_COMPLETENESS.md`](P3_GEOMETRY_COMPLETENESS.md)
- P4: инженерный QA (PASS/FAIL/WARNING/NOT_CHECKED) — [`P4_QUALITY.md`](P4_QUALITY.md)
- Legacy 2D: `build_koleso_otlivka(..., use_ocp=False)`

Проверка DXF:

```bash
python3 -m eskd_cad.qa.validate_dxf out/KP-062215009-01_Otlivka.dxf
librecad dxf2pdf -a out/KP-062215009-01_Otlivka.dxf
```

Инженерные числа — только `eskd_cad/knowledge/calc/` (vendored из листа расчёта / `koleso_data`). Приближения запрещены (`_assert_calc`).

Качество ЕСКД (10 пунктов: виды, разрезы, штриховка, размеры, базы/оси, выноски/ТТ, штамп, слои, геометрия) — `eskd_cad/qa/quality_checklist.py`, гоняется из `test_casting_koleso`.

## Зависимости

Системный Python 3.12: `ezdxf`, `shapely`, `numpy`, `matplotlib` (уже в среде).  
OCP/CadQuery — только через `~/.local/cad/venv-*` (см. план).  
LibreCAD + poppler-utils — для просмотра DXF и QA PDF.  
Не ставить: AutoCAD, PaddleOCR в system (см. `AUDIT_AND_PLAN.md`).
