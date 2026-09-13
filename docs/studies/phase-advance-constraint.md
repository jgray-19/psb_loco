# Spec: measured phase advance as a fit observable (breaks the BPM-gain degeneracy)

**For:** whoever implements this in `psb_loco` (`method2_delta_orbit/run_method2.py`)
and, if the observable itself needs anything new, in `aba_optimiser`.
**Written from:** `psb_loco`. **Implemented** — `--phase-constraint`
(`method2_delta_orbit/run_method2.py`) and its `--phase-weight` passthrough
(`scripts/run_campaign_fits.py`, `scripts/refresh_docs.sh` Stage 2b). All the
phase-specific code (the series builder `run_method2.py` calls, and the
standalone investigation scripts behind §10/§11's evidence) lives in its own
top-level `phase_advance_constraint/` package, isolated from the production
fitter for review — see §9. See §10 for results.
**Status:** implemented, weight is not yet a settled default — see §10.

**Size:** the data already exists and a sibling fitter already consumes it —
this is a wiring spec, not a new-physics or new-measurement one. Read §3
before assuming otherwise.

---

## 1. What is being asked for

Add the measured **BPM-to-BPM phase advance** (`mu1`/`mu2`, i.e. `MUX`/`MUY`
differenced between adjacent BPMs, never the cumulative phase — see §5) as an
extra residual in Method 2's loss, fitted jointly with the existing
closed-orbit response.

This is not a BPM-calibration knob. It is the thing that makes a BPM-gain
knob *worth adding*: see §2 for why gain cannot be resolved from orbit
response alone, and why phase advance is the one observable in this
pipeline that is immune to it.

---

## 2. Why — BPM gain and magnet strength are the same degree of freedom in an
orbit-only fit

Every observable Method 2 currently fits is a **linear response of orbit
displacement to a corrector kick**: `d(orbit)/dk`. Consider a single BPM
whose true gain is `g != 1`, so its *reported* reading is `g * x_true`
instead of `x_true`. The fit sees `g * x_true` and asks the model to explain
it. If quadrupole `k1` at some element scales that BPM's response by the
same `g` (which, for the one-BPM, one-corrector case, a nearby gradient
error can always be tuned to do to first order), the fit cannot tell "this
BPM over-reads by `g`" from "the optics genuinely amplify by `g` here" — both
explanations fit the same residual to the same accuracy. **Orbit-response
LOCO is scale-degenerate between BPM gain and local magnet strength.** This
is not new physics; it is why the original Safranek LOCO algorithm always
fits BPM and corrector gains *jointly* with magnet strengths, using extra
constraints (an independent measurement, or a global sum-rule) to pin the
overall scale.

**Phase advance breaks this degeneracy because it does not scale.** BPM
gain multiplies the *amplitude* of whatever the BPM sees; it does nothing to
*when in the oscillation cycle* it sees it. `mu1`/`mu2` (the phase of the
betatron oscillation between two adjacent BPMs) is gain-independent by
construction — a mis-calibrated BPM reports the wrong amplitude at the right
phase. So a fit that includes measured phase advance alongside orbit
response has, for the first time in this pipeline, an observable that
constrains magnet strength (which does move phase advance, through the
gradient's effect on the beta function and hence the phase integral)
**without also being consistent with, and therefore confusable with, a BPM
gain error.**

Concretely: if a future BPM-gain knob family is added to Method 2 with only
the existing orbit-response observable, its Hessian will have a near-null
direction along "every gain and the local `k1` move together" — exactly the
flat-valley signature already seen in this session's `k1`+tilt investigation
(`plots/hessian_uncertainty_vs_iteration.png`: tilt uncertainty ~10x k1's,
both campaigns, i.e. a family that is real but only weakly separated from
its neighbours in the null space). Phase advance is the fix for that
specific flatness, not a replacement observable — it is added *alongside*
orbit response, not instead of it, because orbit response is what constrains
overall geometry and dispersion that phase advance is comparatively blind
to.

**Consequence for scope:** a BPM-gain knob family should not be added to
Method 2 before this spec, or after it without also being added — a gain
knob with only orbit response to constrain it is not a useful addition, it
is a new flat direction. This document is what makes a future BPM-gain spec
worth writing.

---

## 3. Feasibility — the data already exists, and a sibling fitter already
uses it

Checked this session, not assumed:

- `psb_md`'s own MD pipeline (`psb_md/psb_md/hio_analysis.py`,
  `run_driven_compensated_optics_from_lin_files` and
  `run_acd_phase_analysis`) already runs omc3's hole-in-one / ACD analysis on
  the same turn-by-turn acquisitions that live under the same mount
  `loco_common.campaign` already points `measurements_path` at
  (`/user/psbop/MultiTurn/2026_08_*_Multiturn`). It already writes
  **`phase_x.tfs`/`phase_y.tfs`** (omc3-standard: `PHASEX`, `ERRPHASEX`,
  `PHASEXMDL`, `DELTAPHASEX`, `ERRDELTAPHASEX` columns) per momentum, per
  campaign — this is not new data to acquire.
- `tmom-recon`'s `measurements/twiss_from_measurement.py` (already a
  `psb_md` dependency, and reachable from `psb_loco`'s own venv) already
  parses these into `MUX`/`MUY` frames, indexed by BPM.
- `psb_md/psb_md/measured_optics.py` already assembles a fit-ready,
  BPM-indexed frame carrying `mu1`/`mu2` **alongside** `x`, `y`, `beta11`,
  `beta22`, `dx`, `dy` (`PSB_OBSERVABLES`, line 64), for its own use of
  `aba_optimiser.training_closed_twiss.ClosedTwissFitter` — **the same
  fitter class `method2_delta_orbit/run_method2.py` already imports as
  `ClosedOrbitFitter`** (`run_method2.py:24`). Its module docstring documents
  exactly the differencing this spec needs:

  > `mu1`/`mu2` are the **BPM-to-BPM advance**, never the cumulative phase.
  > Only the advance between adjacent BPMs is measurable; the running total
  > is an accumulation of those advances and carries no extra information...
  > Both sides are differenced before the residual is formed —
  > `_advance_targets` on the measurement... and `_to_advance` on the model.

  This means `ClosedTwissFitter` **already has** the machinery to fit
  `mu1`/`mu2` as an observable (it is exercised today, by `psb_md`, not a
  hypothetical). The open question this spec does not yet answer is whether
  that machinery, built for `psb_md`'s absolute-twiss fit, plugs into
  `run_method2.py`'s corrector-response settings (`CorrectorSetting`,
  `closed_orbit_series`) without change, or needs the same kind of
  observable-family plumbing `--absolute-planes` already added for
  absolute `x`/`y` — see §4.

