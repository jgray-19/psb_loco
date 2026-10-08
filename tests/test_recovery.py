"""Acceptance: POCO recovers a known machine.

Compared on derived quantities (the loss, the closed orbit), not knobs: the closed-orbit null space is large (knobs came back 59-79% wrong with a good derived quantity).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from loco_common.model import LocoModel
from loco_common.naming import lsa_to_knob

pytestmark = pytest.mark.slow

CORRECTORS = [
    "BR3.DHZ8L1", "BR3.DHZ9L1", "BR3.DHZ11L4", "BR3.DHZ12L4", "BR3.DHZ13L4", "BR3.DHZ14L1",
    "BR3.DVT2L4", "BR3.DVT6L4", "BR3.DVT8L1", "BR3.DVT9L1", "BR3.DVT12L4", "BR3.DVT13L4",
]


@pytest.fixture
def loco_model(sequence_file) -> LocoModel:
    """A bare ring-3 model: the fake machine carries its own state, not a campaign's."""
    return LocoModel(
        sequence_file=sequence_file,
        tune_knobs={},
        corrector_knobs={lsa_to_knob(corrector): 0.0 for corrector in CORRECTORS},
    )


def _rms(matrix: np.ndarray) -> float:
    return float(np.sqrt(np.mean(matrix**2)))


def _poco_deltas(line, bpms, correctors, dk):
    """Measured delta orbits for POCO, from the same truth line."""
    import xtrack_tools as xtt

    def orbit(corrector=None, step=0.0):
        if corrector is not None:
            element = line[corrector.lower()]
            vertical = "dvt" in corrector.lower()
            attribute = "ksl" if vertical else "knl"
            original = float(getattr(element, attribute)[0])
            getattr(element, attribute)[0] = original + (step if vertical else -step)
        table = xtt.xsuite_tws_to_ng(line.twiss(method="4d")).loc[bpms]
        if corrector is not None:
            getattr(element, attribute)[0] = original
        return table

    nominal = orbit()
    frames = {}
    for corrector in correctors:
        kicked = orbit(corrector, dk)
        frame = pd.DataFrame(index=pd.Index(bpms, name="NAME"))
        frame["X"] = kicked["x"] - nominal["x"]
        frame["Y"] = kicked["y"] - nominal["y"]
        frame["ERRX"] = frame["ERRY"] = 1e-7
        frames[corrector] = frame
    return frames


def test_poco_reduces_the_delta_orbit_misfit_to_the_truth_machine(
    truth_line, bpm_names, loco_model, tmp_path
):
    """Fitted to delta orbits of a machine with known gradient errors, POCO ends far below its starting misfit.

    Asserted on the loss (the derived quantity), not the knobs: the closed-orbit null space is large.
    """
    from poco.run_poco import run as run_poco
    from poco.settings import CorrectorSetting

    bpms = [name.upper() for name in bpm_names]
    dk = 5e-4  # a large trim, so the delta orbit is well above the BPM noise floor
    settings = [
        CorrectorSetting(
            corrector=corrector,
            knob="k" + corrector.replace(".", "").lower(),
            offset_k=dk,
            orbit=frame,
            dk=dk,
        )
        for corrector, frame in _poco_deltas(truth_line, bpms, CORRECTORS, dk).items()
    ]

    result, history = run_poco(
        settings,
        loco_model,
        max_iterations=10,
        group_quadrupoles_by_cell=True,
        output_path=tmp_path / "poco",
    )

    losses = [loss for _, loss in history]
    assert result.knobs and len(losses) > 1
    assert min(losses) < losses[0] / 10.0, f"misfit only went {losses[0]:.3e} -> {min(losses):.3e}"


def _poco_absolute_settings(line, bpms, correctors, dk):
    """Settings for the absolute-y mode: x differenced (as :func:`_poco_deltas`), y kept as the machine's closed orbit."""
    import xtrack_tools as xtt

    from poco.settings import CorrectorSetting

    def orbit(corrector=None, step=0.0):
        if corrector is not None:
            element = line[corrector.lower()]
            vertical = "dvt" in corrector.lower()
            attribute = "ksl" if vertical else "knl"
            original = float(getattr(element, attribute)[0])
            getattr(element, attribute)[0] = original + (step if vertical else -step)
        table = xtt.xsuite_tws_to_ng(line.twiss(method="4d")).loc[bpms]
        if corrector is not None:
            getattr(element, attribute)[0] = original
        return table

    nominal = orbit()
    settings = []
    for corrector in correctors:
        kicked = orbit(corrector, dk)
        frame = pd.DataFrame(index=pd.Index(bpms, name="NAME"))
        frame["X"] = kicked["x"] - nominal["x"]
        frame["Y"] = kicked["y"]  # absolute: no reference removed
        frame["ERRX"] = 1e-7
        # The floor the CLI applies, standing in for the BPM offsets not fitted.
        frame["ERRY"] = 1e-4
        settings.append(
            CorrectorSetting(
                corrector=corrector,
                knob="k" + corrector.replace(".", "").lower(),
                offset_k=dk,
                orbit=frame,
                dk=dk,
            )
        )
    return settings


def test_absolute_y_recovers_the_vertical_orbit_the_delta_fit_cannot_see(
    truth_line, bpm_names, loco_model, sequence_file, tmp_path
):
    """Keeping the vertical closed orbit lets quadrupole ``dy`` explain it.

    ``truth_line`` has a 2e-4 rms vertical misalignment the delta fit cannot see. Asserted on the
    derived quantity: the fitted model's vertical closed orbit must be substantially closer than the nominal's.
    """
    from poco.run_poco import run as run_poco
    from tests.madng_helpers import closed_orbit, open_interface

    bpms = [name.upper() for name in bpm_names]
    settings = _poco_absolute_settings(truth_line, bpms, CORRECTORS, dk=5e-4)

    knobs = run_poco(
        settings,
        loco_model,
        max_iterations=10,
        absolute_planes=("y",),
        errors={},
        misalignments={"quad": {"dy"}},
        output_path=tmp_path / "poco_absolute",
    )[0].knobs
    assert knobs and all(name.endswith(".dy") for name in knobs), (
        f"expected quadrupole dy knobs only, got {sorted(knobs)[:5]}"
    )

    truth = settings[0].orbit["Y"].to_numpy()
    # Knob-carrying interface, so the dy knobs exist under the names the fit reported.
    interface = open_interface(sequence_file, misalignments={"quad": {"dy"}})
    try:
        start = closed_orbit(interface).loc[bpms, "Y"].to_numpy()
        for name, value in knobs.items():
            interface.mad.send(f"loaded_sequence['{name}'] = {float(value):.15e}")
        fitted = closed_orbit(interface).loc[bpms, "Y"].to_numpy()
    finally:
        interface.mad.close()

    before, after = _rms(start - truth), _rms(fitted - truth)
    assert _rms(truth) > 1e-4, "the misalignment must actually show in the orbit"
    # Margin is wide of the achieved 3.1e-3 -> 1.1e-5 (factor 277), so the test fails on breakage, not drift.
    assert after < before / 20.0, (
        f"vertical orbit distance to the machine only went {before:.3e} -> {after:.3e}"
    )
