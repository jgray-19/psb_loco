# Measured optics

PSB ring 3 · 2026-08-21 · AC-dipole turn-by-turn and the tune/chroma scan · [method](../method.md)

!!! note "What the beta error bars mean"

    Every bar on this page is omc3's propagated error added in quadrature to a bootstrap over the folder's AC-dipole kicks: the kicks are resampled with replacement and the optics stage rerun on each replica. omc3's bar alone comes from one pooled analysis and contains no repeat of the machine, so it misses the shot-to-shot spread entirely; on its own it is 3-5 times too small for the phase beta. The bootstrap in turn cannot see anything common to the whole folder -- the kick normalisation and BPM calibration the amplitude beta leans on -- which is why the two are added rather than one replacing the other.

## The machine

=== "Normal tunes, 29th, nominal"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17297 / 4.22925 | 3.5e-05 / 1.4e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.708 / -13.153 | 0.032 / 0.073 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

=== "Normal tunes, 29th, matched"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17297 / 4.22925 | 3.5e-05 / 1.4e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.708 / -13.153 | 0.032 / 0.073 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

=== "Normal tunes, QDE14 error, nominal"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17306 / 4.22986 | 5.5e-05 / 1.2e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.582 / -13.219 | 0.030 / 0.068 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

=== "Normal tunes, QDE14 error, matched"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17306 / 4.22986 | 5.5e-05 / 1.2e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.582 / -13.219 | 0.030 / 0.068 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

=== "Normal tunes, QDE14+QDE3 error, nominal"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17314 / 4.22883 | 4.6e-05 / 2.5e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.675 / -13.064 | 0.034 / 0.077 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

=== "Normal tunes, QDE14+QDE3 error, matched"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17314 / 4.22883 | 4.6e-05 / 2.5e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.675 / -13.064 | 0.034 / 0.077 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

=== "Normal tunes, sextupoles on, nominal"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17354 / 4.22938 | 9.2e-05 / 2.8e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.964 / -12.756 | 0.030 / 0.070 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

=== "Normal tunes, sextupoles on, matched"

    | quantity | value | spread across the flat bottom |
    |---|---|---|
    | natural tune $Q_x$ / $Q_y$ | 4.17354 / 4.22938 | 9.2e-05 / 2.8e-04 |
    | $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | -6.964 / -12.756 | 0.030 / 0.070 (fit $1\sigma$) |
    | QFO / QDE circuit, MAD $k_1$ | 0.7289003149 / -0.7442765967 | sent to the magnets |

## AC-dipole drive

=== "Normal tunes, 29th, nominal"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169601 / 0.232495 | 0.1696 / 0.2325 | 4.7e-07 / 2.2e-06 | 32 |
    | `m2mm` | 0.173801 / 0.240995 | 0.1738 / 0.2410 | 4.7e-07 / 1.4e-06 | 31 |
    | `2mm` | 0.165201 / 0.224596 | 0.1652 / 0.2246 | 4.0e-07 / 1.6e-06 | 36 |

    Optics from `2mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_29_Multiturn/normal_tunes/blank_acquisitions/2mm`.

=== "Normal tunes, 29th, matched"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169601 / 0.232495 | 0.1696 / 0.2325 | 4.7e-07 / 2.2e-06 | 32 |
    | `m2mm` | 0.173801 / 0.240995 | 0.1738 / 0.2410 | 4.7e-07 / 1.4e-06 | 31 |
    | `2mm` | 0.165201 / 0.224596 | 0.1652 / 0.2246 | 4.0e-07 / 1.6e-06 | 36 |

    Optics from `2mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_29_Multiturn/normal_tunes/blank_acquisitions/2mm`.

=== "Normal tunes, QDE14 error, nominal"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169301 / 0.232696 | 0.1693 / 0.2327 | 4.7e-07 / 1.7e-06 | 30 |
    | `m2mm` | 0.173601 / 0.241296 | 0.1736 / 0.2413 | 3.0e-07 / 1.3e-06 | 41 |
    | `2mm` | 0.165201 / 0.224294 | 0.1652 / 0.2243 | 6.1e-07 / 2.1e-06 | 36 |

    Optics from `m2mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_29_Multiturn/normal_tunes_qde14_err/blank_acquisitions/m2mm`.

