# CAD-движки в окружении агента

Подключено всё, что реально работает на Linux VM. AutoCAD здесь **недоступен** (Windows-only / нет лицензии).

## Статус

| Движок | Версия | Как вызывать | Назначение |
|--------|--------|--------------|------------|
| **OpenCascade (OCP)** | 8.0.1.1 | `python-ocp8` / venv `~/.local/cad/venv-ocp8` | Непрерывные контуры, 2D offset припусков, BRep |
| **build123d** | 0.13.0 | тот же `python-ocp8` | Высокоуровневая геометрия поверх OCP |
| **CadQuery** | 2.8.0 | `python-cq` / venv `~/.local/cad/venv-cq` | 3D модели, STEP/DXF export |
| **FreeCAD** | 1.1.4 AppImage | `freecadcmd` (headless) | Part/Draft, STEP, скрипты Python |
| **ezdxf + shapely + matplotlib** | в `cad.py` | системный `python3` | ЕСКД-лист: рамка, штамп, PDF/PNG/DXF |
| **AutoCAD** | — | — | **Нельзя** на этой Linux VM |

Два venv нужны потому, что CadQuery 2.8 тянет OCP **7.9**, а build123d — OCP **8.0**; в одном site-packages они ломают друг друга.

## Пути

```
~/.local/cad/
  venv-ocp8/          # build123d + OCP 8 + ezdxf/shapely
  venv-cq/            # CadQuery 2.8 + OCP 7.9 + VTK
  freecad/
    FreeCAD.AppImage
    squashfs-root/    # распакованный AppImage
    user/             # FREECAD_USER_HOME
  bin/
    python-ocp8 → venv-ocp8
    python-cq   → venv-cq
    freecadcmd  → FreeCAD console
    freecad     → FreeCAD GUI (нужен DISPLAY)

~/.local/bin/{python-ocp8,python-cq,freecadcmd}
```

## Проверка

```bash
python-ocp8 /tmp/eskd_agent_pack/tool/engines/smoke_ocp8.py
python-cq   /tmp/eskd_agent_pack/tool/engines/smoke_cq.py
freecadcmd  /tmp/eskd_agent_pack/tool/engines/smoke_freecad.py
python3     /tmp/eskd_agent_pack/tool/engines/check_all.py
```

## Использование из `cad_work`

Чертёж ЕСКД по-прежнему строится через `cad.py` (matplotlib/ezdxf + OpenGost).  
Геометрию контуров/припусков можно считать через OCP:

```python
from engines.occ_bridge import offset_closed_polyline
pts = offset_closed_polyline([(0,0),(100,0),(100,40),(0,40)], amount=4.0)
sh.geom(...); sh.pl(pts, 'allow')
```

`occ_bridge.py` вызывает `python-ocp8` subprocess’ом, чтобы не смешивать OCP 8 с системным Python.
