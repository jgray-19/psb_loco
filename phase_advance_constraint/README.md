# Phase-advance constraint

Everything specific to the phase-advance-constraint extension of Method 2,
kept apart from `method2_delta_orbit/` so it can be read and audited on its
own. Full spec, rationale and results: `docs/studies/phase-advance-constraint.md`.

- `series.py` — `phase_optics_dir` (phase from `results/optics/<campaign>/<folder>/free`,
  written by `scripts/measured_optics.py --optics-folders all`) and
  `build_phase_series`. The only phase-specific code the production fitter
  (`method2_delta_orbit/run_method2.py`'s `--phase-constraint` /
  `--phase-weight`) imports.
- `experiment.py` — standalone `ClosedTwissFitter` experiment used to
  isolate the phase/orbit SNR-weighting effect before it was wired into the
  real fitter.

      python -m phase_advance_constraint.experiment --campaign p17_p23_final \
          --observables x y mux muy --phase-weight 10 --label orbit_plus_phase_10x

- `plot_experiment.py` — docs-style figures for `experiment.py`'s output.

      python -m phase_advance_constraint.plot_experiment --campaign p17_p23_final \
          --labels orbit_only orbit_plus_phase orbit_plus_phase_10x

- `plot_scenarios.py` — the real Method-2 case matrix, no-constraint vs
  phase-constraint, with measured points overlaid; this is what produced the
  doc's §11 figures.

      python -m phase_advance_constraint.plot_scenarios --campaign p17_p23_final
      python -m phase_advance_constraint.plot_scenarios --campaign p23_p13_final

`run_campaign_fits.py`'s `--phase-constraint`/`--phase-weight` and
`refresh_docs.sh`'s Stage 2b are the only other places phase-specific
plumbing lives, and both are small, clearly-marked argument passthroughs
rather than logic — see them directly.
