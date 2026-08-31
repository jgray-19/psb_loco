"""Inverted multi-absolute fit with the independent +/-1.5e-4 scan added.

The standard scan contributes its four nonzero steps and one averaged absolute
orbit per RF setting. The large-step scan contributes only its +/-1.5e-4
corrector measurements: its untrimmed acquisitions are duplicate measurements
of the same machine state and must not silently double the static-orbit weight.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from psb_md.closed_orbit_fitting import write_optimisation_results

from loco_common.campaign import INVERTED, INVERTED_DOUBLE
from loco_common.measured_response import RF_STEERING_OFFSETS
from loco_common.model import DEFAULT_SEQUENCE_FILE, build_model, model_twiss
from method2_delta_orbit.run_method2 import (
    DISPERSION,
    STATIC_ORBIT,
    build_multi_pt_settings,
    run,
)


def combined_settings(model):
    common = {
        "model": model,
        "rf_offsets": list(RF_STEERING_OFFSETS),
        "twiss": model_twiss(model, chrom=True),
        "absolute_planes": ("x", "y"),
        "error_floor": 1e-4,
        "corrector_baseline": "machine",
    }
    standard = build_multi_pt_settings(campaign=INVERTED, **common)
    large = build_multi_pt_settings(campaign=INVERTED_DOUBLE, **common)
    extra = [
        setting for setting in large
        if setting.offset_k != 0.0
        and setting.corrector not in {DISPERSION, STATIC_ORBIT}
    ]
    return standard + extra, len(standard), len(extra)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sequence-file", type=Path, default=DEFAULT_SEQUENCE_FILE)
    args = parser.parse_args()

    model = build_model(sequence_file=args.sequence_file, campaign=INVERTED)
    settings, standard_count, extra_count = combined_settings(model)
    initial_path = (
        Path("results/matrix_inverted")
        / "xy__k1+b+dy+t__bpm-family/knobs.csv"
    )
    initial = pd.read_csv(initial_path).set_index("knob")["value"].to_dict()
    knobs, uncertainties, diagnostics = run(
        settings,
        model,
        batch_momenta=True,
        prior_strength=args.prior,
        optimise_quadrupoles=True,
        optimise_bends=True,
        optimise_quad_dy=True,
        optimise_quad_tilt=True,
        group_quadrupoles_by_cell=True,
        initial_knob_strengths=initial,
        output_path=args.output,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    write_optimisation_results(
        args.output / "knobs.csv", knobs, uncertainties, stage_name="large_step_prior_study"
    )
    summary = {
        "method": "delta_orbit",
        "status": "complete" if diagnostics.get("accepted_evaluations", 0) >= 2 else "no_valid_step",
        "diagnostics": diagnostics,
        "prior_strength": args.prior,
        "initial_knobs": str(initial_path),
        "standard_settings": standard_count,
        "added_large_step_settings": extra_count,
        "n_settings": len(settings),
        "large_step_offsets_k": sorted({s.offset_k for s in settings if abs(s.offset_k) == 1.5e-4}),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
