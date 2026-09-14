# Delta orbits

PSB ring 3 · single momentum · both planes as delta orbits · 4 machine configurations as tabs.

## Fitted knobs, per family

=== "Normal tunes, 29th"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.69 | 4.78 | 0.23 | 8.59 | 47 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.35 | 4.25 | 0.22 | 7.80 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 5.62 | 12.39 | 3.20 | 1.55 | 32 of 48 |

=== "Normal tunes, QDE14 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.96 | 5.51 | 0.27 | 10.40 | 45 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.48 | 4.29 | 0.25 | 9.33 | 45 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 5.91 | 15.87 | 3.17 | 1.36 | 28 of 48 |

=== "Normal tunes, QDE14+QDE3 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 3.12 | 5.95 | 0.26 | 10.66 | 45 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.71 | 5.28 | 0.24 | 9.42 | 44 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 5.30 | 10.01 | 3.35 | 1.48 | 30 of 48 |

=== "Normal tunes, sextupoles on"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 3.17 | 5.39 | 0.23 | 14.02 | 47 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 2.86 | 5.05 | 0.22 | 13.45 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 5.78 | 16.11 | 3.59 | 0.82 | 20 of 48 |

## Fitted knobs

=== "Normal tunes, 29th"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/p17_p23_final/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/p17_p23_final_qde14/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final_qde14/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final_qde14/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final_qde14/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![gradient error per magnet against s](../../assets/figures/p17_p23_final_sexts_on/delta/delta_dk1l_by_s.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final_sexts_on/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final_sexts_on/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final_sexts_on/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

## Fitted lattice, against the tune-matched model

=== "Normal tunes, 29th"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final_qde14/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final_qde14/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final_qde14/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final_qde14/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final_qde14/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final_sexts_on/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final_sexts_on/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final_sexts_on/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final_sexts_on/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final_sexts_on/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

## Tune and chromaticity

=== "Normal tunes, 29th"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final_qde14/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final_qde14/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final_sexts_on/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final_sexts_on/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

## Residuals

=== "Normal tunes, 29th"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final_qde14/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final_qde14_qde3/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final_sexts_on/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final_sexts_on/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final_sexts_on/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>
