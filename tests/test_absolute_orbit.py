"""The absolute-orbit mode: which plane keeps its closed orbit, and what pays for it.

Method 2's default subtracts the global reference orbit from both the data and
the model, which makes it a pure response fit and throws the machine's static
closed orbit away. These tests cover the mode that keeps that orbit in a chosen
plane, and -- more importantly -- pin that switching it on changes *nothing* in
the plane that stayed a delta, and nothing at all when it is off.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from loco_common.measured_response import (
    apply_error_floor,
    measured_orbits,
    subtract_reference,
)
from method2_delta_orbit.run_method2 import CorrectorSetting

CORRECTOR = "logical.BR3.DHZ8L1/K"
SLOPES = {"BR3.BPM1L3": 12.5, "BR3.BPM2L3": -4.0, "BR3.BPM3L3": 0.0}
BASELINE = 5e-3


def _frame(values_x, values_y, error=1e-6) -> pd.DataFrame:
    index = pd.Index([f"BPM{i}" for i in range(len(values_x))], name="NAME")
    return pd.DataFrame(
        {
            "X": np.asarray(values_x, dtype=float),
            "ERRX": np.full(len(values_x), error),
            "Y": np.asarray(values_y, dtype=float),
            "ERRY": np.full(len(values_y), error),
        },
        index=index,
    )


# --------------------------------------------------------------- data side


def test_an_absolute_plane_keeps_its_orbit_and_the_other_does_not():
    frame = _frame([1.0, 2.0], [3.0, 4.0])
    reference = _frame([0.5, 0.5], [1.0, 1.0])

    delta = subtract_reference(frame, reference, absolute_planes=("y",))

    np.testing.assert_allclose(delta["X"], [0.5, 1.5])
    np.testing.assert_allclose(delta["Y"], [3.0, 4.0])


def test_an_absolute_plane_does_not_inherit_the_references_error():
    """There is no reference on that side, so there is no error to add."""
    frame = _frame([1.0, 2.0], [3.0, 4.0], error=3e-6)
    reference = _frame([0.5, 0.5], [1.0, 1.0], error=4e-6)

    delta = subtract_reference(frame, reference, absolute_planes=("y",))

    np.testing.assert_allclose(delta["ERRX"], 5e-6)  # hypot(3, 4) micron
    np.testing.assert_allclose(delta["ERRY"], 3e-6)


def test_no_absolute_planes_is_the_untouched_default():
    frame, reference = _frame([1.0, 2.0], [3.0, 4.0]), _frame([0.5, 0.5], [1.0, 1.0])
    pd.testing.assert_frame_equal(
        subtract_reference(frame, reference), subtract_reference(frame, reference, ())
    )


def test_an_unknown_plane_is_rejected():
    frame = _frame([1.0], [1.0])
    with pytest.raises(ValueError, match="Unknown plane"):
        subtract_reference(frame, frame, absolute_planes=("z",))


def test_the_error_floor_touches_only_the_named_plane():
    frame = _frame([1.0, 2.0], [3.0, 4.0], error=3e-5)
    floored = apply_error_floor(frame, 4e-5, ("y",))

    np.testing.assert_allclose(floored["ERRX"], 3e-5)
    np.testing.assert_allclose(floored["ERRY"], 5e-5)
    np.testing.assert_allclose(floored["Y"], frame["Y"])


def test_a_zero_floor_is_the_identity():
    frame = _frame([1.0], [1.0])
    pd.testing.assert_frame_equal(apply_error_floor(frame, 0.0, ("x", "y")), frame)


def test_the_untrimmed_acquisitions_survive_only_in_absolute_mode(fake_scan):
    """They are zero by construction only in a plane that was subtracted."""
    points, orbits = fake_scan({CORRECTOR: SLOPES}, baseline=BASELINE)

    assert (CORRECTOR, 0.0) not in measured_orbits(
        0.0, points=points, orbit_by_path=orbits
    )
    absolute = measured_orbits(
        0.0, points=points, orbit_by_path=orbits, absolute_planes=("y",)
    )
    assert (CORRECTOR, 0.0) in absolute
    # The untrimmed vertical orbit is the static orbit itself, not zero.
    np.testing.assert_allclose(absolute[(CORRECTOR, 0.0)]["Y"], BASELINE)
    np.testing.assert_allclose(absolute[(CORRECTOR, 0.0)]["X"], 0.0, atol=1e-12)


def test_the_delta_plane_is_unchanged_by_the_other_planes_mode(fake_scan):
    """The test that protects the default: x must not notice what y is doing."""
    points, orbits = fake_scan({CORRECTOR: SLOPES}, baseline=BASELINE, noise=1e-6)
    delta = measured_orbits(0.0, points=points, orbit_by_path=orbits)
    mixed = measured_orbits(
        0.0, points=points, orbit_by_path=orbits, absolute_planes=("y",), error_floor=1e-4
    )
    for key, frame in delta.items():
        for column in ("X", "ERRX"):
            np.testing.assert_array_equal(mixed[key][column], frame[column])


# -------------------------------------------------------------- model side


def _observable(name: str):
    from aba_optimiser.workers import Observable

    return Observable(name=name, targets=np.zeros(2), variances=np.ones(2))


def _prepared(**overrides):
    from aba_optimiser.workers.closed_orbit import (
        ClosedOrbitMeasurementData,
        ClosedOrbitSeriesData,
        ClosedOrbitWorker,
    )

    worker = ClosedOrbitWorker.__new__(ClosedOrbitWorker)
    worker.worker_id = 0
    data = ClosedOrbitSeriesData(
        bpm_names=["BR3.BPM1L3", "BR3.BPM2L3"],
        measurements=[
            ClosedOrbitMeasurementData(
                observables=[_observable("x"), _observable("y")]
            )
        ],
        control_knob="kbr3dhz8l1",
        **{"control_delta": 5e-5, **overrides},
    )
    worker.prepare_data(data)
    return worker


def test_the_model_subtracts_the_reference_only_where_the_data_did():
    worker = _prepared(absolute_planes=("y",))
    # Two orbit rows (x, y), two BPMs, one knob.
    kicked = (np.array([[3.0, 4.0], [5.0, 6.0]]), np.ones((2, 2, 1)) * 10.0)
    nominal = (np.array([[1.0, 1.0], [2.0, 2.0]]), np.ones((2, 2, 1)) * 4.0)

    model, jacobian = worker._compare_to_reference(kicked, nominal)

    np.testing.assert_allclose(model[0], [2.0, 3.0])  # x: differenced
    np.testing.assert_allclose(model[1], [5.0, 6.0])  # y: absolute
    np.testing.assert_allclose(jacobian[0], 6.0)
    np.testing.assert_allclose(jacobian[1], 10.0)


def test_without_absolute_planes_the_difference_is_the_old_one():
    worker = _prepared()
    kicked = (np.array([[3.0, 4.0], [5.0, 6.0]]), np.ones((2, 2, 1)) * 10.0)
    nominal = (np.array([[1.0, 1.0], [2.0, 2.0]]), np.ones((2, 2, 1)) * 4.0)

    model, jacobian = worker._compare_to_reference(kicked, nominal)

    np.testing.assert_allclose(model, kicked[0] - nominal[0])
    np.testing.assert_allclose(jacobian, kicked[1] - nominal[1])


def test_an_untrimmed_worker_is_signal_only_when_a_plane_is_absolute():
    with pytest.raises(ValueError, match="absolute plane"):
        _prepared(control_delta=0.0)
    # The same payload with a plane kept is the static-orbit constraint.
    assert _prepared(control_delta=0.0, absolute_planes=("y",)).absolute_planes == ("y",)


def test_an_unknown_model_plane_is_rejected():
    with pytest.raises(ValueError, match="Unknown absolute plane"):
        _prepared(absolute_planes=("z",))


# ------------------------------------------------------------ family prior


def test_knobs_are_sorted_into_families_by_their_suffix():
    from method2_delta_orbit.run_method2 import PRIOR_SUFFIXES

    assert PRIOR_SUFFIXES == {
        "quadrupoles": "dk1l",
        "bends": "dk0l",
        "quad_dy": "dy",
        "quad_tilt": "tilt",
    }


def test_one_family_reproduces_upstreams_isotropic_alpha():
    """The regression that says the default fit did not quietly change.

    Upstream's prior is ``alpha = strength x median(diag H)`` over every knob.
    With a single family this must return exactly that, or moving the prior into
    this class has moved the answer.
    """
    from aba_optimiser.training_closed_twiss.fitter import _prior_alphas

    names = [f"BR3.QNO{i}.dk1l" for i in range(5)]
    hessian = np.diag([1.0, 3.0, 5.0, 7.0, 9.0]) * 1e10

    alphas = _prior_alphas({"dk1l": 1e-4}, hessian, names)

    assert alphas == pytest.approx(np.full(5, 5e6))


def test_each_family_is_scaled_inside_itself():
    """Mixed units: the quadrupole prior must not move when bends are enabled."""
    from aba_optimiser.training_closed_twiss.fitter import _prior_alphas

    names = ["BR3.QNO1.dk1l", "BR3.QNO2.dk1l", "BR.BHZ1.dk0l", "BR.BHZ2.dk0l"]
    hessian = np.diag([1e10, 3e10, 2.0, 4.0])

    alphas = _prior_alphas({"dk1l": 1e-4, "dk0l": 1e-3}, hessian, names)

    quadrupole_median, bend_median = 2e10, 3.0
    np.testing.assert_allclose(alphas[:2], 1e-4 * quadrupole_median)
    np.testing.assert_allclose(alphas[2:], 1e-3 * bend_median)


def test_a_family_with_zero_strength_is_unregularised():
    from aba_optimiser.training_closed_twiss.fitter import _prior_alphas

    names = ["BR3.QNO1.dk1l", "BR3.QNO1.dy"]

    alphas = _prior_alphas({"dk1l": 1e-4, "dy": 0.0}, np.diag([1e10, 1.0]), names)

    assert alphas[0] > 0.0
    assert alphas[1] == 0.0


# ------------------------------------------------- the machine's own correctors


def test_the_horizontal_correctors_are_inverted_and_the_vertical_are_not():
    """The one conversion that separates an LSA reading from a MAD kick."""
    from loco_common.model import SCAN_CORRECTOR_SETTINGS_LSA, scan_corrector_knobs

    knobs = scan_corrector_knobs()

    assert knobs["kbr3dhz14l1"] == -SCAN_CORRECTOR_SETTINGS_LSA["logical.BR3.DHZ14L1/K"]
    assert knobs["kbr3dvt8l1"] == +SCAN_CORRECTOR_SETTINGS_LSA["logical.BR3.DVT8L1/K"]
    assert len(knobs) == 12


def test_every_scanned_corrector_has_a_recorded_setting(fake_scan):
    """The settings and the scan have to name the same twelve magnets.

    The handover list said DHZ11L1/DHZ12L1/DHZ13L1 where the scan log says L4.
    If that ever drifts back, the model sits on a corrector the machine did not
    move, which in absolute mode is indistinguishable from a dipole error.
    """
    from loco_common.measured_response import cached_scan
    from loco_common.model import SCAN_CORRECTOR_SETTINGS_LSA

    points, _ = cached_scan()
    assert {p.corrector for p in points} == set(SCAN_CORRECTOR_SETTINGS_LSA)


@pytest.mark.slow
def test_the_delta_orbit_cannot_see_the_standing_correctors(sequence_file):
    """Why the stale corrector file invalidated nothing that came before it.

    A standing corrector setting appears identically on both sides of
    ``co(k + dk) - co(k)``, so it cancels; what is left is sextupole feed-down.
    This is also exactly why the absolute mode is the first thing here that can
    be wrong about it, and why it had to be fixed before that mode is run.
    """
    from loco_common.model import build_model

    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    campaign = build_model(sequence_file=sequence_file, scan_correctors=False)
    scan = build_model(sequence_file=sequence_file)
    # The correction is not cosmetic: it moves the horizontal orbit by more than
    # the orbit's own amplitude.
    assert abs(scan.corrector_knobs["kbr3dhz14l1"] - campaign.corrector_knobs["kbr3dhz14l1"]) > 3e-3

    interface = open_interface(sequence_file)
    try:
        def delta(knobs, knob, dk, plane):
            for name, value in knobs.items():
                set_knob(interface, name, value)
            before = closed_orbit(interface)[plane].to_numpy()
            set_knob(interface, knob, knobs[knob] + dk)
            return closed_orbit(interface)[plane].to_numpy() - before

        for knob, dk, plane in (("kbr3dhz8l1", -1e-4, "X"), ("kbr3dvt8l1", 1e-4, "Y")):
            a = delta(campaign.corrector_knobs, knob, dk, plane)
            b = delta(scan.corrector_knobs, knob, dk, plane)
            relative = np.abs(b - a).max() / np.abs(a).max()
            assert relative < 5e-3, f"{knob} delta moved by {relative:.3e}"
    finally:
        interface.mad.close()


def test_the_quad_circuits_come_from_the_machine_not_a_tune_match():
    """The start model sits on the machine's currents, trims pinned at zero."""
    from loco_common.model import SCAN_QUAD_SETTINGS

    assert SCAN_QUAD_SETTINGS["kbrqf"] == pytest.approx(0.7289003149414066, abs=0)
    assert SCAN_QUAD_SETTINGS["kbrqd"] == pytest.approx(-0.7442765966796879, abs=0)
    trims = ("kbrqfcorr", "kbrqdcorr", "kbrqd3corr", "kbrqd14corr")
    assert all(SCAN_QUAD_SETTINGS[name] == 0.0 for name in trims)


