"""Method 2's optional multi-momentum mode, and what a wrong ``pt`` costs.

The five RF-steering settings are five momenta, but the scan records a radial
offset in millimetres, not a ``dp/p``. Everything here is about the consequence
of that: the momentum has to be estimated, so these tests check both that the
estimate is right and what happens when it is not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from loco_common.momentum import estimate_pt, frame_from_orbit

pytestmark = pytest.mark.slow

KNOWN_PT = (-1e-3, -5e-4, 5e-4, 1e-3)


def _ng_twiss(line, bpms, *, pt: float = 0.0):
    """The line's twiss at a known ``pt``, in MAD-NG conventions.

    xsuite's ``delta0`` is ``dp/p``; MAD-NG's ``pt`` is not. At PSB flat bottom
    ``beta0`` is 0.52, so the two differ by nearly a factor of two. The
    conversion goes through :func:`pymadng_utils.physics.pt2dp` -- the same
    closed form MAD-NG's own ``gphys`` uses -- rather than a series expanded
    here, so the test pins the production convention and not a copy of it.
    """
    import xtrack_tools as xtt
    from pymadng_utils.physics import pt2dp

    beta0 = float(np.atleast_1d(line.particle_ref.beta0)[0])
    return xtt.xsuite_tws_to_ng(line.twiss(method="4d", delta0=pt2dp(pt, beta0))).loc[bpms]


def _orbit(twiss) -> pd.DataFrame:
    return pd.DataFrame({"X": twiss["x"], "Y": twiss["y"]}, index=twiss.index)


@pytest.fixture
def bpms(bpm_names) -> list[str]:
    return [name.upper() for name in bpm_names]


@pytest.mark.parametrize("pt", KNOWN_PT)
def test_pt_is_recovered_from_the_dispersive_orbit(psb_line, bpms, pt):
    model = _ng_twiss(psb_line, bpms)
    frame = frame_from_orbit(_orbit(model), model)

    estimate = estimate_pt(_orbit(_ng_twiss(psb_line, bpms, pt=pt)), model, frame)

    assert estimate == pytest.approx(pt, rel=2e-2)


def test_the_estimate_is_monotonic_in_momentum(psb_line, bpms):
    model = _ng_twiss(psb_line, bpms)
    frame = frame_from_orbit(_orbit(model), model)

    estimates = [
        estimate_pt(_orbit(_ng_twiss(psb_line, bpms, pt=pt)), model, frame)
        for pt in KNOWN_PT
    ]

    assert np.all(np.diff(estimates) > 0)


def test_a_retained_plane_needs_fitted_angles(psb_line, bpms):
    """The frame refuses to invent the closed-orbit angles it is not given.

    This mode relies on the momentum being an offset from a *measured* orbit
    zero: a dipole error is exactly degenerate with the dispersive orbit at a
    single momentum, so a modelled origin would bias ``pt`` by tens of percent
    while looking perfectly reasonable. :func:`frame_from_orbit` makes both
    planes dynamic, which subtracts that measured orbit and needs no angles;
    the moment a plane is retained instead, ``tmom_recon`` demands explicitly
    fitted momenta rather than falling back to a model or to zero.
    """
    from tmom_recon import ReconstructionFrame

    model = _ng_twiss(psb_line, bpms)
    orbit_zero = _orbit(model).rename(columns={"X": "x", "Y": "y"})

    with pytest.raises(ValueError, match="fitted"):
        ReconstructionFrame(orbit_zero=orbit_zero, dynamic_planes=("y",))


def test_the_frame_subtracts_the_measured_origin(psb_line, bpms):
    """Both planes dynamic, so the origin leaves the data before the projection."""
    model = _ng_twiss(psb_line, bpms)
    frame = frame_from_orbit(_orbit(model), model)

    assert frame.dynamic_planes == ("x", "y")
    assert frame.fitted_momenta is None
    prepared = frame.prepare_data(
        pd.DataFrame(
            {
                "name": list(model.index),
                "x": model["x"].to_numpy(dtype=float),
                "y": model["y"].to_numpy(dtype=float),
            }
        )
    )
    assert prepared[["x", "y"]].abs().to_numpy().max() == pytest.approx(0.0, abs=1e-12)


def _delta_settings(line, bpms, correctors, dk, pt):
    """Measured delta orbits at one momentum, as Method-2 settings.

    The reference subtracted is the *global* one -- untrimmed correctors at
    ``pt = 0`` -- not the untrimmed orbit at this momentum, matching what
    ``loco_common.measured_response`` does to the real data. Each delta therefore
    carries this momentum's dispersion orbit on top of the corrector response,
    which is precisely why the momentum has to be right.
    """
    from method2_delta_orbit.run_method2 import CorrectorSetting

    nominal = _ng_twiss(line, bpms, pt=0.0)
    settings = []
    for corrector in correctors:
        element = line[corrector.lower()]
        vertical = "dvt" in corrector.lower()
        attribute = "ksl" if vertical else "knl"
        original = float(getattr(element, attribute)[0])
        getattr(element, attribute)[0] = original + (dk if vertical else -dk)
        try:
            kicked = _ng_twiss(line, bpms, pt=pt)
        finally:
            getattr(element, attribute)[0] = original
        frame = pd.DataFrame(index=pd.Index(bpms, name="NAME"))
        frame["X"] = kicked["x"] - nominal["x"]
        frame["Y"] = kicked["y"] - nominal["y"]
        frame["ERRX"] = frame["ERRY"] = 1e-7
        settings.append(
            CorrectorSetting(
                corrector=corrector,
                knob="k" + corrector.replace(".", "").lower(),
                offset_k=dk,
                orbit=frame,
                dk=dk,
                pt=pt,
                reference_pt=0.0,
            )
        )
    return settings


def _distance_to_truth(knobs: dict[str, float], truth_errors, psb_line) -> float:
    """Euclidean distance from a fitted knob set to the errors that were installed.

    The knobs are ``dk1l`` -- integrated -- so the truth is each quadrupole's
    ``k1`` error times its length. Quadrupoles with no installed error count too:
    inventing gradient where there was none is exactly the failure being measured.
    """
    truth = {
        f"{name.lower()}.dk1l": error * float(psb_line[name].length)
        for name, error in truth_errors.items()
    }
    return float(np.linalg.norm([value - truth.get(knob, 0.0) for knob, value in knobs.items()]))


def test_a_wrong_pt_costs_more_than_it_gains(
    truth_line, truth_errors, psb_line, bpms, sequence_file, tmp_path
):
    """Bound the price of a bad estimate: it is a bias, not extra noise.

    With the global reference the delta orbit at a non-zero momentum *contains*
    that momentum's dispersion, so telling the model the wrong ``pt`` hands the
    quadrupoles a first-order orbit that has nothing to do with them. The
    measurable consequence is a fit that lands further from the installed errors,
    which is why the multi-momentum mode is opt-in rather than the default.

    The margin here is deliberately modest -- a 20% error in the estimate. Larger
    ones do not degrade gracefully: a sign error walks the quadrupoles into an
    unstable lattice and MAD's normal form fails rather than returning a bad
    answer.
    """
    from loco_common.model import LocoModel
    from method2_delta_orbit.run_method2 import run

    model = LocoModel(sequence_file=sequence_file, tune_knobs={}, corrector_knobs={})
    correctors = ["BR3.DHZ8L1", "BR3.DVT2L4"]
    dk, true_pt = 5e-4, 1e-3

    settings = _delta_settings(truth_line, bpms, correctors, dk, true_pt)
    correct, _, _ = run(settings, model, max_iterations=8, output_path=tmp_path / "right")

    for setting in settings:
        # A plausibly-bad estimate, not an absurd one: 20% low. Flipping the sign
        # drives the quadrupoles far enough to make the lattice unstable and MAD's
        # normal form fail outright, which is a real result about how unforgiving
        # this is but not something a test can assert on.
        setting.pt = 0.8 * true_pt
    wrong, _, _ = run(settings, model, max_iterations=8, output_path=tmp_path / "wrong")

    correct_error = _distance_to_truth(correct, truth_errors, psb_line)
    wrong_error = _distance_to_truth(wrong, truth_errors, psb_line)
    assert wrong_error > 2.0 * correct_error, (
        "a 20%-low pt should visibly degrade the recovered gradients; "
        f"got {wrong_error:.3e} against {correct_error:.3e}"
    )
