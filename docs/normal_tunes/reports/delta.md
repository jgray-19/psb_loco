# Delta orbits

PSB ring 3 · multi momentum · both planes as delta orbits · 4 machine configurations as tabs.

## Fitted knobs, per family

=== "Normal tunes, 29th"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.61 | 3.29 | 0.03 | 29.05 | 48 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.66 | 3.35 | 0.03 | 30.22 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 2.89 | 4.26 | 0.45 | 5.91 | 46 of 48 |
    | Gradients and bpm and corrector gains, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.48 | 1.03 | — | — | — |

=== "Normal tunes, QDE14 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.50 | 3.14 | 0.04 | 22.81 | 46 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.50 | 3.10 | 0.04 | 22.74 | 45 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 2.05 | 3.19 | 0.45 | 4.41 | 44 of 48 |
    | Gradients and bpm and corrector gains, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.46 | 1.10 | — | — | — |

=== "Normal tunes, QDE14+QDE3 error"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.50 | 3.09 | 0.03 | 23.74 | 47 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.50 | 3.09 | 0.03 | 23.55 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 1.97 | 3.13 | 0.48 | 3.79 | 44 of 48 |
    | Gradients and bpm and corrector gains, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.48 | 1.09 | — | — | — |

=== "Normal tunes, sextupoles on"

    | case | family | knobs | rms | max | median $\sigma$ | median $\lvert v\rvert/\sigma$ | above 1 |
    |---|---|---|---|---|---|---|---|
    | Gradients, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.66 | 3.50 | 0.03 | 25.94 | 48 of 48 |
    | Gradients and rolls, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 1.71 | 3.56 | 0.03 | 29.48 | 48 of 48 |
    |  | rolls \[mrad] | 32 of 48 | 2.80 | 4.22 | 0.50 | 5.46 | 46 of 48 |
    | Gradients and bpm and corrector gains, lumped to 32 knobs by cell | gradients \[% of nominal $k_1L$] | 32 of 48 | 0.44 | 1.10 | — | — | — |

## Fitted knobs

