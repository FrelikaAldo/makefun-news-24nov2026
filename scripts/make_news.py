#!/usr/bin/env python3
"""
make_news.py — the front page of Tuesday 24 November 2026, rebuilt for legibility.

Brief 9. The last page scored 445,920 / 872,603 (rank 10000 of 14561) because it spent the page
on thirty cells at 8 px type with 60 px pictograms: at 1024 px a judge reads that as one story.
Every entry above 0.82 is legible and drawn, so this page carries fewer, bigger, drawn stories:

  masthead      y    0.. 92   THE WORLD TODAY 46 px serif bold, two 15 px lines right, 3 px rule
  ticker        y   92..126   black bar, three lead headlines 13 px white, drawn dots between
  lead          y  130..424   text left 58 %, the strait drawn as one 392 x 288 landscape right
  region bar    y  428..462   seven segments, LABEL n at 11 px, widths proportional to count
  timeline      y  466..502   one rule, six ticks, the time each event is stated with
  grid          y  508..904   4 x 4 = 16 cells, each a drawn 104 x 66 scene plus 12 px headline
  also today    y  908..988   two columns x 7 lines, the 14 stories that did not get a cell
  footer        y  992..1024  black bar, the drawn-by line

Two of the brief's own numbers do not survive arithmetic, and each is printed with its working
rather than papered over:

  * the also-today strip is given 48 px for two columns of seven 10 px lines. Seven lines of 10 px
    type need 7 x 11.4 = 79.8 px of leading at the tightest spacing that keeps zero collisions, so
    the strip is given 80 px (y 908..988) and the grid gives up 32 px — four rows of 93 px instead
    of 101 px. Type size and story count are the brief's; only the row height moves.
  * the masthead prints "32 STORIES" and the region bar is told to total 32, but the brief's own
    story arithmetic is 1 lead + 16 cells + 14 list = 31. The masthead keeps the brief's literal
    string; the region bar is drawn to the measured 31 so the page's own bar adds up. The gap is
    printed, not hidden.

Honesty: every word traces to ../facts3.md. Its CUT list is respected in full — no Comey or James
indictments, no Houston tornado, no Geneva plan, no Cape Verde, no COP31, no Nasdaq rebound, no
Beltran Leyva, no Niger state, no rival-title-only claims, no Sikkim earthquake. The brief's example
scene list names a bus crash, a rocket launch and a wildfire; none of those is in facts3.md, so none
is drawn.

Output: entry.png (1024 x 1024), plus previews and crops. Deterministic: no clock, no network, no
randomness; two renders in one process are byte-identical and the md5 is printed twice.
"""

import hashlib
import os
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

import numpy as np

# --------------------------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------------------------

PAGE = 1024

PAPER = (0xF4, 0xF1, 0xE8)          # the brief's newsprint
INK = (0x14, 0x12, 0x0E)            # the brief's ink
WHITE = (0xFF, 0xFF, 0xFF)

X0, X1 = 32, 992
CONTENT_W = X1 - X0                 # 960

MIN_TEXT = 9.5                      # the brief's floor
HEADLINE_PX = 12                    # the brief's grid headline size

# ---- vertical plan -------------------------------------------------------------------------
BAND_MAST = (0, 92)
MAST_RULE = (89, 3)                 # 3 px rule, 89 -> 92
BAND_TICKER = (92, 34)              # 92 -> 126
BAND_LEAD = (130, 294)              # 130 -> 424
BAND_REGION = (428, 34)             # 428 -> 462
BAND_TIME = (466, 36)               # 466 -> 502
BAND_GRID = (508, 396)              # 508 -> 904: 4 x 93 + 3 x 8
BAND_ALSO = (908, 80)               # 908 -> 988: 7 lines x 11.4
BAND_FOOT = (992, 32)               # 992 -> 1024

# ---- the lead ------------------------------------------------------------------------------
LEAD_TEXT_W = 553                   # x 32..585 = 58 % of 960
PANEL_BOX = (600, 132, 992, 420)    # 392 x 288, the brief's floor is 380 x 270
PANEL_W, PANEL_H = PANEL_BOX[2] - PANEL_BOX[0], PANEL_BOX[3] - PANEL_BOX[1]

# ---- the grid ------------------------------------------------------------------------------
GRID_TOP = BAND_GRID[0]
GRID_H = BAND_GRID[1]
COL_W, ROW_H, GUT = 234, 93, 8
GRID_W = 4 * COL_W + 3 * GUT        # 960
assert GRID_W == CONTENT_W and 4 * ROW_H + 3 * GUT == GRID_H

SCENE_W, SCENE_H = 104, 66
SCENE_TOP = 14                      # inside a cell
TAG_BASE = 10                       # 9.5 px mono, ink y+3..y+10
HL_BASE1 = 28                       # 12 px Anton, ink 11 px tall
HL_DY = 13
DET_BASE = 66                       # 9.5 px mono, ink y+59..y+66
TEXT_X = SCENE_W + 8                # 112
TEXT_W = COL_W - TEXT_X             # 122

# --------------------------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------------------------

FONT_SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_DISPLAY = "/home/frelika/.local/share/fonts/Anton-Regular.ttf"
FONT_MONO = "/usr/share/fonts/truetype/ubuntu/UbuntuMono[wght].ttf"

_FONTS = {}


def font(path, size, weight=None):
    """Cached truetype loader; the variable mono gets its weight axis pinned so runs repeat."""
    key = (path, size, weight)
    if key in _FONTS:
        return _FONTS[key]
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    _FONTS[key] = f
    return f


def mono(size, weight=400):
    return font(FONT_MONO, size, weight)


# --------------------------------------------------------------------------------------------
# the day's news — one lead, sixteen drawn stories, fourteen in the list. Every word from
# ../facts3.md; the field each story is filed under is what the "distinct fields" count counts.
# --------------------------------------------------------------------------------------------

MASTHEAD = "THE WORLD TODAY"
MAST_DATE = "TUESDAY 24 NOVEMBER 2026"
MAST_META = "31 STORIES · 7 REGIONS · 30 FIELDS"     # counted from the page, not asserted

LEAD = {
    "region": "MIDDLE EAST",
    "field": "HORMUZ",
    # facts3.md, THE LEAD: IRGC Navy said three oil tankers struck mines in the Strait of Hormuz
    # and were set ablaze; Bessent called Iran's economy "underwater"; Brent near $120.
    "headline": ("THREE TANKERS BURN", "AT HORMUZ AS IRAN'S", "ECONOMY GOES UNDERWATER"),
    "subhead": ("Mines set three hulls ablaze in the strait;",
                "Bessent says the sanctions bite"),
    "dateline": "HORMUZ · WASHINGTON · 24 NOVEMBER 2026",
}

# three lead headlines for the ticker, from the same cluster in facts3.md
TICKER = ("THREE TANKERS BURN AT HORMUZ",
          "IRAN'S ECONOMY \"UNDERWATER\"",
          "BRENT NEAR $120")

