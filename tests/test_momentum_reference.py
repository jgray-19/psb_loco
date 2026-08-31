from types import SimpleNamespace

import pytest

from loco_common import momentum


def test_absolute_dpp_is_rebased_before_conversion_to_pt(monkeypatch, tmp_path):
    table = {
        -1: SimpleNamespace(dpp=-0.2),
        0: SimpleNamespace(dpp=0.25),
        1: SimpleNamespace(dpp=0.5),
    }
    monkeypatch.setattr(
        "psb_md.tune_measurements.load_orbit_tune_table", lambda *_args, **_kwargs: table
    )
    accelerator = SimpleNamespace(dp2pt=lambda dpp: dpp + dpp**2)

    result = momentum.chroma_pt_by_rf_offset(
        tmp_path / "chroma.txt", [-1.0, 0.0, 1.0], accelerator
    )

    # Relative Dp/p is (1+dpp_i)/(1+dpp_0)-1, hence -0.36, 0, +0.2.
    assert result == pytest.approx({-1.0: -0.2304, 0.0: 0.0, 1.0: 0.24})


def test_calibration_comparison_requires_the_same_relative_reference():
    assert momentum.compare_momentum_calibrations(
        {-1.0: -0.2, 0.0: 0.0, 1.0: 0.3},
        {-1.0: -0.1, 0.0: 0.0, 1.0: 0.5},
    ) == pytest.approx({-1.0: 0.1, 0.0: 0.0, 1.0: 0.2})

    with pytest.raises(ValueError, match="zero at the nominal-RF reference"):
        momentum.compare_momentum_calibrations(
            {-1.0: -0.2, 0.0: 0.4, 1.0: 0.3},
            {-1.0: -0.1, 0.0: 0.0, 1.0: 0.5},
        )
