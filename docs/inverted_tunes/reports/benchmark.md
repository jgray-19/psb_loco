# Method 1 against Method 2

PSB ring 3 · both methods, same 32 cell-grouped knobs, same delta orbits. Wall clock is one run on one machine, not a mean over repeats; the CPU column is the whole process tree, which for Method 2 is one worker per corrector setting.

## The two runs

=== "Inverted tunes, 28th"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 16.7 | 25.0 | 259 | 1 |
    | Method 2 | 6.2 | 25.1 | 270 | 48 |

=== "Inverted tunes, QDE14 error"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 17.5 | 28.4 | 263 | 1 |
    | Method 2 | 5.8 | 26.3 | 267 | 48 |

=== "Inverted tunes, QDE14+QDE3 error"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 16.7 | 27.7 | 258 | 1 |
    | Method 2 | 5.4 | 26.1 | 269 | 48 |

=== "Inverted tunes, sextupoles on"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 17.1 | 28.0 | 259 | 1 |
    | Method 2 | 5.7 | 26.5 | 270 | 48 |

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
