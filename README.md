# psb_loco

PSB ring-3 LOCO: recover quadrupole errors (and optionally BPM and corrector gains) by matching the model's corrector orbit response to the 2026-08-21 scan. The fit is POCO, `adelmo`'s closed-orbit fitter.

## Data

- Six DHZ and six DVT correctors, each stepped through `offset_k = 0, ±dk, ±2dk` (`dk = 5e-5` LSA `/K`), at five RF-steering offsets.
- Two quadrupole powerings (normal, inverted tunes), four configurations each: `loco_common/campaign.py`. Every script takes `--campaign <slug>`.
- Read from the SDDS mount once, then cached in `data/`.
- The start model uses the machine's own circuits. It is never tune-matched: matching moves the circuits a gradient error moves.

## Layout

| path | contents |
|---|---|
| `loco_common/` | campaigns, measured response and orbits, model, naming and sign conventions, momentum calibration |
| `poco/settings.py` | scan → `CorrectorSetting` → `ClosedOrbitSeries` |
| `poco/run_poco.py` | CLI and `run()` |
| `scripts/` | case runner, measured optics, prediction and plotting |
| `loco_report/` | the docs site's figures and pages |
| `phase_advance_constraint/` | optional phase-advance series ([study](docs/studies/phase-advance-constraint.md)) |

## Run

```bash
source ../accpy/bin/activate
python -m poco.run_poco --output results/poco                      # k1 on delta orbits, nominal RF
python -m poco.run_poco --rf-offsets -2 0 2 --batch-momenta        # add momenta
python -m poco.run_poco --fit-gains --output results/poco_gains    # + BPM and corrector gains
python scripts/run_campaign_fits.py --campaign p23_p13_final       # every case a report page shows
```

| option | effect |
|---|---|
| `--errors` / `--misalign` | knob families to free, e.g. `quad:k1`, `bend:k0`, `quad:dy`, `quad:tilt` |
| `--absolute-planes x y` | keep that plane's closed orbit instead of a delta (needs `bend:k0` / `quad:dy`) |
| `--group-quadrupoles-by-cell` | 32 knobs per family instead of 48 |
| `--rf-offsets` | chroma-calibrated momenta; each adds a dispersion orbit |
| `--batch-momenta` | one MAD-NG process per trim, not per (trim, momentum) |
| `--correctors`, `--offsets` | restrict the scan (negative steps in decimal: `-0.0001`) |
| `--prior-strength`, `--prior FAMILY=V` | Tikhonov strength, per family |
| `--initial-knobs` | warm start from a `knobs.csv` |

Output in `--output`: `knobs.csv`, `history.json`, `summary.json` (status, diagnostics, arguments), `gains.csv` with `--fit-gains`.

## Gain fits

`--fit-gains` fits `(1 + b)` per BPM and plane and `(1 + g)` per corrector kick next to the magnet knobs (`adelmo.poco.calibrated`).

- Delta orbits only. Untrimmed orbits are dropped, and `--absolute-planes` is refused.
- Only differences between correctors of one plane are determined; the overall scale is shared with that plane's BPM gains. The priors fix it: `--sigma-bpm` (0.05), `--sigma-corrector` (0.3).
- Magnet knobs are regularised by absolute widths (`--knob-sigma FAMILY=V`; `quadrupoles` 5e-3 `dk1l`, `quad_tilt` 5e-3 rad), not by `--prior-strength`.
- Measured response ÷ model is 0.71–0.93 on the DHZ and 0.95–1.03 on the DVT. This is what the corrector gains are for.

## Conventions

[`docs/reference/conventions.md`](docs/reference/conventions.md). Each is pinned by a test.

- LSA `/K` is inverted for DHZ, not DVT (`loco_common/naming.py`).
- One reference orbit for the whole scan: untrimmed, nominal RF. The model takes its reference at `pt = 0`.
- Delta fits stand on zero correctors; absolute fits on the machine's.

## Tests

```bash
pytest          # fast set
pytest -m ""    # + MAD-NG and xsuite truth
```

Open issues and traps: [HANDOVER.md](HANDOVER.md).
