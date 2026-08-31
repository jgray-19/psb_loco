# Method 1 against Method 2

PSB ring 3 · both methods, same 32 cell-grouped knobs, same delta orbits. Wall clock is one run on one machine, not a mean over repeats; the CPU column is the whole process tree, which for Method 2 is one worker per corrector setting.

## The two runs

=== "Normal tunes, 29th"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 11.7 | 22.6 | 260 | 1 |
    | Method 2 | 5.3 | 24.6 | 267 | 48 |

=== "Normal tunes, QDE14 error"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 10.7 | 21.7 | 254 | 1 |
    | Method 2 | 20.1 | 22.8 | 268 | 48 |

=== "Normal tunes, QDE14+QDE3 error"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 13.9 | 24.8 | 255 | 1 |
    | Method 2 | 4.7 | 22.4 | 265 | 48 |

=== "Normal tunes, sextupoles on"

    | method | wall [s] | CPU [s] | peak RSS [MB] | processes |
    |---|---|---|---|---|
    | Method 1 | 9.7 | 20.6 | 257 | 1 |
    | Method 2 | 4.9 | 24.6 | 269 | 48 |

## Agreement

| configuration | magnets | correlation | rms difference [%] | max difference [%] |
|---|---|---|---|---|
| Normal tunes, 29th | 48 | +0.9998 | 0.07 | 0.14 |
| Normal tunes, QDE14 error | 48 | +0.9999 | 0.05 | 0.10 |
| Normal tunes, QDE14+QDE3 error | 48 | +0.9998 | 0.08 | 0.20 |
| Normal tunes, sextupoles on | 48 | +1.0000 | 0.03 | 0.06 |

## Speed and agreement

<figure markdown>
![wall clock and CPU per method](../../assets/figures/scenarios/normal/benchmark_speed.png)
<figcaption>Wall clock and whole-tree CPU for each method, every benchmarked configuration.</figcaption>
</figure>

<figure markdown>
![Method 1 against Method 2 per magnet](../../assets/figures/scenarios/normal/benchmark_agreement.png)
<figcaption>Each magnet's fitted gradient, Method 1 against Method 2.</figcaption>
</figure>
