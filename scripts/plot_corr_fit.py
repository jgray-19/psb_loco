"""Plot the measured closed-orbit response to corrector changes.

The scan loading, reference subtraction and slope fit all live in
:mod:`loco_common.measured_response` -- the same code the two LOCO methods take
their targets from, so what is plotted here is what is fitted there.
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

from loco_common.campaign import add_campaign_argument, campaign_by_slug
from loco_common.measured_response import (
    ScanPoint,
    cached_scan,
    global_reference_orbit,
    measured_response,
    subtract_reference,
)

# Wong palette: high-contrast colours that remain distinguishable for common
# forms of colour-vision deficiency.
COLOURBLIND_PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")


def plot_plane(
    points: list[ScanPoint],
    plane: str,
    rf_offset: float,
    orbit_by_path: dict,
    reference: pd.DataFrame,
    output: Path,
) -> None:
    """One panel per BPM, one colour per corrector, with the fitted slope drawn."""
    plane_points = [point for point in points if point.plane == plane]
    if not plane_points:
        return
    correctors = list(dict.fromkeys(point.corrector for point in plane_points))
    column = "X" if plane == "x" else "Y"
    # measured_response() keeps both BPM channels per corrector (a corrector can
    # couple into the other plane), so (NAME, CORRECTOR) is not a unique index
    # until the row for the *other* plane's channel is dropped first -- keeping
    # both left .loc[(bpm, corrector)] returning two rows and drawing a line
    # built from one plane's slope and the other's intercept.
    response = measured_response(
        rf_offset, points=plane_points, orbit_by_path=orbit_by_path, reference=reference
    )
    response = response[response["PLANE"] == plane].set_index(["NAME", "CORRECTOR"])

    bpm_names = list(orbit_by_path[plane_points[0].path][column][0].index)
    figure, axes = plt.subplots(4, 4, figsize=(16, 13), sharex=True, sharey=True)
    axes = axes.ravel()

    for bpm_index, bpm in enumerate(bpm_names):
        axis = axes[bpm_index]
        for corrector_index, corrector in enumerate(correctors):
            selected = sorted(
                (p for p in plane_points if p.corrector == corrector),
                key=lambda p: p.offset_k,
            )
            offsets = np.array([p.offset_k for p in selected])
            error_column = "ERRX" if column == "X" else "ERRY"
            # Subtracted through the same helper the fits use, against the same
            # single global reference, so the points drawn are the points fitted.
            deltas = [
                subtract_reference(_frame(orbit_by_path[p.path]), reference).loc[bpm]
                for p in selected
            ]
            values = np.array([d[column] for d in deltas]) * 1e3
            errors = np.array([d[error_column] for d in deltas]) * 1e3
            colour = COLOURBLIND_PALETTE[corrector_index % len(COLOURBLIND_PALETTE)]
            axis.errorbar(
                offsets, values, yerr=errors, fmt="o", ms=3, capsize=2,
                color=colour, label=corrector.rsplit(".", 1)[-1],
            )
            fit = response.loc[(bpm, corrector)]
            fit_x = np.array([offsets.min(), offsets.max()])
            axis.plot(
                fit_x,
                (fit["SLOPE"] * fit_x + fit["INTERCEPT"]) * 1e3,
                "-", lw=1, color=colour,
            )
        axis.set_title(str(bpm))
        axis.grid(alpha=0.25)

    for axis in axes[len(bpm_names):]:
        axis.set_visible(False)
    figure.supxlabel("Corrector offset, $\\Delta k$ [rad]")
    figure.supylabel("Closed-orbit change [mm]")
    figure.suptitle(f"Corrector response ({plane.upper()} plane, RF offset {rf_offset:+g} mm)")
    axes[0].legend(fontsize="small", loc="best")
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _frame(orbit) -> pd.DataFrame:
    """One acquisition as the ``X/ERRX/Y/ERRY`` frame the subtraction takes."""
    frame = pd.DataFrame(
        {
            "X": orbit["X"][0],
            "ERRX": orbit["X"][1],
            "Y": orbit["Y"][0],
            "ERRY": orbit["Y"][1],
        }
    )
    frame.index.name = "NAME"
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_campaign_argument(parser, default="p23_p13_final")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    campaign = campaign_by_slug(args.campaign)
    # The acquisition mount is read-only, so figures land beside this script by
    # default, namespaced by campaign like every other generated product.
    output_root = args.output or Path(__file__).parent
    output_stem = output_root / campaign.slug / "corr_fit"

    points, orbit_by_path = cached_scan(campaign=campaign)
    reference = global_reference_orbit(points, orbit_by_path)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    for rf_offset in campaign.rf_offsets:
        rf_points = [point for point in points if point.rf_offset == rf_offset]
        suffix = f"rf_{rf_offset:+g}".replace("+", "p").replace("-", "m")
        for plane in ("x", "y"):
            plot_plane(
                rf_points, plane, rf_offset, orbit_by_path, reference,
                output_stem.with_name(f"{output_stem.name}_{suffix}_{plane}.png"),
            )
    print(f"Associated {len(points)} scan points; plots written with stem {output_stem}")


if __name__ == "__main__":
    main()
