"""Plot the fitted knobs themselves, per element against ``s``, in ``psb_md.plotting``'s house style.

Bars at the element position, QFO/QDE by colour, the fit's own error bars on top.

    uv run python scripts/plot_knobs.py --options xy__k1+b+dy+t__dy32-t32-k1free
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from psb_md.plotting import finalize_figure, style_axis

from loco_common.model import (
    DEFAULT_SEQUENCE_FILE,
    build_model,
    model_element_positions,
)

logger = logging.getLogger(__name__)

#: Wong palette, shared with ``report_cases``; QFO and QDE take the first two slots (element labels are the secondary encoding).
QFO_COLOUR = "#0072B2"
QDE_COLOUR = "#D55E00"
OTHER_COLOUR = "#009E73"
OVERLAY_COLOURS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")

#: Nominal integrated strengths, as ``report_cases``: k1 = 0.7289 over a 0.5036 m QFO, 2*pi/32 per dipole.
NOMINAL_K1L = 0.36705
NOMINAL_BEND_ANGLE = 0.19635

#: One panel per knob family, in stacking order: suffix -> (axis label, scale from raw units).
PANELS: dict[str, tuple[str, float]] = {
    ".dk1l": ("quadrupole $\\Delta k_1 L / k_1 L$ [%]", 100 / NOMINAL_K1L),
    ".dk0l": ("bend $\\Delta k_0 L / \\theta$ [%]", 100 / NOMINAL_BEND_ANGLE),
    ".dy": ("quadrupole $dy$ [mm]", 1e3),
    ".tilt": ("quadrupole tilt [mrad]", 1e3),
}


#: The 16 BPMs the scan reads; ``BR3.BPMT3L1`` is in the sequence but not measured.
MEASURED_BPM_RE = re.compile(r"^BR3\.BPM\d+L3$")


def bpm_positions(positions: dict[str, float]) -> list[float]:
    """``s`` of the 16 measured BPMs, in order (``BR3.BPMT3L1`` excluded)."""
    return sorted(
        s for name, s in positions.items() if MEASURED_BPM_RE.match(name.upper())
    )


def mark_bpms(axis, positions: dict[str, float], *, label: bool = False) -> None:
    """Dashed verticals at the BPMs, behind everything else."""
    for index, s in enumerate(bpm_positions(positions)):
        axis.axvline(
            s, color="0.55", linestyle="--", linewidth=0.7, alpha=0.7, zorder=0,
            label="BPM" if (label and index == 0) else None,
        )


def bar_width(positions: np.ndarray) -> float:
    """``psb_md``'s rule: a third of the tightest spacing, with a floor."""
    if positions.size < 2:
        return 0.35
    spacing = np.diff(np.sort(positions))
    positive = spacing[spacing > 0]
    return max(0.2, 0.35 * float(positive.min())) if positive.size else 0.35


def element_colour(element: str) -> str:
    """QFO blue, QDE orange, anything else green -- the fixed categorical order."""
    upper = element.upper()
    if "QFO" in upper:
        return QFO_COLOUR
    if "QDE" in upper:
        return QDE_COLOUR
    return OTHER_COLOUR


def read_knobs(path: Path, positions: dict[str, float]) -> pd.DataFrame:
    """``knobs.csv`` joined to the element ``s`` from the model sequence (``<element><suffix>`` knob names)."""
    frame = pd.read_csv(path)
    lowered = {name.casefold(): s for name, s in positions.items()}
    rows = []
    for knob, value, uncertainty in frame.itertuples(index=False):
        element, _, suffix = knob.rpartition(".")
        s = lowered.get(element.casefold())
        if s is None:
            continue
        rows.append((element, f".{suffix}", float(s), float(value), float(uncertainty)))
    return pd.DataFrame(rows, columns=["element", "suffix", "s", "value", "uncertainty"])


def figure_knobs_by_s(
    knobs: pd.DataFrame, option: str, output: Path,
    bpm_s: dict[str, float] | None = None,
) -> None:
    """One panel per free family: the fitted value of every magnet against ``s``, with the fit's ``JᵀWJ`` errors."""
    present = [suffix for suffix in PANELS if (knobs["suffix"] == suffix).any()]
    if not present:
        logger.warning("%s: no plottable knob families", option)
        return
    figure, axes = plt.subplots(
        len(present), 1, sharex=True, constrained_layout=True,
        figsize=(14, max(2.8 * len(present), 4.6)),
        squeeze=False,
    )
    for axis, suffix in zip(axes[:, 0], present, strict=True):
        block = knobs[knobs["suffix"] == suffix].sort_values("s")
        label, scale = PANELS[suffix]
        values = scale * block["value"].to_numpy()
        errors = scale * block["uncertainty"].to_numpy()
        positions = block["s"].to_numpy()
        colours = [element_colour(e) for e in block["element"]]

        if bpm_s is not None:
            mark_bpms(axis, bpm_s)
        axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
        axis.bar(positions, values, width=bar_width(positions), color=colours, alpha=0.85)
        axis.errorbar(positions, values, yerr=errors, fmt="none", ecolor="black",
                      elinewidth=0.9, capsize=2.0)
        axis.set_ylabel(label, fontsize=9)
        style_axis(axis)
    axes[-1, 0].set_xlabel("s [m]")
    axes[0, 0].legend(
        handles=[
            Patch(facecolor=QFO_COLOUR, label="QFO (focusing)"),
            Patch(facecolor=QDE_COLOUR, label="QDE (defocusing)"),
            Patch(facecolor=OTHER_COLOUR, label="bend"),
        ],
        fontsize=8, ncols=3, loc="upper left",
    )
    figure.suptitle(f"Fitted knobs around the ring — {option}", fontsize=12)
    finalize_figure(figure, output / f"knobs_by_s_{option}.png")


