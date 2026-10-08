"""Measured scan -> :class:`CorrectorSetting` (one orbit each) -> upstream ``ClosedOrbitSeries``."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from adelmo.machine.accelerators.psb import PSB
from adelmo.poco.closed_orbit import ClosedOrbitMeasurement, ClosedOrbitSeries

from loco_common.measured_response import (
    average_orbit_frames,
    cached_scan,
    global_reference_orbit,
    measured_orbits,
    pooled_intershot_noise,
    subtract_reference,
)
from loco_common.momentum import chroma_pt_by_rf_offset
from loco_common.naming import lsa_k_to_rad, lsa_to_knob

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import pandas as pd

    from loco_common.campaign import Campaign
    from loco_common.model import LocoModel

logger = logging.getLogger(__name__)

#: Label of the orbit taken with no corrector trimmed: the static orbit (absolute plane) or a momentum's dispersion orbit.
UNTRIMMED = "(untrimmed)"


@dataclass(frozen=True)
class CorrectorSetting:
    """One measured orbit: *knob* trimmed by *dk* from its standing value, at momentum *pt*."""

    corrector: str
    knob: str | None
    offset_k: float
    orbit: pd.DataFrame = field(repr=False)
    dk: float = 0.0
    rf_offset: float = 0.0
    pt: float = 0.0

    @property
    def label(self) -> str:
        return f"{self.corrector}@{self.offset_k:+g},rf{self.rf_offset:+g}"


def standing_state(model: LocoModel, absolute_planes: Sequence[str] = ()) -> dict[str, float]:
    """The fitter's reference state: the campaign's quadrupole circuits plus the correctors.

    A delta orbit moves by 1e-3 relative with the standing correctors, so they are zeroed; an absolute plane is
    largely the correctors' own kicks, so they stay at the machine's values.
    """
    correctors = model.corrector_knobs if absolute_planes else dict.fromkeys(model.corrector_knobs, 0.0)
    return {**model.tune_knobs, **correctors}


def trim_settings(
    orbits: Mapping[tuple[str, float], pd.DataFrame],
    *,
    rf_offset: float = 0.0,
    pt: float = 0.0,
    correctors: Sequence[str] | None = None,
    offsets: Sequence[float] | None = None,
) -> list[CorrectorSetting]:
    """One setting per ``(corrector, offset_k)`` orbit, restricted to *correctors* and *offsets* when given."""
    return [
        CorrectorSetting(
            corrector=corrector,
            knob=lsa_to_knob(corrector),
            offset_k=float(offset_k),
            orbit=orbit,
            dk=float(offset_k) * lsa_k_to_rad(corrector),
            rf_offset=rf_offset,
            pt=pt,
        )
        for (corrector, offset_k), orbit in sorted(orbits.items())
        if (not correctors or corrector in correctors)
        and (not offsets or any(np.isclose(offset_k, o) for o in offsets))
    ]


def scan_settings(
    campaign: Campaign,
    model: LocoModel,
    rf_offsets: Sequence[float] = (0.0,),
    *,
    absolute_planes: Sequence[str] = (),
    correctors: Sequence[str] | None = None,
    offsets: Sequence[float] | None = None,
) -> list[CorrectorSetting]:
    """Every orbit the scan holds at *rf_offsets*, each referred to the one nominal-RF untrimmed orbit.

    Off nominal RF, and on an absolute plane, the untrimmed acquisitions enter once, averaged:
    a momentum's dispersion orbit, or the static orbit.
    """
    if 0.0 not in rf_offsets:
        raise ValueError("The nominal-RF (0 mm) scan is required as the momentum reference")
    points, orbit_by_path = cached_scan(campaign)
    intershot = pooled_intershot_noise(points, orbit_by_path)
    reference = global_reference_orbit(points, orbit_by_path, intershot)
    scan = {"points": points, "orbit_by_path": orbit_by_path, "intershot": intershot}
    momenta = (
        {0.0: 0.0}
        if tuple(rf_offsets) == (0.0,)
        else chroma_pt_by_rf_offset(
            campaign.chroma_file,
            rf_offsets,
            PSB(ring=model.ring, sequence_file=model.sequence_file, kinetic_energy=model.kinetic_energy),
        )
    )
    settings = []
    for offset in rf_offsets:
        delta = measured_orbits(offset, **scan, reference=reference, absolute_planes=absolute_planes)
        settings += trim_settings(
            {key: orbit for key, orbit in delta.items() if key[1] != 0.0},
            rf_offset=offset,
            pt=momenta[offset],
            correctors=correctors,
            offsets=offsets,
        )
        if offset == 0.0 and not absolute_planes:
            continue  # the reference itself: zero by construction
        untrimmed = [orbit for key, orbit in measured_orbits(offset, **scan, delta=False).items() if key[1] == 0.0]
        if not untrimmed:
            raise ValueError(f"RF offset {offset:+g} mm has no untrimmed-corrector acquisition")
        settings.append(
            CorrectorSetting(
                corrector=UNTRIMMED,
                knob=None,
                offset_k=0.0,
                # Averaged, not summed: summing would average ERRX/ERRY instead of dividing by sqrt(N).
                orbit=subtract_reference(average_orbit_frames(untrimmed), reference, absolute_planes),
                rf_offset=offset,
                pt=momenta[offset],
            )
        )
    return settings


def closed_orbit_series(
    settings: Sequence[CorrectorSetting],
    standing: Mapping[str, float],
    *,
    absolute_planes: Sequence[str] = (),
    batch_momenta: bool = False,
) -> list[ClosedOrbitSeries]:
    """One series per setting; with *batch_momenta* one per trim, holding every momentum it was measured at.

    A series' machine state is its corrector at *standing* plus ``dk``; ``adelmo`` works out the change from the
    fitter's own reference (*standing*).
    """
    groups: dict[tuple, list[CorrectorSetting]] = {}
    for index, setting in enumerate(settings):
        key = (setting.corrector, setting.dk) if batch_momenta else (index,)
        groups.setdefault(key, []).append(setting)
    series = []
    for group in groups.values():
        group.sort(key=lambda setting: setting.pt)
        first = group[0]
        series.append(
            ClosedOrbitSeries(
                measurements=tuple(ClosedOrbitMeasurement(orbit=s.orbit, pt=s.pt) for s in group),
                machine_state={first.knob: standing[first.knob] + first.dk} if first.knob else {},
                absolute_planes=tuple(absolute_planes),
                label=first.label if not batch_momenta else f"{first.corrector}@{first.offset_k:+g}",
            )
        )
    return series
