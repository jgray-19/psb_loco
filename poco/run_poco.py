"""POCO driver: fit PSB ring-3 magnet errors to the measured corrector-scan orbits.

One MAD-NG worker per (corrector, step) and, unless ``--batch-momenta``, per momentum.
``--fit-gains`` also fits a gain per BPM and plane and per corrector kick.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from adelmo.fitting.config import OutputConfig, SequenceConfig
from adelmo.machine.accelerators.psb import PSB
from adelmo.machine.accelerators.selection import add_selection_args, parse_selection
from adelmo.optimisers.levenberg_marquardt import LevenbergMarquardtConfig
from adelmo.poco.calibrated import CalibratedClosedOrbitFitter
from adelmo.poco.closed_orbit import ClosedOrbitFitter
from psb_md.closed_orbit_fitting import GRADIENT_CONVERGED_VALUE, PRIOR_STRENGTH
from psb_md.optimisation import write_optimisation_results

from loco_common.campaign import add_campaign_argument, campaign_by_slug
from loco_common.model import LocoModel, build_model
from phase_advance_constraint.series import build_phase_series
from poco.settings import CorrectorSetting, closed_orbit_series, scan_settings, standing_state

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from adelmo.fitting.results import FitResult
    from adelmo.poco.closed_orbit import ClosedOrbitSeries

logger = logging.getLogger(__name__)

#: Family name -> ((family, attribute) it frees, terminal name of its knobs, default 1-sigma width in a gain fit or ``None``).
#: Widths are in the knob's units: integrated gradient (1/m, ~1.5 % of a QFO), roll (rad). Only delta-visible families have one.
FAMILIES: dict[str, tuple[tuple[str, str], str, float | None]] = {
    "quadrupoles": (("quad", "k1"), "dk1l", 5e-3),
    "bends": (("bend", "k0"), "dk0l", None),
    "quad_dy": (("quad", "dy"), "dy", None),
    "quad_tilt": (("quad", "tilt"), "tilt", 5e-3),
    "quad_k0s": (("quad", "k0s"), "dk0sl", None),
    "quad_k1s": (("quad", "k1s"), "dk1sl", None),
}

#: Overrides of ``--prior-strength``. Tilt: the psb_sim seeds' truth correlation is 0.57 at 1e-2 and 0.59 at 1e-1.
DEFAULT_PRIORS = {"quad_tilt": 1e-2}

#: Fitted when ``--errors`` and ``--misalign`` are both absent.
DEFAULT_ERRORS = {"quad": {"k1"}}

#: 1-sigma gain priors: BPM readout is percent-level; the DHZ kicks are measured 0.71-0.93 of the model's.
SIGMA_BPM = 0.05
SIGMA_CORRECTOR = 0.3

INITIAL_LAMBDA = 1e-3


def selected_families(errors: Mapping, misalignments: Mapping) -> list[str]:
    """Names (keys of :data:`FAMILIES`) of the families *errors* and *misalignments* free."""
    selected = {
        (family, attribute)
        for selection in (errors, misalignments)
        for family, attributes in selection.items()
        for attribute in attributes
    }
    return [name for name, (selection, _, _) in FAMILIES.items() if selection in selected]


def warn_family_mismatch(absolute_planes: Sequence[str], families: Sequence[str]) -> None:
    """Warn when a family and the orbit that constrains it do not go together (bends: x; dy, tilt, skew terms: y)."""
    free = {"x": "bends" in families, "y": bool({"quad_dy", "quad_tilt", "quad_k0s", "quad_k1s"} & set(families))}
    for plane, is_free in free.items():
        if is_free and plane not in absolute_planes:
            logger.warning("%s-plane static-orbit knobs are free but that orbit is a delta: the prior decides them", plane)
        if plane in absolute_planes and not is_free:
            logger.warning("the %s orbit is absolute but no free knob can explain it: the gradients will absorb it", plane)


def run(
    settings: Sequence[CorrectorSetting],
    model: LocoModel,
    *,
    errors: Mapping[str, set[str]] | None = None,
    misalignments: Mapping[str, set[str]] | None = None,
    absolute_planes: Sequence[str] = (),
    batch_momenta: bool = False,
    group_quadrupoles_by_cell: bool = False,
    fit_gains: bool = False,
    sigma_bpm: float = SIGMA_BPM,
    sigma_corrector: float = SIGMA_CORRECTOR,
    knob_sigmas: Mapping[str, float] | None = None,
    prior_strength: float = PRIOR_STRENGTH,
    priors: Mapping[str, float] | None = None,
    max_iterations: int = 20,
    initial_knobs: Mapping[str, float] | None = None,
    extra_series: Sequence[ClosedOrbitSeries] = (),
    output_path: Path = Path("results/poco"),
) -> tuple[FitResult, list]:
    """Fit the selected knob families; return the result and every accepted iteration's ``(knobs, loss)``.

    *priors* override *prior_strength* per family; *knob_sigmas* override each family's default width in a gain fit.
    """
    if errors is None and misalignments is None:
        errors = DEFAULT_ERRORS
    errors = {family: set(attributes) for family, attributes in (errors or {}).items() if attributes}
    misalignments = {family: set(attributes) for family, attributes in (misalignments or {}).items() if attributes}
    families = selected_families(errors, misalignments)
    if not families:
        raise ValueError("No knob family enabled: there is nothing to fit")
    standing = standing_state(model, absolute_planes)
    series = closed_orbit_series(
        [setting for setting in settings if setting.knob or not fit_gains],  # an untrimmed orbit has no kick to calibrate
        standing,
        absolute_planes=absolute_planes,
        batch_momenta=batch_momenta,
    ) + list(extra_series)
    # Per family: k1, k0 and dy differ in unit, and a global median(diag H) would move the k1 knee.
    # The fitter wants every optimised family named, or no prior at all.
    prior_strengths = {FAMILIES[name][1]: float((priors or {}).get(name, prior_strength)) for name in families}
    gain_options = {}
    if fit_gains:
        if absolute_planes:
            raise ValueError("Gain fits need delta orbits: an absolute plane carries the standing correctors' kicks")
        widths = {name: (knob_sigmas or {}).get(name, FAMILIES[name][2]) for name in families}
        if missing := [name for name, width in widths.items() if width is None]:
            raise ValueError(f"A gain fit needs a width for {missing}: pass --knob-sigma FAMILY=VALUE")
        gain_options = {
            "sigma_bpm": sigma_bpm,
            "sigma_corrector": sigma_corrector,
            "knob_sigmas": {FAMILIES[name][1]: width for name, width in widths.items()},
            "kick_prefix": f"kbr{model.ring}",
        }
    fitter = (CalibratedClosedOrbitFitter if fit_gains else ClosedOrbitFitter)(
        accelerator=PSB(
            ring=model.ring,
            sequence_file=model.sequence_file,
            kinetic_energy=model.kinetic_energy,
            errors=errors,
            misalignments=misalignments,
            group_quadrupoles_by_cell=group_quadrupoles_by_cell,
        ),
        sequence_config=SequenceConfig(magnet_range="$start/$end"),
        series=series,
        machine_state=standing,
        lm_config=LevenbergMarquardtConfig(
            max_iterations=max_iterations,
            gradient_converged_value=GRADIENT_CONVERGED_VALUE,
            initial_lambda=INITIAL_LAMBDA,
        ),
        initial_knob_strengths=dict(initial_knobs) if initial_knobs else None,
        prior_strengths=prior_strengths,
        output_config=OutputConfig(tensorboard_root=output_path / "tensorboard"),
        **gain_options,
    )
    try:
        return fitter.run(), fitter.history
    finally:
        fitter.close()  # otherwise MAD's ``__del__`` tears the pipe down mid-message at exit


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_campaign_argument(parser)
    parser.add_argument("--sequence-file", type=Path, help="Default: the vendored ring-3 sequence.")
    parser.add_argument("--output", type=Path, default=Path("results/poco"))
    parser.add_argument("--correctors", nargs="+", help="Default: every corrector in the scan.")
    parser.add_argument(
        "--offsets", type=float, nargs="+",
        help="Corrector steps to keep (write negatives in decimal: -0.0001, not -1e-4). Default: all.",
    )
    parser.add_argument(
        "--rf-offsets", type=float, nargs="+", default=[0.0],
        help="RF-steering offsets (mm). More than nominal adds chroma-calibrated momenta and a dispersion orbit each.",
    )
    parser.add_argument(
        "--batch-momenta", action="store_true",
        help="One MAD-NG process per trim, fitting all its momenta, rather than per (trim, momentum).",
    )
    parser.add_argument(
        "--absolute-planes", nargs="+", choices=("x", "y"), default=[],
        help="Planes whose closed orbit is not referred to the nominal one (pair with --errors bend:k0 / --misalign quad:dy).",
    )
    add_selection_args(parser, accelerator=PSB, errors_default=["quad:k1"])
    parser.add_argument(
        "--group-quadrupoles-by-cell", action="store_true",
        help="One knob for the two QFO of each cell (32 knobs per family, not 48).",
    )
    parser.add_argument(
        "--fit-gains", action="store_true",
        help="Also fit a gain per BPM and plane and per corrector kick (delta orbits only).",
    )
    parser.add_argument("--sigma-bpm", type=float, default=SIGMA_BPM, help="1-sigma prior on a BPM gain.")
    parser.add_argument("--sigma-corrector", type=float, default=SIGMA_CORRECTOR, help="1-sigma prior on a corrector gain.")
    parser.add_argument(
        "--knob-sigma", action="append", default=[], metavar="FAMILY=VALUE",
        help=f"1-sigma width of a family's knobs in a gain fit; one of {sorted(FAMILIES)}.",
    )
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument(
        "--prior-strength", type=float, default=PRIOR_STRENGTH,
        help="Tikhonov prior, as a multiple of median(diag H); not used by --fit-gains.",
    )
    parser.add_argument(
        "--prior", action="append", default=[], metavar="FAMILY=VALUE",
        help=f"Override --prior-strength for one of {sorted(FAMILIES)}.",
    )
    parser.add_argument("--initial-knobs", type=Path, help="knobs.csv of a fit to start from.")
    parser.add_argument(
        "--phase-constraint", action="store_true",
        help="Add a phase-only series per RF offset (docs/studies/phase-advance-constraint.md).",
    )
    parser.add_argument("--phase-weight", type=float, default=1.0, help="Multiplies the phase constraint's weight.")
    return parser.parse_args(argv)


def family_values(items: Sequence[str]) -> dict[str, float]:
    """``["quad_tilt=1e-2"]`` -> ``{"quad_tilt": 0.01}``."""
    return {name: float(value) for name, value in (item.split("=") for item in items)}


def write_results(
    output: Path, args: argparse.Namespace, result: FitResult, history: list, settings: Sequence[CorrectorSetting]
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    write_optimisation_results(output / "knobs.csv", result.knobs, result.uncertainties, stage_name="loco_poco")
    (output / "history.json").write_text(json.dumps([{"knobs": knobs, "loss": loss} for knobs, loss in history]))
    if result.extra:
        pd.Series(result.extra, name="value").rename_axis("parameter").to_csv(output / "gains.csv")
    diagnostics = result.diagnostics
    summary = {
        # If MAD-NG rejects every trial state, the seed vector comes back without an error.
        "status": "complete" if diagnostics and (diagnostics.accepted_evaluations or 0) >= 2 else "no_valid_step",
        "diagnostics": asdict(diagnostics) if diagnostics else None,
        "n_settings": len(settings),
        "momenta": {f"{offset:g}": pt for offset, pt in sorted({(s.rf_offset, s.pt) for s in settings})},
        "args": vars(args),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, default=str))


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    errors, misalignments = parse_selection(args.errors), parse_selection(args.misalign)
    absolute_planes = tuple(dict.fromkeys(args.absolute_planes))
    warn_family_mismatch(absolute_planes, selected_families(errors, misalignments))
    if absolute_planes and len(args.rf_offsets) > 1 and not args.initial_knobs:
        raise SystemExit("Multi-momentum absolute fits need --initial-knobs from the nominal-momentum absolute fit.")

    campaign = campaign_by_slug(args.campaign)
    model = build_model(campaign=campaign, sequence_file=args.sequence_file)
    settings = scan_settings(
        campaign,
        model,
        args.rf_offsets,
        absolute_planes=absolute_planes,
        correctors=args.correctors,
        offsets=args.offsets,
    )
    if not settings:
        raise SystemExit("No corrector settings selected.")
    extra_series = []
    if args.phase_constraint:
        if len(args.rf_offsets) < 2:
            raise SystemExit("--phase-constraint needs more than one --rf-offsets entry")
        extra_series = build_phase_series(
            campaign, args.rf_offsets, {s.rf_offset: s.pt for s in settings}, phase_weight=args.phase_weight
        )
    initial_knobs = (
        pd.read_csv(args.initial_knobs).set_index("knob")["value"].astype(float).to_dict()
        if args.initial_knobs
        else None
    )
    result, history = run(
        settings,
        model,
        errors=errors,
        misalignments=misalignments,
        absolute_planes=absolute_planes,
        batch_momenta=args.batch_momenta,
        group_quadrupoles_by_cell=args.group_quadrupoles_by_cell,
        fit_gains=args.fit_gains,
        sigma_bpm=args.sigma_bpm,
        sigma_corrector=args.sigma_corrector,
        knob_sigmas=family_values(args.knob_sigma),
        prior_strength=args.prior_strength,
        priors={**DEFAULT_PRIORS, **family_values(args.prior)},
        max_iterations=args.max_iterations,
        initial_knobs=initial_knobs,
        extra_series=extra_series,
        output_path=args.output,
    )
    write_results(args.output, args, result, history, settings)
    logger.info("POCO done: %d knobs from %d settings", len(result.knobs), len(settings))


if __name__ == "__main__":
    main()
