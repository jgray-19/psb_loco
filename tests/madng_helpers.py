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
    from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
    from aba_optimiser.mad import GenericMadInterface, GradientDescentMadInterface

    accelerator = OptimiserPSB(
        ring=ring, sequence_file=sequence_file, kinetic_energy=kinetic_energy, **optimise
    )
    if not optimise:
        return GenericMadInterface(accelerator=accelerator)
    return GradientDescentMadInterface(accelerator=accelerator)


def open_response_interface(sequence_file, *, ring: int = 3, kinetic_energy: float = 0.16):
    """Method 1's native 32-knob PSB interface."""
    from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
    from aba_optimiser.mad import GradientDescentMadInterface

    accelerator = OptimiserPSB(
        ring=ring,
        sequence_file=sequence_file,
        kinetic_energy=kinetic_energy,
        errors={"quad": {"k1"}},
        group_quadrupoles_by_cell=True,
    )
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


def setup_response_da(interface, corr_elements, quad_knobs=None):
    """Load ``response_da.mad`` and return its full x/y response matrix."""
    import numpy as np

    from method1_madng_da.run_method1 import SCRIPT

    mad = interface.mad
    mad["corr_elements"] = list(corr_elements)
    mad["quad_knobs"] = list(
        getattr(interface, "knob_names", []) if quad_knobs is None else quad_knobs
    )
    mad["target_mat"] = np.zeros((1, len(corr_elements)))
    mad["weight_mat"] = np.zeros((1, len(corr_elements)))
    mad.send(f"pyi = {interface.py_name}")
    mad.send(SCRIPT.read_text())
    mad.send("compute_response(); send_response()")
    names = [str(name) for name in mad.recv()]
    response = np.asarray(mad.recv(), dtype=float)
    return names, response


def read_response(interface):
    """Recompute and return ``(bpm_names, response)`` from the loaded script."""
    import numpy as np

    interface.mad.send("compute_response(); send_response()")
    names = [str(name) for name in interface.mad.recv()]
    return names, np.asarray(interface.mad.recv(), dtype=float)


def response_with_knobs(sequence_file, corr_elements, knobs):
    """Return Method 1's response after applying native ``dk1l`` knobs."""
    import numpy as np

    interface = open_response_interface(sequence_file)
    try:
        names, response = setup_response_da(interface, corr_elements)
        for name, value in knobs.items():
            interface.mad[f"loaded_sequence['{name}']"] = float(value)
        if knobs:
            names, response = read_response(interface)
    finally:
        interface.close()
    return names, np.asarray(response, dtype=float)
