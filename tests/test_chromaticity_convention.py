import math

import numpy as np
import pytest

from loco_common.chromaticity import PROTON_MASS_GEV, chromaticity_from_dq_dpt
from scripts.measured_optics import fit_chromaticity_all_ctimes


def test_madng_dq_dpt_is_converted_to_dq_ddelta_without_tune_normalisation():
    gamma = 1.2
    beta = math.sqrt(1.0 - 1.0 / gamma**2)
    headers = {
        "energy": gamma * PROTON_MASS_GEV,
        "q1": 4.17,
        "q2": 4.23,
        "dq1": -6.5,
        "dq2": -13.0,
    }

    horizontal, vertical = chromaticity_from_dq_dpt(headers)

    assert horizontal == pytest.approx(beta * headers["dq1"])
    assert vertical == pytest.approx(beta * headers["dq2"])
    assert horizontal != pytest.approx(beta * headers["dq1"] / headers["q1"])


def test_all_ctimes_share_one_slope_but_keep_independent_tune_intercepts():
    pt = np.array([
        [-2e-3, -2e-3, -2e-3],
        [-1e-3, -1e-3, -1e-3],
        [0.0, 0.0, 0.0],
        [1e-3, 1e-3, 1e-3],
        [2e-3, 2e-3, 2e-3],
    ])
    intercepts = np.array([4.17, 4.18, 4.16])
    tunes = intercepts + (-6.5 * pt)

    slope, error, fitted_intercepts = fit_chromaticity_all_ctimes(tunes, pt)

    assert slope == pytest.approx(-6.5)
    assert error == pytest.approx(0.0, abs=1e-10)
    assert fitted_intercepts == pytest.approx(intercepts)


@pytest.mark.slow
def test_madng_twiss_dispersion_and_chromaticity_are_derivatives_by_pt(sequence_file):
    """Pin the MAD-NG convention against explicit method-6 finite differences."""
    from adelmo.machine.accelerators.psb import PSB as OptimiserPSB
    from adelmo.machine.mad.optimising_mad_interface import GenericMadInterface

    accelerator = OptimiserPSB(ring=3, sequence_file=sequence_file, kinetic_energy=0.16)
    interface = GenericMadInterface(accelerator=accelerator)
    dpp = 1e-4
    pt = accelerator.dp2pt(dpp)
    try:
        nominal = interface.run_twiss(observe=1, method=6)
        positive = interface.run_twiss(observe=1, deltap=dpp, method=6)
        negative = interface.run_twiss(observe=1, deltap=-dpp, method=6)
    finally:
        interface.close()

    common = nominal.index.intersection(positive.index).intersection(negative.index)
    dispersion_fd = (
        positive.loc[common, "x"].to_numpy(dtype=float)
        - negative.loc[common, "x"].to_numpy(dtype=float)
    ) / (2 * pt)
    assert dispersion_fd == pytest.approx(
        nominal.loc[common, "dx"].to_numpy(dtype=float), rel=5e-4, abs=1e-7
    )
    for plane in (1, 2):
        tune_fd = (
            float(positive.headers[f"q{plane}"])
            - float(negative.headers[f"q{plane}"])
        ) / (2 * pt)
        assert float(nominal.headers[f"dq{plane}"]) == pytest.approx(tune_fd, rel=5e-4)
