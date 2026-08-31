# Method 1 against Method 2

PSB ring 3 · both methods, same 32 cell-grouped knobs, same delta orbits · [method](../method.md)

## The two runs

=== "Normal tunes, 29th"

    | | Method 1 | Method 2 |
    |---|---|---|
    | free knobs | 32 cell-grouped $\Delta k_1 L$ over 48 magnets | 32 cell-grouped $\Delta k_1 L$ over 48 magnets |
    | what it fits | the measured response matrix | 48 delta closed orbits |
    | processes | 1 | 48 |
    | wall clock | 11.7 s | 5.3 s |
    | CPU, whole tree | 22.6 s | 24.6 s |
    | peak RSS | 260 MB | 267 MB |
    | stopped at | `XTOL` after 298 calls | its own convergence test |
    | its own residual | weighted response rms 117.0 → 80.1 | not comparable: a different objective |

=== "Normal tunes, QDE14 error"

    | | Method 1 | Method 2 |
    |---|---|---|
    | free knobs | 32 cell-grouped $\Delta k_1 L$ over 48 magnets | 32 cell-grouped $\Delta k_1 L$ over 48 magnets |
    | what it fits | the measured response matrix | 48 delta closed orbits |
    | processes | 1 | 48 |
    | wall clock | 10.7 s | 20.1 s |
    | CPU, whole tree | 21.7 s | 22.8 s |
    | peak RSS | 254 MB | 268 MB |
    | stopped at | `XTOL` after 265 calls | its own convergence test |
    | its own residual | weighted response rms 118.9 → 80.2 | not comparable: a different objective |

=== "Normal tunes, QDE14+QDE3 error"

    | | Method 1 | Method 2 |
    |---|---|---|
    | free knobs | 32 cell-grouped $\Delta k_1 L$ over 48 magnets | 32 cell-grouped $\Delta k_1 L$ over 48 magnets |
    | what it fits | the measured response matrix | 48 delta closed orbits |
    | processes | 1 | 48 |
    | wall clock | 13.9 s | 4.7 s |
    | CPU, whole tree | 24.8 s | 22.4 s |
    | peak RSS | 255 MB | 265 MB |
    | stopped at | `XTOL` after 369 calls | its own convergence test |
    | its own residual | weighted response rms 114.7 → 77.3 | not comparable: a different objective |

=== "Normal tunes, sextupoles on"

    | | Method 1 | Method 2 |
    |---|---|---|
    | free knobs | 32 cell-grouped $\Delta k_1 L$ over 48 magnets | 32 cell-grouped $\Delta k_1 L$ over 48 magnets |
    | what it fits | the measured response matrix | 48 delta closed orbits |
    | processes | 1 | 48 |
    | wall clock | 9.7 s | 4.9 s |
    | CPU, whole tree | 20.6 s | 24.6 s |
    | peak RSS | 257 MB | 269 MB |
    | stopped at | `XTOL` after 232 calls | its own convergence test |
    | its own residual | weighted response rms 118.3 → 79.9 | not comparable: a different objective |

## What each answer and each run cost

=== "Normal tunes, 29th"

    The two fits correlate at **+0.9998** over 48 magnets (32 distinct knobs each). Their gradients differ by 0.07 % of nominal $k_1L$ rms, 0.14 % at the worst magnet, against fitted magnitudes of 2.36 % and 2.32 % rms.

    Method 2 finishes **2.2x** faster in wall clock and **0.9x** in CPU, while holding 48 MAD-NG workers to Method 1's one.

=== "Normal tunes, QDE14 error"

    The two fits correlate at **+0.9999** over 48 magnets (32 distinct knobs each). Their gradients differ by 0.05 % of nominal $k_1L$ rms, 0.10 % at the worst magnet, against fitted magnitudes of 3.07 % and 3.03 % rms.

    Method 2 finishes **0.5x** faster in wall clock and **0.9x** in CPU, while holding 48 MAD-NG workers to Method 1's one.

=== "Normal tunes, QDE14+QDE3 error"

    The two fits correlate at **+0.9998** over 48 magnets (32 distinct knobs each). Their gradients differ by 0.08 % of nominal $k_1L$ rms, 0.20 % at the worst magnet, against fitted magnitudes of 2.64 % and 2.57 % rms.

    Method 2 finishes **2.9x** faster in wall clock and **1.1x** in CPU, while holding 48 MAD-NG workers to Method 1's one.

=== "Normal tunes, sextupoles on"

    The two fits correlate at **+1.0000** over 48 magnets (32 distinct knobs each). Their gradients differ by 0.03 % of nominal $k_1L$ rms, 0.06 % at the worst magnet, against fitted magnitudes of 3.05 % and 3.04 % rms.

    Method 2 finishes **2.0x** faster in wall clock and **0.8x** in CPU, while holding 48 MAD-NG workers to Method 1's one.

## Speed and agreement

<figure markdown>
![Wall clock and whole-tree CPU for each method, every benchmarked campaign on this page.](../../assets/figures/scenarios/normal/benchmark_speed.png)
<figcaption>Wall clock and whole-tree CPU for each method, every benchmarked campaign on this page.</figcaption>
</figure>
<figure markdown>
![Each magnet's fitted gradient, Method 1 against Method 2.](../../assets/figures/scenarios/normal/benchmark_agreement.png)
<figcaption>Each magnet's fitted gradient, Method 1 against Method 2.</figcaption>
</figure>

Wall clock is one run on one machine, not a mean over repeats, and the CPU column is the whole process tree as the operating system reports it — for Method 2 that is one worker per corrector setting, started and terminated by the fitter.

Method 1 stops on **XTOL** (`--var-rtol 3e-3`: no knob moves by more than 0.3 % of itself), not on `FMIN`/`FTOL`, since measured BPM bars keep all 384 response cells infeasible by thousands of sigma. Here: normal tunes, 29th `XTOL` at 298 calls, normal tunes, qde14 error `XTOL` at 265 calls, normal tunes, qde14+qde3 error `XTOL` at 369 calls, normal tunes, sextupoles on `XTOL` at 232 calls. Tightening to 1e-8 costs 4000–6000 extra calls and changes no gradient by more than 2.2e-4 % of nominal $k_1L$, against fitted magnitudes of about 3 %.

---

## Rerunning this page

```bash
uv run python -m scripts.benchmark_methods --campaign normal_second normal_qde14_err normal_qde14_qde3_err normal_sexts_on
uv run python scripts/analyse_cross_campaign.py --direction normal
uv run python scripts/plot_cross_campaign.py --direction normal
uv run python reports/loco_option_matrix/make_pages.py
```
