#!/usr/bin/env python3
"""
make_news.py — a newspaper front page for the world's news of Tuesday 24 November 2026.

Brief 1 (this pass): the page skeleton. Paper, masthead, date bar, kicker, the lead band with a
placeholder illustration panel, the brief grid with placeholder pictogram slots, the footer.
Brief 5: the OIL cell is gone and the brief runs five cells — three across the top, two wider across
the foot — with MORNING EDITION / ONE DAY, ONE PAGE as the kicker.

Two hooks are deliberately left empty for brief 2:
    draw_lead_panel(box)      -> the Strait of Hormuz illustration, 960x228
    draw_pictogram(name, box) -> one flat 54x54 ink pictogram per story

Everything else (grid, rules, type, collision asserts, measurements) is finished and must not move.

Output: entry.png, 1024x1024, PNG, <= 1 MiB. Deterministic: two runs produce byte-identical files.
"""

import hashlib
import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

try:
    import numpy as np
except ImportError:  # pragma: no cover - fallback keeps the page renderable without numpy
    np = None

# --------------------------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------------------------

PAGE = 1024

PAPER = (0xF3, 0xEE, 0xE2)
INK = (0x14, 0x11, 0x0D)
ACCENT = (0x8C, 0x2F, 0x39)          # oxblood — kicker, region tags, rules that need weight
WHITE = (0xFF, 0xFF, 0xFF)

SEED = 20261124                      # every random number on this page comes from here

# content box
X0, X1 = 32, 992
CONTENT_W = X1 - X0                  # 960

# vertical plan (y, height) — printed as the measurement block
BAND_TOP_RULE = (32, 3)
BAND_MASTHEAD = (48, 62)             # DejaVu Serif Bold 74, tracking +5
BAND_MAST_RULE = (132, 1)
BAND_DATEBAR = (142, 56)             # filled black rect 960x56
BAND_KICKER = (210, 26)              # Ubuntu Mono 19
BAND_KICK_RULE = (236, 1)
BAND_LEAD = (246, 350)               # 246 -> 596
BAND_GRID = (606, 300)               # 606 -> 906
BAND_FOOTER = (916, 76)              # 916 -> 992

PANEL = (X0, 246, X0 + CONTENT_W, 246 + 228)        # 960 x 228 illustration panel

# lead band baselines (the 350 px band is tight by design: 228 panel + 2 headline lines + standfirst)
LEAD_L1_BASE = 521
LEAD_L2_BASE = 569
LEAD_SF_BASE = 591

# grid geometry — a newspaper two-row brief: three cells across the top, two wider across the foot
GRID_TOP = 606
GUTTER = 20
CELL_H = 140
TOP_COLS = 3
TOP_CELL_W = 306                     # 3*306 + 2*20 = 958, so the top row sits 1 px inside each side
BOT_COLS = 2
BOT_CELL_W = (CONTENT_W - GUTTER) // BOT_COLS   # 470 — half the content width less the gutter
GRID_X0 = X0 + (CONTENT_W - (TOP_COLS * TOP_CELL_W + (TOP_COLS - 1) * GUTTER)) // 2

# inside a cell
ICON = 54
ICON_GAP = 10                        # icon -> region tag
TAG_BASE = 33                        # baseline, relative to cell top
LBL_L1_BASE = 88                     # 8 px of air under the pictogram slot
LBL_L2_BASE = 122
CELL_RULE_DY = 130

# footer
FOOT_LINE_BASE = 936
FOOT_BAR = (X0, 948, X0 + CONTENT_W, 992)            # 960 x 44

EDGE = 26                            # nothing within this many px of any edge

# --------------------------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------------------------

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_ANTON = "/home/frelika/.local/share/fonts/Anton-Regular.ttf"
FONT_INTER = "/home/frelika/.local/share/fonts/Inter-var.ttf"
FONT_MONO = "/usr/share/fonts/truetype/ubuntu/UbuntuMono[wght].ttf"

_FONT_CACHE = {}


def font(path, size, weight=None, opsz=None):
    """Cached truetype loader. Variable fonts get their axes pinned so the render is repeatable."""
    key = (path, size, weight, opsz)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    f = ImageFont.truetype(path, size)
    try:
        axes = f.get_variation_axes()
        values = []
        for axis in axes:
            name = axis["name"]
            if isinstance(name, bytes):
                name = name.decode("utf-8", "replace")
            if "Weight" in name and weight is not None:
                values.append(weight)
            elif "Optical" in name and opsz is not None:
                values.append(opsz)
            else:
                values.append(axis["default"])
        if values:
            f.set_variation_by_axes(values)
    except Exception:
        pass  # static font: no axes to set
    _FONT_CACHE[key] = f
    return f


# --------------------------------------------------------------------------------------------
# the day's news — one list, seven stories, five fields
# --------------------------------------------------------------------------------------------

STORIES = [
    # --- the lead band: one story, told by the panel, the headline and the standfirst ---
    {
        "slot": "lead",
        "tag": "MIDDLE EAST",
        "icon": "hormuz",
        "label": ("HORMUZ STAYS SHUT AS IRAN'S",
                  'ECONOMY GOES "UNDERWATER"'),
    },
    {
        "slot": "standfirst",
        "tag": "MIDDLE EAST",
        "icon": "hormuz",
        "label": ("Bessent says the sanctions bite; a Saudi-led coalition downs a Houthi drone",),
    },
    # --- the two-row brief grid: three across the top, two wider across the foot ---
    {
        "slot": "grid",
        "tag": "UNITED NATIONS",
        "icon": "unsc",
        "label": ("SECURITY COUNCIL", "DEBATES TECH AND WAR"),
    },
    {
        "slot": "grid",
        "tag": "AFRICA",
        "icon": "addis",
        "label": ("ADDIS ABABA: AFRICA", "ON HEALTH SOVEREIGNTY"),
    },
    {
        "slot": "grid",
        "tag": "ASIA",
        "icon": "planes",
        "label": ("CHINA CUTS MORE", "JAPAN FLIGHT ROUTES"),
    },
    {
        "slot": "grid",
        "tag": "EUROPE",
        "icon": "eu",
        "label": ("STRASBOURG DEBATES", "UKRAINE BEFORE SUMMIT"),
    },
    {
        "slot": "grid",
        "tag": "SKY",
        "icon": "moon",
        "label": ("FIRST OF THREE", "SUPERMOONS TONIGHT"),
    },
]

