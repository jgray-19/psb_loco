"""The report generator: loaders against the results on disk, and page rendering."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from loco_common.campaign import campaign_by_slug
from loco_common.fit_mode import fit_mode_by_slug
from loco_report import data

REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = "inverted_second"
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
