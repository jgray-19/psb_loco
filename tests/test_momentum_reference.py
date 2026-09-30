import math
from pathlib import Path

import psb_md
import pytest
from aba_optimiser.accelerators import PSB
from psb_md.defaults import DPP_PER_MM
from psb_md.tune_measurements import load_orbit_tune_table

from loco_common import momentum
from loco_common.campaign import campaign_by_slug

RF_OFFSETS = [-2.0, 0.0, 2.0]
# Any real PSB ring-3 sequence: dp2pt depends only on the beam energy.
SEQUENCE = (
    Path(psb_md.__file__).parents[1]
    / "tests/data/models/reference/model_qx0.170000_qy0.230000_driven_qx0.162500_qy0.235200"
    / "psb3_saved.seq"
)


@pytest.fixture(scope="module")
def chroma():
    chroma_file = campaign_by_slug("p23_p13_final").chroma_file
    return chroma_file, load_orbit_tune_table(chroma_file, dpp_per_index=DPP_PER_MM)


@pytest.fixture(scope="module")
def accelerator():
    return PSB(ring=3, sequence_file=SEQUENCE)


def test_chroma_dpp_is_rebased_on_the_0mm_plateau_before_conversion_to_pt(chroma, accelerator):
    chroma_file, table = chroma

    result = momentum.chroma_pt_by_rf_offset(chroma_file, RF_OFFSETS, accelerator)

    reference = 1.0 + table[0].dpp
    expected = {
        offset: accelerator.dp2pt((1.0 + table[int(offset)].dpp) / reference - 1.0)
        for offset in RF_OFFSETS
    }
    expected[0.0] = 0.0
    assert result == pytest.approx(expected, rel=1e-12, abs=0.0)
    assert result[-2.0] < 0.0 < result[2.0]
    # Subtracting absolute pt values is off by a few ppm on this scan, above the tolerance.
    for offset in (-2.0, 2.0):
        naive = accelerator.dp2pt(table[int(offset)].dpp) - accelerator.dp2pt(table[0].dpp)
        assert abs(naive - result[offset]) > 1e-7 * abs(result[offset])


def test_chroma_pt_error_combines_the_band_and_reference_scatter(chroma, accelerator):
    chroma_file, table = chroma

    errors = momentum.chroma_pt_error_by_rf_offset(chroma_file, RF_OFFSETS, accelerator)

    assert errors[0.0] == 0.0
    # |Dp/p| ~ 1e-3, so the rebasing slopes are one to 1e-3 and dp2pt is locally linear.
    slope = (accelerator.dp2pt(1e-6) - accelerator.dp2pt(-1e-6)) / 2e-6
    for offset in (-2.0, 2.0):
        sigma = math.hypot(table[int(offset)].dpp_std, table[0].dpp_std)
        assert errors[offset] == pytest.approx(slope * sigma, rel=1e-2)


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