GRID_STORIES = [s for s in STORIES if s["slot"] == "grid"]
LEAD_STORY = next(s for s in STORIES if s["slot"] == "lead")
SF_STORY = next(s for s in STORIES if s["slot"] == "standfirst")

KICKER_LEFT = "MORNING EDITION"
KICKER_RIGHT = "ONE DAY, ONE PAGE"
FOOT_LINE = "Tuesday's news, drawn by an AI agent for make.fun"
FOOT_BAR_TEXT = "THE WORLD TODAY  ·  TUESDAY 24 NOVEMBER 2026  ·  DRAWN BY AN AI AGENT FOR make.fun"
DATE_TEXT = "TUESDAY 24 NOVEMBER 2026"
MASTHEAD = "THE WORLD TODAY"

# --------------------------------------------------------------------------------------------
# surfaces + measurement registry
# --------------------------------------------------------------------------------------------

_IMG = None
_DRAW = None

ITEMS = []       # every box on the page: {"name", "box", "kind"}  kind in text|rule|slot|container


def _surface():
    if _IMG is None or _DRAW is None:
        raise RuntimeError("no surface: call build() first")
    return _IMG, _DRAW


def register(name, box, kind, size=None):
    ITEMS.append({"name": name, "box": tuple(float(v) for v in box), "kind": kind, "size": size})
    return box


# --------------------------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------------------------

def draw_tracked(draw, text, fnt, tracking, x, y, fill, anchor="ls", name=None, kind="text"):
    """
    Draw text glyph by glyph so letter-spacing works (Pillow has no tracking).

    anchor is Pillow's two-letter form: horizontal l|m|r, vertical s (baseline) | t (ascender top).
    Alignment is snapped to the real ink box, so a right-anchored line ends exactly on x and a
    centred line is optically centred rather than advance-centred.
    Returns (box, total_width) where box is the union of the real ink boxes.
    """
    if not text:
        return (x, y, x, y), 0.0
    adv = [fnt.getlength(ch) for ch in text]
    total = sum(adv) + tracking * max(0, len(text) - 1)
    baseline = y if anchor[1] == "s" else y + fnt.getmetrics()[0]

    def ink_at(start):
        boxes, cur = [], start
        for ch, a in zip(text, adv):
            b = draw.textbbox((cur, baseline), ch, font=fnt, anchor="ls")
            if b[2] > b[0]:
                boxes.append(b)
            cur += a + tracking
        if not boxes:
            return (start, baseline, start, baseline)
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))

    cur = x - total / 2.0 if anchor[0] == "m" else (x - total if anchor[0] == "r" else x)
    box = ink_at(cur)
    if anchor[0] == "r":
        cur -= box[2] - x
    elif anchor[0] == "m":
        cur -= (box[0] + box[2]) / 2.0 - x
    box = ink_at(cur)

    for ch, a in zip(text, adv):
        draw.text((cur, baseline), ch, font=fnt, fill=fill, anchor="ls")
        cur += a + tracking

    if name:
        register(name, box, kind, size=fnt.size)
    return box, total


def tracked_width(text, fnt, tracking):
    return sum(fnt.getlength(ch) for ch in text) + tracking * max(0, len(text) - 1)


def hairline(draw, y, x0=X0, x1=X1, name=None, weight=1):
    draw.rectangle([x0, y, x1 - 1, y + weight - 1], fill=INK)
    if name:
        register(name, (x0, y, x1, y + weight), "rule")


def band(draw, y, h, fill, x0=X0, x1=X1, name=None, kind="container"):
    draw.rectangle([x0, y, x1 - 1, y + h - 1], fill=fill)
    if name:
        register(name, (x0, y, x1, y + h), kind)


# --------------------------------------------------------------------------------------------
# paper
# --------------------------------------------------------------------------------------------

def make_paper():
    """Paper #F3EEE2 with a seeded fibre grain (sigma 2.0) and a 1.5% vignette."""
    if np is None:  # pragma: no cover
        rnd = random.Random(SEED)
        img = Image.new("RGB", (PAGE, PAGE), PAPER)
        px = img.load()
        cx = cy = PAGE / 2.0
        dmax = math.hypot(cx, cy)
        for yy in range(PAGE):
            for xx in range(PAGE):
                g = rnd.gauss(0.0, 2.0)
                v = 1.0 - 0.015 * (math.hypot(xx - cx, yy - cy) / dmax) ** 2
                px[xx, yy] = tuple(max(0, min(255, int((c + g) * v))) for c in PAPER)
        return img

    rng = np.random.default_rng(SEED)
    arr = np.empty((PAGE, PAGE, 3), dtype=np.float32)
    arr[:] = np.array(PAPER, dtype=np.float32)
    arr += rng.normal(0.0, 2.0, (PAGE, PAGE, 1)).astype(np.float32)

    yy, xx = np.mgrid[0:PAGE, 0:PAGE].astype(np.float32)
    c = PAGE / 2.0
    r = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / math.hypot(c, c)
    arr *= (1.0 - 0.015 * r ** 2)[..., None]

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------------------------
# drawing kit — ImageDraw has no antialiasing, so every drawing is built at 4x and downscaled
# once with LANCZOS. Flat two-colour: ink on paper, oxblood accent.
# --------------------------------------------------------------------------------------------

DRAW_SCALE = 4                       # scratch multiplier
STROKE_MAIN = 3                      # px at 1x — main stroke
STROKE_SECOND = 2                    # px at 1x — secondary stroke

INK_RGBA = INK + (255,)
ACCENT_RGBA = ACCENT + (255,)
CLEAR = (0, 0, 0, 0)                 # erases: ImageDraw on RGBA replaces pixels, it does not blend


