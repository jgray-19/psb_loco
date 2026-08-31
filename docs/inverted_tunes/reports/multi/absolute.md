# Absolute orbits — multi momentum

PSB ring 3 · method 2 · multi momentum · 2026-08-21 corrector scans · both planes absolute · [method](../../../method.md)

**Multi momentum fit.** All measured RF offsets, 12 correctors, 4 non-zero `dkick` values per momentum. Warm-started from the matching nominal-momentum absolute fit; prior centred on zero. All RF residuals are in-sample.

## Machine and start models

=== "Inverted tunes, 28th"

    |  | measured | model, $k_1$ as sent | model, matched to the tune |
    |---|---|---|---|
    | QFO / QDE, MAD $k_1$ | 0.739524 / -0.737759, from LSA | the same | 0.734112 / -0.741176 (-0.73 % / +0.46 %) |
    | beta-beating from phase, x | — | 8.3 % rms, 17.1 % peak | 8.1 % rms, 16.0 % peak |
    | beta-beating from phase, y | — | 6.0 % rms, 12.1 % peak | 6.1 % rms, 11.7 % peak |
    | beta-beating from amplitude, x | — | 10.7 % rms, 25.4 % peak | 10.6 % rms, 26.1 % peak |
    | beta-beating from amplitude, y | — | 6.6 % rms, 11.7 % peak | 6.6 % rms, 12.2 % peak |
    | AC-dipole drive, 0mm | 0.230502 / 0.130996 (set 0.2305 / 0.1310) | — | — |
    | AC-dipole drive, m2mm | 0.234702 / 0.139496 (set 0.2347 / 0.1395) | — | — |
    | AC-dipole drive, 2mm | 0.226503 / 0.122793 (set 0.2265 / 0.1228) | — | — |
    | measurement variation / fit error | tune 1.3e-04 / 8.3e-05, $dq1/dq2$ fit $1\sigma$ 0.038 / 0.063 | — | — |

=== "Inverted tunes, QDE14 error"

    |  | measured | model, $k_1$ as sent | model, matched to the tune |
    |---|---|---|---|
    | QFO / QDE, MAD $k_1$ | 0.739524 / -0.737759, from LSA | the same | 0.733986 / -0.741113 (-0.75 % / +0.45 %) |
    | beta-beating from phase, x | — | 10.6 % rms, 24.4 % peak | 10.3 % rms, 23.2 % peak |
    | beta-beating from phase, y | — | 5.9 % rms, 11.1 % peak | 6.1 % rms, 10.7 % peak |
    | beta-beating from amplitude, x | — | 11.6 % rms, 26.6 % peak | 11.5 % rms, 27.3 % peak |
    | beta-beating from amplitude, y | — | 6.7 % rms, 12.0 % peak | 6.7 % rms, 12.6 % peak |
    | AC-dipole drive, 0mm | 0.229701 / 0.131397 (set 0.2297 / 0.1314) | — | — |
    | AC-dipole drive, m2mm | 0.234201 / 0.139897 (set 0.2342 / 0.1399) | — | — |
    | AC-dipole drive, 2mm | 0.225702 / 0.123296 (set 0.2257 / 0.1233) | — | — |
    | measurement variation / fit error | tune 1.8e-04 / 3.2e-04, $dq1/dq2$ fit $1\sigma$ 0.031 / 0.051 | — | — |

=== "Inverted tunes, QDE14+QDE3 error"

    |  | measured | model, $k_1$ as sent | model, matched to the tune |
    |---|---|---|---|
    | QFO / QDE, MAD $k_1$ | 0.739524 / -0.737759, from LSA | the same | 0.733947 / -0.741091 (-0.75 % / +0.45 %) |
    | beta-beating from phase, x | — | 11.3 % rms, 24.1 % peak | 10.8 % rms, 22.9 % peak |
    | beta-beating from phase, y | — | 6.1 % rms, 11.2 % peak | 6.2 % rms, 11.5 % peak |
    | beta-beating from amplitude, x | — | 12.1 % rms, 36.3 % peak | 12.0 % rms, 35.0 % peak |
    | beta-beating from amplitude, y | — | 6.1 % rms, 11.9 % peak | 6.1 % rms, 12.4 % peak |
    | AC-dipole drive, 0mm | 0.229401 / 0.131597 (set 0.2294 / 0.1316) | — | — |
    | AC-dipole drive, m2mm | 0.233901 / 0.139996 (set 0.2339 / 0.1400) | — | — |
    | AC-dipole drive, 2mm | 0.225402 / 0.123496 (set 0.2254 / 0.1235) | — | — |
    | measurement variation / fit error | tune 5.8e-05 / 1.0e-04, $dq1/dq2$ fit $1\sigma$ 0.030 / 0.063 | — | — |