@pytest.mark.slow
def test_the_quad_circuit_choice_moves_the_response(sequence_file):
    """The counterpart of the corrector test: this one is *not* invisible.

    A standing corrector cancels out of a delta orbit; a quadrupole circuit does
    not, because it changes the optics. This pins that the two sources really do
    give different answers, so nothing fitted on a tune-matched start model can
    be compared with something fitted on the machine's currents.
    """
    from loco_common.model import build_model

    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    matched = build_model(sequence_file=sequence_file, scan_quads=False)
    machine = build_model(sequence_file=sequence_file)
    assert matched.tune_knobs != machine.tune_knobs

    interface = open_interface(sequence_file)
    try:
        deltas = []
        for model in (matched, machine):
            for name, value in {**model.tune_knobs, **model.corrector_knobs}.items():
                set_knob(interface, name, value)
            before = closed_orbit(interface)["X"].to_numpy()
            set_knob(interface, "kbr3dhz8l1", model.corrector_knobs["kbr3dhz8l1"] - 1e-4)
            deltas.append(closed_orbit(interface)["X"].to_numpy() - before)
        relative = np.abs(deltas[1] - deltas[0]).max() / np.abs(deltas[0]).max()
        assert relative > 1e-2, f"the two start models agree to {relative:.3e}"
    finally:
        interface.mad.close()


