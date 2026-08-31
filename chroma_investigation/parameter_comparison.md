# MAD-NG versus chroma-file parameters

The MAD-NG columns are from the tune-matched model used for the plots. The
chroma columns are read from the corresponding XImeter export or fitted from
its five plateau values. A dash means that the chroma export does not contain
that machine/model parameter.

| quantity | normal MAD-NG | normal chroma | inverted MAD-NG | inverted chroma |
|---|---:|---:|---:|---:|
| (Q_x) | 4.171101 | 4.171627 (0 mm) | 4.233491 | 4.233322 (0 mm) |
| (Q_y) | 4.229443 | 4.230093 (0 mm) | 4.127960 | 4.127730 (0 mm) |
| (Q_x') | -3.357215 | -3.4486 ± 0.4204 | -3.380443 | -3.4769 ± 0.3264 |
| (Q_y') | -6.768489 | -6.8077 ± 0.6796 | -6.674395 | -6.5495 ± 0.4422 |
| (alpha_p) | 0.065492 | 0.06259 ± 0.05551 | 0.063389 | 0.06256 ± 0.03312 |
| phase-slip factor (eta=1/gamma^2-alpha_p) | 0.664364 | 0.667263 | 0.666468 | 0.667295 |
| (gamma) | 1.1705262 | — | 1.1705262 | — |
| (eta) | 0.5197529 | — | 0.5197529 | — |
| momentum [GeV/c] | 0.5708302 | — | 0.5708302 | — |
| circumference [m] | 157.08 | — | 157.08 | — |
| effective (C/(2pi)) radius [m] | 25.00006 | — | 25.00006 | — |

The chroma-file plateau data used for the last two fits are:

| setting | RF offset [mm] | `Dp/p` | `Frev` [Hz] | `Frev` SEM [Hz] |
|---|---:|---:|---:|---:|
| normal | -2 | -1.245632e-3 | 993500.461 | 6.715 |
| normal | -1 | -6.279661e-4 | 993910.267 | 4.560 |
| normal | 0 | 0 | 994326.909 | 4.836 |
| normal | +1 | +5.947159e-4 | 994721.491 | 6.514 |
| normal | +2 | +1.184310e-3 | 995112.673 | 6.403 |
| inverted | -2 | -1.251448e-3 | 993554.545 | 4.119 |
| inverted | -1 | -6.403174e-4 | 993960.061 | 3.195 |
| inverted | 0 | 0 | 994384.942 | 2.044 |
| inverted | +1 | +6.329736e-4 | 994804.952 | 3.244 |
| inverted | +2 | +1.231421e-3 | 995202.048 | 3.609 |

The complete machine constants, matched quadrupole knobs, and source values are
in [parameters.json](parameters.json). The fit uncertainties above include the
available tune/Frev/Dp/p uncertainties, the 10% model-dispersion uncertainty
for the orbit-calibrated branch, and the guessed 1% relative energy uncertainty
in (1/gamma^2).