=== "Inverted tunes, sextupoles on"

    |  | measured | model, $k_1$ as sent | model, matched to the tune |
    |---|---|---|---|
    | QFO / QDE, MAD $k_1$ | 0.739524 / -0.737759, from LSA | the same | 0.734027 / -0.741169 (-0.74 % / +0.46 %) |
    | beta-beating from phase, x | — | 8.6 % rms, 17.7 % peak | 8.3 % rms, 16.6 % peak |
    | beta-beating from phase, y | — | 5.3 % rms, 9.0 % peak | 5.4 % rms, 9.6 % peak |
    | beta-beating from amplitude, x | — | 11.1 % rms, 26.1 % peak | 10.9 % rms, 26.8 % peak |
    | beta-beating from amplitude, y | — | 6.8 % rms, 11.9 % peak | 6.8 % rms, 12.5 % peak |
    | AC-dipole drive, 0mm | 0.229802 / 0.131895 (set 0.2298 / 0.1319) | — | — |
    | AC-dipole drive, m2mm | 0.234001 / 0.140295 (set 0.2340 / 0.1403) | — | — |
    | AC-dipole drive, 2mm | 0.225802 / 0.123494 (set 0.2258 / 0.1235) | — | — |
    | measurement variation / fit error | tune 1.6e-04 / 2.1e-04, $dq1/dq2$ fit $1\sigma$ 0.042 / 0.074 | — | — |

## Fitted knobs

=== "Inverted tunes, 28th"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, bends and offsets, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.86 | 4.77 | 0.22 | 4.74 | 43 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.37 | 0.03 | 3.22 | 26 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.14 | 0.42 | 0.02 | 3.71 | 41 of 48 |
    | Gradients, bends, offsets and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.76 | 3.97 | 0.22 | 4.74 | 42 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.37 | 0.03 | 3.22 | 26 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.14 | 0.42 | 0.02 | 3.93 | 39 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.61 | 4.46 | 5.82 | 0.18 | 0 of 48 |

=== "Inverted tunes, QDE14 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, bends and offsets, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.90 | 4.80 | 0.22 | 5.27 | 42 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.37 | 0.03 | 3.17 | 25 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.14 | 0.41 | 0.02 | 3.62 | 41 of 48 |
    | Gradients, bends, offsets and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.81 | 4.11 | 0.22 | 4.88 | 41 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.12 | 0.37 | 0.03 | 3.17 | 25 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.13 | 0.42 | 0.02 | 3.90 | 39 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.73 | 4.87 | 5.92 | 0.21 | 0 of 48 |

=== "Inverted tunes, QDE14+QDE3 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, bends and offsets, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.86 | 4.74 | 0.22 | 4.71 | 43 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.37 | 0.03 | 3.20 | 26 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.14 | 0.42 | 0.02 | 3.64 | 41 of 48 |
    | Gradients, bends, offsets and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.76 | 4.01 | 0.22 | 4.71 | 44 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.37 | 0.03 | 3.20 | 26 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.13 | 0.42 | 0.02 | 3.92 | 39 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.76 | 5.12 | 5.95 | 0.16 | 0 of 48 |

=== "Inverted tunes, sextupoles on"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, bends and offsets, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.74 | 4.51 | 0.22 | 3.91 | 44 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.37 | 0.03 | 3.33 | 26 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.14 | 0.42 | 0.02 | 3.71 | 41 of 48 |
    | Gradients, bends, offsets and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.64 | 3.70 | 0.22 | 4.51 | 42 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.37 | 0.03 | 3.32 | 26 of 32 |
    |  | offsets \[mm] | 32 of 48 | 0.13 | 0.42 | 0.02 | 3.98 | 39 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.65 | 4.43 | 5.95 | 0.16 | 0 of 48 |

### Gradients

