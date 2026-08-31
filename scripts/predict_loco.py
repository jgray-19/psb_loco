"""Evaluate every fitted LOCO option on one common set of predictions.

A fit's own loss is not a score: each option fits a different target, so their
residuals are not comparable -- the same trap docs/reference/handover.md section 9.4 documents
for the momentum curve. What *is* comparable is what each fitted model predicts
about the machine, so every result directory is evaluated here on the same three
questions, whatever it was fitted on:

1. **Delta orbits.** The 48 corrector trims at nominal RF, reference removed.
   This is Method 2's home ground and the number docs/reference/handover.md quotes.
2. **Static closed orbit.** The machine's untrimmed orbit in both planes, which
   only the bends (x) and quadrupole ``dy`` (y) can explain.
3. **Dispersion.** The slope of the untrimmed orbit against momentum over the
   five RF-steering settings, measured and modelled the same way -- a linear fit
   over the same five ``pt``, so no twiss-column convention enters.

Every model is stood up identically: all three knob families created (so a knob
absent from a fit is set to zero rather than missing), the machine's own
corrector settings standing, and the corrector trims applied through the MAD-X
global the sequence defers to.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
from aba_optimiser.mad import GradientDescentMadInterface

from loco_common.campaign import Campaign, add_campaign_argument, campaign_by_slug
from loco_common.fit_mode import add_fit_mode_argument, fit_mode_by_slug, result_is_valid
from loco_common.measured_response import (
    RF_STEERING_OFFSETS,
    average_orbit_frames,
    cached_orbits,
    cached_scan,
    measured_orbits,
)
from loco_common.model import DEFAULT_SEQUENCE_FILE, build_model, model_twiss
from loco_common.momentum import estimate_pt_by_rf_offset
from method2_delta_orbit.run_method2 import build_settings
from tmom_recon.physics.closed_orbit import fit_dispersion

logger = logging.getLogger(__name__)

PLANES = ("x", "y")
#: Measured-frame column per plane; the model's twiss columns are lowercase.
MEASURED_COLUMN = {"x": "X", "y": "Y"}
#: The measurement's own error bar, alongside the value. It is a standard error
#: of the mean over turns and bunches (``measured_response.closed_orbit``),
#: propagated through the reference subtraction in quadrature, so a residual can
#: be read against it: inside the bar the model already explains the orbit to
#: the precision the machine was measured at, and no fit can do better.
MEASURED_ERROR_COLUMN = {"x": "ERRX", "y": "ERRY"}


def measured_targets(model, campaign: Campaign):
    """The three common targets, in metres, indexed by BPM.

    Returns ``(deltas, absolute, pt)`` where *deltas* maps a corrector trim to
    its reference-subtracted orbit frame, *absolute* maps an RF offset to the
    machine's untrimmed orbit, and *pt* maps an RF offset to its momentum.
    """
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
        if not untrimmed:
            # This campaign's RF steering scan skipped this offset (e.g. a
            # three-point momentum scan only touched -2/0/2 mm); nothing to
            # average, so it's absent downstream rather than a hard failure.
            continue
        # Repeats of one machine state: every corrector's scan started here.
        # ``sum(...) / len(...)`` would average the ERRX/ERRY columns with the
        # orbits and leave the error bar a factor sqrt(N) too large.
        absolute[offset] = average_orbit_frames(list(untrimmed.values()))
    pt = estimate_pt_by_rf_offset(absolute, model_twiss(model, chrom=True))
    # ``machine`` so that ``setting.nominal`` is where the corrector actually
    # stood: the trim is applied as nominal + dk against a model whose other
    # correctors are at their machine values, so the delta is the measured one.
    deltas = build_settings(
        cached_orbits(0.0, campaign=campaign), model, rf_offset=0.0,
        corrector_baseline="machine",
    )
    return deltas, absolute, pt


def open_full_interface(model):
    """One interface carrying every knob family, on the machine's correctors.

    All four families are created even for a fit that froze one, so that a
    frozen family enters as an explicit zero and every option is evaluated on
    the same lattice parametrisation. Missing one here would not error -- the
    fitted knobs for it would simply never be applied, and the option would be
    scored as though it had never been fitted at all.
    """
    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=str(model.sequence_file),
        kinetic_energy=model.kinetic_energy,
        optimise_quadrupoles=True,
        optimise_bends=True,
        optimise_quad_dy=True,
        optimise_quad_tilt=True,
    )
    return GradientDescentMadInterface(
        accelerator=accelerator,
        tune_knobs=model.tune_knobs or None,
        corrector_knobs=model.corrector_knobs or None,
    )


def orbit_at(interface, pt: float = 0.0) -> pd.DataFrame:
    """Closed orbit at the observed BPMs, in metres, at momentum ``pt``.

    ``pt`` goes to twiss directly: MAD-NG is ``pt``-based throughout and
    ``run_twiss`` accepts ``pt=``, seeding it as ``X0=[0,0,0,0,0,pt]``. No
    conversion to ``dp/p`` happens or should -- the momenta this module works
    in are the same ``pt`` that :func:`estimate_pt_by_rf_offset` returns and
    that :func:`dispersion` fits the orbit slope against.
    """
    twiss = interface.run_twiss(observe=1, pt=pt, method=6)
    return pd.DataFrame(
        {"x": twiss["x"].astype(float), "y": twiss["y"].astype(float)}, index=twiss.index
    )


def set_corrector(interface, knob: str, value: float) -> None:
    """Set a corrector's MAD-X global, the same deferral the sequence uses."""
    interface.mad.send(f"MADX['{knob}'] = {value:.15e}")


