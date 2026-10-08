# Phase-advance constraint

`--phase-constraint` (with `--rf-offsets`) adds one plain-twiss, no-corrector series per RF offset. Its residual is the measured BPM-to-BPM phase advance (`mu1`, `mu2`), never the cumulative phase.

## Why

Orbit response cannot separate a BPM gain from a magnet strength, since both scale the response. Phase advance is independent of BPM gain. The gains are now fitted directly (`--fit-gains`), which is the other way to break the degeneracy; the two are not combined.

## Inputs

- The phase is the equation-compensated optics at each RF offset: `scripts/measured_optics.py --optics-folders all`, read from `results/optics/<campaign>/<folder>/free`.
- The orbits are the LOCO scan. Code: `phase_advance_constraint/series.py`.

## Result

On `p17_p23_final`, `none__k1__bpm-family`, the model has a BPM-to-BPM X-phase zigzag that the measurement does not. At the measured weight phase has no effect, because the closed orbit's SNR (median 3400) is about ten times phase's (290) and about 140 orbit settings outnumber 3 phase ones. `--phase-weight W` divides `mu1_var` and `mu2_var` by `W`:

| `W` | RMS(model − measured) [2π] | max [2π] |
|---:|---:|---:|
| none | 0.01879 | 0.03324 |
| 1 | 0.01830 | 0.03252 |
| 10 | 0.01497 | 0.02758 |
| 100 | 0.00713 | 0.01520 |
| 1000 | 0.00481 | 0.01084 |

![RMS zigzag residual against phase weight](../assets/figures/studies/phase-advance-constraint/phase_weight_scan_p17_p23_final.png)

![Model and measured X phase advance, constraint off and on (W = 100)](../assets/figures/studies/phase-advance-constraint/real_method2_phase_check_p17_p23_final.png)

The reduction is monotonic but saturates, and some pairs (0, 3, 5, 7/9, 14) persist at every weight.

## Open

- No default weight is chosen.
- Why the zigzag persists: either the knob family cannot represent the phase data, or those pairs share structure not yet found.
- `p17_p23_final/xy__k1+b+dy+t__bpm-family` diverged at `W = 100` after 16 iterations (every worker failed on one trial step at λ ≈ 0.02). Unexplained.
