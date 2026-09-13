"""The phase-advance-constraint extension to Method 2 (docs/studies/phase-advance-constraint.md).

Everything phase-specific lives here, isolated from the production LOCO
fitter: the series-building glue (`series.py`, imported by
`method2_delta_orbit/run_method2.py`'s `--phase-constraint` flag) and the
standalone investigation scripts (`experiment.py`, `plot_experiment.py`,
`plot_scenarios.py`) that produced the evidence in the doc.
"""
