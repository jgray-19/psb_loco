# Handover

Not published on the site. The earlier session log is in git history (`git log -- HANDOVER.md`).

## Open

1. **Gain fits: not yet interpreted.** Multi-momentum `k1+g` cuts the delta-orbit residual from 0.267 to 0.209 (x) and 0.044 to 0.024 (y) on `p23_p13_final`, and 0.210 to 0.148 and 0.047 to 0.025 on `p17_p23_final`; dispersion does not improve. But with off-momentum data the vertical BPM gains fit to about −0.5 and the DVT gains to about +0.9 (product ≈ 0.95): the split is a prior-set scale, and the cause is probably the model's wrong vertical dispersion (item 2) entering through the BPM gain. This is untested. Nominal-RF only, `p23_p13_final`, 32 knobs: DHZ gains −0.08…−0.29, DVT −0.00…−0.08 (the measured/model ratios were 0.71–0.93 and 0.95–1.03), BPM gains 4 % rms (max 11 %), loss 3.9e-9 → 2.5e-10. Not comparable as it stands: the gain fit regularises the magnet knobs with absolute widths (`--knob-sigma`, a guess), the plain fit with a relative prior, and its `dk1l` rms is larger (6.6e-3 against 2.8e-3). Compare at matched regularisation before concluding that gains explain the residual.
2. **The model's vertical dispersion is wrong.** The machine has 7.7e-5 m rms where the model has 2.0e-5 m; horizontally the residual is 79–84 % of the measured amplitude. Under the global reference this enters every off-momentum target as a 40–90 σ first-order term, and caps the multi-momentum fits. The momentum estimates and the dispersion orbits themselves are ruled out.
3. **`DPP_PER_MM`** is 6e-4; the chroma scan gives 4.5e-4. Unexplained.
4. **The closed-orbit null space is large.** Judge a fit by derived quantities (loss, closed orbit), not by knobs. A fit's own residual is not a quality score. `PRIOR_STRENGTH` (1e-4) is not a tuning knob; the only deviation is the tilt prior (1e-2).
5. **`tests/test_recovery.py`, `test_pt_mode.py`, `test_naming.py`** build xsuite truth. They failed on 2026-10-08 here: `accpy` has xtrack 0.115 (no `ptau`), `.venv` has 0.111 (rejects `yoshida-6`). Run them on `cs-ccr-dev3`.

## Traps

- A wrong `pt` biases the fit, and a sign error makes the lattice unstable (MAD's normal form fails). `test_pt_mode.py` uses 20 % low.
- Analysis scripts must build the model as the driver does (`build_model`, tune and corrector knobs). `open_interface` applies neither.
- Fixtures speak the machine's convention (LSA `/K`); convert to MAD's at the driver's boundary.
- A `|` inside inline maths silently kills a Markdown table. Write `$\lvert v\rvert$`; `tests/test_report_render.py` checks.
- `adelmo`'s fitter treats `prior_strengths=None` as no prior, and a dict must name every optimised family. `run()` always passes the full dict.
- `pymadng` waits with `select()`, which rejects descriptors ≥ 1024: about 250 workers. `ClosedOrbitFitter` caps at `machine_worker_limit()` and gives each process several settings.

## Rules

- The acquisition mount is read-only; generated output stays here.
- No mocks or monkeypatching in tests; prefer physics checks to pinning implementation.
- Delete focused debug scripts once the diagnosis is done.
- Upstream (`psb_md`, `tmom_recon`, `xtrack_tools`, `pymadng`) is imported, not edited. `adelmo` is edited only for features this repo needs (2026-10-08: `kick_prefix` and attribute-keyed `knob_sigmas` in `CalibratedClosedOrbitFitter`).
