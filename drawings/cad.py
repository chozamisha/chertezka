# -*- coding: utf-8 -*-
"""Чертёжная мини-CAD: запись примитивов в мм листа, вывод в DXF (ezdxf) и PNG/PDF (matplotlib).
Линии по ГОСТ 2.303-68, шрифт тип Б (OpenGost Type B) по ГОСТ 2.304-81."""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import LineString, Polygon, MultiLineString, box
from shapely.ops import unary_union

FONT = str((__import__('pathlib').Path(__file__).resolve().parent / 'fonts' / 'OpenGostTypeB-Regular.ttf'))
fm.fontManager.addfont(FONT)
FP = FontProperties(fname=FONT)
CAPR = 1000 / 1700.0           # высота прописной / кегль
MM2PT = 72 / 25.4
S = 0.7                         # основная
T = 0.25                        # тонкая (s/3...s/2)
KIND = {'main': S, 'thin': T, 'axis': T, 'hidden': T, 'cut': 1.05, 'wave': T, 'mf': T}
PAT = {'axis': (14.0, 1.5, 1.0, 1.5), 'mf': (14.0, 1.5, 1.0, 1.5), 'hidden': (5.0, 1.5)}
FORMATS = {'A1': (841, 594), 'A2': (594, 420), 'A3': (420, 297), 'A4': (210, 297)}


def text_width(s, h):
    if not s:
        return 0.0
    tp = TextPath((0, 0), s.replace(' ', '\u00a0'), size=100, prop=FP)
    w = tp.get_extents().width
    return w / 100.0 * (h / CAPR)


def dash_split(pts, pattern):
    """разбить полилинию на штрихи; длина штриха подгоняется, чтобы линия начиналась и кончалась штрихом"""
    pts = np.asarray(pts, float)
    seglen = np.hypot(*np.diff(pts, axis=0).T)
    Ltot = seglen.sum()
    dash = pattern[0]
    gaps = pattern[1:]
    gsum = sum(gaps)
    if Ltot < dash * 1.2:
        return [pts], []
    n = max(1, int(round((Ltot - dash) / (dash + gsum))))
    d = (Ltot - n * gsum) / (n + 1)
    # интервалы штрихов
    pieces = []          # (s0, s1) длинные штрихи
    dots = []            # точки (короткие штрихи)
    s = 0.0
    for i in range(n + 1):
        pieces.append((s, s + d))
        s += d
        if i < n:
            if len(gaps) == 3:
                dots.append((s + gaps[0], s + gaps[0] + 0.0))
            s += gsum
    cum = np.concatenate([[0], np.cumsum(seglen)])

    def at(sv):
        k = min(np.searchsorted(cum, sv, side='right') - 1, len(seglen) - 1)
        t = (sv - cum[k]) / seglen[k] if seglen[k] > 0 else 0
        return pts[k] + (pts[k + 1] - pts[k]) * t

    out = []
    for a, b in pieces:
        inner = [pts[k] for k in range(1, len(pts) - 1) if a < cum[k] < b]
        out.append(np.array([at(a)] + inner + [at(b)]))
    dl = []
    for a, _ in dots:
        p = at(a + 0.5)
        k = min(np.searchsorted(cum, a + 0.5, side='right') - 1, len(seglen) - 1)
        u = (pts[k + 1] - pts[k]) / seglen[k]
        dl.append(np.array([p - u * 0.5, p + u * 0.5]))
    return out, dl


