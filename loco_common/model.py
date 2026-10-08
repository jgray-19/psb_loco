"""The ring-3 model both methods fit, built from ``psb_md``'s sequence, campaign circuits and corrector strengths."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from psb_md.acd_config import psb_orbit_corrector_strengths
from psb_md.modelling import matched_tune_knobs

if TYPE_CHECKING:
    import pandas as pd

    from loco_common.campaign import Campaign

logger = logging.getLogger(__name__)

#: The vendored ring-3 sequence.
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
    sequence_file: Path | None = None,
    orbit: int = 0,
    scan_quads: bool = True,
) -> LocoModel:
    """Resolve the ring-3 sequence and the knobs that put it on *campaign*'s machine.

    Correctors are the campaign's LSA settings converted with :func:`loco_common.naming.lsa_k_to_rad`;
    they are never free knobs but must sit at machine values.

    ``scan_quads`` (default) uses the campaign's quadrupole circuits rather than a tune match;
    pass ``False`` for the tune-matched lattice.
    """
    sequence = Path(sequence_file or DEFAULT_SEQUENCE_FILE)
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
    from adelmo.machine.accelerators.psb import PSB as OptimiserPSB
    from adelmo.machine.mad.optimising_mad_interface import GenericMadInterface
    from adelmo.machine.mad.machine_state import merge_machine_states

    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    return GenericMadInterface(
        accelerator=accelerator,
        machine_state=merge_machine_states(model.corrector_knobs, model.tune_knobs),
    )


def model_element_positions(model: LocoModel) -> dict[str, float]:
    """Every element's ``s`` in the loaded sequence, keyed by element name (twiss with ``observe=0``)."""
    interface = _interface(model)
    try:
        table = interface.run_twiss(observe=0, method=6)
    finally:
        interface.close()
    return {str(name): float(s) for name, s in zip(table.index, table["s"], strict=True)}


def model_twiss(model: LocoModel, *, chrom: bool = False) -> pd.DataFrame:
    """The model's method-6 closed Twiss at the BPMs, indexed by BPM name; ``chrom=True`` adds ``ddx``."""
    interface = _interface(model)
    try:
        return interface.run_twiss(observe=1, method=6, chrom=chrom)
    finally:
        interface.close()
