# Method

PSB ring 3, flat bottom, kinetic energy 0.16 GeV. 16 BPMs per plane, 48 ring quadrupoles, 12 orbit correctors (6 DHZ, 6 DVT).

## Configurations

The corrector scan was run twice on 2026-08-21, at two quadrupole powerings. The correctors were not changed between them.

| | Normal tunes, 29th | Normal tunes, QDE14 error | Normal tunes, QDE14+QDE3 error | Normal tunes, sextupoles on |
|---|---|---|---|---|
| acquisitions | `0mm` | `0mm` | `0mm` | `0mm` |
| scan log | `scan_20260829T095805.jsonl` | `scan_20260829T125640.jsonl` | `scan_20260829T163906.jsonl` | `scan_20260830T093624.jsonl` |
| corrector step, LSA `/K` | 0, ±7.5e-05, ±0.00015 | 0, ±7.5e-05, ±0.00015 | 0, ±7.5e-05, ±0.00015 | 0, ±7.5e-05, ±0.00015 |
| QFO / QDE, MAD $k_1$ | 0.7289003149 / -0.7442765967 | 0.7289003149 / -0.7442765967 | 0.7289003149 / -0.7442765967 | 0.7289003149 / -0.7442765967 |
| trim circuits | all four at zero | all four at zero | all four at zero | all four at zero |
| AC-dipole folders | `0mm`, `m2mm`, `2mm` | `0mm`, `m2mm`, `2mm` | `0mm`, `m2mm`, `2mm` | `0mm`, `m2mm`, `2mm` |
| model tune, $k_1$ as sent | 4.1704 / 4.2311 | 4.1704 / 4.2311 | 4.1704 / 4.2311 | 4.1704 / 4.2311 |
| model tune, matched | 4.1730 / 4.2293 | 4.1731 / 4.2299 | 4.1731 / 4.2288 | 4.1735 / 4.2294 |

A third scan, `CO_measurements_inverted_tunes_double` / `scan_20260821T150756.jsonl`, repeats the inverted lattice with a single ±1.5e-4 step. It is fitted (`--campaign inverted_double`) and not shown on the pages.

## Orbit measurement

1. Each corrector is trimmed to each step in the table above, at five RF-steering offsets; one acquisition per setting.
2. A closed orbit is the mean over turns and bunches; its bar is the standard error of that mean.
3. One reference orbit — the untrimmed machine at nominal RF — is subtracted from every orbit in the scan.
4. LSA `/K` is taken as the kick in rad; the six DHZ carry a sign inversion, the six DVT do not.

## Tune and chromaticity

Full XImeter tune/chroma export. Every measured `Dp/p` is converted to $p_t$ with the PSB accelerator class, then all ctimes are fitted together with one shared slope and a separate tune intercept per ctime. The plots show MAD-NG-native $dq1=dQ_x/dp_t$ and $dq2=dQ_y/dp_t$; their bars carry the common fit's $1\sigma$ slope errors. The file's `Xi` summary is not used.

## Optics measurement

1. AC-dipole turn-by-turn, two drive settings per configuration, 10 000 turns per acquisition, flat top from turn 2 000.
2. The drive is re-measured per acquisition: ring-summed `|FFT|` peak within 0.006 of the set tune, refined by sub-bin projection maximisation on the loudest BPM; the folder value is the median.
3. Preprocessing: demodulate, remove energy motion, remove interference, SSA clean per BPM (window 200, rank 4). The two removals need AC-dipole-off blanks; this MD took none, so they did not run.
4. An omc3 model is built at the measured natural and driven tunes.
5. Harpy over turns 2 500-9 500, then driven optics, then equation-compensated free optics.
6. Beta is taken from phase and from amplitude, both reported.

## Models

One sequence, `models/model_qx0.165000_qy0.227500/psb3_saved.seq`, twissed in MAD-NG (integrator method 6, DA/normal-form chromaticity), correctors at their scan settings. Two lattices per configuration:

- **$k_1$ as sent** — `kbrqf`/`kbrqd` at the LSA currents above, the four trims at zero, no matching. The fits start here.
- **matched** — the same, then `kbrqf`/`kbrqd` matched to the measured natural tune (`MAD.match`, `fmin = 1e-8`).

