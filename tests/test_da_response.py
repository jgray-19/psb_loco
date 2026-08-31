"""Method 1's first-order DA response-matrix construction."""

from __future__ import annotations

import numpy as np
import pytest

from loco_common.naming import lsa_to_element

pytestmark = pytest.mark.slow

CORRECTORS = ["logical.BR3.DHZ8L1/K", "logical.BR3.DVT2L4/K"]
DK = 1e-5


@pytest.fixture
def da_interface(sequence_file):
    from tests.madng_helpers import open_response_interface, setup_response_da

    interface = open_response_interface(sequence_file)
    try:
        names, response = setup_response_da(
            interface, [lsa_to_element(name) for name in CORRECTORS]
        )
        yield interface, names, response
    finally:
        interface.close()


def _finite_difference_response(sequence_file, corrector: str, bpms: list[str]):
    from loco_common.naming import lsa_to_knob
    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    interface = open_interface(sequence_file)
    try:
        knob = lsa_to_knob(corrector)
        set_knob(interface, knob, DK)
        plus = closed_orbit(interface)
        set_knob(interface, knob, -DK)
        minus = closed_orbit(interface)
    finally:
        interface.close()
    return (plus.loc[bpms] - minus.loc[bpms]) / (2.0 * DK)


def test_response_has_one_row_per_bpm_channel(da_interface):
    _interface, names, response = da_interface
    assert response.shape == (2 * len(names), len(CORRECTORS))


def test_parametric_response_matches_finite_differences(sequence_file, da_interface):
    _interface, names, response = da_interface
    nbpm = len(names)
    for corr, corrector in enumerate(CORRECTORS):
        expected = _finite_difference_response(sequence_file, corrector, names)
        for plane, column in enumerate(("X", "Y")):
            actual = response[plane * nbpm : (plane + 1) * nbpm, corr]
            truth = expected[column].to_numpy()
            scale = max(float(np.max(np.abs(truth))), 1.0)
            np.testing.assert_allclose(actual, truth, rtol=2e-3, atol=1e-4 * scale)


def test_quadrupoles_use_the_native_32_knob_topology(da_interface):
    interface, _names, _response = da_interface
    knobs = interface.knob_names
    assert len(knobs) == 32
    assert len([name for name in knobs if ".QFOCELL" in name]) == 16
    assert len([name for name in knobs if ".QDE" in name]) == 16


def test_each_matrix_cell_accepts_its_own_weight(da_interface):
    interface, _names, response = da_interface
    weights = np.arange(response.size, dtype=float).reshape(response.shape) + 1.0
    weights[0, 0] = 0.0
    interface.mad["target_mat"] = response
    interface.mad["weight_mat"] = weights
    interface.mad.send("py:send({run_match(1, 1e-12, 0)}, true)")
    status, fmin, ncall = interface.mad.recv()
    assert status == "FMIN"
    assert float(fmin) == pytest.approx(0.0, abs=1e-14)
    assert int(ncall) == 1
