# Handover — psb_loco

!!! note "Not published"
    A working log, kept in the repository rather than on the site. The site
    presents results; this is the record of how they were arrived at, and
    parts of it describe a layout the repository has since moved past. The
    settled conventions are on the site at `docs/reference/conventions.md`.

Written 2026-08-21, at the end of the session that built this and ran it on the
first real scan; extended the same day by a Method-2-only session that lifted the
worker-count ceiling and then ran the whole scan through it (§9). `README.md`
describes what the code *is*; this describes what you need to know to pick it up
— what is settled, what is not, what cost time, and what I would do next.

---

## 1. Where things stand

Both methods work, are tested against an independently-generated truth, and have
been run on the real 2026-08-21 ring-3 scan. They agree. The best fit takes the
response error from 15.5 % to **8.8 %** (Method 2, 12 correctors, all four
corrector steps, one momentum — §9.2).

The remaining 9 % is **not** noise, and this is the single most important thing
to carry forward: there is a systematic in the data that quadrupole gradients
cannot represent (§4.1). Until that is modelled, driving the residual lower is
fitting it into the gradients, not measuring the machine. The second session
tested that claim as hard as the scan allows — every corrector, every step, one
to five momenta, 292 settings at the widest — and it holds: **nothing in the
scan buys anything past 8.8 %** (§9.3). The data is exhausted; the model is not.

**Version control.** The repo was working-tree only until 2026-08-31, when it
was initialised and the tree committed as it stood (`c76c574`). Anything this
document describes from before that date has no history behind it.

---

## 2. Running it

```bash
source ../accpy/bin/activate           # the interpreter with pymadng + the sibling packages
# Results now live under results/matrix_<campaign>[_multi]/<case-slug>/; the
# --output paths below are the layout this section was written against and no
# longer exist. scripts/refresh_docs.sh <direction> runs the whole pipeline.
python -m method1_madng_da.run_method1 --campaign p23_p13_final \
    --sequence-file "$SEQ"
python -m method2_delta_orbit.run_method2 --campaign p23_p13_final \
    --sequence-file "$SEQ"
python compare_fits.py                 # every results/*/knobs.csv against the measurement
python compare_fits.py --bounds 0.05 0.10   # count knobs past other thresholds
```

The best single run, and the widest one, both from §9:

```bash
python -m method2_delta_orbit.run_method2 --rf-offset 0 \
    --sequence-file "$SEQ" --output results/method2_1pt_allsteps
python -m method2_delta_orbit.run_method2 --rf-offsets -2 -1 0 1 2 --batch-momenta \
    --sequence-file "$SEQ" --output results/method2_lumped_5pt_allsteps
```

`--offsets` now defaults to every corrector step in the scan, and `--batch-momenta`
is what makes the second command 49 processes rather than 244 (§9.1). If you do
pass `--offsets`, note that argparse only accepts a negative step written in
decimal — `-0.0001`, not `-1e-4`, which it reads as an option name.

`--sequence-file` is currently **required**. `build_model()`'s default
(`psb_md/results/hio_psb_r3/current/psb_r3_free_qx0p165_qy0p2275`) does not
exist on disk. What all the numbers below were produced with:

```
/afs/cern.ch/work/j/jmgray/private/psb_md/models/reference/
  model_qx0.234255_qy0.127202_driven_qx0.230300_qy0.131200_dpp-3.850735e-06_state_tunematch/psb3_saved.seq
```

Tune knobs and corrector strengths resolve independently of that path, so
substituting a current model should be safe — but re-run `compare_fits.py`
against the old one first, because every number in `README.md` is tied to this
lattice.

`compare_fits.py` auto-discovers `results/*/knobs.csv` and labels each by its
directory, so new runs appear without editing it. It stands the model up exactly
as the drivers do — see §5.1 for why that matters more than it sounds.

### Data access

The scan lives on a read-only mount:
`/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_21_Multiturn/psb_loco_scan/`
(892 SDDS files). **Write nothing there.** `cached_scan()` reads it once per campaign into
`data/<campaign>_scan_points.parquet` + `data/<campaign>_scan_orbits.parquet`; that took the cold read
from ~10 minutes to 0.66 s. If the mount is absent, the cached parquet is enough
for everything except regenerating it, and the mount-gated tests skip themselves.

---

## 3. Conventions that are settled — do not re-derive these

Each cost real time to establish. They are pinned by tests; if a test in this
list fails, believe the test.

### 3.1 LSA `/K` is sign-inverted for DHZ, not for DVT

`LSA_K_SIGN = {"x": -1.0, "y": 1.0}` in `loco_common/naming.py`.

A horizontal corrector's LSA `/K` step produces the *opposite* kick to MAD's
`hkick` of the same sign. All six DHZ correlate at −0.998 against the model, all
six DVT at +0.999.

