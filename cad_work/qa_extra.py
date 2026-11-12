# -*- coding: utf-8 -*-
"""Дополнение к qa_check: текст не должен касаться линий, штриховки и стрелок.

qa_check.review сравнивает только bbox текстов между собой. Правило ЕСКД
запрещает и наезд надписи на контур, штриховку, размерную или выносную линию.
Здесь лист растеризуется дважды (только тексты / только линии и заливки),
и пересечение масок относится к тексту, в чей bbox оно попало.
"""
from __future__ import annotations

import numpy as np

import cad
import qa_check

PX_PER_MM = 10
# 0,1 мм: запятая в «Ra 6,3» над полкой знака ещё не касание, цифра на штриховке уже да
TOUCH_MM = 0.1
MIN_PIXELS = 4

STAMP_LABELS = {
    "Разраб.", "Пров.", "Т.контр.", "Н.контр.", "Утв.",
    "Инв. № подл.", "Подп. и дата", "Взам. инв. №", "Инв. № дубл.",
    "Справ. №", "Перв. примен.",
}


def _figure(sh):
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(sh.W / 25.4, sh.H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, sh.W)
    ax.set_ylim(0, sh.H)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def _mask(fig):
    import matplotlib.pyplot as plt

    fig.set_dpi(PX_PER_MM * 25.4)
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    plt.close(fig)
    return rgba[:, :, :3].min(axis=2) < 200


def _lines_mask(sh):
    from matplotlib.patches import Polygon as MPoly

    fig, ax = _figure(sh)

    def draw(pts, lw):
        ax.plot(pts[:, 0], pts[:, 1], color="k", lw=lw * cad.MM2PT,
                solid_capstyle="round", solid_joinstyle="round")

    for e in sh.ents:
        if e[0] in ("pl", "arc"):
            pts = e[1] if e[0] == "pl" else e[3]
            kind = e[2]
            lw = cad.KIND[kind]
            if kind in cad.PAT:
                dashes, dots = cad.dash_split(pts, cad.PAT[kind])
                for p in dashes:
                    draw(p, lw)
                for p in dots:
                    draw(p, lw)
            else:
                draw(pts, lw)
        elif e[0] == "solid":
            ax.add_patch(MPoly(e[1], closed=True, fc="k", ec="k", lw=0.1))
    return _mask(fig)


def _texts_mask(sh):
    fig, ax = _figure(sh)
    for e in sh.ents:
        if e[0] != "text":
            continue
        (x, y), s, h, ha, va, rot = e[1:]
        ax.text(
            x, y, s, fontproperties=cad.FP, fontsize=h / cad.CAPR * cad.MM2PT, ha=ha,
            va={"baseline": "baseline", "bottom": "baseline", "top": "top", "center": "center"}[va],
            rotation=rot, rotation_mode="anchor", color="k",
        )
    return _mask(fig)


def _dilate(mask, radius_px):
    from PIL import Image, ImageFilter

    if radius_px < 1:
        return mask
    img = Image.fromarray((mask * 255).astype(np.uint8))
    img = img.filter(ImageFilter.MaxFilter(2 * radius_px + 1))
    return np.asarray(img) > 0


def text_line_touches(sh):
    """Список (текст, x, y, пикселей касания) для надписей, задевающих линии."""
    lines = _lines_mask(sh)
    texts = _texts_mask(sh)
    hit = _dilate(texts, int(round(TOUCH_MM * PX_PER_MM))) & lines
    if not hit.any():
        return []
    height = hit.shape[0]
    found = []
    for item in qa_check.text_bboxes(sh):
        x0, y0, x1, y1 = item["bbox"]
        c0 = max(int(np.floor(x0 * PX_PER_MM)), 0)
        c1 = min(int(np.ceil(x1 * PX_PER_MM)), hit.shape[1])
        r0 = max(height - int(np.ceil(y1 * PX_PER_MM)), 0)
        r1 = min(height - int(np.floor(y0 * PX_PER_MM)), height)
        if c1 <= c0 or r1 <= r0:
            continue
        n = int(hit[r0:r1, c0:c1].sum())
        if n >= MIN_PIXELS:
            found.append((item["s"], item["x"], item["y"], n))
    return found


def _drawn_by_cad(sh, s, x, y):
    """Надпись целиком рисует cad.py (frame / rough_corner), лист на неё не влияет."""
    in_margin = x <= 20.5
    in_stamp = x >= sh.W - 190.0 and y <= 60.0
    if s in STAMP_LABELS and (in_margin or in_stamp):
        return True
    return s in ("(", ")") and y >= sh.H - 40.0


def _fmt(s, x, y, n):
    return f"Текст касается линии: «{s}»@{x:.1f},{y:.1f} ({n} px)"


def review(sh):
    """Замечания к листу. Касания внутри самого cad.py сюда не входят: см. tool_defects."""
    return [_fmt(*t) for t in text_line_touches(sh) if not _drawn_by_cad(sh, *t[:3])]


def tool_defects(sh):
    """Касания в рамке и угловом знаке, которые даёт сам cad.py при любом листе."""
    return [_fmt(*t) for t in text_line_touches(sh) if _drawn_by_cad(sh, *t[:3])]
