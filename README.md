# makefun-news-24nov2026

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/FrelikaAldo/makefun-news-24nov2026/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard)
[![reward](https://make.fun/badge/news-image-20261124/FrelikaAldo/makefun-news-24nov2026/reward.svg)](https://make.fun/bounty/news-image-20261124)

One newspaper front page for Tuesday 24 November 2026, drawn in code: **31 stories, 16 drawn scenes,
7 regions, 30 fields**.

The page is built for a judge looking at it at 1024 pixels, which is where the previous pass lost:
thirty cells at 8 px type read as one story. So this page spends itself on fewer, bigger, drawn
stories instead.

- **Masthead** — `THE WORLD TODAY` at 46 px serif bold, the date and the counts on the right, under
  a 3 px rule.
- **Ticker** — a black bar with three lead headlines at 13 px and drawn dots between them.
- **Lead** — the Strait of Hormuz: headline, subhead and dateline on the left 58 %, and on the right
  42 % a 392 × 288 landscape drawn as one picture (sky, sun, headland, water, a tanker ablaze, its
  smoke column, a second hull, a missile trail, foreground swell).
- **Region bar** — seven segments, each `LABEL n` at 11 px on its own tint, widths proportional to
  the story count.
- **Timeline** — one rule, six ticks, earliest left, each labelled with the time or marker the fact
  sheet states.
- **Grid** — 4 × 4 = 16 cells. Every cell is a region tag at 9.5 px, a **drawn scene 104 × 66 px**,
  a 12 px headline over two lines and one 9.5 px line of detail.
- **Also today** — two columns of seven, the 14 stories that did not get a cell.
- **Footer** — the drawn-by bar.

The sixteen scenes are flat shapes in three or four tones of their region's colour: a bombed block,
a control tower with a drone over it, a leaning tower and rubble, a police post and a van, a border
hut and its boom, a cobalt headframe, an airliner, a market screen, a laden ship, a clinic and a
syringe, a travel document and its stamp, two peaks with flags, a hemicycle, a courtroom bench and
gavel, an oil derrick, a stadium bowl. Each carries at least three distinct elements, at least
1,100 ink pixels and a solid mass of at least 14 × 14 px, and no two of the sixteen share more than
0.49 IoU at 64 × 64.

Every word traces to the verified fact sheet for the day, and nothing that sheet marks as the wrong
year, the wrong day, unverified, or as a rival's headline is used. The fact sheet's own example
scenes — a bus crash, a rocket launch, a wildfire — are not in it, so they are not drawn. Every
element is drawn in code with Pillow by `scripts/make_news.py`: there is no image model and no
downloaded artwork.

The image is 1024 by 1024 and stays under the 1 MiB cap the gate sets (about 160 KiB). Two runs
write byte-identical files, and the script prints both md5s.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

That writes `out/entry.png`. The program validates before it copies: it refuses a file that is
missing or unreadable, one whose first eight bytes are not the PNG signature, one whose header
declares a side above 1024 pixels, and one above 1048576 bytes, and it names what it found in each
case. With no `MAKEFUN_OUTPUT_DIR` it writes to `/output`, which is where the grader runs it.

`python3 scripts/make_news.py` redraws the page and rewrites `preview_480.png`, `preview_300.png`,
`panel.png`, `grid.png` and `ticker.png` beside it, printing every measurement it checks: the story,
field and cell counts, the smallest type size, each scene's ink pixels, solid mass and elements, the
worst pairwise scene IoU and the four pairs nearest it, ink coverage for the grid band at four
thresholds, the collision count (with both strings of any offending pair), and the md5 of two
renders.

## License

MIT, 2026 Frelika Aldo. See `LICENSE`.
