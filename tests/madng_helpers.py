"""Small MAD-NG helpers shared by the slow tests, for asking the model a direct question."""

from __future__ import annotations

import pandas as pd


def open_interface(
    sequence_file, *, ring: int = 3, kinetic_energy: float = 0.16, **optimise
):
    """A MAD-NG interface on the ring-3 sequence, BPMs observed.

    With no ``errors`` / ``misalignments`` this is the bare model. Pass a family
    (``misalignments={"quad": {"dy"}}``) to get the knob-creating interface, the only way to
    *set* a misalignment (a bare interface silently ignores ``element.dy``).
    """
    from adelmo.machine.accelerators.psb import PSB as OptimiserPSB
    from adelmo.machine.mad.optimising_mad_interface import (
        GenericMadInterface,
        GradientDescentMadInterface,
    )

    accelerator = OptimiserPSB(
        ring=ring, sequence_file=sequence_file, kinetic_energy=kinetic_energy, **optimise
    )
    if not optimise:
        return GenericMadInterface(accelerator=accelerator)
    return GradientDescentMadInterface(accelerator=accelerator)


def set_knob(interface, name: str, value: float) -> None:
    """Set a MAD-X global variable, e.g. a corrector's ``kbr3dhz8l1``."""
    interface.mad.send(f"MADX['{name}'] = {value:.15e}")


def closed_orbit(interface) -> pd.DataFrame:
    """Closed orbit at the observed BPMs as an ``X``/``Y`` frame in metres."""
    twiss = interface.run_twiss(observe=1, method=6)
    frame = pd.DataFrame({"X": twiss["x"].astype(float), "Y": twiss["y"].astype(float)})
    frame.index.name = "NAME"
    return frame
