"""The scan-to-target pipeline: association, reference subtraction, slope fit."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from loco_common.measured_response import (
    MAX_HOLD,
    ScanPoint,
    average_orbit_frames,
    find_scan_measurements,
    measured_orbits,
    measured_response,
    pooled_intershot_noise,
    read_scan_log,
)

CORRECTOR = "logical.BR3.DHZ8L1/K"
SLOPES = {"BR3.BPM1L3": 12.5, "BR3.BPM2L3": -4.0, "BR3.BPM3L3": 0.0}
DELTA_K = 7.5e-5


def _utc(seconds: float) -> str:
    return (pd.Timestamp("2026-08-28T10:00:00+00:00") + pd.Timedelta(seconds=seconds)).isoformat()


def _entry(seconds: float, offset_k: float = 0.0, event: str = "scan_point") -> dict:
    """A log line written *seconds* in, 1.2 s after the cycle that triggered it."""
    return {
        "event": event,
        "parameter": CORRECTOR,
        "plane": "x",
        "offset_k": offset_k,
        "cycle_stamp_trigger": _utc(seconds - 1.2),
        "write_started_utc": _utc(seconds),
    }


def _acquisitions(*seconds: float) -> dict[pd.Timestamp, str]:
    return {
        pd.Timestamp(_utc(s)).tz_convert("Europe/Zurich"): f"{s:g}.sdds" for s in seconds
    }


def _intershot(bpms, error: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame(
        {"ERRX": error, "ERRY": error}, index=pd.Index(list(bpms), name="NAME")
    )


def _associated(entries, measurements) -> list[tuple[str, float]]:
    return [
        (point.path, point.offset_k)
        for point in find_scan_measurements(entries, measurements, rf_offset=0.0)
    ]


def test_every_acquisition_of_a_held_setting_is_kept():
    """A setting held over two cycles was measured twice; both count."""
    entries = [_entry(0.0), _entry(21.6, DELTA_K)]
    found = _associated(entries, _acquisitions(9.6, 20.4, 31.2))
    assert found == [("9.6.sdds", 0.0), ("20.4.sdds", 0.0), ("31.2.sdds", DELTA_K)]


def test_the_cycle_that_triggered_a_write_measured_the_previous_setting():
    """Its file is stamped just before the write, so it stays with the old setting."""
    entries = [_entry(0.0), _entry(10.8, DELTA_K), _entry(21.6, -DELTA_K)]
    found = _associated(entries, _acquisitions(9.6, 20.4))
    assert found == [("9.6.sdds", 0.0), ("20.4.sdds", DELTA_K)]


def test_the_first_setting_owns_the_cycles_since_the_scan_started():
    """Offset zero is the start-up state the machine was already in."""
    entries = [_entry(0.0), _entry(10.8, DELTA_K)]
    entries[0]["cycle_stamp_trigger"] = _utc(-20.0)
    found = _associated(entries, _acquisitions(-30.0, -10.0, 9.6))
    assert found == [("-10.sdds", 0.0), ("9.6.sdds", 0.0)]


def test_the_last_setting_is_kept_for_at_most_the_longest_hold():
    """No write ends it; after MAX_HOLD the RF is being changed for the next run."""
    entries = [_entry(0.0, DELTA_K), _entry(10.8, event="reset")]
    last_hold = 10.8 + MAX_HOLD.total_seconds()
    found = _associated(entries, _acquisitions(9.6, 20.4, last_hold - 1.0, last_hold + 1.0))
    assert found == [("9.6.sdds", DELTA_K), ("20.4.sdds", 0.0), (f"{last_hold - 1.0:g}.sdds", 0.0)]


def test_the_scan_log_keeps_resets_and_drops_restores(tmp_path):
    lines = [
        _entry(10.8, event="reset"),
        _entry(0.0, DELTA_K),
        {"event": "restore", "parameter": CORRECTOR, "write_started_utc": _utc(12.0)},
    ]
    log = tmp_path / "scan.jsonl"
    log.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    assert [entry["event"] for entry in read_scan_log(log)] == ["scan_point", "reset"]


def test_repeat_acquisitions_of_one_setting_are_averaged():
    """Plain mean; turn error of the mean and intershot/sqrt(N) in quadrature."""
    index = pd.Index(list(SLOPES), name="NAME")
    points, orbit_by_path = [], {}
    for value in (1e-3, 3e-3):
        path = Path(f"/fake/{value:g}.sdds")
        points.append(ScanPoint(CORRECTOR, "x", 0.0, DELTA_K, path))
        series = pd.Series(value, index=index)
        errors = pd.Series(1e-6, index=index)
        orbit_by_path[path] = {"X": (series, errors), "Y": (series, errors)}

    frame = measured_orbits(
        0.0,
        points=points,
        orbit_by_path=orbit_by_path,
        delta=False,
        intershot=_intershot(SLOPES, 3e-6),
    )[(CORRECTOR, DELTA_K)]

    np.testing.assert_allclose(frame["X"], 2e-3)
    np.testing.assert_allclose(frame["ERRX"], np.sqrt(2e-12 / 4 + 9e-12 / 2))


def test_intershot_noise_is_pooled_over_degrees_of_freedom():
    """Two RF groups, 2 and 3 repeats: sum of squares over dof, less turn noise."""
    index = pd.Index(["BR3.BPM1L3"], name="NAME")
    points, orbit_by_path = [], {}
    for rf_offset, values in ((0.0, (1e-6, 3e-6)), (1.0, (10e-6, 12e-6, 14e-6))):
        for value in values:
            path = Path(f"/fake/{rf_offset:g}_{value:g}.sdds")
            points.append(ScanPoint(CORRECTOR, "x", rf_offset, 0.0, path))
            series, errors = pd.Series(value, index=index), pd.Series(0.5e-6, index=index)
            orbit_by_path[path] = {"X": (series, errors), "Y": (series, errors)}
    # A trimmed acquisition is not a repeat of the untrimmed machine.
    trimmed = Path("/fake/trimmed.sdds")
    points.append(ScanPoint(CORRECTOR, "x", 0.0, DELTA_K, trimmed))
    orbit_by_path[trimmed] = {"X": (pd.Series(1.0, index=index), errors)} | {
        "Y": (pd.Series(1.0, index=index), errors)
    }

    noise = pooled_intershot_noise(points, orbit_by_path)

    # (2 + 8) um^2 over 1 + 2 dof, minus the 0.25 um^2 turn variance.
    np.testing.assert_allclose(noise["ERRX"], np.sqrt(10 / 3 - 0.25) * 1e-6)


def test_a_single_acquisition_carries_the_full_intershot_noise():
    frame = pd.DataFrame(
        {"X": [1e-3], "ERRX": [3e-6], "Y": [1e-3], "ERRY": [3e-6]},
        index=pd.Index(["BR3.BPM1L3"], name="NAME"),
    )
    averaged = average_orbit_frames([frame], _intershot(frame.index, 4e-6))
    np.testing.assert_allclose(averaged[["ERRX", "ERRY"]], 5e-6)


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


def test_slope_errors_include_intershot_noise(fake_scan):
    """Method 1's single acquisitions are not exempt from shot-to-shot jitter."""
    points, orbits = fake_scan({CORRECTOR: SLOPES}, noise=1e-6)
    errors = [
        measured_response(
            0.0, points=points, orbit_by_path=orbits, intershot=_intershot(SLOPES, error)
        )
        .query("PLANE == 'x'")["ERRSLOPE"]
        .to_numpy()
        for error in (0.0, 1e-5)
    ]
    assert np.all(errors[1] > 5 * errors[0])


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
    frame = measured_orbits(
        0.0, points=points, orbit_by_path=orbits, intershot=_intershot(SLOPES)
    )[(CORRECTOR, DELTA_K)]
    # The reference averages the zero step and the reset.
    expected = np.hypot(noise, noise / np.sqrt(2))
    np.testing.assert_allclose(frame["ERRX"].to_numpy(), expected, rtol=1e-9)
