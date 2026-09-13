"""Draw every figure and render every page. The only entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

from loco_common.campaign import (
    INVERTED_PAGE_CAMPAIGNS,
    NORMAL_PAGE_CAMPAIGNS,
    Campaign,
)
from loco_common.case_names import PLANES_PHRASE
from loco_common.fit_mode import FitMode, fit_mode_by_slug
from loco_common.model import (
    DEFAULT_SEQUENCE_FILE,
    build_model,
    model_element_positions,
)
from loco_report import figures, render, studies
from loco_report.data import Results
from loco_report.pages import PAGE_SPECS, PageSpec
from loco_report.style import FAMILIES

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
FIGURE_ROOT = DOCS / "assets" / "figures"
SCENARIO_ROOT = FIGURE_ROOT / "scenarios"
BENCHMARK_ROOT = REPO_ROOT / "results" / "benchmark"

DIRECTIONS = {
    "inverted": INVERTED_PAGE_CAMPAIGNS,
    "normal": NORMAL_PAGE_CAMPAIGNS,
}
MODES = ("single", "multi")

#: Method 1 fits the nominal-RF response matrix and has no multi-momentum form.
SINGLE_ONLY = {"method1"}


def draw(results: Results, spec: PageSpec, output: Path) -> list[Path]:
    """Every figure one page shows for one (campaign, momentum mode)."""
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob(f"{spec.slug}_*.png"):
        stale.unlink()
    # Only the cases that produced a usable fit reach a figure.
    page = replace(spec.page, cases=results.valid(spec.page.cases))
    written: list[Path] = []
    for suffix in FAMILIES:
        written += figures.family_by_s(results, page, suffix, output)
    for suffix in (".dk1l", ".tilt", ".dk0sl", ".dk1sl"):
        written += figures.family_significance(results, page, suffix, output)
    written += figures.optics(results, page, output)
    written += figures.phase_advance(results, page, output)
    written += figures.case_tunes(results, page, output)
    written += figures.case_chromaticity(results, page, output)
    written += figures.residuals(results, page, output)
    written += figures.scores(results, page, output)
    return written


def figures_for(campaign: Campaign, mode: FitMode, spec: PageSpec) -> Path:
    return mode.figures_dir(campaign, FIGURE_ROOT) / spec.slug


def render_page(spec: PageSpec, campaigns, mode: FitMode, destination: Path,
                positions: dict[str, float]) -> str:
    """One page, tabbed over the campaigns, showing only figures that exist."""
    relative = render.prefix(FIGURE_ROOT, destination)
    blocks: list[str] = []
    for section in spec.sections:
        tabs = {}
        if section.table:
            blocks += [render.heading(section.heading), render.tabbed({
                campaign.label: getattr(render, section.table)(
                    Results(campaign, mode, positions), spec.page)
                for campaign in campaigns
            })]
            continue
        for campaign in campaigns:
            directory = figures_for(campaign, mode, spec)
            found = [
                render.figure(
                    str((directory / f"{spec.slug}_{item.stem}.png").relative_to(FIGURE_ROOT)),
                    item.alt, item.caption, relative,
                )
                for item in section.figures
                if (directory / f"{spec.slug}_{item.stem}.png").exists()
            ]
            if found:
                tabs[campaign.label] = "\n\n".join(found)
        if tabs:
            blocks += [render.heading(section.heading), render.tabbed(tabs)]
    statement = (
        f"PSB ring 3 · {mode.label.lower()} · {_planes(spec)} · "
        f"{len(campaigns)} machine configurations as tabs."
    )
    return render.page(spec.title, statement, blocks)


def cached_positions(campaign: Campaign, mode: FitMode) -> dict[str, float]:
    """Element positions from the cached start-model twiss, so no MAD-NG run."""
    import pandas as pd

    path = mode.results_root(campaign) / "optics" / "start-model.twiss.parquet"
    if not path.exists():
        return {}
    return {str(name): float(s) for name, s in pd.read_parquet(path)["s"].items()}


def specs_for(mode: FitMode, specs: list[PageSpec]) -> list[PageSpec]:
    """The pages this momentum mode has fits for."""
    if mode.slug == "single":
        return specs
    return [spec for spec in specs if spec.slug not in SINGLE_ONLY]


def _planes(spec: PageSpec) -> str:
    """The page's orbit-matching mode in words, or a note that it mixes them."""
    return PLANES_PHRASE.get(spec.page.planes, "mixed orbit-matching modes")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=sorted(DIRECTIONS), required=True)
    parser.add_argument("--momentum-mode", choices=MODES, default=None,
                        help="Default: every mode.")
    parser.add_argument("--page", nargs="+", default=None,
                        help="Page slugs to build. Default: every page.")
    parser.add_argument("--figures-only", action="store_true")
    parser.add_argument("--pages-only", action="store_true")
    parser.add_argument("--sequence-file", type=Path, default=DEFAULT_SEQUENCE_FILE)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    campaigns = DIRECTIONS[args.direction]
    modes = [fit_mode_by_slug(args.momentum_mode)] if args.momentum_mode else [
        fit_mode_by_slug(slug) for slug in MODES
    ]
    specs = [spec for spec in PAGE_SPECS
             if args.page is None or spec.slug in args.page]

    try:
        positions = cached_positions(campaigns[0], modes[0])
        if not args.pages_only:
            positions = model_element_positions(
                build_model(sequence_file=args.sequence_file, campaign=campaigns[0])
            )
            for campaign in campaigns:
                for mode in modes:
                    results = Results(campaign, mode, positions)
                    if mode is modes[0]:
                        figures.measured_optics(
                            results, campaign.figures_dir(FIGURE_ROOT))
                    for spec in specs_for(mode, specs):
                        written = draw(results, spec, figures_for(campaign, mode, spec))
                        logger.info("%s %s %s: %d figures",
                                    campaign.slug, mode.slug, spec.slug, len(written))
        if not args.figures_only:
            for mode in modes:
                for spec in specs_for(mode, specs):
                    destination = page_path(args.direction, mode, spec)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(render_page(spec, campaigns, mode, destination, positions))
                    logger.info("wrote %s", destination)
            write_studies(args.direction, campaigns, modes)
            method = DOCS / "method.md"
            method.write_text(studies.render_method_page(
                [(label, DIRECTIONS[key]) for key, label in
                 (("inverted", "Inverted tunes"), ("normal", "Normal tunes"))]))
            logger.info("wrote %s", method)
            index = DOCS / f"{args.direction}_tunes" / "reports" / "index.md"
            index.write_text(render_index(campaigns, modes, specs, positions))
            logger.info("wrote %s", index)
    except Exception:
        logger.exception("report generation failed")
        return 1
    return 0



