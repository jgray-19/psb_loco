"""``--fit-gains`` recovers a corrector that delivers other than the kick it was asked for."""

from __future__ import annotations

import pandas as pd
import pytest

from loco_common.model import LocoModel
from loco_common.naming import lsa_to_knob
from poco.run_poco import run
from poco.settings import CorrectorSetting

pytestmark = pytest.mark.slow

CORRECTORS = ["BR3.DHZ8L1", "BR3.DHZ9L1", "BR3.DVT2L4", "BR3.DVT6L4"]
STEPS = (5e-4, -5e-4)
#: DHZ8L1 delivers 20 % less kick than it is asked for.
GAINS = {"BR3.DHZ8L1": -0.2}


def _delta_orbits(sequence_file) -> list[CorrectorSetting]:
    """Orbit changes of the bare model with every kick scaled by ``1 + gain``, as the scan would report them."""
    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    interface = open_interface(sequence_file)
    try:
        for corrector in CORRECTORS:
            set_knob(interface, lsa_to_knob(corrector), 0.0)
        nominal = closed_orbit(interface)
        settings = []
        for corrector in CORRECTORS:
            knob = lsa_to_knob(corrector)
            for dk in STEPS:
                set_knob(interface, knob, dk * (1.0 + GAINS.get(corrector, 0.0)))
                kicked = closed_orbit(interface)
                set_knob(interface, knob, 0.0)
                frame = (kicked - nominal).assign(ERRX=1e-7, ERRY=1e-7)
                settings.append(CorrectorSetting(corrector, knob, dk, frame, dk=dk))
        return settings
    finally:
        interface.mad.close()


def test_a_corrector_gain_error_is_fitted_not_absorbed_by_the_quadrupoles(sequence_file, tmp_path):
    model = LocoModel(
        sequence_file=sequence_file,
        tune_knobs={},
        corrector_knobs={lsa_to_knob(corrector): 0.0 for corrector in CORRECTORS},
    )

    result, history = run(
        _delta_orbits(sequence_file),
        model,
        fit_gains=True,
        sigma_corrector=0.5,
        max_iterations=40,
        output_path=tmp_path,
    )

    gains = pd.Series(result.extra)
    # A plane's overall scale is its BPM gains' too: only differences between correctors of one plane are determined.
    assert gains["corrgain.DHZ8L1"] - gains["corrgain.DHZ9L1"] == pytest.approx(GAINS["BR3.DHZ8L1"], abs=0.03)
    assert gains["corrgain.DVT2L4"] - gains["corrgain.DVT6L4"] == pytest.approx(0.0, abs=0.03)
    assert history[-1][1] < history[0][1] / 10.0