=== "Normal tunes, 29th"

    <figure markdown>
    ![gradient error per magnet against s, first cases](../../assets/figures/p17_p23_final/multi/delta/delta_dk1l_by_s_1.png)
    <figcaption>Fitted gradient error per magnet, one panel per case (continued below).</figcaption>
    </figure>

    <figure markdown>
    ![gradient error per magnet against s, remaining cases](../../assets/figures/p17_p23_final/multi/delta/delta_dk1l_by_s_2.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final/multi/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final/multi/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final/multi/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![gradient error per magnet against s, first cases](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_dk1l_by_s_1.png)
    <figcaption>Fitted gradient error per magnet, one panel per case (continued below).</figcaption>
    </figure>

    <figure markdown>
    ![gradient error per magnet against s, remaining cases](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_dk1l_by_s_2.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![gradient error per magnet against s, first cases](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_dk1l_by_s_1.png)
    <figcaption>Fitted gradient error per magnet, one panel per case (continued below).</figcaption>
    </figure>

    <figure markdown>
    ![gradient error per magnet against s, remaining cases](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_dk1l_by_s_2.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![gradient error per magnet against s, first cases](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_dk1l_by_s_1.png)
    <figcaption>Fitted gradient error per magnet, one panel per case (continued below).</figcaption>
    </figure>

    <figure markdown>
    ![gradient error per magnet against s, remaining cases](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_dk1l_by_s_2.png)
    <figcaption>Fitted gradient error per magnet, one panel per case.</figcaption>
    </figure>

    <figure markdown>
    ![gradient error over its own error bar](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_dk1l_significance.png)
    <figcaption>The same gradients as |value| / sigma, log scale.</figcaption>
    </figure>

    <figure markdown>
    ![quadrupole roll per magnet against s](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_tilt_by_s.png)
    <figcaption>Fitted quadrupole roll per magnet, where rolls were free.</figcaption>
    </figure>

    <figure markdown>
    ![roll over its own error bar](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_tilt_significance.png)
    <figcaption>The same rolls as |value| / sigma, log scale.</figcaption>
    </figure>

## Gains

=== "Normal tunes, 29th"

    <figure markdown>
    ![fitted corrector and BPM gains](../../assets/figures/p17_p23_final/multi/delta/delta_gains.png)
    <figcaption>Fitted corrector kick gain per corrector, and BPM gain per BPM and plane, where gains were free. Only differences between correctors of one plane are determined. A plane's overall scale is shared between its BPM gains and corrector gains, so read the product (1 + b)(1 + g), not the two separately: with off-momentum data the vertical BPM gains move far from zero while the vertical corrector gains move the opposite way.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![fitted corrector and BPM gains](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_gains.png)
    <figcaption>Fitted corrector kick gain per corrector, and BPM gain per BPM and plane, where gains were free. Only differences between correctors of one plane are determined. A plane's overall scale is shared between its BPM gains and corrector gains, so read the product (1 + b)(1 + g), not the two separately: with off-momentum data the vertical BPM gains move far from zero while the vertical corrector gains move the opposite way.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![fitted corrector and BPM gains](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_gains.png)
    <figcaption>Fitted corrector kick gain per corrector, and BPM gain per BPM and plane, where gains were free. Only differences between correctors of one plane are determined. A plane's overall scale is shared between its BPM gains and corrector gains, so read the product (1 + b)(1 + g), not the two separately: with off-momentum data the vertical BPM gains move far from zero while the vertical corrector gains move the opposite way.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![fitted corrector and BPM gains](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_gains.png)
    <figcaption>Fitted corrector kick gain per corrector, and BPM gain per BPM and plane, where gains were free. Only differences between correctors of one plane are determined. A plane's overall scale is shared between its BPM gains and corrector gains, so read the product (1 + b)(1 + g), not the two separately: with off-momentum data the vertical BPM gains move far from zero while the vertical corrector gains move the opposite way.</figcaption>
    </figure>

## Fitted lattice, against the tune-matched model

=== "Normal tunes, 29th"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final/multi/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final/multi/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final/multi/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final/multi/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final/multi/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![beta-beating against the matched model](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_beta_beating_matched.png)
    <figcaption>Beta-beating against the tune-matched model, with the measured points; the machine-knob model is the dotted curve.</figcaption>
    </figure>

    <figure markdown>
    ![phase error against the matched model](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_phase_error_matched.png)
    <figcaption>Phase error, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![BPM-to-BPM phase advance against the matched model](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_phase_advance_matched.png)
    <figcaption>Phase advance between adjacent BPMs, computed from each fitted lattice, the matched model and the measured points.</figcaption>
    </figure>

    <figure markdown>
    ![dispersion against the matched model](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_dispersion_matched.png)
    <figcaption>Dispersion, referred to the lattice matched to the measured tune.</figcaption>
    </figure>

    <figure markdown>
    ![coupling against the matched model](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_coupling_matched.png)
    <figcaption>Coupling amplitudes, referred to the tune-matched lattice.</figcaption>
    </figure>

## Tune and chromaticity

=== "Normal tunes, 29th"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final/multi/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final/multi/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![fitted tune per case](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_case_tunes.png)
    <figcaption>Fitted tune per case against the measured tune, bar length is the error.</figcaption>
    </figure>

    <figure markdown>
    ![fitted chromaticity per case](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_case_chromaticity.png)
    <figcaption>Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations.</figcaption>
    </figure>

## Residuals

=== "Normal tunes, 29th"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final/multi/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final/multi/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final/multi/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final_qde14/multi/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Normal tunes, QDE14+QDE3 error"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final_qde14_qde3/multi/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>

=== "Normal tunes, sextupoles on"

    <figure markdown>
    ![delta-orbit residual per BPM](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_residuals_delta.png)
    <figcaption>Delta-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![closed-orbit residual per BPM](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_residuals_absolute.png)
    <figcaption>Closed-orbit residual rms per BPM, measured minus model.</figcaption>
    </figure>

    <figure markdown>
    ![residual per scored measurement](../../assets/figures/p17_p23_final_sexts_on/multi/delta/delta_scores.png)
    <figcaption>Residual rms per scored measurement, as a percentage of the measured amplitude, log scale.</figcaption>
    </figure>
