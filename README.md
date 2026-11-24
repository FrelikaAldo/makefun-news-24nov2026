# makefun-news-24nov2026

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/FrelikaAldo/makefun-news-24nov2026/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard)
[![reward](https://make.fun/badge/news-image-20261124/FrelikaAldo/makefun-news-24nov2026/reward.svg)](https://make.fun/bounty/news-image-20261124)

One newspaper front page for Tuesday 24 November 2026, drawn in code.

The masthead is `THE WORLD TODAY` and the date runs across the top. The lead is the
Strait of Hormuz: the strait is still shut, and Treasury Secretary Scott Bessent said
Iran's economy is "underwater" after the latest round of sanctions, with a Saudi-led
coalition reporting it intercepted a Houthi drone. Under the lead, six briefs cover the
rest of the day: the Security Council's high-level debate on conflict resolution in an
era of rapid technological change; CPHIA 2026 in Addis Ababa, on health sovereignty and
reforming the global health architecture; China cutting more China to Japan flight
routes in its row with Tokyo; the European Parliament debating Ukraine in Strasbourg on
the eve of the special European Council; crude rising as Hormuz stays shut; and the
Beaver Moon, the first of three consecutive supermoons.

Every element is drawn in code with Pillow by `scripts/make_news.py`. There is no image
model and no downloaded artwork: the tanker, the strait and its broken chain, the
warship, the drone, the six pictograms, the rules, the type and the hatching are all
drawn from coordinates and rectangles.

The image is 1024 by 1024 pixels and stays under the 1 MiB cap the gate sets. It is
legible at about 300 pixels across: the date, the lead headline and all six region tags
still read at that size, which is roughly how the judge sees it.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

That writes `out/entry.png`. The program validates before it copies: it refuses a file
that is missing or unreadable, one whose first eight bytes are not the PNG signature,
one whose header declares a side above 1024 pixels, and one above 1048576 bytes, and it
names what it found in each case. With no `MAKEFUN_OUTPUT_DIR` it writes to `/output`,
which is where the grader runs it.

`python3 scripts/make_news.py` redraws the page, and rewrites `preview_480.png` and
`preview_300.png` beside it.

## License

MIT, 2026 Frelika Aldo. See `LICENSE`.