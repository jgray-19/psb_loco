"""Measured orbits -> settings -> upstream series."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from loco_common.campaign import P23_P13_FINAL
from loco_common.model import LocoModel
from poco.settings import UNTRIMMED, CorrectorSetting, closed_orbit_series, scan_settings, standing_state, trim_settings

DHZ = "logical.BR3.DHZ8L1/K"
DVT = "logical.BR3.DVT2L4/K"
KNOB = "kbr3dhz8l1"
STANDING = {KNOB: 0.0, "kbr3dvt2l4": 0.0}


def _orbit(value: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame(
        {"X": [value, value], "ERRX": [1e-6, 1e-6], "Y": [0.0, 0.0], "ERRY": [1e-6, 1e-6]},
        index=["BR3.BPM1L3", "BR3.BPM2L3"],
    )


def _setting(*, corrector="BR3.DHZ8L1", knob=KNOB, dk=5e-5, pt=0.0, value=0.0) -> CorrectorSetting:
    return CorrectorSetting(corrector, knob, 1e-5, _orbit(value), dk=dk, pt=pt)


def _model() -> LocoModel:
    return LocoModel(
        sequence_file="unused",
        tune_knobs={"kbrqf": 0.73},
        corrector_knobs={KNOB: 1e-3, "kbr3dvt2l4": -2e-3},
    )


# ------------------------------------------------------------ standing state


def test_a_delta_fit_stands_on_zero_correctors_and_an_absolute_one_on_the_machines():
    """A subtracted plane cannot see the correctors (1e-3 relative); an absolute one is largely their kicks."""
    model = _model()

    assert standing_state(model) == {"kbrqf": 0.73, KNOB: 0.0, "kbr3dvt2l4": 0.0}
    assert standing_state(model, ("y",)) == {"kbrqf": 0.73, KNOB: 1e-3, "kbr3dvt2l4": -2e-3}


# ----------------------------------------------------------------- settings


def test_a_trim_is_the_lsa_step_in_madx_kick_units():
    """DHZ is inverted relative to MAD's hkick, DVT is not (``loco_common.naming``)."""
    settings = trim_settings({(DHZ, 1e-4): _orbit(), (DVT, 1e-4): _orbit()})

    assert {s.knob: s.dk for s in settings} == {KNOB: -1e-4, "kbr3dvt2l4": 1e-4}


def test_correctors_and_offsets_restrict_the_settings():
    orbits = {(DHZ, 1e-4): _orbit(), (DHZ, -1e-4): _orbit(), (DVT, 1e-4): _orbit()}

    settings = trim_settings(orbits, correctors=[DHZ], offsets=[1e-4])

    assert [(s.corrector, s.offset_k) for s in settings] == [(DHZ, 1e-4)]


needs_scan = pytest.mark.skipif(
    not P23_P13_FINAL.cache_file("scan_points.parquet").exists(), reason="needs the cached scan (build it from the mount)"
)


@needs_scan
def test_nominal_rf_scan_settings_are_the_trims_alone():
    settings = scan_settings(P23_P13_FINAL, _model())

    assert settings
    assert all(s.knob and s.pt == 0.0 and s.rf_offset == 0.0 for s in settings)
    assert all(s.dk != 0.0 for s in settings)


@needs_scan
def test_an_absolute_plane_adds_the_static_orbit_once_with_the_other_plane_differenced():
    delta = scan_settings(P23_P13_FINAL, _model())
    absolute = scan_settings(P23_P13_FINAL, _model(), absolute_planes=("y",))

    (static,) = [s for s in absolute if s.corrector == UNTRIMMED]
    assert static.knob is None and static.dk == 0.0
    assert len(absolute) == len(delta) + 1
    # The vertical orbit is the machine's own (millimetres); the horizontal one is a difference of the same acquisitions.
    assert static.orbit["Y"].abs().max() > 10 * static.orbit["X"].abs().max()


def test_a_scan_without_nominal_rf_has_no_momentum_reference():
    with pytest.raises(ValueError, match="nominal-RF"):
        scan_settings(P23_P13_FINAL, _model(), rf_offsets=(2.0,))


# ------------------------------------------------------------------- series


def test_unbatched_layout_keeps_one_series_per_setting():
    series = closed_orbit_series([_setting(pt=-1e-3), _setting(pt=2e-3)], STANDING)

    assert [len(item.measurements) for item in series] == [1, 1]


