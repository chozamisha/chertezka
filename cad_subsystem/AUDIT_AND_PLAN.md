# Аудит Linux-окружения и план CAD-подсистемы

Дата: 2026-11-11. Среда: **только Linux**. AutoCAD / COM / pyautocad — **запрещены**.

---

## 1. Аудит окружения

| Параметр | Значение |
|----------|----------|
| ОС | Ubuntu 24.04.5 LTS (noble), kernel 6.12.113+, x86_64 |
| Python | 3.12.3 (`/usr/bin/python3`) |
| Системный apt CAD | **не установлен** (LibreCAD, Inkscape, tesseract, poppler — только candidates) |

### Уже есть (не трогать)

| Компонент | Где | Версия |
|-----------|-----|--------|
| NumPy / SciPy / SymPy | system user site | 2.5.4 / 1.18.1 / 1.14.0 |
| Shapely | system | 2.2.0 |
| ezdxf | system | 1.4.5 |
| Matplotlib | system | 3.11.2 |
| PyMuPDF (`pymupdf` / `fitz`) | system | 2.1 |
| Pillow, svgwrite | system | OK |
| **OCP 8 + build123d** | `~/.local/cad/venv-ocp8` · `python-ocp8` | 8.0.1.1 / 0.13.0 |
| **CadQuery** | `~/.local/cad/venv-cq` · `python-cq` | 2.8.0 (OCP 7.9) |
| **FreeCAD** | AppImage → `freecadcmd` | 1.1.4 |
| ЕСКД pack | `/tmp/eskd_agent_pack` | `cad.py`, knowledge, tables |

### Нет (и зачем)

| Компонент | Нужен сейчас? | Примечание |
|-----------|---------------|------------|
| LibreCAD | **да** (этап 7) | просмотр/правка DXF |
| poppler-utils | **да** | `pdftoppm` для QA PDF |
| Inkscape | желательно | SVG↔PDF; не блокер DXF |
| OpenCV | позже | только распознавание входных чертежей |
| Tesseract | позже | лёгкий OCR |
| PaddleOCR | **нет на этапе CAD** | тяжёлый, риск конфликтов numpy/CUDA |
| AutoCAD | никогда | Windows-only |

### Конфликт OCP (уже решён изоляцией)

CadQuery 2.8 ↔ OCP **7.9**, build123d ↔ OCP **8.0**.  
В одном `site-packages` ломаются. **Не ставить** OCP/CadQuery/build123d в системный Python.  
Мост: subprocess `python-ocp8` / `python-cq`.

---

## 2. Аудит существующих модулей

| Модуль | Роль | Ограничение |
|--------|------|-------------|
| `/tmp/eskd_agent_pack/tool/cad_work/cad.py` | ЕСКД-лист: примитивы → PNG/PDF (matplotlib) + DXF (ezdxf) | DXF: линии/круги/текст; **нет** настоящих `DIMENSION`/`HATCH` сечений; размеры «разобраны» на линии+текст |
| `qa_check.py`, `layout_fit.py` | автопроверка | оставить как есть |
| `koleso_data.py`, `gost26645_table6.py` | числа отливки | **источник истины** для геометрии |
| `knowledge/tables/*` | ГОСТ/расчёты | не заменять приближениями |
| `tool/engines/*` | OCP offset, FreeCAD/CQ smoke | переиспользовать |
| `gidproject/drawings/` | **удалён** с `main` | не восстанавливать старый набор без запроса; новая подсистема — рядом |

Вывод: нужен **независимый** пакет `cad_subsystem/`, который:

- не патчит и не ломает `cad.py`;
- пишет **редактируемый** DXF с CAD-сущностями;
- берёт размеры из calc/knowledge;
- использует OCP только через существующий venv.

---

## 3. Подходящие библиотеки (выбор)

### Обязательные сейчас (этапы 5–7)

| Слой | Библиотека | Решение |
|------|------------|---------|
| Сцена / DXF | **ezdxf** (уже есть) | ядро экспорта: LINE, ARC, CIRCLE, LWPOLYLINE, HATCH, DIMENSION, MTEXT, LEADER |
| Геометрия 2D | **Shapely + NumPy** (уже есть) | булевы, штриховка, bbox |
| Offset припусков | **OCP8 / build123d** (venv) | через `engines/occ_bridge` |
| PDF | **Matplotlib** + тот же scene graph **или** ezdxf→PDF через matplotlib draw | без Windows |
| Просмотр DXF | **LibreCAD** (apt) | этап 7 |
| QA PDF | **poppler-utils** | растр для кропов |

### Отложить

| Библиотека | Когда |
|------------|-------|
| OpenCV (`opencv-python-headless`) | пайплайн «распознать чертёж детали» |
| Tesseract + rus | лёгкий OCR подписей |
| PaddleOCR | только если Tesseract недостаточен; отдельный venv |
| Inkscape | SVG-полировка / доп. QA |
| CadQuery / FreeCAD | 3D вспомогательно; **не** основной путь 2D ЕСКД |
| SymPy / SciPy | уже есть; для формул/углов по мере надобности |