def predict(open_interface, model, targets):
    """Model predictions for the three common targets, aligned to the BPMs.

    *open_interface* is a factory, not an interface, because a fitted lattice can
    fail to close at the measured off-momentum settings -- an unstable optics is
    one of the things an option can predict, and it has to be recorded rather
    than crash the sweep. MAD-NG is not reliably usable after it errors, so each
    off-momentum point gets a fresh process and a failure becomes ``NaN``.
    """
    deltas, absolute, pt = targets
    standing = dict(model.corrector_knobs)
    interface = open_interface()
    for knob, value in standing.items():
        set_corrector(interface, knob, value)

    nominal = {0.0: orbit_at(interface, pt[0.0])}
    lost = []

    delta_rows = []
    for setting in deltas:
        set_corrector(interface, setting.knob, setting.nominal + setting.dk)
        kicked = orbit_at(interface)
        set_corrector(interface, setting.knob, standing.get(setting.knob, 0.0))
        difference = kicked - nominal[0.0]
        target = setting.orbit
        common = difference.index.intersection(target.index)
        for plane in PLANES:
            delta_rows.append(
                pd.DataFrame(
                    {
                        "corrector": setting.corrector,
                        "offset_k": setting.offset_k,
                        "plane": plane,
                        "bpm": common,
                        "model": difference.loc[common, plane].to_numpy(),
                        "measured": target.loc[common, MEASURED_COLUMN[plane]].to_numpy(),
                        "error": target.loc[common, MEASURED_ERROR_COLUMN[plane]].to_numpy(),
                    }
                )
            )
    delta_frame = pd.concat(delta_rows, ignore_index=True)
    interface.close()

    for offset in absolute:
        if offset == 0.0:
            continue
        interface = open_interface()
        try:
            for knob, value in standing.items():
                set_corrector(interface, knob, value)
            nominal[offset] = orbit_at(interface, pt[offset])
        except RuntimeError:  # what MAD-NG raises when the closed orbit diverges
            logger.warning("No closed orbit at RF %+g mm (pt %+.3e)", offset, pt[offset])
            nominal[offset] = nominal[0.0] * np.nan
            lost.append(offset)
        finally:
            interface.close()

    absolute_rows = []
    for offset in absolute:
        target = absolute[offset]
        common = nominal[offset].index.intersection(target.index)
        for plane in PLANES:
            absolute_rows.append(
                pd.DataFrame(
                    {
                        "rf_offset": offset,
                        "pt": pt[offset],
                        "plane": plane,
                        "bpm": common,
                        "model": nominal[offset].loc[common, plane].to_numpy(),
                        "measured": target.loc[common, MEASURED_COLUMN[plane]].to_numpy(),
                        "error": target.loc[common, MEASURED_ERROR_COLUMN[plane]].to_numpy(),
                    }
                )
            )
    return delta_frame, pd.concat(absolute_rows, ignore_index=True), lost


def dispersion(frame: pd.DataFrame) -> pd.DataFrame:
    """Orbit slope against ``pt`` per BPM; wraps ``tmom_recon.physics.closed_orbit.fit_dispersion``."""
    return fit_dispersion(frame)


def rms(values) -> float:
    return float(np.sqrt(np.mean(np.square(np.asarray(values, dtype=float)))))


