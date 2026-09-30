"""Draw the cross-campaign comparison figures from ``results/cross_campaign/``.

Run ``analyse_cross_campaign.py`` first; nothing here reads per-campaign results.

    uv run python scripts/analyse_cross_campaign.py
    uv run python scripts/plot_cross_campaign.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from loco_common.campaign import INVERTED_PAGE_CAMPAIGNS, NORMAL_PAGE_CAMPAIGNS
from loco_common.case_names import DELTA_PAGE
from loco_common.fit_mode import fit_mode_by_slug
from scripts.analyse_cross_campaign import OUTPUT_ROOT
from scripts.report_cases import (
    LOCO_OPTICS_FITS,
    figure_beta_beat_summary,
    figure_benchmark_agreement,
    figure_benchmark_speed,
    figure_perturbation_effect,
    figure_perturbation_tunes,
    figure_scenario_knob_diffs,
    figure_scenario_tunes_chromas,
)

logger = logging.getLogger(__name__)


def _read_json(path: Path) -> object:
    return json.loads(path.read_text())


def _campaign_summaries(campaigns: tuple, summaries_by_slug: dict) -> list[tuple[object, dict]]:
    return [
        (campaign, summaries_by_slug[campaign.slug])
        for campaign in campaigns
        if summaries_by_slug.get(campaign.slug)
    ]


def plot_direction(direction: str, page_campaigns: tuple, analysis_root: Path, output: Path) -> None:
    """Every cross-campaign figure for one direction, in ``scenarios/<direction>`` (``<direction>`` is a campaign figures folder)."""
    root = analysis_root / direction
    scenario_output = output / "scenarios" / direction
    scenario_output.mkdir(parents=True, exist_ok=True)

    summaries_by_slug = _read_json(root / "scenario_optics_summaries.json")
    summaries = _campaign_summaries(page_campaigns, summaries_by_slug)
    beats_path = root / "scenario_optics_beat_along_s.parquet"
    beats = pd.read_parquet(beats_path) if beats_path.exists() else pd.DataFrame()
    # Older analysis directories lack these: no beating frame skips the along-s figures, no positions drops the BPM markers.
    positions_path = root / "element_positions.json"
    positions = _read_json(positions_path) if positions_path.exists() else {}
    figure_beta_beat_summary(summaries, beats, positions, scenario_output)
    figure_scenario_tunes_chromas(summaries, scenario_output)
    values_path = root / "scenario_optics_values.parquet"
    values = pd.read_parquet(values_path) if values_path.exists() else pd.DataFrame()
    # One folder per fit so same-named figures do not overwrite each other.
    for fit in LOCO_OPTICS_FITS:
        fit_output = scenario_output / fit[0]
        fit_output.mkdir(parents=True, exist_ok=True)
        figure_perturbation_effect(summaries, values, positions, fit_output, fit)
    figure_perturbation_tunes(summaries, scenario_output)
    records = _read_json(root / "benchmark.json")
    figure_benchmark_speed(records, scenario_output)
    figure_benchmark_agreement(records, scenario_output)

    baseline, *scenarios = page_campaigns
    for mode in (fit_mode_by_slug("single"), fit_mode_by_slug("multi")):
        for case_slug in DELTA_PAGE.cases:
            path = root / "scenario_knobs" / mode.slug / f"{case_slug}.parquet"
            if not path.exists():
                continue
            frame = pd.read_parquet(path)
            base = frame[frame["campaign"] == baseline.slug]
            # groupby() would sort alphabetically; keep ``scenarios`` order for OVERLAY_COLOURS.
            blocks = [
                (scenario, frame[frame["campaign"] == scenario.slug])
                for scenario in scenarios
                if (frame["campaign"] == scenario.slug).any()
            ]
            if base.empty or not blocks:
                continue
            diff_output = (
                scenario_output / "scenario-comparison" / mode.slug / case_slug
            )
            diff_output.mkdir(parents=True, exist_ok=True)
            figure_scenario_knob_diffs(mode, case_slug, baseline, base, blocks, diff_output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--output", type=Path, default=Path("docs/assets/figures"))
    parser.add_argument(
        "--direction", nargs="+", default=["normal", "inverted"],
        choices=["normal", "inverted"],
        help="Tune directions to draw; match it to analyse_cross_campaign.py.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    for direction, page_campaigns in (
        ("normal", NORMAL_PAGE_CAMPAIGNS),
        ("inverted", INVERTED_PAGE_CAMPAIGNS),
    ):
        if direction not in args.direction:
            continue
        plot_direction(direction, page_campaigns, args.analysis, args.output)
    logger.info("cross-campaign figures written under %s", args.output)


if __name__ == "__main__":
    main()
