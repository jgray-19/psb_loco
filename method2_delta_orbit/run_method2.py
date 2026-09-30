"""Method 2 driver: fit quadrupole ``k1`` to measured delta closed orbits.

One worker per (corrector, step), and per momentum with ``--rf-offsets``;
``--batch-momenta`` fits all momenta of a trim in one process.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
from aba_optimiser.accelerators.selection import add_selection_args, parse_selection
from aba_optimiser.training.config import OutputConfig, SequenceConfig
from aba_optimiser.training_closed_twiss import (
    ClosedOrbitFitter,
    ClosedOrbitMeasurement,
    ClosedOrbitSeries,
    LevenbergMarquardtConfig,
)
from psb_md.closed_orbit_fitting import GRADIENT_CONVERGED_VALUE, PRIOR_STRENGTH
from psb_md.optimisation import write_optimisation_results

from loco_common.campaign import (
    Campaign,
    add_campaign_argument,
    campaign_by_slug,
)
from loco_common.measured_response import (
    average_orbit_frames,
    cached_orbits,
    cached_scan,
    global_reference_orbit,
    measured_orbits,
    pooled_intershot_noise,
    subtract_reference,
)
from loco_common.model import (
    LocoModel,
    build_model,
    model_twiss,
)
from loco_common.momentum import compare_momentum_calibrations
from loco_common.naming import lsa_k_to_rad, lsa_to_knob
from phase_advance_constraint.series import build_phase_series

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


#: Untrimmed-orbit target labels; not LSA names, never pass to ``lsa_to_knob``.
STATIC_ORBIT = "(static orbit)"
DISPERSION = "(dispersion)"
UNTRIMMED_SETTINGS: tuple[str, ...] = (STATIC_ORBIT, DISPERSION)

PRIOR_SUFFIXES: dict[str, str] = {
    "quadrupoles": "dk1l",
    "bends": "dk0l",
    "quad_dy": "dy",
    "quad_tilt": "tilt",
    "quad_k0s": "dk0sl",
    "quad_k1s": "dk1sl",
}

#: The (family, attribute) selection each :data:`PRIOR_SUFFIXES` name stands for.
PRIOR_FAMILIES: dict[str, tuple[str, str]] = {
    "quadrupoles": ("quad", "k1"),
    "bends": ("bend", "k0"),
    "quad_dy": ("quad", "dy"),
    "quad_tilt": ("quad", "tilt"),
    "quad_k0s": ("quad", "k0s"),
    "quad_k1s": ("quad", "k1s"),
}

#: Tilt prior strength (x median(diag H) of the tilt block); psb_sim seeds 1-3 tilt correlation
#: with truth: 0.15 at 1e-4, 0.25 at 1e-3, 0.57 at 1e-2, 0.59 at 1e-1, 0.49 at 1.
TILT_PRIOR_STRENGTH = 1e-2

#: The fit this script runs when no selection is given: quadrupole gradients.
DEFAULT_ERRORS: dict[str, set[str]] = {"quad": {"k1"}}


def _selected(
    errors: Mapping[str, Iterable[str]], misalignments: Mapping[str, Iterable[str]]
) -> set[tuple[str, str]]:
    return {
        (family, attribute)
        for selection in (errors, misalignments)
        for family, attributes in selection.items()
        for attribute in attributes
    }


def family_selection(args) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Turn ``--errors`` / ``--misalign`` into ``errors`` / ``misalignments`` selections."""
    return parse_selection(args.errors), parse_selection(args.misalign)


@dataclass
class CorrectorSetting:
    """One measured orbit and the model state at which it must be evaluated."""

    corrector: str
    knob: str
    offset_k: float
    orbit: pd.DataFrame = field(repr=False)
    dk: float = 0.0
    nominal: float = 0.0
    rf_offset: float = 0.0
    pt: float = 0.0
    reference_pt: float = 0.0
    orbit_pt: float | None = None
    chroma_pt: float | None = None
    absolute_planes: tuple[str, ...] = ()
    corrector_baseline: str = "zero"

    @property
    def label(self) -> str:
        return f"{self.corrector}@{self.offset_k:+g},rf{self.rf_offset:+g}"

