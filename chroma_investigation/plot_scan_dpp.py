"""Plot the tmom-recon relative momentum for every LOCO scan point.

The estimator uses the averaged untrimmed nominal-RF orbit as its reference.
Every scan acquisition is still retained; the reference subtraction is only
the relative-momentum definition used by ``tmom-recon``.

Run with::

    MPLCONFIGDIR=/tmp .venv/bin/python chroma_investigation/plot_scan_dpp.py --campaign inverted_second
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loco_common.campaign import Campaign, add_campaign_argument, campaign_by_slug
from loco_common.measured_response import _orbit_frame, global_reference_orbit, load_scan
from loco_common.model import DEFAULT_SEQUENCE_FILE, build_model, model_twiss
from loco_common.momentum import chroma_pt_by_rf_offset, estimate_pt, frame_from_orbit

HERE = Path(__file__).parent
LOGGER = logging.getLogger(__name__)


def make_plot(result: pd.DataFrame, output: Path) -> None:
    fig, axis = plt.subplots(figsize=(11, 4.8))
    # Coloured by RF offset, not fixed to the five the first campaigns scanned:
    # a campaign like ``inverted_second`` only visited a subset of them (its RF
    # condition was set by which directory a run was saved to, not a
    # steered-per-point field -- see Campaign.rf_scan_logs).
    offsets = sorted(result["rf_offset_mm"].unique())
    colors = {offset: f"C{index % 10}" for index, offset in enumerate(offsets)}

    for rf_offset, group in result.groupby("rf_offset_mm", sort=True):
        axis.plot(
            group["scan_index"],
            group["dpp_relative"] * 1e3,
            ".-",
            ms=4,
            lw=0.8,
            color=colors.get(float(rf_offset)),
            label=f"RF {rf_offset:+g} mm",
        )
        axis.plot(
            group["scan_index"],
            group["dpp_expected"] * 1e3,
            "--",
            color=colors.get(float(rf_offset)),
            lw=1.2,
            label=f"chroma expected {rf_offset:+g} mm",
        )

    changes = result.loc[result["rf_offset_mm"].ne(result["rf_offset_mm"].shift()), "scan_index"]
    for index in changes.iloc[1:]:
        axis.axvline(index - 0.5, color="0.7", lw=0.8, zorder=0)

    axis.axhline(0.0, color="0.25", lw=0.8)
    axis.set(
        xlabel="chronological LOCO scan index",
        ylabel=r"relative $\Delta p/p$ ($10^{-3}$)",
        title="LOCO scan: tmom-recon relative momentum at every acquisition",
    )
    axis.grid(alpha=0.25)
    axis.legend(ncol=5, fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_campaign_argument(parser, default="normal")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    campaign: Campaign = campaign_by_slug(args.campaign)
    output_dir = HERE / campaign.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output_plot = output_dir / "scan_dpp_by_index.png"
    output_data = output_dir / "scan_dpp_by_index.csv"

    LOGGER.info("Freshly reading %s LOCO scan log and SDDS acquisitions", campaign.slug)
    # Deliberately bypass cached_scan(): this diagnostic must see newly copied
    # acquisitions and any updated scan-log association on every invocation.
    points, orbit_by_path = load_scan(campaign=campaign)
    LOGGER.info("Loaded %d scan points from %d distinct acquisitions", len(points), len(orbit_by_path))
    reference_orbit = global_reference_orbit(points, orbit_by_path)

    LOGGER.info("Building the campaign model and dispersion")
    model = build_model(
        campaign=campaign,
        scan_correctors=False,
        sequence_file=DEFAULT_SEQUENCE_FILE,
    )
    twiss = model_twiss(model, chrom=True)
    reference_frame = frame_from_orbit(reference_orbit, twiss)
    LOGGER.info(
        "Using the averaged untrimmed nominal-RF orbit as the tmom-recon reference"
    )
    from aba_optimiser.accelerators import PSB as OptimiserPSB

    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    # The RF offsets actually scanned by this campaign, not the fixed five the
    # first campaigns visited: a campaign like ``inverted_second`` only ran a
    # subset (its condition was set by save directory, not a per-point field --
    # see Campaign.rf_scan_logs), and the chroma calibration is looked up per
    # offset, so asking for one that was never scanned here would be wrong even
    # where the chroma file happens to carry that band too.
    rf_offsets = sorted({point.rf_offset for point in points})
    expected_pt = chroma_pt_by_rf_offset(
        campaign.optics.chroma_file,
        rf_offsets,
        accelerator,
    )
    expected_dpp = {
        offset: float(accelerator.pt2dp(pt)) for offset, pt in expected_pt.items()
    }
    LOGGER.info("Expected chroma-scan dpp by RF offset: %s", expected_dpp)

    rows = []
    for scan_index, point in enumerate(points):
        frame = _orbit_frame(orbit_by_path[point.path])
        pt = estimate_pt(frame, twiss, reference_frame)
        dpp = float(accelerator.pt2dp(pt))
        LOGGER.info(
            "scan_index=%d rf_offset=%+g mm corrector=%s plane=%s offset_k=%+.6g "
            "file=%s relative_pt=%+.6e relative_dpp=%+.6e",
            scan_index,
            point.rf_offset,
            point.corrector,
            point.plane,
            point.offset_k,
            point.path.name,
            pt,
            dpp,
        )
        rows.append(
            {
                "scan_index": scan_index,
                "rf_offset_mm": point.rf_offset,
                "corrector": point.corrector,
                "plane": point.plane,
                "offset_k": point.offset_k,
                "file": str(point.path),
                "dpp_relative": dpp,
                "dpp_expected": expected_dpp[point.rf_offset],
            }
        )

    result = pd.DataFrame(rows)
    result.to_csv(output_data, index=False)
    make_plot(result, output_plot)
    LOGGER.info("Wrote %s", output_plot)
    LOGGER.info("Wrote %s", output_data)


if __name__ == "__main__":
    main()
