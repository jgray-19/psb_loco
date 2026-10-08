# Reproducing

Nothing on a results page is typed by hand: tables and figures are computed from `scoreboard.csv` and each fit's outputs. Page text lives in `loco_report/pages.py` and `loco_report/studies.py`; every file under `docs/*_tunes/` and `docs/method.md` is overwritten on render.

## Pipeline

`scripts/refresh_docs.sh <direction>` runs all of it. Per campaign (`--campaign <slug>`):

```bash
python scripts/measured_optics.py --campaign <slug> --optics-folders all   # harpy + omc3, ~1 h per folder
python scripts/run_campaign_fits.py --campaign <slug>                      # multi-momentum; fits the single-momentum warm starts itself
python scripts/predict_loco.py --campaign <slug>                           # scores each fit
python scripts/predict_loco.py --campaign <slug> --merge                   # scoreboard.csv
python scripts/case_optics.py --campaign <slug>                            # twiss each fitted lattice
```

Per direction (`inverted` or `normal`):

```bash
python scripts/analyse_cross_campaign.py --direction <direction>
python scripts/plot_cross_campaign.py --direction <direction>
python -m loco_report --direction <direction>        # every figure and page
zensical build                                       # the site, into site/
```

`predict_loco.py` and `case_optics.py` take `--options`, `loco_report` takes `--page`: rebuilding one page from existing fits takes minutes.

## Layout

| path | contents |
|---|---|
| `loco_common/campaign.py` | every configuration: acquisitions, scan log, circuits, optics, results roots |
| `loco_common/case_names.py` | which cases each page shows, and every name a reader sees |
| `results/matrix_<slug>_multi/<planes>__<families>__<lump>` | a reported fit (`knobs.csv`, `gains.csv` if any, `summary.json`) |
| `results/matrix_<slug>/` | the single-momentum warm starts, not reported |
| `docs/assets/figures/<slug>/multi/`, `.../scenarios/<direction>/` | per-campaign and cross-campaign figures |

The case slug is an address and appears on a page only inside a shell command.

## Traps

- Write `$\lvert v\rvert$`, never `$|v|$`, and escape a bare `|` in a table cell: otherwise the renderer silently emits a paragraph of pipes.
- The acquisition mount `/home/jmgray/mnt` is read-only and often absent. Only `measured_optics.py` and a cold scan read need it.
