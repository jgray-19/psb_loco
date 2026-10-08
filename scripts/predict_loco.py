"""Evaluate every fitted LOCO option on one common set of predictions.

Each option fits a different target, so fit losses are not comparable; every
result directory is scored on the same three targets:

1. **Delta orbits.** The 48 corrector trims at nominal RF, reference removed.
2. **Static closed orbit.** The untrimmed orbit in both planes.
3. **Dispersion.** Slope of the untrimmed orbit against ``pt`` over the five RF settings.

Every model is stood up identically: all knob families created (absent knobs set
to zero), the machine's corrector settings standing, trims applied through the MAD-X global.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from adelmo.machine.accelerators.psb import PSB as OptimiserPSB
from adelmo.machine.mad.optimising_mad_interface import GradientDescentMadInterface
from adelmo.machine.mad.machine_state import merge_machine_states
from tmom_recon.physics.closed_orbit import fit_dispersion, measure_dispersion

from loco_common.campaign import Campaign, add_campaign_argument, campaign_by_slug
from loco_common.case_names import parse_case
from loco_common.fit_mode import (
    add_fit_mode_argument,
    fit_mode_by_slug,
    result_is_valid,
)
from loco_common.measured_response import (
    average_orbit_frames,
    cached_scan,
    measured_orbits,
)
from loco_common.model import DEFAULT_SEQUENCE_FILE, build_model, model_twiss
from loco_common.momentum import chroma_pt_by_rf_offset, chroma_pt_error_by_rf_offset
from loco_common.naming import lsa_to_element
from poco.settings import trim_settings

logger = logging.getLogger(__name__)

PLANES = ("x", "y")
#: Measured-frame column per plane; the model's twiss columns are lowercase.
MEASURED_COLUMN = {"x": "X", "y": "Y"}
#: The measurement's error bar: standard error of the mean over turns and bunches, propagated through the reference subtraction.
MEASURED_ERROR_COLUMN = {"x": "ERRX", "y": "ERRY"}


def measured_targets(model, campaign: Campaign):
    """The three common targets, in metres, indexed by BPM.

    Returns ``(deltas, absolute, pt, measured_dispersion_error)``: trim -> delta orbit,
    RF offset -> untrimmed orbit, RF offset -> ``pt``, and the one-sigma on the measured
    dispersion slope indexed by ``(plane, bpm)``.
    """
    points, orbit_by_path = cached_scan(campaign=campaign)
    absolute = {}
    raw_by_offset: dict[float, list[pd.DataFrame]] = {}
    for offset in campaign.rf_offsets:
        untrimmed = {
            key: frame
            for key, frame in measured_orbits(
                offset, points=points, orbit_by_path=orbit_by_path, delta=False
            ).items()
            if key[1] == 0.0
        }
        # Not sum/len: that would average ERRX/ERRY instead of dividing by sqrt(N).
        raw_by_offset[offset] = list(untrimmed.values())
        absolute[offset] = average_orbit_frames(raw_by_offset[offset])
    # Chroma calibration: independent of model dispersion and carries its own uncertainty.
    momentum_accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
    )
    pt = chroma_pt_by_rf_offset(
        campaign.chroma_file, sorted(absolute), momentum_accelerator
    )
    pt_error = chroma_pt_error_by_rf_offset(
        campaign.chroma_file, sorted(absolute), momentum_accelerator
    )
    measured_dispersion_error = measured_dispersion_uncertainty(
        raw_by_offset, pt, pt_error, model_twiss(model, chrom=True)
    )
    # Trims are applied as nominal + dk on the machine's corrector values.
    deltas = trim_settings(
        measured_orbits(0.0, points=points, orbit_by_path=orbit_by_path)
    )
    return deltas, absolute, pt, measured_dispersion_error


def measured_dispersion_uncertainty(
    raw_by_offset: dict[float, list[pd.DataFrame]],
    pt: dict[float, float],
    pt_error: dict[float, float],
    tws: pd.DataFrame,
) -> pd.DataFrame:
    """One-sigma on the measured dispersion slope, via ``tmom_recon.physics.closed_orbit.measure_dispersion``.

    Orbit scatter comes from the repeat untrimmed acquisitions in *raw_by_offset*,
    momentum scatter from *pt_error*. *tws* is the ``pt = 0`` twiss with
    ``chrom=True``; its ``ddx``/``ddy`` are removed before the slope fit.

    Returns one row per ``(plane, bpm)`` with a ``measured_error`` column.
    """
    orbits_by_pt: dict[float, list[pd.DataFrame]] = {}
    pt_sigma: dict[float, float] = {}
    for offset, frames in raw_by_offset.items():
        orbits_by_pt[pt[offset]] = [
            pd.DataFrame({"name": frame.index, "x": frame["X"], "y": frame["Y"]})
            for frame in frames
        ]
        pt_sigma[pt[offset]] = pt_error[offset]
    result = measure_dispersion(orbits_by_pt, pt_sigma, tws=tws)
    rows = []
    for plane, error_column in (("x", "dx_err"), ("y", "dy_err")):
        rows.append(
            pd.DataFrame(
                {
                    "plane": plane,
                    "bpm": result.index,
                    "measured_error": result[error_column].to_numpy(),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def open_full_interface(model):
    """One interface carrying every knob family, on the machine's correctors.

    Every family is created so a frozen one enters as zero; a missing one would silently go unapplied.
    """
    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=str(model.sequence_file),
        kinetic_energy=model.kinetic_energy,
        errors={"quad": {"k1", "k0s", "k1s"}, "bend": {"k0"}},
        misalignments={"quad": {"dy", "tilt"}},
    )
    return GradientDescentMadInterface(
        accelerator=accelerator,
        machine_state=merge_machine_states(model.corrector_knobs, model.tune_knobs) or None,
    )


def orbit_at(interface, pt: float = 0.0, *, high_order: bool = False) -> pd.DataFrame:
    """Closed orbit at the observed BPMs, in metres, at momentum ``pt``.

    ``high_order`` selects the order-8, 2-slice integrator instead of ``method=6``;
    each branch is a literal call so ``tests/test_production_optics_conventions.py`` can pin both.
    """
    if high_order:
        twiss = interface.run_twiss(observe=1, pt=pt, method=8, nslice=2)
    else:
        twiss = interface.run_twiss(observe=1, pt=pt, method=6)
    return pd.DataFrame(
        {"x": twiss["x"].astype(float), "y": twiss["y"].astype(float)}, index=twiss.index
    )


def corrector_value(interface, standing: dict[str, float], knob: str) -> float:
    """The corrector's standing value, else the one the MAD environment holds for it."""
    if knob in standing:
        return standing[knob]
    from adelmo.machine.mad.machine_state import read_state

    return read_state(interface.mad, interface.py_name, [knob])[knob]


