# Method 1 against Method 2

PSB ring 3 · both methods, same 32 cell-grouped knobs, same delta orbits. Wall clock is one run on one machine, not a mean over repeats; the CPU column is the whole process tree, which for Method 2 is one worker per corrector setting.

## The two runs

=== "Inverted tunes, 28th"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 13.2 | 24.2 | 254 | 1 |
    | Method 2 | 5.6 | 25.8 | 265 | 48 |

=== "Inverted tunes, QDE14 error"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 18.1 | 28.8 | 257 | 1 |
    | Method 2 | 6.0 | 26.1 | 269 | 48 |

=== "Inverted tunes, QDE14+QDE3 error"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 13.7 | 24.6 | 258 | 1 |
    | Method 2 | 6.2 | 26.5 | 270 | 48 |

=== "Inverted tunes, sextupoles on"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 16.5 | 27.5 | 254 | 1 |
    | Method 2 | 5.6 | 25.9 | 266 | 48 |

## Agreement

| configuration | magnets | correlation | rms difference [%] | max difference [%] |
|---|---|---|---|---|
| Inverted tunes, 28th | 48 | +0.9999 | 0.03 | 0.09 |
| Inverted tunes, QDE14 error | 48 | +0.9999 | 0.06 | 0.11 |
| Inverted tunes, QDE14+QDE3 error | 48 | +0.9999 | 0.04 | 0.07 |
| Inverted tunes, sextupoles on | 48 | +0.9999 | 0.03 | 0.07 |

## Speed and agreement

<figure markdown>
![wall clock and CPU per method](../../assets/figures/scenarios/inverted/benchmark_speed.png)
<figcaption>Wall clock and whole-tree CPU for each method, every benchmarked configuration.</figcaption>
</figure>

<figure markdown>
![Method 1 against Method 2 per magnet](../../assets/figures/scenarios/inverted/benchmark_agreement.png)
<figcaption>Each magnet's fitted gradient, Method 1 against Method 2.</figcaption>
</figure>
