"""Phase-only ``ClosedOrbitSeries`` for POCO's ``--phase-constraint`` (see ``docs/studies/phase-advance-constraint.md``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adelmo.poco.closed_orbit import ClosedOrbitMeasurement, ClosedOrbitSeries
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

    ``scripts/measured_optics.py --optics-folders all`` writes them per psb_md orbit folder
    (``FINAL_ACD_ORBIT_FOLDERS``); the closed orbits they are joined with come from the LOCO scan.
    """
    return campaign.optics_dir / FINAL_ACD_ORBIT_FOLDERS[int(rf_offset)] / "free"


def build_phase_series(
    campaign: Campaign,
    rf_offsets: list[float],
    momenta: dict[float, float],
    *,
    phase_weight: float = 1.0,
) -> list[ClosedOrbitSeries]:
    """One phase-only series per RF offset: a plain twiss, no corrector trim, residual is the BPM-to-BPM phase advance (mu1/mu2).

    Each is its own ``ClosedOrbitSeries`` at the fitter's machine state, and each momentum has its own measured phase.

    ``phase_weight`` divides ``mu1_var``/``mu2_var``, multiplying phase's fit weight by it; phase SNR
    (median ~290) is far below orbit's (~3400), so ~140 orbit settings otherwise swamp 3 phase settings.
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
        # Average, do not sum: summing under-weights the error bars twelve-fold.
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
