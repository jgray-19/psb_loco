"""The two machine configurations stay separated, all the way down.

The failure this guards against is quiet and expensive: a fit that reads the
inverted-tunes acquisitions against the normal-tunes model, or writes over the
first campaign's parquet cache with the second's orbits. Nothing about either
would raise -- the fit would converge and the numbers would be wrong -- so the
separation is asserted rather than inspected.
"""

from __future__ import annotations

import pytest

from loco_common.campaign import (
    CAMPAIGNS,
    INVERTED,
    INVERTED_DOUBLE,
    INVERTED_SECOND,
    NORMAL,
    NORMAL_SECOND,
    campaign_by_slug,
)


def test_every_campaign_has_its_own_acquisitions_and_log():
    logs = {campaign.scan_log for campaign in CAMPAIGNS.values()}
    folders = {campaign.measurements_path for campaign in CAMPAIGNS.values()}
    assert len(logs) == len(CAMPAIGNS)
    assert len(folders) == len(CAMPAIGNS)


def test_caches_do_not_collide():
    """One cache file per campaign, and the first keeps the name it has on disk."""
    names = {
        campaign.slug: campaign.cache_file("scan_points.parquet")
        for campaign in CAMPAIGNS.values()
    }
    assert len(set(names.values())) == len(names)
    assert NORMAL.cache_file("scan_points.parquet").name == "scan_points.parquet"


def test_results_roots_are_distinct():
    roots = {campaign.results_root for campaign in CAMPAIGNS.values()}
    assert len(roots) == len(CAMPAIGNS)
    assert NORMAL.results_root.name == "matrix"


def test_momentum_modes_have_separate_results_and_figure_roots(tmp_path):
    from loco_common.fit_mode import MULTI, SINGLE

    assert SINGLE.results_root(NORMAL) == NORMAL.results_root
    assert MULTI.results_root(NORMAL).name == "matrix_multi"
    assert MULTI.results_root(INVERTED).name == "matrix_inverted_multi"
    assert SINGLE.figures_dir(INVERTED, tmp_path) == tmp_path / "inverted"
    assert MULTI.figures_dir(INVERTED, tmp_path) == tmp_path / "inverted" / "multi"


def test_inverted_double_is_the_same_machine_as_inverted():
    """Same quads, same optics -- a step-size cross-check, not a third lattice."""
    assert INVERTED_DOUBLE.quad_settings == INVERTED.quad_settings
    assert INVERTED_DOUBLE.optics is INVERTED.optics
    assert INVERTED_DOUBLE.optics_dir == INVERTED.optics_dir
    assert INVERTED_DOUBLE.delta_k != INVERTED.delta_k


def test_the_two_lattices_really_are_different():
    for knob in ("kbrqf", "kbrqd"):
        assert NORMAL.quad_settings[knob] != INVERTED.quad_settings[knob]
    assert NORMAL.optics.chroma_file != INVERTED.optics.chroma_file


def test_campaign_lookup_accepts_the_cli_spelling():
    assert campaign_by_slug("inverted-double") is INVERTED_DOUBLE
    with pytest.raises(ValueError, match="Unknown campaign"):
        campaign_by_slug("sideways")


def test_build_model_takes_its_circuits_from_the_campaign(monkeypatch):
    """No tune match, and the campaign's own currents -- the whole point."""
    from loco_common import model as model_module

    monkeypatch.setattr(model_module, "resolve_sequence_file", lambda *_, **__: "seq")
    monkeypatch.setattr(model_module, "matched_tune_knobs", lambda *_, **__: {"kbrqf": 0.7, "kbrqd": -0.7})
    monkeypatch.setattr(model_module, "psb_orbit_corrector_strengths", lambda *_, **__: {})

    # Live campaigns, not NORMAL/INVERTED: the retired pair carries no
    # machine_config, which build_model requires to resolve its knobs.
    for campaign in (NORMAL_SECOND, INVERTED_SECOND):
        built = model_module.build_model(sequence_file="seq", campaign=campaign)
        assert built.tune_knobs == campaign.quad_settings


def test_page_case_commands_match_the_matrix_script():
    """The nine page cases map to the flags ``run_loco_matrix.sh`` would use."""
    from scripts.run_campaign_fits import command

    argv = command(
        "xy__k1+b+dy+t__bpm-family", "inverted_second", "seq",
        __import__("pathlib").Path("out"),
    )
    assert "--absolute-planes" in argv and argv[argv.index("--absolute-planes") + 1 : ][:2] == ["x", "y"]
    assert "--optimise-bends" in argv
    assert "--optimise-quad-dy" in argv
    assert "--optimise-quad-tilt" in argv
    assert "--no-optimise-quadrupoles" not in argv
    assert "--group-quadrupoles-by-cell" in argv

    frozen = command("none__t__none", "normal_second", "seq", __import__("pathlib").Path("out"))
    assert "--no-optimise-quadrupoles" in frozen
    assert "--group-quadrupoles-by-cell" not in frozen


