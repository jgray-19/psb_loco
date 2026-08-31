# Reproducing

Nothing on a results page is typed by hand: the tables are computed from
`scoreboard.csv` and each fit's `knobs.csv` at render time, the figures from the
same outputs. Prose lives in `reports/loco_option_matrix/make_pages.py`, never in
`docs/inverted_tunes/reports/*.md`, `docs/method.md` or
`docs/inverted_tunes/studies/measured-optics.md` — those five files are
overwritten on every render.

## From nothing

```bash
# 0. measured optics, per configuration (harpy + omc3, ~1 h each)
uv run python scripts/measured_optics.py --campaign normal inverted

# 1. the fits (serial, hours)
uv run python scripts/run_campaign_fits.py --campaign inverted
uv run python scripts/run_campaign_fits.py --campaign inverted --momentum-mode multi

# 2. score, then merge the shards
uv run python scripts/predict_loco.py --shard i/8   # i = 1..8, one-based
uv run python scripts/predict_loco.py --merge
uv run python scripts/predict_loco.py --momentum-mode multi --shard i/8
uv run python scripts/predict_loco.py --momentum-mode multi --merge

# 3. twiss each fitted lattice (one MAD-NG process per case)
uv run python scripts/case_optics.py
uv run python scripts/case_optics.py --momentum-mode multi

# 4. figures, then pages
uv run python scripts/report_cases.py
uv run python reports/loco_option_matrix/make_pages.py
uv run python scripts/report_cases.py --momentum-mode multi
uv run python reports/loco_option_matrix/make_pages.py --momentum-mode multi

# 5. the site
uv run --with zensical zensical build     # into site/
uv run --with zensical zensical serve     # preview on localhost
```

The multi-momentum campaign command automatically runs or reuses the matching
nominal-momentum absolute fit and supplies it as the warm start. Direct
multi-momentum absolute invocations require `--initial-knobs`; the prior remains
centred on zero rather than on that initial lattice.

Steps 2, 3 and 4 take `--campaign <slug>`; run them once per tab. Results,
prediction caches and figures are namespaced by campaign and momentum mode
(`results/matrix_inverted_second/`, `results/matrix_inverted_second_multi/`,
`docs/assets/figures/inverted_second/`,
`docs/assets/figures/inverted_second/multi/`). Cross-campaign figures are not
per-campaign: they go under `docs/assets/figures/scenarios/<direction>/`, since
`normal` and `inverted` are campaign slugs and own those folders already.

`predict_loco.py` writes `scoreboard.shard<i>of<n>.csv`; run it again with
`--merge` to make the `scoreboard.csv` the scores figure reads.

`scripts/refresh_normal_second_docs.sh` and
`scripts/refresh_inverted_second_docs.sh` run all of it for one direction.

Steps 2 and 3 take `--options`, step 4 takes `--page`: rebuilding one page from
existing fits is a couple of minutes. Each results page carries the exact
commands for its own options at the bottom.

`--shard i/n` is one-based; `predict_loco.py` rejects an out-of-range index.

## The pieces

| file | what it owns |
|---|---|
| `loco_common/campaign.py` | the two configurations: acquisitions, scan log, circuits, measured optics, results roots |
| `loco_common/case_names.py` | which options each page shows, and every name a reader sees |
| `scripts/measured_optics.py` | measured optics per configuration, against both models |
| `scripts/predict_loco.py` | scores each fit on the six targets |
| `scripts/case_optics.py` | twisses each fitted lattice against its start model |
| `scripts/report_cases.py` | every figure |
| `reports/loco_option_matrix/make_pages.py` | the method page, the results pages, every table |

A fit lives under `results/matrix[_<campaign>][_multi]/<planes>__<families>__<lump>`.
That slug is an address and never appears on a page except inside a shell command.

## Tests

```bash
uv run pytest          # fast set
uv run pytest -m ""    # everything, including MAD-NG and xsuite (~60 s)
```

## Two things that bite

Write `$\lvert v\rvert$`, never `$|v|$`, and escape a bare `|` inside a table
cell: an unescaped pipe gives the header row one more cell than the delimiter row
and the renderer silently emits a paragraph of pipes instead of a table.

The acquisition mount `/home/jmgray/mnt` is read-only and often absent. Every
campaign is describable without it; `scripts/measured_optics.py` is the only
thing that needs it, and it fails loudly if the pinned tunes disagree with the
export.