# --------------------------------------------------------- corrector baseline


def _model(sequence_file):
    from loco_common.model import LocoModel, scan_corrector_knobs

    return LocoModel(
        sequence_file=sequence_file, tune_knobs={}, corrector_knobs=scan_corrector_knobs()
    )


def test_the_baseline_defaults_pair_with_the_planes():
    """A subtracted plane cannot see the correctors; an absolute one needs them."""
    from method2_delta_orbit.run_method2 import default_corrector_baseline

    assert default_corrector_baseline(()) == "zero"
    assert default_corrector_baseline(("y",)) == "machine"
    assert default_corrector_baseline(("x", "y")) == "machine"


def test_the_zero_baseline_zeroes_every_corrector_explicitly(sequence_file):
    """Explicitly zero, not absent: an empty dict keeps the sequence's own values."""
    from method2_delta_orbit.run_method2 import corrector_baseline_knobs

    model = _model(sequence_file)
    zero = corrector_baseline_knobs(model, "zero")

    assert set(zero) == set(model.corrector_knobs)
    assert set(zero.values()) == {0.0}
    assert corrector_baseline_knobs(model, "machine") == model.corrector_knobs


def test_an_unknown_baseline_is_rejected(sequence_file):
    from method2_delta_orbit.run_method2 import corrector_baseline_knobs

    with pytest.raises(ValueError, match="Unknown corrector baseline"):
        corrector_baseline_knobs(_model(sequence_file), "nominal")


