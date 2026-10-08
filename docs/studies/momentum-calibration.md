# Momentum calibration

PSB ring 3 · MAD-NG method 6.

## Convention

MAD-NG `dx`, `dq1`, `dq2` are derivatives with respect to canonical `pt`, not `dp/p` (`madl_twiss.mad` converts the `chrom` step with `dp2pt`). Checked on the PSB model: for `dp/p = 1e-4`, `pt = 5.19772e-5`, and the orbit projected on `dx` gives `5.19783e-5`. Pinned by `tests/test_chromaticity_convention.py`.

## Two calibrations

Both take the nominal-RF orbit as `pt = 0`. The fits use the RF/XImeter one.

| source | converts |
|---|---|
| RF/XImeter | each measured `Dp/p` to `pt`, then subtracts the nominal point |
| orbit | the measured orbit change, projected on the start model's `dx/dpt` |

| campaign | RF offset [mm] | orbit `pt` | RF/XImeter `pt` |
|---|---:|---:|---:|
| normal | -2 | -4.9057e-4 | -6.4698e-4 |
| normal | +2 | +4.6556e-4 | +6.1568e-4 |
| inverted | -2 | -5.2171e-4 | -6.5017e-4 |
| inverted | +2 | +4.9511e-4 | +6.4034e-4 |

They differ by 25–30 %. This is not the `dp/p`↔`pt` conversion or the reference choice; it is an external readback against a projection through the start model's dispersion.

## Effect on the fit

Same sequence, absolute targets, `k1+b+dy+tilt`, lumped, warm-started.

| campaign, momenta | source | best loss | fitted `dQx/dpt` | fitted `dQy/dpt` |
|---|---|---:|---:|---:|
| normal, 5 | orbit | 2.960e-9 | -6.643 | -12.948 |
| normal, 5 | RF/XImeter | 1.578e-8 | -7.365 | -14.419 |
| inverted, 3 | orbit | 3.965e-9 | -6.629 | -12.899 |
| inverted, 3 | RF/XImeter | 1.120e-8 | -7.475 | -13.892 |

Tune-scan slopes with RF/XImeter momentum are -6.503 / -13.266 (normal) and -6.606 / -12.578 (inverted). The knob vectors from the two sources correlate at 0.41 (normal) and 0.56 (inverted).

Two RF/XImeter scopes failed deterministically in MAD-NG's normal-form eigen ordering; this is optimiser-path instability, not evidence for either calibration.
