"""Measured orbit response of PSB ring 3 to its DHZ/DVT correctors.

The 2026-08-21 scan stepped each of six DHZ and six DVT correctors through
``offset_k = 0, +-dk, +-2dk`` under five RF-steering offsets, taking a multiturn
BPM acquisition at every point. It was run three times, at two quadrupole
powerings and two step sizes; which one is being read is the *campaign*
(:mod:`loco_common.campaign`), and every function here takes one, defaulting to
the first. This module turns that pile of SDDS files plus the JSONL scan log into
the two things the fitters need:

* :func:`measured_orbits` -- the closed orbit *change* at each scan point, which
  is Method 2's target;
* :func:`measured_response` -- the per-BPM slope ``d(orbit)/d(k)`` of those
  changes, which is Method 1's target.

Both come from the same acquisitions and the same reference subtraction, so the
two methods are fitting the same measurement in two different shapes rather than
two differently-prepared datasets.

That reference is *one* orbit for the whole scan --
:func:`global_reference_orbit`, the untrimmed machine at nominal RF -- not each
corrector's own ``offset_k = 0`` point and not each RF setting's own. Using a
per-RF reference would subtract the off-momentum orbit away, and the
off-momentum orbit is dispersion: a real, quadrupole-sensitive signal that the
multi-momentum mode exists to fit. Method 1's slopes are unchanged by the
choice (its fit keeps the intercept free, so any constant reference cancels);
Method 2's targets are not, and the model side has to match it by taking its own
reference at ``pt = 0`` with the correctors nominal.

Reading the SDDS files dominates the runtime (~900 acquisitions), so both
products are cached to parquet under :data:`CACHE_PATH`.
"""

from __future__ import annotations

import json
import logging
from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from turn_by_turn import read_tbt

from loco_common import campaign as campaign_module
from loco_common.campaign import NORMAL, Campaign

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

RF_STEERING_OFFSETS: tuple[float | None, ...] = (-2.0, -1.0, 0.0, 1.0, 2.0, None)
MEASUREMENT_PATTERN = "MULTITURN_ACQ__*.sdds"
READ_WORKERS = 8

#: Every path this module reads is a property of the campaign it is asked for --
#: :mod:`loco_common.campaign`. These names are the normal-tunes campaign's, kept
#: because the whole repository was written against them; new code should take a
#: :class:`~loco_common.campaign.Campaign` instead.
MOUNT_PATH = campaign_module.MOUNT_PATH
USE_MOUNT = campaign_module.USE_MOUNT
BASE_PATH = campaign_module.FIRST_PATH
SCAN_PATH = campaign_module.SCAN_PATH
MEASUREMENTS_PATH = NORMAL.measurements_path
JSON_PATH = NORMAL.scan_log
#: The acquisition mount is read-only, so the cache lives beside this repository.
CACHE_PATH = campaign_module.CACHE_PATH

#: Value and error columns of each plane, in the orbit frames this module builds.
PLANE_COLUMNS: dict[str, tuple[str, str]] = {"x": ("X", "ERRX"), "y": ("Y", "ERRY")}

#: Corrector step used by the first scan (``psb_md/scan_psb_loco.py``), in LSA
#: ``/K``. The large-step inverted scan used 1.5e-4 instead, which is why the step
#: is a campaign field: read ``campaign.delta_k`` rather than this.
DELTA_K = NORMAL.delta_k


@dataclass(frozen=True)
class ScanPoint:
    """One acquisition, tagged with the machine setting it was taken at."""

    corrector: str
    plane: str
    rf_offset: float
    offset_k: float
    path: Path


def closed_orbit(path: Path) -> dict[str, tuple[pd.Series, pd.Series]]:
    """Return orbit means and standard errors of the mean by plane, in metres."""
    tbt = read_tbt(path, datatype="psb")
    result = {}
    for plane in ("X", "Y"):
        frames = [getattr(matrix, plane) for matrix in tbt.matrices]
        values = np.stack([frame.to_numpy() for frame in frames]) * 1e-3 # mm to m
        mean = pd.Series(values.mean(axis=(0, 2)), index=frames[0].index)
        sem = pd.Series(
            values.std(axis=(0, 2), ddof=1) / np.sqrt(values.shape[0] * values.shape[2]),
            index=frames[0].index,
        )
        result[plane] = mean, sem
    return result


