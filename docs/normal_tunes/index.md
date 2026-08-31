# Normal tunes — results

The normal-tunes counterpart of the [inverted-tunes results](../inverted_tunes/reports/index.md),
taken at the P17/P23 tune point on 2026-08-29.

## Method 2 — single momentum

These fits use every measured corrector kick at nominal RF only. Their predictions
at the other four RF offsets are held-out validation.

| page | contents |
|---|---|
| [Delta orbits](reports/delta.md) | two fits, both planes as delta orbits |
| [Absolute orbits](reports/absolute.md) | two fits, both planes absolute |
| [One knob per magnet](reports/per-magnet.md) | 48 free gradients, delta and absolute orbit options |

## Method 2 — multi momentum

These fits use every measured corrector kick at all five RF offsets. The five
momenta are batched into the same 49 MAD-NG workers used by the corresponding
single-momentum layout.

| page | contents |
|---|---|
| [Delta orbits](reports/multi/delta.md) | both planes as delta orbits, 244 fitted targets |
| [Absolute orbits](reports/multi/absolute.md) | both planes absolute, 245 fitted targets |
| [One knob per magnet](reports/multi/per-magnet.md) | 48 free gradients, delta and absolute orbit options |

## Method 1

| page | contents |
|---|---|
| [Method 1](reports/method1.md) | the response-matrix fit, delta orbits, against Method 2 |
| [Method 1 against Method 2](reports/benchmark.md) | same knobs and data: agreement and runtime |

## Common measurements

| page | contents |
|---|---|
| [Measured optics](studies/measured-optics.md) | measured tune, $Q'$, beta and beta-beating, against both models |
| [Scenario comparison](reports/scenario-comparison.md) | fitted knob errors and tune/chroma, all scenarios against the baseline |

Every page tabs between the four campaigns; the optics page tabs between the
(campaign, model) pairs. Tabs are linked, so a choice holds for the page.

Definitions are on the [method page](method.md). The narrative study of the
rolls is [under Reference](../studies/quadrupole-roll.md).
