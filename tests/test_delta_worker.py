"""PSB translation into the reusable closed-orbit fitting framework."""

from __future__ import annotations

import numpy as np
import pandas as pd
from method2_delta_orbit.run_method2 import CorrectorSetting, closed_orbit_series


def _orbit(value: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "X": [value, value],
            "ERRX": [1e-6, 1e-6],
            "Y": [0.0, 0.0],
            "ERRY": [1e-6, 1e-6],
        },
        index=["BR3.BPM1L3", "BR3.BPM2L3"],
    )


def _setting(*, pt=0.0, dk=5e-5, corrector="BR3.DHZ8L1", value=0.0):
    return CorrectorSetting(
        corrector=corrector,
        knob="k" + corrector.replace(".", "").lower(),
        offset_k=1e-5,
        orbit=_orbit(value),
        dk=dk,
        pt=pt,
        reference_pt=0.0,
    )


def test_batching_retains_each_momentums_target_and_global_reference():
    series = closed_orbit_series(
        [_setting(pt=-1e-3, value=1.0), _setting(pt=2e-3, value=2.0)],
        batch_momenta=True,
    )

    assert len(series) == 1
    measurements = series[0].measurements
    assert [item.pt for item in measurements] == [-1e-3, 2e-3]
    assert [item.reference_pt for item in measurements] == [0.0, 0.0]
    assert [item.orbit.iloc[0]["X"] for item in measurements] == [1.0, 2.0]


def test_batching_does_not_combine_different_corrector_states():
    series = closed_orbit_series(
        [_setting(dk=5e-5), _setting(dk=1e-4), _setting(corrector="BR3.DVT2L4")],
        batch_momenta=True,
    )

    assert len(series) == 3


def test_unbatched_layout_keeps_one_process_per_measurement():
    series = closed_orbit_series(
        [_setting(pt=-1e-3), _setting(pt=2e-3)], batch_momenta=False
    )

    assert len(series) == 2
    assert all(len(item.measurements) == 1 for item in series)


def test_pure_dispersion_has_no_fake_corrector_control():
    series = closed_orbit_series([_setting(pt=1e-3, dk=0.0)], batch_momenta=True)

    assert series[0].control_knob is None
    assert series[0].measurements[0].pt == 1e-3


def test_a_zero_trim_at_the_reference_state_is_dropped_from_a_batch():
    series = closed_orbit_series(
        [_setting(pt=0.0, dk=0.0), _setting(pt=1e-3, dk=0.0)],
        batch_momenta=True,
    )

    assert [item.pt for item in series[0].measurements] == [1e-3]


def test_the_untrimmed_duplicates_are_dropped_by_default():
    from method2_delta_orbit.run_method2 import drop_zero_step_duplicates

    orbits = {
        ("BR3.DHZ8L1", 0.0): pd.DataFrame(),
        ("BR3.DVT2L4", 0.0): pd.DataFrame(),
        ("BR3.DHZ8L1", 1e-4): pd.DataFrame(),
        ("BR3.DHZ8L1", -1e-4): pd.DataFrame(),
    }

    kept = drop_zero_step_duplicates(orbits)

    assert sorted(offset for _corrector, offset in kept) == [-1e-4, 1e-4]


def test_momentum_points_are_not_averaged_or_collapsed():
    values = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    series = closed_orbit_series(
        [_setting(pt=pt * 1e-3, value=value) for pt, value in zip(values, values)],
        batch_momenta=True,
    )[0]

    assert len(series.measurements) == 5
    np.testing.assert_allclose(
        [item.orbit.iloc[0]["X"] for item in series.measurements], values
    )
