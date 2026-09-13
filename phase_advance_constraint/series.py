"""Phase-only ``ClosedOrbitSeries`` for Method 2's ``--phase-constraint``.

Everything here is imported by ``method2_delta_orbit/run_method2.py`` and
nowhere else -- the production fitter's own file only carries the CLI flags
and the one-line call into :func:`build_phase_series`. See
``docs/studies/phase-advance-constraint.md`` for why this observable exists,
what it does to the fit, and the weight-scan evidence behind
``--phase-weight``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aba_optimiser.training_closed_twiss import (
    ClosedOrbitMeasurement,
    ClosedOrbitSeries,
)
from psb_md.defaults import FINAL_ACD_ORBIT_FOLDERS
from psb_md.measured_optics import assemble_measured_optics

from loco_common.measured_response import (
    average_orbit_frames,
    cached_scan,
    measured_orbits,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

    from loco_common.campaign import Campaign


def phase_optics_dir(campaign: Campaign, rf_offset: float) -> Path:
    """The equation-compensated optics measured at one RF offset.

    ``scripts/measured_optics.py --optics-folders all`` writes them per psb_md
    orbit folder (``FINAL_ACD_ORBIT_FOLDERS``), so the offset -> folder mapping
    is psb_md's, not a second table here. The optics come from cleaned
    turn-by-turn data (its production preprocessing chain); the closed orbits
    they are joined with come from the LOCO scan, which needs no cleaning.
    """
    return campaign.optics_dir / FINAL_ACD_ORBIT_FOLDERS[int(rf_offset)] / "free"


def build_phase_series(
    campaign: Campaign,
    rf_offsets: list[float],
    momenta: dict[float, float],
    *,
    phase_weight: float = 1.0,
) -> list[ClosedOrbitSeries]:
    """One phase-only series per RF offset: a plain twiss, no corrector trim,
    whose residual is only the BPM-to-BPM phase advance (mu1/mu2).

    Phase advance is BPM-to-BPM within a single twiss, never a delta against a
    reference state (docs/studies/phase-advance-constraint.md), so this rides
    alongside the many orbit-only corrector-trim series without touching them:
    each is its own ``ClosedOrbitSeries`` with ``control_knob=None``. Every
    momentum has its own measured phase, so this cannot reuse one folder for
    all three RF offsets the way the nominal-RF orbit reference can.

    ``phase_weight`` divides ``mu1_var``/``mu2_var`` by this factor, which
    multiplies phase's fit weight by it (weight = 1/variance). Needed because
    phase's measurement SNR (median ~290) is far looser than the closed
    orbit's (median ~3400), so under chi-normalisation the ~140 orbit
    corrector-trim settings otherwise swamp 3 phase-only settings to the point
    of no visible effect -- see docs/studies/phase-advance-constraint.md and
    plots/real_method2_phase_check_p17_p23_final.png (weight=1).
    """
    optics_dirs = {momenta[offset]: phase_optics_dir(campaign, offset) for offset in rf_offsets}
    missing = [str(path) for path in optics_dirs.values() if not (path / "beta_phase_x.tfs").exists()]
    if missing:
        raise FileNotFoundError(
            f"No measured optics for {campaign.slug} at {missing}; run "
            f"scripts/measured_optics.py --campaign {campaign.slug} --optics-folders all first."
        )

    points, orbit_by_path = cached_scan(campaign=campaign)
    closed_orbits: dict[float, pd.DataFrame] = {}
    for offset in rf_offsets:
        untrimmed = {
            key: frame
            for key, frame in measured_orbits(
                offset, points=points, orbit_by_path=orbit_by_path, delta=False, campaign=campaign
            ).items()
            if key[1] == 0.0
        }
        # Twelve recordings of one machine state (drop_zero_step_duplicates'
        # rationale applies here too): average, do not sum, or the error bars
        # go in twelve-fold under-weighted.
        closed_orbits[momenta[offset]] = average_orbit_frames(list(untrimmed.values()))

    frames = assemble_measured_optics(closed_orbits=closed_orbits, optics_dirs=optics_dirs, dispersion=None)
    if phase_weight != 1.0:
        for frame in frames.values():
            for column in ("mu1_var", "mu2_var"):
                if column in frame.columns:
                    frame[column] = frame[column] / phase_weight
    return [
        ClosedOrbitSeries(
            measurements=(ClosedOrbitMeasurement(orbit=frame, pt=pt, reference_pt=pt),),
            observables=("mu1", "mu2"),
            label=f"phase@pt{pt:+.2e}",
        )
        for pt, frame in frames.items()
    ]