class Pen:
    """Draws in 1x design units onto a 4x scratch canvas."""

    def __init__(self, draw, scale=DRAW_SCALE, image=None):
        self.d = draw
        self.s = scale
        self.img = image if image is not None else draw._image   # draw.im is the core buffer

    def _pt(self, x, y):
        return (x * self.s, y * self.s)

    def _box(self, x0, y0, x1, y1):
        s = self.s
        return [x0 * s, y0 * s, x1 * s - 1, y1 * s - 1]

    @staticmethod
    def _w(w, s):
        return max(1, int(round(float(w) * s)))

    def poly(self, pts, fill=None, outline=None, w: float = 0):
        self.d.polygon([self._pt(x, y) for x, y in pts], fill=fill, outline=outline,
                       width=self._w(w, self.s) if outline else 0)

    def line(self, pts, w: float = STROKE_MAIN, fill=INK_RGBA):
        self.d.line([self._pt(x, y) for x, y in pts], fill=fill,
                    width=self._w(w, self.s), joint="curve")

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, w: float = 0):
        self.d.rectangle(self._box(x0, y0, x1, y1), fill=fill, outline=outline,
                         width=self._w(w, self.s) if outline else 0)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, w: float = 0):
        self.d.ellipse(self._box(cx - rx, cy - ry, cx + rx, cy + ry), fill=fill,
                       outline=outline, width=self._w(w, self.s) if outline else 0)

    def arc(self, cx, cy, r, a0, a1, w: float = STROKE_MAIN, fill=INK_RGBA):
        self.d.arc(self._box(cx - r, cy - r, cx + r, cy + r), a0, a1, fill=fill,
                   width=self._w(w, self.s))

    def dot(self, cx, cy, r, fill=INK_RGBA):
        self.ellipse(cx, cy, r, r, fill=fill)

    def hatch(self, pts, step=7.0, w=STROKE_SECOND, fill=INK_RGBA):
        """45-degree hatching clipped to a polygon — the headlands are hatched, not filled."""
        s = self.s
        size = self.img.size
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).polygon([self._pt(x, y) for x, y in pts], fill=255)
        lines = Image.new("L", size, 0)
        ld = ImageDraw.Draw(lines)
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        lo = int((min(xs) + min(ys)) * s) - 1
        hi = int((max(xs) + max(ys)) * s) + 1
        y0, y1 = int(min(ys) * s), int(max(ys) * s)
        for c in range(lo, hi, max(1, int(step * s))):
            ld.line([(c - y0, y0), (c - y1, y1)], fill=255, width=self._w(w, s))
        layer = Image.new("RGBA", size, fill)
        self.img.paste(layer, (0, 0), ImageChops.multiply(lines, mask))


def _scratch(w, h):
    canvas = Image.new("RGBA", (int(w) * DRAW_SCALE, int(h) * DRAW_SCALE), CLEAR)
    return canvas, Pen(ImageDraw.Draw(canvas), DRAW_SCALE, canvas)


def _flatten(canvas, w, h):
    """Downscale the 4x scratch once, LANCZOS — this is what kills the staircasing."""
    return canvas.resize((int(w), int(h)), Image.Resampling.LANCZOS)


# --------------------------------------------------------------------------------------------
# the lead panel — the Strait of Hormuz, 960x228, ink + oxblood
# --------------------------------------------------------------------------------------------