def test_a_quadrupole_fits_settings_sit_on_zero_correctors(sequence_file):
    """The delta fit trims from zero, so it depends on no standing setting."""
    from method2_delta_orbit.run_method2 import build_settings

    model = _model(sequence_file)
    orbit = _frame([1e-4, 2e-4], [0.0, 0.0])
    orbits = {("logical.BR3.DHZ8L1/K", 1e-4): orbit}

    settings = build_settings(orbits, model)

    assert [s.nominal for s in settings] == [0.0]
    assert {s.corrector_baseline for s in settings} == {"zero"}


def test_an_absolute_fits_settings_sit_on_the_machines_correctors(sequence_file):
    from method2_delta_orbit.run_method2 import build_settings

    model = _model(sequence_file)
    orbits = {("logical.BR3.DHZ8L1/K", 1e-4): _frame([1e-4, 2e-4], [0.0, 0.0])}

    settings = build_settings(orbits, model, absolute_planes=("x",))

    assert settings[0].nominal == model.corrector_knobs["kbr3dhz8l1"] != 0.0
    assert settings[0].corrector_baseline == "machine"


def test_a_fit_cannot_mix_baselines(sequence_file):
    """Half the fit would compare the model against a machine the other half denies."""
    from method2_delta_orbit.run_method2 import run

    frame = _frame([1e-4], [0.0])
    settings = [
        CorrectorSetting("a", "kbr3dhz8l1", 1e-4, frame, dk=1e-4, corrector_baseline="zero"),
        CorrectorSetting("b", "kbr3dhz9l1", 1e-4, frame, dk=1e-4, corrector_baseline="machine"),
    ]
    with pytest.raises(ValueError, match="one corrector baseline"):
        run(settings, _model(sequence_file))