---

## 4. Implementation sketch

### 4.1 What `run_method2.py` fits today

Every `CorrectorSetting` is one (corrector, step, momentum) measurement of
**delta orbit** — orbit relative to a reference, not an absolute twiss
quantity. `--absolute-planes` already exists as an escape hatch: it lets `x`
and/or `y` enter as absolute (not subtracted) observables, folded into the
same per-corrector settings (`run_method2.py`'s `warn_family_mismatch` and
`default_corrector_baseline`).

`mu1`/`mu2` are **not** a function of which corrector was stepped — the
measured phase advance is one dataset per momentum, a property of the
machine's own periodic solution, exactly like the absolute `x`/`y` plane is
one measurement folded into every corrector-response setting. It should
enter the same way absolute planes do: as an observable attached to
*every* setting at a given momentum (constant across correctors), not as
its own new `CorrectorSetting`.

### 4.2 Sketch, not yet verified against `ClosedTwissFitter`'s exact call
signature

1. `loco_common/campaign.py`: expose `optics_dir` (already present per the
   agent survey but currently unused for phase) so a campaign can be asked
   for its `phase_x.tfs`/`phase_y.tfs` path per momentum.
2. New module (or a `loco_common/measured_phase.py` mirroring
   `loco_common/measured_response.py`'s caching pattern): load
   `phase_x.tfs`/`phase_y.tfs` via the same `tmom_recon` reader
   `psb_md.measured_optics.load_optics_frame` already uses, return a
   BPM-indexed `mu1`/`mu2` frame per momentum.
3. `run_method2.py`: new flag `--absolute-planes` gains `mu1`/`mu2` as
   allowed values (or a new `--phase-advance` flag, if mixing rotation-like
   phase into the same list as position planes reads badly — pick one
   deliberately, do not silently overload `x`/`y`'s
   baseline-corrector logic onto a differently-shaped observable).
4. Confirm `ClosedOrbitFitter`/`ClosedTwissFitter` accepts `mu1`/`mu2` in its
   `observables` argument when constructed from `run_method2.run()` — §3
   established the fitter supports it for `psb_md`'s call pattern, not yet
   for `run_method2.py`'s. This is the one thing in this sketch that must be
   checked against real code before estimating further, and is the natural
   first test (§6.1).

### 4.3 Prior / units

`mu1`/`mu2` are phase (dimensionless tune units), not metres — same
mixed-units problem the tilt spec (§5 of `quadrupole-roll.md`) already
solved with a per-family prior. If phase advance enters through the same
`prior_strengths` mechanism as the existing families, it needs its own
suffix in `PRIOR_SUFFIXES`; if it enters via `ClosedTwissFitter`'s own
observable-weighting instead (more likely, since it is an observable not a
knob), the relevant knob is unaffected — check which side of the fitter the
existing `psb_md` usage weights this on before assuming psb_loco's
per-family prior story applies at all.

---

## 5. Conventions to get right (mirrors `psb_md.measured_optics`'s own
warnings)

