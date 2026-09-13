"""Plot the difference between two campaigns' measured closed-orbit response.

Same panel layout as :mod:`scripts.plot_corr_fit` (one panel per BPM, one
colour per corrector, x-axis corrector offset, y-axis orbit change) but the
y-axis is *campaign B's orbit change minus campaign A's*, at matching
correctors and offsets, with both campaigns' error bars added in quadrature.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loco_common.campaign import campaign_by_slug
from loco_common.measured_response import (
    ScanPoint,
    cached_scan,
    global_reference_orbit,
    measured_response,
    subtract_reference,
)
from scripts.plot_corr_fit import COLOURBLIND_PALETTE, _frame


def plot_plane_diff(
    points_a: list[ScanPoint], orbit_by_path_a: dict, reference_a: pd.DataFrame, label_a: str,
    points_b: list[ScanPoint], orbit_by_path_b: dict, reference_b: pd.DataFrame, label_b: str,
    plane: str, rf_offset: float, output: Path,
) -> None:
    plane_points_a = [p for p in points_a if p.plane == plane and p.rf_offset == rf_offset]
    plane_points_b = [p for p in points_b if p.plane == plane and p.rf_offset == rf_offset]
    if not plane_points_a or not plane_points_b:
        return
    correctors = [
        c for c in dict.fromkeys(p.corrector for p in plane_points_a)
        if c in {p.corrector for p in plane_points_b}
    ]
    column = "X" if plane == "x" else "Y"
    error_column = "ERRX" if column == "X" else "ERRY"

    response_a = measured_response(
        rf_offset, points=plane_points_a, orbit_by_path=orbit_by_path_a, reference=reference_a
    )
    response_a = response_a[response_a["PLANE"] == plane].set_index(["NAME", "CORRECTOR"])
    response_b = measured_response(
        rf_offset, points=plane_points_b, orbit_by_path=orbit_by_path_b, reference=reference_b
    )
    response_b = response_b[response_b["PLANE"] == plane].set_index(["NAME", "CORRECTOR"])

    bpm_names = list(orbit_by_path_a[plane_points_a[0].path][column][0].index)
    figure, axes = plt.subplots(4, 4, figsize=(16, 13), sharex=True, sharey=True)
    axes = axes.ravel()

    for bpm_index, bpm in enumerate(bpm_names):
        axis = axes[bpm_index]
        for corrector_index, corrector in enumerate(correctors):
            selected_a = sorted(
                (p for p in plane_points_a if p.corrector == corrector), key=lambda p: p.offset_k
            )
            selected_b = sorted(
                (p for p in plane_points_b if p.corrector == corrector), key=lambda p: p.offset_k
            )
            offsets_a = {round(p.offset_k, 12): p for p in selected_a}
            offsets_b = {round(p.offset_k, 12): p for p in selected_b}
            common_offsets = sorted(set(offsets_a) & set(offsets_b))
            if not common_offsets:
                continue
            deltas_a = [
                subtract_reference(_frame(orbit_by_path_a[offsets_a[o].path]), reference_a).loc[bpm]
                for o in common_offsets
            ]
            deltas_b = [
                subtract_reference(_frame(orbit_by_path_b[offsets_b[o].path]), reference_b).loc[bpm]
                for o in common_offsets
            ]
            values = (
                np.array([d[column] for d in deltas_b]) - np.array([d[column] for d in deltas_a])
            ) * 1e3
            errors = np.hypot(
                np.array([d[error_column] for d in deltas_a]),
                np.array([d[error_column] for d in deltas_b]),
            ) * 1e3
            offsets = np.array(common_offsets)
            colour = COLOURBLIND_PALETTE[corrector_index % len(COLOURBLIND_PALETTE)]
            axis.errorbar(
                offsets, values, yerr=errors, fmt="o", ms=3, capsize=2,
                color=colour, label=corrector.rsplit(".", 1)[-1],
            )
            fit_a = response_a.loc[(bpm, corrector)]
            fit_b = response_b.loc[(bpm, corrector)]
            fit_x = np.array([offsets.min(), offsets.max()])
            line_a = fit_a["SLOPE"] * fit_x + fit_a["INTERCEPT"]
            line_b = fit_b["SLOPE"] * fit_x + fit_b["INTERCEPT"]
            axis.plot(fit_x, (line_b - line_a) * 1e3, "-", lw=1, color=colour)
        axis.axhline(0, color="grey", lw=0.6)
        axis.set_title(str(bpm))
        axis.grid(alpha=0.25)

    for axis in axes[len(bpm_names):]:
        axis.set_visible(False)
    figure.supxlabel("Corrector offset, $\\Delta k$ [rad]")
    figure.supylabel(f"Orbit change, {label_b} $-$ {label_a} [mm]")
    figure.suptitle(f"Corrector response difference ({plane.upper()} plane, RF offset {rf_offset:+g} mm)")
    axes[0].legend(fontsize="small", loc="best")
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)
    print(f"Wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-a", required=True)
    parser.add_argument("--campaign-b", required=True)
    parser.add_argument("--output", type=Path, default=Path("plots"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    campaign_a = campaign_by_slug(args.campaign_a)
    campaign_b = campaign_by_slug(args.campaign_b)
    points_a, orbit_by_path_a = cached_scan(campaign=campaign_a)
    points_b, orbit_by_path_b = cached_scan(campaign=campaign_b)
    reference_a = global_reference_orbit(points_a, orbit_by_path_a)
    reference_b = global_reference_orbit(points_b, orbit_by_path_b)

    output_stem = args.output / f"corr_fit_diff_{campaign_b.slug}_minus_{campaign_a.slug}"
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    for rf_offset in campaign_a.rf_offsets:
        rf_points_a = [p for p in points_a if p.rf_offset == rf_offset]
        rf_points_b = [p for p in points_b if p.rf_offset == rf_offset]
        suffix = f"rf_{rf_offset:+g}".replace("+", "p").replace("-", "m")
        for plane in ("x", "y"):
            plot_plane_diff(
                rf_points_a, orbit_by_path_a, reference_a, campaign_a.slug,
                rf_points_b, orbit_by_path_b, reference_b, campaign_b.slug,
                plane, rf_offset,
                output_stem.with_name(f"{output_stem.name}_{suffix}_{plane}.png"),
            )


if __name__ == "__main__":
    main()
