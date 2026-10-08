"""Fake PSB ring-3 data for the LOCO tests, generated with xsuite.

Truth comes from ``xtrack`` and is fitted by MAD-NG, so a convention error shared by data and model cannot cancel.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

#: The same ring-3 sequence xtrack-tools and sgd-magnet-tuner already test on.
SEQUENCE_FILE = (
    Path(__file__).resolve().parents[2]
    / "xtrack-tools/tests/data/sequences/psb3_saved.seq"
)
KINETIC_ENERGY = 0.16  # GeV, PSB flat bottom -- kinetic, not total.
SEQ_NAME = "psb3"
BPM_PATTERN = r"(?i)^br3\.bpm\d+l3$"
QUAD_PATTERN = re.compile(r"(?i)^br\.q(?:fo|de)\d+$")
#: BPM resolution used for the noisy fixtures, in metres.
BPM_NOISE = 5e-5


def _require(module: str):
    return pytest.importorskip(module, reason=f"{module} is needed for the fake-data fixtures")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Prevent serial tests from running inside pytest-xdist workers."""
    if (
        item.get_closest_marker("serial")
        and getattr(item.config, "workerinput", None) is not None
    ):
        pytest.fail(f"{item.nodeid} is marked serial and cannot run under pytest-xdist")


@pytest.fixture(scope="session")
def sequence_file() -> Path:
    if not SEQUENCE_FILE.exists():
        pytest.skip(f"PSB ring-3 sequence not available at {SEQUENCE_FILE}")
    return SEQUENCE_FILE


@pytest.fixture(scope="session")
def psb_env(sequence_file, tmp_path_factory):
    """The unperturbed ring-3 environment; the model both methods start from."""
    xtt = _require("xtrack_tools")
    cache = tmp_path_factory.mktemp("xsuite") / "psb3.json"
    return xtt.create_xsuite_environment(
        sequence_file=sequence_file,
        kinetic_energy=KINETIC_ENERGY,
        seq_name=SEQ_NAME,
        json_file=cache,
    )


@pytest.fixture
def psb_line(psb_env):
    """A private copy of the unperturbed ring-3 line, per test (fixtures install errors or trim correctors)."""
    return psb_env.lines[SEQ_NAME].copy()


@pytest.fixture
def bpm_names(psb_line) -> list[str]:
    xtt = _require("xtrack_tools")
    return xtt.get_monitor_names_at_pattern(psb_line, BPM_PATTERN)


@pytest.fixture
def quad_names(psb_line) -> list[str]:
    return [name for name in psb_line.element_names if QUAD_PATTERN.match(name)]


@pytest.fixture
def truth_errors(psb_line, quad_names) -> dict[str, float]:
    """Known individual-quadrupole ``k1`` errors (~1e-3 relative on a named subset), returned so a test can compare against them."""
    rng = np.random.default_rng(20260821)
    return {
        name: float(psb_line[name].k1) * float(rng.normal(0.0, 1e-3))
        for name in quad_names[::4]
    }


@pytest.fixture
def truth_line(psb_env, truth_errors):
    """The perturbed machine: :func:`truth_errors` plus a vertical misalignment (so the nominal closed orbit is not flat)."""
    xtt = _require("xtrack_tools")
    line = psb_env.lines[SEQ_NAME].copy()
    for name, error in truth_errors.items():
        line[name].k1 = float(line[name].k1) + error
    xtt.apply_vertical_quad_misalignment(line, rms=2e-4, seed=7, name_prefix="br.")
    return line


def orbit_frame(line, bpm_names: list[str], *, noise: float = 0.0, seed: int = 0) -> pd.DataFrame:
    """Closed orbit at the BPMs as the ``X/ERRX/Y/ERRY`` frame the fitters take, via ``xsuite_tws_to_ng``."""
    xtt = _require("xtrack_tools")
    twiss = xtt.xsuite_tws_to_ng(line.twiss(method="4d"))
    names = [name.upper() for name in bpm_names]
    frame = pd.DataFrame(index=pd.Index(names, name="NAME"))
    rng = np.random.default_rng(seed)
    for column, source in (("X", "x"), ("Y", "y")):
        values = twiss.loc[names, source].to_numpy(dtype=float)
        if noise > 0.0:
            values = values + rng.normal(0.0, noise, values.shape)
        frame[column] = values
        frame[f"ERR{column}"] = noise if noise > 0.0 else 1e-9
    return frame


@pytest.fixture
def fake_orbits(bpm_names):
    """``fake_orbits(line, corrector, dk, ...)`` -> the orbit at that corrector setting.

    Sign convention is xsuite's, pinned by ``test_naming.py``: ``knl[0] = -hkick``, ``ksl[0] = +vkick``.
    """

    def _orbits(line, corrector: str | None = None, dk: float = 0.0, **kwargs) -> pd.DataFrame:
        if corrector is None or dk == 0.0:
            return orbit_frame(line, bpm_names, **kwargs)
        element = line[corrector.lower()]
        vertical = "dvt" in corrector.lower()
        attribute = "ksl" if vertical else "knl"
        original = float(getattr(element, attribute)[0])
        getattr(element, attribute)[0] = original + (dk if vertical else -dk)
        try:
            return orbit_frame(line, bpm_names, **kwargs)
        finally:
            getattr(element, attribute)[0] = original

    return _orbits


@pytest.fixture
def fake_scan():
    """``fake_scan(slopes, noise=..)`` -> the ``(points, orbit_by_path)`` pair, without writing SDDS.

    Each BPM's orbit is linear in ``offset_k`` with a known slope; each corrector ends with a ``reset`` to zero, as in the real scan.
    """
    from loco_common.measured_response import ScanPoint  # noqa: PLC0415

    delta_k = 7.5e-5  # psb_md/scan_psb_loco.py's corrector step

    def _scan(
        slopes: dict[str, dict[str, float]],
        *,
        noise: float = 0.0,
        seed: int = 3,
        rf_offset: float = 0.0,
        offsets: tuple[float, ...] = (-2, -1, 0, 1, 2),
        baseline: float = 1e-3,
    ) -> tuple[list, dict]:
        rng = np.random.default_rng(seed)
        points, orbit_by_path = [], {}
        for corrector, per_bpm in slopes.items():
            plane = "y" if "DVT" in corrector.upper() else "x"
            bpms = list(per_bpm)
            steps = [*offsets, "reset"] if 0 in offsets else list(offsets)
            for step in steps:
                offset_k = 0.0 if step == "reset" else step * delta_k
                path = Path(f"/fake/{corrector}_{step}_{rf_offset:+g}.sdds")
                orbit = {}
                for label in ("X", "Y"):
                    # Static baseline orbit the reference subtraction must remove exactly.
                    values = np.full(len(bpms), baseline)
                    if label.lower() == plane:
                        values = values + offset_k * np.array([per_bpm[b] for b in bpms])
                    if noise > 0.0:
                        values = values + rng.normal(0.0, noise, values.shape)
                    index = pd.Index(bpms, name="NAME")
                    errors = pd.Series(np.full(len(bpms), max(noise, 1e-9)), index=index)
                    orbit[label] = (pd.Series(values, index=index), errors)
                orbit_by_path[path] = orbit
                points.append(
                    ScanPoint(
                        corrector=corrector,
                        plane=plane,
                        rf_offset=rf_offset,
                        offset_k=offset_k,
                        path=path,
                    )
                )
        return points, orbit_by_path

    return _scan
