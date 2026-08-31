"""Kick-to-kick error bars for the driven-optics measurement.

omc3 quotes an error per BPM that it propagates from the phase errors of one
pooled analysis of a whole ACD folder. Nothing in that bar is a repeat
measurement, so it does not know how much the machine moves between kicks -- and
measured against the folder's own kicks it is several times too small.

The bar this module builds is a bootstrap over kicks: resample the folder's
kicks with replacement, rerun the compensated-optics stage on each replica, and
take the spread of the resulting betas. The replica keeps the folder's kick
count, so the 3-BPM beta-from-phase stays as well conditioned as it is in the
real measurement -- which matters, because from a single kick that method is
badly enough conditioned to return a negative beta.

Only the harpy stage is expensive and it is already cached as lin files, so a
replica costs a fraction of a second.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

#: Bootstrap replicas per folder. The spread of a spread converges slowly, but
#: the bar only needs its leading digit and 100 puts that well inside 10%.
REPLICAS = 100


def lin_bases(folder_root: Path) -> list[Path]:
    """Every kick under *folder_root* that has a paired ``.linx``/``.liny``."""
    lin_dir = folder_root / "driven" / "lin_files"
    bases = sorted(
        path.with_suffix("")
        for path in lin_dir.glob("*.linx")
        if path.with_suffix(".liny").exists()
    )
    if not bases:
        raise FileNotFoundError(f"No paired lin files under {lin_dir}")
    return bases


def optics_for(
    bases: list[Path],
    model_dir: Path,
    work: Path,
    read_frame: Callable[[Path], pd.DataFrame],
) -> pd.DataFrame | None:
    """Run the compensated-optics stage on one set of kicks.

    A repeated base is staged under a fresh name, so a replica that drew a kick
    twice really carries it twice instead of collapsing to the unique set.
    """
    from psb_md.hio_analysis import run_driven_compensated_optics_from_lin_files  # noqa: PLC0415

    lin_dir, out_dir = work / "lin", work / "out"
    shutil.rmtree(work, ignore_errors=True)
    lin_dir.mkdir(parents=True)
    for number, base in enumerate(bases):
        for suffix in (".linx", ".liny"):
            shutil.copy(base.with_suffix(base.suffix + suffix), lin_dir / f"{number:04d}{suffix}")
    try:
        run_driven_compensated_optics_from_lin_files(lin_dir, model_dir, out_dir)
    except Exception as error:  # one bad replica must not lose the rest
        logger.warning("optics failed on a replica of %d kicks (%s)", len(bases), error)
        return None
    return read_frame(out_dir)


def bootstrap_frames(
    folder_root: Path,
    read_frame: Callable[[Path], pd.DataFrame],
    *,
    replicas: int = REPLICAS,
    seed: int = 0,
    single: bool = False,
) -> pd.DataFrame:
    """One row per (replica, BPM). *single* runs each kick alone instead.

    The single-kick mode is a diagnostic, not an error bar: see the module
    docstring on why one kick is too ill-conditioned to resample from.
    """
    model_dir = folder_root / "omc3_model"
    bases = lin_bases(folder_root)
    rng = np.random.default_rng(seed)
    draws = (
        [[base] for base in bases]
        if single
        else [list(rng.choice(bases, size=len(bases), replace=True)) for _ in range(replicas)]
    )
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "replica"
        for number, draw in enumerate(draws, start=1):
            frame = optics_for(draw, model_dir, work, read_frame)
            if frame is None:
                continue
            rows.append(frame.assign(REPLICA=number))
    if not rows:
        raise RuntimeError(f"Every replica of {folder_root} failed the optics stage")
    return pd.concat(rows).reset_index()


def bootstrap_errors(
    folder_root: Path,
    read_frame: Callable[[Path], pd.DataFrame],
    *,
    replicas: int = REPLICAS,
    seed: int = 0,
) -> pd.DataFrame:
    """Per-BPM bootstrap error for every measured column *read_frame* returns.

    Columns are named as the measurement's own error columns -- ``beta_x`` gives
    ``beta_x_err`` -- so the result can be dropped straight onto the frame.
    """
    frames = bootstrap_frames(folder_root, read_frame, replicas=replicas, seed=seed)
    measured = [
        column
        for column in frames.columns
        if column not in ("NAME", "REPLICA") and not column.endswith(("_err", "_model"))
    ]
    errors = frames.groupby("NAME")[measured].std(ddof=1)
    return errors.rename(columns={column: f"{column}_err" for column in measured})


def apply_bootstrap_errors(
    measured: pd.DataFrame,
    folder_root: Path,
    read_frame: Callable[[Path], pd.DataFrame],
    *,
    replicas: int = REPLICAS,
    seed: int = 0,
) -> pd.DataFrame:
    """*measured* with the bootstrap added in quadrature to its quoted errors.

    Added, not substituted, because the two bars cover different things and
    neither contains the other. The bootstrap resamples within one kick set, so
    it sees how much the machine moves between kicks but is blind to anything
    common to the whole folder -- the kick normalisation and the BPM
    calibration that the amplitude beta leans on. omc3's propagated bar carries
    those and no repeat of the machine. Phase beta is dominated by the
    bootstrap and grows several times; amplitude beta is dominated by omc3's
    and barely moves.

    A column the bootstrap could not produce keeps omc3's bar rather than
    losing it.
    """
    errors = bootstrap_errors(folder_root, read_frame, replicas=replicas, seed=seed)
    updated = measured.copy()
    for column in errors.columns:
        if column not in updated.columns:
            continue
        resampled = errors[column].reindex(updated.index)
        combined = np.hypot(resampled, updated[column]).fillna(updated[column])
        logger.info(
            "%s: %s bootstrap %.4g, omc3 %.4g, combined %.4g (x%.1f)",
            folder_root.name, column,
            resampled.median(), updated[column].median(), combined.median(),
            (combined / updated[column]).median(),
        )
        updated[column] = combined
    return updated
