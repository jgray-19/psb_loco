# Phase-advance constraint

Phase-specific code, kept apart from `poco/`. Rationale and results: [`docs/studies/phase-advance-constraint.md`](../docs/studies/phase-advance-constraint.md).

- `series.py`: `build_phase_series`, used by `run_poco --phase-constraint`.
- `experiment.py`, `plot_experiment.py`: standalone experiment that isolated the phase/orbit weighting effect, and its figures.

      python -m phase_advance_constraint.experiment --campaign p17_p23_final --observables x y mux muy --phase-weight 10 --label orbit_plus_phase_10x
      python -m phase_advance_constraint.plot_experiment --campaign p17_p23_final --labels orbit_only orbit_plus_phase orbit_plus_phase_10x

`run_campaign_fits.py` and `refresh_docs.sh` (stage 2b) only pass `--phase-constraint` / `--phase-weight` through.
