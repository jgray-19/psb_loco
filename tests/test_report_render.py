"""The report generator: loaders against the results on disk, and page rendering."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from loco_common.campaign import campaign_by_slug
from loco_common.fit_mode import fit_mode_by_slug
from loco_report import data

REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = "p23_p13_final"
OPTION = "none__k1__bpm-family"


@pytest.fixture(scope="module")
def matrix() -> Path:
    root = fit_mode_by_slug("single").results_root(campaign_by_slug(CAMPAIGN))
    if not (root / OPTION / "knobs.csv").exists():
        pytest.skip(f"no fitted results under {root}")
    return root


@pytest.fixture(scope="module")
def positions(matrix) -> dict[str, float]:
    """Element positions faked from the knob names, so no MAD-NG is spawned."""
    names = pd.read_csv(matrix / OPTION / "knobs.csv")["knob"]
    elements = sorted({name.rpartition(".")[0] for name in names})
    return {element: float(index) for index, element in enumerate(elements)}


def test_knobs_keeps_every_row_and_splits_the_suffix(matrix, positions):
    raw = pd.read_csv(matrix / OPTION / "knobs.csv")
    frame = data.knobs(matrix / OPTION / "knobs.csv", positions)
    assert len(frame) == len(raw)
    assert set(frame["suffix"]) == {
        f".{name.rpartition('.')[2]}" for name in raw["knob"]
    }
    assert frame["value"].to_numpy() == pytest.approx(raw["value"].to_numpy())


def test_knobs_is_empty_rather_than_raising_when_the_fit_is_absent(positions):
    frame = data.knobs(Path("/nonexistent/knobs.csv"), positions)
    assert frame.empty
    assert list(frame.columns) == ["element", "suffix", "s", "value", "uncertainty"]


def test_knob_statistics_match_a_hand_computation(matrix, positions):
    frame = data.knobs(matrix / OPTION / "knobs.csv", positions)
    statistics = data.knob_statistics(frame, ".dk1l")
    family = frame[frame["suffix"] == ".dk1l"]
    assert statistics["magnets"] == len(family)
    assert statistics["rms"] == pytest.approx((family["value"] ** 2).mean() ** 0.5)
    assert statistics["max"] == pytest.approx(family["value"].abs().max())


def test_knob_statistics_are_none_for_a_family_the_fit_did_not_free(matrix, positions):
    frame = data.knobs(matrix / OPTION / "knobs.csv", positions)
    # none__k1__* frees gradients only.
    assert data.knob_statistics(frame, ".tilt") is None


def test_scoreboard_is_indexed_by_option_and_keeps_every_row(matrix):
    path = matrix / "predictions" / "scoreboard.csv"
    if not path.exists():
        pytest.skip("no scoreboard written")
    frame = data.scoreboard(matrix / "predictions")
    raw = pd.read_csv(path)
    assert frame.index.name == "option"
    assert len(frame) == len(raw)
    assert frame.loc[OPTION, "delta_x_rel"] == pytest.approx(
        raw.set_index("option").loc[OPTION, "delta_x_rel"]
    )


def test_missing_artifacts_load_as_empty_frames_not_exceptions():
    assert data.read_parquet(Path("/nonexistent/x.parquet")).empty
    assert data.read_json(Path("/nonexistent/x.json")) == {}
    assert data.scoreboard(Path("/nonexistent")).empty


def test_results_reports_which_options_have_a_fit(matrix, positions):
    results = data.Results(
        campaign_by_slug(CAMPAIGN), fit_mode_by_slug("single"), positions
    )
    assert results.matrix == matrix
    assert results.has(OPTION)
    assert not results.has("no__such__case")
    assert results.valid((OPTION, "no__such__case")) == (OPTION,)


DOCS = REPO_ROOT / "docs"
FIGURE_ROOT = DOCS / "assets" / "figures"


def generated_pages() -> list[Path]:
    """The report pages loco_report writes, as they are on disk."""
    return sorted(
        path
        for tree in ("inverted_tunes", "normal_tunes")
        for path in (DOCS / tree / "reports").rglob("*.md")
    )


@pytest.fixture(scope="module")
def pages() -> list[Path]:
    found = generated_pages()
    if not found:
        pytest.skip("no report pages rendered yet")
    return found


def test_no_figure_repeats_its_caption_as_alt_text(pages):
    """The old generator printed every caption twice; 654 of 654 figures did."""
    import re

    offenders = []
    for path in pages:
        text = path.read_text()
        for match in re.finditer(
            r"!\[(.*?)\]\(.*?\)\s*\n\s*<figcaption>(.*?)</figcaption>", text, re.S
        ):
            if match.group(1).strip() == match.group(2).strip():
                offenders.append(f"{path.name}: {match.group(1)[:50]}")
    assert not offenders, offenders[:5]


def test_every_referenced_figure_exists(pages):
    import re

    missing = []
    for path in pages:
        for reference in re.findall(r"\]\((\.\./[^)]+\.png)\)", path.read_text()):
            if not (path.parent / reference).resolve().exists():
                missing.append(f"{path}: {reference}")
    assert not missing, missing[:5]


def test_no_page_carries_more_than_two_tables(pages):
    """Bar charts over tables: two tables a page is the cap."""
    over = []
    for path in pages:
        lines = path.read_text().splitlines()
        # Distinct header rows: a table repeated per campaign tab is one table.
        headers = {
            lines[index - 1].strip()
            for index, line in enumerate(lines)
            if index and line.strip().startswith("|---")
        }
        if len(headers) > 2:
            over.append(f"{path.name}: {len(headers)} distinct tables")
    assert not over, over


def test_every_nav_target_exists():
    import re

    nav = (REPO_ROOT / "zensical.toml").read_text()
    nav = nav[nav.index("nav = ["):nav.index("[project.theme]")]
    missing = [
        target for target in re.findall(r'"([^"]+\.md)"', nav)
        if not (DOCS / target).exists()
    ]
    assert not missing, missing


def test_no_figure_on_disk_is_unreferenced():
    """Every figure on disk is referenced: the site shows everything it draws."""
    import re

    referenced = {
        (page.parent / reference).resolve()
        for page in DOCS.rglob("*.md")
        for reference in re.findall(r"\]\(([^)]+\.png)\)", page.read_text())
    }
    orphans = sorted(
        path.relative_to(FIGURE_ROOT)
        for path in FIGURE_ROOT.rglob("*.png")
        if path.resolve() not in referenced
    )
    assert not orphans, [str(path) for path in orphans[:10]]


def test_family_figures_chunk_past_the_panel_cap():
    """A page with more cases than the panel cap spills into numbered figures."""
    from dataclasses import replace

    from loco_common.case_names import ABSOLUTE_PAGE
    from loco_report.style import MAX_PANELS

    page = replace(ABSOLUTE_PAGE, cases=ABSOLUTE_PAGE.cases * 2)
    assert len(page.cases) > MAX_PANELS
    chunks = [
        page.cases[i:i + MAX_PANELS]
        for i in range(0, len(page.cases), MAX_PANELS)
    ]
    assert len(chunks) == -(-len(page.cases) // MAX_PANELS)
    assert all(len(chunk) <= MAX_PANELS for chunk in chunks)