#: ``zero``: every corrector at zero, the trimmed one at ``dk`` (quadrupole fits on delta orbits;
#: standing correctors move a delta orbit by only 1e-3 relative).
#: ``machine``: every corrector at its standing value, the trimmed one at ``nominal + dk``
#: (bends / quad dy fits on the absolute orbit).
CORRECTOR_BASELINES: tuple[str, ...] = ("zero", "machine")


def corrector_baseline_knobs(model: LocoModel, baseline: str) -> dict[str, float]:
    """Standing corrector settings for *baseline*; ``zero`` is explicit, not an empty dict."""
    if baseline not in CORRECTOR_BASELINES:
        raise ValueError(f"Unknown corrector baseline {baseline!r}; expected {CORRECTOR_BASELINES}")
    if baseline == "machine":
        return dict(model.corrector_knobs)
    return dict.fromkeys(model.corrector_knobs, 0.0)


def default_corrector_baseline(absolute_planes: tuple[str, ...]) -> str:
    """``machine`` once any plane keeps its closed orbit, ``zero`` otherwise."""
    return "machine" if absolute_planes else "zero"


def build_settings(
    orbits: dict[tuple[str, float], pd.DataFrame],
    model: LocoModel,
    *,
    rf_offset: float = 0.0,
    pt: float = 0.0,
    orbit_pt: float | None = None,
    chroma_pt: float | None = None,
    correctors: list[str] | None = None,
    offsets: list[float] | None = None,
    absolute_planes: tuple[str, ...] = (),
    corrector_baseline: str | None = None,
) -> list[CorrectorSetting]:
    """Turn measured delta orbits into one :class:`CorrectorSetting` per worker."""
    baseline = corrector_baseline or default_corrector_baseline(absolute_planes)
    standing = corrector_baseline_knobs(model, baseline)
    settings = []
    for (corrector, offset_k), orbit in sorted(orbits.items()):
        untrimmed = corrector in UNTRIMMED_SETTINGS
        # Untrimmed orbits ignore the --correctors/--offsets subsets.
        if not untrimmed and correctors and corrector not in correctors:
            continue
        if not untrimmed and offsets and not any(np.isclose(offset_k, o) for o in offsets):
            continue
        # Any knob will do for an untrimmed setting: dk = 0 leaves it at ``nominal``.
        knob = next(iter(model.corrector_knobs)) if untrimmed else lsa_to_knob(corrector)
        settings.append(
            CorrectorSetting(
                corrector=corrector,
                knob=knob,
                offset_k=float(offset_k),
                orbit=orbit,
                dk=0.0 if untrimmed else float(offset_k) * lsa_k_to_rad(corrector),
                nominal=float(standing.get(knob, 0.0)),
                corrector_baseline=baseline,
                rf_offset=rf_offset,
                pt=pt,
                orbit_pt=orbit_pt,
                chroma_pt=chroma_pt,
                absolute_planes=absolute_planes,
            )
        )
    return settings


def drop_zero_step_duplicates(
    orbits: dict[tuple[str, float], pd.DataFrame],
) -> dict[tuple[str, float], pd.DataFrame]:
    """Drop the per-corrector untrimmed acquisitions; the averaged ``(dispersion)`` setting replaces them."""
    return {key: frame for key, frame in orbits.items() if key[1] != 0.0}


def average_zero_step(
    orbits: dict[tuple[str, float], pd.DataFrame],
) -> dict[tuple[str, float], pd.DataFrame]:
    """Average one RF setting's untrimmed acquisitions into a single static-orbit target (absolute mode)."""
    zero = [frame for (_, offset), frame in orbits.items() if offset == 0.0]
    kept = {key: frame for key, frame in orbits.items() if key[1] != 0.0}
    if not zero:
        return kept
    kept[(STATIC_ORBIT, 0.0)] = average_orbit_frames(zero)
    return kept


