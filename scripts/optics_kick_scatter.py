"""Report how far omc3's measured-optics error bar is from kick-to-kick reality.

The estimator lives in :mod:`loco_common.optics_reproducibility`, which is also
what ``measured_optics.py`` uses to set the bars it writes; this script is the
standalone view of the same numbers, one folder at a time, and the place to run
the single-kick diagnostic that shows why the bootstrap resamples whole folders
rather than individual kicks.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loco_common.campaign import campaign_by_slug  # noqa: E402
from loco_common.optics_reproducibility import REPLICAS, bootstrap_frames  # noqa: E402
from scripts.measured_optics import measured_frame  # noqa: E402

logger = logging.getLogger(__name__)

OUTPUT = Path("results/optics_kick_scatter")


def summarise(replicas: pd.DataFrame, pooled: pd.DataFrame) -> pd.DataFrame:
    """Per-BPM resampled error against the error omc3 quoted for the folder."""
    measured = [
        column
        for column in replicas.columns
        if column not in ("NAME", "REPLICA") and not column.endswith(("_err", "_model"))
    ]
    rows = []
    for column in measured:
        grouped = replicas.groupby("NAME")[column]
        rows.append(
            pd.DataFrame(
                {
                    "COLUMN": column,
                    "VALUE": pooled[column],
                    "RESAMPLED_ERR": grouped.std(ddof=1),
                    "QUOTED_ERR": pooled.get(f"{column}_err"),
                    "REPLICAS": grouped.count(),
                }
            )
        )
    out = pd.concat(rows).reset_index()
    out["RATIO"] = out.RESAMPLED_ERR / out.QUOTED_ERR
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--folder", required=True)
    parser.add_argument("--replicas", type=int, default=REPLICAS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--single", action="store_true", help="per-kick optics instead of bootstrap replicas"
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    campaign = campaign_by_slug(args.campaign)
    root = campaign.optics_dir / args.folder
    replicas = bootstrap_frames(
        root, measured_frame, replicas=args.replicas, seed=args.seed, single=args.single
    )
    summary = summarise(replicas, measured_frame(root / "free"))

    args.output.mkdir(parents=True, exist_ok=True)
    stem = f"{campaign.slug}_{args.folder}" + ("_single" if args.single else "")
    summary.to_parquet(args.output / f"{stem}_summary.parquet")

    for column, sub in summary.groupby("COLUMN"):
        logger.info(
            "%s %s/%s: quoted %.4g, resampled %.4g -- error bar low by %.1fx",
            campaign.slug, args.folder, column,
            sub.QUOTED_ERR.median(), sub.RESAMPLED_ERR.median(), sub.RATIO.median(),
        )


if __name__ == "__main__":
    main()