The subtle part, worth understanding before you touch it: **the response matrix
alone cannot establish this.** "LSA `/K` is inverted" and "the BPM X reading is
inverted" predict *identical* response matrices — both flip the same product. The
dispersion orbit is what separates them, because no corrector touches it. The
measured horizontal dispersion tracks the model's with the *correct* sign, so the
BPM is right and the corrector convention is what is inverted.

If you ever suspect this again, that is the experiment — not another response fit.

### 3.2 Method 1 is a first-order response matrix

Method 1 now uses DA only for the corrector derivative: one first-order
parametric twiss builds the full `(2*N_BPM) x N_corrector` response matrix.
Every matrix cell is one independently weighted `MAD.match` equality. MAD.match
finite-differences those equalities with respect to the same 32 native
cell-grouped `dk1l` knobs as grouped Method 2. The former second-order
corrector×quadrupole cross-term path, 48 absolute-`k1` output, conversion step,
and `k1_limit` bounds were removed rather than retained as compatibility modes.

### 3.3 MAD-NG twiss `dx` is `dx/dpt`, not `dx/dδ`

`δ = pt/β₀ − pt²/(2β₀²γ₀²)`, and β₀ ≈ 0.5198 at PSB 160 MeV kinetic. I lost time
to this — it made the measured dispersion look like it disagreed with
`DPP_PER_MM` by a factor 2.6 when the real gap is 34 % (§4.3).

### 3.4 One global reference orbit

Every acquisition — every corrector step, every RF setting — has the *same* orbit
subtracted: untrimmed, nominal RF. Not each RF setting referred to its own zero.

The consequence that is easy to get wrong: the **model** side must then take its
reference at `pt = 0`, not at the worker's own momentum
(`ClosedOrbitMeasurement.reference_pt`). Referring each RF setting to itself would
subtract that momentum's dispersion away, and dispersion is exactly the
quadrupole-sensitive signal the multi-momentum mode exists to fit.

The multi-momentum driver retains the original orbit-projected calibration by
default (`--momentum-source orbit`). The independent RF/XImeter calibration is
available as `--momentum-source chroma`. The former depends on the starting-model
dispersion; the latter depends on the XImeter `Dp/p` bands. Each fit records both
calibrations and the selected per-offset `pt` values in `summary.json`; their
controlled method-6 comparison, rather than the default, decides their interpretation.
That comparison is recorded in
[`../studies/momentum-calibration.md`](../studies/momentum-calibration.md): the
two sources differ by 25--30%, materially move the fitted lattice, and cannot be
made equivalent by a `dp/p`/`pt` beta factor or by changing the subtraction origin.

### 3.5 One dispersion setting per momentum, not twelve

Each non-zero RF setting was acquired untrimmed **once per corrector** — twelve
recordings of one machine state. `build_multi_pt_settings` averages them into a
single `(dispersion)` setting and drops the twelve; `--keep-zero-step-duplicates`
restores the old behaviour for comparison only.

This was the *default* until the second session, and it was silently weighting
one orbit twelvefold in every multi-momentum fit that did not pass `--offsets`.
It cost 0.6 points at 3 momenta (12.1 % → 11.5 %) and 0.4 at 5 (11.4 % → 11.0 %).
Pinned by `tests/test_delta_worker.py`.

The same change makes `--no-dispersion-workers` mean what it says: it used to
drop the averaged setting while leaving twelve copies of the same orbit in, so it
never removed the constraint it exists to isolate.

### 3.6 xsuite corrector convention

`knl[0] = -hkick`, `ksl[0] = +vkick`. Pinned in `tests/test_naming.py`.

---

## 4. Open problems, in the order I would attack them

### 4.1 Per-corrector gain is unmodelled — this is the ceiling

The measured/model response ratio, fitted per corrector across all BPMs:

| | range |
|---|---|
| six DHZ | 0.71 – 0.93 |
| six DVT | 0.95 – 1.03 |

It is **uniform across BPMs for a given corrector**. That is the signature of a
calibration error, and no quadrupole gradient can produce it: a gradient error
changes the *shape* of a corrector's response, not its overall scale. The fit is
currently absorbing a scale error into shape parameters, which is why the
gradients come back larger than physical (6.2 % rms, 17 of 48 at the 5 % bound).

A conventional LOCO frees corrector and BPM gains alongside the quadrupoles. This
one does not, by design — it was scoped to quadrupole `k1`. Adding 12 corrector
gain knobs would be cheap in the DA map (they are already parameters) and would
very likely take the residual down and the gradients back toward physical.

**This changes what is being fitted, so it is a decision, not a fix.** It was
raised with the user and not taken up; do not assume it is wanted.

### 4.2 The model's vertical dispersion is badly wrong

The machine carries **7.7e−5 m rms of vertical dispersion where the model has
2.0e−5 m**. Horizontally the residual is 79–84 % of the measured amplitude;
vertically it is **108–110 %** — i.e. the model's vertical dispersion is not
merely wrong in size, it is essentially uncorrelated with the machine's.