def draw_lead_panel(box=None):
    """
    A wide editorial illustration, not a map.

    left third   a blunt tanker in profile, low and heavy: ink hull, accent waterline, a deck of
                 pipes, three containers on the stern, sitting on the flat ink horizon rule
    centre       the strait: two angular headlands narrowing the water, hatched, with a broken
                 chain across the gap in oxblood
    right third  a warship silhouette further out, and above it a drone in plan view — long
                 straight wing, bulbous nose, pusher prop at the tail — with a thin accent sight
                 line down to the water
    sky          paper only, three short accent dashes as emission marks
    water        three horizontal ink rules of decreasing length
    """
    img, _ = _surface()
    if box is None:
        box = PANEL
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    canvas, p = _scratch(w, h)

    HZ = 150.0                                     # horizon, panel-local

    # ---- water: three rules, decreasing length ---------------------------------------
    for yy, ln in ((158.0, w), (174.0, w * 0.792), (192.0, w * 0.583)):
        p.line([(0.0, yy), (ln, yy)], w=STROKE_SECOND)

    # ---- the flat ink horizon rule ---------------------------------------------------
    p.line([(0.0, HZ), (float(w), HZ)], w=STROKE_MAIN)

    # ---- left third: the tanker ------------------------------------------------------
    p.poly([(16, 110), (280, 110), (300, 134), (288, 148), (28, 148), (16, 132)], fill=INK_RGBA)
    p.line([(24.0, 137.5), (294.0, 137.5)], w=3.0, fill=ACCENT_RGBA)      # waterline
    p.line([(120.0, 102.0), (272.0, 102.0)], w=STROKE_SECOND)             # deck of pipes
    p.line([(120.0, 107.0), (272.0, 107.0)], w=STROKE_SECOND)
    for px in range(126, 273, 24):
        p.line([(float(px), 102.0), (float(px), 110.0)], w=STROKE_SECOND)
    for i in range(3):                                                    # three containers, stern
        cx0 = 36.0 + i * 24.0
        p.rect(cx0, 96.0, cx0 + 20.0, 110.0, fill=INK_RGBA)

    # ---- centre: the strait ----------------------------------------------------------
    left_land = [(340, HZ), (372, 112), (404, 92), (436, 106), (450, HZ)]
    right_land = [(620, HZ), (596, 110), (572, 96), (548, 112), (536, HZ)]
    for land in (left_land, right_land):
        p.hatch(land, step=7.0, w=STROKE_SECOND)
        p.poly(land, outline=INK_RGBA, w=STROKE_MAIN)

    # the chain, in oxblood, with one link gone and two ends drooping into the water
    for i in range(7):
        cx = 452.0 + i * 14.0
        if i == 3:
            continue
        if i % 2 == 0:
            p.rect(cx - 8.0, 136.5, cx + 8.0, 146.5, outline=ACCENT_RGBA, w=STROKE_SECOND)
        else:
            p.rect(cx - 5.0, 133.5, cx + 5.0, 149.5, outline=ACCENT_RGBA, w=STROKE_SECOND)
    p.line([(487.0, 141.0), (483.0, 149.0)], w=STROKE_SECOND, fill=ACCENT_RGBA)
    p.line([(501.0, 141.0), (505.0, 149.0)], w=STROKE_SECOND, fill=ACCENT_RGBA)

    # ---- right third: the warship, further out ---------------------------------------
    p.poly([(700, 134), (820, 134), (838, 148), (690, 148)], fill=INK_RGBA)
    p.rect(740.0, 120.0, 776.0, 134.0, fill=INK_RGBA)                     # superstructure
    p.line([(760.0, 120.0), (753.0, 107.0)], w=2.5)                       # raked mast
    p.rect(747.0, 101.0, 761.0, 107.0, fill=INK_RGBA)                     # radar block
    p.poly([(710, 134), (722, 134), (717, 125)], fill=INK_RGBA)           # deck gun

    # ---- the drone, plan view: long straight wing, bulbous nose, pusher prop ----------
    p.poly([(762, 60), (946, 60), (950, 63), (946, 66), (762, 66), (758, 63)], fill=INK_RGBA)
    p.rect(800.0, 59.0, 892.0, 67.0, fill=INK_RGBA)                       # slim body
    p.ellipse(798.0, 63.0, 11.0, 8.0, fill=INK_RGBA)                      # bulbous nose
    p.poly([(892, 59), (914, 61.5), (914, 64.5), (892, 67)], fill=INK_RGBA)
    p.line([(918.0, 50.0), (918.0, 76.0)], w=3.0)                         # pusher prop
    p.dot(918.0, 63.0, 2.5)

    # ---- the thin accent sight line, from the drone's belly down to the water ---------
    p.line([(852.0, 70.0), (852.0, 146.0)], w=STROKE_SECOND, fill=ACCENT_RGBA)
    p.line([(846.0, 146.0), (858.0, 146.0)], w=STROKE_SECOND, fill=ACCENT_RGBA)

    # ---- sky: three emission dashes --------------------------------------------------
    for ax, ay, ln in ((862.0, 40.0, 16.0), (838.0, 30.0, 12.0), (886.0, 50.0, 14.0)):
        p.line([(ax, ay), (ax + ln, ay)], w=3.0, fill=ACCENT_RGBA)

    flat = _flatten(canvas, w, h)
    img.paste(flat, (int(x0), int(y0)), flat)
    register("lead_panel", box, "container")


# --------------------------------------------------------------------------------------------
# the five pictograms — 54x54, 2 px of air inside the box, one system
# --------------------------------------------------------------------------------------------

def _ell_arc(p, cx, cy, rx, ry, a0, a1, w=STROKE_MAIN, fill=INK_RGBA):
    """
    Elliptical arc on the 4x scratch canvas.

    Pen.arc only takes a single radius, and a globe's latitude lines are ellipses, not circles, so
    this mirrors Pen._box / Pen._w with a separate rx and ry. Angles are Pillow's: 0 at 3 o'clock,
    increasing clockwise (y grows down).
    """
    s = p.s
    box = [(cx - rx) * s, (cy - ry) * s, (cx + rx) * s - 1, (cy + ry) * s - 1]
    p.d.arc(box, a0, a1, fill=fill, width=max(1, int(round(float(w) * s))))


def _star(p, cx, cy, r_out, r_in=None, fill=ACCENT_RGBA):
    """A filled five-pointed star, one point up: ten vertices alternating outer and inner radius."""
    r_in = r_out * 0.382 if r_in is None else r_in
    pts = []
    for i in range(10):
        rad = math.radians(-90.0 + i * 36.0)
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))
    p.poly(pts, fill=fill)


def _icon_unsc(p):
    """
    The Security Council: a wireframe globe — the 40 px outline, two elliptical latitude arcs and
    one vertical meridian, all 3 px ink — plus a small antenna mast outside the top-right rim, so
    the mark still says technology rather than geography.
    """
    cx, cy, r = 27.0, 27.0, 20.0
    p.ellipse(cx, cy, r, r, outline=INK_RGBA, w=STROKE_MAIN)        # the 40 px circle outline
    _ell_arc(p, cx, cy - 8.0, r, 5.5, 0, 180)                       # latitude, upper third
    _ell_arc(p, cx, cy + 8.0, r, 5.5, 0, 180)                       # latitude, lower third
    p.ellipse(cx, cy, 8.0, r, outline=INK_RGBA, w=STROKE_MAIN)      # the vertical meridian

    # the antenna: a mast, two short elements and a cap — clear of the rim at top right
    p.line([(46.5, 14.0), (46.5, 4.0)], w=2.0)                      # the mast
    p.dot(46.5, 3.0, 1.3)                                           # the cap
    p.line([(43.5, 7.0), (49.5, 7.0)], w=2.0)                       # element, upper
    p.line([(44.5, 10.0), (48.5, 10.0)], w=2.0)                     # element, lower


def _icon_addis(p):
    """CPHIA in Addis: a medical cross inside a shield."""
    p.poly([(9, 10), (45, 10), (45, 24), (27, 48), (9, 24)], outline=INK_RGBA, w=STROKE_MAIN)
    p.rect(16.0, 21.0, 38.0, 27.0, fill=INK_RGBA)            # cross, horizontal arm
    p.rect(24.0, 13.0, 30.0, 35.0, fill=INK_RGBA)            # cross, vertical arm