- **Difference before residual, on both sides.** Never fit cumulative
  `MUX`/`MUY` directly — the running total weights each interval by how far
  around the ring it sits and gives the arbitrary origin BPM an unearned
  say in the answer. `psb_md.measured_optics`'s docstring (quoted in §3) is
  the canonical statement of why; reuse its `_advance_targets`/`_to_advance`
  pattern rather than re-deriving it.
- **`mu1`/`mu2` come from equation-compensated optics, not
  `compensation="none"`.** `psb_md.measured_optics.load_optics_frame`'s own
  docstring: the fitter computes the free periodic solution of a sequence
  with no AC dipole in it, so feeding it driven-but-uncompensated optics
  attributes the AC dipole's own beta-beat to the magnets. Whatever loads
  `phase_x.tfs` for `psb_loco` must point at the same compensated folder
  `psb_md` already produces, not a raw driven one.
- **Alpha stays excluded.** `psb_md.measured_optics` deliberately drops
  `alfa11`/`alfa22` because the measured alpha sits too far from the model
  to be a usable target. No reason to relitigate that here; phase advance
  does not need alpha.

---

## 6. Tests

### 6.1 `ClosedTwissFitter` accepts `mu1`/`mu2` through `run_method2.py`'s
call path — do this first

Construct a `ClosedOrbitFitter` exactly as `run_method2.run()` does today,
but pass `observables` including `mu1`/`mu2` and a measurement frame that
has them. Confirm it builds and evaluates without error before writing any
of §4's plumbing. This is the load-bearing assumption of the whole spec;
§3 shows the fitter supports it for a different caller, not this one.

### 6.2 Degeneracy check — the actual point of this spec

Fit `k1` (+ any BPM-gain knob, once that spec exists) once with orbit
response only, once with orbit response + `mu1`/`mu2`. The Hessian's
smallest eigenvalue in the joint `k1`/gain subspace must increase materially
with phase advance included — that is the direct, measurable statement of
"the degeneracy in §2 is broken." Reuse this session's
`plot_hessian_uncertainty.py` pattern (monkeypatch
`_GaussNewtonFitter._collect_gn`, run `hessian_uncertainties` on the
physical Hessian) rather than re-deriving it.

### 6.3 Phase advance alone should reproduce known-good `k1`

On a campaign with no injected error and no BPM-gain knob (i.e. today's
knob set), fitting orbit + phase advance should recover the same `k1` as
orbit alone, within its now-tighter uncertainty — adding an observable that
agrees with the existing physics must not move the answer, only sharpen it.
A shift here means the phase data and the orbit data disagree about the
model, which is a data-quality question to chase before trusting either.

### 6.4 The family is off by default