def figure_knob_overlay(
    matrix: Path, options: list[str], suffix: str, positions: dict[str, float],
    output: Path,
) -> None:
    """One family, every option overlaid element by element."""
    label, scale = PANELS[suffix]
    figure, axis = plt.subplots(figsize=(14, 5.0), constrained_layout=True)
    mark_bpms(axis, positions, label=True)
    drawn = 0
    for option, colour in zip(options, OVERLAY_COLOURS, strict=False):
        path = matrix / option / "knobs.csv"
        if not path.exists():
            continue
        block = read_knobs(path, positions)
        block = block[block["suffix"] == suffix].sort_values("s")
        if block.empty:
            continue
        axis.step(block["s"], scale * block["value"], where="mid", color=colour,
                  linewidth=2.0, alpha=0.9, label=option)
        drawn += 1
    if not drawn:
        plt.close(figure)
        return
    axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
    axis.set_xlabel("s [m]")
    axis.set_ylabel(label)
    axis.set_title(f"{label} per magnet, option by option", fontsize=11)
    style_axis(axis)
    axis.legend(fontsize=7, ncols=2)
    finalize_figure(figure, output / f"knobs_overlay_{suffix.lstrip('.')}.png")


def figure_tilt_vs_dispersion(
    matrix: Path, predictions: Path, option: str, positions: dict[str, float],
    output: Path,
) -> None:
    """Fitted tilt against vertical dispersion (``docs/studies/quadrupole-roll.md``)."""
    knobs_path = matrix / option / "knobs.csv"
    dispersion_path = predictions / f"{option}.dispersion.parquet"
    if not knobs_path.exists() or not dispersion_path.exists():
        logger.warning("%s: no tilt/dispersion pair to plot", option)
        return
    tilt = read_knobs(knobs_path, positions)
    tilt = tilt[tilt["suffix"] == ".tilt"].sort_values("s")
    if tilt.empty:
        logger.info("%s: no tilt knobs, skipping", option)
        return
    frame = pd.read_parquet(dispersion_path)
    vertical = frame[frame["plane"] == "y"]

    figure, axes = plt.subplots(2, 1, figsize=(14, 7.0), constrained_layout=True)
    axis = axes[0]
    mark_bpms(axis, positions, label=True)
    axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
    axis.bar(tilt["s"], 1e3 * tilt["value"], width=bar_width(tilt["s"].to_numpy()),
             color=[element_colour(e) for e in tilt["element"]], alpha=0.85)
    axis.set_ylabel("fitted tilt [mrad]")
    axis.set_title(f"Fitted quadrupole roll and the vertical dispersion it has to "
                   f"explain — {option}", fontsize=11)
    axis.legend(handles=[Patch(facecolor=QFO_COLOUR, label="QFO"),
                         Patch(facecolor=QDE_COLOUR, label="QDE")],
                fontsize=8, ncols=2, loc="upper left")
    style_axis(axis)

    axis = axes[1]
    index = np.arange(len(vertical))
    axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
    axis.plot(index, vertical["measured"], marker="o", markersize=5,
              color=OVERLAY_COLOURS[0], linewidth=2.0, label="measured")
    axis.plot(index, vertical["model"], marker="s", markersize=5,
              color=OVERLAY_COLOURS[1], linewidth=2.0, label="model")
    axis.set_xticks(index, vertical["bpm"], rotation=90, fontsize=6)
    axis.set_ylabel("$D_y$ [m]")
    axis.legend(fontsize=8)
    style_axis(axis)
    finalize_figure(figure, output / f"tilt_vs_dispersion_{option}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=Path("results/matrix"))
    parser.add_argument("--predictions", type=Path,
                        default=Path("results/matrix/predictions"))
    parser.add_argument("--output", type=Path, default=Path("results/matrix/figures"))
    parser.add_argument("--sequence-file", type=Path,
                        default=DEFAULT_SEQUENCE_FILE)
    parser.add_argument("--options", nargs="+", default=None,
                        help="Options to draw; default is every fitted directory.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    positions = model_element_positions(build_model(sequence_file=args.sequence_file))
    options = args.options or sorted(
        path.parent.name for path in args.matrix.glob("*/knobs.csv")
    )
    args.output.mkdir(parents=True, exist_ok=True)

    for option in options:
        knobs = read_knobs(args.matrix / option / "knobs.csv", positions)
        figure_knobs_by_s(knobs, option, args.output, positions)
        figure_tilt_vs_dispersion(args.matrix, args.predictions, option, positions,
                                  args.output)
    for suffix in PANELS:
        figure_knob_overlay(args.matrix, options, suffix, positions, args.output)
    logger.info("Wrote knob figures for %d option(s) to %s", len(options), args.output)


if __name__ == "__main__":
    main()