def load_measurements(measurements_path: Path = MEASUREMENTS_PATH) -> dict[pd.Timestamp, Path]:
    """Map each acquisition's local timestamp to its file, in time order."""
    measurements = {}
    for path in measurements_path.glob(MEASUREMENT_PATTERN):
        timestamp = pd.to_datetime(
            path.stem.split("__", 1)[1], format="%d-%m-%y_%H-%M-%S"
        ).tz_localize("Europe/Zurich")
        measurements[timestamp] = path
    return dict(sorted(measurements.items()))


def find_scan_measurements(
    entries: list[dict], measurements: dict[pd.Timestamp, Path]
) -> list[ScanPoint]:
    """Associate the first acquisition in each scan interval with its scan point.

    A scan point with no acquisition inside its interval is dropped rather than
    matched to the neighbouring one: a mis-assigned acquisition is a wrong
    target, while a missing point only costs one constraint.
    """
    times = list(measurements)
    found = []
    for entry, next_entry in zip(entries, entries[1:], strict=False):
        start = pd.to_datetime(entry["write_started_utc"])
        end = pd.to_datetime(next_entry["write_started_utc"])
        index = bisect_left(times, start)
        if index == len(times) or times[index] > end:
            continue
        found.append(
            ScanPoint(
                corrector=entry["parameter"],
                plane=entry["plane"],
                rf_offset=float(entry.get("rf_offset_mm") or 0.0),
                offset_k=float(entry["offset_k"]),
                path=measurements[times[index]],
            )
        )
    return found


def read_scan_log(
    json_path: Path = JSON_PATH, *, rf_offset_override: float | None = None
) -> list[dict]:
    """Read the scan JSONL, keeping only usable corrector points, in time order.

    *rf_offset_override* is for a scan log whose RF condition was set by which
    directory it was written to rather than an ``rf_offset_mm`` field on each
    entry -- see :attr:`~loco_common.campaign.Campaign.rf_scan_logs`. Every entry
    is stamped with it, replacing whatever (usually absent) value it carried.
    """
    entries = [json.loads(line) for line in json_path.read_text().splitlines() if line.strip()]
    entries = [
        entry
        for entry in entries
        if entry.get("plane") in ("x", "y")
        and entry.get("parameter")
        and (rf_offset_override is not None or entry.get("rf_offset_mm") in RF_STEERING_OFFSETS)
    ]
    if rf_offset_override is not None:
        for entry in entries:
            entry["rf_offset_mm"] = rf_offset_override
    entries.sort(key=lambda entry: pd.to_datetime(entry["write_started_utc"]))
    return entries


def load_scan(
    json_path: Path | None = None,
    measurements_path: Path | None = None,
    *,
    campaign: Campaign = NORMAL,
) -> tuple[list[ScanPoint], dict[Path, dict[str, tuple[pd.Series, pd.Series]]]]:
    """Read the scan log and every acquisition it points at.

    Each distinct file is read exactly once and reused for both planes and every
    RF setting; that read is the whole cost of this module.

    A campaign whose RF-offset conditions were scanned as separate runs rather
    than as an ``rf_offset_mm`` column -- :attr:`Campaign.rf_scan_logs` -- has
    those runs' logs merged in here, each stamped with its own RF offset.
    """
    json_path = json_path or campaign.scan_log
    measurements_path = measurements_path or campaign.measurements_path
    entries = read_scan_log(json_path)
    for rf_offset, extra_log in campaign.rf_scan_logs.items():
        entries += read_scan_log(extra_log, rf_offset_override=rf_offset)
    entries.sort(key=lambda entry: pd.to_datetime(entry["write_started_utc"]))
    points = find_scan_measurements(entries, load_measurements(measurements_path))
    if not points:
        raise RuntimeError("No scan measurements could be associated with the JSON log.")
    paths = sorted({point.path for point in points})
    with ThreadPoolExecutor(max_workers=READ_WORKERS) as executor:
        orbit_by_path = dict(zip(paths, executor.map(closed_orbit, paths), strict=False))
    logger.info("Associated %d scan points with %d acquisitions", len(points), len(paths))
    return points, orbit_by_path