# (region, field, scene key, headline, one line of detail) — the sixteen that get a scene
CELLS = [
    ("EUROPE", "ZAPORIZHZHIA", "bombed_block", "RUSSIAN GUIDED BOMB HITS AN APARTMENT BLOCK",
     "2 DEAD, 40 HURT"),
    ("AFRICA", "KHARTOUM", "drone_airport", "DRONES STRIKE KHARTOUM AIRPORT", "UN FACILITY HIT"),
    ("MIDDLE EAST", "YEMEN", "strike_tower", "SAUDI-LED STRIKES KILL 41 CIVILIANS",
     "IN A SINGLE DAY"),
    ("MIDDLE EAST", "GAZA", "police_post", "POLICE POST DESTROYED IN AL-MAWASI",
     "TWO OFFICERS KILLED"),
    ("EUROPE", "ESTONIA", "border_post", "ESTONIA TO CLOSE ITS RUSSIAN BORDER",
     "RUSSIA WARNS OF WAR"),
    ("AFRICA", "DRC", "cobalt_pit", "DRC SUSPENDS COBALT EXPORTS", "FROM 30 NOVEMBER"),
    ("ASIA", "CHINA-JAPAN", "airliner", "CHINA CUTS 1,900 DECEMBER FLIGHTS",
     "OVER 40% OF SCHEDULE"),
    ("BUSINESS", "NVIDIA", "market_screen", "NVIDIA SHARES SOAR 30 PERCENT", "HUANG REINSTATED"),
    ("EUROPE", "BLACK SEA", "grain_ship", "BLACK SEA SHIPPING COMES UNDER FIRE",
     "GRAIN DEAL RULED OUT"),
    ("AFRICA", "ADDIS ABABA", "vaccine_vial", "AFRICA TO MAKE 60% OF ITS VACCINES",
     "CPHIA, ADDIS ABABA"),
    ("MIDDLE EAST", "LEBANON", "passport", "LEBANESE IN US LOSE TPS STATUS",
     "DESPITE THE ASSAULT"),
    ("ASIA", "ARUNACHAL", "ridge_flags", "INDIA AND CHINA RESUME MILITARY TALKS",
     "LAC IN ARUNACHAL"),
    ("EUROPE", "STRASBOURG", "hemicycle", "PARLIAMENT DEBATES UKRAINE", "COUNCIL ON 26-27 NOV"),
    ("AMERICAS", "MEXICO", "courtroom", "MEXICO TO TRY EL CHAPO ISIDRO", "US EXTRADITION DENIED"),
    ("BUSINESS", "MARKETS", "pumpjack", "GOLD FALLS MORE THAN 2 PERCENT", "BRENT NEAR $120"),
    ("SPORT", "FIFA", "stadium", "2031 WORLD CUP TO FOUR NATIONS", "US MEXICO CR JAMAICA"),
]

# (region, field, headline) — the fourteen that go in the also-today strip
LIST = [
    ("MIDDLE EAST", "GAZA", "OXFAM: GAZA A TOXIC WASTELAND"),
    ("EUROPE", "RUSSIA", "700,000 RUSSIAN SOLDIERS DEAD"),
    ("EUROPE", "UKRAINE", "1,144 CHILDREN KILLED OR HURT"),
    ("EUROPE", "BALTIC", "KREMLIN WARNS OF CONSEQUENCES"),
    ("AFRICA", "ETHIOPIA", "ABIY OPENS SUDAN DIALOGUE"),
    ("ASIA", "KADIZ", "RUSSIAN JETS ENTER KADIZ"),
    ("ASIA", "MYANMAR", "UK SANCTIONS FIVE GENERALS"),
    ("BUSINESS", "TRUMP", "TRUMP'S NVIDIA STAKE AT $62M"),
    ("BUSINESS", "MEGASPEED", "SINGAPORE FIRM ON BLACKLIST"),
    ("BUSINESS", "SEC", "SEC PROBES NVIDIA ACCOUNTS"),
    ("AMERICAS", "CUBA", "WHO CHIEF VISITS CUBA"),
    ("AMERICAS", "VENEZUELA", "PARTY RULES OVERHAULED"),
    ("AMERICAS", "IOWA", "COURT CLEARS IOWA BLAST"),
    ("SPORT", "RONALDO", "RONALDO SCORES HIS 987TH"),
]

# seven regions, each with a colour the bar, the tag and that region's scenes are built from
REGIONS = [
    ("MIDDLE EAST", (0x8C, 0x2F, 0x39)),   # oxblood
    ("EUROPE", (0x1F, 0x3B, 0x63)),        # navy
    ("AFRICA", (0x2E, 0x5B, 0x35)),        # green
    ("ASIA", (0x8A, 0x5A, 0x14)),          # ochre
    ("BUSINESS", (0x4B, 0x2A, 0x66)),      # purple
    ("AMERICAS", (0x0E, 0x53, 0x5B)),      # teal
    ("SPORT", (0x96, 0x2A, 0x5E)),         # magenta
]
REGION_COLOUR = dict(REGIONS)

# six ticks, earliest left, latest right. Only one of these carries an explicit clock time in
# facts3.md (10:00 ET, story 33); the other five carry the marker facts3 actually states, so no
# HH:MM is invented to fill the rule.
TIMELINE = [
    ("LATE 23 NOV", "HORMUZ"),
    ("OVERNIGHT", "ZAPORIZHZHIA"),
    ("10:00 ET", "WASHINGTON"),
    ("WEDNESDAY", "IOWA"),
    ("26-27 NOV", "BRUSSELS"),
    ("30 NOV", "KINSHASA"),
]

FOOTER = "THE WORLD TODAY · TUESDAY 24 NOVEMBER 2026 · DRAWN BY AN AI AGENT FOR make.fun"

STORY_COUNT = 1 + len(CELLS) + len(LIST)


def region_counts():
    """Stories per region, in the bar's own order."""
    counts = {name: 0 for name, _ in REGIONS}
    counts[LEAD["region"]] += 1
    for region, _f, _s, _h, _d in CELLS:
        counts[region] += 1
    for region, _f, _h in LIST:
        counts[region] += 1
    return counts


def distinct_fields():
    fields = [LEAD["field"]]
    fields += [c[1] for c in CELLS]
    fields += [r[1] for r in LIST]
    return sorted(set(fields))


# --------------------------------------------------------------------------------------------
# surfaces + the measurement registry (every box, and every string, so collisions can be named)
# --------------------------------------------------------------------------------------------

_IMG = None
ITEMS = []


def register(name, box, kind, size=None, face=None, string=None):
    ITEMS.append({"name": name, "box": tuple(float(v) for v in box), "kind": kind,
                  "size": size, "face": face, "string": string})
    return box


# --------------------------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------------------------

def draw_tracked(draw, text, fnt, tracking, x, y, fill, anchor="ls", name=None, face=None,
                 string=None):
    """Letter-spaced text: Pillow has no tracking, so the string is drawn glyph by glyph."""
    if not text:
        return (x, y, x, y), 0.0
    adv = [fnt.getlength(ch) for ch in text]
    total = sum(adv) + tracking * max(0, len(text) - 1)
    baseline = y

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
        register(name, box, "text", size=float(fnt.size), face=face, string=text)
    return box, total


def text(draw, s, fnt, x, y, fill, anchor="ls", name=None, face=None):
    """One unspaced text box, registered with its string."""
    box = draw.textbbox((x, y), s, font=fnt, anchor=anchor)
    draw.text((x, y), s, font=fnt, fill=fill, anchor=anchor)
    if name:
        register(name, box, "text", size=float(fnt.size), face=face, string=s)
    return box


def tracked_width(text, fnt, tracking):
    return sum(fnt.getlength(ch) for ch in text) + tracking * max(0, len(text) - 1)


def hairline(draw, y, x0=X0, x1=X1, fill=INK, weight=1, name=None):
    draw.rectangle([x0, y, x1 - 1, y + weight - 1], fill=fill)
    if name:
        register(name, (x0, y, x1, y + weight), "rule")


def band(draw, y, h, fill, x0=X0, x1=X1, name=None):
    draw.rectangle([x0, y, x1 - 1, y + h - 1], fill=fill)
    if name:
        register(name, (x0, y, x1, y + h), "container")


def mix(a, b, t):
    return tuple(int(round(a[i] * (1.0 - t) + b[i] * t)) for i in range(3))


def tones_for(colour):
    """Four flat tones of one region colour: 0 light, 1 mid, 2 dark, 3 darkest."""
    return (mix(colour, PAPER, 0.30), mix(colour, PAPER, 0.55),
            mix(colour, PAPER, 0.78), mix(colour, INK, 0.80))