Under the global reference (§3.4) this enters every off-momentum target as a
first-order term worth 40–90 σ. It is what caps the multi-momentum mode: the mode
works and is well-conditioned, but has nothing to gain while the dispersion it
would exploit is this wrong.

Ruled out already, so do not re-check: the momentum estimates (`tmom_recon` and
an independent dispersion projection agree to the displayed digits) and the
dispersion workers (dropping them moves 42.0 % → 41.1 %).

### 4.3 A 34 % gap in `DPP_PER_MM`

Measured 4.5e−4 per mm of RF steering against `DPP_PER_MM = 6e−4`. Unexplained.
Small enough not to block anything, large enough to be real. Possibly related to
§4.2. Note §3.3 before measuring this again.

### 4.4 Historical Method 1 result

`MAD.match` finds its best point at call 2 (`fbst[2] = 1.40859e+02`) and 398
further calls never improve on it. Reproducible between the 50-call and 400-call
runs, so it is structural, not a budget problem. Method 1 lands at 12.4 % where
Method 2 reaches 9.1 %; this is probably why. Worth a look at the trust region
That result used the removed 48-absolute-`k1`, bounded, second-order formulation;
it does not describe the current matrix-cell/32-knob implementation.

### 4.5 Worker count is capped near 250 — worked around, not fixed

`pymadng` waits on each MAD process with `select()` (`madp_pymad.py:124`), and
`select()` rejects any descriptor numbered ≥ `FD_SETSIZE` (1024). 170 workers
start; 292 dies at worker 261 with `ValueError: filedescriptor out of range in
select()`. **`ulimit -n` does not help** — the limit is on the descriptor's
*number*, not the count.

`--batch-momenta` (§9.1) removes the momentum factor from the process count, which
was enough: the 292-setting configuration that used to die now runs in **61**
processes. The ceiling itself is untouched and still upstream — what changed is
that the study no longer needs to approach it. If you widen the fit in a
direction lumping does not cover (more correctors, more steps), the arithmetic to
keep under ~250 is now `len(offsets) × len(correctors) + 1`.

---

## 5. Traps that cost me time

### 5.1 Compare fits on the lattice the drivers actually use

My first comparison harness used `open_interface`, which applies **no tune knobs
and no corrector knobs**, while both drivers use `build_model` +
`GenericMadInterface` *with* them. Every number it produced was wrong — it showed
Method 2 apparently making things 69.6 % worse when it is in fact the best fit at
9.1 %. `compare_fits.py` now mirrors the drivers exactly. If you write another
analysis script, mirror them too.

### 5.2 Historical per-magnet bound

Without `--k1-limit` (default 0.05) the first Newton step moved gradients ~40 %,
which takes the lattice through a stop band:
`mad_tpsa_fun.c:191: invalid domain invsqrt(-2.4740E+00)` then `SIGSEGV`.

The bound is not a convergence aid. On measured data the starting residual is
thousands of sigma — the BPM errors are the standard error of a many-turn mean,
so a few-percent model error is enormous in those units. A LOCO answer larger
than a few percent is a divergence, not a gradient error, so the bound turns a
crash into a visibly-at-the-limit result.

The old per-magnet Method 1 used `k1_limit`; the current 32-knob implementation
has no bounds. `compare_fits.py` reports thresholds only as diagnostics.
**Read those counts as a warning sign, not a detail** — at 10 % the
single-momentum fits still put 6–8 of 48 knobs beyond any gradient error a real
PSB quadrupole has. The user's decision, on being shown this, was to leave
Method 2 unconstrained.

### 5.3 A wrong `pt` sign makes the lattice unstable

Not a bad answer — MAD's normal form fails outright
(`madl_gphys.mad:453: attempt to perform arithmetic on local 'kk' (a boolean
value)`). `tests/test_pt_mode.py` uses a 20 %-low `pt` rather than a flipped one
for exactly this reason.

### 5.4 Fixture conventions must match the machine's

When the LSA sign (§3.1) landed, three `test_recovery` tests and one
`test_da_response` broke because the fixtures generated responses in MAD's kick
convention while the driver reads its input as LSA `/K`. The fix was to convert
in `fake_response`, `_target_matrix` and `test_parametric_response_matches_xsuite`
— i.e. **fixtures should speak the machine's convention**, and conversion to
MAD's belongs at the same boundary the driver puts it.

---

## 6. Ground rules from the user

These were explicit and should be treated as still in force unless re-negotiated:

- **No upstream edits.** `psb_md`, `aba_optimiser`, `tmom_recon`, `xtrack_tools`
  and `pymadng` are imported as installed packages. This is why §4.5 is a
  documented limit rather than a patch.
- **The acquisition mount is read-only.** All generated output stays in `psb_loco`.
- **`PRIOR_STRENGTH = 1e-4` is not a tuning parameter.** `psb_md`'s docstring is
  emphatic that the prior's shape *and* scale are what pick the answer out of a
  large null space. Do not retune it to improve a residual.