class Sheet:
    def __init__(self, fmt='A2'):
        self.fmt = fmt
        self.W, self.H = FORMATS[fmt]
        self.ents = []

    # ---------- примитивы ----------
    def pl(self, pts, kind='main', close=False):
        pts = np.asarray(pts, float)
        if close:
            pts = np.vstack([pts, pts[:1]])
        self.ents.append(('pl', pts, kind))

    def seg(self, x1, y1, x2, y2, kind='main'):
        self.pl([(x1, y1), (x2, y2)], kind)

    def arc(self, cx, cy, r, a0=0, a1=360, kind='main'):
        n = max(24, int(abs(a1 - a0) / 2))
        a = np.radians(np.linspace(a0, a1, n))
        self.ents.append(('arc', (cx, cy, r, a0, a1), kind, np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a)])))

    def circle(self, cx, cy, r, kind='main'):
        self.arc(cx, cy, r, 0, 360, kind)

    def solid(self, pts):
        self.ents.append(('solid', np.asarray(pts, float)))

    def text(self, x, y, s, h=3.5, ha='left', va='baseline', rot=0.0):
        self.ents.append(('text', (x, y), s, h, ha, va, rot))
        return text_width(s, h)

    def geom(self, g, kind='main'):
        """контуры shapely-геометрии"""
        gs = g.geoms if hasattr(g, 'geoms') else [g]
        for p in gs:
            if isinstance(p, Polygon):
                self.pl(np.array(p.exterior.coords), kind)
                for i in p.interiors:
                    self.pl(np.array(i.coords), kind)
            elif hasattr(p, 'coords'):
                self.pl(np.array(p.coords), kind)

    def hatch(self, poly, angle=45, step=2.5, kind='thin'):
        """штриховка shapely-полигона отрезками"""
        if poly.is_empty:
            return
        minx, miny, maxx, maxy = poly.bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        R = math.hypot(maxx - minx, maxy - miny) / 2 + step
        a = math.radians(angle)
        d = np.array([math.cos(a), math.sin(a)]); n = np.array([-d[1], d[0]])
        k = -R + (((cx * n[0] + cy * n[1]) + R) % step)   # привязка к глобальной сетке
        lines = []
        kk = -R - ((cx * n[0] + cy * n[1]) % step)
        while kk <= R:
            p0 = np.array([cx, cy]) + n * kk
            lines.append(LineString([p0 - d * R, p0 + d * R]))
            kk += step
        inter = poly.intersection(MultiLineString(lines))
        gs = inter.geoms if hasattr(inter, 'geoms') else [inter]
        for g in gs:
            if g.length > 0.3 and hasattr(g, 'coords'):
                self.pl(np.array(g.coords), kind)

    # ---------- стрелки, размеры ----------
    def arrow(self, tip, direction, L=3.0, W=1.0):
        d = np.asarray(direction, float); d /= np.linalg.norm(d)
        n = np.array([-d[1], d[0]]); tip = np.asarray(tip, float)
        base = tip - d * L
        self.solid([tip, base + n * W / 2, base - n * W / 2])

    def dim(self, p1, p2, off, txt, h=3.5, tpos=0.5, ext_over=2.0, out=False, tshift=0.0, ext1=True, ext2=True):
        """линейный размер; off - вынос размерной линии по нормали (мм листа)."""
        p1 = np.asarray(p1, float); p2 = np.asarray(p2, float)
        u = (p2 - p1) / np.linalg.norm(p2 - p1); n = np.array([-u[1], u[0]])
        q1, q2 = p1 + n * off, p2 + n * off
        sg = 1 if off >= 0 else -1
        if ext1 and abs(off) > 0.01:
            self.seg(*(p1 + n * sg * 0.0), *(q1 + n * sg * ext_over), 'thin')
        if ext2 and abs(off) > 0.01:
            self.seg(*p2, *(q2 + n * sg * ext_over), 'thin')
        if not out:
            self.seg(*q1, *q2, 'thin'); self.arrow(q1, -u); self.arrow(q2, u)
        else:
            self.seg(*(q1 - u * 9), *(q2 + u * 9), 'thin'); self.arrow(q1, u); self.arrow(q2, -u)
        ang = math.degrees(math.atan2(u[1], u[0]))
        nn = n
        if ang > 90.1 or ang < -89.9:
            ang += 180; nn = -n
        w = text_width(txt, h)
        c = q1 + (q2 - q1) * tpos + u * tshift
        tp = c + nn * 1.0
        self.ents.append(('text', tuple(tp), txt, h, 'center', 'bottom', ang))
        return w

    def leader(self, tip, knee, txt, h=3.5, side='right', arrow=True, dot=False, below=None):
        tip = np.asarray(tip, float); knee = np.asarray(knee, float)
        self.seg(*tip, *knee, 'thin')
        if arrow:
            self.arrow(tip, tip - knee)
        if dot:
            self.circle_fill(tip, 0.5)
        w = max(text_width(txt, h), text_width(below or '', h)) + 2
        if side == 'right':
            self.seg(knee[0], knee[1], knee[0] + w, knee[1], 'thin')
            self.text(knee[0] + 1, knee[1] + 1.0, txt, h)
            if below:
                self.text(knee[0] + 1, knee[1] - 1.0, below, h, va='top')
        else:
            self.seg(knee[0], knee[1], knee[0] - w, knee[1], 'thin')
            self.text(knee[0] - w + 1, knee[1] + 1.0, txt, h)
            if below:
                self.text(knee[0] - w + 1, knee[1] - 1.0, below, h, va='top')

    def circle_fill(self, c, r):
        a = np.radians(np.linspace(0, 360, 20))
        self.solid(np.column_stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)]))

    def rough(self, tip, ndir, val='Ra 6,3', h=3.5, pre=None, flip=False):
        """знак шероховатости ГОСТ 2.309-73 (с полкой). tip - точка на поверхности, ndir - нормаль наружу.
        pre - величина припуска перед знаком (ГОСТ 3.1125-88)."""
        n = np.asarray(ndir, float); n /= np.linalg.norm(n)
        t = np.array([n[1], -n[0]])
        if flip:
            t = -t
        tip = np.asarray(tip, float)
        Hs = 1.6 * h        # высота короткой ветви
        k = math.tan(math.radians(30))
        a = tip + n * Hs - t * Hs * k
        Hl = 3.0 * h
        b = tip + n * Hl + t * Hl * k
        self.seg(*tip, *a, 'thin'); self.seg(*tip, *b, 'thin')
        ang = math.degrees(math.atan2(t[1], t[0]))
        w = text_width(val, h) + 1.5
        e = b + t * w
        self.seg(*b, *e, 'thin')
        rot = ang
        tt, nn = t, n
        if rot > 90.1 or rot < -89.9:
            rot += 180
            p = e + n * 0.9 - t * 0.0
            self.ents.append(('text', tuple(b + n * 0.9 + t * w / 2), val, h, 'center', 'bottom', rot))
        else:
            self.ents.append(('text', tuple(b + n * 0.9 + t * w / 2), val, h, 'center', 'bottom', rot))
        if pre:
            q = a - t * 1.0 + n * 0.0
            self.ents.append(('text', tuple(a - t * 1.2 - n * (Hs * 0.55)), pre, h, 'right', 'center', rot))

    def rough_leader(self, tip, knee, val='Ra 6,3', pre=None, h=3.5, side='right'):
        """знак шероховатости на полке линии-выноски; pre - припуск перед знаком"""
        tip = np.asarray(tip, float); knee = np.asarray(knee, float)
        self.seg(*tip, *knee, 'thin'); self.arrow(tip, tip - knee)
        k = math.tan(math.radians(30))
        wp = text_width(pre, h) + 1.5 if pre else 0.0
        wv = text_width(val, h) + 1.5
        Hs, Hl = 1.6 * h, 3.0 * h
        total = 1.5 + wp + Hs * k + Hl * k + wv
        x0 = knee[0] if side == 'right' else knee[0] - total
        self.seg(x0, knee[1], x0 + total, knee[1], 'thin')
        if pre:
            self.text(x0 + 1.0, knee[1] + 1.0, pre, h)
        t = np.array([x0 + 1.5 + wp + Hs * k, knee[1]])
        a = t + np.array([-Hs * k, Hs]); b = t + np.array([Hl * k, Hl])
        self.seg(*t, *a, 'thin'); self.seg(*t, *b, 'thin')
        self.seg(*b, b[0] + wv, b[1], 'thin')
        self.text(b[0] + wv / 2, b[1] + 0.9, val, h, ha='center')

    def rough_corner(self, x, y, h=3.5, val='Ra 6,3'):
        """знак в правом верхнем углу: Ra … на полке + (√); круг — без удаления слоя."""
        Hs = 1.6 * h; k = math.tan(math.radians(30))
        tip = np.array([x, y], float)
        a = tip + np.array([-Hs * k, Hs]); b = tip + np.array([3 * h * k, 3 * h])
        self.seg(*tip, *a, 'thin'); self.seg(*tip, *b, 'thin')
        r = Hs * k * 0.62
        self.arc(x, y + Hs * 0.62, r, 0, 360, 'thin')
        wv = text_width(val, h) + 1.5
        e = b + np.array([wv, 0.0])
        self.seg(*b, *e, 'thin')
        self.text((b[0] + e[0]) / 2, b[1] + 0.9, val, h, ha='center')
        # (√)
        x2 = e[0] + 2.0
        self.text(x2, y + 1.0, '(', h=h * 1.4)
        tip2 = np.array([x2 + 3.0, y + 0.8])
        a2 = tip2 + np.array([-Hs * 0.6 * k, Hs * 0.6]); b2 = tip2 + np.array([2.0 * h * k, 2.0 * h])
        self.seg(*tip2, *a2, 'thin'); self.seg(*tip2, *b2, 'thin')
        self.text(tip2[0] + 2.0 * h * k + 0.6, y + 1.0, ')', h=h * 1.4)

    # ---------- рамка и основная надпись (ГОСТ 2.104, форма 1 + доп. графы) ----------
    def frame(self, name_lines, code, material, mass, scale, org=('СФУ ИЦМ', 'гр. ЗЦМ22-01Б'),
              sheet='1', sheets='1', lit='У', dev='Шарабуров', chk='Степанова', above=None):
        W, H = self.W, self.H
        x0, y0, x1, y1 = 20, 5, W - 5, H - 5
        self.pl([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 'main', close=True)
        bx, by = x1 - 185, y0
        M, Tn = 'main', 'thin'
        self.pl([(bx, by), (x1, by), (x1, by + 55), (bx, by + 55)], M, close=True)
        cols = [0, 7, 17, 40, 55, 65]
        for c in cols[1:]:
            self.seg(bx + c, by, bx + c, by + 55, M)
        for i in range(1, 11):
            yy = by + 5 * i
            self.seg(bx, yy, bx + 65, yy, M if i in (6, 7) else Tn)
        hdr = ['Изм.', 'Лист', '№ докум.', 'Подп.', 'Дата']
        for c0, c1, s in zip(cols[:-1], cols[1:], hdr):
            self.text(bx + (c0 + c1) / 2, by + 31.3, s, h=2.5, ha='center')
        labels = ['Разраб.', 'Пров.', 'Т.контр.', '', 'Н.контр.', 'Утв.']
        names = [dev, chk, '', '', '', '']
        for i, (lb, nm) in enumerate(zip(labels, names)):
            yy = by + 25 - 5 * i + 1.3
            self.text(bx + 0.8, yy, lb, h=2.5)
            if nm:
                self.text(bx + 17.8, yy, nm, h=2.5)
        rx = bx + 65
        self.seg(rx, by + 40, x1, by + 40, M)
        self.seg(rx, by + 15, x1, by + 15, M)
        mx = rx + 70
        self.seg(mx, by, mx, by + 40, M)
        self.seg(mx, by + 35, x1, by + 35, M)
        self.seg(mx, by + 20, x1, by + 20, M)
        for c in (5, 10):
            self.seg(mx + c, by + 20, mx + c, by + 35, Tn)
        self.seg(mx + 15, by + 20, mx + 15, by + 40, M)
        self.seg(mx + 32, by + 20, mx + 32, by + 40, M)
        self.text(mx + 7.5, by + 36.3, 'Лит.', h=2.5, ha='center')
        self.text(mx + 23.5, by + 36.3, 'Масса', h=2.5, ha='center')
        self.text(mx + 41, by + 36.3, 'Масштаб', h=2.5, ha='center')
        self.text(mx + 2.5, by + 26, lit, h=3.5, ha='center')
        self.text(mx + 23.5, by + 26, mass, h=3.5, ha='center')
        self.text(mx + 41, by + 26, scale, h=3.5, ha='center')
        self.seg(mx + 20, by + 15, mx + 20, by + 20, M)
        self.text(mx + 1, by + 16.3, 'Лист ' + sheet, h=2.5)
        self.text(mx + 21, by + 16.3, 'Листов ' + sheets, h=2.5)
        self.text(rx + 60, by + 47.5, code, h=7, ha='center', va='center')
        n = len(name_lines)
        for i, s in enumerate(name_lines):
            self.text(rx + 35, by + 27.5 + (n - 1) * 3.2 - i * 6.4, s, h=5 if i == 0 else 3.5, ha='center', va='center')
        ml = material if isinstance(material, (list, tuple)) else [material]
        for i, s in enumerate(ml):
            self.text(rx + 35, by + 7.5 + (len(ml) - 1) * 2.7 - i * 5.4, s, h=3.5, ha='center', va='center')
        for i, s in enumerate(org):
            self.text(mx + 25, by + 7.5 + (len(org) - 1) * 2.7 - i * 5.4, s, h=3.5, ha='center', va='center')
        # графа 26
        gx, gy = x0, y1 - 14
        self.pl([(gx, gy), (gx + 70, gy), (gx + 70, y1)], M)
        self.text(gx + 35, gy + 7, code, h=5, ha='center', va='center', rot=180)
        # дополнительные графы 19-23 на поле подшивки
        sx0, sx1, sx2 = 8, 13, 20
        segs = [(0, 25, 'Инв. № подл.'), (25, 60, 'Подп. и дата'), (60, 85, 'Взам. инв. №'),
                (85, 110, 'Инв. № дубл.'), (110, 145, 'Подп. и дата')]
        self.pl([(sx0, y0), (sx0, y0 + 145), (sx2, y0 + 145)], M)
        self.seg(sx1, y0, sx1, y0 + 145, M)
        for a, b, s in segs:
            self.seg(sx0, y0 + b, sx2, y0 + b, M)
            self.text(sx0 + 3.6, y0 + (a + b) / 2, s, h=2.5, ha='center', va='center', rot=90)
        # графы 24-25 (Перв. примен., Справ. №)
        ty0 = y1 - 120
        self.pl([(sx0, ty0), (sx0, y1), (sx2, y1)], M)
        self.seg(sx0, ty0, sx2, ty0, M); self.seg(sx0, ty0 + 60, sx2, ty0 + 60, M)
        self.seg(sx1, ty0, sx1, y1, M)
        self.text(sx0 + 3.6, ty0 + 30, 'Справ. №', h=2.5, ha='center', va='center', rot=90)
        self.text(sx0 + 3.6, ty0 + 90, 'Перв. примен.', h=2.5, ha='center', va='center', rot=90)
        self.text(sx1 + 3.6, ty0 + 90, code, h=2.5, ha='center', va='center', rot=90)
        if above:
            self.text(bx + 92.5, by + 58, above, h=5, ha='center', va='bottom')
        # копировал / формат
        self.text(bx + 75, 1.2, 'Копировал', h=2.5)
        self.text(x1 - 30, 1.2, 'Формат ' + self.fmt, h=2.5)

    # ---------- вывод ----------
    def render(self, png, pdf=None, dpi=200, check_collisions=False, pad=0.4):
        """Рендер PNG/PDF. Если check_collisions — вернуть список пересечений bbox текстов."""
        fig = plt.figure(figsize=(self.W / 25.4, self.H / 25.4))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, self.W); ax.set_ylim(0, self.H)
        ax.set_aspect('equal'); ax.axis('off')
        texts = []

        def draw(pts, lw):
            ax.plot(pts[:, 0], pts[:, 1], color='k', lw=lw * MM2PT, solid_capstyle='round',
                    solid_joinstyle='round')
        for e in self.ents:
            if e[0] in ('pl', 'arc'):
                pts = e[1] if e[0] == 'pl' else e[3]
                kind = e[2]
                lw = KIND[kind]
                if kind in PAT:
                    ds, dots = dash_split(pts, PAT[kind])
                    for p in ds:
                        draw(p, lw)
                    for p in dots:
                        draw(p, lw)
                else:
                    draw(pts, lw)
            elif e[0] == 'solid':
                ax.add_patch(MPoly(e[1], closed=True, fc='k', ec='k', lw=0.1))
            elif e[0] == 'text':
                (x, y), s, h, ha, va, rot = e[1:]
                t = ax.text(x, y, s, fontproperties=FP, fontsize=h / CAPR * MM2PT, ha=ha,
                            va={'baseline': 'baseline', 'bottom': 'baseline', 'top': 'top', 'center': 'center'}[va],
                            rotation=rot, rotation_mode='anchor', color='k')
                texts.append((t, s, x, y))
        collisions = []
        if check_collisions:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            boxes = []
            x0, y0, x1, y1 = 20.0, 5.0, self.W - 5.0, self.H - 5.0
            stamp_x0 = self.W - 5.0 - 185.0
            for t, s, x, y in texts:
                bb = t.get_window_extent(renderer=renderer).transformed(ax.transData.inverted())
                in_stamp = (x >= stamp_x0 - 1 and y <= 60.0)
                in_margin = (x <= 22.0) or (y >= self.H - 20.0 and x <= 95.0)  # боковые/верхняя доп. графы
                under = (y < 4.5)
                boxes.append((s, bb.x0 - pad, bb.y0 - pad, bb.x1 + pad, bb.y1 + pad, x, y,
                              in_stamp or in_margin or under))
                if not (in_stamp or in_margin or under):
                    if bb.x0 < x0 - 0.3 or bb.x1 > x1 + 0.3 or bb.y0 < y0 - 0.3 or bb.y1 > y1 + 0.3:
                        collisions.append(('frame', s[:40], (round(bb.x0, 1), round(bb.y0, 1),
                                                            round(bb.x1, 1), round(bb.y1, 1))))
            for i in range(len(boxes)):
                si, ax0, ay0, ax1, ay1, _, _, skip_i = boxes[i]
                if skip_i:
                    continue
                for j in range(i + 1, len(boxes)):
                    sj, bx0, by0, bx1, by1, _, _, skip_j = boxes[j]
                    if skip_j:
                        continue
                    if ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0:
                        collisions.append(('overlap', si[:40], sj[:40]))
        fig.savefig(png, dpi=dpi, facecolor='white')
        if pdf:
            matplotlib.rcParams['pdf.fonttype'] = 42
            fig.savefig(pdf, facecolor='white')
        plt.close(fig)
        return collisions

    def to_dxf(self, path):
        import ezdxf
        doc = ezdxf.new('R2013', setup=False)
        doc.units = 4
        doc.header['$INSUNITS'] = 4
        doc.header['$LWDISPLAY'] = 1
        doc.styles.add('GOST', font='GOST type B.ttf')
        doc.linetypes.add('GOST_AXIS', pattern=[18.0, 14.0, -1.5, 1.0, -1.5], description='Штрихпунктирная ГОСТ 2.303')
        doc.linetypes.add('GOST_HIDDEN', pattern=[6.5, 5.0, -1.5], description='Штриховая ГОСТ 2.303')
        L = {'main': ('Основная', 70, 'CONTINUOUS'), 'thin': ('Тонкая', 25, 'CONTINUOUS'),
             'axis': ('Осевая', 25, 'GOST_AXIS'), 'mf': ('Разъем', 25, 'GOST_AXIS'),
             'hidden': ('Невидимая', 25, 'GOST_HIDDEN'), 'cut': ('Сечение', 100, 'CONTINUOUS'),
             'wave': ('Тонкая', 25, 'CONTINUOUS')}
        for nm, lw, lt in set(L.values()):
            if nm not in doc.layers:
                doc.layers.add(nm, color=7, lineweight=lw, linetype=lt)
        doc.layers.add('Текст', color=7, lineweight=25)
        msp = doc.modelspace()
        for e in self.ents:
            if e[0] == 'pl':
                nm, lw, lt = L[e[2]]
                msp.add_lwpolyline([tuple(p) for p in e[1]], dxfattribs={'layer': nm, 'lineweight': lw})
            elif e[0] == 'arc':
                nm, lw, lt = L[e[2]]
                cx, cy, r, a0, a1 = e[1]
                if abs(a1 - a0) >= 359.9:
                    msp.add_circle((cx, cy), r, dxfattribs={'layer': nm, 'lineweight': lw})
                else:
                    msp.add_arc((cx, cy), r, a0, a1, dxfattribs={'layer': nm, 'lineweight': lw})
            elif e[0] == 'solid':
                p = e[1]
                if len(p) == 3:
                    msp.add_solid([tuple(p[0]), tuple(p[1]), tuple(p[2])], dxfattribs={'layer': 'Тонкая'})
                else:
                    h = msp.add_hatch(color=7, dxfattribs={'layer': 'Тонкая'})
                    h.paths.add_polyline_path([tuple(q) for q in p])
            elif e[0] == 'text':
                (x, y), s, h, ha, va, rot = e[1:]
                s2 = s.replace('⌀', '%%c').replace('°', '%%d').replace('±', '%%p')
                t = msp.add_text(s2, height=h, rotation=rot, dxfattribs={'style': 'GOST', 'layer': 'Текст', 'width': 1.0})
                from ezdxf.enums import TextEntityAlignment as A
                key = {('left', 'baseline'): A.LEFT, ('center', 'baseline'): A.CENTER, ('right', 'baseline'): A.RIGHT,
                       ('left', 'bottom'): A.LEFT, ('center', 'bottom'): A.CENTER, ('right', 'bottom'): A.RIGHT,
                       ('left', 'center'): A.MIDDLE_LEFT, ('center', 'center'): A.MIDDLE_CENTER, ('right', 'center'): A.MIDDLE_RIGHT,
                       ('left', 'top'): A.TOP_LEFT, ('center', 'top'): A.TOP_CENTER, ('right', 'top'): A.TOP_RIGHT}[(ha, va)]
                t.set_placement((x, y), align=key)
        doc.saveas(path)


