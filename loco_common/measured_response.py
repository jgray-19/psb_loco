"""Measured orbit response of PSB ring 3 to its DHZ/DVT correctors.

``psb_md/scan_psb_loco.py`` steps each of six DHZ and six DVT correctors through
``offset_k = 0, +dk, -dk, +2dk, -2dk`` and writes it back to its start-up value
(a ``reset``) before the next one, once per RF-steering offset. The BPM
acquisition runs independently of it, so the scan log only records *when* each
setting was written. This module turns those acquisitions plus the logs of a
campaign (:mod:`loco_common.campaign`) into the two things the fitters need:

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

Reading the SDDS files dominates the runtime (~650 acquisitions per campaign), so
both products are cached to parquet under the campaign's cache files.
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

if TYPE_CHECKING:
    from collections.abc import Sequence

    from loco_common.campaign import Campaign

logger = logging.getLogger(__name__)

MEASUREMENT_PATTERN = "MULTITURN_ACQ__*.sdds"
READ_WORKERS = 8

#: The longest the scan holds one setting between two writes: two 10.8 s
#: supercycles. The scan log does not record when the RF was changed for the next
#: run, so an acquisition later than this after a log's final write is not a scan
#: acquisition.
MAX_HOLD = pd.Timedelta(seconds=21.6)

#: Value and error columns of each plane, in the orbit frames this module builds.
PLANE_COLUMNS: dict[str, tuple[str, str]] = {"x": ("X", "ERRX"), "y": ("Y", "ERRY")}


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


def load_measurements(measurements_path: Path) -> dict[pd.Timestamp, Path]:
    """Map each acquisition's local timestamp to its file, in time order."""
    measurements = {}
    for path in measurements_path.glob(MEASUREMENT_PATTERN):
        timestamp = pd.to_datetime(
            path.stem.split("__", 1)[1], format="%d-%m-%y_%H-%M-%S"
        ).tz_localize("Europe/Zurich")
        measurements[timestamp] = path
    return dict(sorted(measurements.items()))


def read_scan_log(json_path: Path) -> list[dict]:
    """Every setting one scan log wrote, in time order: ``scan_point`` and ``reset``.

    A reset writes the corrector back to its start-up value, so it is the
    untrimmed machine (``offset_k = 0``) and its acquisitions count like any
    other. The ``restore`` events after the scan rewrite the same start-up values
    and change nothing.
    """
    entries = [json.loads(line) for line in json_path.read_text().splitlines() if line.strip()]
    entries = [entry for entry in entries if entry["event"] in ("scan_point", "reset")]
    return sorted(entries, key=lambda entry: pd.to_datetime(entry["write_started_utc"]))


def find_scan_measurements(
    entries: list[dict], measurements: dict[pd.Timestamp, Path], rf_offset: float
) -> list[ScanPoint]:
    """Tag every acquisition taken while one of a log's settings was held.

    A setting holds from its write to the next write. The cycle that triggered a
    write still measured the previous setting, and its file is stamped just before
    that cycle, so the write time separates the two on both sides. Repeat
    acquisitions of one setting are all kept. Two ends of the log differ:

    * the first setting is offset zero, the start-up state the machine was
      already in, so it also owns the cycles since the scan's first cycle stamp;
    * no write ends the last setting, so it is held for at most :data:`MAX_HOLD`.
    """
    times = list(measurements)
    points = []
    for index, entry in enumerate(entries):
        start = pd.to_datetime(
            entry["cycle_stamp_trigger" if index == 0 else "write_started_utc"]
        )
        end = pd.to_datetime(entry["write_started_utc"]) + MAX_HOLD
        if index + 1 < len(entries):
            end = min(end, pd.to_datetime(entries[index + 1]["write_started_utc"]))
        points += [
            ScanPoint(
                corrector=entry["parameter"],
                plane=entry["plane"],
                rf_offset=rf_offset,
                offset_k=float(entry["offset_k"]),
                path=measurements[time],
            )
            for time in times[bisect_left(times, start) : bisect_left(times, end)]
        ]
    return points


def load_scan(
    campaign: Campaign,
) -> tuple[list[ScanPoint], dict[Path, dict[str, tuple[pd.Series, pd.Series]]]]:
    """Read every scan log of *campaign* and every acquisition they point at.

    Each distinct file is read exactly once and reused for both planes and every
    RF setting; that read is the whole cost of this module.
    """
    measurements = load_measurements(campaign.measurements_path)
    points = [
        point
        for rf_offset, log in campaign.scan_logs.items()
        for point in find_scan_measurements(read_scan_log(log), measurements, rf_offset)
    ]
    paths = sorted({point.path for point in points})
    with ThreadPoolExecutor(max_workers=READ_WORKERS) as executor:
        orbit_by_path = dict(zip(paths, executor.map(closed_orbit, paths), strict=True))
    logger.info(
        "Associated %d of %d acquisitions with the %s scan",
        len(paths), len(measurements), campaign.slug,
    )
    return points, orbit_by_path


