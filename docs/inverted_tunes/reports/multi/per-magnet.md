# One knob per magnet

PSB ring 3 · multi momentum · mixed orbit-matching modes · 4 machine configurations as tabs.

## Fitted knobs, per family

=== "Inverted tunes, 28th"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, one knob per magnet, delta orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 9.26 | 22.81 | 0.02 | 342.73 | 48 of 48 |
    | Gradients, bends and offsets, one knob per magnet, absolute orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 5.27 | 13.99 | 1.54 | 2.88 | 39 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.36 | 0.03 | 3.53 | 26 of 32 |
    |  | offsets \[mm] | 48 of 48 | 0.15 | 0.49 | 0.06 | 1.70 | 32 of 48 |

=== "Inverted tunes, QDE14 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, one knob per magnet, delta orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 10.29 | 25.04 | 0.02 | 346.66 | 48 of 48 |
    | Gradients, bends and offsets, one knob per magnet, absolute orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 5.83 | 15.17 | 1.54 | 2.98 | 39 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.36 | 0.03 | 3.46 | 25 of 32 |
    |  | offsets \[mm] | 48 of 48 | 0.15 | 0.48 | 0.06 | 1.67 | 31 of 48 |

=== "Inverted tunes, QDE14+QDE3 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, one knob per magnet, delta orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 9.83 | 23.75 | 0.02 | 344.60 | 48 of 48 |
    | Gradients, bends and offsets, one knob per magnet, absolute orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 5.54 | 14.04 | 1.55 | 2.91 | 39 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.36 | 0.03 | 3.51 | 26 of 32 |
    |  | offsets \[mm] | 48 of 48 | 0.15 | 0.48 | 0.06 | 1.66 | 31 of 48 |

=== "Inverted tunes, sextupoles on"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, one knob per magnet, delta orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 7.24 | 19.96 | 0.02 | 251.72 | 48 of 48 |
    | Gradients, bends and offsets, one knob per magnet, absolute orbits | gradients \[% of nominal $k_1L$] | 48 of 48 | 4.33 | 12.21 | 1.54 | 2.35 | 38 of 48 |
    |  | bends \[% of nominal bend angle] | 32 of 32 | 0.13 | 0.36 | 0.03 | 3.46 | 26 of 32 |
    |  | offsets \[mm] | 48 of 48 | 0.15 | 0.48 | 0.06 | 1.70 | 31 of 48 |

## Fitted knobs

=== "Inverted tunes, 28th"

    <figure markdown>
    ![gradient error per magnet against s](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![bend error per magnet against s](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_dk0l_by_s.png)
    <figcaption>Fitted bend error per magnet, where bends were free.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole offset per magnet against s](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_dy_by_s.png)
    <figcaption>Fitted quadrupole offset per magnet, where offsets were free.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![gradient error per magnet against s](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![bend error per magnet against s](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_dk0l_by_s.png)
    <figcaption>Fitted bend error per magnet, where bends were free.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole offset per magnet against s](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_dy_by_s.png)
    <figcaption>Fitted quadrupole offset per magnet, where offsets were free.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![gradient error per magnet against s](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![bend error per magnet against s](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_dk0l_by_s.png)
    <figcaption>Fitted bend error per magnet, where bends were free.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole offset per magnet against s](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_dy_by_s.png)
    <figcaption>Fitted quadrupole offset per magnet, where offsets were free.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![gradient error per magnet against s](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![bend error per magnet against s](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_dk0l_by_s.png)
    <figcaption>Fitted bend error per magnet, where bends were free.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole offset per magnet against s](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_dy_by_s.png)
    <figcaption>Fitted quadrupole offset per magnet, where offsets were free.</figcaption>
    </figure>

## Fitted lattice, against the start model

=== "Inverted tunes, 28th"

    <figure markdown>
    ![beta-beating along s](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![beta-beating along s](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![beta-beating along s](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![beta-beating along s](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

## Fitted lattice, against the tune-matched model

=== "Inverted tunes, 28th"

    <figure markdown>
    ![beta-beating against the matched model](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![beta-beating against the matched model](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![beta-beating against the matched model](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![beta-beating against the matched model](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

## Tune and chromaticity

=== "Inverted tunes, 28th"

    <figure markdown>
    ![fitted tune per case](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![fitted tune per case](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![fitted tune per case](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![fitted tune per case](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

## Residuals

=== "Inverted tunes, 28th"

    <figure markdown>
    ![delta-orbit residual per BPM](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../../assets/figures/inverted_second/multi/per-magnet/per-magnet_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../../assets/figures/inverted_qde14_err/multi/per-magnet/per-magnet_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../../assets/figures/inverted_qde14_qde3_err/multi/per-magnet/per-magnet_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![delta-orbit residual per BPM](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../../assets/figures/inverted_sexts_on/multi/per-magnet/per-magnet_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>