def build_multi_pt_settings(
    model: LocoModel,
    rf_offsets: list[float],
    twiss: pd.DataFrame,
    *,
    dispersion_workers: bool = True,
    zero_step_duplicates: bool = False,
    absolute_planes: tuple[str, ...] = (),
    corrector_baseline: str | None = None,
    campaign: Campaign,
    **kwargs,
) -> list[CorrectorSetting]:
    """Settings across several RF-steering offsets, each at its chroma-calibrated ``pt``.

    The orbit-projected ``pt`` is only a logged cross-check (``orbit_pt``).
    The twelve untrimmed acquisitions per RF setting enter as one averaged
    ``(dispersion)`` setting; ``zero_step_duplicates`` restores them for comparison only.
    """
    from loco_common.momentum import chroma_pt_by_rf_offset, estimate_pt_by_rf_offset

    if 0.0 not in rf_offsets:
        raise ValueError("The nominal-RF (0 mm) setting is required as the momentum reference")
    baseline = corrector_baseline or default_corrector_baseline(absolute_planes)
    standing = corrector_baseline_knobs(model, baseline)
    points, orbit_by_path = cached_scan(campaign=campaign)
    intershot = pooled_intershot_noise(points, orbit_by_path)
    absolute = {}
    for offset in rf_offsets:
        untrimmed = {
            key: frame
            for key, frame in measured_orbits(
                offset,
                points=points,
                orbit_by_path=orbit_by_path,
                delta=False,
                intershot=intershot,
            ).items()
            if key[1] == 0.0
        }
        if not untrimmed:
            raise ValueError(f"RF offset {offset:+g} mm has no untrimmed-corrector acquisition")
        # Not sum/len: that would average ERRX/ERRY instead of dividing by sqrt(N).
        absolute[offset] = average_orbit_frames(list(untrimmed.values()))
    orbit_momenta = estimate_pt_by_rf_offset(absolute, twiss)
    momentum_accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    chroma_momenta = chroma_pt_by_rf_offset(
        campaign.chroma_file, rf_offsets, momentum_accelerator
    )
    momenta = chroma_momenta
    differences = compare_momentum_calibrations(chroma_momenta, orbit_momenta)
    logger.warning(
        "Momentum calibration comparison (orbit - RF/chroma): %s",
        ", ".join(f"{offset:+g} mm {delta:+.4e}" for offset, delta in differences.items()),
    )
    logger.info(
        "Using chroma momentum calibration: %s",
        ", ".join(
            f"{offset:+g} mm {value:+.4e}" for offset, value in sorted(momenta.items())
        ),
    )
    reference = global_reference_orbit(points, orbit_by_path, intershot)
    settings: list[CorrectorSetting] = []
    for offset in rf_offsets:
        orbits = measured_orbits(
            offset,
            points=points,
            orbit_by_path=orbit_by_path,
            absolute_planes=absolute_planes,
            reference=reference,
            intershot=intershot,
        )
        if not zero_step_duplicates:
            orbits = drop_zero_step_duplicates(orbits)
        settings += build_settings(
            orbits,
            model,
            rf_offset=offset,
            pt=momenta[offset],
            absolute_planes=absolute_planes,
            corrector_baseline=baseline,
            orbit_pt=orbit_momenta[offset],
            chroma_pt=chroma_momenta[offset],
            **kwargs,
        )
        if not dispersion_workers or (offset == 0.0 and not absolute_planes):
            # Zero by construction at nominal RF unless a plane is absolute.
            continue
        # Untrimmed orbit minus the global reference: this momentum's dispersion orbit.
        settings.append(
            CorrectorSetting(
                corrector=DISPERSION if offset != 0.0 else STATIC_ORBIT,
                # ``nominal`` must be the baseline value: an absolute plane has no reference to cancel it.
                knob=next(iter(model.corrector_knobs)),
                offset_k=0.0,
                orbit=subtract_reference(absolute[offset], reference, absolute_planes),
                dk=0.0,
                nominal=float(standing.get(next(iter(model.corrector_knobs)), 0.0)),
                corrector_baseline=baseline,
                rf_offset=offset,
                pt=momenta[offset],
                orbit_pt=orbit_momenta[offset],
                chroma_pt=chroma_momenta[offset],
                absolute_planes=absolute_planes,
            )
        )
    return settings