def render_index(campaigns, modes, specs, positions) -> str:
    """This tree's grid: which fits exist, per page, mode and campaign."""
    blocks: list[str] = []
    for mode in modes:
        rows = []
        for spec in specs_for(mode, specs):
            page_file = page_path_name(mode, spec)
            for slug in spec.page.cases:
                found = [
                    campaign.label for campaign in campaigns
                    if Results(campaign, mode, positions).has(slug)
                ]
                rows.append([
                    f"[{spec.title}]({page_file})",
                    spec.page.label(slug),
                    f"{len(found)} of {len(campaigns)}",
                ])
        if rows:
            blocks += [
                render.heading(mode.label),
                render.table(["page", "fitted option", "configurations with a fit"], rows),
            ]
    statement = (
        f"Every fit on this working point. {len(campaigns)} machine configurations, "
        f"shown as tabs on each page: "
        + ", ".join(campaign.label for campaign in campaigns) + "."
    )
    return render.page("Results", statement, blocks)


def page_path_name(mode: FitMode, spec: PageSpec) -> str:
    part = "" if mode.slug == "single" else f"{mode.slug}/"
    return f"{part}{spec.slug}.md"


def write_studies(direction: str, campaigns, modes) -> None:
    """The three pages that are not per-case."""
    tree = DOCS / f"{direction}_tunes"
    scenario_root = SCENARIO_ROOT / direction
    targets = (
        (tree / "studies" / "measured-optics.md",
         lambda path: studies.render_optics_page(
             campaigns, FIGURE_ROOT, scenario_root, path)),
        (tree / "reports" / "benchmark.md",
         lambda path: studies.render_benchmark_page(
             campaigns, BENCHMARK_ROOT, scenario_root, path)),
        (tree / "reports" / "scenarios.md",
         lambda path: studies.render_scenario_page(
             campaigns, scenario_root, modes, path)),
    )
    for path, build in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build(path))
        logger.info("wrote %s", path)


def page_path(direction: str, mode: FitMode, spec: PageSpec) -> Path:
    return DOCS / f"{direction}_tunes" / "reports" / page_path_name(mode, spec)


if __name__ == "__main__":
    sys.exit(main())