def _icon_planes(p):
    """China's route cuts: an aircraft nose-down with a cancelled slash across it."""
    p.poly([(27, 47), (23, 38), (23, 15), (31, 15), (31, 38)], fill=INK_RGBA)     # fuselage
    p.poly([(23, 24), (4.5, 15), (4.5, 19.5), (23, 31)], fill=INK_RGBA)           # wing, left
    p.poly([(31, 24), (49.5, 15), (49.5, 19.5), (31, 31)], fill=INK_RGBA)         # wing, right
    p.poly([(23, 16), (15.5, 11.5), (15.5, 14.5), (23, 20)], fill=INK_RGBA)       # tailplane
    p.poly([(31, 16), (38.5, 11.5), (38.5, 14.5), (31, 20)], fill=INK_RGBA)
    p.line([(7.0, 45.0), (47.0, 9.0)], w=6.0, fill=CLEAR)                         # paper gap
    p.line([(7.0, 45.0), (47.0, 9.0)], w=3.0, fill=ACCENT_RGBA)                   # the slash


def _icon_eu(p):
    """Strasbourg: the European emblem — twelve small five-pointed stars on a 38 px ring, oxblood,
    no centre mark."""
    cx, cy, ring = 27.0, 27.0, 19.0
    for i in range(12):
        rad = math.radians(-90.0 + i * 30.0)              # one star at the top, evenly spaced
        _star(p, cx + ring * math.cos(rad), cy + ring * math.sin(rad), 3.4)


def _icon_moon(p):
    """The first of three supermoons: a full 36 px ink disc, three craters inside it only, and a
    thin 2 px oxblood halo ring at 46 px. No rays, nothing protruding."""
    cx, cy, r = 27.0, 27.0, 18.0
    p.ellipse(cx, cy, r, r, fill=INK_RGBA)
    # three craters, all clustered in one quadrant and of three sizes — a corner cluster cannot be
    # read as two eyes and a mouth the way a centred triangle can
    for dx, dy, rr in ((-7.5, -5.5, 2.9), (-2.0, -8.0, 2.1), (-8.0, 1.5, 1.6)):
        p.dot(cx + dx, cy + dy, rr, fill=CLEAR)          # craters: paper through the disc
    p.ellipse(cx, cy, 23.0, 23.0, outline=ACCENT_RGBA, w=2.0)     # the halo, 46 px across


ICONS = {
    "unsc": _icon_unsc,
    "addis": _icon_addis,
    "planes": _icon_planes,
    "eu": _icon_eu,
    "moon": _icon_moon,
}


def draw_pictogram(name, box):
    """
    One flat ink pictogram per story, 54x54, 2 px of air inside the box.

    Every icon is built on a 4x scratch canvas and downscaled once, so the rim of the globe and the
    circle of the halo and the stars of the emblem are smooth at 1:1 instead of staircased.
    """
    img, _ = _surface()
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    try:
        fn = ICONS[name]
    except KeyError:
        raise SystemExit("no pictogram drawn for icon %r (have: %s)"
                         % (name, ", ".join(sorted(ICONS))))

    canvas = Image.new("RGBA", (int(w) * DRAW_SCALE, int(h) * DRAW_SCALE), CLEAR)
    fn(Pen(ImageDraw.Draw(canvas), DRAW_SCALE, canvas))
    flat = _flatten(canvas, w, h)
    img.paste(flat, (int(x0), int(y0)), flat)      # its own alpha is the mask: paper shows through
    register("icon:" + name, box, "slot")



# --------------------------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------------------------

def build():
    global _IMG, _DRAW
    ITEMS.clear()

    img = make_paper()
    draw = ImageDraw.Draw(img)
    _IMG, _DRAW = img, draw

    # ---- top rule ---------------------------------------------------------------------
    y, h = BAND_TOP_RULE
    hairline(draw, y, name="rule:top", weight=h)

    # ---- masthead ---------------------------------------------------------------------
    y, h = BAND_MASTHEAD
    f_mast = font(FONT_SERIF, 74)
    draw_tracked(draw, MASTHEAD, f_mast, 5.0, PAGE / 2, y, INK, anchor="mt", name="masthead")

    # ---- hairline under masthead ------------------------------------------------------
    y, h = BAND_MAST_RULE
    hairline(draw, y, name="rule:masthead")

    # ---- date bar ---------------------------------------------------------------------
    y, h = BAND_DATEBAR
    band(draw, y, h, INK, name="datebar")
    f_date = font(FONT_ANTON, 38)
    draw_tracked(draw, DATE_TEXT, f_date, 2.4, PAGE / 2, y + 45, WHITE, anchor="ms", name="date")

    # ---- kicker row -------------------------------------------------------------------
    y, h = BAND_KICKER
    f_kick = font(FONT_MONO, 19, weight=400)
    draw_tracked(draw, KICKER_LEFT, f_kick, 2.0, X0, y + 16, ACCENT, anchor="ls", name="kicker_left")
    draw_tracked(draw, KICKER_RIGHT, f_kick, 2.0, X1, y + 16, ACCENT, anchor="rs", name="kicker_right")

    y, h = BAND_KICK_RULE
    hairline(draw, y, name="rule:kicker")

    # ---- lead band --------------------------------------------------------------------
    draw_lead_panel(PANEL)

    f_hl = font(FONT_ANTON, 50)
    for i, line in enumerate(LEAD_STORY["label"]):
        base = LEAD_L1_BASE if i == 0 else LEAD_L2_BASE
        draw_tracked(draw, line, f_hl, -0.5, X0, base, INK, anchor="ls", name="lead_l%d" % (i + 1))

    f_sf = font(FONT_INTER, 23, weight=500, opsz=28)
    draw_tracked(draw, SF_STORY["label"][0], f_sf, 0.0, X0, LEAD_SF_BASE, INK,
                 anchor="ls", name="standfirst")

    # ---- brief grid: three across the top, two wider across the foot ------------------
    for idx, story in enumerate(GRID_STORIES):
        cx, cy, cell_w, cell_h = cell_rect(idx)

        icon_box = (cx, cy, cx + ICON, cy + ICON)
        draw_pictogram(story["icon"], icon_box)

        f_tag = font(FONT_MONO, 17, weight=400)
        draw_tracked(draw, story["tag"], f_tag, 1.2, cx + ICON + ICON_GAP, cy + TAG_BASE,
                     ACCENT, anchor="ls", name="tag:%s" % story["tag"].replace(" ", "_"))

        f_lbl = font(FONT_ANTON, 30)
        for li, line in enumerate(story["label"]):
            if len(line) > 26:
                raise SystemExit("label line over 26 characters: %r (%d)" % (line, len(line)))
            base = cy + (LBL_L1_BASE if li == 0 else LBL_L2_BASE)
            box, w = draw_tracked(draw, line, f_lbl, -0.3, cx, base, INK, anchor="ls",
                                  name="label:%s:%d" % (story["icon"], li + 1))
            if w > cell_w:
                raise SystemExit("label wider than the cell: %r (%.1f > %d)" % (line, w, cell_w))
            if box[2] > cx + cell_w:
                raise SystemExit("label overruns its cell: %r right edge %.0f > %d"
                                 % (line, box[2], cx + cell_w))

        hairline(draw, cy + CELL_RULE_DY, x0=cx, x1=cx + cell_w,
                 name="rule:cell:%d" % idx)

    # ---- footer -----------------------------------------------------------------------
    f_fl = font(FONT_INTER, 21, weight=400, opsz=21)
    draw_tracked(draw, FOOT_LINE, f_fl, 0.0, X0, FOOT_LINE_BASE, INK, anchor="ls", name="foot_line")

    bx0, by0, bx1, by1 = FOOT_BAR
    band(draw, by0, by1 - by0, INK, x0=bx0, x1=bx1, name="footer_bar")
    # the bar now carries the full edition line, so it sets at 17 px (the type floor) to hold 82
    # characters inside the 960 px bar with air at both ends
    f_fb = font(FONT_MONO, 17, weight=400)
    draw_tracked(draw, FOOT_BAR_TEXT, f_fb, 1.0, PAGE / 2, by0 + 29, WHITE, anchor="ms",
                 name="foot_bar_text")

    check_layout()
    return img