- **No monkeypatching in tests** without explicit approval.
- Prefer behavioural/physics validation over implementation-pinning tests.
- Remove focused debug scripts once the diagnosis is done.

---

## 7. What the numbers mean

Read `README.md`'s results table with three cautions.

**Neither method's own residual is a quality score.** The acceptance evidence is
that two formulations sharing no solver and no objective land together: +0.97
correlation on the response change, +0.92 on the gradients. That is what to
protect when you change something.

**The multi-momentum rows are scored against a handicap.** The single-momentum
fit is measured on exactly the data it fitted; the multi-momentum fit is measured
on one fifth of its own. 8.8 % vs 11.0 % is closer to a wash than it reads, and
the multi-momentum fit is the better-conditioned of the two (4.2 % rms gradient
change, 10/48 past 5 %, against 6.6 % and 19/48).

**Two rows are inflated by the duplicate weighting (§3.5) and are marked † in the
table.** Their deduplicated counterparts are the ones to quote.

**Momentum saturates at two, and the first one costs.** The second session ran
the full curve (§9.3): 8.8, 10.8, 11.5, 11.2, 11.0 % for one through five momenta
with every corrector step. Flat from two onward, and the fits are near-identical
to each other (+0.998 on the gradients, 4 vs 5). The step between one and two is
real and goes the *wrong* way — see §9.4, which is the finding I would most want
you to read before deciding anything about the multi-momentum mode.

**Four correctors is not enough for 48 knobs.** The 4-corrector fit is worse than
the starting model. Its catastrophic multi-momentum number (42 %) was
under-constraint, not a problem with the mode — at 12 correctors the same
comparison is 8.8 % → 11.0 %. I initially misread that as evidence against the
mode; it was evidence against fitting 48 knobs from 4 correctors.

---

## 8. If you do one thing

Add per-corrector gain knobs (§4.1) — *after* checking with the user that
widening the fit is wanted. It is the only open item with a clear mechanism, a
clear signature in the data, and a cheap implementation. Everything else either
depends on fixing the model (§4.2, §4.3) or is upstream (§4.5).

The second session strengthens this rather than changing it. Every configuration
the scan supports has now been fitted, and the answer does not move: more
correctors' steps, more momenta, more acquisitions, all land between 8.8 and
11.5 % with the same gradients. There is no data left to add. The next real
number comes from changing what is fitted, not what it is fitted to.

---

## 9. Second session: lumped momenta, and the whole scan fitted

!!! warning "Evidence directories are gone"
    The `results/method2_1pt_allsteps` and `method2_lumped_*pt_allsteps`
    directories this section's tables were measured from no longer exist.
    Fits now live under `results/matrix_<campaign>[_multi]/<case-slug>/`, so
    the numbers below cannot be reproduced by the commands printed beside
    them without re-running the sweep under the current layout.

Method 2 only. The brief was to stop one MAD-NG process per (corrector, step,
momentum) from running out of file descriptors (§4.5), then use the headroom to
fit every scenario the scan holds rather than the subsets every earlier study was
forced into.

### 9.1 `--batch-momenta`: one process per corrector trim

`aba_optimiser.ClosedOrbitWorker` fits every momentum of one corrector trim
inside a single MAD-NG process. `run_method2.closed_orbit_series()` groups the
settings by what the worker actually sets on the machine — `(corrector, knob,
dk, nominal, absolute_planes)` — so only the momentum and its target differ
within a group.

What is shared and what is not, because this is the part worth understanding
before changing it:

- **Not shared:** each momentum gets its own `cofind` + parametric twiss at its
  own `pt`, so its Jacobian is evaluated at its own closed orbit.
- **Shared:** the reference twiss — correctors nominal, `pt = reference_pt = 0`.
  Shared not to save work but because §3.4 says every target has that same orbit
  subtracted. In the unlumped layout each worker was recomputing an *identical*
  pt = 0 reference; lumping computes it once. Hence `2·n_pt → 1 + n_pt` twisses.
- **Summing is exact, not an approximation.** The objective is a sum of
  per-(trim, momentum) chi-squares, so its gradient is the sum of the per-slice
  gradients, each already `2 Jᵀ W r` with that slice's own residual and weights.
  The one thing that would break it is a per-worker or per-slice normalisation,
  `ClosedOrbitSeriesData.iter_observables()` exposes all measurements before the
  shared global `weight_scale` / `total_points` are computed.

**Evidence it is the same fit, on real data:** the 5-momentum, 1-step
configuration run as 64 processes and as 13 agrees to **5e-12 relative** on all
48 knobs and 2e-12 on the uncertainties. A synthetic version of the same check is
in `tests/test_delta_worker.py` as a slow test. If you change the worker, that
test is the one that catches you.

The 292-setting configuration §4.5 recorded as dying at worker 261 now runs in
**61** processes.

