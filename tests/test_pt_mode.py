"""POCO's multi-momentum mode: the momentum has to be estimated (the scan records mm, not ``dp/p``), so test the estimate and the cost of a wrong one."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from loco_common.momentum import estimate_pt, frame_from_orbit
from loco_common.naming import lsa_to_knob

pytestmark = pytest.mark.slow

KNOWN_PT = (-1e-3, -5e-4, 5e-4, 1e-3)


def _ng_twiss(line, bpms, *, pt: float = 0.0):
    """The line's twiss at a known ``pt``, in MAD-NG conventions.

    xsuite's ``delta0`` is ``dp/p``, which differs from ``pt`` by nearly a factor of two at PSB flat
    bottom; converted with :func:`pymadng_utils.physics.pt2dp`, MAD-NG's own closed form.
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


def test_the_frame_is_the_measured_orbit_origin(psb_line, bpms):
    """The frame is the measured nominal-RF orbit itself, so that orbit has zero momentum offset."""
    model = _ng_twiss(psb_line, bpms)
    orbit = _orbit(model)
    frame = frame_from_orbit(orbit, model)

    assert list(frame.columns) == ["x", "y"]
    assert frame.index.name == "name"
    assert frame["x"].to_numpy() == pytest.approx(orbit["X"].to_numpy(dtype=float))
    assert estimate_pt(orbit, model, frame) == pytest.approx(0.0, abs=1e-9)


def _delta_settings(line, bpms, correctors, dk, pt):
    """Measured delta orbits at one momentum, as POCO settings.

    The reference is the *global* one (``pt = 0``), as in ``loco_common.measured_response``, so each
    delta carries this momentum's dispersion orbit.
    """
    from poco.settings import CorrectorSetting

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
            )
        )
    return settings


def _distance_to_truth(knobs: dict[str, float], truth_errors, psb_line) -> float:
    """Euclidean distance from a fitted knob set to the installed errors (``dk1l`` = ``k1`` error times length; unerrored quadrupoles count)."""
    truth = {
        f"{name.lower()}.dk1l": error * float(psb_line[name].length)
        for name, error in truth_errors.items()
    }
    return float(np.linalg.norm([value - truth.get(knob, 0.0) for knob, value in knobs.items()]))


def test_a_wrong_pt_costs_more_than_it_gains(
    truth_line, truth_errors, psb_line, bpms, sequence_file, tmp_path
):
    """Bound the price of a bad estimate: a bias, not extra noise.

    A wrong ``pt`` hands the quadrupoles a first-order dispersion orbit, so the fit lands further from
    the installed errors (hence the mode is opt-in). The margin is modest (20% error); a sign error
    makes the lattice unstable and MAD's normal form fails.
    """
    from loco_common.model import LocoModel
    from poco.run_poco import run

    correctors = ["BR3.DHZ8L1", "BR3.DVT2L4"]
    model = LocoModel(
        sequence_file=sequence_file,
        tune_knobs={},
        corrector_knobs={lsa_to_knob(corrector): 0.0 for corrector in correctors},
    )
    dk, true_pt = 5e-4, 1e-3

    settings = _delta_settings(truth_line, bpms, correctors, dk, true_pt)
    correct = run(settings, model, max_iterations=8, output_path=tmp_path / "right")[0].knobs

    # 20% low; a sign flip makes the lattice unstable and MAD's normal form fail.
    biased = [replace(setting, pt=0.8 * true_pt) for setting in settings]
    wrong = run(biased, model, max_iterations=8, output_path=tmp_path / "wrong")[0].knobs

    correct_error = _distance_to_truth(correct, truth_errors, psb_line)
    wrong_error = _distance_to_truth(wrong, truth_errors, psb_line)
    assert wrong_error > 2.0 * correct_error, (
        "a 20%-low pt should visibly degrade the recovered gradients; "
        f"got {wrong_error:.3e} against {correct_error:.3e}"
    )
