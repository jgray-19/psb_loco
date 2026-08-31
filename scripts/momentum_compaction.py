"""Fit measured momentum compaction from XImeter Frev and orbit-derived Dp/p.

The XImeter ``Dp/p`` values only identify RF plateaus. Momentum for the fit is
independently reconstructed from the measured closed orbit. The fitted law is

    (Frev - Frev0) / Frev0 = -eta * Dp/p + intercept
    alpha_p = eta + 1/gamma**2 = 1/gamma**2 - slope.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from loco_common.campaign import Campaign, campaign_by_slug
from loco_common.chromaticity import PROTON_MASS_GEV
from loco_common.measured_response import (
    RF_STEERING_OFFSETS,
    average_orbit_frames,
    cached_scan,
    measured_orbits,
)
from loco_common.model import DEFAULT_SEQUENCE_FILE, KINETIC_ENERGY, build_model, model_twiss
from loco_common.momentum import estimate_pt_by_rf_offset
from psb_md.defaults import DPP_PER_MM
from psb_md.tune_measurements import (
    DEFAULT_JUMP_THRESHOLD,
    DEFAULT_ZERO_THRESHOLD,
    _aggregate_rows_by_orbit,
    _collect_section_boundaries,
    _infer_row_orbit_map,
)


def _parse_rows(lines, start, end):
    section = lines[start:end]
    times = [int(cell.strip()) for cell in section[0].split(",")[2:]]
    values = {"Dp/p": {}, "Frev": {}}
    for line in section[1:]:
        cells = [cell.strip() for cell in line.split(",")]
        if not cells or cells[0] not in values:
            continue
        raw = cells[2 : 2 + len(times)]
        raw += [""] * (len(times) - len(raw))
        values[cells[0]][int(cells[1])] = [
            None if cell == "" else float(cell) for cell in raw
        ]
    return times, values["Dp/p"], values["Frev"]


def frev_by_rf_offset(path: Path) -> dict[int, tuple[float, float, int]]:
    """Mean Frev, standard error and sample count for each XImeter plateau."""
    lines = path.read_text(encoding="utf-8").splitlines()
    first, vertical_marker, second = _collect_section_boundaries(lines)
    h_times, h_dpp, h_frev = _parse_rows(lines, first, vertical_marker)
    v_times, v_dpp, v_frev = _parse_rows(lines, second, None)
    lower, upper = min(h_times + v_times), max(h_times + v_times)
    row_map, orbits = _infer_row_orbit_map(
        h_times,
        h_dpp,
        v_times,
        v_dpp,
        ctime_min=lower,
        ctime_max=upper,
        dpp_per_index=DPP_PER_MM,
        jump_threshold=DEFAULT_JUMP_THRESHOLD,
        zero_threshold=DEFAULT_ZERO_THRESHOLD,
    )
    h = _aggregate_rows_by_orbit(
        h_times, h_frev, row_map, orbits, ctime_min=lower, ctime_max=upper
    )
    v = _aggregate_rows_by_orbit(
        v_times, v_frev, row_map, orbits, ctime_min=lower, ctime_max=upper
    )
    result = {}
    for orbit in orbits:
        samples = np.asarray(h[orbit] + v[orbit], dtype=float)
        if samples.size:
            sem = float(samples.std(ddof=1) / np.sqrt(samples.size)) if samples.size > 1 else 0.0
            result[orbit] = float(samples.mean()), sem, int(samples.size)
    return result


def orbit_dpp_by_rf_offset(campaign: Campaign) -> dict[int, float]:
    """Reconstruct relative Dp/p from the measured untrimmed closed orbits."""
    points, orbit_by_path = cached_scan(campaign=campaign)
    absolute = {}
    for offset in RF_STEERING_OFFSETS:
        untrimmed = {
            key: frame
            for key, frame in measured_orbits(
                offset, points=points, orbit_by_path=orbit_by_path, delta=False
            ).items()
            if key[1] == 0.0
        }
        absolute[offset] = average_orbit_frames(list(untrimmed.values()))

    # Use the lattice matched to the measured tune. In particular, the recorded
    # inverted currents put the model near integer Qy and are not the measured optics.
    model = build_model(
        campaign=campaign,
        sequence_file=DEFAULT_SEQUENCE_FILE,
        scan_quads=False,
    )
    pt = estimate_pt_by_rf_offset(absolute, model_twiss(model, chrom=True))
    from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: PLC0415, N811

    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=str(model.sequence_file),
        kinetic_energy=model.kinetic_energy,
    )
    return {int(offset): float(accelerator.pt2dp(value)) for offset, value in pt.items()}


def fit_momentum_compaction(campaign: Campaign, chroma_file: Path) -> dict[str, object]:
    frev = frev_by_rf_offset(chroma_file)
    dpp = orbit_dpp_by_rf_offset(campaign)
    offsets = sorted(set(frev) & set(dpp) & {int(v) for v in RF_STEERING_OFFSETS})
    if 0 not in offsets or len(offsets) < 3:
        raise ValueError(f"Need zero and two off-momentum plateaus, found {offsets}")

    x = np.asarray([dpp[offset] for offset in offsets])
    frequency = np.asarray([frev[offset][0] for offset in offsets])
    f0 = frev[0][0]
    y = (frequency - f0) / f0
    design = np.column_stack([np.ones(x.size), x])
    coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - design @ coefficients
    covariance = (
        (residual @ residual / (x.size - 2)) * np.linalg.inv(design.T @ design)
    )
    intercept, slope = map(float, coefficients)
    slope_error = float(np.sqrt(covariance[1, 1]))
    gamma = (KINETIC_ENERGY + PROTON_MASS_GEV) / PROTON_MASS_GEV
    return {
        "campaign": campaign.slug,
        "chroma_file": str(chroma_file),
        "offsets_mm": offsets,
        "orbit_dpp": {str(offset): dpp[offset] for offset in offsets},
        "frev_Hz": {str(offset): frev[offset][0] for offset in offsets},
        "frev_standard_error_Hz": {str(offset): frev[offset][1] for offset in offsets},
        "reference_frev_Hz": f0,
        "fit_intercept": intercept,
        "fit_slope_dfrev_over_f_per_dpp": slope,
        "fit_slope_error": slope_error,
        "slip_factor_eta": -slope,
        "gamma": gamma,
        "alpha_p": 1.0 / gamma**2 - slope,
        "alpha_p_statistical_error": slope_error,
        "fractional_frequency_residual_rms": float(np.sqrt(np.mean(residual**2))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=("normal", "inverted"), default="normal")
    parser.add_argument("--chroma-file", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    campaign = campaign_by_slug(args.campaign)
    result = fit_momentum_compaction(
        campaign, args.chroma_file or campaign.optics.chroma_file
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(f"Campaign:                    {result['campaign']}")
    print(f"Reference Frev:               {result['reference_frev_Hz']:.6f} Hz")
    print(f"d(Frev/Frev0)/d(Dp/p):        {result['fit_slope_dfrev_over_f_per_dpp']:+.9f}")
    print(f"Slip factor eta:              {result['slip_factor_eta']:+.9f}")
    print(f"Measured momentum compaction: {result['alpha_p']:.9f}")
    print(f"Statistical fit error:        {result['alpha_p_statistical_error']:.3g}")
    print(f"Fit intercept:                {result['fit_intercept']:+.3e}")


if __name__ == "__main__":
    main()
