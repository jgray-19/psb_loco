"""Fake PSB ring-3 data for the LOCO tests, generated with xsuite.

The truth is made by ``xtrack``/``xtrack_tools`` and fitted by MAD-NG. That is
the point of the arrangement: a convention error shared between the model and the
data -- a sign on a corrector kick, a factor between ``pt`` and ``dp/p`` -- would
cancel out of the answer if one twiss produced both, and would not be caught by
any assertion. Making the data in a different code means it cannot cancel.
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
    """A private copy of the unperturbed ring-3 line.

    A copy per test, not the session environment's line: every fixture below
    installs errors or trims a corrector, and a shared line would carry those
    into whichever test happened to run next.
    """
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
    """Known individual-quadrupole ``k1`` errors: the answer a fit must recover.

    A realistic ~1e-3 relative gradient error on a named subset. Returned rather
    than applied, so a test can compare against it.
    """
    rng = np.random.default_rng(20260821)
    return {
        name: float(psb_line[name].k1) * float(rng.normal(0.0, 1e-3))
        for name in quad_names[::4]
    }


@pytest.fixture
def truth_line(psb_env, truth_errors):
    """The perturbed machine: :func:`truth_errors` plus a vertical misalignment.

    The misalignment is what keeps the *nominal* closed orbit from being flat,
    which is what makes Method 2's delta subtraction load-bearing rather than
    trivially true -- subtracting a flat orbit changes nothing.
    """
    xtt = _require("xtrack_tools")
    line = psb_env.lines[SEQ_NAME].copy()
    for name, error in truth_errors.items():
        line[name].k1 = float(line[name].k1) + error
    xtt.apply_vertical_quad_misalignment(line, rms=2e-4, seed=7, name_prefix="br.")
    return line


def orbit_frame(line, bpm_names: list[str], *, noise: float = 0.0, seed: int = 0) -> pd.DataFrame:
    """Closed orbit at the BPMs as the ``X/ERRX/Y/ERRY`` frame the fitters take.

    Converted through ``xsuite_tws_to_ng`` rather than read straight off the
    xsuite table, so the column names, signs and momentum convention are the ones
    MAD-NG uses instead of ones assumed to match.
    """
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

    The sign convention is xsuite's and is pinned by ``test_naming.py``:
    ``knl[0] = -hkick`` horizontally, ``ksl[0] = +vkick`` vertically.
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
def fake_response(fake_orbits, bpm_names):
    """``fake_response(line, correctors, dk)`` -> the response frame Method 1 fits.

    Built as a central difference so it is the derivative at the nominal setting,
    matching what a symmetric ``0, +-dk, +-2dk`` scan measures rather than a
    one-sided slope.

    ``dk`` is an LSA ``/K`` step, because that is what the fitters are handed and
    what the machine reports -- not a MAD kick. ``fake_orbits`` works in MAD's
    convention, so the step is converted through :func:`lsa_k_to_rad` on the way
    in and the slope back out. This matters: the two differ by a sign in the
    horizontal plane, and a fixture that skipped the conversion would be testing
    the fit against data no machine would ever produce.
    """
    from loco_common.naming import lsa_k_to_rad  # noqa: PLC0415

    def _response(line, correctors: list[str], dk: float = 5e-5) -> pd.DataFrame:
        rows = []
        for corrector in correctors:
            kick = dk * lsa_k_to_rad(corrector)
            plus = fake_orbits(line, corrector, kick)
            minus = fake_orbits(line, corrector, -kick)
            for plane in ("x", "y"):
                slope = (plus[plane.upper()] - minus[plane.upper()]) / (2.0 * dk)
                for bpm in slope.index:
                    rows.append(
                        {
                            "NAME": bpm,
                            "CORRECTOR": corrector,
                            "PLANE": plane,
                            "SLOPE": float(slope[bpm]),
                            "ERRSLOPE": 1.0,
                        }
                    )
        return pd.DataFrame(rows)

    return _response


@pytest.fixture
def fake_scan():
    """``fake_scan(slopes, noise=..)`` -> the ``(points, orbit_by_path)`` pair.

    Stands in for the SDDS side of a real scan without writing SDDS: the loaders
    that read the files are exercised separately, and everything downstream of
    them takes exactly this pair. Each BPM's orbit is linear in ``offset_k`` with
    a known slope, so the fitted slope has an exact right answer.
    """
    from loco_common.measured_response import DELTA_K, ScanPoint  # noqa: PLC0415

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
            for step in offsets:
                offset_k = step * DELTA_K
                path = Path(f"/fake/{corrector}_{step:+g}_{rf_offset:+g}.sdds")
                orbit = {}
                for label in ("X", "Y"):
                    # A static, corrector-independent baseline orbit: the
                    # reference subtraction has to remove it exactly.
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
