"""The ring-3 model both methods fit, built the way every other psb_md stage builds it.

Nothing machine-specific is decided here: the sequence, the campaign's quadrupole
circuits and its corrector strengths all come from ``psb_md``, so a LOCO fit runs
on the same lattice as the optics reconstruction it is meant to improve.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from psb_md.acd_config import psb_orbit_corrector_strengths
from psb_md.defaults import REFERENCE_MODEL_DIR
from psb_md.modelling import matched_tune_knobs, resolve_sequence_file

if TYPE_CHECKING:
    import pandas as pd

    from loco_common.campaign import Campaign

logger = logging.getLogger(__name__)

#: The ring-3 sequence this analysis is built on, vendored into the repository.
#: ``REFERENCE_MODEL_DIR`` points into ``psb_md``'s own working directory, which
#: it may delete and rebuild concurrently (see that constant's docstring); every
#: script here wants the frozen copy, and four scripts each spelling out the
#: same path is how three of them end up pointing at a sequence the fits were
#: not run against.
DEFAULT_SEQUENCE_FILE = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "model_qx0.165000_qy0.227500"
    / "psb3_saved.seq"
)

RING = 3
KINETIC_ENERGY = 0.16  # GeV, PSB flat bottom -- kinetic, not total.


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
    campaign: Campaign,
    model_dir: Path = REFERENCE_MODEL_DIR,
    sequence_file: Path | None = None,
    orbit: int = 0,
    scan_quads: bool = True,
) -> LocoModel:
    """Resolve the ring-3 sequence and the knobs that put it on *campaign*'s machine.

    The correctors are the campaign's own LSA settings, ``psb_md``'s orbit-corrector
    file, already converted with :func:`loco_common.naming.lsa_k_to_rad`. They are
    never free knobs, but they have to exist at their machine values for their
    response to be the machine's, and an absolute-orbit target contains their kicks.

    ``scan_quads`` (the default) stands the model on the campaign's quadrupole
    circuits rather than a tune match, so its tune comes out wherever those put it.
    That disagreement with the measured tune is the signal: matching the model to
    it would absorb the very gradient error LOCO exists to find into the two main
    circuits. Pass ``False`` for the tune-matched lattice.
    """
    sequence = Path(sequence_file) if sequence_file else resolve_sequence_file(model_dir)
    matched = matched_tune_knobs(campaign.machine_config, orbit, kinetic_energy=KINETIC_ENERGY)
    quad_settings = campaign.quad_settings
    model = LocoModel(
        sequence_file=sequence,
        tune_knobs=quad_settings if scan_quads else matched,
        corrector_knobs=psb_orbit_corrector_strengths(campaign.machine_config),
    )
    if scan_quads:
        logger.info(
            "Quadrupole circuits from the %s machine, not a tune match: %s",
            campaign.slug,
            ", ".join(
                f"{knob} {value:+.10f} (matched {matched[knob]:+.10f}, "
                f"{100 * (value - matched[knob]) / abs(matched[knob]):+.3f} %)"
                for knob, value in quad_settings.items()
                if knob in matched
            ),
        )
    logger.info(
        "Ring-%d model from %s: %d tune knobs, %d corrector knobs",
        model.ring,
        model.sequence_file,
        len(model.tune_knobs),
        len(model.corrector_knobs),
    )
    return model


def _interface(model: LocoModel):
    from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
    from aba_optimiser.mad import GenericMadInterface

    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    return GenericMadInterface(
        accelerator=accelerator,
        tune_knobs=model.tune_knobs,
        corrector_knobs=model.corrector_knobs,
    )


def model_element_positions(model: LocoModel) -> dict[str, float]:
    """Every element's ``s`` in the loaded sequence, keyed by element name.

    ``model_twiss`` observes the BPMs only; the quadrupole positions the ``dy``
    lumping groups by are not in it, so this runs the same twiss with
    ``observe=0`` and keeps the geometry alone.
    """
    interface = _interface(model)
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
    interface = _interface(model)
    try:
        return interface.run_twiss(observe=1, method=6, chrom=chrom)
    finally:
        interface.close()
