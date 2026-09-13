"""Load fit results into tidy frames. One loader per artifact kind, no page logic."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd

from loco_common.campaign import Campaign
from loco_common.case_names import METHOD1_OPTION
from loco_common.fit_mode import FitMode, result_is_valid

logger = logging.getLogger(__name__)

#: Scored measurement kinds, as (prediction file stem, axis label).
RESIDUAL_TARGETS = {
    "delta": "delta-orbit residual [mm]",
    "absolute": "closed-orbit residual [mm]",
}


@dataclass(frozen=True)
class Results:
    """Every path and frame for one (campaign, momentum mode)."""

    campaign: Campaign
    mode: FitMode
    positions: dict[str, float]

    @property
    def matrix(self) -> Path:
        return self.mode.results_root(self.campaign)

    @property
    def predictions(self) -> Path:
        return self.matrix / "predictions"

    @property
    def optics_dir(self) -> Path:
        return self.matrix / "optics"

    def has(self, option: str) -> bool:
        """Whether this option produced a usable fit."""
        return option == METHOD1_OPTION or result_is_valid(self.matrix / option)

    def valid(self, options) -> tuple[str, ...]:
        return tuple(option for option in options if self.has(option))

    def knobs(self, option: str) -> pd.DataFrame:
        return knobs(self.matrix / option / "knobs.csv", self.positions)

    def summary(self, option: str) -> dict:
        return read_json(self.matrix / option / "summary.json")

    def optics(self, option: str) -> pd.DataFrame:
        return read_parquet(self.optics_dir / f"{option}.optics.parquet")

    def twiss(self, name: str) -> pd.DataFrame:
        return read_parquet(self.optics_dir / f"{name}.twiss.parquet")

    @cached_property
    def scoreboard(self) -> pd.DataFrame:
        return scoreboard(self.predictions)

    @cached_property
    def measured_optics(self) -> pd.DataFrame:
        return measured_optics(self.campaign, self.positions)

    @cached_property
    def measured_phase(self) -> pd.DataFrame:
        return measured_phase(self.campaign, self.positions)

    @cached_property
    def optics_summary(self) -> dict:
        return read_json(self.campaign.optics_dir / "summary.json")

    @cached_property
    def measured_dispersion(self) -> pd.DataFrame:
        return measured_dispersion(self.predictions, self.positions)


def read_json(path: Path) -> dict:
    """A JSON file, or an empty dict where the stage has not run."""
    return json.loads(path.read_text()) if path.exists() else {}


def read_parquet(path: Path) -> pd.DataFrame:
    """A parquet file, or an empty frame where the stage has not run."""
    if not path.exists():
        logger.warning("missing %s", path)
        return pd.DataFrame()
    return pd.read_parquet(path)


def knobs(path: Path, positions: dict[str, float]) -> pd.DataFrame:
    """``knobs.csv`` joined to the element ``s`` the sequence puts it at."""
    if not path.exists():
        return pd.DataFrame(columns=["element", "suffix", "s", "value", "uncertainty"])
    frame = pd.read_csv(path)
    lowered = {name.casefold(): s for name, s in positions.items()}
    rows = []
    for knob, value, uncertainty in frame.itertuples(index=False):
        element, _, suffix = knob.rpartition(".")
        s = lowered.get(element.casefold())
        if s is None:
            continue
        rows.append((element, f".{suffix}", float(s), float(value), float(uncertainty)))
    return pd.DataFrame(rows, columns=["element", "suffix", "s", "value", "uncertainty"])


def knob_statistics(frame: pd.DataFrame, suffix: str) -> dict[str, float] | None:
    """One family's fitted magnitudes and |value| / sigma, per group as fitted."""
    family = frame[frame["suffix"] == suffix]
    if family.empty:
        return None
    sigma = family["uncertainty"].abs()
    ratio = (family["value"].abs() / sigma).replace([np.inf, -np.inf], np.nan).dropna()
    # Method 1 reports no covariance (NaN sigma), so its significance is empty.
    if ratio.empty:
        ratio = pd.Series([float("nan")])
    return {
        "knobs": float(family["value"].round(12).nunique()),
        "magnets": float(len(family)),
        "rms": float((family["value"] ** 2).mean() ** 0.5),
        "max": float(family["value"].abs().max()),
        "sigma": float(sigma.median()),
        "median_significance": float(ratio.median()),
        "determined": float("nan") if ratio.isna().all() else float((ratio > 1.0).sum()),
    }


def scoreboard(predictions: Path) -> pd.DataFrame:
    """One row per option, indexed by option, with the ``*_rel`` residuals."""
    path = predictions / "scoreboard.csv"
    if not path.exists():
        logger.warning("missing %s", path)
        return pd.DataFrame()
    return pd.read_csv(path).set_index("option")


def measured_optics(campaign: Campaign, positions: dict[str, float]) -> pd.DataFrame:
    """The measured-optics table with each BPM's ``s`` from the model sequence."""
    frame = read_parquet(campaign.optics_dir / "measured.parquet")
    if frame.empty:
        return frame
    by_name = {name.upper(): s for name, s in positions.items()}
    frame = frame.assign(s=[by_name.get(str(n).upper(), np.nan) for n in frame.index])
    return frame.sort_values("s")


def measured_phase(campaign: Campaign, positions: dict[str, float]) -> pd.DataFrame:
    """The measured BPM-to-BPM phase-advance table, at the downstream BPM's ``s``."""
    frame = read_parquet(campaign.optics_dir / "measured_phase.parquet")
    if frame.empty:
        return frame
    by_name = {name.upper(): s for name, s in positions.items()}
    frame = frame.assign(s=[by_name.get(str(n).upper(), np.nan) for n in frame.index])
    return frame.sort_values("s")


def measured_dispersion(predictions: Path, positions: dict[str, float]) -> pd.DataFrame:
    """Measured ``d orbit / dpt`` at each BPM, with model ``s`` positions.

    The uncertainty comes straight from ``measured_error`` in the parquet --
    written by ``scripts/predict_loco.py`` from
    ``tmom_recon.physics.closed_orbit.measure_dispersion``, propagating the
    repeat-acquisition orbit scatter and the chroma pt uncertainty -- rather
    than refitted here from the handful of RF-steering points, which leaves
    too few degrees of freedom to be a meaningful residual estimate.
    """
    columns = ["plane", "bpm", "measured", "uncertainty", "s"]
    frame = read_parquet(predictions / "start-model.dispersion.parquet")
    if frame.empty:
        return pd.DataFrame(columns=columns)
    by_name = {name.upper(): s for name, s in positions.items()}
    frame = frame.rename(columns={"measured_error": "uncertainty"}).copy()
    frame["s"] = frame["bpm"].astype(str).str.upper().map(by_name)
    return frame.loc[~frame["s"].isna(), columns]


def benchmark(root: Path, campaigns) -> list[dict]:
    """The Method-1-against-Method-2 record per campaign, where one was written."""
    records = []
    for campaign in campaigns:
        record = read_json(root / f"{campaign.slug}.json")
        if record:
            # The record's own "campaign" is the slug; keep the object apart.
            records.append({**record, "campaign_object": campaign})
    return records