@pytest.mark.slow
def test_a_delta_orbit_is_the_same_on_either_baseline(sequence_file):
    """Why a quadrupole fit may trim from zero, and an absolute fit may not.

    ``co(k + dk) - co(k)`` is independent of ``k`` for a linear machine, so the
    quadrupole fit loses nothing by zeroing the standing correctors and gains
    independence from settings it cannot see. The same model, read absolutely
    rather than differenced, moves by millimetres -- which is the other half of
    the pairing in ``CORRECTOR_BASELINES``.
    """
    from method2_delta_orbit.run_method2 import corrector_baseline_knobs

    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    model = _model(sequence_file)
    interface = open_interface(sequence_file)
    try:
        absolutes, deltas = [], []
        for baseline in ("zero", "machine"):
            standing = corrector_baseline_knobs(model, baseline)
            for name, value in standing.items():
                set_knob(interface, name, value)
            before = closed_orbit(interface)["X"].to_numpy()
            set_knob(interface, "kbr3dhz8l1", standing["kbr3dhz8l1"] - 1e-4)
            deltas.append(closed_orbit(interface)["X"].to_numpy() - before)
            absolutes.append(before)

        delta_change = np.abs(deltas[1] - deltas[0]).max() / np.abs(deltas[0]).max()
        absolute_change = np.sqrt(np.mean((absolutes[1] - absolutes[0]) ** 2))
        assert delta_change < 5e-3, f"the delta moved by {delta_change:.3e}"
        assert absolute_change > 1e-3, f"the absolute orbit moved only {absolute_change:.3e}"
    finally:
        interface.mad.close()


def test_the_untrimmed_setting_survives_build_settings(sequence_file):
    """The single-RF absolute path folds the untrimmed orbit in as a target.

    ``average_zero_step`` labels it ``(static orbit)``, which is not an LSA
    parameter name; handing it to ``lsa_to_knob`` raised, so this whole path was
    broken. It gets a real knob name, a zero step, and the baseline's value.
    """
    from method2_delta_orbit.run_method2 import STATIC_ORBIT, build_settings

    model = _model(sequence_file)
    orbits = {
        ("logical.BR3.DHZ8L1/K", 1e-4): _frame([1e-4, 2e-4], [0.0, 0.0]),
        (STATIC_ORBIT, 0.0): _frame([3e-3, 4e-3], [1e-3, 2e-3]),
    }

    settings = build_settings(orbits, model, absolute_planes=("x", "y"))

    static = next(s for s in settings if s.corrector == STATIC_ORBIT)
    assert static.dk == 0.0
    assert static.knob in model.corrector_knobs
    # It must sit at the machine's value for that knob, not at zero: an absolute
    # plane has no second side for a wrong nominal to cancel against.
    assert static.nominal == model.corrector_knobs[static.knob] != 0.0


def test_a_corrector_subset_does_not_drop_the_untrimmed_orbit(sequence_file):
    """It is the machine, not one corrector's measurement."""
    from method2_delta_orbit.run_method2 import STATIC_ORBIT, build_settings

    orbits = {
        ("logical.BR3.DHZ8L1/K", 1e-4): _frame([1e-4], [0.0]),
        ("logical.BR3.DHZ9L1/K", 1e-4): _frame([1e-4], [0.0]),
        (STATIC_ORBIT, 0.0): _frame([3e-3], [1e-3]),
    }

    settings = build_settings(
        orbits, _model(sequence_file), absolute_planes=("x",),
        correctors=["logical.BR3.DHZ8L1/K"], offsets=[1e-4],
    )

    assert {s.corrector for s in settings} == {"logical.BR3.DHZ8L1/K", STATIC_ORBIT}
