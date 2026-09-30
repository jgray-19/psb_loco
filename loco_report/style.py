"""Figure style, palette and unit tables. The only definition of each."""

from __future__ import annotations

import re
from dataclasses import dataclass

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

# Wong palette: distinguishable under the common colour-vision deficiencies.
QFO_COLOUR = "#0072B2"
QDE_COLOUR = "#D55E00"
OTHER_COLOUR = "#009E73"
CASE_COLOURS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")
OVERLAY_COLOURS = (*CASE_COLOURS, "#E69F00", "#56B4E9")
START_COLOUR = "0.35"
PREFIT_COLOUR = "0.6"

# k1 = 0.7289 over a 0.5036 m QFO; 2*pi/32 over 32 dipoles.
NOMINAL_K1L = 0.36705
NOMINAL_BEND_ANGLE = 0.19635

# Two panels is the cap; a page-width figure taller than this is unreadable.
MAX_PANELS = 2
FIGURE_WIDTH = 8.0
PANEL_HEIGHT = 2.4


@dataclass(frozen=True)
class Family:
    """One knob family, with every name and scale a figure or table needs."""

    word: str
    unit: str
    axis_label: str
    scale: float


#: Knob suffix -> family. Replaces FAMILY_AXIS, PANELS and FAMILY_UNITS.
FAMILIES: dict[str, Family] = {
    ".dk1l": Family(
        "gradients", "% of nominal $k_1L$",
        "gradient error $\\Delta k_1 L / k_1 L$ [%]", 100 / NOMINAL_K1L,
    ),
    ".dk0l": Family(
        "bends", "% of nominal bend angle",
        "bend error $\\Delta k_0 L / \\theta$ [%]", 100 / NOMINAL_BEND_ANGLE,
    ),
    ".dy": Family("offsets", "mm", "quadrupole offset $dy$ [mm]", 1e3),
    ".tilt": Family("rolls", "mrad", "quadrupole roll [mrad]", 1e3),
    ".dk0sl": Family(
        "skew dipole errors", "mrad",
        "quadrupole skew dipole error $\\Delta k_{0s} L$ [mrad]", 1e3,
    ),
    ".dk1sl": Family(
        "skew gradient errors", "m$^{-1}$",
        "quadrupole skew gradient error $\\Delta k_{1s} L$ [m$^{-1}$]", 1.0,
    ),
}


@dataclass(frozen=True)
class Quantity:
    """One optics quantity: how its rms is taken and how it is written."""

    label: str
    scale: float
    relative: bool
    fmt: str


#: Optics column prefix -> quantity.
QUANTITIES: dict[str, Quantity] = {
    "beta_beating": Quantity("beta-beating [%]", 100.0, True, "{:.1f}%"),
    "phase_error": Quantity("phase error [$2\\pi$]", 1.0, False, "{:.4f}"),
    "dispersion": Quantity("$D$ [m]", 1.0, False, "{:.1f}%"),
    "coupling": Quantity("$|f|$", 1.0, False, "{:.2e}"),
}


def quantity_of(column: str) -> Quantity:
    """The quantity a twiss column belongs to, by its prefix."""
    for prefix, quantity in QUANTITIES.items():
        if column.startswith(prefix):
            return quantity
    raise KeyError(f"No quantity for column {column!r}")


#: The 16 BPMs the scan reads. BR3.BPMT3L1 is in the sequence but unmeasured.
MEASURED_BPM_RE = re.compile(r"^BR3\.BPM\d+L3$")


def bpm_positions(positions: dict[str, float]) -> list[float]:
    """``s`` of the 16 measured BPMs, in order."""
    return sorted(
        s for name, s in positions.items() if MEASURED_BPM_RE.match(name.upper())
    )


def mark_bpms(axis, positions: dict[str, float], *, label: bool = False) -> None:
    """Dashed verticals at the BPMs: where the ring is actually read."""
    for index, s in enumerate(bpm_positions(positions)):
        axis.axvline(
            s, color="0.55", linestyle="--", linewidth=0.7, alpha=0.7, zorder=0,
            label="BPM" if (label and index == 0) else None,
        )


def bar_width(positions: np.ndarray) -> float:
    """psb_md's rule: a third of the tightest spacing, with a floor."""
    if positions.size < 2:
        return 0.35
    spacing = np.diff(np.sort(positions))
    positive = spacing[spacing > 0]
    return max(0.2, 0.35 * float(positive.min())) if positive.size else 0.35


def element_colour(element: str) -> str:
    """QFO blue, QDE orange, anything else green."""
    upper = element.upper()
    if "QFO" in upper:
        return QFO_COLOUR
    if "QDE" in upper:
        return QDE_COLOUR
    return OTHER_COLOUR


def legend_handles(elements) -> list[Patch]:
    """Only the element kinds actually drawn: an absent kind reads as a zero."""
    kinds = {element_colour(element) for element in elements}
    swatches = (
        (QFO_COLOUR, "QFO (focusing)"),
        (QDE_COLOUR, "QDE (defocusing)"),
        (OTHER_COLOUR, "bend"),
    )
    return [Patch(facecolor=c, label=t) for c, t in swatches if c in kinds]


def panels(count: int, *, sharex: bool = True, sharey: bool = False):
    """A page-width figure of at most MAX_PANELS stacked axes."""
    if not 1 <= count <= MAX_PANELS:
        raise ValueError(f"{count} panels; the cap is {MAX_PANELS}")
    figure, axes = plt.subplots(
        count, 1, figsize=(FIGURE_WIDTH, PANEL_HEIGHT * count),
        sharex=sharex, sharey=sharey, constrained_layout=True,
    )
    return figure, np.atleast_1d(axes)


def log_axis(axis, values, *, floor: float = 1e-3) -> None:
    """Log y, so one dominant bar cannot flatten the band of interest."""
    finite = np.asarray([v for v in np.ravel(values) if np.isfinite(v) and v > 0])
    if finite.size == 0:
        return
    axis.set_yscale("log")
    axis.set_ylim(max(floor, 0.5 * finite.min()), 2.0 * finite.max())


def legend_headroom(axis, fraction: float = 0.35) -> None:
    """Grow the top of the y-axis so the legend does not sit on the data."""
    low, high = axis.get_ylim()
    if axis.get_yscale() == "log":
        if low <= 0 or high <= 0:
            return
        span = np.log10(high) - np.log10(low)
        axis.set_ylim(low, 10 ** (np.log10(high) + fraction * span))
        return
    axis.set_ylim(low, high + fraction * (high - low))
