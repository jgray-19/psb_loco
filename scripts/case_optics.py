"""Optics of each fitted lattice along ``s``, against the model it started from.

Each case gets its own twiss, differenced against the start model:

* **beta-beating**, ``(beta_fit - beta_start) / beta_start``, per plane;
* **phase-advance error**, ``mu_fit - mu_start`` in units of :math:`2\\pi`, ring-wide slope kept;
* **dispersion**, ``dx`` and ``dy``, for the fitted and start lattice.

One MAD-NG process per case, so the result is cached to parquet for the figure scripts.

    uv run python scripts/case_optics.py                    # every page's cases
    uv run python scripts/case_optics.py --options none__k1__none
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from loco_common.campaign import add_campaign_argument, campaign_by_slug
from loco_common.case_names import parse_case
from loco_common.fit_mode import (
    add_fit_mode_argument,
    fit_mode_by_slug,
    result_is_valid,
)
from loco_common.model import DEFAULT_SEQUENCE_FILE, build_model
from scripts.measured_optics import campaign_natural_tune
from scripts.predict_loco import open_full_interface

logger = logging.getLogger(__name__)

#: Columns the figures need, and the names they keep in the cache.
TWISS_COLUMNS = ("s", "beta11", "beta22", "mu1", "mu2", "dx", "dy", "x", "y",
                 "f1001", "f1010")


def _twiss(model, fitted: pd.Series | None, match_to: tuple[float, float] | None = None,
           *, high_order: bool = False) -> pd.DataFrame:
    """One lattice's twiss at every element, with the fitted knobs applied.

    Every knob family is created and zeroed first, as ``predict_loco`` does.
    ``match_to`` matches ``kbrqf``/``kbrqd`` to a tune, for the reference lattice only.
    ``high_order`` selects the order-8, 2-slice integrator (skew-multipole case only), so its diff
    against the method=6 reference includes an integrator-order difference.
    """
    interface = open_full_interface(model)
    try:
        values = dict.fromkeys(interface.knob_names, 0.0)
        if fitted is not None:
            values.update({k: float(v) for k, v in fitted.items() if k in values})
        interface.update_knob_values(values)
        if match_to is not None:
            interface.match_tunes(*match_to)
        # coupling=True adds the f1001/f1010 columns.
        if high_order:
            table = interface.run_twiss(observe=0, method=8, nslice=2, coupling=True)
        else:
            table = interface.run_twiss(observe=0, method=6, coupling=True)
    finally:
        interface.close()
    present = [c for c in TWISS_COLUMNS if c in table.columns]
    # RDTs are complex; figures and rms use the amplitude, as omc3 does. Don't take the modulus of real columns.
    frame = pd.DataFrame({
        column: (
            np.abs(table[column].to_numpy())
            if np.iscomplexobj(table[column].to_numpy())
            else table[column].to_numpy(float)
        )
        for column in present
    }, index=table.index)
    frame["dq_dpt_x"] = float(table.headers["dq1"])
    frame["dq_dpt_y"] = float(table.headers["dq2"])
    frame.index = [str(name) for name in table.index]
    frame.index.name = "element"
    return frame


def case_optics(model, knobs_path: Path | None, start: pd.DataFrame,
                 *, high_order: bool = False) -> pd.DataFrame:
    """One case's optics, differenced element by element against *start*; a zero beta divides through rather than being floored."""
    fitted = (
        None if knobs_path is None
        else pd.read_csv(knobs_path).set_index("knob")["value"]
    )
    frame = _twiss(model, fitted, high_order=high_order)
    common = frame.index.intersection(start.index)
    frame, reference = frame.loc[common], start.loc[common]

    optics = pd.DataFrame({"element": common, "s": frame["s"].to_numpy()})
    for plane, beta, mu in (("x", "beta11", "mu1"), ("y", "beta22", "mu2")):
        optics[f"beta_beating_{plane}"] = (
            frame[beta].to_numpy() / reference[beta].to_numpy() - 1.0
        )
        optics[f"phase_error_{plane}"] = frame[mu].to_numpy() - reference[mu].to_numpy()
        optics[f"beta_{plane}"] = frame[beta].to_numpy()
    for rdt in ("f1001", "f1010"):
        if rdt in frame.columns:
            optics[f"coupling_{rdt}"] = frame[rdt].to_numpy()
            optics[f"coupling_{rdt}_start"] = reference[rdt].to_numpy()
    for plane in ("x", "y"):
        optics[f"dispersion_{plane}"] = frame[plane_dispersion(frame, plane)].to_numpy()
        optics[f"dispersion_{plane}_start"] = (
            reference[plane_dispersion(reference, plane)].to_numpy()
        )
        optics[f"dq_dpt_{plane}"] = frame[f"dq_dpt_{plane}"].to_numpy()
    return optics