def set_corrector(interface, knob: str, value: float) -> None:
    """Set a corrector's MAD-X global, the same deferral the sequence uses."""
    interface.mad.send(f"MADX['{knob}'] = {value:.15e}")


def predict(open_interface, model, targets, *, high_order: bool = False, gains: pd.Series | None = None):
    """Model predictions for the three common targets, aligned to the BPMs.

    *open_interface* is a factory: a lattice can fail to close off-momentum and MAD-NG is
    unreliable after an error, so each off-momentum point gets a fresh process and a failure becomes ``NaN``.
    ``high_order`` is passed to :func:`orbit_at`. *gains* (a fit's ``gains.csv``) scales each delta-orbit kick by
    ``1 + corrgain`` and each BPM reading by ``1 + bpmgain``; the closed and dispersion orbits are not scaled, as the fit did not use them.
    """
    gains = gains if gains is not None else pd.Series(dtype=float)
    deltas, absolute, pt, _measured_dispersion_error = targets
    standing = dict(model.corrector_knobs)
    interface = open_interface()
    for knob, value in standing.items():
        set_corrector(interface, knob, value)

    nominal = {0.0: orbit_at(interface, pt[0.0], high_order=high_order)}
    lost = []

    delta_rows = []
    for setting in deltas:
        base = corrector_value(interface, standing, setting.knob)
        kick = setting.dk * (1.0 + gains.get(f"corrgain.{lsa_to_element(setting.corrector).split('.', 1)[1]}", 0.0))
        set_corrector(interface, setting.knob, base + kick)
        kicked = orbit_at(interface, high_order=high_order)
        set_corrector(interface, setting.knob, base)
        difference = kicked - nominal[0.0]
        target = setting.orbit
        common = difference.index.intersection(target.index)
        for plane in PLANES:
            bpm_gain = np.array([gains.get(f"bpmgain.{plane}.{bpm}", 0.0) for bpm in common])
            delta_rows.append(
                pd.DataFrame(
                    {
                        "corrector": setting.corrector,
                        "offset_k": setting.offset_k,
                        "plane": plane,
                        "bpm": common,
                        "model": (1.0 + bpm_gain) * difference.loc[common, plane].to_numpy(),
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
            nominal[offset] = orbit_at(interface, pt[offset], high_order=high_order)
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
    # Shards are 1-based; --shard 0/8 would slice [-1::8].
    if not 1 <= index <= count:
        raise SystemExit(f"--shard i/n needs 1 <= i <= n, got {args.shard}")
    model = build_model(sequence_file=args.sequence_file, campaign=campaign)
    targets = measured_targets(model, campaign)
    measured_dispersion_error = targets[3]
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

        # Only the skew-multipole families use the order-8 integrator.
        high_order = bool({"k0s", "k1s"} & set(parse_case(name).family_list))
        gain_file = None if run is None else run / "gains.csv"
        gains = (
            pd.read_csv(gain_file).set_index("parameter")["value"]
            if gain_file is not None and gain_file.exists()
            else None
        )
        delta_frame, absolute_frame, lost = predict(
            open_configured, model, targets, high_order=high_order, gains=gains
        )
        dispersion_frame = dispersion(absolute_frame).merge(
            measured_dispersion_error, on=["plane", "bpm"], how="left"
        )
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
