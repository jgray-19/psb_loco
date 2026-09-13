# Reproducing

Nothing on a results page is typed by hand: the tables are computed from
`scoreboard.csv` and each fit's `knobs.csv` at render time, the figures from the
same outputs. Page text lives in `loco_report/pages.py` and
`loco_report/studies.py`, never in the markdown — every file under
`docs/*_tunes/` and `docs/method.md` is overwritten on every render.

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

# 4. cross-campaign comparison, then every figure and page for a direction
uv run python scripts/analyse_cross_campaign.py --direction inverted
uv run python scripts/plot_cross_campaign.py --direction inverted
uv run python -m loco_report --direction inverted

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
(`results/matrix_p23_p13_final/`, `results/matrix_p23_p13_final_multi/`,
`docs/assets/figures/p23_p13_final/`,
`docs/assets/figures/p23_p13_final/multi/`). Cross-campaign figures are not
per-campaign: they go under `docs/assets/figures/scenarios/<direction>/`, since
`normal` and `inverted` are campaign slugs and own those folders already.

`predict_loco.py` writes `scoreboard.shard<i>of<n>.csv`; run it again with
`--merge` to make the `scoreboard.csv` the scores figure reads.

`scripts/refresh_docs.sh <direction>` runs all of it for one direction.

Steps 2 and 3 take `--options`, step 4 takes `--page`: rebuilding one page from
existing fits is a couple of minutes. Each results page carries the exact
commands for its own options at the bottom.

`--shard i/n` is one-based; `predict_loco.py` rejects an out-of-range index.

## The pieces

| file | what it owns |
|---|---|
| `loco_common/campaign.py` | every configuration: acquisitions, scan log, circuits, measured optics, results roots |
| `loco_common/case_names.py` | which options each page shows, and every name a reader sees |
| `scripts/measured_optics.py` | measured optics per configuration, against both models |
| `scripts/predict_loco.py` | scores each fit on the six targets |
| `scripts/case_optics.py` | twisses each fitted lattice against its machine-knob model |
| `scripts/report_cases.py` | the cross-campaign frames and comparison figures |
| `loco_report/` | every figure, every results page, the method page and every table |

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