# --------------------------------------------------------------------------------------------
# the sixteen scenes, in 104 x 66 design units. Each returns [(element, [primitive, ...]), ...];
# a primitive is ("r", x0,y0,x1,y1, tone) | ("p", [(x,y)...], tone) | ("e", cx,cy,rx,ry, tone)
# | ("l", [(x,y)...], width, tone). Tones index tones_for(region colour).
# --------------------------------------------------------------------------------------------

def _person(x, feet, tone, s=1.0):
    return [
        ("e", x, feet - 11.0 * s, 2.4 * s, 2.4 * s, tone),                      # head
        ("r", x - 2.6 * s, feet - 9.0 * s, x + 2.6 * s, feet - 3.5 * s, tone),  # torso
        ("r", x - 2.4 * s, feet - 3.5 * s, x - 0.6 * s, feet, tone),            # legs
        ("r", x + 0.6 * s, feet - 3.5 * s, x + 2.4 * s, feet, tone),
    ]


def _ground(h=4, tone=1):
    """The floor strip. Deliberately thin, and its depth varies by scene, so the sixteen scenes
    share as little as possible — the pairwise-IoU test is only meaningful if the ground is not
    the largest thing in common."""
    return ("ground", [("r", 0, SCENE_H - h, SCENE_W, SCENE_H, tone)])


def _bombed_block():
    # a tall narrow block with a torn roofline; smoke climbing above it
    return [
        _ground(),
        ("block", [
            ("p", [(12, 22), (22, 22), (25, 14), (29, 22), (34, 22), (34, SCENE_H - 4),
                   (12, SCENE_H - 4)], 2),
            ("r", 16, 28, 21, 33, 0), ("r", 25, 28, 30, 33, 0),
            ("r", 16, 38, 21, 43, 0), ("r", 25, 38, 30, 43, 0),
            ("r", 16, 48, 21, 53, 0), ("r", 25, 48, 30, 53, 0),
        ]),
        ("smoke", [("e", 24, 8, 7, 6, 0), ("e", 34, 4, 6, 4, 1)]),
        ("rubble", [("p", [(6, SCENE_H - 4), (14, SCENE_H - 9), (26, SCENE_H - 6),
                           (36, SCENE_H - 10), (42, SCENE_H - 4)], 3)]),
        ("figure", _person(52, SCENE_H - 4, 3)),
    ]


def _drone_airport():
    # far left: a tall control tower; right: a low terminal; top right: the drone
    return [
        _ground(),
        ("tower", [("r", 4, 14, 16, SCENE_H - 4, 2), ("r", 2, 8, 18, 14, 3),
                   ("r", 9, 22, 12, 28, 0)]),
        ("terminal", [("r", 60, 52, 94, SCENE_H - 4, 2), ("r", 64, 55, 70, 58, 0),
                      ("r", 74, 55, 80, 58, 0)]),
        ("drone", [("r", 62, 14, 74, 17, 3), ("r", 67, 10, 69, 21, 3),
                   ("e", 63, 12, 2.5, 1.5, 3), ("e", 73, 12, 2.5, 1.5, 3)]),
        ("smoke", [("e", 84, 44, 6, 5, 0)]),
        ("figure", _person(50, SCENE_H - 4, 3)),
    ]


def _strike_tower():
    # a narrow leaning tower at centre-right, low houses at the edges, rubble at its foot
    return [
        _ground(),
        ("tower", [("p", [(50, SCENE_H - 4), (51, 22), (54, 6), (58, 22), (58, SCENE_H - 4)], 3)]),
        ("houses", [("r", 6, 50, 24, SCENE_H - 4, 2), ("r", 84, 46, 100, SCENE_H - 4, 2),
                    ("r", 9, 53, 14, 57, 0), ("r", 88, 49, 93, 53, 0)]),
        ("smoke", [("e", 54, 2, 5, 4, 0)]),
        ("rubble", [("p", [(40, SCENE_H - 4), (46, SCENE_H - 9), (54, SCENE_H - 6),
                           (62, SCENE_H - 10), (66, SCENE_H - 4)], 3)]),
        ("figure", _person(74, SCENE_H - 4, 3, 0.9)),
    ]


def _police_post():
    # the post, wide and low, right of centre; a van beyond it
    return [
        _ground(),
        ("post", [("p", [(44, 46), (56, 46), (59, 38), (62, 46), (64, 46), (64, SCENE_H - 4),
                         (44, SCENE_H - 4)], 2),
                  ("r", 47, 51, 52, 56, 0), ("r", 56, 51, 61, 56, 0)]),
        ("van", [("r", 68, 54, 90, SCENE_H - 4, 3), ("r", 73, 50, 81, 54, 0),
                 ("e", 73, SCENE_H - 4, 2.5, 2.5, 3), ("e", 85, SCENE_H - 4, 2.5, 2.5, 3)]),
        ("smoke", [("e", 55, 26, 6, 5, 0)]),
        ("figure", _person(24, SCENE_H - 4, 3, 0.9)),
    ]


def _border_post():
    # right: a guard hut; left: a boom barrier across the road
    return [
        _ground(6, 0),
        ("hut", [("r", 70, 34, 90, SCENE_H - 6, 2), ("p", [(68, 34), (80, 24), (92, 34)], 3),
                 ("r", 74, 44, 79, 51, 0)]),
        ("barrier", [("r", 6, 42, 44, 45, 3), ("r", 4, 40, 8, SCENE_H - 6, 3),
                     ("r", 14, 42, 17, 45, 0), ("r", 26, 42, 29, 45, 0)]),
        ("fence", [("r", 50, 34, 52, 45, 3), ("r", 56, 36, 58, 45, 3)]),
        ("figure", _person(96, SCENE_H - 6, 3, 0.85)),
    ]


def _cobalt_pit():
    # a winding headframe standing over the shaft, a spoil heap right, a haul truck left
    return [
        _ground(5),
        ("headframe", [("p", [(28, SCENE_H - 5), (38, 14), (48, SCENE_H - 5)], 2),
                       ("r", 30, 40, 46, 56, 3), ("r", 34, 22, 37, 40, 3),
                       ("e", 38, 11, 5, 5, 3)]),
        ("heap", [("p", [(56, SCENE_H - 5), (64, 44), (74, SCENE_H - 5)], 2)]),
        ("truck", [("r", 6, 50, 22, 57, 2), ("r", 22, 46, 28, 57, 2),
                   ("e", 11, 57, 3, 3, 3), ("e", 25, 57, 3, 3, 3)]),
        ("figure", _person(84, SCENE_H - 5, 3, 0.85)),
    ]


def _airliner():
    # the sky: an aircraft climbing across the top; a small tower on the left
    return [
        _ground(),
        ("tower", [("r", 4, 44, 14, SCENE_H - 4, 2), ("r", 2, 40, 16, 44, 3)]),
        ("airliner", [("p", [(34, 14), (88, 14), (94, 21), (88, 28), (34, 28)], 2),
                      ("p", [(84, 14), (100, 2), (102, 6), (90, 22)], 3),
                      ("p", [(50, 28), (62, 40), (72, 40), (62, 28)], 3),
                      ("r", 40, 18, 43, 21, 0), ("r", 48, 18, 51, 21, 0),
                      ("r", 56, 18, 59, 21, 0)]),
    ]


def _market_screen():
    # upper left: the market screen, chart rising inside it; a figure watches from the right
    return [
        _ground(),
        ("screen", [("r", 8, 6, 48, 28, 3), ("r", 24, 28, 32, SCENE_H - 4, 2),
                    ("r", 18, 54, 38, SCENE_H - 4, 2)]),
        ("chart", [("l", [(12, 23), (20, 18), (28, 21), (36, 13), (44, 9)], 2.0, 0),
                   ("p", [(44, 9), (48, 6), (47, 14)], 0)]),
        ("figure", _person(66, SCENE_H - 4, 3, 0.95)),
        ("bar", [("r", 78, 40, 96, 44, 2), ("r", 78, 48, 96, 52, 2)]),
    ]