def closed_orbit_series(
    settings: list[CorrectorSetting], *, batch_momenta: bool
) -> list[ClosedOrbitSeries]:
    """Translate PSB settings to independent upstream measurement series."""
    usable = [
        setting
        for setting in settings
        if not (
            setting.dk == 0.0
            and setting.pt == setting.reference_pt
            and not setting.absolute_planes
        )
    ]
    if len(usable) != len(settings):
        logger.info(
            "Dropped %d zero-trim reference-state target(s) with no orbit signal",
            len(settings) - len(usable),
        )
    if not usable:
        raise ValueError("Every closed-orbit target is a reference state with no signal")

    grouped: dict[tuple, list[CorrectorSetting]] = {}
    if batch_momenta:
        for setting in usable:
            key = (
                setting.corrector,
                setting.knob,
                setting.dk,
                setting.nominal,
                setting.absolute_planes,
            )
            grouped.setdefault(key, []).append(setting)
    else:
        grouped = {(index,): [setting] for index, setting in enumerate(usable)}

    result = []
    for group in grouped.values():
        group.sort(key=lambda setting: setting.pt)
        first = group[0]
        result.append(
            ClosedOrbitSeries(
                measurements=tuple(
                    ClosedOrbitMeasurement(
                        orbit=setting.orbit,
                        pt=setting.pt,
                        reference_pt=setting.reference_pt,
                    )
                    for setting in group
                ),
                control_knob=first.knob if first.dk != 0.0 else None,
                control_nominal=first.nominal,
                control_delta=first.dk,
                absolute_planes=first.absolute_planes,
                label=first.label,
            )
        )
    return result


def prior_strengths_by_suffix(
    *,
    default: float,
    overrides: dict[str, float],
    errors: Mapping[str, Iterable[str]],
    misalignments: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, float] | None:
    """Scale priors independently for enabled families with different units."""
    selected = _selected(errors, misalignments or {})
    families = [
        family for family, selection in PRIOR_FAMILIES.items() if selection in selected
    ]
    if len(families) == 1 and not overrides:
        return None
    return {
        PRIOR_SUFFIXES[family]: float(overrides.get(family, default))
        for family in families
    }