def plane_dispersion(frame: pd.DataFrame, plane: str) -> str:
    """The twiss column carrying ``d<plane>/dpt``, or a zero column if absent."""
    column = f"d{plane}"
    if column not in frame.columns:
        frame[column] = 0.0
        logger.warning("Twiss has no %s column; vertical dispersion plotted as zero", column)
    return column


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    add_campaign_argument(parser)
    add_fit_mode_argument(parser)
    parser.add_argument("--sequence-file", type=Path,
                        default=DEFAULT_SEQUENCE_FILE)
    parser.add_argument(
        "--options", nargs="+", default=None,
        help="Options to twiss; default is every option any report page shows, Method 1 included.",
    )
    parser.add_argument(
        "--models-only", action="store_true",
        help="Twiss the two reference lattices and stop, leaving the cases cached.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from loco_common.case_names import every_option

    campaign = campaign_by_slug(args.campaign)
    mode = fit_mode_by_slug(args.momentum_mode)
    root = mode.results_root(campaign)
    args.matrix = args.matrix or root
    args.output = args.output or root / "optics"
    model = build_model(sequence_file=args.sequence_file, campaign=campaign)
    options = args.options or every_option()
    args.output.mkdir(parents=True, exist_ok=True)

    start = _twiss(model, None)
    start.to_parquet(args.output / "start-model.twiss.parquet")
    logger.info("Start model twiss over %d elements", len(start))

    # Second reference lattice: main circuits matched to the measured tune.
    natural_tune = campaign_natural_tune(campaign, args.sequence_file)
    matched = _twiss(model, None, match_to=natural_tune)
    matched.to_parquet(args.output / "matched-model.twiss.parquet")
    logger.info(
        "Matched model twiss over %d elements, matched to %.5f / %.5f",
        len(matched), *natural_tune,
    )
    if args.models_only:
        return

    for option in options:
        knobs = args.matrix / option / "knobs.csv"
        if not knobs.exists():
            logger.warning("%s: no knobs.csv, skipping", option)
            continue
        if option != "method1" and not result_is_valid(args.matrix / option):
            logger.warning("%s: no accepted optimisation step, skipping", option)
            continue
        # Only the skew-multipole families use the order-8 integrator.
        high_order = bool({"k0s", "k1s"} & set(parse_case(option).family_list))
        optics = case_optics(model, knobs, start, high_order=high_order)
        optics.to_parquet(args.output / f"{option}.optics.parquet")
        logger.info(
            "%-30s beta-beating rms %5.2f%% / %5.2f%%   dQx %+.4f  dQy %+.4f",
            option,
            100 * float(np.sqrt(np.mean(optics["beta_beating_x"] ** 2))),
            100 * float(np.sqrt(np.mean(optics["beta_beating_y"] ** 2))),
            float(optics["phase_error_x"].iloc[-1]),
            float(optics["phase_error_y"].iloc[-1]),
        )


if __name__ == "__main__":
    main()
