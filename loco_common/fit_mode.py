"""Momentum fit layouts shared by every campaign tool."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse
    from pathlib import Path

from loco_common.campaign import REPO_ROOT, Campaign


@dataclass(frozen=True)
class FitMode:
    """One fitted data scope and the directories derived from it."""

    slug: str
    label: str
    rf_offsets: tuple[float, ...]
    batch_momenta: bool

    def results_root(self, campaign: Campaign) -> Path:
        if self.slug == "single":
            return campaign.results_root
        suffix = "multi" if self.slug == "multi" else self.slug
        name = f"matrix_{suffix}" if campaign.slug == "normal" else f"matrix_{campaign.slug}_{suffix}"
        return REPO_ROOT / "results" / name

    def figures_dir(self, campaign: Campaign, root: Path) -> Path:
        base = campaign.figures_dir(root)
        return base if self.slug == "single" else base / self.slug

    def rf_offsets_for(self, campaign: Campaign) -> tuple[float, ...]:
        """This mode's RF offsets, narrowed to what ``campaign``'s scan has.

        ``self.rf_offsets`` is the layout for a campaign with the full
        five-point scan. A campaign with a coarser scan (e.g. -2/0/+2 mm
        only) has no untrimmed acquisition at the missing offsets, so
        MULTI and THREE both fall back to whatever ``available_rf_offsets``
        reports instead of the fixed list.
        """
        if self.slug == "single":
            return self.rf_offsets
        from loco_common.measured_response import available_rf_offsets

        available = available_rf_offsets(campaign)
        if self.slug == "multi":
            return tuple(available)
        negative = max((o for o in available if o < 0), default=None)
        positive = min((o for o in available if o > 0), default=None)
        return tuple(sorted(o for o in (negative, 0.0, positive) if o is not None))


SINGLE = FitMode("single", "Single momentum", (0.0,), batch_momenta=False)
THREE = FitMode("three", "Three momentum", (-1.0, 0.0, 1.0), batch_momenta=True)
MULTI = FitMode(
    "multi", "Multi momentum", (-2.0, -1.0, 0.0, 1.0, 2.0), batch_momenta=True
)
FIT_MODES = {mode.slug: mode for mode in (SINGLE, THREE, MULTI)}


def fit_mode_by_slug(slug: str) -> FitMode:
    try:
        return FIT_MODES[slug]
    except KeyError as error:
        raise ValueError(f"Unknown momentum mode {slug!r}; expected {sorted(FIT_MODES)}") from error


def add_fit_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--momentum-mode",
        choices=sorted(FIT_MODES),
        default="single",
        help="Fit/result scope: nominal only, the central three, or all five momenta.",
    )


def result_is_valid(directory: Path) -> bool:
    """Whether a Method-2 directory contains an accepted optimisation step."""
    summary = directory / "summary.json"
    if not summary.exists():
        return False
    return json.loads(summary.read_text()).get("status", "complete") == "complete"