### 9.2 The best fit is one momentum with every corrector step: 8.8 %

`results/method2_1pt_allsteps` — 12 correctors, all four LSA steps (±5e-5,
±1e-4), RF offset 0, 48 settings.

| | response error | weighted | k1 rms | past 5 % | past 10 % |
|---|---|---|---|---|---|
| previous best (1 step) | 9.14 % | 103 σ | 6.15 % | 17/48 | 6/48 |
| **all four steps** | **8.80 %** | **98 σ** | 6.64 % | 19/48 | 8/48 |

It also agrees with Method 1 at **+0.987** on the response change, the highest
cross-method agreement recorded — which matters more than the 0.34 points, per
§7. The gradients are *less* physical, not more (8 of 48 past 10 %), which is
§4.1 arriving in the only parameters the fit has.

### 9.3 The full momentum curve, every corrector setting

All 12 correctors, all four steps, lumped, 1 → 5 momenta. RF offsets added in the
order 0, +2, −2, +1, −1.

| momenta | settings | processes | response error | weighted | k1 rms | past 5 % | past 10 % |
|---|---|---|---|---|---|---|---|
| 1 | 48 | 48 | **8.80 %** | 98 σ | 6.64 % | 19/48 | 8/48 |
| 2 | 97 | 49 | 10.82 % | 126 σ | 4.54 % | 10/48 | 3/48 |
| 3 | 146 | 49 | 11.46 % | 133 σ | 4.38 % | 10/48 | 2/48 |
| 4 | 195 | 49 | 11.18 % | 130 σ | 4.28 % | 10/48 | 2/48 |
| 5 | 244 | 49 | 10.96 % | 127 σ | 4.23 % | 10/48 | 2/48 |
| 5, duplicates kept | 292 | 61 | 11.36 % | 132 σ | 4.31 % | 10/48 | 2/48 |

Flat from two onward: 2 vs 5 correlate at +0.962 on the gradients, 3 vs 5 at
+0.990, 4 vs 5 at **+0.998**. These are not different answers.

### 9.4 The trade the curve exposes — read this one

**The fit that best reproduces the measured response is the one asking for the
least physical machine.** One momentum gives 8.8 % with 8 of 48 knobs past 10 %;
every multi-momentum fit gives 11 % with 2 or 3. Momenta buy conditioning and
cost response error, monotonically, and both halves trace to the same cause:

- they regularise, because the off-momentum Jacobians are genuinely independent
  and lift the null space §7 warns about;
- they cost, because the model's vertical dispersion is wrong by a factor 4
  (§4.2) and under the global reference that error enters every off-momentum
  target at 40–90 σ, which no quadrupole can absorb.

So neither number is a quality score while §4.2 stands, and "which configuration
is best" is not answerable from these residuals. What *is* now settled is that
the answer does not depend on how much of the scan you use.

### 9.5 The duplicate-weighting default, and an error bar that is wrong

See §3.5 for the change. The detail that outlives it: the averaging is
`sum(frames) / len(frames)`, which averages the **error bars** along with the
orbits, giving `err_mean = mean(err)` where the average of twelve deserves
`err/√12`. The dispersion setting therefore enters with an error bar ~3.5× too
large — under-weighted roughly twelvefold in the inverse-variance sum.

Left as-is deliberately. Given §4.2 it is accidentally protective, and correcting
it would pull the fit *harder* toward dispersion the model does not have. **If
you fix §4.2, fix this first**, or the dispersion weight jumps by an order of
magnitude underneath you and you will read the change as physics.

### 9.6 What changed in the code

- `aba_optimiser.training_closed_twiss.ClosedOrbitFitter` — public fit lifecycle,
  mixed-unit priors, global normalisation and uncertainty calculation.
- `aba_optimiser.workers.ClosedOrbitWorker` — per-measurement momentum and target,
  global-reference subtraction and exact-state caching.
- `method2_delta_orbit/run_method2.py` — `--batch-momenta`,
  `--keep-zero-step-duplicates`, `drop_zero_step_duplicates()`, and the change of
  default in §3.5.
- `compare_fits.py` — `--bounds`, and `at 5% bound` → `past N%` (§5.2).
- `tests/test_delta_worker.py` — 13 new tests, one of them the slow
  lumped-equals-unlumped fit.

The reusable implementation now lives upstream in `aba_optimiser`; Method 2
only prepares PSB measurements and selects accelerator options. The solve,
prior, normalisation and uncertainty code is no longer duplicated or subclassed.

### 9.7 Results directories from this session

`method2_1pt_allsteps` (§9.2) · `method2_lumped_{2,3,4,5}pt_allsteps` (§9.3) ·
`method2_lumped_5pt_everything` (292 settings, duplicates kept) ·
`method2_lumped_5pt_1step` (the 13-process twin of `method2_5pt_12corr_1step`,
§9.1).

## 10. How much prior does the full 5-momentum fit actually need?

