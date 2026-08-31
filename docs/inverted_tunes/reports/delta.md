# Delta orbits

PSB ring 3 · single momentum · both planes as delta orbits · 4 machine configurations as tabs.

## Fitted knobs, per family

=== "Inverted tunes, 28th"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.61 | 5.90 | 0.02 | 101.61 | 48 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.76 | 0.97 | 0.02 | 48.74 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.37 | 3.71 | 0.36 | 2.25 | 32 of 48 |

=== "Inverted tunes, QDE14 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 3.41 | 7.35 | 0.02 | 129.83 | 48 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.76 | 0.98 | 0.02 | 48.52 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.19 | 3.30 | 0.35 | 1.38 | 28 of 48 |

=== "Inverted tunes, QDE14+QDE3 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.93 | 5.86 | 0.02 | 135.40 | 46 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.77 | 0.98 | 0.02 | 50.21 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.96 | 4.45 | 0.35 | 4.77 | 40 of 48 |

=== "Inverted tunes, sextupoles on"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.85 | 5.79 | 0.02 | 127.64 | 47 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.77 | 0.98 | 0.02 | 50.07 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.92 | 3.74 | 0.36 | 3.89 | 39 of 48 |

## Fitted knobs

=== "Inverted tunes, 28th"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/inverted_second/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/inverted_second/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/inverted_second/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/inverted_second/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/inverted_qde14_err/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/inverted_qde14_err/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/inverted_qde14_err/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/inverted_qde14_err/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/inverted_qde14_qde3_err/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/inverted_qde14_qde3_err/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/inverted_qde14_qde3_err/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/inverted_qde14_qde3_err/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/inverted_sexts_on/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/inverted_sexts_on/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/inverted_sexts_on/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/inverted_sexts_on/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

## Fitted lattice, against the start model

=== "Inverted tunes, 28th"

    <figure markdown>
    ![beta-beating along s](../../assets/figures/inverted_second/delta/delta_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../assets/figures/inverted_second/delta/delta_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../assets/figures/inverted_second/delta/delta_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../assets/figures/inverted_second/delta/delta_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![beta-beating along s](../../assets/figures/inverted_qde14_err/delta/delta_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../assets/figures/inverted_qde14_err/delta/delta_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../assets/figures/inverted_qde14_err/delta/delta_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../assets/figures/inverted_qde14_err/delta/delta_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![beta-beating along s](../../assets/figures/inverted_qde14_qde3_err/delta/delta_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../assets/figures/inverted_qde14_qde3_err/delta/delta_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../assets/figures/inverted_qde14_qde3_err/delta/delta_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../assets/figures/inverted_qde14_qde3_err/delta/delta_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![beta-beating along s](../../assets/figures/inverted_sexts_on/delta/delta_beta_beating.png)
    <figcaption>Beta-beating of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![phase error along s](../../assets/figures/inverted_sexts_on/delta/delta_phase_error.png)
    <figcaption>Phase error of each fitted lattice, ring-wide slope kept.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion along s](../../assets/figures/inverted_sexts_on/delta/delta_dispersion.png)
    <figcaption>Dispersion of each fitted lattice, with the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![coupling RDT amplitudes along s](../../assets/figures/inverted_sexts_on/delta/delta_coupling.png)
    <figcaption>Coupling |f1001| and |f1010|, with omc3's measured amplitudes.</figcaption>
    </figure>

## Fitted lattice, against the tune-matched model

=== "Inverted tunes, 28th"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/inverted_second/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/inverted_second/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/inverted_second/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/inverted_second/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/inverted_qde14_err/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/inverted_qde14_err/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/inverted_qde14_err/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/inverted_qde14_err/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/inverted_qde14_qde3_err/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/inverted_qde14_qde3_err/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/inverted_qde14_qde3_err/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/inverted_qde14_qde3_err/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/inverted_sexts_on/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/inverted_sexts_on/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/inverted_sexts_on/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/inverted_sexts_on/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

## Tune and chromaticity

=== "Inverted tunes, 28th"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/inverted_second/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/inverted_second/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/inverted_qde14_err/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/inverted_qde14_err/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/inverted_qde14_qde3_err/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/inverted_qde14_qde3_err/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/inverted_sexts_on/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/inverted_sexts_on/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

## Residuals

=== "Inverted tunes, 28th"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/inverted_second/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/inverted_second/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/inverted_second/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/inverted_qde14_err/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/inverted_qde14_err/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/inverted_qde14_err/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Inverted tunes, QDE14+QDE3 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/inverted_qde14_qde3_err/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/inverted_qde14_qde3_err/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/inverted_qde14_qde3_err/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Inverted tunes, sextupoles on"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/inverted_sexts_on/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/inverted_sexts_on/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/inverted_sexts_on/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>
