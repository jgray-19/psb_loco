"""Multi-momentum absolute-orbit fit (k0+dy+k1+tilt), with or without phase advance (mu1/mu2) in the loss.

Phase SNR (median ~290) is far below orbit's (~3400), so under chi-normalisation orbit swamps
phase; ``--phase-weight W`` divides ``mu1_var``/``mu2_var`` by W to compensate.

Usage:
    python -m phase_advance_constraint.experiment --campaign p17_p23_final \
        --observables x y mu1 mu2 --phase-weight 10 --label orbit_plus_phase_10x
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "/afs/cern.ch/work/j/jmgray/private/psb_md")
sys.path.insert(0, "/afs/cern.ch/work/j/jmgray/private/sgd-magnet-tuner/src")

from adelmo.machine.accelerators.psb import PSB as OptimiserPSB
from adelmo.machine.mad.machine_state import merge_machine_states
from adelmo.fitting.config import OutputConfig, SequenceConfig
from adelmo.poco.fitter import ClosedTwissFitter
from adelmo.optimisers.levenberg_marquardt import LevenbergMarquardtConfig
from psb_md.closed_orbit_fitting import (  # noqa: E402
    GRADIENT_CONVERGED_VALUE,
    isotropic_prior_strengths,
)
from psb_md.measured_optics import assemble_measured_optics  # noqa: E402

from loco_common.campaign import campaign_by_slug  # noqa: E402
from loco_common.measured_response import (  # noqa: E402
    average_orbit_frames,
    cached_scan,
    measured_orbits,
)
from loco_common.model import build_model  # noqa: E402
from loco_common.momentum import chroma_pt_by_rf_offset  # noqa: E402

SEQUENCE_FILE = "/afs/cern.ch/work/j/jmgray/private/psb_loco/models/model_qx0.165000_qy0.227500/psb3_saved.seq"
RESULTS_DIR = Path("/afs/cern.ch/work/j/jmgray/private/psb_loco/results/phase_advance_experiment")

RF_OFFSETS = (-2.0, 0.0, 2.0)

# rf_offset (mm) -> phase-cache subfolder (chromaticity-sign cross-check against momentum_reference_sources.json).
LABEL_BY_OFFSET = {-2.0: "offmom_0", 0.0: "0Hz", 2.0: "offmom_1"}

CACHE_HIO_DIR_BY_CAMPAIGN = {
    "p17_p23_final": (
        "/afs/cern.ch/work/j/jmgray/private/psb_md/"
        ".psb_cache_p17_p23_final_dynamic_demodulated_no_interference_comb_notch_no_ripple/hio"
    ),
    "p23_p13_final": (
        "/afs/cern.ch/work/j/jmgray/private/psb_md/"
        ".psb_cache_p23_p13_final_dynamic_demodulated_no_interference_comb_notch_no_ripple/hio"
    ),
}


def closed_orbits_by_pt(campaign_slug, pt_by_offset):
    campaign = campaign_by_slug(campaign_slug)
    points, orbit_by_path = cached_scan(campaign=campaign)
    orbits = {}
    for offset in RF_OFFSETS:
        untrimmed = {
            key: frame
            for key, frame in measured_orbits(
                offset, points=points, orbit_by_path=orbit_by_path, delta=False, campaign=campaign
            ).items()
            if key[1] == 0.0
        }
        orbits[pt_by_offset[offset]] = average_orbit_frames(list(untrimmed.values()))
    return orbits


def run_fit(campaign_slug: str, observables: tuple[str, ...], phase_weight: float, label: str):
    cache_hio_dir = CACHE_HIO_DIR_BY_CAMPAIGN[campaign_slug]
    campaign = campaign_by_slug(campaign_slug)
    model = build_model(sequence_file=SEQUENCE_FILE, campaign=campaign, scan_quads=False)
    momentum_accelerator = OptimiserPSB(
        ring=3, sequence_file=str(model.sequence_file), kinetic_energy=model.kinetic_energy
    )
    pt_by_offset = chroma_pt_by_rf_offset(campaign.chroma_file, RF_OFFSETS, momentum_accelerator)

    closed_orbits = closed_orbits_by_pt(campaign_slug, pt_by_offset)
    optics_dirs = {
        pt_by_offset[offset]: Path(cache_hio_dir) / f"{LABEL_BY_OFFSET[offset]}_undriven"
        for offset in RF_OFFSETS
    }
    frames = assemble_measured_optics(closed_orbits=closed_orbits, optics_dirs=optics_dirs, dispersion=None)

    if phase_weight != 1.0:
        for frame in frames.values():
            for col in ("mu1_var", "mu2_var"):
                if col in frame.columns:
                    frame[col] = frame[col] / phase_weight

    accelerator = OptimiserPSB(
        ring=3,
        sequence_file=str(model.sequence_file),
        errors={"bend": {"k0"}, "quad": {"k1"}},
        misalignments={"quad": {"dy", "tilt"}},
        group_quadrupoles_by_cell=True,
    )
    fitter = ClosedTwissFitter(
        accelerator=accelerator,
        sequence_config=SequenceConfig(magnet_range="$start/$end"),
        lm_config=LevenbergMarquardtConfig(
            max_iterations=30,
            gradient_converged_value=GRADIENT_CONVERGED_VALUE,
            initial_lambda=1e-3,
        ),
        prior_strengths=isotropic_prior_strengths(accelerator),
        measurements=frames,
        observables=observables,
        output_config=OutputConfig(
            tensorboard_root=Path("/tmp/phase_advance_experiment") / label / "tensorboard"
        ),
        machine_state=merge_machine_states(model.corrector_knobs, model.tune_knobs) or None,
        use_errors=True,
    )
    try:
        knobs, uncertainties = fitter.run()
    finally:
        fitter.close()
    print(f"{label}: {len(knobs)} knobs, diagnostics={dict(fitter.diagnostics)}", flush=True)
    return knobs, uncertainties


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, choices=sorted(CACHE_HIO_DIR_BY_CAMPAIGN))
    parser.add_argument("--observables", nargs="+", default=["x", "y"])
    parser.add_argument(
        "--phase-weight",
        type=float,
        default=1.0,
        help="Divide mu1_var/mu2_var by this factor (i.e. multiply phase's fit weight by it).",
    )
    parser.add_argument("--label", required=True, help="Output file stem under results/phase_advance_experiment/")
    args = parser.parse_args()

    knobs, uncertainties = run_fit(
        args.campaign, tuple(args.observables), args.phase_weight, args.label
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = RESULTS_DIR / f"{args.label}.json"
    output.write_text(json.dumps({"knobs": knobs, "uncertainties": uncertainties}, indent=2))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
