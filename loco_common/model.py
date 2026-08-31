"""The ring-3 model both methods fit, built the way every other psb_md stage builds it.

Nothing machine-specific is decided here: the sequence, the campaign's tune knobs
and its corrector strengths all come from ``psb_md``, so a LOCO fit runs on the
same lattice as the optics reconstruction it is meant to improve.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from psb_md.acd_config import psb_orbit_corrector_strengths
from psb_md.defaults import CURRENT_FREE_MODEL_DIR

#: The ring-3 sequence this analysis is built on, vendored into the repository.
#: ``CURRENT_FREE_MODEL_DIR`` points into ``psb_md``'s own results tree, which is
#: a working directory that moves; every script here wants the frozen copy, and
#: four scripts each spelling out the same path is how three of them end up
#: pointing at a sequence the fits were not run against.
DEFAULT_SEQUENCE_FILE = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "model_qx0.165000_qy0.227500"
    / "psb3_saved.seq"
)
from psb_md.modelling import matched_tune_knobs, resolve_sequence_file

from loco_common.campaign import NORMAL, Campaign
from loco_common.naming import lsa_k_to_rad, lsa_to_knob

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

RING = 3
KINETIC_ENERGY = 0.16  # GeV, PSB flat bottom -- kinetic, not total.

#: The DHZ/DVT settings the machine actually sat at during the 2026-08-21 scan,
#: as read from LSA in ``/K`` -- *not* converted. The conversion to a MAD kick is
#: :func:`scan_corrector_knobs`, so the number recorded here is the number that
#: was read off the machine and the sign convention stays in one place.
#:
#: Why these are here rather than taken from ``psb_md``: that package's
#: ``data/orbit_correctors.madx`` is dated 2026-07-27, three and a half weeks
#: before this scan, and it disagrees with the machine on both counts --
#: different values (``kbr3dvt6l4`` by a factor 4.5) and, on all six DHZ, the
#: wrong sign, because it stores LSA readings without applying the horizontal
#: inversion :data:`loco_common.naming.LSA_K_SIGN` documents. Upstream is not
#: edited (HANDOVER.md section 6), so the correct values live here.
#:
#: **Both errors were invisible to every result recorded so far, by
#: construction.** Method 2 fits a *delta* orbit and Method 1 fits a slope with a
#: free intercept; a standing corrector offset cancels out of both. Measured on
#: the ring-3 model, offsetting a corrector by 1e-3 rad changes its delta orbit
#: by 5e-4 relative -- pure sextupole feed-down. Nothing in HANDOVER.md is
#: invalidated by this correction. The absolute-orbit mode is the first thing
#: here that reads the standing settings at first order, which is why it is the
#: first thing that could notice.
SCAN_CORRECTOR_SETTINGS_LSA: dict[str, float] = {
    "logical.BR3.DHZ8L1/K": 1.4928400000000008e-5,
    "logical.BR3.DHZ9L1/K": 1.000266660000003e-5,
    # Recorded as "DHZ11L1"/"DHZ12L1"/"DHZ13L1" when handed over; the scan log
    # (logical.BR3.DHZ11L4/K etc.) and the model agree on L4, and the machine
    # moved the L4 magnets.
    "logical.BR3.DHZ11L4/K": -5.696629999999999e-4,
    "logical.BR3.DHZ12L4/K": -3.084136e-4,
    "logical.BR3.DHZ13L4/K": 5.698738999999999e-4,
    "logical.BR3.DHZ14L1/K": -1.8397684999999996e-3,
    "logical.BR3.DVT2L4/K": 1.4324919999999998e-4,
    "logical.BR3.DVT6L4/K": 7.736600000000013e-6,
    "logical.BR3.DVT8L1/K": 3.954501999999999e-4,
    "logical.BR3.DVT9L1/K": -2.468889000000001e-4,
    "logical.BR3.DVT12L4/K": 2.9619200000000003e-5,
    "logical.BR3.DVT13L4/K": 2.0048949999999996e-4,
}


#: The quadrupole circuits the machine actually sat at during the 2026-08-21
#: scan, as MAD ``k1`` -- LSA delivers these in the model's own convention, so
#: they need no conversion. The four trim circuits were off; they are pinned
#: explicitly rather than left to the sequence's defaults, so that a sequence
#: which happens to define them non-zero cannot silently move the start model.
#:
#: These replace ``psb_md.modelling.matched_tune_knobs``, which sets the
#: circuits by matching the model to a target *tune* rather than by reading the
#: machine. The difference is +0.137 % on ``kbrqf`` and +0.042 % on ``kbrqd``,
#: and unlike a corrector offset a circuit error does not cancel out of a delta
#: orbit: it moves the measured response by 4.06 % horizontally and 1.43 %
#: vertically, against Method 2's best residual of 8.80 %.
#:
#: **No tune matching happens anywhere in the fit path, deliberately.** The model
#: is stood up on the machine's own circuit currents and its tune comes out
#: wherever those put it -- which is *not* where the machine's tune was measured.
#: That disagreement is the signal: matching the model to the measured tune would
#: absorb the very gradient error LOCO exists to find into the two main circuits.
#: :mod:`scripts.measured_optics` quantifies the gap for both campaigns.
#:
#: **Every number in HANDOVER.md predates this and was fitted from a start model
#: on the matched circuits.** They are not comparable to anything fitted after
#: it and have to be regenerated. Pass ``scan_quads=False`` to reproduce one.
SCAN_QUAD_SETTINGS: dict[str, float] = dict(NORMAL.quad_settings)


def scan_corrector_knobs() -> dict[str, float]:
    """:data:`SCAN_CORRECTOR_SETTINGS_LSA` as MAD-X knobs, in rad.

    The horizontal inversion is applied by :func:`loco_common.naming.lsa_k_to_rad`,
    the same function every measured step and slope goes through, so a standing
    setting and a scanned step cannot end up in different conventions. That sign
    is measured rather than assumed: against the ring-3 model all six DHZ
    correlate at -0.998 and all six DVT at +0.999.
    """
    return {
        lsa_to_knob(parameter): value * lsa_k_to_rad(parameter)
        for parameter, value in SCAN_CORRECTOR_SETTINGS_LSA.items()
    }


@dataclass(frozen=True)
class LocoModel:
    """Everything both methods need to stand a ring-3 model up in MAD-NG."""

    sequence_file: Path
    tune_knobs: dict[str, float]
    corrector_knobs: dict[str, float]
    ring: int = RING
    kinetic_energy: float = KINETIC_ENERGY

    @property
    def seq_name(self) -> str:
        return f"psb{self.ring}"


def build_model(
    *,
    model_dir: Path = CURRENT_FREE_MODEL_DIR,
    sequence_file: Path | None = None,
    orbit: int = 0,
    scan_correctors: bool = True,
    scan_quads: bool = True,
    campaign: Campaign = NORMAL,
) -> LocoModel:
    """Resolve the ring-3 sequence and the knobs that put it on the machine's state.

    ``include_orbit_correctors=True`` is required rather than incidental: the
    scanned DHZ/DVT correctors have to exist in the model at their machine
    settings for their *response* to be the machine's, even though they are never
    free knobs in either fit.

    ``scan_correctors`` (the default) uses the settings the machine actually sat
    at during the scan, :data:`SCAN_CORRECTOR_SETTINGS_LSA`, in place of
    ``psb_md``'s stale and wrong-signed campaign file -- see that constant for
    why, and for why no previously recorded result changes. Pass ``False`` to
    reproduce a fit made before the correction.

    ``scan_quads`` (the default) does the same for the quadrupole circuits, in
    place of a tune match. That one *does* change the answer: see
    :data:`SCAN_QUAD_SETTINGS`.

    ``campaign`` selects which machine state is being modelled -- the circuits
    come from it, so the model that fits the inverted-tunes acquisitions is the
    inverted-tunes lattice and cannot quietly be the other one.
    """
    sequence = Path(sequence_file) if sequence_file else resolve_sequence_file(model_dir)
    if campaign.machine_config is None:
        raise ValueError(
            f"campaign {campaign.slug!r} has no machine_config; every campaign "
            "must provide one for build_model to resolve corrector/tune knobs"
        )
    machine_config = campaign.machine_config
    campaign_knobs = psb_orbit_corrector_strengths(
        machine_config, include_orbit_correctors=True
    )
    matched = matched_tune_knobs(machine_config, orbit, kinetic_energy=KINETIC_ENERGY)
    model = LocoModel(
        sequence_file=sequence,
        tune_knobs=dict(campaign.quad_settings) if scan_quads else matched,
        corrector_knobs=scan_corrector_knobs() if scan_correctors else campaign_knobs,
    )
    if scan_quads:
        logger.info(
            "Quadrupole circuits from the %s machine, not a tune match: %s",
            campaign.slug,
            ", ".join(
                f"{knob} {value:+.10f} (matched {matched[knob]:+.10f}, "
                f"{100 * (value - matched[knob]) / abs(matched[knob]):+.3f} %)"
                for knob, value in campaign.quad_settings.items()
                if knob in matched
            ),
        )
        logger.info(
            "Whatever this model twisses to is not matched to the machine's "
            "measured tune, by design (scripts/measured_optics.py reads that "
            "tune live from %s)",
            campaign.optics.chroma_file,
        )
    if scan_correctors:
        worst = max(
            (
                (abs(value - campaign_knobs.get(knob, 0.0)), knob)
                for knob, value in model.corrector_knobs.items()
            ),
            default=(0.0, ""),
        )
        logger.info(
            "Using the scan's own corrector settings; largest disagreement with "
            "%s is %.3e rad on %s",
            "psb_md's campaign file",
            worst[0],
            worst[1],
        )
    logger.info(
        "Ring-%d model from %s: %d tune knobs, %d corrector knobs",
        model.ring,
        model.sequence_file,
        len(model.tune_knobs),
        len(model.corrector_knobs),
    )
    return model


def model_element_positions(model: LocoModel) -> dict[str, float]:
    """Every element's ``s`` in the loaded sequence, keyed by element name.

    ``model_twiss`` observes the BPMs only; the quadrupole positions the ``dy``
    lumping groups by are not in it, so this runs the same twiss with
    ``observe=0`` and keeps the geometry alone.
    """
    from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
    from aba_optimiser.mad import GenericMadInterface

    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    interface = GenericMadInterface(
        accelerator=accelerator,
        tune_knobs=model.tune_knobs or None,
        corrector_knobs=model.corrector_knobs or None,
    )
    try:
        table = interface.run_twiss(observe=0, method=6)
    finally:
        interface.close()
    return {str(name): float(s) for name, s in zip(table.index, table["s"], strict=True)}


def model_twiss(model: LocoModel, *, chrom: bool = False) -> pd.DataFrame:
    """The model's method-6 closed Twiss at the BPMs, indexed by BPM name.

    Used by the multi-momentum mode to project a measured orbit onto a momentum
    offset. Set ``chrom=True`` when a second-order dispersion column (``ddx``)
    is needed by a nonlinear momentum estimator.
    """
    from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
    from aba_optimiser.mad import GenericMadInterface

    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    interface = GenericMadInterface(
        accelerator=accelerator,
        tune_knobs=model.tune_knobs or None,
        corrector_knobs=model.corrector_knobs or None,
    )
    try:
        return interface.run_twiss(observe=1, method=6, chrom=chrom)
    finally:
        interface.close()