def cached_scan(
    json_path: Path | None = None,
    measurements_path: Path | None = None,
    *,
    campaign: Campaign = NORMAL,
    refresh: bool = False,
) -> tuple[list[ScanPoint], dict[Path, dict[str, tuple[pd.Series, pd.Series]]]]:
    """:func:`load_scan`, cached to parquet: the same ``(points, orbit_by_path)``.

    The SDDS read is ~10 minutes for the whole scan and every derived product --
    both methods, every RF offset, the plots -- starts from it, so it is cached
    whole rather than per product. The cache is keyed by *campaign* and by nothing
    else: within one campaign it is the scan, so pass *refresh* if the
    acquisitions themselves have changed.
    """
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    orbit_cache = campaign.cache_file("scan_orbits.parquet")
    point_cache = campaign.cache_file("scan_points.parquet")
    if orbit_cache.exists() and point_cache.exists() and not refresh:
        orbits = pd.read_parquet(orbit_cache)
        table = pd.read_parquet(point_cache)
        points = [
            ScanPoint(
                corrector=row.CORRECTOR,
                plane=row.PLANE,
                rf_offset=float(row.RF_OFFSET),
                offset_k=float(row.OFFSET_K),
                path=Path(row.PATH),
            )
            for row in table.itertuples()
        ]
        orbit_by_path = {
            Path(path): {
                "X": (group["X"], group["ERRX"]),
                "Y": (group["Y"], group["ERRY"]),
            }
            for path, group in orbits.set_index("NAME").groupby("PATH")
        }
        logger.info(
            "Loaded %d %s scan points from the cache", len(points), campaign.slug
        )
        return points, orbit_by_path

    points, orbit_by_path = load_scan(json_path, measurements_path, campaign=campaign)
    pd.DataFrame(
        [
            {
                "CORRECTOR": point.corrector,
                "PLANE": point.plane,
                "RF_OFFSET": point.rf_offset,
                "OFFSET_K": point.offset_k,
                "PATH": str(point.path),
            }
            for point in points
        ]
    ).to_parquet(point_cache)
    pd.concat(
        [_orbit_frame(orbit).assign(PATH=str(path)) for path, orbit in orbit_by_path.items()]
    ).reset_index().to_parquet(orbit_cache)
    return points, orbit_by_path


def available_rf_offsets(campaign: Campaign) -> list[float]:
    """Distinct RF offsets this campaign's scan actually has data for, 0 included.

    Some campaigns only ever ran a three-point steering scan (e.g. -2/0/+2 mm)
    rather than the full five-point one, so a fixed offset list is wrong; this
    reads it back from the cache instead.
    """
    points, _ = cached_scan(campaign=campaign)
    offsets = {point.rf_offset for point in points}
    offsets.add(0.0)
    return sorted(offsets)


def _points_for(points: list[ScanPoint], corrector: str, rf_offset: float) -> list[ScanPoint]:
    return sorted(
        (p for p in points if p.corrector == corrector and p.rf_offset == rf_offset),
        key=lambda p: p.offset_k,
    )


def _orbit_frame(
    orbit: dict[str, tuple[pd.Series, pd.Series]], bpms: pd.Index | None = None
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "X": orbit["X"][0],
            "ERRX": orbit["X"][1],
            "Y": orbit["Y"][0],
            "ERRY": orbit["Y"][1],
        }
    )
    frame.index.name = "NAME"
    return frame if bpms is None else frame.loc[bpms]