def cached_scan(
    campaign: Campaign, *, refresh: bool = False
) -> tuple[list[ScanPoint], dict[Path, dict[str, tuple[pd.Series, pd.Series]]]]:
    """:func:`load_scan`, cached to parquet: the same ``(points, orbit_by_path)``.

    The SDDS read is ~10 minutes for a whole campaign and every derived product --
    both methods, every RF offset, the plots -- starts from it, so it is cached
    whole rather than per product. Pass *refresh* if the acquisitions or the
    association have changed.
    """
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

    points, orbit_by_path = load_scan(campaign)
    orbit_cache.parent.mkdir(parents=True, exist_ok=True)
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


def _orbit_frame(orbit: dict[str, tuple[pd.Series, pd.Series]]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "X": orbit["X"][0],
            "ERRX": orbit["X"][1],
            "Y": orbit["Y"][0],
            "ERRY": orbit["Y"][1],
        }
    )
    frame.index.name = "NAME"
    return frame


def pooled_intershot_noise(
    points: list[ScanPoint], orbit_by_path: dict
) -> pd.DataFrame:
    """Per-BPM shot-to-shot orbit jitter, pooled over every untrimmed repeat group.

    The untrimmed acquisitions (``offset_k = 0``) at one RF offset are repeats of
    one machine state: 24 at nominal RF (the global reference), 12 at each other
    RF setting. Their scatter is what one acquisition's turn-averaged error
    (``ERRX``/``ERRY``, ~0.2 um) misses -- shot-to-shot jitter and corrector
    hysteresis, measured at 3-5 um in x. Grouping by RF offset keeps each
    acquisition in exactly one group.

    Groups have different means but share one noise process, so the variance is
    pooled over degrees of freedom, ``sum((n_g - 1) s_g**2) / sum(n_g - 1)``,
    rather than an RMS of per-group values that would weight a 12-frame group like
    the 24-frame one. The mean turn-noise variance is then subtracted: each frame's
    scatter already contains it, and :func:`average_orbit_frames` adds it back in
    quadrature.

    Returns ``ERRX``/``ERRY`` per BPM, in metres.
    """
    groups: dict[float, list[pd.DataFrame]] = {}
    for point in points:
        if point.offset_k == 0.0:
            groups.setdefault(point.rf_offset, []).append(_orbit_frame(orbit_by_path[point.path]))
    dof = sum(len(frames) - 1 for frames in groups.values())
    if dof == 0:
        raise ValueError("No repeated untrimmed acquisitions to estimate intershot noise from")
    index = next(iter(groups.values()))[0].index
    noise = pd.DataFrame(index=index)
    for value, error in (("X", "ERRX"), ("Y", "ERRY")):
        squares = 0.0
        for frames in groups.values():
            values = np.array([f[value] for f in frames])
            squares = squares + ((values - values.mean(axis=0)) ** 2).sum(axis=0)
        turn_variance = np.mean(
            [f[error] ** 2 for frames in groups.values() for f in frames], axis=0
        )
        noise[error] = np.sqrt(np.clip(squares / dof - turn_variance, 0.0, None))
    logger.info(
        "Intershot noise pooled over %d repeat groups (%d dof): median %.3g m in x, %.3g m in y",
        len(groups),
        dof,
        noise["ERRX"].median(),
        noise["ERRY"].median(),
    )
    return noise