=== "Normal tunes, QDE14 error, matched"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169301 / 0.232696 | 0.1693 / 0.2327 | 4.7e-07 / 1.7e-06 | 30 |
    | `m2mm` | 0.173601 / 0.241296 | 0.1736 / 0.2413 | 3.0e-07 / 1.3e-06 | 41 |
    | `2mm` | 0.165201 / 0.224294 | 0.1652 / 0.2243 | 6.1e-07 / 2.1e-06 | 36 |

    Optics from `m2mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_29_Multiturn/normal_tunes_qde14_err/blank_acquisitions/m2mm`.

=== "Normal tunes, QDE14+QDE3 error, nominal"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169601 / 0.232395 | 0.1696 / 0.2324 | 3.9e-07 / 1.4e-06 | 26 |
    | `m2mm` | 0.174001 / 0.240795 | 0.1740 / 0.2408 | 4.4e-07 / 2.0e-06 | 26 |
    | `2mm` | 0.165401 / 0.224196 | 0.1654 / 0.2242 | 2.4e-07 / 1.2e-06 | 22 |

    Optics from `0mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_29_Multiturn/normal_tunes_qde14_qde3_err/blank_acquisitions/0mm`.

=== "Normal tunes, QDE14+QDE3 error, matched"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169601 / 0.232395 | 0.1696 / 0.2324 | 3.9e-07 / 1.4e-06 | 26 |
    | `m2mm` | 0.174001 / 0.240795 | 0.1740 / 0.2408 | 4.4e-07 / 2.0e-06 | 26 |
    | `2mm` | 0.165401 / 0.224196 | 0.1654 / 0.2242 | 2.4e-07 / 1.2e-06 | 22 |

    Optics from `0mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_29_Multiturn/normal_tunes_qde14_qde3_err/blank_acquisitions/0mm`.

=== "Normal tunes, sextupoles on, nominal"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169801 / 0.232496 | 0.1698 / 0.2325 | 3.4e-07 / 1.4e-06 | 29 |
    | `m2mm` | 0.174401 / 0.240395 | 0.1744 / 0.2404 | 6.6e-07 / 2.6e-06 | 30 |
    | `2mm` | 0.165401 / 0.224295 | 0.1654 / 0.2243 | 6.2e-07 / 2.2e-06 | 34 |

    Optics from `2mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_30_Multiturn/normal_tunes_sext_on/blank_acquisitions/2mm`.

=== "Normal tunes, sextupoles on, matched"

    | folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |
    |---|---|---|---|---|
    | `0mm` | 0.169801 / 0.232496 | 0.1698 / 0.2325 | 3.4e-07 / 1.4e-06 | 29 |
    | `m2mm` | 0.174401 / 0.240395 | 0.1744 / 0.2404 | 6.6e-07 / 2.6e-06 | 30 |
    | `2mm` | 0.165401 / 0.224295 | 0.1654 / 0.2243 | 6.2e-07 / 2.2e-06 | 34 |

    Optics from `2mm`. Preprocessing: `cleaning=svd(rank=2), demodulate, remove_interference, remove_energy_motion`, blanks from `/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_30_Multiturn/normal_tunes_sext_on/blank_acquisitions/2mm`.

## Tune, chromaticity and beta-beating