def average_orbit_frames(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Average repeat acquisitions of one machine state, errors as the SEM.

    The values are a plain mean; the errors are combined as
    ``sqrt(sum(err**2)) / N``, which is the standard error *of the mean* and
    shrinks with the repeat count. Averaging the error columns alongside the
    values -- what ``sum(frames) / len(frames)`` does, since pandas addition
    hits ``ERRX``/``ERRY`` too -- leaves ``mean(err)``, a factor ``sqrt(N)``
    too large, and under-weights the averaged orbit by ``N`` in the fit.

    With equal errors this is exactly the inverse-variance weighted mean that
    ``aba_optimiser.measurements.orbit_averaging`` uses, so the two repositories
    agree on the convention.
    """
    frames = list(frames)
    if not frames:
        raise ValueError("No frames to average")
    averaged = pd.DataFrame(index=frames[0].index)
    averaged.index.name = frames[0].index.name
    for value, error in (("X", "ERRX"), ("Y", "ERRY")):
        averaged[value] = np.mean([f[value] for f in frames], axis=0)
        averaged[error] = np.sqrt(np.sum([f[error] ** 2 for f in frames], axis=0)) / len(frames)
    return averaged[["X", "ERRX", "Y", "ERRY"]]


def global_reference_orbit(
    points: list[ScanPoint], orbit_by_path: dict
) -> pd.DataFrame:
    """The one orbit every measurement is referred to: no trim, nominal RF.

    Every corrector's ``offset_k = 0`` acquisition at ``rf_offset = 0`` sat on
    the same machine, so these are repeats of a single orbit and are averaged;
    the error of the mean shrinks with the repeat count accordingly.
    """
    zero = [p for p in points if p.rf_offset == 0.0 and p.offset_k == 0.0]
    if not zero:
        raise ValueError("The scan carries no untrimmed acquisition at nominal RF")
    frames = [_orbit_frame(orbit_by_path[p.path]) for p in zero]
    reference = average_orbit_frames(frames)
    logger.info("Global reference orbit averaged over %d untrimmed acquisitions", len(frames))
    return reference


def subtract_reference(
    frame: pd.DataFrame,
    reference: pd.DataFrame,
    absolute_planes: Sequence[str] = (),
) -> pd.DataFrame:
    """``frame - reference`` per plane, errors added in quadrature.

    A plane named in *absolute_planes* is passed through untouched: no reference
    is removed and no reference error is added, because there is no reference
    orbit on that side of the fit. That plane's target is then the machine's
    *absolute* closed orbit, which is what dipole errors and quadrupole
    misalignments -- not gradients -- have to explain. The model side has to
    match, via ``ClosedOrbitSeries.absolute_planes``.
    """
    unknown = set(absolute_planes) - set(PLANE_COLUMNS)
    if unknown:
        raise ValueError(f"Unknown plane(s) {sorted(unknown)}; expected x and/or y")
    delta = pd.DataFrame(index=frame.index)
    for plane, (value, error) in PLANE_COLUMNS.items():
        if plane in absolute_planes:
            delta[value] = frame[value]
            delta[error] = frame[error]
            continue
        delta[value] = frame[value] - reference.loc[frame.index, value]
        delta[error] = np.hypot(frame[error], reference.loc[frame.index, error])
    return delta


def apply_error_floor(
    frame: pd.DataFrame, floor: float, planes: Sequence[str] = ()
) -> pd.DataFrame:
    """``err <- hypot(err, floor)`` in *planes*; identity when *floor* is zero.

    An absolute-orbit target's error bar is not its acquisition SEM. The SEM is
    ~1e-6 m; the uncertainty that actually applies is the BPM zero offset, which
    is not fitted here and is ~1e-4 m. Without this floor the absolute planes
    enter the summed objective at thousands of sigma and the delta planes stop
    mattering. The floor is therefore a stated systematic, and its value is
    something to scan rather than to trust.
    """
    if not floor or not planes:
        return frame
    if floor < 0.0:
        raise ValueError("absolute_error_floor must be >= 0")
    floored = frame.copy()
    for plane in planes:
        _, error = PLANE_COLUMNS[plane]
        floored[error] = np.hypot(frame[error], floor)
    return floored


def measured_orbits(
    rf_offset: float = 0.0,
    *,
    points: list[ScanPoint] | None = None,
    orbit_by_path: dict | None = None,
    reference: pd.DataFrame | None = None,
    delta: bool = True,
    absolute_planes: Sequence[str] = (),
    error_floor: float = 0.0,
    campaign: Campaign = NORMAL,
) -> dict[tuple[str, float], pd.DataFrame]:
    """Closed orbits per ``(corrector, offset_k)``, as ``X/ERRX/Y/ERRY`` in metres.

    With *delta* (the default, and what Method 2 fits) the single global
    reference orbit -- untrimmed correctors at nominal RF -- is subtracted from
    every acquisition and its error added in quadrature. At ``rf_offset = 0``
    the ``offset_k = 0`` points are then zero to within noise and are dropped;
    at any other RF setting they are *not*, they are that momentum's dispersion
    orbit, and they are kept under the key ``(corrector, 0.0)``.

    *absolute_planes* exempts a plane from that subtraction. Two consequences:
    the exempted plane keeps the machine's static closed orbit, and the
    ``rf_offset = 0, offset_k = 0`` acquisitions stop being zero by
    construction -- they become the untrimmed static orbit itself, the single
    most direct constraint on bends and quadrupole ``dy``, so they are kept
    rather than dropped. *error_floor* is added in quadrature to the exempted
    planes' errors; see :func:`apply_error_floor` for why it is needed.
    """
    if points is None or orbit_by_path is None:
        points, orbit_by_path = cached_scan(campaign=campaign)
    selected = [p for p in points if p.rf_offset == rf_offset]
    orbits: dict[tuple[str, float], pd.DataFrame] = {}
    # Pass *reference* when *points* has been pre-filtered: the global reference
    # lives at rf_offset 0, so a caller handing in one RF setting's points cannot
    # have it computed for them.
    if delta and reference is None:
        reference = global_reference_orbit(points, orbit_by_path)
    for corrector in dict.fromkeys(p.corrector for p in selected):
        corrector_points = _points_for(selected, corrector, rf_offset)
        frames = [_orbit_frame(orbit_by_path[p.path]) for p in corrector_points]
        offsets = np.array([p.offset_k for p in corrector_points])
        if not frames:
            continue
        if not delta:
            orbits.update({(corrector, o): f for o, f in zip(offsets, frames, strict=True)})
            continue
        for offset, frame in zip(offsets, frames, strict=True):
            if offset == 0.0 and rf_offset == 0.0 and not absolute_planes:
                continue
            orbits[(corrector, float(offset))] = apply_error_floor(
                subtract_reference(frame, reference, absolute_planes),
                error_floor,
                absolute_planes,
            )
    return orbits


def _weighted_slope(
    offsets: np.ndarray, values: np.ndarray, errors: np.ndarray
) -> tuple[float, float, float]:
    """Weighted straight-line fit; return slope, its error, and the intercept.

    A free intercept is kept even though the reference point is zero by
    construction: forcing the line through it would give that one acquisition the
    weight of the whole fit.
    """
    finite = np.isfinite(values) & np.isfinite(errors) & (errors > 0)
    if finite.sum() < 2 or len(np.unique(offsets[finite])) < 2:
        return float("nan"), float("nan"), float("nan")
    x, y, weight = offsets[finite], values[finite], 1.0 / errors[finite] ** 2
    design = np.vstack([x, np.ones_like(x)]).T
    scaled = design * weight[:, None]
    covariance = np.linalg.inv(design.T @ scaled)
    slope, intercept = covariance @ (scaled.T @ y)
    return float(slope), float(np.sqrt(covariance[0, 0])), float(intercept)


def measured_response(
    rf_offset: float = 0.0,
    *,
    points: list[ScanPoint] | None = None,
    orbit_by_path: dict | None = None,
    reference: pd.DataFrame | None = None,
    campaign: Campaign = NORMAL,
) -> pd.DataFrame:
    """Per-BPM orbit response ``d(orbit)/d(k)`` in m/rad, one row per (BPM, corrector).

    Columns: ``NAME``, ``CORRECTOR``, ``PLANE`` (the BPM channel), ``SLOPE``,
    ``ERRSLOPE`` and ``INTERCEPT`` (which the fit keeps free and the methods
    ignore; it is there so a plot can draw the line that was actually fitted).
    Both BPM channels are retained for every corrector, giving the conventional
    ``(2*N_BPM) x N_corrector`` orbit-response matrix.
    """
    if points is None or orbit_by_path is None:
        points, orbit_by_path = cached_scan(campaign=campaign)
    selected = [p for p in points if p.rf_offset == rf_offset]
    # Any constant reference gives the same slope -- the fit keeps the intercept
    # free -- so this only has to be *a* consistent orbit. It is the global one
    # for the sake of the intercept a plot draws, and so both methods can say
    # they subtracted the same thing.
    if reference is None:
        reference = global_reference_orbit(points, orbit_by_path)
    rows = []
    for corrector in dict.fromkeys(p.corrector for p in selected):
        corrector_points = _points_for(selected, corrector, rf_offset)
        if len(corrector_points) < 2:
            logger.warning("Corrector %s has %d points; skipped", corrector, len(corrector_points))
            continue
        frames = [
            subtract_reference(_orbit_frame(orbit_by_path[p.path]), reference) for p in corrector_points
        ]
        offsets = np.array([p.offset_k for p in corrector_points])
        for plane, (value_column, error_column) in PLANE_COLUMNS.items():
            for bpm in frames[0].index:
                values = np.array([f.loc[bpm, value_column] for f in frames])
                errors = np.array([f.loc[bpm, error_column] for f in frames])
                slope, slope_error, intercept = _weighted_slope(offsets, values, errors)
                rows.append(
                    {
                        "NAME": bpm,
                        "CORRECTOR": corrector,
                        "PLANE": plane,
                        "SLOPE": slope,
                        "ERRSLOPE": slope_error,
                        "INTERCEPT": intercept,
                    }
                )
    return pd.DataFrame(rows)


def cached_response(
    rf_offset: float = 0.0, *, campaign: Campaign = NORMAL, refresh: bool = False
) -> pd.DataFrame:
    """:func:`measured_response`, cached to parquet under :data:`CACHE_PATH`."""
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    name = f"response_xy_rf{rf_offset:+g}.parquet".replace("+", "p").replace("-", "m")
    cache = campaign.cache_file(name)
    if cache.exists() and not refresh:
        return pd.read_parquet(cache)
    response = measured_response(rf_offset, campaign=campaign)
    response.to_parquet(cache)
    return response


def cached_orbits(
    rf_offset: float = 0.0, *, campaign: Campaign = NORMAL, refresh: bool = False
) -> dict[tuple[str, float], pd.DataFrame]:
    """:func:`measured_orbits`, cached to a single tidy parquet file."""
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    name = f"orbits_rf{rf_offset:+g}.parquet".replace("+", "p").replace("-", "m")
    cache = campaign.cache_file(name)
    if cache.exists() and not refresh:
        stacked = pd.read_parquet(cache)
        return {
            (corrector, float(offset)): frame.drop(columns=["CORRECTOR", "OFFSET_K"])
            for (corrector, offset), frame in stacked.groupby(["CORRECTOR", "OFFSET_K"])
        }
    orbits = measured_orbits(rf_offset, campaign=campaign)
    stacked = pd.concat(
        [frame.assign(CORRECTOR=corrector, OFFSET_K=offset) for (corrector, offset), frame in orbits.items()]
    )
    stacked.to_parquet(cache)
    return orbits