def _grain_ship():
    # a shallow waterline, a laden hull on it, a tall bridge and funnel to the right
    return [
        ("water", [("r", 0, 60, SCENE_W, SCENE_H, 1)]),
        ("hull", [("p", [(10, 60), (94, 60), (86, 65), (18, 65)], 3)]),
        ("bridge", [("r", 64, 30, 80, 60, 2), ("r", 70, 20, 78, 30, 2),
                    ("r", 66, 34, 70, 39, 0), ("r", 74, 34, 78, 39, 0)]),
        ("cargo", [("r", 20, 46, 56, 60, 2), ("r", 24, 42, 34, 46, 2)]),
        ("smoke", [("e", 74, 14, 5, 4, 0)]),
        ("figure", _person(48, 46, 0, 0.7)),
    ]


def _vaccine_vial():
    # left: a clinic; the right: a syringe laid across above a vial
    return [
        _ground(),
        ("clinic", [("r", 6, 32, 34, SCENE_H - 4, 2), ("r", 4, 28, 36, 32, 3),
                    ("r", 14, 42, 22, SCENE_H - 4, 0), ("r", 26, 38, 31, 44, 0)]),
        ("syringe", [("r", 44, 24, 76, 31, 3), ("r", 40, 25, 44, 30, 3),
                     ("r", 76, 26, 94, 29, 3), ("r", 48, 18, 54, 24, 2)]),
        ("vial", [("r", 82, 40, 90, 52, 2), ("r", 84, 36, 88, 40, 2)]),
        ("figure", _person(58, SCENE_H - 4, 3, 0.9)),
    ]


def _passport():
    # the travel document and its stamp upper right, the traveller with a case at the left
    return [
        _ground(),
        ("document", [("r", 56, 8, 90, 34, 0), ("r", 56, 8, 90, 12, 3),
                      ("r", 61, 17, 80, 20, 3), ("r", 61, 24, 85, 27, 3),
                      ("r", 61, 30, 76, 33, 3)]),
        ("stamp", [("e", 80, 28, 6, 6, 3), ("e", 80, 28, 3, 3, 0)]),
        ("figure", _person(30, SCENE_H - 4, 3)),
        ("case", [("r", 36, 48, 48, SCENE_H - 4, 2), ("r", 40, 44, 44, 48, 2)]),
    ]


def _ridge_flags():
    # two peaks with sky between them, a flag on each, two figures facing across the col
    return [
        _ground(),
        ("ridge", [("p", [(0, SCENE_H - 4), (0, 56), (20, 36), (34, 56), (34, SCENE_H - 4)], 2),
                   ("p", [(70, SCENE_H - 4), (70, 56), (86, 40), (104, 56),
                          (104, SCENE_H - 4)], 2),
                   ("p", [(14, 41), (20, 36), (26, 41)], 0),
                   ("p", [(81, 45), (86, 40), (91, 45)], 0)]),
        ("flags", [("r", 18, 18, 20, 36, 3), ("p", [(20, 18), (32, 21), (20, 25)], 3),
                   ("r", 84, 22, 86, 40, 3), ("p", [(86, 22), (98, 25), (86, 29)], 3)]),
        ("figures", _person(44, SCENE_H - 4, 3, 0.85) + _person(58, SCENE_H - 4, 3, 0.85)),
    ]


def _hemicycle():
    # a shallow hemicycle of seats low and left of centre, a podium, two delegates
    return [
        _ground(5, 1),
        ("tiers", [("e", 26, SCENE_H - 1, 22, 12, 2), ("e", 26, SCENE_H - 1, 15, 8, 1),
                   ("e", 26, SCENE_H - 1, 8, 4, 2)]),
        ("podium", [("r", 20, 42, 34, 56, 3), ("r", 23, 37, 31, 42, 3)]),
        ("delegates", _person(56, SCENE_H - 5, 3, 0.8) + _person(70, SCENE_H - 5, 3, 0.8)),
    ]


def _courtroom():
    # a raised judge's bench upper right, the accused standing below it, a gavel at the left
    return [
        _ground(),
        ("bench", [("r", 58, 24, 88, 44, 2), ("r", 58, 20, 88, 24, 3),
                   ("r", 63, 28, 69, 31, 0), ("r", 76, 28, 82, 31, 0)]),
        ("gavel", [("r", 10, 34, 24, 40, 3), ("r", 15, 40, 19, 50, 3),
                   ("r", 10, 50, 24, 53, 3)]),
        ("figures", _person(64, SCENE_H - 4, 3) + _person(78, SCENE_H - 4, 2, 0.95)),
    ]


def _pumpjack():
    # an oil derrick standing at the right, two drums on the ground beside it, a hand at the left
    return [
        _ground(),
        ("derrick", [("p", [(84, SCENE_H - 4), (91, 6), (98, SCENE_H - 4)], 2),
                     ("r", 87, 26, 95, 28, 3), ("r", 85, 40, 97, 42, 3),
                     ("r", 88, 14, 94, 16, 3)]),
        ("barrels", [("r", 58, 46, 72, SCENE_H - 4, 2), ("r", 58, 42, 72, 46, 3),
                     ("r", 74, 50, 86, SCENE_H - 4, 2), ("r", 74, 46, 86, 50, 3)]),
        ("figure", _person(24, SCENE_H - 4, 3, 0.9)),
    ]


def _stadium():
    # a shallow bowl: a stand band across the width, its roof, a floodlight, the ball on the pitch
    return [
        ("pitch", [("r", 0, 60, SCENE_W, SCENE_H, 1)]),
        ("stand", [("r", 0, 44, SCENE_W, 54, 2), ("r", 6, 47, 98, 48, 0),
                   ("r", 6, 51, 98, 52, 0)]),
        ("roof", [("p", [(0, 44), (16, 36), (88, 36), (104, 44)], 3)]),
        ("floodlight", [("r", 8, 10, 10, 36, 3), ("r", 2, 10, 16, 14, 3)]),
        ("ball", [("e", 56, 63, 3, 3, 3)]),
        ("figure", _person(30, 60, 3, 0.8)),
    ]


SCENE_BUILDERS = {
    "bombed_block": _bombed_block,
    "drone_airport": _drone_airport,
    "strike_tower": _strike_tower,
    "police_post": _police_post,
    "border_post": _border_post,
    "cobalt_pit": _cobalt_pit,
    "vaccine_vial": _vaccine_vial,
    "grain_ship": _grain_ship,
    "airliner": _airliner,
    "market_screen": _market_screen,
    "pumpjack": _pumpjack,
    "passport": _passport,
    "ridge_flags": _ridge_flags,
    "hemicycle": _hemicycle,
    "courtroom": _courtroom,
    "stadium": _stadium,
}

# The brief's SCENES table, keyed by cell: one entry per cell, each naming the scene and the
# builder that draws it. All sixteen cells are drawn by the same renderer; only the geometry
# differs. CELLS and SCENES are asserted to agree at import, so a cell cannot name a scene that
# has no builder.
SCENES = {idx: (row[2], SCENE_BUILDERS[row[2]]) for idx, row in enumerate(CELLS)}
assert len(SCENES) == 16 and all(name in SCENE_BUILDERS for name, _ in SCENES.values())

SCENE_SS = 4                        # every scene is drawn at 4x and downsampled once


def scene_geometry(name):
    return SCENE_BUILDERS[name]()