# --------------------------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------------------------

def _inside(a, b, tol=0.5):
    return a[0] >= b[0] - tol and a[1] >= b[1] - tol and a[2] <= b[2] + tol and a[3] <= b[3] + tol


def _overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _separation(a, b):
    """Chebyshev gap between two non-overlapping boxes."""
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return max(dx, dy)


def check_layout():
    # 0. no text smaller than 17 px
    for it in ITEMS:
        if it["kind"] == "text" and it["size"] is not None and it["size"] < 17:
            raise SystemExit("text below the 17 px floor: %s at %d px" % (it["name"], it["size"]))

    # 1. every box sits inside the 26 px edge margin
    for it in ITEMS:
        b = it["box"]
        if b[0] < EDGE or b[1] < EDGE or b[2] > PAGE - EDGE or b[3] > PAGE - EDGE:
            raise SystemExit("edge margin violated by %s: box=(%.0f,%.0f,%.0f,%.0f) needs %d px"
                             % (it["name"], b[0], b[1], b[2], b[3], EDGE))

    # 2. nothing collides
    for i, a in enumerate(ITEMS):
        for b in ITEMS[i + 1:]:
            if a["kind"] == "container" or b["kind"] == "container":
                cont, other = (a, b) if a["kind"] == "container" else (b, a)
                if _inside(other["box"], cont["box"]):
                    continue          # text inside its own bar/panel is intended
            if a["kind"] == "container" and b["kind"] == "container":
                continue
            if _overlap(a["box"], b["box"]):
                raise SystemExit("collision: %s (%.0f,%.0f,%.0f,%.0f) hits %s (%.0f,%.0f,%.0f,%.0f)"
                                 % (a["name"], *a["box"], b["name"], *b["box"]))


def pairs_checked():
    """Every pair of boxes the collision rule actually looks at, with the container exemptions."""
    out = []
    for i, a in enumerate(ITEMS):
        for b in ITEMS[i + 1:]:
            if a["kind"] == "container" or b["kind"] == "container":
                cont, other = (a, b) if a["kind"] == "container" else (b, a)
                if _inside(other["box"], cont["box"]):
                    continue          # text inside its own bar/panel is intended
            if a["kind"] == "container" and b["kind"] == "container":
                continue
            out.append((a, b))
    return out


def count_collisions():
    """How many of those pairs actually overlap. check_layout() already refuses to reach 1."""
    return sum(1 for a, b in pairs_checked() if _overlap(a["box"], b["box"]))


def smallest_gap():
    best = (None, None, 1e9)
    for i, a in enumerate(ITEMS):
        for b in ITEMS[i + 1:]:
            if a["kind"] == "container" or b["kind"] == "container":
                cont, other = (a, b) if a["kind"] == "container" else (b, a)
                if _inside(other["box"], cont["box"]):
                    continue
            if a["kind"] == "container" and b["kind"] == "container":
                continue
            if _overlap(a["box"], b["box"]):
                continue
            g = _separation(a["box"], b["box"])
            if g < best[2]:
                best = (a["name"], b["name"], g)
    return best


def ink_pixels(img, box, thresh=30):
    """
    Count pixels inside box that are visibly inked: far enough from the paper tone that the seeded
    grain (sigma 2.0) cannot be mistaken for ink. Ink and oxblood both count; paper does not.
    """
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    crop = img.crop((x0, y0, x1, y1)).convert("RGB")
    n = 0
    for px in crop.getdata():
        if (abs(px[0] - PAPER[0]) + abs(px[1] - PAPER[1]) + abs(px[2] - PAPER[2])) > thresh:
            n += 1
    return n