Existing fits (no `--absolute-planes mu1`/`mu2` or whatever flag §4.3
settles on) must be byte-identical to today's output.

---

## 7. Acceptance

Minimum: §6.1 passes (the fitter accepts the observable through this
caller), §6.4 passes (opt-in, no behaviour change by default), and §6.3
shows no unexplained shift in `k1` on a clean campaign.

The result this exists to enable, which this spec does not itself claim:
once phase advance is in the loss, a BPM-gain knob family (a follow-on spec,
not part of this one) becomes something the fit can actually resolve rather
than something that only adds a flat direction. Whether the normal-tunes
`k1`+tilt behaviour investigated earlier this session changes once that
combination exists is a question for that follow-on work, not this one.

---

## 8. Out of scope

- The BPM-gain knob family itself — deliberately not specified here. Adding
  it before this lands would repeat the mistake §2 describes; adding it
  without ever writing this would leave gain permanently under-constrained.
- `beta11`/`beta22` as an additional observable — `psb_md.measured_optics`
  already carries it (from amplitude, not phase), and it is a natural
  next addition once `mu1`/`mu2` plumbing exists, but beta has its own
  amplitude-vs-phase estimator question (see `load_optics_frame`'s
  docstring) that is independent of the gain-degeneracy argument this spec
  is built around.
- Corrector-gain calibration (the analogous degeneracy for the correctors
  themselves, not the BPMs) — same shape of problem, not addressed here.

---

## 9. Reproducing the evidence

Nothing in this repo yet reproduces §3's claims mechanically — they were
established this session by reading `psb_md/psb_md/measured_optics.py`,
`psb_md/psb_md/hio_analysis.py`, and
`tmom-recon/src/tmom_recon/measurements/twiss_from_measurement.py` directly,
and by re-reading `method2_delta_orbit/run_method2.py`'s existing
`--absolute-planes` handling as the closest existing precedent for how a
momentum-level (not corrector-level) observable already enters this fitter.
Whoever implements §4 should start by running `psb_md`'s own
`assemble_measured_optics` against one campaign's optics dir to confirm the
`mu1`/`mu2` frame it returns looks as documented, before writing any new
`psb_loco` code against it.

**Post-implementation:** §10/§11's evidence now reproduces from
`phase_advance_constraint/`, kept apart from `method2_delta_orbit/` so it can
be audited on its own:

* `phase_advance_constraint/series.py` — `phase_optics_dir` (the cleaned,
  equation-compensated optics `scripts/measured_optics.py --optics-folders all`
  writes per RF folder) and `build_phase_series`, the only phase-specific
  code `run_method2.py` itself calls (`--phase-constraint`).
* `phase_advance_constraint/experiment.py` — the standalone
  `ClosedTwissFitter` experiment (`python -m
  phase_advance_constraint.experiment --campaign p17_p23_final --observables
  x y mu1 mu2 --phase-weight 10 --label ...`) that first isolated the
  SNR-dominance effect in §10.1, ahead of wiring it into the real Method 2
  fitter.
* `phase_advance_constraint/plot_experiment.py` and
  `phase_advance_constraint/plot_scenarios.py` — the figures behind §10.2
  and §11 respectively, both run as `python -m phase_advance_constraint.<name>
  --campaign <slug>`.

---

## 10. Results — phase must be up-weighted to move the fit

§4's implementation was landed as `--phase-constraint` (three extra
plain-twiss, no-corrector series, one per RF offset, `observables=("mu1",
"mu2")`) alongside every existing orbit-only corrector-trim series, in the
same `ClosedOrbitFitter` run. `aba_optimiser`'s `ClosedOrbitFitter` /
`ClosedOrbitSeries` / `ClosedOrbitWorker` needed a small extension for
this: a per-series `observables` override and a phase-only branch in
`ClosedOrbitWorker.prepare_data`/`_model_and_jacobian` (a phase-only series
carries no control knob and is never reference-subtracted, since BPM-to-BPM
phase advance is self-contained within one twiss).

### 10.1 At equal nominal weight, phase has no visible effect

