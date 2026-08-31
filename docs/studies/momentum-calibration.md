# Momentum-calibration investigation

PSB ring 3 · 2026-08-24 · MAD-NG method 6 throughout

## Convention audit

The apparent `dp/p` versus `pt` convention conflict was in the MAD-NG reference
documentation, not in this repository's conversion. In `madl_twiss.mad`, the
`chrom` value is supplied as a `dp/p` step, converted with `dp2pt`, and every
finite difference is divided by the resulting `dpt`. Consequently `dx`, `dq1`,
`dq2`, and the chromatic columns are derivatives with respect to canonical `pt`.

This was verified directly on the PSB model at method 6. For `dp/p = 1e-4`,
`pt = 5.19772e-5`; projection of the off-momentum orbit onto the returned `dx`
gave `5.19783e-5`. The tune finite differences were
`dQ/d(dp/p) = -3.35246 / -6.72714`, while the Twiss headers and explicit
`dQ/dpt` were `-6.45011 / -12.94296`. The regression is pinned in
`tests/test_chromaticity_convention.py` and the MAD-NG documentation was
corrected to match the implementation.

## Calibrations

Both calibrations use the measured nominal-RF orbit as zero. The RF/XImeter
source converts each absolute `Dp/p` point to `pt` before subtracting the
nominal point; the orbit source projects the measured closed-orbit change onto
the starting model's `dx/dpt`.

| campaign | RF offset \[mm] | orbit `pt` | RF/XImeter `pt` |
|---|---:|---:|---:|
| normal | -2 | -4.9057e-4 | -6.4698e-4 |
| normal | -1 | -2.4829e-4 | -3.2624e-4 |
| normal | +1 | +2.3388e-4 | +3.0910e-4 |
| normal | +2 | +4.6556e-4 | +6.1568e-4 |
| inverted | -2 | -5.2171e-4 | -6.5017e-4 |
| inverted | -1 | -2.6285e-4 | -3.3274e-4 |
| inverted | +1 | +2.4696e-4 | +3.2908e-4 |
| inverted | +2 | +4.9511e-4 | +6.4034e-4 |

The difference is therefore real and much larger than nonlinear `dp/p` to `pt`
conversion or reference subtraction. It is a disagreement between an external
momentum readback and a projection through the starting model dispersion.

## Controlled LOCO fits

Every fit used the same sequence, method 6, absolute x/y targets, fitted
`k1+b+dy+tilt`, BPM-family quadrupole grouping, prior, and nominal-fit warm start.

| campaign/scope | source | best loss | fitted `dQx/dpt` | fitted `dQy/dpt` |
|---|---|---:|---:|---:|
| normal, five momenta | orbit | 2.960e-9 | -6.643 | -12.948 |
| normal, five momenta | RF/XImeter | 1.578e-8 | -7.365 | -14.419 |
| inverted, three momenta | orbit | 3.965e-9 | -6.629 | -12.899 |
| inverted, three momenta | RF/XImeter | 1.120e-8 | -7.475 | -13.892 |

For comparison, tune-scan slopes are `-6.503 / -13.266` (normal) and
`-6.606 / -12.578` (inverted) with RF/XImeter momentum, versus
`-8.748 / -17.304` and `-8.505 / -16.137` when those same tunes are fitted
against orbit-projected momentum.

Changing only the momentum source materially changes the inferred lattice. The
normal five-point knob vectors have correlation 0.408 and RMS difference
1.79e-2; the inverted three-point vectors have correlation 0.564 and RMS
difference 1.32e-2. This is not a harmless choice of horizontal-axis units.

The normal three-point and inverted five-point RF/XImeter fits fail
deterministically in MAD-NG's normal-form eigen ordering during an optimiser
trial; rerunning gives the same failure. The complementary RF/XImeter scopes
complete, so the input momentum points themselves are not intrinsically
invalid. This is recorded as optimiser-path instability, not as evidence for
either calibration.

## Conclusion

Two bugs were found and fixed: Method 2's raw closed-Twiss worker omitted
`method=6`, and MAD-NG's documentation described `pt` derivatives as `dp/p`
derivatives. No reversal or missing beta factor was found in the LOCO momentum
conversion. The remaining 25–30% calibration disagreement is genuine input/model
information and must remain visible. The original orbit source stays the default;
both mappings and the selected values are written to each fit summary.