def run(
    settings: list[CorrectorSetting],
    model: LocoModel,
    *,
    max_iterations: int = 20,
    initial_lambda: float = 1e-3,
    batch_momenta: bool = False,
    prior_strength: float = PRIOR_STRENGTH,
    prior_strengths: dict[str, float] | None = None,
    errors: Mapping[str, Iterable[str]] | None = None,
    misalignments: Mapping[str, Iterable[str]] | None = None,
    group_quadrupoles_by_cell: bool = False,
    initial_knob_strengths: dict[str, float] | None = None,
    output_path: Path = Path("results/method2"),
    extra_series: list[ClosedOrbitSeries] | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, object]]:
    """Run the summed-gradient delta-orbit fit over the selected knob families.

    The model sits on the corrector baseline the settings were built with.
    """
    if errors is None and misalignments is None:
        errors = DEFAULT_ERRORS
    errors = {family: set(attrs) for family, attrs in (errors or {}).items() if attrs}
    misalignments = {
        family: set(attrs) for family, attrs in (misalignments or {}).items() if attrs
    }
    if not (errors or misalignments):
        raise ValueError("No knob family enabled: there is nothing to fit")
    baselines = {setting.corrector_baseline for setting in settings}
    if len(baselines) > 1:
        raise ValueError(
            f"Every setting must share one corrector baseline, got {sorted(baselines)}"
        )
    standing = corrector_baseline_knobs(model, baselines.pop())
    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
        errors=errors,
        misalignments=misalignments,
        group_quadrupoles_by_cell=group_quadrupoles_by_cell,
    )
    family_priors = prior_strengths_by_suffix(
        default=prior_strength,
        overrides=prior_strengths or {},
        errors=errors,
        misalignments=misalignments,
    )
    series = closed_orbit_series(settings, batch_momenta=batch_momenta)
    if extra_series:
        series += list(extra_series)
    fitter = ClosedOrbitFitter(
        accelerator=accelerator,
        sequence_config=SequenceConfig(magnet_range="$start/$end"),
        series=series,
        lm_config=LevenbergMarquardtConfig(
            max_iterations=max_iterations,
            gradient_converged_value=GRADIENT_CONVERGED_VALUE,
            initial_lambda=initial_lambda,
        ),
        initial_knob_strengths=initial_knob_strengths,
        # Per family: k1, k0 and dy differ in unit, and a global median(diag H) would move the k1 knee.
        prior_strengths=family_priors,
        tune_knobs=model.tune_knobs or None,
        corrector_knobs=standing or None,
        output_config=OutputConfig(tensorboard_root=output_path / "tensorboard"),
    )
    try:
        knobs, uncertainties = fitter.run()
        return knobs, uncertainties, dict(fitter.diagnostics)
    finally:
        # Otherwise MAD's ``__del__`` tears the pipe down mid-message at exit.
        mad_iface = getattr(fitter.config_manager, "mad_iface", None)
        if mad_iface is not None:
            mad_iface.close()