---

## 4. Архитектура `cad_subsystem/`

```
cad_subsystem/
  AUDIT_AND_PLAN.md          ← этот файл
  README.md
  pyproject / requirements    ← без OCP в system pip
  eskd_cad/
    __init__.py
    model/                   # сцена: Layer, Entity, Sheet, View
      entities.py            # Line, Arc, Circle, Polyline, Hatch, DimLinear, DimDiam, Leader, Text, MText
      document.py            # DrawingDocument
      sheet_gost.py          # рамка А3/А2, штамп ф.1
    geom/                    # shapely helpers + occ_bridge adapter
    export/
      dxf_export.py          # настоящие CAD-объекты
      pdf_export.py          # векторный PDF через matplotlib (те же ents)
    views/                   # main / aux / section helpers
    foundry/                 # stubs: core, print, riser, vent, chill — params from knowledge
    knowledge/               # bridge: load tables / calc modules (read-only)
    qa/
      validate_dxf.py        # entity counts, layers, open with ezdxf
  examples/
    test_flange_drawing.py   # этап 5–6: вид + разрез + размеры + штриховка → DXF+PDF
  out/                       # gitignored outputs
```

Поток данных:

```
knowledge/calc ──► foundry params ──► views/geom ──► DrawingDocument
                                                         │
                                              ┌──────────┴──────────┐
                                           DXF (ezdxf)           PDF (mpl)
                                              │
                                         LibreCAD verify
```

---

## 5. План установок (минимальный)

### Сейчас (этап 5–7)

```bash
sudo apt-get install -y librecad poppler-utils
# опционально позже: inkscape
```

**Не ставить сейчас:**

- `paddlepaddle` / `paddleocr` (конфликт с numpy, гигабайты, не нужны для генерации DXF);
- `cadquery` / `build123d` / `cadquery-ocp*` в system Python (ломают друг друга);
- FreeCAD из apt (уже есть AppImage 1.1.4);
- любые Windows/AutoCAD пакеты.

### Возможные конфликты

| Действие | Риск | Митигация |
|----------|------|-----------|
| `pip install cadquery` в system | ломает build123d/OCP8 | только `venv-cq` |
| `pip install build123d` в system | ломает CadQuery | только `venv-ocp8` |
| `opencv-python` (с GUI/Qt) | тянет лишние libs | позже `opencv-python-headless` |
| PaddleOCR | numpy pin, torch | отдельный venv `venv-ocr` |
| apt `python3-opencv` vs pip | дубли | выбрать один путь |
| LibreCAD шрифты ГОСТ | нет OpenGost из коробки | класть font рядом / document style |

### Критерий успеха этапа 5–7

1. `examples/test_flange_drawing.py` пишет `.dxf` + `.pdf`.
2. DXF содержит ≥1 `CIRCLE`/`ARC`, `LWPOLYLINE`, `HATCH`, `DIMENSION` (или эквивалент DIMENSION через `ezdxf.entities.DimStyle`), текст ТТ, штамп.
3. `ezdxf.readfile` открывает без ошибок; LibreCAD открывает файл (headless dump или GUI screenshot если доступен DISPLAY).
4. Существующие `venv-ocp8` / `venv-cq` / FreeCAD / system shapely-ezdxf **не сломаны** (`engines/check_all.py` зелёный).

### Результат 2026-11-11 (выполнено)

| Проверка | Результат |
|----------|-----------|
| Установка | `librecad`, `poppler-utils` (apt). OCP/CQ/Paddle **не** ставились в system |
| Тест | `python3 -m examples.test_flange_drawing` → OK |
| DXF entities | ARC×2, CIRCLE×7, DIMENSION×5, HATCH×2, LINE, LWPOLYLINE, MTEXT, TEXT, SOLID |
| ezdxf recover | 0 errors |
| LibreCAD | `librecad dxf2pdf` успешно печатает `TEST_FLANGE.dxf` |
| Engines | OCP8/CQ/FreeCAD/ezdxf по-прежнему 5/5 |

Выходные артефакты: `cad_subsystem/out/TEST_FLANGE.dxf` (+ PDF/PNG; `out/` в `.gitignore`).

---

## 6. Этапы после теста

### Сделано (этап 8, первая итерация)

- `eskd_cad/knowledge/calc/koleso_data.py` + `KP-062215009-01_calc.md` — источник чисел.
- `eskd_cad/foundry/koleso_otlivka.py` — разрез А-А, план, местный Б-Б, Ст.1/Ст.2, прибыль, хол., ЛС.
- `examples/test_casting_koleso.py` — geometry_check + validate_dxf + LibreCAD dxf2pdf.
- DXF: DIMENSION×9, HATCH×5, слои Основная/Размеры/Штриховка/Осевая/Разъем/…

### Далее

1. Уточнить компоновку/пересечения размеров по ЕСКД (итерации QA).
2. Лист МЛУ (элементы формы) тем же модулем.
3. OCR/CV — отдельный venv, не в system.
