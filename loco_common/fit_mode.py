"""Momentum fit layouts shared by every campaign tool.

``single`` is not reported: its absolute fits warm-start the ``multi`` ones."""

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
    batch_momenta: bool

    def results_root(self, campaign: Campaign) -> Path:
        if self.slug == "single":
            return campaign.results_root
        return REPO_ROOT / "results" / f"matrix_{campaign.slug}_{self.slug}"

    def figures_dir(self, campaign: Campaign, root: Path) -> Path:
        base = campaign.figures_dir(root)
        return base if self.slug == "single" else base / self.slug

    def rf_offsets_for(self, campaign: Campaign) -> tuple[float, ...]:
        """Nominal RF only, or every offset the scan visited."""
        return campaign.rf_offsets if self.slug == "multi" else (0.0,)


SINGLE = FitMode("single", "Single momentum", batch_momenta=False)
MULTI = FitMode("multi", "Multi momentum", batch_momenta=True)
FIT_MODES = {mode.slug: mode for mode in (SINGLE, MULTI)}


def fit_mode_by_slug(slug: str) -> FitMode:
    try:
        return FIT_MODES[slug]
    except KeyError as error:
        raise ValueError(f"Unknown momentum mode {slug!r}; expected {sorted(FIT_MODES)}") from error


def add_fit_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--momentum-mode",
        choices=sorted(FIT_MODES),
        default="multi",
        help="Fit/result scope: nominal RF only (a warm start, not reported) or every RF offset.",
    )


def result_is_valid(directory: Path) -> bool:
    """Whether a POCO directory contains an accepted optimisation step."""
    summary = directory / "summary.json"
    if not summary.exists():
        return False
    return json.loads(summary.read_text()).get("status", "complete") == "complete"
