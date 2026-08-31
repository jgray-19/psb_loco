"""Method 2 driver: fit quadrupole ``k1`` to measured delta closed orbits.

One worker per (corrector, step) -- and, with ``--rf-offsets``, per momentum too.
The worker count multiplies quickly (12 correctors x 4 steps x 5 RF settings is
240 processes), so the corrector, step and RF subsets are all explicit and the
defaults are modest. ``--batch-momenta`` removes the momentum factor by fitting
every momentum of a trim in one process, which is how the full scan fits under
the file-descriptor ceiling (README, "worker count").
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
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
    NORMAL,
    Campaign,
    add_campaign_argument,
    campaign_by_slug,
)
from loco_common.measured_response import (
    apply_error_floor,
    average_orbit_frames,
    cached_orbits,
    cached_scan,
    global_reference_orbit,
    measured_orbits,
    subtract_reference,
)
from loco_common.model import (
    LocoModel,
    build_model,
    model_twiss,
)
from loco_common.momentum import compare_momentum_calibrations
from loco_common.naming import lsa_k_to_rad, lsa_to_knob

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


#: Labels for the settings that are not a corrector trim at all: the untrimmed
#: orbit, entering as a target in its own right. They are not LSA parameter
#: names and must never be handed to ``lsa_to_knob``; :func:`build_settings`
#: gives them a knob name and a zero step directly.
STATIC_ORBIT = "(static orbit)"
DISPERSION = "(dispersion)"
UNTRIMMED_SETTINGS: tuple[str, ...] = (STATIC_ORBIT, DISPERSION)

PRIOR_SUFFIXES: dict[str, str] = {
    "quadrupoles": "dk1l",
    "bends": "dk0l",
    "quad_dy": "dy",
    "quad_tilt": "tilt",
}


@dataclass
class CorrectorSetting:
    """One measured orbit and the model state at which it must be evaluated.

    Every target keeps its own ``pt``. ``reference_pt`` is independent and is
    zero for the PSB global reference even when the signal orbit is off-momentum.
    """

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

#: The two corrector baselines the model can be put on, one per fit.
#:
#: ``zero``  -- every corrector at zero, the trimmed one at ``dk`` alone. What a
#:              *quadrupole* fit wants: its target is a delta orbit, referred to
#:              the untrimmed machine, and a delta is independent of where the
#:              correctors were standing. Measured on the ring-3 model, changing
#:              every standing corrector moves a delta orbit by 1e-3 relative
#:              (sextupole feed-down). Taking the baseline to zero therefore
#:              costs the quadrupole fit nothing and buys it complete
#:              independence from settings it cannot see -- which is exactly why
#:              those settings could be wrong for a whole campaign (ABSOLUTE_
#:              ORBIT_STUDY.md section 2b) without any recorded result moving.
#:
#: ``machine`` -- every corrector at the value the machine actually sat at, the
#:              trimmed one at ``nominal + dk``. What a *bends / quad dy* fit
#:              needs: its target is the absolute closed orbit, and the standing
#:              correctors generate a large part of that orbit. On the zero
#:              baseline the model would attribute their kicks to the bends.
CORRECTOR_BASELINES: tuple[str, ...] = ("zero", "machine")


def corrector_baseline_knobs(model: LocoModel, baseline: str) -> dict[str, float]:
    """The standing corrector settings the model is put on, per :data:`CORRECTOR_BASELINES`.

    ``zero`` returns every corrector explicitly at zero rather than an empty
    dict: an empty dict leaves the sequence's own values in place, which is not
    the same thing and not something this should depend on.
    """
    if baseline not in CORRECTOR_BASELINES:
        raise ValueError(f"Unknown corrector baseline {baseline!r}; expected {CORRECTOR_BASELINES}")
    if baseline == "machine":
        return dict(model.corrector_knobs)
    return dict.fromkeys(model.corrector_knobs, 0.0)


def default_corrector_baseline(absolute_planes: tuple[str, ...]) -> str:
    """``machine`` once any plane keeps its closed orbit, ``zero`` otherwise.

    The coupling is the physics, not a convenience: a plane whose reference has
    been subtracted cannot see the standing correctors, and a plane that keeps
    its closed orbit cannot do without them.
    """
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
    """Turn measured delta orbits into one :class:`CorrectorSetting` per worker.

    *absolute_planes* is carried through to the model side, which has to skip the
    same reference subtraction the data side skipped. *corrector_baseline* says
    what the untrimmed correctors are set to; see :data:`CORRECTOR_BASELINES`.
    """
    baseline = corrector_baseline or default_corrector_baseline(absolute_planes)
    standing = corrector_baseline_knobs(model, baseline)
    settings = []
    for (corrector, offset_k), orbit in sorted(orbits.items()):
        untrimmed = corrector in UNTRIMMED_SETTINGS
        # The untrimmed orbit is not one corrector's measurement, so the
        # --correctors/--offsets subsets do not apply to it: it is the machine.
        if not untrimmed and correctors and corrector not in correctors:
            continue
        if not untrimmed and offsets and not any(np.isclose(offset_k, o) for o in offsets):
            continue
        # Any real knob will do for an untrimmed setting -- the worker needs a
        # name to write, and dk = 0 leaves it at ``nominal``, which the baseline
        # sets to the value the machine was actually standing at.
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
    """Drop the per-corrector untrimmed acquisitions from one RF setting's orbits.

    ``measured_orbits`` keys an untrimmed acquisition by the corrector whose scan
    it belongs to, so a non-zero RF setting carries twelve of them -- twelve
    recordings of one machine state, not twelve measurements. The averaged
    ``(dispersion)`` setting is where that orbit enters the fit; these would
    weight it twelve times over.
    """
    return {key: frame for key, frame in orbits.items() if key[1] != 0.0}


def average_zero_step(
    orbits: dict[tuple[str, float], pd.DataFrame],
) -> dict[tuple[str, float], pd.DataFrame]:
    """Fold one RF setting's untrimmed acquisitions into a single target.

    The counterpart of :func:`drop_zero_step_duplicates` for absolute mode: the
    untrimmed acquisitions are still twelve recordings of one machine state, but
    now they carry signal (the static closed orbit) instead of being zero by
    construction, so they are averaged rather than dropped.

    The caveat docs/reference/handover.md section 9.5 records applies here too: this averages
    the error *bars* along with the orbits, so the result is under-weighted by
    roughly the repeat count. With the absolute error floor dominating those bars
    it makes little difference, but it is the same bug and it is deliberate.
    """
    zero = [frame for (_, offset), frame in orbits.items() if offset == 0.0]
    kept = {key: frame for key, frame in orbits.items() if key[1] != 0.0}
    if not zero:
        return kept
    kept[(STATIC_ORBIT, 0.0)] = sum(zero) / len(zero)
    return kept


def build_multi_pt_settings(
    model: LocoModel,
    rf_offsets: list[float],
    twiss: pd.DataFrame,
    *,
    dispersion_workers: bool = True,
    zero_step_duplicates: bool = False,
    absolute_planes: tuple[str, ...] = (),
    error_floor: float = 0.0,
    corrector_baseline: str | None = None,
    momentum_source: str = "chroma",
    campaign: Campaign = NORMAL,
    **kwargs,
) -> list[CorrectorSetting]:
    """Settings across several RF-steering offsets, each at its calibrated ``pt``.

    The five RF settings are five momenta whose Jacobians are genuinely
    independent, which lifts degeneracies a single momentum leaves. What they are
    not is a momentum in the LOCO log itself. ``momentum_source`` chooses either
    the older model-dispersion projection or the RF-derived ``Dp/p`` measured by
    the chroma scan at the same radial plateaus. Both use the nominal-RF orbit as
    exactly ``pt=0`` and are logged before the fit starts.

    Each non-zero RF setting was acquired untrimmed once *per corrector*: twelve
    recordings of one machine state. They enter as the single averaged
    ``(dispersion)`` setting below and are dropped individually, because passing
    all twelve weights that one orbit twelve times over -- 11.4 % against 11.0 %
    on the 2026-08-21 scan, for 48 more settings. ``zero_step_duplicates``
    restores them for the comparison; it is not the way to run a fit.
    """
    from loco_common.momentum import chroma_pt_by_rf_offset, estimate_pt_by_rf_offset

    if 0.0 not in rf_offsets:
        raise ValueError("The nominal-RF (0 mm) setting is required as the momentum reference")
    baseline = corrector_baseline or default_corrector_baseline(absolute_planes)
    standing = corrector_baseline_knobs(model, baseline)
    points, orbit_by_path = cached_scan(campaign=campaign)
    absolute = {}
    for offset in rf_offsets:
        untrimmed = {
            key: frame
            for key, frame in measured_orbits(
                offset, points=points, orbit_by_path=orbit_by_path, delta=False
            ).items()
            if key[1] == 0.0
        }
        if not untrimmed:
            raise ValueError(f"RF offset {offset:+g} mm has no untrimmed-corrector acquisition")
        # Average the untrimmed acquisitions: at offset_k = 0 every corrector's
        # scan sat on the same machine, so these are repeats of one orbit.
        # Not ``sum(...) / len(...)``: pandas addition hits ERRX/ERRY too, so
        # that averages the error bars into ``mean(err)`` where the mean of N
        # deserves ``err/sqrt(N)``, entering the fit sqrt(12) ~ 3.5x over-errored
        # and so twelve-fold under-weighted.
        absolute[offset] = average_orbit_frames(list(untrimmed.values()))
    orbit_momenta = estimate_pt_by_rf_offset(absolute, twiss)
    momentum_accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    chroma_momenta = chroma_pt_by_rf_offset(
        campaign.optics.chroma_file, rf_offsets, momentum_accelerator
    )
    if momentum_source == "orbit":
        momenta = orbit_momenta
    elif momentum_source == "chroma":
        momenta = chroma_momenta
    else:
        raise ValueError(f"Unknown momentum source {momentum_source!r}")
    differences = compare_momentum_calibrations(chroma_momenta, orbit_momenta)
    logger.warning(
        "Momentum calibration comparison (orbit - RF/chroma): %s",
        ", ".join(f"{offset:+g} mm {delta:+.4e}" for offset, delta in differences.items()),
    )
    logger.info(
        "Using %s momentum calibration: %s",
        momentum_source,
        ", ".join(f"{offset:+g} mm {value:+.4e}" for offset, value in sorted(momenta.items())),
    )
    reference = global_reference_orbit(points, orbit_by_path)
    settings: list[CorrectorSetting] = []
    for offset in rf_offsets:
        orbits = measured_orbits(
            offset,
            points=points,
            orbit_by_path=orbit_by_path,
            absolute_planes=absolute_planes,
            error_floor=error_floor,
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
            # At nominal RF with every plane subtracted the untrimmed orbit is
            # zero by construction. With an absolute plane it is the machine's
            # static closed orbit, which is the whole point of that mode, so it
            # is kept -- under a label that says it is not dispersion.
            continue
        # The untrimmed orbit at this RF setting, minus the global reference, is
        # this momentum's dispersion orbit. Under a per-RF reference it was
        # identically zero and carried nothing; against the global reference it is
        # a quadrupole-sensitive constraint that costs one extra worker, so it is
        # added here rather than left on the floor.
        settings.append(
            CorrectorSetting(
                corrector=DISPERSION if offset != 0.0 else STATIC_ORBIT,
                # No corrector moves here, but the worker still needs a knob
                # name to write. Under a subtracted plane any real one would do,
                # since dk = 0 leaves it at its nominal value on both sides of
                # the difference -- but an *absolute* plane has no other side, so
                # writing the wrong value here would zero that corrector out of
                # the model's closed orbit. Hence ``nominal`` below is the
                # baseline's value for this knob, not 0.
                knob=next(iter(model.corrector_knobs)),
                offset_k=0.0,
                orbit=apply_error_floor(
                    subtract_reference(absolute[offset], reference, absolute_planes),
                    error_floor,
                    absolute_planes,
                ),
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
    """Translate PSB settings to independent upstream measurement series.

    Batching changes process layout only. Each measurement retains its own
    target, signal momentum, and reference momentum; the worker merely caches
    repeated exact model states such as the shared global reference at ``pt=0``.
    """
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
    optimise_quadrupoles: bool,
    optimise_bends: bool,
    optimise_quad_dy: bool,
    optimise_quad_tilt: bool,
) -> dict[str, float] | None:
    """Scale priors independently for enabled families with different units."""
    enabled = {
        "quadrupoles": optimise_quadrupoles,
        "bends": optimise_bends,
        "quad_dy": optimise_quad_dy,
        "quad_tilt": optimise_quad_tilt,
    }
    families = [family for family, value in enabled.items() if value]
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
    optimise_quadrupoles: bool = True,
    optimise_bends: bool = False,
    optimise_quad_dy: bool = False,
    optimise_quad_tilt: bool = False,
    group_quadrupoles_by_cell: bool = False,
    initial_knob_strengths: dict[str, float] | None = None,
    output_path: Path = Path("results/method2"),
) -> tuple[dict[str, float], dict[str, float], dict[str, object]]:
    """Run the summed-gradient delta-orbit fit over the selected knob families.

    The model is put on the corrector baseline the settings were built with --
    every corrector at zero for a quadrupole fit, at the machine's own values for
    a bends / quad ``dy`` fit. See :data:`CORRECTOR_BASELINES`.

    Which families are free is a physics decision, not a default:
    ``psb_md.closed_orbit_fitting`` documents that the closed orbit constrains
    bends and quadrupole ``dy`` and barely responds to gradients, so freeing
    quadrupoles alongside bends lets the solve absorb bend residual into the
    gradients. Delta orbits invert that -- they constrain gradients and say
    almost nothing about ``k0`` or ``dy`` -- which is why the absolute-plane mode
    and these families belong together.
    """
    if not (
        optimise_quadrupoles or optimise_bends or optimise_quad_dy or optimise_quad_tilt
    ):
        raise ValueError("No knob family enabled: there is nothing to fit")
    baselines = {setting.corrector_baseline for setting in settings}
    if len(baselines) > 1:
        # Half the fit would be comparing the model against a machine the other
        # half says was not there.
        raise ValueError(
            f"Every setting must share one corrector baseline, got {sorted(baselines)}"
        )
    standing = corrector_baseline_knobs(model, baselines.pop())
    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
        optimise_quadrupoles=optimise_quadrupoles,
        optimise_bends=optimise_bends,
        optimise_quad_dy=optimise_quad_dy,
        optimise_quad_tilt=optimise_quad_tilt,
        group_quadrupoles_by_cell=group_quadrupoles_by_cell,
    )
    family_priors = prior_strengths_by_suffix(
        default=prior_strength,
        overrides=prior_strengths or {},
        optimise_quadrupoles=optimise_quadrupoles,
        optimise_bends=optimise_bends,
        optimise_quad_dy=optimise_quad_dy,
        optimise_quad_tilt=optimise_quad_tilt,
    )
    fitter = ClosedOrbitFitter(
        accelerator=accelerator,
        sequence_config=SequenceConfig(magnet_range="$start/$end"),
        series=closed_orbit_series(settings, batch_momenta=batch_momenta),
        lm_config=LevenbergMarquardtConfig(
            max_iterations=max_iterations,
            gradient_converged_value=GRADIENT_CONVERGED_VALUE,
            initial_lambda=initial_lambda,
        ),
        initial_knob_strengths=initial_knob_strengths,
        # Not a tuning parameter: psb_md.closed_orbit_fitting documents that both
        # the shape and the scale of this prior are what pick the answer out of a
        # large null space. Overridable only so the sensitivity to it can be
        # measured (docs/reference/handover.md §10); the default is the one to use.
        # Per family, because k1, k0 and dy do not share a unit and one global
        # median(diag H) would move the quadrupole prior off its measured knee
        # as soon as another family is enabled.
        prior_strengths=family_priors,
        tune_knobs=model.tune_knobs or None,
        # Not model.corrector_knobs: on the ``zero`` baseline every corrector is
        # explicitly zeroed, so a quadrupole fit depends on nothing but its own
        # trims. See CORRECTOR_BASELINES.
        corrector_knobs=standing or None,
        output_config=OutputConfig(tensorboard_root=output_path / "tensorboard"),
    )
    try:
        knobs, uncertainties = fitter.run()
        return knobs, uncertainties, dict(fitter.diagnostics)
    finally:
        # Without this MAD's ``__del__`` tears the main-process pipe down
        # mid-message at exit; the same guard psb_md.fit_closed_orbit_knobs uses.
        mad_iface = getattr(fitter.config_manager, "mad_iface", None)
        if mad_iface is not None:
            mad_iface.close()


def warn_family_mismatch(absolute_planes: tuple[str, ...], args) -> None:
    """Warn when a knob family and the plane that constrains it are not paired.

    Neither case is an error. A family without its plane is a legitimate way to
    ask how much the delta orbits say about it (the answer is expected to be
    "almost nothing", leaving the prior to decide); a plane without its family is
    the control that measures how much static orbit the gradients absorb, which
    is exactly the effect ``psb_md.closed_orbit_fitting`` warns about.
    """
    # Tilt sits with dy: a rolled quadrupole is a skew source, so it shows up in
    # the vertical plane -- and it is the only family here that can make vertical
    # dispersion without making the vertical orbit that caps it
    # (docs/studies/quadrupole-roll.md).
    vertical = args.optimise_quad_dy or args.optimise_quad_tilt
    for plane, flag, family in (("x", args.optimise_bends, "bends"),
                                ("y", vertical, "quadrupole dy/tilt")):
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
            "Their pt calibration is selected by --momentum-source; every source "
            "uses the 0 mm orbit as exactly pt=0."
        ),
    )
    parser.add_argument("--correctors", nargs="+", default=None)
    parser.add_argument(
        "--momentum-source",
        choices=("orbit", "chroma"),
        default="orbit",
        help=(
            "Momentum calibration for --rf-offsets. 'orbit' projects each closed "
            "orbit onto the starting model dispersion; 'chroma' uses the independent "
            "RF-derived Dp/p measured at the same radial-orbit plateaus. "
            "Both are referenced to the 0 mm orbit, which is pt=0."
        ),
    )
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
            "misalignments (y), so pair this with --optimise-bends and/or "
            "--optimise-quad-dy; on its own it hands the fit an orbit only the "
            "gradients can absorb."
        ),
    )
    parser.add_argument(
        "--absolute-error-floor",
        type=float,
        default=1e-4,
        help=(
            "Systematic added in quadrature (metres) to the absolute planes' "
            "error bars. Their acquisition SEM is ~1e-6 m while the uncertainty "
            "that actually applies is the unfitted BPM zero offset, ~1e-4 m; "
            "without a floor the absolute planes enter at thousands of sigma and "
            "the delta planes stop mattering. Scan it before trusting it."
        ),
    )
    parser.add_argument(
        "--no-optimise-quadrupoles",
        dest="optimise_quadrupoles",
        action="store_false",
        help=(
            "Free no quadrupole k1. With --optimise-bends or --optimise-quad-dy "
            "this is the pure orbit-geometry control: it measures what the "
            "static orbit asks for when no gradient can absorb it."
        ),
    )
    parser.add_argument(
        "--optimise-bends",
        action="store_true",
        help="Free the sbend/rbend k0. Constrained by an absolute x plane.",
    )
    parser.add_argument(
        "--optimise-quad-dy",
        action="store_true",
        help="Free the quadrupole vertical offsets. Constrained by an absolute y plane.",
    )
    parser.add_argument(
        "--optimise-quad-tilt",
        action="store_true",
        help=(
            "Free the quadrupole rolls about the beam axis. The only skew source "
            "in the fit, and so the only family that can make vertical dispersion "
            "without making the vertical orbit that caps it; constrained by an "
            "absolute y plane. See docs/studies/quadrupole-roll.md."
        ),
    )
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
        default=None,
        help="Prior strength for the quadrupole tilts; defaults to --prior-strength.",
    )
    parser.add_argument(
        "--prior-strength-quad-dy",
        type=float,
        default=None,
        help="Prior strength for the quadrupole dy; defaults to --prior-strength.",
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
    error_floor = float(args.absolute_error_floor) if absolute_planes else 0.0
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
            error_floor=error_floor,
            corrector_baseline=baseline,
            momentum_source=args.momentum_source,
            campaign=campaign,
            **subset,
        )
    elif absolute_planes:
        # Not cached_orbits: that parquet holds the fully-subtracted orbits and
        # is keyed by RF offset alone, so it cannot represent this mode. The
        # expensive SDDS read is cached upstream of it by cached_scan().
        orbits = average_zero_step(
            measured_orbits(
                args.rf_offset,
                absolute_planes=absolute_planes,
                error_floor=error_floor,
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
    }
    prior_strengths = {k: v for k, v in prior_strengths.items() if v is not None}

    fitted_knobs, fitted_uncertainties, diagnostics = run(
        settings,
        model,
        max_iterations=args.max_iterations,
        batch_momenta=args.batch_momenta,
        prior_strength=args.prior_strength,
        prior_strengths=prior_strengths,
        optimise_quadrupoles=args.optimise_quadrupoles,
        optimise_bends=args.optimise_bends,
        optimise_quad_dy=args.optimise_quad_dy,
        optimise_quad_tilt=args.optimise_quad_tilt,
        group_quadrupoles_by_cell=args.group_quadrupoles_by_cell,
        initial_knob_strengths=initial_knob_strengths,
        output_path=args.output,
    )

    knobs, uncertainties = fitted_knobs, fitted_uncertainties
    args.output.mkdir(parents=True, exist_ok=True)
    write_optimisation_results(
        args.output / "knobs.csv", knobs, uncertainties, stage_name="loco_method2"
    )
    summary = {
        "method": "delta_orbit",
        # MAD-NG can reject every trial state before the optimiser takes a step;
        # upstream then returns the zero/tilt-seed vector without raising. Do not
        # let a campaign runner or report mistake that for a fitted lattice.
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
        "batch_momenta": bool(args.batch_momenta),
        "momentum_source": args.momentum_source if args.rf_offsets else None,
        "momentum_values": {
            f"{offset:g}": float(
                next(setting.pt for setting in settings if setting.rf_offset == offset)
            )
            for offset in sorted({setting.rf_offset for setting in settings})
        },
        "momentum_calibration": {
            f"{offset:g}": {
                "selected_pt": float(next(s.pt for s in settings if s.rf_offset == offset)),
                "orbit_pt": float(next(s.orbit_pt for s in settings if s.rf_offset == offset)),
                "chroma_pt": float(next(s.chroma_pt for s in settings if s.rf_offset == offset)),
            }
            for offset in sorted({s.rf_offset for s in settings})
            if next(s for s in settings if s.rf_offset == offset).orbit_pt is not None
        },
        "absolute_planes": list(absolute_planes),
        "corrector_baseline": baseline,
        "absolute_error_floor": float(error_floor),
        "optimise_quadrupoles": bool(args.optimise_quadrupoles),
        "optimise_bends": bool(args.optimise_bends),
        "optimise_quad_dy": bool(args.optimise_quad_dy),
        "optimise_quad_tilt": bool(args.optimise_quad_tilt),
        "group_quadrupoles_by_cell": bool(args.group_quadrupoles_by_cell),
        "prior_strength": float(args.prior_strength),
        "prior_strengths": {k: float(v) for k, v in prior_strengths.items()},
        "initial_knobs": None if args.initial_knobs is None else str(args.initial_knobs),
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
