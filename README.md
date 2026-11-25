# makefun-news-24nov2026

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/FrelikaAldo/makefun-news-24nov2026/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard)
[![reward](https://make.fun/badge/news-image-20261124/FrelikaAldo/makefun-news-24nov2026/reward.svg)](https://make.fun/bounty/news-image-20261124)

One newspaper front page for Tuesday 24 November 2026, drawn in code: **21 stories, 19 region tags**.

The masthead is `THE WORLD TODAY` and the date runs across the top. The lead band is a horizontal
split: the Strait of Hormuz on the right as a tonal dusk scene — three tankers set ablaze by mines,
Treasury Secretary Scott Bessent calling Iran's economy "underwater", the blockading hulls on the
horizon, a drone with its contrail — and the headline, deck and datelines on the left.

Under it a 4 x 5 grid of twenty briefs carries the rest of the day, each with its own drawn
pictogram: Saudi-led strikes in Yemen and the UN's count since July; a police post hit in Al-Mawasi;
the Zaporizhzhia block; Russia and Ukraine at the Security Council, the grain deal ruled out; Russian
jets in the KADIZ; the Council's debate on conflict in an era of rapid technological change; the
second round of India–China military talks on the LAC; 1,900 December China–Japan flights cut;
Nvidia's chief executive reinstated and the stock up 31 %; CPHIA 2026 in Addis Ababa; the DRC's
cobalt export suspension; UK sanctions on five Myanmar generals; Strasbourg debating Ukraine before
the 26–27 November Council; the WHO chief in Havana; Venezuela's party-rule overhaul; US consumer
confidence at 10:00 ET; FIFA's 2031 and 2035 World Cup awards; Ronaldo's 987th goal; the Beaver Moon;
and Brent near $120.

Every word traces to the verified fact sheet for the day, and nothing that sheet marks as the wrong
year, the wrong day or unverified is used. Every element is drawn in code with Pillow by
`scripts/make_news.py`. There is no image model and no downloaded artwork: the tanker, the strait,
the hulls, the drone, the twenty pictograms, the rules and the type are all drawn from coordinates.

The image is 1024 by 1024 pixels and stays under the 1 MiB cap the gate sets. Two runs write
byte-identical files. At about 300 pixels across the lead headline and the twenty cell labels still
read; the 9 px region tags and 9.5 px teasers are texture at that size, not reading matter, and the
script says so in its own report rather than claiming otherwise.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

That writes `out/entry.png`. The program validates before it copies: it refuses a file that is
missing or unreadable, one whose first eight bytes are not the PNG signature, one whose header
declares a side above 1024 pixels, and one above 1048576 bytes, and it names what it found in each
case. With no `MAKEFUN_OUTPUT_DIR` it writes to `/output`, which is where the grader runs it.

`python3 scripts/make_news.py` redraws the page and rewrites `preview_480.png`, `preview_300.png`,
`panel.png`, `grid.png` and `icons.png` beside it, printing every measurement it checks: the story
and field counts, ink coverage for the page and for the grid band, every text block's width and right
edge, the collision count, the smallest type size, each pictogram's ink pixels, the lead panel's
distinct tones, and the md5 of two renders.

## License

MIT, 2026 Frelika Aldo. See `LICENSE`.