class View:
    """вид: модельные мм -> мм листа, масштаб 1:k"""
    def __init__(self, sh, ox, oy, k):
        self.sh, self.ox, self.oy, self.k = sh, ox, oy, k

    def P(self, x, y):
        return np.array([self.ox + x / self.k, self.oy + y / self.k])

    def T(self, pts):
        pts = np.asarray(pts, float)
        return np.column_stack([self.ox + pts[:, 0] / self.k, self.oy + pts[:, 1] / self.k])

    def G(self, g):
        from shapely import affinity
        return affinity.affine_transform(g, [1 / self.k, 0, 0, 1 / self.k, self.ox, self.oy])

    def pl(self, pts, kind='main', close=False):
        self.sh.pl(self.T(pts), kind, close)

    def seg(self, x1, y1, x2, y2, kind='main'):
        self.sh.pl(self.T([(x1, y1), (x2, y2)]), kind)

    def circle(self, cx, cy, r, kind='main', a0=0, a1=360):
        X, Y = self.P(cx, cy)
        self.sh.arc(X, Y, r / self.k, a0, a1, kind)

    def geom(self, g, kind='main'):
        self.sh.geom(self.G(g), kind)

    def hatch(self, g, **kw):
        self.sh.hatch(self.G(g), **kw)

    def dim(self, p1, p2, off, txt, **kw):
        return self.sh.dim(self.P(*p1), self.P(*p2), off, txt, **kw)

    def axis(self, x1, y1, x2, y2):
        self.sh.pl(self.T([(x1, y1), (x2, y2)]), 'axis')


def rough_sign_only(sh, x, y, h=3.5):
    """знак шероховатости без удаления материала (√ с окружностью) в правом верхнем углу"""
    Hs = 1.6 * h; k = math.tan(math.radians(30))
    tip = np.array([x, y])
    a = tip + np.array([-Hs * k, Hs]); b = tip + np.array([3 * h * k, 3 * h])
    sh.seg(*tip, *a, 'thin'); sh.seg(*tip, *b, 'thin')
    sh.arc(x, y + Hs * 0.62, Hs * k * 0.62, 0, 360, 'thin')
