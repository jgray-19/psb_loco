# Chroma momentum investigation

This intentionally small analysis compares two definitions of relative momentum:

1. `orbit/model D`: infer each `delta` from the measured closed-orbit change and
   the model horizontal dispersion using `delta = (D.x)/(D.D)` (the deliberately
   backwards calculation).
2. `chroma`: use the XImeter `Dp/p`, rebased exactly to the nominal-RF plateau as
   `(1 + dpp) / (1 + dpp0) - 1`.

Run it from this directory or the repository root:

```bash
MPLCONFIGDIR=/tmp .venv/bin/python chroma_investigation/analyse.py
```

Run `recalculate_dpp_from_averages.py` first. Despite its historical filename,
it calculates `Dp/p` for every raw `(BfC, Frev)` sample and only then groups the
samples into momentum plateaus. It writes `dpp_recalculated_by_plateau.csv`.
`analyse.py` reads that file together with `input_uncleaned.csv` and
`model_full_ring.csv`, and writes `dispersion.png`, `tune_fits.png`,
`frev_fits.png`, and `summary.csv`. The input CSV is a compact snapshot of the two
2026-08-21 tune settings: the five averaged untrimmed closed-orbit acquisitions,
the corresponding XImeter tune/`Dp/p`/`Frev` exports, and the MAD-NG model values.
The raw files are the normal and inverted campaign paths defined in
`loco_common/campaign.py`; the closed-orbit averaging and XImeter plateau grouping
are the existing `psb_loco`/`psb_md` readers.

Model expectations come from a MAD-NG model matched to the measured nominal tune
of each setting and are shown in every figure. In the tune figure the model
chromatic slope is anchored at the measured nominal tune, deliberately isolating
the chromaticity comparison from the separate model-versus-machine tune offset.
For revolution frequency the fitted relation is

`(Frev - Frev0) / Frev0 = (1/gamma^2 - alphap) delta`,

with `gamma = 1 + 0.160 / 0.93827208816` for 160 MeV protons. A relative
kinetic-energy uncertainty of `1e-3` is propagated through `gamma` and
`1/gamma^2`, then combined in quadrature with the frequency-fit uncertainty on
`alphap - 1/gamma^2`.

The energy statement is an explicit assumption: the 160 MeV kinetic energy has
a guessed `1e-2` relative uncertainty. The uncleaned input was freshly rebuilt from
the raw SDDS matrices by taking their turn means; no SVD, SSA, AC-dipole, or
other turn-by-turn cleaner was called. All available point errors are plotted.
The fresh pass averages all 24 raw untrimmed acquisitions at each off-momentum
setting and all 47 at nominal momentum, independently for each tune pair. Fits
include both-axis point uncertainties by iteratively projecting the x errors
onto y; the reported `fit_error` is then combined in quadrature with the energy
term for `alphap`.

The XImeter `Dp/p` bars are standard deviations over every row assigned to an RF
setting in both tune-plane blocks. The nominal-setting spread is propagated when
absolute `Dp/p` is rebased to zero. The green recalculated branch uses the same
standard-deviation convention after recalculating every raw sample from its own
`BfC` and `Frev`; the XImeter tune and `Frev` bars also use standard deviations.