def _offsets_in(argv: list[str]) -> list[str]:
    """The values after ``--rf-offsets``, up to the next flag."""
    rest = argv[argv.index("--rf-offsets") + 1 :]
    return [value for value in rest[: next(
        (i for i, v in enumerate(rest) if v.startswith("--") and not v[2:3].isdigit()),
        len(rest),
    )]]


def test_multi_momentum_command_uses_every_rf_offset_and_batches():
    """Every offset the campaign's own scan has -- not a fixed five-point list.

    No live campaign runs the 2026-08-21 five-point scan; the 28th/29th/30th
    all step -2/0/+2, and ``FitMode.rf_offsets_for`` narrows to what is there.
    Asserting the fixed list would only pin the retired scan's layout.
    """
    from loco_common.fit_mode import MULTI
    from scripts.run_campaign_fits import command

    expected = MULTI.rf_offsets_for(INVERTED_SECOND)
    argv = command(
        "xy__k1+b+dy+t__bpm-family",
        "inverted_second",
        "seq",
        __import__("pathlib").Path("out"),
        "multi",
    )
    assert _offsets_in(argv) == [f"{value:g}" for value in expected]
    assert 0.0 in expected and len(expected) > 1
    assert "--batch-momenta" in argv
    assert argv[argv.index("--momentum-source") + 1] == "chroma"
    # Warm-started from the nominal-momentum fit, not from THREE: PREVIOUS_MODE
    # sends both staged modes back to SINGLE, which is what the method page
    # describes.
    assert argv[argv.index("--initial-knobs") + 1].endswith(
        "results/matrix_inverted_second/xy__k1+b+dy+t__bpm-family/knobs.csv"
    )


def test_three_momentum_command_uses_central_offsets_and_dispersion_pt():
    """The innermost non-zero offset either side, whatever the scan stepped."""
    from loco_common.fit_mode import THREE
    from scripts.run_campaign_fits import command

    expected = THREE.rf_offsets_for(INVERTED_SECOND)
    argv = command(
        "xy__k1+b+dy+t__bpm-family",
        "inverted_second",
        "seq",
        __import__("pathlib").Path("out"),
        "three",
    )
    assert _offsets_in(argv) == [f"{value:g}" for value in expected]
    assert len(expected) <= 3 and 0.0 in expected
    assert argv[argv.index("--momentum-source") + 1] == "chroma"
    assert "--batch-momenta" in argv
    assert argv[argv.index("--initial-knobs") + 1].endswith(
        "results/matrix_inverted_second/xy__k1+b+dy+t__bpm-family/knobs.csv"
    )


def test_both_staged_modes_warm_start_from_the_nominal_momentum_fit():
    from loco_common.fit_mode import MULTI, SINGLE, THREE
    from scripts.run_campaign_fits import PREVIOUS_MODE

    assert PREVIOUS_MODE[MULTI.slug] is SINGLE
    assert PREVIOUS_MODE[THREE.slug] is SINGLE


def test_rf_offset_narrowing_keeps_its_layout_on_a_five_point_scan(monkeypatch):
    """The layout the two tests above can no longer see, on a synthetic scan.

    MULTI takes everything; THREE takes zero plus the innermost offset either
    side. Pinned here rather than against a campaign so retiring the last
    five-point scan cannot quietly delete the coverage.
    """
    from loco_common import fit_mode as fit_mode_module
    from loco_common import measured_response
    from loco_common.fit_mode import MULTI, THREE

    monkeypatch.setattr(
        measured_response, "available_rf_offsets",
        lambda _campaign: (-2.0, -1.0, 0.0, 1.0, 2.0),
    )
    assert MULTI.rf_offsets_for(NORMAL_SECOND) == (-2.0, -1.0, 0.0, 1.0, 2.0)
    assert THREE.rf_offsets_for(NORMAL_SECOND) == (-1.0, 0.0, 1.0)
    assert fit_mode_module.SINGLE.rf_offsets_for(NORMAL_SECOND) == (0.0,)


def test_the_retired_scans_stay_out_of_the_registry():
    """NORMAL/INVERTED are ``replace()`` bases and history, not fittable.

    They carry no ``machine_config``, so anything that reaches build_model with
    one is a bug; keeping them unlisted is what makes that fail loudly.
    """
    assert NORMAL.slug not in CAMPAIGNS
    assert INVERTED.slug not in CAMPAIGNS
    assert NORMAL.machine_config is None
    assert INVERTED.machine_config is None
    for slug in (NORMAL.slug, INVERTED.slug):
        with pytest.raises(ValueError, match="Unknown campaign"):
            campaign_by_slug(slug)


def test_every_registered_campaign_namespaces_its_own_products():
    """No live campaign relies on the retired ``normal`` unprefixed paths."""
    for campaign in CAMPAIGNS.values():
        assert campaign.slug in campaign.results_root.name
        assert campaign.cache_file("scan_points.parquet").name.startswith(campaign.slug)


def test_single_momentum_command_keeps_the_nominal_only_default():
    from scripts.run_campaign_fits import command

    argv = command(
        "none__k1__bpm-family", "normal_second", "seq", __import__("pathlib").Path("out"),
    )
    assert "--rf-offsets" not in argv
    assert "--batch-momenta" not in argv