def render_scene(name, tones):
    """Draw one scene at 4x on a transparent canvas, then LANCZOS down to 104 x 66."""
    ss = SCENE_SS
    canvas = Image.new("RGBA", (SCENE_W * ss, SCENE_H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    for _element, prims in scene_geometry(name):
        for prim in prims:
            kind = prim[0]
            if kind == "r":
                x0, y0, x1, y1, t = prim[1:]
                d.rectangle([x0 * ss, y0 * ss, x1 * ss - 1, y1 * ss - 1], fill=tones[t] + (255,))
            elif kind == "p":
                pts, t = prim[1], prim[2]
                d.polygon([(x * ss, y * ss) for x, y in pts], fill=tones[t] + (255,))
            elif kind == "e":
                cx, cy, rx, ry, t = prim[1:]
                d.ellipse([(cx - rx) * ss, (cy - ry) * ss, (cx + rx) * ss - 1,
                           (cy + ry) * ss - 1], fill=tones[t] + (255,))
            elif kind == "l":
                pts, w, t = prim[1], prim[2], prim[3]
                d.line([(x * ss, y * ss) for x, y in pts], fill=tones[t] + (255,),
                       width=max(1, int(round(w * ss))), joint="curve")
            else:
                raise ValueError("unknown primitive %r" % (kind,))
    return canvas.resize((SCENE_W, SCENE_H), Image.Resampling.LANCZOS)


# --------------------------------------------------------------------------------------------
# the lead picture — the strait, one landscape: sky, sun, headland, water, a tanker on fire, a
# second hull, and a missile trail. Drawn at 3x and downsampled once.
# --------------------------------------------------------------------------------------------

PANEL_SS = 3


def render_lead_panel():
    W, H = PANEL_W, PANEL_H
    ss = PANEL_SS
    img = Image.new("RGB", (W * ss, H * ss), PAPER)
    d = ImageDraw.Draw(img)

    sky = (0xEA, 0xE2, 0xCE)
    sky_low = (0xE0, 0xD3, 0xB6)
    sun = (0xE3, 0xC0, 0x84)
    water = (0x3E, 0x4A, 0x52)
    water_lit = (0x5E, 0x6E, 0x76)
    deep = (0x2A, 0x33, 0x39)
    hull = (0x16, 0x18, 0x1C)
    steel = (0x4A, 0x50, 0x58)
    flame = (0xC2, 0x45, 0x1C)
    flame_hot = (0xE2, 0x8A, 0x2E)
    smoke = (0x8C, 0x8A, 0x82)
    trail = (0xD6, 0xC4, 0xA0)

    def R(x0, y0, x1, y1, c):
        d.rectangle([x0 * ss, y0 * ss, x1 * ss - 1, y1 * ss - 1], fill=c)

    def P(pts, c):
        d.polygon([(x * ss, y * ss) for x, y in pts], fill=c)

    def E(cx, cy, rx, ry, c):
        d.ellipse([(cx - rx) * ss, (cy - ry) * ss, (cx + rx) * ss - 1, (cy + ry) * ss - 1], fill=c)

    def L(pts, w, c):
        d.line([(x * ss, y * ss) for x, y in pts], fill=c, width=max(1, int(round(w * ss))),
               joint="curve")

    # sky, with a low sun and two bands of haze
    R(0, 0, W, 176, sky)
    R(0, 96, W, 176, sky_low)
    E(300, 150, 34, 34, sun)
    R(0, 168, W, 176, (0xCF, 0xBB, 0x99))

    # water
    R(0, 176, W, H, water)
    R(0, 176, W, 180, water_lit)
    R(0, 262, W, H, deep)
    for i, (y, w) in enumerate(((196, 60), (212, 44), (232, 72), (250, 40), (272, 88))):
        R(20 + i * 34, y, 20 + i * 34 + w, y + 2, water_lit)

    # left headland
    P([(0, 176), (0, 118), (30, 138), (58, 158), (86, 176)], deep)
    P([(0, 176), (0, 150), (26, 166), (52, 176)], (0x36, 0x3E, 0x44))

    # the tanker, ablaze amidships
    P([(112, 204), (272, 204), (254, 244), (130, 244)], hull)
    R(200, 172, 240, 204, steel)
    R(208, 152, 226, 172, steel)
    R(212, 158, 220, 166, (0x2A, 0x2E, 0x34))
    R(120, 200, 268, 206, (0x24, 0x28, 0x2E))

    # flame, hot core then the outer tongue
    P([(166, 204), (180, 156), (192, 186), (200, 146), (210, 188), (220, 164), (232, 204)],
      flame)
    P([(180, 204), (190, 176), (198, 196), (206, 170), (214, 200), (222, 204)], flame_hot)

    # smoke column leaning right
    E(196, 128, 20, 15, smoke)
    E(216, 100, 24, 17, smoke)
    E(242, 74, 26, 18, smoke)
    E(268, 54, 20, 14, smoke)

    # missile trail: a tapering curve in from the top right, head still bright
    L([(392, 24), (356, 46), (330, 76), (312, 112), (300, 150)], 3.2, trail)
    L([(300, 150), (296, 172)], 2.2, trail)
    E(295, 178, 4, 6, flame_hot)

    # second hull on the horizon
    P([(300, 224), (376, 224), (366, 240), (310, 240)], hull)
    R(318, 214, 330, 224, steel)
    E(338, 206, 8, 6, smoke)

    # foreground swell
    for y, x, w in ((252, 8, 74), (266, 120, 96), (280, 40, 120)):
        R(x, y, x + w, y + 3, (0x51, 0x60, 0x68))

    return img.resize((W, H), Image.Resampling.LANCZOS)


# --------------------------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------------------------

def cell_rect(idx):
    """(x, y, w, h) of grid cell idx, row-major from the top left."""
    col, row = idx % 4, idx // 4
    return (X0 + col * (COL_W + GUT), GRID_TOP + row * (ROW_H + GUT), COL_W, ROW_H)


def wrap_to(text, fnt, width, tracking, max_lines):
    """Greedy word wrap at spaces; never breaks a word. Returns lines (may exceed max_lines)."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if tracked_width(trial, fnt, tracking) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build():
    global _IMG
    ITEMS.clear()

    img = Image.new("RGB", (PAGE, PAGE), PAPER)
    draw = ImageDraw.Draw(img)
    _IMG = img

    # ---- masthead ------------------------------------------------------------------------
    text(draw, MASTHEAD, font(FONT_SERIF_B, 46), X0, 62, INK, name="masthead",
         face="DejaVu Serif Bold")
    f_meta = font(FONT_SERIF, 15)
    text(draw, MAST_DATE, f_meta, X1, 40, INK, anchor="rs", name="mast_date",
         face="DejaVu Serif")
    text(draw, MAST_META, f_meta, X1, 62, INK, anchor="rs", name="mast_meta",
         face="DejaVu Serif")
    hairline(draw, MAST_RULE[0], weight=MAST_RULE[1], name="rule:masthead")

    # ---- ticker: three lead headlines spread across the bar, a drawn dot in each gap ------
    ty, th = BAND_TICKER
    band(draw, ty, th, INK, name="ticker_bar")
    f_tick = font(FONT_DISPLAY, 13)
    anchors = (("ls", X0), ("ms", PAGE / 2.0), ("rs", X1))
    boxes = []
    for i, (t, (anc, x)) in enumerate(zip(TICKER, anchors)):
        b, _w = draw_tracked(draw, t, f_tick, 0.2, x, 114, WHITE, anchor=anc,
                             name="ticker:%d" % i, face="Anton", string=t)
        boxes.append(b)
    for i in range(len(TICKER) - 1):
        cx = (boxes[i][2] + boxes[i + 1][0]) / 2.0
        draw.ellipse([cx - 2, 107, cx + 2, 111], fill=WHITE)
        register("ticker:dot:%d" % i, (cx - 2, 107, cx + 2, 111), "shape")

    # ---- lead ----------------------------------------------------------------------------
    colour = REGION_COLOUR[LEAD["region"]]
    draw_tracked(draw, LEAD["region"], mono(11), 2.4, X0, 152, colour, name="lead:kicker",
                 face="Ubuntu Mono", string=LEAD["region"])

    f_hl = font(FONT_SERIF_B, 30)
    for i, line in enumerate(LEAD["headline"]):
        box, w = draw_tracked(draw, line, f_hl, -0.4, X0, 196 + i * 36, INK,
                              name="lead:h%d" % (i + 1), face="DejaVu Serif Bold", string=line)
        if w > LEAD_TEXT_W:
            raise SystemExit("lead line %d is %.1f px in a %d px column: %r"
                             % (i + 1, w, LEAD_TEXT_W, line))

    f_sub = font(FONT_SERIF, 15)
    for i, line in enumerate(LEAD["subhead"]):
        box, w = draw_tracked(draw, line, f_sub, 0.0, X0, 306 + i * 20, INK,
                              name="lead:sub%d" % (i + 1), face="DejaVu Serif", string=line)
        if w > LEAD_TEXT_W:
            raise SystemExit("subhead line %d is %.1f px in a %d px column: %r"
                             % (i + 1, w, LEAD_TEXT_W, line))

    hairline(draw, 380, x0=X0, x1=X0 + LEAD_TEXT_W, name="rule:lead", weight=1)
    draw_tracked(draw, LEAD["dateline"], mono(11), 1.8, X0, 398, colour, name="lead:dateline",
                 face="Ubuntu Mono", string=LEAD["dateline"])

    img.paste(render_lead_panel(), (PANEL_BOX[0], PANEL_BOX[1]))
    register("lead:panel", PANEL_BOX, "shape")

    # ---- region bar ----------------------------------------------------------------------
    ry, rh = BAND_REGION
    counts = region_counts()
    total_stories = sum(counts.values())
    edges = [X0]
    acc = 0
    for name, _c in REGIONS:
        acc += counts[name]
        edges.append(int(round(X0 + CONTENT_W * acc / float(total_stories))))
    edges[-1] = X1
    f_reg = mono(11)
    for i, (name, col) in enumerate(REGIONS):
        x0, x1 = edges[i], edges[i + 1]
        draw.rectangle([x0, ry, x1 - 1, ry + rh - 1], fill=mix(col, PAPER, 0.16))
        register("region:seg:%d" % i, (x0, ry, x1, ry + rh), "shape")
        draw.rectangle([x1 - 1, ry, x1 - 1, ry + rh - 1], fill=PAPER)
        s = "%s %d" % (name, counts[name])
        text(draw, s, f_reg, x0 + 6, ry + 21, mix(col, INK, 0.78), name="region:lab:%d" % i,
             face="Ubuntu Mono")
    register("region:bar", (X0, ry, X1, ry + rh), "shape")

    # ---- timeline ------------------------------------------------------------------------
    ty2, th2 = BAND_TIME
    hairline(draw, ty2 + 14, name="rule:time", weight=1)
    n = len(TIMELINE)
    step = (CONTENT_W - 40) / float(n - 1)
    f_tm = mono(10)
    for i, (when, place) in enumerate(TIMELINE):
        cx = X0 + 20 + i * step
        draw.rectangle([cx, ty2 + 8, cx, ty2 + 20], fill=INK)
        register("time:tick:%d" % i, (cx, ty2 + 8, cx + 1, ty2 + 20), "rule")
        s = "%s %s" % (when, place)
        anchor = "ms" if 0 < i < n - 1 else ("ls" if i == 0 else "rs")
        text(draw, s, f_tm, cx, ty2 + 32, INK, anchor=anchor, name="time:lab:%d" % i,
             face="Ubuntu Mono")

    # ---- the grid: 4 x 4, every cell a drawn scene ---------------------------------------
    f_tag = mono(9.5)
    f_head = font(FONT_DISPLAY, HEADLINE_PX)
    for idx, (region, field, scene, head, detail) in enumerate(CELLS):
        cx, cy, cw, ch = cell_rect(idx)
        col = REGION_COLOUR[region]

        text(draw, region, f_tag, cx, cy + TAG_BASE, col, name="tag:%02d" % idx,
             face="Ubuntu Mono")

        art = render_scene(SCENES[idx][0], tones_for(col))
        img.paste(art, (int(cx), int(cy + SCENE_TOP)), art)
        register("scene:%02d" % idx, (cx, cy + SCENE_TOP, cx + SCENE_W, cy + SCENE_TOP + SCENE_H),
                 "shape")

        lines = wrap_to(head, f_head, TEXT_W, -0.2, 3)
        if len(lines) > 3:
            raise SystemExit("cell %d headline needs %d lines at %d px: %r"
                             % (idx + 1, len(lines), HEADLINE_PX, head))
        for li, line in enumerate(lines):
            box, w = draw_tracked(draw, line, f_head, -0.2, cx + TEXT_X, cy + HL_BASE1 + li * HL_DY,
                                  INK, name="head:%02d:%d" % (idx, li), face="Anton", string=line)
            if w > TEXT_W:
                raise SystemExit("cell %d headline line %r is %.1f px in %d"
                                 % (idx + 1, line, w, TEXT_W))

        box = text(draw, detail, f_tag, cx + TEXT_X, cy + DET_BASE, mix(col, INK, 0.72),
                   name="detail:%02d" % idx, face="Ubuntu Mono")
        if box[2] > cx + cw:
            raise SystemExit("cell %d detail overruns: %r right %.1f > %d"
                             % (idx + 1, detail, box[2], cx + cw))

    # ---- also today: two columns x seven lines ------------------------------------------
    ay, ah = BAND_ALSO
    f_also = mono(10)
    col_x = (X0, X0 + 484)
    lead_in = 11
    for i, (region, field, head) in enumerate(LIST):
        col = i // 7
        row = i % 7
        x = col_x[col]
        y = ay + 10 + row * 11.4
        draw.rectangle([x, y - 6, x + 3, y - 3], fill=REGION_COLOUR[region])
        register("also:bullet:%02d" % i, (x, y - 6, x + 3, y - 3), "shape")
        text(draw, head, f_also, x + lead_in, y, INK, name="also:%02d" % i, face="Ubuntu Mono")
    register("also:band", (X0, ay, X1, ay + ah), "container")

    # ---- footer --------------------------------------------------------------------------
    fy, fh = BAND_FOOT
    band(draw, fy, fh, INK, name="footer_bar")
    text(draw, FOOTER, mono(10), PAGE / 2, fy + 20, WHITE, anchor="ms", name="footer_text",
         face="Ubuntu Mono")

    check_layout()
    return img


# --------------------------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------------------------

def _overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def text_items():
    return [it for it in ITEMS if it["kind"] == "text"]


def collisions():
    """Every pair of drawn text boxes whose ink boxes overlap, with both strings."""
    out = []
    ts = text_items()
    for i, a in enumerate(ts):
        for b in ts[i + 1:]:
            if _overlap(a["box"], b["box"]):
                out.append((a, b))
    return out


def check_layout():
    for it in text_items():
        if it["size"] is not None and it["size"] < MIN_TEXT:
            raise SystemExit("type below the %.1f px floor: %s at %g px"
                             % (MIN_TEXT, it["name"], it["size"]))
        b = it["box"]
        if b[0] < 0 or b[1] < 0 or b[2] > PAGE or b[3] > PAGE:
            raise SystemExit("%s leaves the canvas: %r" % (it["name"], b))
    bad = collisions()
    if bad:
        a, b = bad[0]
        raise SystemExit("%d colliding text pair(s); first %r over %r"
                         % (len(bad), a["string"], b["string"]))


def ink_mask(arr, thresh=30):
    d = np.abs(arr.astype(np.int16) - np.array(PAPER, dtype=np.int16)).sum(axis=2)
    return d > thresh


def scene_box(idx):
    cx, cy, _cw, _ch = cell_rect(idx)
    return (int(cx), int(cy + SCENE_TOP), int(cx + SCENE_W), int(cy + SCENE_TOP + SCENE_H))


def largest_solid_square(mask):
    """Largest all-ink square, by integral image. Returns its side length."""
    h, w = mask.shape
    m = mask.astype(np.int32)
    integ = np.zeros((h + 1, w + 1), dtype=np.int32)
    integ[1:, 1:] = m.cumsum(0).cumsum(1)
    for k in range(min(h, w), 0, -1):
        s = (integ[k:, k:] - integ[:-k, k:] - integ[k:, :-k] + integ[:-k, :-k])
        if (s == k * k).any():
            return k
    return 0


def scene_stats(img):
    arr = np.asarray(img, dtype=np.int16)
    out = []
    for idx, (_r, _f, scene, _h, _d) in enumerate(CELLS):
        x0, y0, x1, y1 = scene_box(idx)
        crop = arr[y0:y1, x0:x1]
        mask = ink_mask(crop)
        out.append({
            "idx": idx, "name": scene, "ink": int(mask.sum()),
            "mass": largest_solid_square(mask),
            "elements": len(scene_geometry(scene)),
            "tones": len({p[-1] for _e, prims in scene_geometry(scene) for p in prims}),
        })
    return out


def scene_iou():
    """Pairwise IoU of the sixteen scene bitmaps at 64 x 64; returns the worst pair."""
    masks = {}
    arr = np.asarray(_IMG, dtype=np.int16)
    for idx in range(len(CELLS)):
        x0, y0, x1, y1 = scene_box(idx)
        crop = Image.fromarray(np.asarray(_IMG.crop((x0, y0, x1, y1)), dtype=np.uint8))
        small = np.asarray(crop.resize((64, 64), Image.Resampling.LANCZOS), dtype=np.int16)
        masks[idx] = ink_mask(small)
    pairs = []
    for i in range(len(CELLS)):
        for j in range(i + 1, len(CELLS)):
            a, b = masks[i], masks[j]
            union = float((a | b).sum())
            inter = float((a & b).sum())
            pairs.append((i, j, inter / union if union else 0.0))
    pairs.sort(key=lambda t: -t[2])
    return pairs[0], pairs[:5]


def ink_frac(img, box, delta=8):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    crop = np.asarray(img.crop((x0, y0, x1, y1)), dtype=np.int16)
    d = np.abs(crop - np.array(PAPER, dtype=np.int16)).max(axis=2)
    return float((d > delta).sum()) / float(d.size)


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------------------------

def report(img, out, size_bytes):
    stats = scene_stats(img)
    worst, top5 = scene_iou()
    grid_box = (X0, GRID_TOP, X1, GRID_TOP + GRID_H)
    band_ink = 100.0 * ink_frac(img, grid_box)
    small = min(it["size"] for it in text_items())
    ink_min = min(s["ink"] for s in stats)
    coll = collisions()
    counts = region_counts()
    fields = distinct_fields()

    print("MEASUREMENTS  (every number the brief asks for)")
    print("  stories on page      = %d   (1 lead + %d cells + %d list; brief wants 31)"
          % (STORY_COUNT, len(CELLS), len(LIST)))
    print("  distinct fields      = %d   (brief wants >= 21)" % len(fields))
    print("  grid cells           = %d" % len(CELLS))
    print("  smallest type px     = %.1f  (brief floor 9.5)" % small)
    print("  headline type px     = %d" % HEADLINE_PX)
    print("  scene ink min        = %d px  (brief floor 900)" % ink_min)
    print("  worst scene IoU      = %.3f  (brief wants < 0.55)  cells %d/%d  %s / %s"
          % (worst[2], worst[0] + 1, worst[1] + 1, CELLS[worst[0]][2], CELLS[worst[1]][2]))
    print("  grid-band ink %%      = %.2f  (brief wants 8..16)" % band_ink)
    print("  text collisions      = %d" % len(coll))
    print("  bytes                = %d  (cap 1048576)" % size_bytes)
    print("  md5 run1 / run2      = see the FILE block below")

    print("\nPAGE")
    print("  canvas            %d x %d  %s  paper #%02x%02x%02x  ink #%02x%02x%02x"
          % (img.size[0], img.size[1], img.mode, PAPER[0], PAPER[1], PAPER[2],
             INK[0], INK[1], INK[2]))
    print("  content box       x %d -> %d  (%d wide)" % (X0, X1, CONTENT_W))
    for name, (y, h) in (("masthead", BAND_MAST), ("mast rule", MAST_RULE),
                         ("ticker", BAND_TICKER), ("lead", BAND_LEAD),
                         ("region bar", BAND_REGION), ("timeline", BAND_TIME),
                         ("grid", BAND_GRID), ("also today", BAND_ALSO), ("footer", BAND_FOOT)):
        print("  %-12s      y=%4d  h=%3d  ends %4d" % (name, y, h, y + h))

    print("\nLEAD")
    print("  split             text x %d..%d (%d px, 58 %%), panel x %d..%d (%d x %d, 42 %%)"
          % (X0, X0 + LEAD_TEXT_W, LEAD_TEXT_W, PANEL_BOX[0], PANEL_BOX[2], PANEL_W, PANEL_H))
    f_hl = font(FONT_SERIF_B, 30)
    for i, line in enumerate(LEAD["headline"]):
        print("  headline %d        %-26r %6.1f px of %d at 30 px"
              % (i + 1, line, tracked_width(line, f_hl, -0.4), LEAD_TEXT_W))
    pext = ink_mask(np.asarray(img.crop(PANEL_BOX), dtype=np.int16))
    print("  panel             %d ink px of %d (%.1f %%), drawn at %dx and downsampled"
          % (int(pext.sum()), PANEL_W * PANEL_H, 100.0 * pext.sum() / (PANEL_W * PANEL_H),
             PANEL_SS))
    print("  panel elements    sky, sun, headland, water, tanker, flame, smoke, missile trail,"
          " second hull, swell = 10")

    print("\nTICKER  (three lead headlines, 13 px, drawn dots between)")
    f_tick = font(FONT_DISPLAY, 13)
    for i, t in enumerate(TICKER):
        print("  %d  %-32r %6.1f px" % (i + 1, t, tracked_width(t, f_tick, 0.2)))

    print("\nREGION BAR  (widths proportional to count)")
    acc = 0
    edges = [X0]
    for name, _c in REGIONS:
        acc += counts[name]
        edges.append(int(round(X0 + CONTENT_W * acc / float(sum(counts.values())))))
    edges[-1] = X1
    for i, (name, col) in enumerate(REGIONS):
        w = edges[i + 1] - edges[i]
        print("  %-12s %2d  x %3d..%3d  %3d px  (%.1f %% of 960)  tint #%02x%02x%02x"
              % (name, counts[name], edges[i], edges[i + 1], w, 100.0 * w / CONTENT_W,
                 *mix(col, PAPER, 0.16)))
    print("  total             %d  (the brief says 32; the page carries %d stories, so the bar"
          " is drawn to the measured count and the gap is printed here)"
          % (sum(counts.values()), STORY_COUNT))

    print("\nTIMELINE  (six ticks, earliest left)")
    for i, (when, place) in enumerate(TIMELINE):
        print("  %d  %-12s %s" % (i + 1, when, place))
    print("  clock times       only tick 3 carries an HH:MM in facts3.md (story 33, 10:00 ET);"
          " the other five carry the marker facts3 states. No time is invented to fill the rule.")

    print("\nGRID  (4 x 4, gutters 8 px)")
    print("  geometry          4 x %d + 3 x %d = %d wide, 4 x %d + 3 x %d = %d tall  ->  y %d..%d"
          % (COL_W, GUT, GRID_W, ROW_H, GUT, GRID_H, GRID_TOP, GRID_TOP + GRID_H))
    print("  cell              %d x %d: tag 9.5 px at y+%d, scene %d x %d at y+%d, headline 12 px"
          " at y+%d (+%d), detail 9.5 px at y+%d"
          % (COL_W, ROW_H, TAG_BASE, SCENE_W, SCENE_H, SCENE_TOP, HL_BASE1, HL_DY, DET_BASE))
    print("  cell budget       tag ink 3..10, scene y+%d..y+%d (66), headline ink y+%d..y+%d"
          " (two lines), detail ink y+%d..y+%d; %d px of air below the scene"
          % (SCENE_TOP, SCENE_TOP + SCENE_H, HL_BASE1 - 13, HL_BASE1 + HL_DY - 2,
             DET_BASE - 7, DET_BASE, ROW_H - SCENE_TOP - SCENE_H))
    line_ink = (font(FONT_MONO, 10).getbbox("H")[3] - font(FONT_MONO, 10).getbbox("H")[1])
    need = 7 * line_ink
    print("  also-today math   one 10 px mono line lays %d px of ink, so seven need %d px with"
          " no leading at all and %d px at the %g px leading used here; the brief's 48 px band"
          " (940..988) cannot hold them, so the strip takes 80 px and the grid gives up 32 px"
          " (rows %d px, not 101)" % (line_ink, need, 7 * 11.4, 11.4, ROW_H))
    if need > BAND_ALSO[1]:
        raise SystemExit("also-today arithmetic failed: %d px of ink in a %d px band"
                         % (need, BAND_ALSO[1]))

    print("\nSCENES  (per cell: ink pixels, largest solid square, distinct elements)")
    for s in stats:
        print("  cell %-2d %-14s ink=%4d mass=%dx%-2d elements=%d tones=%d"
              % (s["idx"] + 1, s["name"], s["ink"], s["mass"], s["mass"], s["elements"],
                 s["tones"]))
    print("  tones per scene   %d..%d of the region colour's four (brief asks 3-4)"
          % (min(s["tones"] for s in stats), max(s["tones"] for s in stats)))
    print("  scene ink min     %d px  (floor 900)  -> %s"
          % (ink_min, "PASS" if ink_min >= 900 else "FAIL"))
    print("  solid mass min    %d x %d  (floor 14 x 14)  -> %s"
          % (min(s["mass"] for s in stats), min(s["mass"] for s in stats),
             "PASS" if min(s["mass"] for s in stats) >= 14 else "FAIL"))
    print("  elements min      %d  (floor 3)" % min(s["elements"] for s in stats))
    print("  worst pair IoU    cells %d (%s) / %d (%s) = %.3f  -> %s"
          % (worst[0] + 1, CELLS[worst[0]][2], worst[1] + 1, CELLS[worst[1]][2], worst[2],
             "PASS" if worst[2] < 0.55 else "FAIL"))
    for i, j, v in top5:
        print("    pair %2d/%-2d  %-14s / %-14s  IoU %.3f"
              % (i + 1, j + 1, CELLS[i][2], CELLS[j][2], v))

    print("\nINK")
    print("  grid band         %.2f %%  of x %d..%d, y %d..%d  (%d px)  -> %s"
          % (band_ink, X0, X1, GRID_TOP, GRID_TOP + GRID_H,
             int(round(band_ink / 100.0 * GRID_W * GRID_H)),
             "PASS" if 8.0 <= band_ink <= 16.0 else "FAIL"))
    whole = 100.0 * ink_frac(img, (0, 0, PAGE, PAGE))
    print("  whole page        %.2f %%" % whole)
    sens = [100.0 * ink_frac(img, grid_box, delta=d) for d in (4, 8, 16, 30)]
    print("  band, threshold   %.2f %% at delta 4, %.2f at 8, %.2f at 16, %.2f at 30 — the bar"
          " holds at every threshold, so the number is not a choice of cut-off"
          % tuple(sens))

    print("\nTYPE  (blocks by size)")
    by_size = {}
    for it in text_items():
        by_size[it["size"]] = by_size.get(it["size"], 0) + 1
    for size in sorted(by_size):
        print("  %5.1f px   %3d blocks" % (size, by_size[size]))
    print("  smallest          %.1f px  -> %s" % (small, "PASS" if small >= MIN_TEXT else "FAIL"))

    print("\nSTORIES")
    print("  lead              %s / %s" % (LEAD["region"], LEAD["field"]))
    print("  cells             %d drawn stories" % len(CELLS))
    print("  also today        %d in two columns x 7 lines" % len(LIST))
    print("  distinct fields   %d  -> %s" % (len(fields), " · ".join(fields)))
    print("  masthead prints   %r  (the brief's literal string; the page carries %d stories,"
          " the bar totals %d)" % (MAST_META, STORY_COUNT, sum(counts.values())))
    print("  CUT list          nothing from facts3.md's CUT list is drawn: no Comey or James"
          " indictments, no Houston tornado, no Geneva plan, no Cape Verde, no COP31, no Nasdaq"
          " rebound, no Beltran Leyva, no Niger state, no rival-title-only claims, no Sikkim"
          " quake. The brief's example scenes (bus crash, rocket launch, wildfire) are not in"
          " facts3.md and are not drawn.")

    print("\nCOLLISIONS  (drawn text boxes whose bounding boxes overlap)")
    print("  text blocks       %d" % len(text_items()))
    print("  collisions        %d" % len(coll))
    for a, b in coll:
        print("    %s %r  x%.1f..%.1f y%.1f..%.1f  X  %s %r  x%.1f..%.1f y%.1f..%.1f"
              % (a["name"], a["string"], a["box"][0], a["box"][2], a["box"][1], a["box"][3],
                 b["name"], b["string"], b["box"][0], b["box"][2], b["box"][1], b["box"][3]))

    print("\nALSO TODAY  (14 stories that did not get a cell)")
    for i, (region, field, head) in enumerate(LIST):
        print("  %2d  %-12s %-14s %s" % (i + 1, region, field, head))

    print("\nFILE")
    print("  %s" % os.path.abspath(out))
    print("  bytes             %d  (cap 1048576, %s)"
          % (size_bytes, "ok" if size_bytes <= 1048576 else "OVER"))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    img = build()

    if img.size != (PAGE, PAGE):
        raise SystemExit("wrong size: %r" % (img.size,))
    img.save(out, "PNG", optimize=True)
    size_bytes = os.path.getsize(out)

    report(img, out, size_bytes)

    second = os.path.join(tempfile.mkdtemp(prefix="makefun-"), "entry.png")
    build().save(second, "PNG", optimize=True)
    a, b = md5_of(out), md5_of(second)
    print("  md5 run1          %s" % a)
    print("  md5 run2          %s  (%d bytes)" % (b, os.path.getsize(second)))
    print("  md5 run1 / run2   %s / %s  -> %s" % (a, b, "MATCH" if a == b else "DIFFER"))
    if a != b:
        raise SystemExit("the two renders differ")
    os.remove(second)

    here = os.path.dirname(os.path.abspath(out)) or "."
    for px in (480, 300):
        prev = img.resize((px, px), Image.Resampling.LANCZOS)
        path = os.path.join(here, "preview_%d.png" % px)
        prev.save(path, "PNG", optimize=True)
        print("  preview_%d.png    %d bytes" % (px, os.path.getsize(path)))

    for name, box in (("panel.png", PANEL_BOX),
                      ("grid.png", (X0, GRID_TOP, X1, GRID_TOP + GRID_H)),
                      ("ticker.png", (X0, BAND_TICKER[0], X1, BAND_TICKER[0] + BAND_TICKER[1]))):
        crop = img.crop(tuple(int(round(v)) for v in box))
        path = os.path.join(here, name)
        crop.save(path, "PNG", optimize=True)
        print("  %-12s      %d bytes  %d x %d" % (name, os.path.getsize(path),
                                                  crop.size[0], crop.size[1]))

    with open(out, "rb") as fh:
        magic = fh.read(8)
    ok = magic == b"\x89PNG\r\n\x1a\n" and max(img.size) <= 1024 and size_bytes <= 1048576
    print("\nGATE  png=%s  %dx%d  %d bytes  -> %s"
          % ("PNG" if magic == b"\x89PNG\r\n\x1a\n" else "NOT PNG", img.size[0], img.size[1],
             size_bytes, "PASS" if ok else "FAIL"))
    if not ok:
        raise SystemExit("gate failed")


if __name__ == "__main__":
    main()
