"""The scan-to-target pipeline: association, reference subtraction, slope fit."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from loco_common.measured_response import (
    DELTA_K,
    find_scan_measurements,
    measured_orbits,
    measured_response,
)

CORRECTOR = "logical.BR3.DHZ8L1/K"
SLOPES = {"BR3.BPM1L3": 12.5, "BR3.BPM2L3": -4.0, "BR3.BPM3L3": 0.0}


def _entry(seconds: int, **overrides) -> dict:
    entry = {
        "parameter": CORRECTOR,
        "plane": "x",
        "rf_offset_mm": 0.0,
        "offset_k": 0.0,
        "write_started_utc": f"2026-08-21T09:{seconds // 60:02d}:{seconds % 60:02d}+00:00",
    }
    entry.update(overrides)
    return entry


def test_slopes_are_recovered_exactly_without_noise(fake_scan):
    points, orbits = fake_scan({CORRECTOR: SLOPES})
    response = measured_response(0.0, points=points, orbit_by_path=orbits)
    fitted = response.query("PLANE == 'x'").set_index("NAME")["SLOPE"]
    for bpm, slope in SLOPES.items():
        assert fitted[bpm] == pytest.approx(slope, abs=1e-9)


def test_slope_error_covers_the_noise(fake_scan):
    noise = 1e-5
    points, orbits = fake_scan({CORRECTOR: SLOPES}, noise=noise)
    response = (
        measured_response(0.0, points=points, orbit_by_path=orbits)
        .query("PLANE == 'x'")
        .set_index("NAME")
    )
    for bpm, truth in SLOPES.items():
        deviation = abs(response.loc[bpm, "SLOPE"] - truth)
        assert deviation < 5.0 * response.loc[bpm, "ERRSLOPE"]
        # The error must scale with the noise rather than being a placeholder.
        assert response.loc[bpm, "ERRSLOPE"] > 0.0


def test_both_bpm_planes_are_retained(fake_scan):
    points, orbits = fake_scan({CORRECTOR: SLOPES})
    response = measured_response(0.0, points=points, orbit_by_path=orbits)
    assert set(response["PLANE"]) == {"x", "y"}
    assert len(response) == 2 * len(SLOPES)
    np.testing.assert_allclose(response.query("PLANE == 'y'")["SLOPE"], 0.0, atol=1e-9)


def test_delta_orbits_remove_the_static_orbit(fake_scan):
    """The baseline orbit is corrector-independent, so it must not survive."""
    points, orbits = fake_scan({CORRECTOR: SLOPES}, baseline=5e-3)
    deltas = measured_orbits(0.0, points=points, orbit_by_path=orbits)

    assert (CORRECTOR, 0.0) not in deltas, "the zero point is identically zero after subtraction"
    frame = deltas[(CORRECTOR, 2 * DELTA_K)]
    expected = 2 * DELTA_K * np.array([SLOPES[bpm] for bpm in frame.index])
    np.testing.assert_allclose(frame["X"].to_numpy(), expected, atol=1e-12)
    np.testing.assert_allclose(frame["Y"].to_numpy(), 0.0, atol=1e-12)


def test_delta_orbit_errors_add_in_quadrature(fake_scan):
    noise = 2e-5
    points, orbits = fake_scan({CORRECTOR: SLOPES}, noise=noise)
    frame = measured_orbits(0.0, points=points, orbit_by_path=orbits)[(CORRECTOR, DELTA_K)]
    np.testing.assert_allclose(frame["ERRX"].to_numpy(), np.hypot(noise, noise), rtol=1e-9)


def test_a_scan_point_without_an_acquisition_is_dropped():
    """A point with no acquisition in its interval is dropped, not mis-assigned."""
    entries = [_entry(0), _entry(60), _entry(120)]
    times = [pd.Timestamp("2026-08-21T09:00:30+00:00").tz_convert("Europe/Zurich")]
    measurements = {times[0]: "first.sdds"}

    found = find_scan_measurements(entries, measurements)

    assert [point.path for point in found] == ["first.sdds"]


def test_association_takes_the_first_acquisition_in_the_interval():
    entries = [_entry(0), _entry(60)]
    measurements = {
        pd.Timestamp("2026-08-21T09:00:10+00:00").tz_convert("Europe/Zurich"): "early.sdds",
        pd.Timestamp("2026-08-21T09:00:50+00:00").tz_convert("Europe/Zurich"): "late.sdds",
    }

    found = find_scan_measurements(entries, measurements)

    assert [point.path for point in found] == ["early.sdds"]