!!! warning "Evidence directories are gone"
    The `results/method2_1pt_allsteps` and `method2_lumped_*pt_allsteps`
    directories this section's tables were measured from no longer exist.
    Fits now live under `results/matrix_<campaign>[_multi]/<case-slug>/`, so
    the numbers below cannot be reproduced by the commands printed beside
    them without re-running the sweep under the current layout.

Asked of the best-conditioned configuration: all five RF offsets, all corrector
steps, duplicates averaged, momenta lumped — 244 settings in 49 processes
(`--rf-offsets -2 -1 0 1 2 --batch-momenta`). Seven fits, identical in every
respect but `--prior-strength`, scored against the measured response matrix.
Results live under `results/prior_scan/p{0,1em6,…,1em1}/`, which is nested one
level deeper than `results/*/knobs.csv` on purpose so `compare_fits.py`'s
default discovery does not sweep them into every comparison.

| strength | alpha | response err | resid (σ) | k1 rms | max | past 5 % | past 10 % | corr vs 1e-4 |
|---|---|---|---|---|---|---|---|---|
| 0      | —       | 11.00 % | 127.5 | 5.08 % | 14.42 % | 14 | 4 | +0.9988 |
| 1e-6   | 9.2e+04 | 11.00 % | 127.5 | 5.07 % | 14.40 % | 14 | 4 | +0.9988 |
| 1e-5   | 9.2e+05 | 11.00 % | 127.4 | 4.97 % | 14.23 % | 14 | 3 | +0.9991 |
| **1e-4** | 9.3e+06 | **10.96 %** | 127.1 | 4.23 % | 12.74 % | 10 | 2 | — |
| 1e-3   | 9.5e+07 | 10.97 % | 127.1 | 2.26 % |  6.69 % |  3 | 0 | +0.9920 |
| 1e-2   | 9.8e+08 | 11.07 % | 126.8 | 1.02 % |  2.30 % |  0 | 0 | +0.9657 |
| 1e-1   | 1.1e+10 | 11.64 % | 131.6 | 0.44 % |  1.09 % |  0 | 0 | +0.9150 |

`alpha = strength × median(diag H)`, with `median diag H ≈ 9.2e+10` in
`dk1l` units — stable to a few percent across the scan, so alpha tracks the
strength linearly and the knob scale is the only thing being set.

**What it says.**

- The data alone (strength 0) is not ill-posed here. It converges in five LM
  iterations to 11.00 % with a 5.08 % k1 rms. The unprior'd answer is not
  garbage, which is *not* true of the small-scenario configurations — this is
  the payoff of 244 settings.
- 1e-6 and 1e-5 are indistinguishable from no prior at all (`|dA−dB|/|dA|` of
  0.001 and 0.007 against strength 0). They are decorative.
- **1e-4 is the knee.** It is simultaneously the best response error in the
  scan (10.96 %), the best residual tie (127.1 σ), and the point where the k1
  rms drops from 5.0 % to 4.2 % and the number of knobs past 10 % halves from 4
  to 2. Going from 0 to 1e-4 removes a fifth of the knob excursion and *improves*
  the fit — that fifth was noise.
- 1e-3 is the first strength that costs something. The response error is flat
  (10.97 %) but the k1 rms halves again to 2.26 % and the correlation with 1e-4
  drops to +0.9920 with a 13 % vector difference: it is now moving the answer,
  not just trimming it, while buying no accuracy.