def average_orbit_frames(
    frames: Sequence[pd.DataFrame], intershot: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Average acquisitions of one machine state: plain mean, error of the mean.

    Two independent noise sources, added in quadrature:

    - *turn* noise, ``sqrt(sum(err**2)) / N`` from each frame's ``ERRX``/``ERRY``;
    - *intershot* noise, ``intershot / sqrt(N)``, the per-BPM jitter from
      :func:`pooled_intershot_noise`. It applies to single acquisitions too
      (``N = 1``), which have no scatter of their own to estimate it from.

    Pass *intershot* only for raw acquisitions. Frames that are already averages
    (``average_zero_step``, the per-RF absolute orbits) carry it in their errors.
    """
    frames = list(frames)
    n = len(frames)
    averaged = pd.DataFrame(index=frames[0].index)
    for value, error in (("X", "ERRX"), ("Y", "ERRY")):
        averaged[value] = np.mean([f[value] for f in frames], axis=0)
        variance = np.sum([f[error] ** 2 for f in frames], axis=0) / n**2
        if intershot is not None:
            variance = variance + intershot.loc[averaged.index, error].to_numpy() ** 2 / n
        averaged[error] = np.sqrt(variance)
    return averaged[["X", "ERRX", "Y", "ERRY"]]


def global_reference_orbit(
    points: list[ScanPoint], orbit_by_path: dict, intershot: pd.DataFrame | None = None
) -> pd.DataFrame:
    """The one orbit every measurement is referred to: no trim, nominal RF.

    Every untrimmed acquisition at ``rf_offset = 0`` -- each corrector's zero
    step and every reset -- sat on the same machine, so these are repeats of a
    single orbit and are averaged; the error of the mean shrinks accordingly.
    *intershot* defaults to :func:`pooled_intershot_noise` of the same scan.
    """
    if intershot is None:
        intershot = pooled_intershot_noise(points, orbit_by_path)
    frames = [
        _orbit_frame(orbit_by_path[p.path])
        for p in points
        if p.rf_offset == 0.0 and p.offset_k == 0.0
    ]
    logger.info("Global reference orbit averaged over %d untrimmed acquisitions", len(frames))
    return average_orbit_frames(frames, intershot)


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


def measured_orbits(
    rf_offset: float = 0.0,
    *,
    points: list[ScanPoint] | None = None,
    orbit_by_path: dict | None = None,
    reference: pd.DataFrame | None = None,
    delta: bool = True,
    absolute_planes: Sequence[str] = (),
    intershot: pd.DataFrame | None = None,
    campaign: Campaign | None = None,
) -> dict[tuple[str, float], pd.DataFrame]:
    """Closed orbits per ``(corrector, offset_k)``, as ``X/ERRX/Y/ERRY`` in metres.

    Pass either a campaign or its ``(points, orbit_by_path)``. Repeat
    acquisitions of one ``(corrector, offset_k)`` -- a setting held over two
    cycles, or a corrector's zero step and its reset -- are averaged first.

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
    rather than dropped.

    Every acquisition's error includes *intershot* noise, which defaults to
    :func:`pooled_intershot_noise` of the scan; pass it to compute it once.
    """
    if points is None or orbit_by_path is None:
        points, orbit_by_path = cached_scan(campaign)
    # Pass *reference* and *intershot* when *points* has been pre-filtered: both
    # need the untrimmed acquisitions of every RF offset.
    if intershot is None:
        intershot = pooled_intershot_noise(points, orbit_by_path)
    if delta and reference is None:
        reference = global_reference_orbit(points, orbit_by_path, intershot)
    repeats: dict[tuple[str, float], list[pd.DataFrame]] = {}
    for point in points:
        if point.rf_offset == rf_offset:
            repeats.setdefault((point.corrector, point.offset_k), []).append(
                _orbit_frame(orbit_by_path[point.path])
            )
    orbits: dict[tuple[str, float], pd.DataFrame] = {}
    for (corrector, offset), frames in repeats.items():
        frame = average_orbit_frames(frames, intershot)
        if not delta:
            orbits[(corrector, offset)] = frame
        elif offset != 0.0 or rf_offset != 0.0 or absolute_planes:
            orbits[(corrector, offset)] = subtract_reference(frame, reference, absolute_planes)
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
    intershot: pd.DataFrame | None = None,
    campaign: Campaign | None = None,
) -> pd.DataFrame:
    """Per-BPM orbit response ``d(orbit)/d(k)`` in m/rad, one row per (BPM, corrector).

    Columns: ``NAME``, ``CORRECTOR``, ``PLANE`` (the BPM channel), ``SLOPE``,
    ``ERRSLOPE`` and ``INTERCEPT`` (which the fit keeps free and the methods
    ignore; it is there so a plot can draw the line that was actually fitted).
    Both BPM channels are retained for every corrector, giving the conventional
    ``(2*N_BPM) x N_corrector`` orbit-response matrix. Every acquisition enters
    the line fit, repeats included, each with the *intershot* noise
    (default :func:`pooled_intershot_noise`) added to its turn error.
    """
    if points is None or orbit_by_path is None:
        points, orbit_by_path = cached_scan(campaign)
    selected = [p for p in points if p.rf_offset == rf_offset]
    # Any constant reference gives the same slope -- the fit keeps the intercept
    # free -- so this only has to be *a* consistent orbit. It is the global one
    # for the sake of the intercept a plot draws, and so both methods can say
    # they subtracted the same thing.
    if intershot is None:
        intershot = pooled_intershot_noise(points, orbit_by_path)
    if reference is None:
        reference = global_reference_orbit(points, orbit_by_path, intershot)
    rows = []
    for corrector in dict.fromkeys(p.corrector for p in selected):
        corrector_points = [p for p in selected if p.corrector == corrector]
        frames = [
            subtract_reference(
                average_orbit_frames([_orbit_frame(orbit_by_path[p.path])], intershot), reference
            )
            for p in corrector_points
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


def _cache_name(stem: str, rf_offset: float) -> str:
    return f"{stem}_rf{rf_offset:+g}.parquet".replace("+", "p").replace("-", "m")


def cached_response(
    rf_offset: float, *, campaign: Campaign, refresh: bool = False
) -> pd.DataFrame:
    """:func:`measured_response`, cached to parquet."""
    cache = campaign.cache_file(_cache_name("response_xy", rf_offset))
    if cache.exists() and not refresh:
        return pd.read_parquet(cache)
    response = measured_response(rf_offset, campaign=campaign)
    response.to_parquet(cache)
    return response


def cached_orbits(
    rf_offset: float, *, campaign: Campaign, refresh: bool = False
) -> dict[tuple[str, float], pd.DataFrame]:
    """:func:`measured_orbits`, cached to a single tidy parquet file."""
    cache = campaign.cache_file(_cache_name("orbits", rf_offset))
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