The motivating test: `p17_p23_final`'s `none__k1__bpm-family` case shows a
large, spurious BPM-to-BPM X-phase zigzag in the model that the measured
phase does not have (found investigating why normal tunes behaves
differently from inverted under Method 2). Adding `--phase-constraint` at
its nominal measurement weight (`--phase-weight 1`, i.e. `mu1_var`/`mu2_var`
exactly as measured) barely moved this: RMS(model − measured) X phase
advance went from 0.01879 (no constraint) to 0.01830 — a 3% change, not
visible by eye.

The reason is an SNR mismatch: the closed orbit's measurement precision
(`|X|/ERRX`, median ≈ 3400) is roughly 10x tighter than phase's
(`|PHASEX|/ERRPHASEX`, median ≈ 290), and with `use_errors=True`
chi-normalisation the ~140 orbit corrector-trim settings swamp the 3
phase-only settings by construction. Phase is correctly wired into the
loss (confirmed separately: both sides of the `mu1`/`mu2` residual are
BPM-to-BPM advances, `_advance_targets` on the measurement side and
`_to_advance` on the model side — no unit mismatch), it is simply
out-numbered.

### 10.2 Up-weighting phase reduces the zigzag, with diminishing returns

`--phase-weight W` divides `mu1_var`/`mu2_var` by `W` (weight = 1/variance,
so this multiplies phase's contribution to the loss by `W`, holding the
measured values themselves fixed). Scanning `W` on the same case:

| phase weight | RMS(model − measured) [2π] | max residual [2π] |
| ---: | ---: | ---: |
| (no constraint) | 0.01879 | 0.03324 |
| 1 | 0.01830 | 0.03252 |
| 10 | 0.01497 | 0.02758 |
| 100 | 0.00713 | 0.01520 |
| 1000 | 0.00481 | 0.01084 |

![RMS zigzag residual vs phase weight](../assets/figures/studies/phase-advance-constraint/phase_weight_scan_p17_p23_final.png)

![Model vs measured X phase advance, phase constraint off vs on (weight 100)](../assets/figures/studies/phase-advance-constraint/real_method2_phase_check_p17_p23_final.png)

The reduction is real and monotonic but saturates: 10→100 buys a 2.1x
improvement, 100→1000 only 1.5x more, for a 10x larger weight each time.
The zigzag is reduced, not eliminated, even at `W=1000` — some structure at
BPM pairs 0, 3, 5, 7/9, 14 persists in every weighted fit, so up-weighting
phase is a partial, not a complete, explanation of the original symptom.

All fits above converged cleanly (no LM instability) except one unrelated
case in the full-matrix run at `W=100`:
`p17_p23_final/xy__k1+b+dy+t__bpm-family` (absolute-plane bends + dy + tilt
+ k1) diverged after 16 GN iterations — loss was decreasing steadily, then
every worker crashed on the same trial step at low `lambda` (≈0.02), which
reads as a bad global step rather than a per-worker fluke. Not yet chased
further; every other case (11/12 across both confirmed campaigns) completed.

### 10.3 Open questions this leaves

- **What weight should be the default, if any?** `W=1` is what the
  measurement itself says phase deserves and is not enough to matter;
  `W=1000` still has diminishing returns and no principled stopping point
  has been chosen.
- **Why does the zigzag persist at all weights?** If it were purely an
  orbit/phase-loss trade-off, a large enough weight should eventually pin
  the model to the measured phase advance at the constrained BPM pairs
  exactly. That it does not (residual asymptotes rather than vanishing)
  suggests either the phase data itself has structure the model's knob
  family cannot represent (the constraint is legitimately fighting the
  orbit data for an incompatible answer), or the specific BPM pairs that
  persist share something structural (odd/even magnet numbering,
  `group_quadrupoles_by_cell` lumping) not yet investigated.
- **The `xy__k1+b+dy+t__bpm-family` divergence** at `W=100` is unexplained
  and untested at other weights.

---

## 11. All-scenario optics — no phase constraint vs phase constraint (weight 100)

