"""Settings spread over fewer workers give the fit of one worker per setting."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from adelmo.machine.accelerators.psb import PSB as OptimiserPSB
from adelmo.optimisers.levenberg_marquardt import LevenbergMarquardtConfig
from adelmo.fitting.config import SequenceConfig
from adelmo.poco.closed_orbit import ClosedOrbitFitter, ClosedOrbitMeasurement, ClosedOrbitSeries

pytestmark = pytest.mark.slow

BPMS = [f"BR3.BPM{i}L3" for i in range(1, 17)]
CORRECTORS = ["BR3.DHZ8L1", "BR3.DHZ11L4", "BR3.DVT2L4", "BR3.DVT8L1"]


def _orbit(rng) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "X": rng.normal(0, 1e-4, len(BPMS)),
            "ERRX": 1e-5,
            "Y": rng.normal(0, 1e-4, len(BPMS)),
            "ERRY": 1e-5,
        },
        index=BPMS,
    )


def _series() -> list[ClosedOrbitSeries]:
    rng = np.random.default_rng(1)
    return [
        ClosedOrbitSeries(
            measurements=tuple(
                ClosedOrbitMeasurement(orbit=_orbit(rng), pt=pt) for pt in (-1e-3, 0.0, 1e-3)
            ),
            machine_state={"k" + name.replace(".", "").lower(): 5e-5 * (1 + i)},
            label=name,
        )
        for i, name in enumerate(CORRECTORS)
    ]


def _fit(sequence_file, max_workers, tmp_path):
    from adelmo.fitting.config import OutputConfig

    fitter = ClosedOrbitFitter(
        accelerator=OptimiserPSB(
            ring=3,
            sequence_file=sequence_file,
            kinetic_energy=0.16,
            errors={"quad": {"k1"}},
            group_quadrupoles_by_cell=True,
        ),
        sequence_config=SequenceConfig(magnet_range="$start/$end"),
        series=_series(),
        lm_config=LevenbergMarquardtConfig(max_iterations=2),
        output_config=OutputConfig(tensorboard_root=tmp_path / str(max_workers)),
        max_workers=max_workers,
    )
    try:
        knobs = fitter.run().knobs
    finally:
        fitter.close()
    return knobs, fitter.n_workers


def test_batched_workers_reproduce_one_worker_per_setting(sequence_file, tmp_path):
    reference, n_reference = _fit(sequence_file, len(CORRECTORS), tmp_path)
    assert n_reference == len(CORRECTORS)
    assert max(abs(v) for v in reference.values()) > 1e-9

    for max_workers in (1, 2):
        knobs, n_workers = _fit(sequence_file, max_workers, tmp_path)
        assert n_workers == max_workers
        assert knobs.keys() == reference.keys()
        np.testing.assert_allclose(
            [knobs[k] for k in reference], [reference[k] for k in reference], rtol=1e-6, atol=1e-12
        )
