"""The campaigns are exactly psb_md's, and each keeps its products apart (no cross-reading of acquisitions or caches)."""

from __future__ import annotations

from pathlib import Path

import pytest
from psb_md.acd_config import psb_orbit_corrector_strengths
from psb_md.defaults import CAMPAIGNS as PSB_MD_CAMPAIGNS

from loco_common.campaign import (
    CAMPAIGNS,
    P17_P23_FINAL,
    P23_P13_FINAL,
    P23_P13_FINAL_QDE14,
    campaign_by_slug,
)


def test_the_campaigns_are_exactly_psb_mds():
    configs = [campaign.machine_config for campaign in CAMPAIGNS.values()]
    assert len(configs) == len(set(configs)) == len(PSB_MD_CAMPAIGNS)
    assert set(configs) == set(PSB_MD_CAMPAIGNS)


def test_every_campaign_reads_its_own_scan_logs():
    """One log per RF offset, beside the campaign's own AC-dipole folders."""
    for campaign in CAMPAIGNS.values():
        logs = campaign.scan_logs
        assert tuple(sorted(logs)) == campaign.rf_offsets == (-2.0, 0.0, 2.0)
        assert {log.parent.parent for log in logs.values()} == {campaign.loco_dir}
    folders = {campaign.measurements_path for campaign in CAMPAIGNS.values()}
    assert len(folders) == len(CAMPAIGNS)


def test_caches_results_and_figures_do_not_collide(tmp_path):
    from loco_common.fit_mode import MULTI, SINGLE

    for campaign in CAMPAIGNS.values():
        assert campaign.cache_file("scan_points.parquet").name.startswith(campaign.slug)
        assert SINGLE.results_root(campaign) == campaign.results_root
        assert MULTI.results_root(campaign).name == f"matrix_{campaign.slug}_multi"
        assert MULTI.figures_dir(campaign, tmp_path) == tmp_path / campaign.slug / "multi"
    roots = {campaign.results_root for campaign in CAMPAIGNS.values()}
    assert len(roots) == len(CAMPAIGNS)


def test_an_error_campaign_starts_from_the_unperturbed_circuits():
    """LOCO has to recover the mis-trim, so the model is never handed it."""
    assert P23_P13_FINAL_QDE14.quad_settings == P23_P13_FINAL.quad_settings
    assert P23_P13_FINAL_QDE14.quad_settings["kbrqd14corr"] == 0.0


def test_the_two_lattices_really_are_different():
    for knob in ("kbrqf", "kbrqd"):
        assert P17_P23_FINAL.quad_settings[knob] != P23_P13_FINAL.quad_settings[knob]
    assert P17_P23_FINAL.chroma_file != P23_P13_FINAL.chroma_file


def test_campaign_lookup_accepts_the_cli_spelling():
    assert campaign_by_slug("p23-p13-final") is P23_P13_FINAL
    with pytest.raises(ValueError, match="Unknown campaign"):
        campaign_by_slug("sideways")


def test_build_model_takes_circuits_and_correctors_from_the_campaign(monkeypatch):
    """No tune match, and each campaign's own currents and corrector settings."""
    from loco_common import model as model_module

    monkeypatch.setattr(model_module, "matched_tune_knobs", lambda *_, **__: {"kbrqf": 0.7, "kbrqd": -0.7})

    built = {
        campaign.slug: model_module.build_model(sequence_file="seq", campaign=campaign)
        for campaign in (P17_P23_FINAL, P23_P13_FINAL)
    }
    for campaign in (P17_P23_FINAL, P23_P13_FINAL):
        assert built[campaign.slug].tune_knobs == campaign.quad_settings
        assert built[campaign.slug].corrector_knobs == psb_orbit_corrector_strengths(
            campaign.machine_config
        )
    # The 29th's normal-tunes machine stood on different correctors than the 28th's.
    assert built[P17_P23_FINAL.slug].corrector_knobs != built[P23_P13_FINAL.slug].corrector_knobs


def _values_after(argv: list[str], flag: str) -> list[str]:
    """The values after *flag*, up to the next flag."""
    rest = argv[argv.index(flag) + 1 :]
    end = next((i for i, value in enumerate(rest) if value.startswith("--")), len(rest))
    return rest[:end]


def test_page_case_commands_match_the_matrix_script():
    """The page cases map to the flags ``run_loco_matrix.sh`` would use."""
    from scripts.run_campaign_fits import command

    argv = command("xy__k1+b+dy+t__bpm-family", "p23_p13_final", "seq", Path("out"))
    assert "--absolute-planes" in argv and argv[argv.index("--absolute-planes") + 1 : ][:2] == ["x", "y"]
    assert _values_after(argv, "--errors") == ["quad:k1", "bend:k0"]
    assert _values_after(argv, "--misalign") == ["quad:dy", "quad:tilt"]
    assert "--group-quadrupoles-by-cell" in argv

    frozen = command("none__t__none", "p17_p23_final", "seq", Path("out"))
    assert _values_after(frozen, "--errors") == ["none"]
    assert _values_after(frozen, "--misalign") == ["quad:tilt"]
    assert "--group-quadrupoles-by-cell" not in frozen


def _offsets_in(argv: list[str]) -> list[str]:
    """The values after ``--rf-offsets``, up to the next flag."""
    rest = argv[argv.index("--rf-offsets") + 1 :]
    end = next(
        (i for i, v in enumerate(rest) if v.startswith("--") and not v[2:3].isdigit()),
        len(rest),
    )
    return rest[:end]


def test_multi_momentum_command_uses_the_campaigns_rf_offsets_and_batches():
    """Every campaign steps -2/0/+2 mm, so the multi mode fits all three."""
    from loco_common.fit_mode import fit_mode_by_slug
    from scripts.run_campaign_fits import command

    expected = fit_mode_by_slug("multi").rf_offsets_for(P23_P13_FINAL)
    argv = command("xy__k1+b+dy+t__bpm-family", "p23_p13_final", "seq", Path("out"), "multi")
    assert expected == (-2.0, 0.0, 2.0)
    assert _offsets_in(argv) == [f"{value:g}" for value in expected]
    assert "--batch-momenta" in argv
    # Warm-started from the nominal-momentum fit: PREVIOUS_MODE sends the multi mode back to SINGLE.
    assert argv[argv.index("--initial-knobs") + 1].endswith(
        "results/matrix_p23_p13_final/xy__k1+b+dy+t__bpm-family/knobs.csv"
    )


def test_multi_warm_starts_from_the_nominal_momentum_fit():
    from loco_common.fit_mode import MULTI, SINGLE
    from scripts.run_campaign_fits import PREVIOUS_MODE

    assert PREVIOUS_MODE[MULTI.slug] is SINGLE


def test_single_momentum_command_keeps_the_nominal_only_default():
    from scripts.run_campaign_fits import command

    argv = command("none__k1__bpm-family", "p17_p23_final", "seq", Path("out"))
    assert "--rf-offsets" not in argv
    assert "--batch-momenta" not in argv