Every multi-momentum case, both campaigns with a confirmed phase mapping, beta-beating / phase-error / dispersion / coupling against the tune-matched model, with the measured points overlaid exactly as the report pages draw them (`phase_advance_constraint/plot_scenarios.py`). `p17_p23_final`'s "gradients, bends, offsets and rolls" tab is the one whose phase-constraint fit diverged (§10.2); it shows only the no-constraint curve.



=== "Normal tunes, 29th"

    === "Gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits"

        ![Beta-beating, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__bpm-family_beta_beating.png)

        ![Phase error, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__bpm-family_phase_error.png)

        ![Dispersion, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__bpm-family_dispersion.png)

        ![Coupling, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__bpm-family_coupling.png)

    === "Gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits"

        ![Beta-beating, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1+t__bpm-family_beta_beating.png)

        ![Phase error, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1+t__bpm-family_phase_error.png)

        ![Dispersion, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1+t__bpm-family_dispersion.png)

        ![Coupling, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1+t__bpm-family_coupling.png)

    === "Gradients free, one knob per magnet, fitted with both planes as delta orbits"

        ![Beta-beating, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__none_beta_beating.png)

        ![Phase error, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__none_phase_error.png)

        ![Dispersion, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__none_dispersion.png)

        ![Coupling, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/none__k1__none_coupling.png)

    === "Gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute"

        ![Beta-beating, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__bpm-family_beta_beating.png)

        ![Phase error, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__bpm-family_phase_error.png)

        ![Dispersion, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__bpm-family_dispersion.png)

        ![Coupling, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__bpm-family_coupling.png)

    === "Gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute"

        ![Beta-beating, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__none_beta_beating.png)

        ![Phase error, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__none_phase_error.png)

        ![Dispersion, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__none_dispersion.png)

        ![Coupling, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy__none_coupling.png)

    === "Gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute"

        ![Beta-beating, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy+t__bpm-family_beta_beating.png)

        ![Phase error, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy+t__bpm-family_phase_error.png)

        ![Dispersion, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy+t__bpm-family_dispersion.png)

        ![Coupling, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p17_p23_final/xy__k1+b+dy+t__bpm-family_coupling.png)


=== "Inverted tunes, 28th"

    === "Gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits"

        ![Beta-beating, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__bpm-family_beta_beating.png)

        ![Phase error, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__bpm-family_phase_error.png)

        ![Dispersion, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__bpm-family_dispersion.png)

        ![Coupling, gradients free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__bpm-family_coupling.png)

    === "Gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits"

        ![Beta-beating, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1+t__bpm-family_beta_beating.png)

        ![Phase error, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1+t__bpm-family_phase_error.png)

        ![Dispersion, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1+t__bpm-family_dispersion.png)

        ![Coupling, gradients and rolls free, lumped to 32 knobs by cell, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1+t__bpm-family_coupling.png)

    === "Gradients free, one knob per magnet, fitted with both planes as delta orbits"

        ![Beta-beating, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__none_beta_beating.png)

        ![Phase error, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__none_phase_error.png)

        ![Dispersion, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__none_dispersion.png)

        ![Coupling, gradients free, one knob per magnet, fitted with both planes as delta orbits](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/none__k1__none_coupling.png)

    === "Gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute"

        ![Beta-beating, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__bpm-family_beta_beating.png)

        ![Phase error, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__bpm-family_phase_error.png)

        ![Dispersion, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__bpm-family_dispersion.png)

        ![Coupling, gradients, bends and offsets free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__bpm-family_coupling.png)

    === "Gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute"

        ![Beta-beating, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__none_beta_beating.png)

        ![Phase error, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__none_phase_error.png)

        ![Dispersion, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__none_dispersion.png)

        ![Coupling, gradients, bends and offsets free, one knob per magnet, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy__none_coupling.png)

    === "Gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute"

        ![Beta-beating, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy+t__bpm-family_beta_beating.png)

        ![Phase error, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy+t__bpm-family_phase_error.png)

        ![Dispersion, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy+t__bpm-family_dispersion.png)

        ![Coupling, gradients, bends, offsets and rolls free, lumped to 32 knobs by cell, fitted with both planes absolute](../assets/figures/studies/phase-advance-constraint/scenarios/p23_p13_final/xy__k1+b+dy+t__bpm-family_coupling.png)