## Fits

**Method 2**, on every page but one: delta closed orbits, Levenberg-Marquardt Gauss-Newton (`aba_optimiser.ClosedTwissFitter`), one MAD-NG worker per corrector setting, isotropic Tikhonov prior at strength 1e-4. The reference orbit and its Jacobian are recomputed every iteration.

The **single-momentum** result pages fit nominal RF only: 48 non-zero corrector settings, plus one averaged static-orbit target when either plane is absolute. Their non-zero-RF scores are held-out validation.

The **multi-momentum** result pages fit all five RF offsets (`-2, -1, 0, +1, +2 mm`): 240 non-zero corrector settings plus four dispersion targets for a pure-delta fit, or five averaged untrimmed orbit targets when a plane is absolute. The 244/245 targets are batched into 50 MAD-NG workers without changing the objective. Absolute-orbit fits first solve the matching nominal-momentum case, then use that lattice to initialise the joint five-momentum solve; the Tikhonov prior remains centred on zero error knobs.

**Method 1**, on its own page: the measured response matrix is the target and a first-order MAD-NG parametric twiss the model. Every matrix cell is one weighted `MAD.match` equality, fitted directly with the 32 native cell-grouped $\Delta k_1 L$ knobs used by grouped Method 2. It stops on `XTOL`, when no knob moves by more than 0.3 % of itself; the objective tests are only made at a feasible point, which measured data never is.

| page | planes keeping the closed orbit |
|---|---|
| [Delta orbits](reports/delta.md) | both planes as delta orbits |
| [Absolute orbits](reports/absolute.md) | both planes absolute |
| [One knob per magnet](reports/per-magnet.md) | one option from each of the three |
| [Method 1](reports/method1.md) | both planes as delta orbits |
| [Scenario comparison, gradients only](reports/scenario-comparison.md) | delta orbits, error-injection scenarios against the baseline |
| [Scenario comparison, gradients and rolls](reports/scenario-comparison-rolls.md) | delta orbits, error-injection scenarios against the baseline |

Two cases per Method-2 page:

| case | free families | knobs |
|---|---|---|
| Gradients, lumped to 32 knobs by cell | gradients | lumped to 32 knobs by cell |
| Gradients and rolls, lumped to 32 knobs by cell | gradients and rolls | lumped to 32 knobs by cell |

Lumping to 32 ties the two QFO flanking a QDE and leaves the QDE free, by magnet name. Rolls are parametrised as the gradients are. Neither arm of a page frees a per-magnet knob: rolls per magnet are not run at all, and gradients per magnet — 48 against 16 BPMs per plane — are on the [one knob per magnet](reports/per-magnet.md) page rather than beside the lumped fits.

## Scoring

Every fit is stood up again and asked the same six questions; the number reported is residual rms as a percentage of the measured amplitude:

| target | what is compared |
|---|---|
| delta x, delta y | corrector delta orbits |
| static x, static y | the machine's closed orbit at each RF setting |
| disp x, disp y | dispersion from the RF-offset orbits |

Absolute planes are weighted with a 1e-4 m BPM zero-offset floor.

## Figures

| figure | contents |
|---|---|
| gradients, bends, offsets, rolls by `s` | fitted value per magnet, one panel per case, fit's own error bars |
| significance | fitted value over its own error bar per magnet, log scale |
| lattice | beta-beating, phase error and dispersion along `s` against the start model, per case, with measured beta-beating and measured dispersion at the BPMs; dispersion is the slope of the five untrimmed closed orbits versus reconstructed `pt` |
| case tunes | each fit's tune against the measured tune, one bar per case, one panel per plane |
| residuals | residual rms per BPM, with the statistical bar and the 0.1 mm systematic |
| scores | residual rms against each scored measurement, one bar per case |
| tune, chromaticity | measured against both model lattices, one bar per model |
| beta-beating | measured beta-beating along $s$ against each reference model, from phase beta and from amplitude beta |
| measured optics | measured beta and beta-beating against one model, one figure per model |

[Reproducing any of it](../reference/reproducing.md)