- 1e-2 and 1e-1 are over-regularised. The response error climbs back
  (11.07 %, 11.64 %) and the knobs collapse toward nominal (0.44 % rms at 1e-1,
  a fortieth of the start model's own 15.46 % error). At 1e-1 the fit is barely
  distinguishable from doing nothing.
- The 1-sigma bars shrink with alpha as they must (median 7.34e-5 at strength 0,
  6.81e-5 at 1e-4, 7.7e-6 at 1e-1), so the reported significance is a statement
  about the posterior and cannot be used to choose the strength. Note the last
  row: heavy shrinkage makes the knobs look *more* significant, not less
  (med |v|/σ = 197 vs 155 at 1e-4). Significance is not evidence of a good fit.

**Conclusion: leave `PRIOR_STRENGTH = 1e-4` alone.** The scan lands on it from
below and above, which is the outcome §6 wanted protected and not a licence to
tune it per configuration. The upstream docstring's recipe — "start small and
increase until the recovered knobs stop chasing noise" — puts the stopping point
between 1e-4 and 1e-3, and 1e-4 is the one that also minimises the held-out
response error.

Caveat worth carrying: this knee was measured at 244 settings. A scan with
fewer scenarios is more ill-posed and its knee would sit higher; the flat
0 → 1e-5 shoulder above is a property of *this* data volume, not of the method.
`--prior-strength` exists to re-measure that, not to improve a residual.

---

## 11. Third session: the second machine configuration, and the measured optics

The MD ran the corrector scan **twice**. Everything in sections 1-10 is the first
run; the second was an hour later at a different quadrupole powering, with the
correctors untouched. The repository knew about only one of them, and nothing in
it said which.

### 11.1 A campaign is now an object

!!! warning "Three campaigns, not nine"
    Written when `CAMPAIGNS` held `NORMAL`, `INVERTED` and `INVERTED_DOUBLE`.
    It now holds nine: four per working point plus the large-step scan. The
    two originals are retired and live in `loco_common/retired_campaigns.py`.

`loco_common/campaign.py` holds what differs between the two machine states:
acquisitions, scan log, corrector step, quadrupole circuits, cache prefix,
results root, and the measured optics. Three instances -- `NORMAL`, `INVERTED`,
`INVERTED_DOUBLE` -- and `NORMAL` is the default everywhere, so every command in
sections 2 and 9 still means what it meant.

| | normal | inverted | inverted, large step |
|---|---|---|---|
| acquisitions | `CO_measurements` (446) | `CO_measurements_inverted_tunes` (585) | `..._double` (266) |
| scan log | `scan_20260821T091044.jsonl` | `scan_20260821T115006.jsonl` | `scan_20260821T150756.jsonl` |
| step, LSA `/K` | 0, ±5e-5, ±1e-4 | the same | 0, ±1.5e-4 |
| `kbrqf` / `kbrqd` | +0.7289003 / −0.7442766 | +0.7395238 / −0.7377587 | the same as inverted |
| measured tune | 4.1711 / 4.2294 | 4.2335 / 4.1279 | the same as inverted |

Both of the ±5e-5 scans associate **431 scan points with 431 acquisitions** --
the same count from the same interval matching -- so the two are directly
comparable and nothing was silently dropped from either.

Three short logs (`143448`, `144832`, `150022`) are aborted runs. Their
acquisitions sit in the inverted folder and are excluded by the interval matching
`find_scan_measurements` already does, which is why they need no special case.

### 11.2 The model is not matched, and now it says so

`build_model` was already reading the machine's circuits rather than matching a
tune (§ `SCAN_QUAD_SETTINGS`). What was missing was the consequence, stated: the
start model's tune is **not** the machine's, deliberately, because matching moves
`kbrqf` and `kbrqd` -- the same lever a distributed gradient error pulls.

`scripts/measured_optics.py` measures the gap, per campaign, from the MD's own
data: the AC-dipole drive re-fitted from each acquisition, harpy and omc3 through
`psb_md`'s pipeline, equation-compensated so the result describes the free
machine, and the natural tune and chromaticity from the tune/chroma scan. It
writes `results/optics/<slug>/summary.json`, which is where the report tabs get
their opening numbers.

Three beta-beats are reported and they are not the same quantity. Against the
LOCO start model it is what the fit sees on iteration zero. Against the same
lattice with `kbrqf`/`kbrqd` matched to the measured tune it is the part no tune
match can remove. Against omc3's analysis model -- matched independently -- it is
the conventional optics number, and it agrees with the matched column to 0.1
points, which is the check that the match itself is not doing something odd.

**The gap is small at the normal tunes and enormous at the inverted ones:**

| | model tune | measured | error | circuits needed to close it |
|---|---|---|---|---|
| normal | 4.17040 / 4.23111 | 4.17110 / 4.22944 | −0.0007 / +0.0017 | +0.005 % / −0.010 % |
| inverted | 4.30040 / 4.01633 | 4.23346 / 4.12792 | **+0.0669 / −0.1116** | **−0.74 % / +0.46 %** |

The last column is the QFO / QDE change, in magnitude, that puts the model on the
measured tune -- `matched_model.quad_settings` in each `summary.json`.

Both are the machine's own circuit currents in the same sequence, so the model's
*tune response* to the two circuits is about **2.1x the machine's**: the machine
moved +0.062 / −0.102 between the two settings and the model moves +0.130 /
−0.215 on the same currents.

The consequence is visible without any fitting. A corrector's closed orbit goes
as `1 / (2 sin(pi Q))`, and the inverted model's fractional `Qy` is 0.016 against
the machine's 0.128 -- a factor of about 7.8 on every vertical orbit it predicts.
That is exactly what the scoreboard shows: the inverted campaign's **start model
scores 689 % on the vertical delta orbit and 810 % on the vertical closed
orbit**, against 7.2 % and 131 % for the normal one. The predicted amplification
from the tune alone is 7.69x; the measured ratio is 689/7.2 = 7.5x, so the tune
error accounts for essentially all of it. The fits still converge and still land
at 7-10 %, but the start model they begin from is nothing like the machine.

The *beta* functions are a different story, and the contrast is the point: the
measured beta-beat against the un-matched model is 7.1 % / 5.2 % rms at the
normal tunes and 7.7 % / 5.3 % at the inverted ones. Beta has no resonant
denominator, so a tune error that multiplies the corrector response by 7.7 barely
moves it. Matching the tune first confirms it: 7.7 % / 5.3 % becomes 7.5 % / 5.3 %
at the inverted setting. Two tenths of a point of the beta-beat is tune; the rest
is gradient error the two main circuits cannot reach, which is what LOCO is for.

Worth checking before this is quoted as a magnet-calibration result: whether the
inverted setting also trimmed `kbrqfcorr` / `kbrqdcorr` (pinned to zero here) or
used a knob the LSA readings above do not carry. At the normal tunes the LSA
currents reproduce the measured tune to 5e-5 of circuit strength; at the inverted
ones they are 0.74 % and 0.46 % out. That is not a smooth calibration slope, and
a missing trim would explain it.

The pinned tunes and chromaticities in `campaign.py` are **checked** against the
exports, not trusted: `measured_optics.py` refuses to run if they disagree by
more than 1e-5. The pinning exists so a campaign can be described with the mount
absent, which is the normal state of affairs (§2).

### 11.2b The preprocessing chain, and the one that was nearly used

The first run of `measured_optics.py` used `TbtPreprocessing()`, whose defaults
are **SSA cleaning alone**. That is the configuration `psb_md`'s
`ACD_PREPROCESSING_ORDER_REPORT.md` section 8.5 measures as the weakest of the
lot: over the 23 acquisitions of one orbit, 8 pass the AC-dipole consistency
guard with the full chain and *none* with SSA alone.

`PRODUCTION_PREPROCESSING` is now the chain that report's section 1 names:
demodulate, remove the dispersive ripple, remove the per-BPM hardware lines, then
SSA-clean per BPM (window 200, rank 4).

**Two of those four stages cannot run on this MD.** The ripple and interference
removals are fitted from AC-dipole-off blanks, and 2026-08-21 took none --
`find_blank_acquisitions_dir` returns `None` for all four driven folders, both
stages log and skip. What actually ran is demodulation (envelope depth 57-66 %,
closed orbit held to 1e-19 m) and SSA. `summary.json` records the chain and
whether blanks were found, and the pages say so; do not quote these optics as
having had the full treatment.

### 11.3 What is per-campaign now

- `cached_scan` / `cached_response` / `cached_orbits` take `campaign=` and
  namespace their parquet by slug. The normal-tunes files keep their existing
  names, so the ten-minute cold read is not repeated.
- `run_method2`, `run_method1`, `predict_loco`, `case_optics`, `report_cases` and
  `compare_fits` all take `--campaign`, and their `--matrix` / `--output` /
  figure directories default off it. Figures live under
  `docs/assets/figures/<slug>/<page>/`.
- `scripts/run_campaign_fits.py` runs the nine cases the pages show for one
  campaign. A 60-case sweep was run once on the first configuration; it has been
  retired — its fits, its driver script and the findings page that quoted them
  are gone, and it will not be repeated.
- Each report page is now two content tabs, one per configuration, each opening
  with that machine's measured-vs-model optics. `pymdownx.tabbed` had to be
  enabled in `zensical.toml`.

### 11.4 What to be careful about

**Gradients do not compare across tabs the way they compare within one.** The two
tabs are two lattices with two start models, so a fitted `k1` is a correction to
a different starting point in each. Agreement between them is evidence about the
magnets; disagreement is information, not a bug.

**Chromaticity plots use MAD-NG-native `dq1` / `dq2` everywhere.** Every `Dp/p`
point in the full XImeter export is converted with the PSB accelerator's
`dp2pt`; all ctimes then share one fitted slope while retaining independent tune
intercepts. The plotted measured error is the common slope's fit covariance.
The export's `Xi` summary is not used.

**The large-step scan is not a third machine.** `INVERTED_DOUBLE` shares
`INVERTED`'s quads and its optics analysis; only the step differs. It exists to
say whether 1.5e-4 in one step buys anything over 5e-5 in four.

### 11.5 Fourth pass: the matched model, and a table bug worth knowing

- `measured_optics.py` now twisses **two** model lattices per campaign, the
  un-matched start model and the same sequence with `kbrqf`/`kbrqd` matched to
  the measured tune, and writes both betas, both beatings, both chromaticities
  and the matched circuits into `measured.parquet` and `summary.json`.
- `report_cases.py` draws `measured_optics.png` and `measured_optics_matched.png`
  per campaign, both carrying the measured points, and both titled with the
  machine's tune and the model's. The per-case lattice figure
  (`<page>_optics.png`) now carries the measured beta-beating on its beating
  panels, against the same start model the curves are against.
- **A `|` inside inline maths silently kills a Markdown table.** The header row
  gets one more cell than the delimiter row and Python-Markdown declines to make
  a table at all -- it emits a paragraph of pipes, the build reports no error, and
  six tables were shipping that way. Write `$\lvert v\rvert$`, never `$|v|$`.
  `tests/test_docs_render.py` renders every page in `docs/` with the site's own
  extension set and fails on a surviving delimiter row.
