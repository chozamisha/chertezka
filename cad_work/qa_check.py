# -*- coding: utf-8 -*-
"""Автопроверка листа ЕСКД. Непустой список issues или код 1 = сдавать нельзя."""
from __future__ import annotations

from shapely.geometry import box

import cad

FORBIDDEN_SUBSTRINGS = (
    "Шарабуров",
    "Чертёж детали",
    "Чертеж детали",
    "Чертёж отливки",
    "Чертеж отливки",
    "Производство",
    "Материал детали",
    "Материал -",
    "ГОСТ 3212-80",
)

LEFT_MARGIN_OK = {
    "Инв. № подл.",
    "Подп. и дата",
    "Взам. инв. №",
    "Инв. № дубл.",
    "Справ. №",
    "Перв. примен.",
    "Копировал",
}


def text_bboxes(sh):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly

    fig = plt.figure(figsize=(sh.W / 25.4, sh.H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, sh.W)
    ax.set_ylim(0, sh.H)
    ax.set_aspect("equal")
    ax.axis("off")

    def draw(pts, lw):
        ax.plot(
            pts[:, 0],
            pts[:, 1],
            color="k",
            lw=lw * cad.MM2PT,
            solid_capstyle="round",
            solid_joinstyle="round",
        )

    texts = []
    for e in sh.ents:
        if e[0] in ("pl", "arc"):
            pts = e[1] if e[0] == "pl" else e[3]
            kind = e[2]
            lw = cad.KIND[kind]
            if kind in cad.PAT:
                ds, dots = cad.dash_split(pts, cad.PAT[kind])
                for p in ds:
                    draw(p, lw)
                for p in dots:
                    draw(p, lw)
            else:
                draw(pts, lw)
        elif e[0] == "solid":
            ax.add_patch(MPoly(e[1], closed=True, fc="k", ec="k", lw=0.1))
        elif e[0] == "text":
            (x, y), s, h, ha, va, rot = e[1:]
            t = ax.text(
                x,
                y,
                s,
                fontproperties=cad.FP,
                fontsize=h / cad.CAPR * cad.MM2PT,
                ha=ha,
                va={
                    "baseline": "baseline",
                    "bottom": "baseline",
                    "top": "top",
                    "center": "center",
                }[va],
                rotation=rot,
                rotation_mode="anchor",
                color="k",
            )
            texts.append((t, s, x, y, h, rot))

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = []
    for t, s, x, y, h, rot in texts:
        bb = t.get_window_extent(renderer=renderer)
        inv = ax.transData.inverted()
        x0, y0 = inv.transform((bb.x0, bb.y0))
        x1, y1 = inv.transform((bb.x1, bb.y1))
        boxes.append(
            {
                "s": s,
                "x": x,
                "y": y,
                "h": h,
                "rot": rot,
                "bbox": (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)),
            }
        )
    plt.close(fig)
    return boxes


def find_overlaps(boxes, pad=0.0):
    bad = []
    for i, bi in enumerate(boxes):
        a = bi["bbox"]
        ai = box(a[0] - pad, a[1] - pad, a[2] + pad, a[3] + pad)
        for bj in boxes[i + 1 :]:
            b = bj["bbox"]
            other = box(b[0], b[1], b[2], b[3])
            if ai.intersects(other) or ai.touches(other):
                bad.append((bi, bj))
    return bad


def review(sh, *, code: str, dev: str = "Шевцов", chk: str = "Степанова"):
    issues = []
    boxes = text_bboxes(sh)
    texts = [str(e[2]) for e in sh.ents if e[0] == "text"]
    blob = "\n".join(texts)

    for e in sh.ents:
        if e[0] != "text":
            continue
        s = str(e[2])
        for bad in FORBIDDEN_SUBSTRINGS:
            if bad in s:
                issues.append(f"Запрещённый текст: {s}")

    if dev not in blob:
        issues.append(f"Нет «{dev}» в штампе")
    if chk not in blob:
        issues.append(f"Нет «{chk}» в штампе")
    if code not in texts:
        issues.append(f"Нет обозначения {code}")
    if "ЗЦМ22-01Б" not in blob:
        issues.append("Нет «гр. ЗЦМ22-01Б» в штампе")
    if "СФУ ИЦМ" not in blob:
        issues.append("Нет «СФУ ИЦМ» в штампе")

    for t in texts:
        if t.startswith("1:") and t not in ("1:1", "1:2"):
            issues.append(f"Недопустимый масштаб: {t}")

    tt = [e for e in sh.ents if e[0] == "text" and "Технические требования" in str(e[2])]
    if not tt:
        issues.append("Нет блока «Технические требования»")
    elif tt[0][1][1] < 60:
        issues.append("ТТ не над штампом")

    for t in texts:
        compact = (
            t.replace(" ", "")
            .replace("–", "-")
            .replace("—", "-")
            .replace("−", "-")
        )
        if compact in ("A-A", "B-B", "C-C") or t.startswith("A –") or t.startswith("A -"):
            issues.append(f"Разрез подписать кириллицей «А-А», сейчас: {t}")

    if "Размеры для справок" in blob:
        starred = [
            t
            for t in texts
            if ("*" in t) and ("справок" not in t) and ("Технические" not in t)
        ]
        if not starred:
            issues.append(
                "В ТТ есть «*Размеры для справок», но на листе нет размеров со звёздочкой"
            )

    for a, b in find_overlaps(boxes):
        issues.append(
            f"Пересечение: «{a['s']}»@{a['x']:.1f},{a['y']:.1f} "
            f"× «{b['s']}»@{b['x']:.1f},{b['y']:.1f}"
        )

    x0, y0, x1, y1 = 20, 5, sh.W - 5, sh.H - 5
    for item in boxes:
        s = item["s"]
        if s in LEFT_MARGIN_OK or str(s).startswith("Формат "):
            continue
        if s == code and item["rot"] in (90, 180, -90, 270):
            continue
        bx0, by0, bx1, by1 = item["bbox"]
        if bx1 <= 20.5:
            continue
        if bx0 < x0 - 0.8 or by0 < y0 - 0.8 or bx1 > x1 + 0.8 or by1 > y1 + 0.8:
            issues.append(
                f"Выход за рамку: «{s}» bbox={tuple(round(v, 2) for v in item['bbox'])}"
            )
    return issues


def require_clean(issues):
    for it in issues:
        print("ISSUE:", it)
    if issues:
        print(f"qa_check FAILED: {len(issues)}")
        return 1
    print("qa_check OK")
    return 0