def score(delta_frame, absolute_frame, dispersion_frame) -> dict:
    """One row of the scoreboard: relative rms residual per target and plane."""
    result = {}
    delta_frame = delta_frame.dropna(subset=["model"])
    dispersion_frame = dispersion_frame.dropna(subset=["model"])
    static = absolute_frame[absolute_frame["rf_offset"] == 0.0].dropna(subset=["model"])
    for plane in PLANES:
        for label, frame in (
            ("delta", delta_frame[delta_frame["plane"] == plane]),
            ("static", static[static["plane"] == plane]),
            ("dispersion", dispersion_frame[dispersion_frame["plane"] == plane]),
        ):
            if frame.empty:
                result[f"{label}_{plane}_rel"] = np.nan
                continue
            residual = rms(frame["model"] - frame["measured"])
            measured = rms(frame["measured"])
            result[f"{label}_{plane}_residual"] = residual
            result[f"{label}_{plane}_measured"] = measured
            result[f"{label}_{plane}_model"] = rms(frame["model"])
            result[f"{label}_{plane}_rel"] = residual / measured if measured else np.nan
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=None)
    parser.add_argument("--sequence-file", type=Path,
                        default=DEFAULT_SEQUENCE_FILE)
    parser.add_argument("--output", type=Path, default=None)
    add_campaign_argument(parser)
    add_fit_mode_argument(parser)
    parser.add_argument(
        "--shard",
        default="1/1",
        help=(
            "``i/n``: evaluate only every n-th option, starting at i. Each option "
            "is an independent MAD-NG process, so sharding across a few shells is "
            "the whole of the parallelism -- merge with --merge afterwards."
        ),
    )
    parser.add_argument(
        "--options", nargs="+", default=None,
        help=(
            "Score only these fit directories, plus the start model. Default is "
            "every fit in --matrix. Re-scoring the handful of cases a report page "
            "shows is minutes; the whole matrix is hours."
        ),
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Concatenate the per-shard scoreboards into scoreboard.csv and exit.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    campaign = campaign_by_slug(args.campaign)
    mode = fit_mode_by_slug(args.momentum_mode)
    root = mode.results_root(campaign)
    args.matrix = args.matrix or root
    args.output = args.output or root / "predictions"

    if args.merge:
        shards = sorted(args.output.glob("scoreboard.shard*.csv"))
        merged = pd.concat([pd.read_csv(path) for path in shards], ignore_index=True)
        merged = merged.sort_values("option").drop_duplicates("option")
        merged.to_csv(args.output / "scoreboard.csv", index=False)
        logger.info("Merged %d shards into %d options", len(shards), len(merged))
        return

    index, count = (int(part) for part in args.shard.split("/"))
    # Shards are 1-based. Without this, --shard 0/8 slices [-1::8] and quietly
    # scores exactly one option while looking like it worked.
    if not 1 <= index <= count:
        raise SystemExit(f"--shard i/n needs 1 <= i <= n, got {args.shard}")
    model = build_model(sequence_file=args.sequence_file, campaign=campaign)
    targets = measured_targets(model, campaign)
    runs = sorted(path.parent for path in args.matrix.glob("*/knobs.csv"))
    invalid = [run for run in runs if not result_is_valid(run)]
    runs = [run for run in runs if result_is_valid(run)]
    for run in invalid:
        for suffix in ("delta", "absolute", "dispersion"):
            stale = args.output / f"{run.name}.{suffix}.parquet"
            if stale.exists():
                stale.unlink()
        logger.warning("%s: no accepted optimisation step; excluding result", run.name)
    if args.options:
        wanted = set(args.options)
        runs = [run for run in runs if run.name in wanted]
        missing = wanted - {run.name for run in runs}
        if missing:
            raise SystemExit(f"No fit directory for: {', '.join(sorted(missing))}")
    todo = [None, *runs][index - 1 :: count]
    logger.info("Evaluating %d of %d options (shard %s)", len(todo), len(runs) + 1, args.shard)

    args.output.mkdir(parents=True, exist_ok=True)
    scoreboard = []
    # The start model is the control: what the lattice predicts before any fit.
    for run in todo:
        name = "start-model" if run is None else run.name
        fitted = (
            None if run is None
            else pd.read_csv(run / "knobs.csv").set_index("knob")["value"]
        )

        def open_configured(fitted=fitted):
            interface = open_full_interface(model)
            values = dict.fromkeys(interface.knob_names, 0.0)
            if fitted is not None:
                values.update({k: float(v) for k, v in fitted.items() if k in values})
            interface.update_knob_values(values)
            return interface

        delta_frame, absolute_frame, lost = predict(open_configured, model, targets)
        dispersion_frame = dispersion(absolute_frame)
        delta_frame.to_parquet(args.output / f"{name}.delta.parquet")
        absolute_frame.to_parquet(args.output / f"{name}.absolute.parquet")
        dispersion_frame.to_parquet(args.output / f"{name}.dispersion.parquet")
        row = {"option": name, "unstable_rf_offsets": ",".join(f"{o:+g}" for o in lost)}
        if run is not None:
            row.update(json.loads((run / "summary.json").read_text()))
        row.update(score(delta_frame, absolute_frame, dispersion_frame))
        scoreboard.append(row)
        logger.info(
            "%-28s delta %5.1f%% / %5.1f%%   static %5.1f%% / %5.1f%%   disp %5.1f%% / %5.1f%%",
            name,
            100 * row["delta_x_rel"],
            100 * row["delta_y_rel"],
            100 * row["static_x_rel"],
            100 * row["static_y_rel"],
            100 * row["dispersion_x_rel"],
            100 * row["dispersion_y_rel"],
        )
        if lost:
            logger.warning("%s: no closed orbit at RF %s", name, row["unstable_rf_offsets"])
        pd.DataFrame(scoreboard).to_csv(
            args.output / f"scoreboard.shard{index}of{count}.csv", index=False
        )
    logger.info("Wrote shard %s", args.shard)


if __name__ == "__main__":
    main()