def ink_extent(img, box, thresh=30):
    """Bounding box of the ink actually laid down inside box, or None if the box is empty paper."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    crop = img.crop((x0, y0, x1, y1)).convert("RGB")
    if np is not None:
        arr = np.asarray(crop, dtype=np.int16)
        d = np.abs(arr - np.array(PAPER, dtype=np.int16)).sum(axis=2)
        ys, xs = np.where(d > thresh)
        if len(ys) == 0:
            return None
        return (x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()), y0 + int(ys.max()))
    rows = [y for y in range(y0, y1) if ink_pixels(img, (x0, y, x1, y + 1), thresh)]
    if not rows:
        return None
    cols = [x for x in range(x0, x1) if ink_pixels(img, (x, rows[0], x + 1, rows[-1] + 1), thresh)]
    return (cols[0], rows[0], cols[-1], rows[-1])


def cell_rect(idx):
    """
    (x, y, width, height) of grid cell `idx`: the first three share the top row at one third of the
    measure each; the last two share the foot row at half the content width less the gutter.
    """
    if idx < TOP_COLS:
        return (GRID_X0 + idx * (TOP_CELL_W + GUTTER), GRID_TOP, TOP_CELL_W, CELL_H)
    j = idx - TOP_COLS
    return (X0 + j * (BOT_CELL_W + GUTTER), GRID_TOP + CELL_H + GUTTER, BOT_CELL_W, CELL_H)


def check_labels():
    """
    Every tag and every label line must sit inside its own cell and inside the content box, and no
    two of them may touch. Raises SystemExit naming the offending pair.
    """
    cells = {}
    for idx, story in enumerate(GRID_STORIES):
        cx, cy, cw, ch = cell_rect(idx)
        cells[story["icon"]] = (cx, cy, cx + cw, cy + ch)

    labs = [it for it in ITEMS if it["name"].startswith(("label:", "tag:"))]

    for it in labs:
        b = it["box"]
        if b[0] < X0 - 0.5 or b[2] > X1 + 0.5:
            raise SystemExit("label crosses the content box: %s spans x %.1f -> %.1f (box %d..%d)"
                             % (it["name"], b[0], b[2], X0, X1))
        if it["name"].startswith("label:"):
            icon = it["name"].split(":")[1]
            right = cells[icon][2]
            if b[2] > right + 0.5:
                raise SystemExit("label overruns its cell: %s right edge %.1f > cell right %d"
                                 % (it["name"], b[2], right))

    for i, a in enumerate(labs):
        for b in labs[i + 1:]:
            if _overlap(a["box"], b["box"]):
                raise SystemExit("labels collide: %s (%.0f,%.0f,%.0f,%.0f) hits %s (%.0f,%.0f,%.0f,%.0f)"
                                 % (a["name"], *a["box"], b["name"], *b["box"]))
    return labs


def smallest_label_gap(labs):
    best = (None, None, 1e9)
    for i, a in enumerate(labs):
        for b in labs[i + 1:]:
            if _overlap(a["box"], b["box"]):
                continue
            g = _separation(a["box"], b["box"])
            if g < best[2]:
                best = (a["name"], b["name"], g)
    return best


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    img = build()

    if img.size != (PAGE, PAGE):
        raise SystemExit("wrong size: %r" % (img.size,))
    img.save(out, "PNG", optimize=True)

    size_bytes = os.path.getsize(out)
    if size_bytes > 1048576:
        raise SystemExit("PNG over 1 MiB: %d bytes" % size_bytes)

    print("PAGE")
    print("  canvas            %d x %d  %s" % (img.size[0], img.size[1], img.mode))
    print("  content box       x %d -> %d  (%d wide)" % (X0, X1, CONTENT_W))

    print("\nBANDS  (y, height)")
    for name, (y, h) in [
        ("top rule", BAND_TOP_RULE),
        ("masthead", BAND_MASTHEAD),
        ("hairline", BAND_MAST_RULE),
        ("date bar", BAND_DATEBAR),
        ("kicker row", BAND_KICKER),
        ("hairline", BAND_KICK_RULE),
        ("lead band", BAND_LEAD),
        ("brief grid", BAND_GRID),
        ("footer strip", BAND_FOOTER),
    ]:
        print("  %-14s y=%4d  h=%3d   ends %4d" % (name, y, h, y + h))

    print("\nLEAD BAND")
    print("  panel             x %d -> %d, y %d -> %d  (%d x %d)"
          % (PANEL[0], PANEL[2], PANEL[1], PANEL[3], PANEL[2] - PANEL[0], PANEL[3] - PANEL[1]))
    for it in ITEMS:
        if it["name"] in ("lead_l1", "lead_l2", "standfirst"):
            b = it["box"]
            print("  %-12s ink %6.1f wide, right edge %6.1f, y %4.0f -> %4.0f"
                  % (it["name"], b[2] - b[0], b[2], b[1], b[3]))

    print("\nGRID  (3 across the top at %d, 2 across the foot at %d, gutter %d, cell h %d)"
          % (TOP_CELL_W, BOT_CELL_W, GUTTER, CELL_H))
    print("  top row   x %d -> %d   (%d + %d + %d + 2 x %d)"
          % (GRID_X0, GRID_X0 + TOP_COLS * TOP_CELL_W + (TOP_COLS - 1) * GUTTER,
             TOP_CELL_W, TOP_CELL_W, TOP_CELL_W, GUTTER))
    print("  foot row  x %d -> %d   (%d + %d + %d)"
          % (X0, X0 + BOT_COLS * BOT_CELL_W + (BOT_COLS - 1) * GUTTER,
             BOT_CELL_W, BOT_CELL_W, GUTTER))
    for idx, story in enumerate(GRID_STORIES):
        cx, cy, cw, ch = cell_rect(idx)
        row = "top" if idx < TOP_COLS else "foot"
        print("  %-4s cell x %3d -> %3d  y %3d -> %3d  (%3d x %d)   %s / %s"
              % (row, cx, cx + cw, cy, cy + ch, cw, ch, story["tag"], story["icon"]))

    print("\nPICTOGRAMS  (ink pixels inside the 54x54 box — floor 300)")
    for idx, story in enumerate(GRID_STORIES):
        cx, cy, cw, ch = cell_rect(idx)
        ibox = (cx, cy, cx + ICON, cy + ICON)
        n = ink_pixels(img, ibox)
        if n < 300:
            raise SystemExit("pictogram %r has only %d ink px inside %s (floor 300)"
                             % (story["icon"], n, ibox))
        print("  %-6s box x %3d -> %3d  y %3d -> %3d   ink %4d px   %s"
              % (story["icon"], ibox[0], ibox[2], ibox[1], ibox[3], n, story["tag"]))

    labs = check_labels()
    gap = smallest_label_gap(labs)
    print("\nLABELS  (ink width, right edge, cell right edge, clearance)")
    for idx, story in enumerate(GRID_STORIES):
        cx, cy, cw, ch = cell_rect(idx)
        for it in labs:
            if not it["name"].startswith("label:%s:" % story["icon"]):
                continue
            b = it["box"]
            print("  %-16s %6.1f wide  right %6.1f  cell right %3d  clear %5.1f  ink h %4.1f"
                  % (it["name"], b[2] - b[0], b[2], cx + cw, cx + cw - b[2], b[3] - b[1]))
    for it in labs:
        if it["name"].startswith("tag:"):
            b = it["box"]
            print("  %-16s %6.1f wide  right %6.1f  (region tag, Ubuntu Mono 17)"
                  % (it["name"], b[2] - b[0], b[2]))
    n_coll = count_collisions()
    print("  labels/tags       %d measured, 0 crossing the content box, %d collisions"
          % (len(labs), n_coll))
    if n_coll:
        raise SystemExit("%d colliding pair(s) on the page" % n_coll)
    print("  smallest label gap %.1f px  between %s and %s" % (gap[2], gap[0], gap[1]))

    print("\nLEAD  (ink width, right edge, content right edge)")
    for it in ITEMS:
        if it["name"] in ("lead_l1", "lead_l2", "standfirst", "kicker_left", "kicker_right"):
            b = it["box"]
            print("  %-12s %6.1f wide  right %6.1f  clear %5.1f"
                  % (it["name"], b[2] - b[0], b[2], X1 - b[2]))

    pext = ink_extent(img, PANEL)
    if pext is None:
        raise SystemExit("the lead panel drew nothing inside %r" % (PANEL,))
    l1 = next(it["box"] for it in ITEMS if it["name"] == "lead_l1")
    print("  panel ink         y %d -> %d inside its %d x %d slot; headline ink starts y %.0f"
          % (pext[1], pext[3], PANEL[2] - PANEL[0], PANEL[3] - PANEL[1], l1[1]))
    print("  panel to head     %.0f px of real air (the slot's empty foot, not a collision)"
          % (l1[1] - pext[3]))

    def probe(nm):
        for it in ITEMS:
            if it["name"] == nm:
                return it["size"], it["box"][3] - it["box"][1]
        return None, None

    print("\nTYPE  (face, size, ink height) — measured, not asserted")
    for face, nm, note in [
        ("DejaVu Serif Bold", "masthead", "masthead"),
        ("Anton", "date", "date bar"),
        ("Ubuntu Mono", "kicker_left", "kicker"),
        ("Anton", "lead_l1", "lead headline"),
        ("Inter Medium", "standfirst", "standfirst"),
        ("Ubuntu Mono", "tag:UNITED_NATIONS", "region tags"),
        ("Anton", "label:unsc:1", "grid labels"),
        ("Inter", "foot_line", "footer line"),
        ("Ubuntu Mono", "foot_bar_text", "footer bar"),
    ]:
        size, ink = probe(nm)
        print("  %-18s %3s px   ink %5.1f px   %s" % (face, size, ink, note))
    print("  smallest face     %d px — floor is 17 px"
          % min(it["size"] for it in ITEMS if it["kind"] == "text" and it["size"]))
    print("  judge-critical    lead 50 / labels 30 / date 38 (all >= 30 px as specified)")

    gaps = smallest_gap()
    print("\nSPACING")
    print("  smallest gap      %.1f px  between %s and %s" % (gaps[2], gaps[0], gaps[1]))
    print("  edge margin       %d px, nothing outside x %d..%d / y %d..%d"
          % (EDGE, EDGE, PAGE - EDGE, EDGE, PAGE - EDGE))
    print("  pairs checked     %d" % len(pairs_checked()))
    print("  collisions        %d" % count_collisions())

    print("\nFILE")
    print("  %s" % os.path.abspath(out))
    print("  bytes             %d  (cap 1048576, %s)"
          % (size_bytes, "ok" if size_bytes <= 1048576 else "OVER"))
    print("  md5               %s" % md5_of(out))
    print("  stories           %d in STORIES: %d grid + lead + standfirst"
          % (len(STORIES), len(GRID_STORIES)))
    print("  fields            %s" % ", ".join(s["tag"] for s in GRID_STORIES))

    # ---- previews: what the judge actually sees -----------------------------------------
    here = os.path.dirname(os.path.abspath(out)) or "."
    print("\nPREVIEWS  (LANCZOS, beside the page)")
    for px in (480, 300):
        prev = img.resize((px, px), Image.Resampling.LANCZOS)
        path = os.path.join(here, "preview_%d.png" % px)
        prev.save(path, "PNG", optimize=True)
        print("  preview_%d.png   %6d bytes   %d x %d" % (px, os.path.getsize(path), px, px))

    # ---- the gate ----------------------------------------------------------------------
    with open(out, "rb") as fh:
        magic = fh.read(8)
    ok_png = magic == b"\x89PNG\r\n\x1a\n"
    print("\nGATE")
    print("  format            %s" % ("PNG" if ok_png else "NOT PNG"))
    print("  dimensions        %d x %d  (cap 1024 x 1024, %s)"
          % (img.size[0], img.size[1], "ok" if max(img.size) <= 1024 else "OVER"))
    print("  bytes             %d  (cap 1048576, %s)"
          % (size_bytes, "ok" if size_bytes <= 1048576 else "OVER"))
    if not ok_png or max(img.size) > 1024 or size_bytes > 1048576:
        raise SystemExit("gate failed: png=%s size=%r bytes=%d" % (ok_png, img.size, size_bytes))
    print("  gate              PASS")


if __name__ == "__main__":
    main()
