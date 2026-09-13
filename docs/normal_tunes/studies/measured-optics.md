# Measured optics

PSB ring 3 · AC-dipole turn-by-turn and the tune/chroma scan · 4 machine configurations, each against the same lattice tune-matched to the measurement. Every beta bar is omc3's propagated error added in quadrature to a bootstrap over the folder's AC-dipole kicks.

## Measured tunes

| configuration | natural $Q_x$ | natural $Q_y$ | model $Q'_H$ / $Q'_V$ | measured $Q'_H$ / $Q'_V$ (XImeter) | measured $Q'_H$ / $Q'_V$ (closed-orbit) |
|---|---|---|---|---|---|
| Normal tunes, 29th | 4.17297 ± 0.00004 | 4.22925 ± 0.00014 | -3.359 / -6.742 | -3.487 ± 0.017 / -6.836 ± 0.038 | -3.723 ± 0.044 / -7.067 ± 0.144 |
| Normal tunes, QDE14 error | 4.17306 ± 0.00006 | 4.22986 ± 0.00012 | -3.359 / -6.743 | -3.421 ± 0.016 / -6.871 ± 0.036 | -3.560 ± 0.021 / -7.248 ± 0.029 |
| Normal tunes, QDE14+QDE3 error | 4.17314 ± 0.00005 | 4.22883 ± 0.00025 | -3.359 / -6.741 | -3.469 ± 0.018 / -6.790 ± 0.040 | -3.649 ± 0.007 / -7.081 ± 0.018 |
| Normal tunes, sextupoles on | 4.17354 ± 0.00009 | 4.22938 ± 0.00028 | -3.359 / -6.743 | -3.620 ± 0.015 / -6.630 ± 0.036 | -3.841 ± 0.071 / -6.861 ± 0.073 |

## ACDipole config

=== "Normal tunes, 29th"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `m2mm` | 0.173801 / 0.240995 | 0.1738 / 0.2410 | 4.6e-07 / 1.4e-06 | 31 |
    | `0mm` | 0.169601 / 0.232495 | 0.1696 / 0.2325 | 4.6e-07 / 2.2e-06 | 32 |
    | `2mm` | 0.165201 / 0.224596 | 0.1652 / 0.2246 | 3.9e-07 / 1.6e-06 | 36 |

    Optics from `2mm`.

=== "Normal tunes, QDE14 error"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `m2mm` | 0.173601 / 0.241296 | 0.1736 / 0.2413 | 2.9e-07 / 1.3e-06 | 41 |
    | `0mm` | 0.169301 / 0.232696 | 0.1693 / 0.2327 | 4.6e-07 / 1.7e-06 | 30 |
    | `2mm` | 0.165201 / 0.224294 | 0.1652 / 0.2243 | 6.1e-07 / 2.1e-06 | 36 |

    Optics from `m2mm`.

=== "Normal tunes, QDE14+QDE3 error"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `m2mm` | 0.174001 / 0.240795 | 0.1740 / 0.2408 | 4.3e-07 / 2.0e-06 | 26 |
    | `0mm` | 0.169601 / 0.232395 | 0.1696 / 0.2324 | 3.9e-07 / 1.4e-06 | 26 |
    | `2mm` | 0.165401 / 0.224196 | 0.1654 / 0.2242 | 2.4e-07 / 1.2e-06 | 22 |

    Optics from `m2mm`.

=== "Normal tunes, sextupoles on"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `m2mm` | 0.174401 / 0.240395 | 0.1744 / 0.2404 | 6.5e-07 / 2.6e-06 | 30 |
    | `0mm` | 0.169801 / 0.232496 | 0.1698 / 0.2325 | 3.4e-07 / 1.4e-06 | 29 |
    | `2mm` | 0.165401 / 0.224295 | 0.1654 / 0.2243 | 6.1e-07 / 2.2e-06 | 34 |

    Optics from `2mm`.

## Across configurations

<figure markdown>
![measured beta-beating against each model](../../assets/figures/scenarios/normal/comparison_beta_beat.png)
<figcaption>Measured beta-beating along s against each reference model, from phase (filled) and from amplitude (open).</figcaption>
</figure>

## Measured against the model

=== "Normal tunes, 29th"

    <figure markdown>
    ![measured beta against the matched model](../../assets/figures/p17_p23_final/measured_beta.png)
    <figcaption>Measured beta from phase and from amplitude, against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured beta-beating against the matched model](../../assets/figures/p17_p23_final/measured_beat.png)
    <figcaption>Measured beta-beating against the tune-matched model, both planes.</figcaption>
    </figure>

    <figure markdown>
    ![measured coupling amplitudes](../../assets/figures/p17_p23_final/measured_coupling.png)
    <figcaption>Measured |f1001| and |f1010| against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured phase advance against the matched model](../../assets/figures/p17_p23_final/measured_phase.png)
    <figcaption>Measured phase advance between adjacent BPMs against the tune-matched model, both planes.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![measured beta against the matched model](../../assets/figures/p17_p23_final_qde14/measured_beta.png)
    <figcaption>Measured beta from phase and from amplitude, against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured beta-beating against the matched model](../../assets/figures/p17_p23_final_qde14/measured_beat.png)
    <figcaption>Measured beta-beating against the tune-matched model, both planes.</figcaption>
    </figure>

    <figure markdown>
    ![measured coupling amplitudes](../../assets/figures/p17_p23_final_qde14/measured_coupling.png)
    <figcaption>Measured |f1001| and |f1010| against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured phase advance against the matched model](../../assets/figures/p17_p23_final_qde14/measured_phase.png)
    <figcaption>Measured phase advance between adjacent BPMs against the tune-matched model, both planes.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![measured beta against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/measured_beta.png)
    <figcaption>Measured beta from phase and from amplitude, against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured beta-beating against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/measured_beat.png)
    <figcaption>Measured beta-beating against the tune-matched model, both planes.</figcaption>
    </figure>

    <figure markdown>
    ![measured coupling amplitudes](../../assets/figures/p17_p23_final_qde14_qde3/measured_coupling.png)
    <figcaption>Measured |f1001| and |f1010| against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured phase advance against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/measured_phase.png)
    <figcaption>Measured phase advance between adjacent BPMs against the tune-matched model, both planes.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![measured beta against the matched model](../../assets/figures/p17_p23_final_sexts_on/measured_beta.png)
    <figcaption>Measured beta from phase and from amplitude, against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured beta-beating against the matched model](../../assets/figures/p17_p23_final_sexts_on/measured_beat.png)
    <figcaption>Measured beta-beating against the tune-matched model, both planes.</figcaption>
    </figure>

    <figure markdown>
    ![measured coupling amplitudes](../../assets/figures/p17_p23_final_sexts_on/measured_coupling.png)
    <figcaption>Measured |f1001| and |f1010| against the tune-matched model.</figcaption>
    </figure>

    <figure markdown>
    ![measured phase advance against the matched model](../../assets/figures/p17_p23_final_sexts_on/measured_phase.png)
    <figcaption>Measured phase advance between adjacent BPMs against the tune-matched model, both planes.</figcaption>
    </figure>
