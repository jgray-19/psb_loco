"""Acceptance: both methods recover a known machine, and agree with each other.

Compared on recovered *responses*, not knobs: the closed-orbit null space is large (knobs came back 59-79% wrong with a good derived quantity).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from loco_common.model import LocoModel

pytestmark = pytest.mark.slow

CORRECTORS = [
    "BR3.DHZ8L1", "BR3.DHZ9L1", "BR3.DHZ11L4", "BR3.DHZ12L4", "BR3.DHZ13L4", "BR3.DHZ14L1",
    "BR3.DVT2L4", "BR3.DVT6L4", "BR3.DVT8L1", "BR3.DVT9L1", "BR3.DVT12L4", "BR3.DVT13L4",
]
PLANES = ["y" if "DVT" in name else "x" for name in CORRECTORS]
DK = 1e-5


@pytest.fixture
def loco_model(sequence_file) -> LocoModel:
    """A bare ring-3 model: the fake machine carries its own state, not a campaign's."""
    return LocoModel(sequence_file=sequence_file, tune_knobs={}, corrector_knobs={})


@pytest.fixture
def truth_response(truth_line, fake_response) -> pd.DataFrame:
    return fake_response(truth_line, CORRECTORS, dk=DK)


def _target_matrix(response: pd.DataFrame, bpms: list[str], correctors: list[str]) -> np.ndarray:
    """The measured response on a given (BPM, corrector) grid, in MAD's convention.

    Slopes are per LSA ``/K`` and divided by :func:`lsa_k_to_rad`, as ``run_method1._matrices`` does.
    Corrector order is a parameter: ``run_method1`` sorts, a direct ``response_da`` readout keeps the given order.
    """
    from loco_common.naming import lsa_k_to_rad

    indexed = response.set_index(["NAME", "PLANE", "CORRECTOR"])["SLOPE"]
    return np.array(
        [
            [
                indexed[(bpm, plane, corrector)] / lsa_k_to_rad(corrector)
                for corrector in correctors
            ]
            for plane in ("x", "y")
            for bpm in bpms
        ]
    )


def _rms(matrix: np.ndarray) -> float:
    return float(np.sqrt(np.mean(matrix**2)))


def test_method1_recovers_the_response_without_noise(truth_response, loco_model):
    """The zero-noise case: the one to debug with, so it is asserted hard."""
    from method1_madng_da.run_method1 import run

    result = run(truth_response, loco_model, max_call=60, info_level=0)

    before = result.residual_rms(result.response_before)
    after = result.residual_rms(result.response_after)
    assert before > 1e-3, "the injected errors must actually show in the response"
    # Truth has per-magnet errors but Method 1 uses the 32-knob cell topology; it must still remove most of the response error.
    assert after < before / 5.0, f"response residual only went {before:.3e} -> {after:.3e}"


def test_method1_still_moves_toward_truth_under_noise(truth_response, loco_model):
    """With noisy slopes the fit is measured against the *noiseless* truth: is the fitted model closer to the machine than the start?"""
    from method1_madng_da.run_method1 import run

    # 0.1% of the largest response: the injected 1e-3 gradient errors change the response by well under a percent, so much more noise would leave more noise than signal.
    rng = np.random.default_rng(11)
    noise = 0.001 * np.abs(truth_response["SLOPE"]).max()
    noisy = truth_response.assign(
        SLOPE=truth_response["SLOPE"] + rng.normal(0.0, noise, len(truth_response)),
        ERRSLOPE=noise,
    )

    result = run(noisy, loco_model, max_call=60, info_level=0)

    truth = _target_matrix(truth_response, result.bpm_names, result.correctors)
    before = _rms(result.response_before - truth)
    after = _rms(result.response_after - truth)
    assert before > 1e-3
    assert after < before / 2.0, f"distance to truth only went {before:.3e} -> {after:.3e}"


def _method2_deltas(line, bpms, correctors, dk):
    """Measured delta orbits for Method 2, from the same truth line."""
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


def test_both_methods_agree_more_closely_than_either_agrees_with_the_start(
    truth_response, truth_line, bpm_names, loco_model, sequence_file, tmp_path
):
    """The acceptance evidence: a parametric-twiss match and a summed-gradient orbit fit, sharing no solver or objective, reproduce the same machine."""
    from method1_madng_da.run_method1 import run as run_method1
    from method2_delta_orbit.run_method2 import CorrectorSetting
    from method2_delta_orbit.run_method2 import run as run_method2
    from tests.madng_helpers import response_with_knobs

    bpms = [name.upper() for name in bpm_names]
    dk = 5e-4  # a large trim, so the delta orbit is well above the BPM noise floor

    first = run_method1(truth_response, loco_model, max_call=60, info_level=0)

    frames = _method2_deltas(truth_line, bpms, CORRECTORS, dk)
    settings = [
        CorrectorSetting(
            corrector=corrector,
            knob="k" + corrector.replace(".", "").lower(),
            offset_k=dk,
            orbit=frame,
            dk=dk,
        )
        for corrector, frame in frames.items()
    ]
    knobs, _, _ = run_method2(
        settings,
        loco_model,
        max_iterations=10,
        group_quadrupoles_by_cell=True,
        output_path=tmp_path / "method2",
    )

    names, response_start = response_with_knobs(sequence_file, CORRECTORS, {})
    _, response_first = response_with_knobs(sequence_file, CORRECTORS, first.knobs)
    _, response_second = response_with_knobs(sequence_file, CORRECTORS, knobs)

    truth = _target_matrix(truth_response, names, CORRECTORS)
    start_error = _rms(response_start - truth)
    assert start_error > 1e-3

    between_methods = _rms(response_first - response_second)
    from_start = max(_rms(response_first - response_start), _rms(response_second - response_start))
    assert between_methods < from_start / 5.0, (
        f"the methods differ by {between_methods:.3e}, having each moved "
        f"{from_start:.3e} from the starting model"
    )
    assert _rms(response_first - truth) < start_error / 10.0
    assert _rms(response_second - truth) < start_error / 2.0


def _method2_absolute_settings(line, bpms, correctors, dk):
    """Settings for the absolute-y mode: x differenced (as :func:`_method2_deltas`), y kept as the machine's closed orbit."""
    import xtrack_tools as xtt

    from method2_delta_orbit.run_method2 import CorrectorSetting

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
                absolute_planes=("y",),
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
    from method2_delta_orbit.run_method2 import run as run_method2
    from tests.madng_helpers import closed_orbit, open_interface

    bpms = [name.upper() for name in bpm_names]
    settings = _method2_absolute_settings(truth_line, bpms, CORRECTORS, dk=5e-4)

    knobs, _, _ = run_method2(
        settings,
        loco_model,
        max_iterations=10,
        errors={},
        misalignments={"quad": {"dy"}},
        output_path=tmp_path / "method2_absolute",
    )
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
