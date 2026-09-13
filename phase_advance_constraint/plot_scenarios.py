"""All-scenario optics figures: every multi-momentum case, no phase constraint
vs phase constraint (--phase-weight 100), beta-beating / phase-error /
dispersion / coupling against the tune-matched model. Reuses the same
twiss/differencing (scripts.case_optics), the measured overlays and rms
(loco_report.data, loco_report.figures) and the styling (loco_report.style,
psb_md.plotting) as the docs site, so the measured points sit on these plots
exactly as they do on the report pages.

    python -m phase_advance_constraint.plot_scenarios --campaign p17_p23_final
    python -m phase_advance_constraint.plot_scenarios --campaign p23_p13_final
"""
import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# psb_md has its own *regular* `scripts` package, which -- once its path is on
# sys.path -- wins package resolution over psb_loco's namespace-package
# `scripts` regardless of sys.path order (a regular package always beats a
# namespace portion, PEP 420). Importing psb_loco's scripts.case_optics here,
# before psb_md's path is inserted below, caches the right module in
# sys.modules so the later `from scripts.case_optics import ...` reuses it.
from scripts.case_optics import case_optics  # noqa: E402

sys.path.insert(0, "/afs/cern.ch/work/j/jmgray/private/psb_md")

import pandas as pd  # noqa: E402
from psb_md.plotting import finalize_figure, style_axis  # noqa: E402

from loco_common.campaign import campaign_by_slug  # noqa: E402
from loco_common.fit_mode import fit_mode_by_slug  # noqa: E402
from loco_common.model import build_model  # noqa: E402
from loco_report.data import Results, read_parquet  # noqa: E402
from loco_report.figures import (  # noqa: E402
    _curve_rms,
    _draw_measured_beat,
    _draw_measured_dispersion,
    _draw_measured_rdt,
)
from loco_report.style import (  # noqa: E402
    CASE_COLOURS,
    START_COLOUR,
    legend_headroom,
    mark_bpms,
    panels,
    quantity_of,
)

SEQUENCE_FILE = "models/model_qx0.165000_qy0.227500/psb3_saved.seq"
RESULTS = Path("results")
OUT_ROOT = Path("docs/assets/figures/studies/phase-advance-constraint/scenarios")

#: The measured-optics table's column suffix for the tune-matched reference,
#: which is the reference these figures difference every case against -- see
#: ``loco_report.figures.optics``.
REFERENCE = "matched_model"

CASES = (
    "none__k1__bpm-family",
    "none__k1+t__bpm-family",
    "none__k1__none",
    "xy__k1+b+dy__bpm-family",
    "xy__k1+b+dy__none",
    "xy__k1+b+dy+t__bpm-family",
)

SCENARIOS = (
    ("multi", "no phase constraint"),
    ("multi_phase", "phase constraint (weight 100)"),
)

OPTICS_FIGURES = (
    ("beta_beating", "beta_beating_x", "beta_beating_y", "beta-beating [%]"),
    ("phase_error", "phase_error_x", "phase_error_y", "phase error [$2\\pi$]"),
    ("dispersion", "dispersion_x", "dispersion_y", "$D$ [m]"),
    ("coupling", "coupling_f1001", "coupling_f1010", "$|f|$"),
)


def load_knobs(path: Path) -> pd.Series:
    return pd.read_csv(path).set_index("knob")["value"]


def plot_case(model, results: Results, start: pd.DataFrame, positions: dict,
              campaign_slug: str, case: str, output: Path) -> int:
    frames = {}
    for suffix, label in SCENARIOS:
        knobs_path = RESULTS / f"matrix_{campaign_slug}_{suffix}" / case / "knobs.csv"
        if not knobs_path.exists():
            continue
        knobs = load_knobs(knobs_path)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            knobs.rename_axis("knob").reset_index().to_csv(handle, index=False)
            csv_path = Path(handle.name)
        frames[label] = case_optics(model, csv_path, start)
        csv_path.unlink()

    if not frames:
        return 0

    measured = results.measured_optics
    written = 0
    for stem, col_x, col_y, ylabel in OPTICS_FIGURES:
        if not all(col_x in frame.columns and col_y in frame.columns for frame in frames.values()):
            continue
        figure, axes = panels(2)
        for axis, column, plane in zip(axes, (col_x, col_y), ("x", "y"), strict=True):
            quantity = quantity_of(column)
            mark_bpms(axis, positions, label=plane == "x")
            axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
            measured_beat = (
                measured[f"beat_{plane}_{REFERENCE}"]
                if not measured.empty and f"beat_{plane}_{REFERENCE}" in measured.columns
                else None
            )
            if stem == "beta_beating" and not measured.empty:
                _draw_measured_beat(axis, measured, plane, REFERENCE)
            if stem == "dispersion":
                _draw_measured_dispersion(axis, results, plane)
            if stem == "coupling":
                _draw_measured_rdt(axis, measured, column)
            if stem in ("coupling", "dispersion"):
                start_column = f"{column}_start"
                any_frame = next(iter(frames.values()))
                if start_column in any_frame.columns:
                    axis.plot(any_frame["s"], any_frame[start_column], color=START_COLOUR,
                              linewidth=2.0, linestyle="--", label="matched model", zorder=1)
            for (label, frame), colour in zip(frames.items(), CASE_COLOURS, strict=False):
                values = frame[column].to_numpy()
                text = _curve_rms(results, column, frame["element"].to_numpy(), values, measured_beat)
                axis.plot(frame["s"], quantity.scale * values, color=colour,
                          linewidth=1.5, alpha=0.9, label=f"{label}, rms {text}")
            axis.set_ylabel(f"{plane}\n{ylabel}", fontsize=8)
            style_axis(axis)
        axes[-1].set_xlabel("s [m]")
        axes[0].legend(fontsize=6, ncols=1, loc="upper left")
        legend_headroom(axes[0])
        figure.suptitle(f"{campaign_slug} / {case}", fontsize=9)
        finalize_figure(figure, output / f"{case}_{stem}.png")
        written += 1
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, choices=("p17_p23_final", "p23_p13_final"))
    args = parser.parse_args()

    campaign = campaign_by_slug(args.campaign)
    model = build_model(sequence_file=SEQUENCE_FILE, campaign=campaign)
    # Both scenarios' fits are differenced against the same tune-matched model
    # the un-constrained "multi" run already cached: the campaign's measured
    # optics are only comparable in that reference frame (see
    # loco_report.figures.optics), and the phase constraint does not change it.
    base_mode = fit_mode_by_slug("multi")
    start = read_parquet(base_mode.results_root(campaign) / "optics" / "matched-model.twiss.parquet")
    positions = start["s"].to_dict()
    results = Results(campaign=campaign, mode=base_mode, positions=positions)

    output = OUT_ROOT / args.campaign
    output.mkdir(parents=True, exist_ok=True)
    total = 0
    for case in CASES:
        count = plot_case(model, results, start, positions, args.campaign, case, output)
        print(f"{case}: {count} figures")
        total += count
    print(f"wrote {total} figures to {output}")


if __name__ == "__main__":
    main()