def test_batching_gathers_a_trims_momenta_in_order_of_pt():
    series = closed_orbit_series(
        [_setting(pt=2e-3, value=2.0), _setting(pt=-1e-3, value=1.0)], STANDING, batch_momenta=True
    )

    assert len(series) == 1
    assert [m.pt for m in series[0].measurements] == [-1e-3, 2e-3]
    assert [m.orbit.iloc[0]["X"] for m in series[0].measurements] == [1.0, 2.0]
    assert all(m.reference_pt == 0.0 for m in series[0].measurements)


def test_batching_keeps_different_trims_apart():
    series = closed_orbit_series(
        [_setting(dk=5e-5), _setting(dk=1e-4), _setting(corrector="BR3.DVT2L4", knob="kbr3dvt2l4")],
        STANDING,
        batch_momenta=True,
    )

    assert len(series) == 3


def test_a_series_sets_only_its_kick_at_standing_plus_dk():
    series = closed_orbit_series([_setting(dk=1e-4)], {KNOB: 2e-5}, batch_momenta=True)

    assert series[0].machine_state == {KNOB: 2e-5 + 1e-4}


def test_an_untrimmed_orbit_sets_no_kick_and_carries_the_absolute_planes():
    untrimmed = CorrectorSetting(UNTRIMMED, None, 0.0, _orbit(1e-3), pt=1e-3)

    series = closed_orbit_series([untrimmed], STANDING, absolute_planes=("y",))

    assert series[0].machine_state == {}
    assert series[0].absolute_planes == ("y",)
    assert series[0].measurements[0].pt == 1e-3


def test_momentum_points_are_neither_averaged_nor_collapsed():
    values = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    series = closed_orbit_series(
        [_setting(pt=value * 1e-3, value=value) for value in values], STANDING, batch_momenta=True
    )[0]

    assert len(series.measurements) == 5
    np.testing.assert_allclose([m.orbit.iloc[0]["X"] for m in series.measurements], values)


# ------------------------------------------------------ MAD-NG, slow


def _machine_model(sequence_file) -> LocoModel:
    from psb_md.acd_config import psb_orbit_corrector_strengths

    return LocoModel(
        sequence_file=sequence_file,
        tune_knobs={},
        corrector_knobs=psb_orbit_corrector_strengths(P23_P13_FINAL.machine_config),
    )


@pytest.mark.slow
def test_the_quad_circuit_choice_moves_the_response(sequence_file):
    """A quadrupole circuit, unlike a standing corrector, changes a delta orbit (it changes the optics)."""
    from loco_common.model import build_model
    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    matched = build_model(sequence_file=sequence_file, campaign=P23_P13_FINAL, scan_quads=False)
    machine = build_model(sequence_file=sequence_file, campaign=P23_P13_FINAL)
    assert matched.tune_knobs != machine.tune_knobs

    interface = open_interface(sequence_file)
    try:
        deltas = []
        for model in (matched, machine):
            for name, value in {**model.tune_knobs, **model.corrector_knobs}.items():
                set_knob(interface, name, value)
            before = closed_orbit(interface)["X"].to_numpy()
            set_knob(interface, KNOB, model.corrector_knobs[KNOB] - 1e-4)
            deltas.append(closed_orbit(interface)["X"].to_numpy() - before)
        relative = np.abs(deltas[1] - deltas[0]).max() / np.abs(deltas[0]).max()
        assert relative > 1e-2, f"the two start models agree to {relative:.3e}"
    finally:
        interface.mad.close()


@pytest.mark.slow
def test_a_delta_orbit_is_the_same_on_either_baseline(sequence_file):
    """A delta fit may trim from zero correctors, an absolute one may not.

    ``co(k + dk) - co(k)`` is independent of ``k`` for a linear machine, but the absolute orbit moves by millimetres.
    """
    from tests.madng_helpers import closed_orbit, open_interface, set_knob

    model = _machine_model(sequence_file)
    interface = open_interface(sequence_file)
    try:
        absolutes, deltas = [], []
        for planes in ((), ("y",)):
            standing = standing_state(model, planes)
            for name, value in standing.items():
                set_knob(interface, name, value)
            before = closed_orbit(interface)["X"].to_numpy()
            set_knob(interface, KNOB, standing[KNOB] - 1e-4)
            deltas.append(closed_orbit(interface)["X"].to_numpy() - before)
            absolutes.append(before)

        delta_change = np.abs(deltas[1] - deltas[0]).max() / np.abs(deltas[0]).max()
        absolute_change = np.sqrt(np.mean((absolutes[1] - absolutes[0]) ** 2))
        assert delta_change < 5e-3, f"the delta moved by {delta_change:.3e}"
        assert absolute_change > 1e-3, f"the absolute orbit moved only {absolute_change:.3e}"
    finally:
        interface.mad.close()