def warn_family_mismatch(absolute_planes: tuple[str, ...], args) -> None:
    """Warn when a knob family and the plane that constrains it are not paired."""
    # Tilt, k0s and k1s are skew sources and sit with dy in the vertical plane.
    selected = _selected(*family_selection(args))
    vertical = bool(
        selected & {("quad", "dy"), ("quad", "tilt"), ("quad", "k0s"), ("quad", "k1s")}
    )
    for plane, flag, family in (
        ("x", ("bend", "k0") in selected, "bends"),
        ("y", vertical, "quadrupole dy/tilt/k0s/k1s"),
    ):
        if flag and plane not in absolute_planes:
            logger.warning(
                "%s are free but the %s plane is a delta: delta orbits barely "
                "constrain that family, so the prior will decide it",
                family,
                plane,
            )
        if plane in absolute_planes and not flag:
            logger.warning(
                "the %s plane is absolute but %s are fixed: the static orbit has "
                "been handed to the fit with nothing that can explain it, so the "
                "gradients will absorb it",
                plane,
                family,
            )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-offset", type=float, default=0.0)
    parser.add_argument(
        "--rf-offsets",
        type=float,
        nargs="+",
        default=None,
        help=(
            "Enable the multi-momentum mode over these RF-steering offsets (mm). "
            "Their pt calibration is always the RF-derived Dp/p measured by the "
            "chroma scan at the same radial plateaus, referenced to the 0 mm "
            "orbit as exactly pt=0."
        ),
    )
    parser.add_argument("--correctors", nargs="+", default=None)
    parser.add_argument(
        "--no-dispersion-workers",
        action="store_true",
        help=(
            "In the multi-momentum mode, drop the one setting per RF offset that "
            "fits the untrimmed (pure dispersion) orbit. With the duplicates now "
            "averaged into it by default, this removes every zero-step "
            "acquisition from the fit, which is what makes it a clean test of "
            "whether the model's suspect dispersion is driving the answer."
        ),
    )
    parser.add_argument("--offsets", type=float, nargs="+", default=None)
    parser.add_argument(
        "--keep-zero-step-duplicates",
        action="store_true",
        help=(
            "In the multi-momentum mode, pass each RF setting's twelve untrimmed "
            "acquisitions individually instead of as the one averaged dispersion "
            "setting. They are twelve recordings of the same machine state, so "
            "this weights that orbit twelvefold; it is for comparison, not for "
            "running a fit."
        ),
    )
    parser.add_argument(
        "--phase-constraint",
        action="store_true",
        help=(
            "Add one plain-twiss, no-corrector series per RF offset, whose residual "
            "is only the BPM-to-BPM phase advance (mu1/mu2) -- see "
            "docs/studies/phase-advance-constraint.md and phase_advance_constraint/. "
            "Requires --rf-offsets and the campaign's optics at each of them "
            "(scripts/measured_optics.py --optics-folders all)."
        ),
    )
    parser.add_argument(
        "--phase-weight",
        type=float,
        default=1.0,
        help=(
            "Multiply the phase constraint's fit weight by this factor (divides "
            "mu1_var/mu2_var). At 1.0 phase's measurement SNR is far looser than "
            "the closed orbit's, so it is swamped by the ~140 orbit corrector-trim "
            "settings with no visible effect; see --phase-constraint's help."
        ),
    )
    parser.add_argument(
        "--batch-momenta",
        action="store_true",
        help=(
            "Fit every momentum of a corrector trim inside one MAD-NG process "
            "instead of one process per (trim, momentum). The objective is "
            "unchanged; the process count drops by the number of RF settings, "
            "which is what lets the full scan run without exhausting file "
            "descriptors."
        ),
    )
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument(
        "--prior-strength",
        type=float,
        default=PRIOR_STRENGTH,
        help=(
            "Isotropic Tikhonov prior on the knobs, as a multiple of "
            "median(diag H). The default is psb_md's and is not a tuning knob: "
            "the prior's shape and scale are what pick the answer out of a large "
            "null space. Provided for sensitivity studies."
        ),
    )
    parser.add_argument(
        "--absolute-planes",
        nargs="+",
        choices=("x", "y"),
        default=[],
        help=(
            "Planes whose closed orbit is NOT referred to the global reference "
            "orbit, so the target is the machine's absolute orbit. The static "
            "orbit is generated by dipole errors (x) and quadrupole vertical "
            "misalignments (y), so pair this with --errors bend:k0 and/or "
            "--misalign quad:dy; on its own it hands the fit an orbit only the "
            "gradients can absorb."
        ),
    )
    add_selection_args(parser, accelerator=OptimiserPSB, errors_default=["quad:k1"])
    parser.add_argument(
        "--group-quadrupoles-by-cell",
        action="store_true",
        help=(
            "Use one shared knob for the two QFO magnets in each PSB cell, "
            "while each QDE remains independent. Every enabled per-quadrupole "
            "family therefore has 32 knobs instead of 48. Grouping happens in "
            "MAD-NG when the knobs are created, so the optimiser works directly "
            "in the reduced parameter space."
        ),
    )
    parser.add_argument(
        "--prior-strength-bends",
        type=float,
        default=None,
        help="Prior strength for the bends; defaults to --prior-strength.",
    )
    parser.add_argument(
        "--prior-strength-quad-tilt",
        type=float,
        default=TILT_PRIOR_STRENGTH,
        help="Prior strength for the quadrupole tilts (default: TILT_PRIOR_STRENGTH = 1e-2).",
    )
    parser.add_argument(
        "--prior-strength-quad-dy",
        type=float,
        default=None,
        help="Prior strength for the quadrupole dy; defaults to --prior-strength.",
    )
    parser.add_argument(
        "--prior-strength-quad-k0s",
        type=float,
        default=None,
        help="Prior strength for the quadrupole k0s; defaults to --prior-strength.",
    )
    parser.add_argument(
        "--prior-strength-quad-k1s",
        type=float,
        default=None,
        help="Prior strength for the quadrupole k1s; defaults to --prior-strength.",
    )
    parser.add_argument(
        "--corrector-baseline",
        choices=CORRECTOR_BASELINES,
        default=None,
        help=(
            "What the untrimmed correctors are set to in the model. Defaults to "
            "'zero' for a delta fit and 'machine' once any plane is absolute, "
            "which is the pairing the physics forces: a subtracted plane cannot "
            "see the standing correctors (a delta orbit moves by 1e-3 when every "
            "one of them changes), while an absolute plane cannot do without "
            "them, since their kicks are a large part of the orbit being fitted."
        ),
    )
    parser.add_argument("--sequence-file", type=Path, default=None)
    parser.add_argument(
        "--initial-knobs",
        type=Path,
        default=None,
        help="Complete physical knob CSV from the nominal-momentum warm-start fit.",
    )
    add_campaign_argument(parser)
    parser.add_argument("--output", type=Path, default=Path("results/method2"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    absolute_planes = tuple(dict.fromkeys(args.absolute_planes))
    baseline = args.corrector_baseline or default_corrector_baseline(absolute_planes)
    warn_family_mismatch(absolute_planes, args)
    if absolute_planes and baseline == "zero":
        logger.warning(
            "An absolute plane is fitted against a model with every corrector at "
            "zero: their kicks (up to 1.8e-3 rad) will be attributed to the bends"
        )
    logger.info(
        "Corrector baseline: %s; absolute planes: %s",
        baseline,
        ", ".join(absolute_planes) or "(none, pure delta fit)",
    )

    campaign = campaign_by_slug(args.campaign)
    logger.info("Campaign: %s (%s)", campaign.label, campaign.measurements_path)
    model = build_model(sequence_file=args.sequence_file, campaign=campaign)
    subset = {"correctors": args.correctors, "offsets": args.offsets}
    if args.rf_offsets:
        settings = build_multi_pt_settings(
            model,
            args.rf_offsets,
            model_twiss(model, chrom=True),
            dispersion_workers=not args.no_dispersion_workers,
            zero_step_duplicates=args.keep_zero_step_duplicates,
            absolute_planes=absolute_planes,
            corrector_baseline=baseline,
            campaign=campaign,
            **subset,
        )
    elif absolute_planes:
        # Not cached_orbits: its parquet holds fully-subtracted orbits and cannot represent this mode.
        orbits = average_zero_step(
            measured_orbits(
                args.rf_offset,
                absolute_planes=absolute_planes,
                campaign=campaign,
            )
        )
        settings = build_settings(
            orbits,
            model,
            rf_offset=args.rf_offset,
            absolute_planes=absolute_planes,
            corrector_baseline=baseline,
            **subset,
        )
    else:
        settings = build_settings(
            cached_orbits(args.rf_offset, campaign=campaign),
            model,
            rf_offset=args.rf_offset,
            corrector_baseline=baseline,
            **subset,
        )
    if not settings:
        raise SystemExit("No corrector settings selected.")

    extra_series = None
    if args.phase_constraint:
        if not args.rf_offsets:
            raise SystemExit(
                "--phase-constraint requires --rf-offsets (the multi-momentum mode)"
            )
        momenta = {setting.rf_offset: setting.pt for setting in settings}
        extra_series = build_phase_series(
            campaign, args.rf_offsets, momenta, phase_weight=args.phase_weight
        )
        logger.info(
            "Phase constraint: %d phase-only series added (weight x%g)",
            len(extra_series),
            args.phase_weight,
        )

    if absolute_planes and args.rf_offsets and args.initial_knobs is None:
        raise SystemExit(
            "Multi-momentum absolute fits require --initial-knobs from the matching "
            "nominal-momentum absolute fit."
        )
    initial_knob_strengths = None
    if args.initial_knobs is not None:
        import pandas as pd

        initial_table = pd.read_csv(args.initial_knobs)
        required_columns = {"knob", "value"}
        if not required_columns.issubset(initial_table.columns):
            raise ValueError(
                f"{args.initial_knobs} must contain columns {sorted(required_columns)}"
            )
        initial_knob_strengths = dict(
            zip(initial_table["knob"], initial_table["value"].astype(float), strict=True)
        )

    prior_strengths = {
        "bends": args.prior_strength_bends,
        "quad_dy": args.prior_strength_quad_dy,
        "quad_tilt": args.prior_strength_quad_tilt,
        "quad_k0s": args.prior_strength_quad_k0s,
        "quad_k1s": args.prior_strength_quad_k1s,
    }
    prior_strengths = {k: v for k, v in prior_strengths.items() if v is not None}

    errors, misalignments = family_selection(args)
    fitted_knobs, fitted_uncertainties, diagnostics = run(
        settings,
        model,
        max_iterations=args.max_iterations,
        batch_momenta=args.batch_momenta,
        prior_strength=args.prior_strength,
        prior_strengths=prior_strengths,
        errors=errors,
        misalignments=misalignments,
        group_quadrupoles_by_cell=args.group_quadrupoles_by_cell,
        initial_knob_strengths=initial_knob_strengths,
        output_path=args.output,
        extra_series=extra_series,
    )

    knobs, uncertainties = fitted_knobs, fitted_uncertainties
    args.output.mkdir(parents=True, exist_ok=True)
    write_optimisation_results(
        args.output / "knobs.csv", knobs, uncertainties, stage_name="loco_method2"
    )
    summary = {
        "method": "delta_orbit",
        # If MAD-NG rejects every trial state, upstream returns the seed vector without raising.
        "status": (
            "complete"
            if int(diagnostics.get("accepted_evaluations", 0)) >= 2
            else "no_valid_step"
        ),
        "diagnostics": diagnostics,
        "rf_offsets": sorted({setting.rf_offset for setting in settings}),
        "correctors": sorted({setting.corrector for setting in settings}),
        "offsets_k": sorted({setting.offset_k for setting in settings}),
        "n_settings": len(settings),
        "phase_constraint": bool(args.phase_constraint),
        "phase_weight": float(args.phase_weight),
        "n_phase_series": len(extra_series) if extra_series else 0,
        "batch_momenta": bool(args.batch_momenta),
        "momentum_source": "chroma" if args.rf_offsets else None,
        "momentum_values": {
            f"{offset:g}": float(
                next(setting.pt for setting in settings if setting.rf_offset == offset)
            )
            for offset in sorted({setting.rf_offset for setting in settings})
        },
        "momentum_calibration": {
            f"{offset:g}": {
                "selected_pt": float(
                    next(s.pt for s in settings if s.rf_offset == offset)
                ),
                "orbit_pt": float(
                    next(s.orbit_pt for s in settings if s.rf_offset == offset)
                ),
                "chroma_pt": float(
                    next(s.chroma_pt for s in settings if s.rf_offset == offset)
                ),
            }
            for offset in sorted({s.rf_offset for s in settings})
            if next(s for s in settings if s.rf_offset == offset).orbit_pt is not None
        },
        "absolute_planes": list(absolute_planes),
        "corrector_baseline": baseline,
        "errors": {family: sorted(attrs) for family, attrs in errors.items()},
        "misalignments": {
            family: sorted(attrs) for family, attrs in misalignments.items()
        },
        "group_quadrupoles_by_cell": bool(args.group_quadrupoles_by_cell),
        "prior_strength": float(args.prior_strength),
        "prior_strengths": {k: float(v) for k, v in prior_strengths.items()},
        "initial_knobs": None
        if args.initial_knobs is None
        else str(args.initial_knobs),
        "zero_step_duplicates": bool(args.keep_zero_step_duplicates),
        "n_fit_knobs": len(fitted_knobs),
        "n_output_knobs": len(knobs),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    logger.info(
        "Method 2 done: %d fitted knobs (%d physical output rows) from %d settings",
        len(fitted_knobs),
        len(knobs),
        len(settings),
    )


if __name__ == "__main__":
    main()