=== "Inverted tunes, 28th"

    <figure markdown>
    ![Fitted gradient error per magnet, one panel per case.](../../../assets/figures/inverted_second/multi/absolute/absolute_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![The same gradients as |value| / σ.](../../../assets/figures/inverted_second/multi/absolute/absolute_dk1l_significance.png)
    <figcaption>The same gradients as |value| / σ.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![Fitted gradient error per magnet, one panel per case.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![The same gradients as |value| / σ.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_dk1l_significance.png)
    <figcaption>The same gradients as |value| / σ.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![Fitted gradient error per magnet, one panel per case.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![The same gradients as |value| / σ.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_dk1l_significance.png)
    <figcaption>The same gradients as |value| / σ.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![Fitted gradient error per magnet, one panel per case.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![The same gradients as |value| / σ.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_dk1l_significance.png)
    <figcaption>The same gradients as |value| / σ.</figcaption>
    </figure>

### Bends

=== "Inverted tunes, 28th"

    <figure markdown>
    ![Fitted bends per magnet, one panel per case.](../../../assets/figures/inverted_second/multi/absolute/absolute_dk0l_by_s.png)
    <figcaption>Fitted bends per magnet, one panel per case.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![Fitted bends per magnet, one panel per case.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_dk0l_by_s.png)
    <figcaption>Fitted bends per magnet, one panel per case.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![Fitted bends per magnet, one panel per case.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_dk0l_by_s.png)
    <figcaption>Fitted bends per magnet, one panel per case.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![Fitted bends per magnet, one panel per case.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_dk0l_by_s.png)
    <figcaption>Fitted bends per magnet, one panel per case.</figcaption>
    </figure>

### Quadrupole offsets

=== "Inverted tunes, 28th"

    <figure markdown>
    ![Fitted quadrupole offsets per magnet, one panel per case.](../../../assets/figures/inverted_second/multi/absolute/absolute_dy_by_s.png)
    <figcaption>Fitted quadrupole offsets per magnet, one panel per case.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![Fitted quadrupole offsets per magnet, one panel per case.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_dy_by_s.png)
    <figcaption>Fitted quadrupole offsets per magnet, one panel per case.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![Fitted quadrupole offsets per magnet, one panel per case.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_dy_by_s.png)
    <figcaption>Fitted quadrupole offsets per magnet, one panel per case.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![Fitted quadrupole offsets per magnet, one panel per case.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_dy_by_s.png)
    <figcaption>Fitted quadrupole offsets per magnet, one panel per case.</figcaption>
    </figure>

### Rolls

=== "Inverted tunes, 28th"

    <figure markdown>
    ![Fitted quadrupole roll per magnet, for the cases that free it.](../../../assets/figures/inverted_second/multi/absolute/absolute_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, for the cases that free it.</figcaption>
    </figure>

    <figure markdown>
    ![The rolls as |value| / σ.](../../../assets/figures/inverted_second/multi/absolute/absolute_tilt_significance.png)
    <figcaption>The rolls as |value| / σ.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![Fitted quadrupole roll per magnet, for the cases that free it.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, for the cases that free it.</figcaption>
    </figure>

    <figure markdown>
    ![The rolls as |value| / σ.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_tilt_significance.png)
    <figcaption>The rolls as |value| / σ.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![Fitted quadrupole roll per magnet, for the cases that free it.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, for the cases that free it.</figcaption>
    </figure>

    <figure markdown>
    ![The rolls as |value| / σ.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_tilt_significance.png)
    <figcaption>The rolls as |value| / σ.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![Fitted quadrupole roll per magnet, for the cases that free it.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, for the cases that free it.</figcaption>
    </figure>

    <figure markdown>
    ![The rolls as |value| / σ.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_tilt_significance.png)
    <figcaption>The rolls as |value| / σ.</figcaption>
    </figure>

## Fitted lattice

=== "Inverted tunes, 28th, nominal"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.](../../../assets/figures/inverted_second/multi/absolute/absolute_optics.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.</figcaption>
    </figure>

=== "Inverted tunes, 28th, matched"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.](../../../assets/figures/inverted_second/multi/absolute/absolute_optics_matched.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error, nominal"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_optics.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error, matched"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_optics_matched.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error, nominal"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_optics.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error, matched"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_optics_matched.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on, nominal"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_optics.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model on the $k_1$ sent to the magnets.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on, matched"

    <figure markdown>
    ![Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_optics_matched.png)
    <figcaption>Beta-beating, phase error and dispersion along s, per case, with the measured beta-beating at the BPMs taken against the model matched to the measured tune.</figcaption>
    </figure>

### Tunes

=== "Inverted tunes, 28th"

    <figure markdown>
    ![Where each fit put the tune, against the measured tune, with both model lattices for scale.](../../../assets/figures/inverted_second/multi/absolute/absolute_case_tunes.png)
    <figcaption>Where each fit put the tune, against the measured tune, with both model lattices for scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![Where each fit put the tune, against the measured tune, with both model lattices for scale.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_case_tunes.png)
    <figcaption>Where each fit put the tune, against the measured tune, with both model lattices for scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![Where each fit put the tune, against the measured tune, with both model lattices for scale.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_case_tunes.png)
    <figcaption>Where each fit put the tune, against the measured tune, with both model lattices for scale.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![Where each fit put the tune, against the measured tune, with both model lattices for scale.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_case_tunes.png)
    <figcaption>Where each fit put the tune, against the measured tune, with both model lattices for scale.</figcaption>
    </figure>

### Chromaticity

=== "Inverted tunes, 28th"

    <figure markdown>
    ![$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.](../../../assets/figures/inverted_second/multi/absolute/absolute_case_chromaticity.png)
    <figcaption>$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_case_chromaticity.png)
    <figcaption>$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_case_chromaticity.png)
    <figcaption>$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_case_chromaticity.png)
    <figcaption>$dq1$ / $dq2$ error against the measurement, paired bars per case for the two `Dp/p` calibrations (RF-derived chroma, hatched closed-orbit); zero is measured and the band is each calibration's fit $1\sigma$. A case's own fit is one number -- only which measurement it is judged against moves.</figcaption>
    </figure>

## Residuals

=== "Inverted tunes, 28th"

    <figure markdown>
    ![Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.](../../../assets/figures/inverted_second/multi/absolute/absolute_scores.png)
    <figcaption>Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.</figcaption>
    </figure>

    <figure markdown>
    ![Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.](../../../assets/figures/inverted_second/multi/absolute/absolute_residuals.png)
    <figcaption>Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_scores.png)
    <figcaption>Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.</figcaption>
    </figure>

    <figure markdown>
    ![Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.](../../../assets/figures/inverted_qde14_err/multi/absolute/absolute_residuals.png)
    <figcaption>Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_scores.png)
    <figcaption>Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.</figcaption>
    </figure>

    <figure markdown>
    ![Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.](../../../assets/figures/inverted_qde14_qde3_err/multi/absolute/absolute_residuals.png)
    <figcaption>Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_scores.png)
    <figcaption>Residual rms against each scored measurement, per case, as a percentage of the measured amplitude.</figcaption>
    </figure>

    <figure markdown>
    ![Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.](../../../assets/figures/inverted_sexts_on/multi/absolute/absolute_residuals.png)
    <figcaption>Residual rms per BPM, with the measurement's statistical bar and the 0.1 mm BPM zero-offset systematic.</figcaption>
    </figure>

---

## Rerunning this page

=== "Inverted tunes, 28th"

    ```bash
    uv run python scripts/measured_optics.py --campaign inverted_second
    uv run python scripts/run_campaign_fits.py --campaign inverted_second --momentum-mode multi --cases \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_second --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_second --momentum-mode multi --merge
    uv run python scripts/case_optics.py --campaign inverted_second --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/report_cases.py --campaign inverted_second --momentum-mode multi --page absolute
    uv run python reports/loco_option_matrix/make_pages.py --momentum-mode multi --page absolute
    ```

=== "Inverted tunes, QDE14 error"

    ```bash
    uv run python scripts/measured_optics.py --campaign inverted_qde14_err
    uv run python scripts/run_campaign_fits.py --campaign inverted_qde14_err --momentum-mode multi --cases \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_qde14_err --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_qde14_err --momentum-mode multi --merge
    uv run python scripts/case_optics.py --campaign inverted_qde14_err --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/report_cases.py --campaign inverted_qde14_err --momentum-mode multi --page absolute
    uv run python reports/loco_option_matrix/make_pages.py --momentum-mode multi --page absolute
    ```

=== "Inverted tunes, QDE14+QDE3 error"

    ```bash
    uv run python scripts/measured_optics.py --campaign inverted_qde14_qde3_err
    uv run python scripts/run_campaign_fits.py --campaign inverted_qde14_qde3_err --momentum-mode multi --cases \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_qde14_qde3_err --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_qde14_qde3_err --momentum-mode multi --merge
    uv run python scripts/case_optics.py --campaign inverted_qde14_qde3_err --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/report_cases.py --campaign inverted_qde14_qde3_err --momentum-mode multi --page absolute
    uv run python reports/loco_option_matrix/make_pages.py --momentum-mode multi --page absolute
    ```

=== "Inverted tunes, sextupoles on"

    ```bash
    uv run python scripts/measured_optics.py --campaign inverted_sexts_on
    uv run python scripts/run_campaign_fits.py --campaign inverted_sexts_on --momentum-mode multi --cases \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_sexts_on --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/predict_loco.py --campaign inverted_sexts_on --momentum-mode multi --merge
    uv run python scripts/case_optics.py --campaign inverted_sexts_on --momentum-mode multi --options \
        xy__k1+b+dy__bpm-family \
        xy__k1+b+dy+t__bpm-family
    uv run python scripts/report_cases.py --campaign inverted_sexts_on --momentum-mode multi --page absolute
    uv run python reports/loco_option_matrix/make_pages.py --momentum-mode multi --page absolute
    ```
