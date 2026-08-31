"""Persist the cross-campaign comparison data the report figures are drawn from.

Analysis, not plotting: everything here reads what earlier pipeline stages
already wrote per campaign (``summary.json``, benchmark records, per-case
``knobs.csv``) and combines it across campaigns into tidy files under
``results/cross_campaign/``. ``scripts/plot_cross_campaign.py`` draws the
comparison figures from what is written here; nothing about a comparison is
recomputed by that script, and nothing here draws a figure -- so a later
analysis that wants the same combined data (a notebook, a different report)
reads these files directly instead of re-deriving them from every campaign's
raw results.

    uv run python scripts/analyse_cross_campaign.py
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
from loco_common.model import DEFAULT_SEQUENCE_FILE, build_model, model_element_positions
from scripts.plot_knobs import read_knobs
from scripts.measured_optics import model_optics
from scripts.report_cases import (
    LOCO_OPTICS_FITS,
    benchmark_records,
    loco_optics_values_along_s,
    optics_beat_along_s,
    optics_summary,
    optics_values_along_s,
    scenario_dispersion_beat,
)

logger = logging.getLogger(__name__)

OUTPUT_ROOT = Path("results/cross_campaign")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    logger.info("wrote %s", path)


def matched_model_bpms(campaign, summary: dict, sequence_file: Path) -> pd.DataFrame | None:
    """The BPM twiss of this campaign's lattice matched to its measured tune.

    Only the dispersion columns are new -- the matched model's beta and phase
    advance are already written beside the measurement by
    ``scripts/measured_optics.py`` -- but nothing stores its dispersion, so the
    match is re-run here. It is the same call that script makes, so the two
    cannot drift apart.
    """
    measured = summary.get("measured", {}).get("natural_tunes")
    if not measured:
        return None
    matched = model_optics(campaign, sequence_file, match_to=tuple(measured))
    return matched["bpms"]


def analyse_direction(
    direction: str, page_campaigns: tuple, positions: dict[str, float],
    benchmark_root: Path, sequence_file: Path, output_root: Path,
) -> None:
    """One direction's scenario campaigns: optics summaries, dispersion, the
    benchmark records, and every case's raw per-magnet fit, campaign by campaign.

    Everything is per-direction because every page that reads it tabs between
    exactly these campaigns; a single global set drawn from the first normal and
    inverted campaigns would put figures on a page that its own tabs never show.
    """
    root = output_root / direction
    summaries = {c.slug: optics_summary(c) for c in page_campaigns}
    _write_json(root / "scenario_optics_summaries.json", summaries)
    dispersion = {c.slug: scenario_dispersion_beat(c) for c in page_campaigns}
    _write_json(root / "scenario_dispersion_beat.json", dispersion)
    _write_json(root / "benchmark.json", benchmark_records(benchmark_root, page_campaigns))

    # The per-BPM beating the two along-s comparison figures draw; the rms in
    # the two files above is what is left of it.
    beats = pd.concat(
        [optics_beat_along_s(c, positions) for c in page_campaigns], ignore_index=True
    )
    beats_path = root / "scenario_optics_beat_along_s.parquet"
    beats_path.parent.mkdir(parents=True, exist_ok=True)
    beats.to_parquet(beats_path)
    logger.info("wrote %s", beats_path)

    # The raw per-BPM values the perturbation-effect figures difference one
    # campaign against another with: the measurement, the tune-matched model,
    # and the LOCO-fitted lattice. One tune match per campaign, for the matched
    # model's dispersion alone; everything else is already on disk.
    blocks = []
    for c in page_campaigns:
        measured = optics_values_along_s(
            c, positions, matched_model_bpms(c, summaries.get(c.slug, {}), sequence_file)
        )
        blocks.append(measured)
        # One block per entry in LOCO_OPTICS_FITS: the perturbation figures
        # are drawn once per fit, on their own page, and both have to be here
        # for the plotting script to draw either without a fit of its own.
        for slug, case_slug, _ in LOCO_OPTICS_FITS:
            blocks.append(loco_optics_values_along_s(
                c, set(measured["name"]), case_slug=case_slug,
                source=f"loco_{slug}",
            ))
    values = pd.concat(blocks, ignore_index=True)
    values_path = root / "scenario_optics_values.parquet"
    values.to_parquet(values_path)
    logger.info("wrote %s", values_path)
    # So the along-s figures can mark the BPMs without plot_cross_campaign.py
    # having to build the model, which is the one thing that script does not do.
    _write_json(root / "element_positions.json", positions)

    baseline, *scenarios = page_campaigns
    for mode in (fit_mode_by_slug("single"), fit_mode_by_slug("multi")):
        for case_slug in DELTA_PAGE.cases:
            base_path = mode.results_root(baseline) / case_slug / "knobs.csv"
            if not base_path.exists():
                logger.info(
                    "%s/%s/%s: no baseline knobs, skipping the scenario diff inputs",
                    direction, mode.slug, case_slug,
                )
                continue
            blocks = [read_knobs(base_path, positions).assign(campaign=baseline.slug)]
            for scenario in scenarios:
                path = mode.results_root(scenario) / case_slug / "knobs.csv"
                if not path.exists():
                    continue
                blocks.append(read_knobs(path, positions).assign(campaign=scenario.slug))
            if len(blocks) < 2:
                continue
            frame = pd.concat(blocks, ignore_index=True)
            out = root / "scenario_knobs" / mode.slug / f"{case_slug}.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(out)
            logger.info("wrote %s", out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=Path("results/benchmark"),
                        help="Where scripts/benchmark_methods.py wrote its records.")
    parser.add_argument("--sequence-file", type=Path, default=DEFAULT_SEQUENCE_FILE)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    parser.add_argument(
        "--direction", nargs="+", default=["normal", "inverted"],
        choices=["normal", "inverted"],
        help="Tune directions to analyse. Narrow it so a refresh of one "
             "direction does not redo the other from whatever state its "
             "results happen to be in.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    for direction, page_campaigns in (
        ("normal", NORMAL_PAGE_CAMPAIGNS),
        ("inverted", INVERTED_PAGE_CAMPAIGNS),
    ):
        if direction not in args.direction:
            continue
        positions = model_element_positions(
            build_model(sequence_file=args.sequence_file, campaign=page_campaigns[0])
        )
        analyse_direction(
            direction, page_campaigns, positions, args.benchmark,
            args.sequence_file, args.output,
        )


if __name__ == "__main__":
    main()
