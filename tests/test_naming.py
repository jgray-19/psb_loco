"""Corrector names and the one unit assumption the fit rests on."""

from __future__ import annotations

import numpy as np
import pytest

from loco_common.naming import (
    LSA_K_TO_RAD,
    element_to_knob,
    lsa_to_element,
    lsa_to_knob,
    plane_of,
)

SCANNED = [
    "logical.BR3.DHZ8L1/K", "logical.BR3.DHZ9L1/K", "logical.BR3.DHZ11L4/K",
    "logical.BR3.DHZ12L4/K", "logical.BR3.DHZ13L4/K", "logical.BR3.DHZ14L1/K",
    "logical.BR3.DVT2L4/K", "logical.BR3.DVT6L4/K", "logical.BR3.DVT8L1/K",
    "logical.BR3.DVT9L1/K", "logical.BR3.DVT12L4/K", "logical.BR3.DVT13L4/K",
]


@pytest.mark.parametrize("parameter", SCANNED)
def test_lsa_element_knob_round_trip(parameter):
    element = lsa_to_element(parameter)
    knob = lsa_to_knob(parameter)
    assert knob == element_to_knob(element)


@pytest.mark.parametrize("parameter", SCANNED)
def test_plane_follows_the_corrector_family(parameter):
    assert plane_of(parameter) == ("y" if "DVT" in parameter.upper() else "x")


@pytest.mark.slow
@pytest.mark.parametrize("parameter", ["logical.BR3.DHZ8L1/K", "logical.BR3.DVT2L4/K"])
def test_every_scanned_corrector_exists_in_the_model(sequence_file, parameter):
    from tests.madng_helpers import open_interface

    interface = open_interface(sequence_file)
    try:
        interface.mad.send(
            f"py:send(loaded_sequence['{lsa_to_element(parameter)}'] ~= nil, true)"
        )
        assert interface.mad.recv()
    finally:
        interface.close()


@pytest.mark.slow
def test_lsa_k_is_a_kick_in_radians(sequence_file, psb_line, bpm_names, fake_orbits):
    """Pin the *magnitude* ``LSA_K_TO_RAD``: one ``/K`` step through both codes.

    This is the one assumption in the fit that no residual would expose. If LSA's
    ``/K`` were not the kick angle in rad, every fitted gradient would be wrong by
    the same factor and every method would agree on the wrong answer, so it is
    checked against a second code rather than asserted.

    It says nothing about the *sign*, and cannot: both codes here are models, and
    the fixture adopts MAD's convention on the xsuite side by construction
    (``knl[0] = -hkick``). Only the machine knows the sign of LSA's ``/K``; see
    ``test_horizontal_lsa_k_is_inverted_in_the_measurement`` below.
    """
    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    parameter = "logical.BR3.DHZ8L1/K"
    step_k = 1e-4
    xsuite_delta = (
        fake_orbits(psb_line, lsa_to_element(parameter), step_k)["X"]
        - fake_orbits(psb_line)["X"]
    )

    interface = open_interface(sequence_file)
    try:
        before = closed_orbit(interface)
        set_knob(interface, lsa_to_knob(parameter), step_k * LSA_K_TO_RAD)
        after = closed_orbit(interface)
    finally:
        interface.close()

    common = [bpm for bpm in after.index if bpm in xsuite_delta.index]
    assert len(common) > 8
    ng_delta = (after.loc[common, "X"] - before.loc[common, "X"]).to_numpy()
    xs_delta = xsuite_delta.loc[common].to_numpy()
    scale = np.max(np.abs(xs_delta))
    assert scale > 1e-5, "the test step must actually move the orbit"
    np.testing.assert_allclose(ng_delta, xs_delta, atol=0.02 * scale)


@pytest.mark.slow
def test_horizontal_lsa_k_is_inverted_in_the_measurement(sequence_file):
    """The evidence behind ``LSA_K_SIGN``, re-derived from the cached measurement.

    Applying the signed conversion has to make the measured response *agree in
    sign* with the model for both planes. Under the wrong convention the six DHZ
    correctors come back at correlation -0.998 while the six DVT sit at +0.999,
    which is not something a quadrupole error can do -- no gradient error flips
    the sign of a corrector's response at every BPM at once.

    Skipped without the acquisition cache, since only the machine can settle this.
    """
    import numpy as np

    from loco_common.campaign import P23_P13_FINAL
    from loco_common.naming import lsa_k_to_rad

    cache = P23_P13_FINAL.cache_file("response_xy_rfp0.parquet")
    if not cache.exists():
        pytest.skip("needs the cached measured response (build it from the mount)")

    import pandas as pd

    from method1_madng_da.run_method1 import _matrices
    from tests.madng_helpers import open_response_interface, setup_response_da

    response = pd.read_parquet(cache)
    correctors = sorted(response["CORRECTOR"].unique())
    interface = open_response_interface(sequence_file)
    try:
        bpms, model = setup_response_da(
            interface,
            [lsa_to_element(name) for name in correctors],
        )
    finally:
        interface.close()

    target, weight = _matrices(response, bpms, correctors)
    for i, corrector in enumerate(correctors):
        offset = 0 if plane_of(corrector) == "x" else len(bpms)
        rows = slice(offset, offset + len(bpms))
        usable = weight[rows, i] > 0
        if usable.sum() < 8:
            continue
        correlation = np.corrcoef(target[rows, i][usable], model[rows, i][usable])[0, 1]
        assert correlation > 0.9, (
            f"{corrector} response is anti-correlated with the model "
            f"({correlation:+.3f}) -- LSA_K_SIGN[{plane_of(corrector)!r}] is wrong"
        )
        assert lsa_k_to_rad(corrector) != 0.0