<figure markdown>
![Each model's tune against the measured tune, every campaign on this page.](../../assets/figures/scenarios/normal/comparison_tunes.png)
<figcaption>Each model's tune against the measured tune, every campaign on this page.</figcaption>
</figure>
<figure markdown>
![$dq1$ / $dq2$ model error against measurement, every campaign on this page.](../../assets/figures/scenarios/normal/comparison_chromaticity.png)
<figcaption>$dq1$ / $dq2$ model error against measurement, every campaign on this page.</figcaption>
</figure>
<figure markdown>
![Measured beta-beating along $s$ against each reference model, from phase beta (filled) and from amplitude beta (open); each curve's rms is in the legend.](../../assets/figures/scenarios/normal/comparison_beta_beat.png)
<figcaption>Measured beta-beating along $s$ against each reference model, from phase beta (filled) and from amplitude beta (open); each curve's rms is in the legend.</figcaption>
</figure>

## Measured against the model

=== "Normal tunes, 29th, nominal"

    This tab's model is stood up on the currents the machine ran at, read from LSA and applied unchanged.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.01x**, y **0.99x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_second/measured_optics.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `2mm` x 0.0029, `2mm` y 0.0029.


=== "Normal tunes, 29th, matched"

    This tab's model is stood up on those same currents, then `kbrqf` and `kbrqd` moved until it sits on the measured tune.

    QFO / QDE move +0.04 % / +0.01 % in magnitude to get there, to 0.729196 / -0.744329.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.00x**, y **1.00x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_second/measured_optics_matched.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `2mm` x 0.0029, `2mm` y 0.0029.


=== "Normal tunes, QDE14 error, nominal"

    This tab's model is stood up on the currents the machine ran at, read from LSA and applied unchanged.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.01x**, y **1.00x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_qde14_err/measured_optics.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `m2mm` x 0.0040, `m2mm` y 0.0033.


=== "Normal tunes, QDE14 error, matched"

    This tab's model is stood up on those same currents, then `kbrqf` and `kbrqd` moved until it sits on the measured tune.

    QFO / QDE move +0.05 % / +0.01 % in magnitude to get there, to 0.729230 / -0.744382.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.00x**, y **1.00x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_qde14_err/measured_optics_matched.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `m2mm` x 0.0040, `m2mm` y 0.0033.


=== "Normal tunes, QDE14+QDE3 error, nominal"

    This tab's model is stood up on the currents the machine ran at, read from LSA and applied unchanged.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.01x**, y **0.99x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_qde14_qde3_err/measured_optics.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `0mm` x 0.0041, `0mm` y 0.0034.


=== "Normal tunes, QDE14+QDE3 error, matched"

    This tab's model is stood up on those same currents, then `kbrqf` and `kbrqd` moved until it sits on the measured tune.

    QFO / QDE move +0.04 % / +0.00 % in magnitude to get there, to 0.729203 / -0.744309.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.00x**, y **1.00x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_qde14_qde3_err/measured_optics_matched.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `0mm` x 0.0041, `0mm` y 0.0034.


=== "Normal tunes, sextupoles on, nominal"

    This tab's model is stood up on the currents the machine ran at, read from LSA and applied unchanged.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.02x**, y **0.99x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_sexts_on/measured_optics.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `2mm` x 0.0031, `2mm` y 0.0028.


=== "Normal tunes, sextupoles on, matched"

    This tab's model is stood up on those same currents, then `kbrqf` and `kbrqd` moved until it sits on the measured tune.

    QFO / QDE move +0.05 % / +0.01 % in magnitude to get there, to 0.729281 / -0.744381.

    Closed-orbit response scaling of this model's tune error, $\sin(\pi Q_\text{machine}) / \sin(\pi Q_\text{model})$: x **1.00x**, y **1.00x**.

    <figure markdown>
    ![Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.](../../assets/figures/normal_sexts_on/measured_optics_matched.png)
    <figcaption>Measured beta against this model, with the beating below each plane; the other model is drawn underneath for scale.</figcaption>
    </figure>

    BPM-to-BPM phase advance against the matched model, rms in units of $2\pi$: `2mm` x 0.0031, `2mm` y 0.0028.


---

## Rerunning this page

```bash
uv run python scripts/measured_optics.py --campaign normal_second normal_qde14_err normal_qde14_qde3_err normal_sexts_on
uv run python scripts/report_cases.py --campaign <slug>
uv run python reports/loco_option_matrix/make_pages.py
```
