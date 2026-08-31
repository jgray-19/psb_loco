"""The figure set behind each report page: one section per case, same plots.

The option matrix this replaces put every fit in one 37-row scoreboard keyed by
its directory name. That is an index, not a study -- it can tell you which row
has the smallest residual and nothing about what any of them did to the machine.

Here a page is a couple of options and every one gets the same four questions
asked of it, so the sections are comparable by construction:

1. what gradients the fit asked for, magnet by magnet, with its own error bars;
2. what rolls it asked for, and whether they are larger than their bars;
3. what it did to the lattice -- beta-beating, phase, dispersion along ``s``;
4. what it left behind -- the residual against every measurement it was scored
   on, on the same page as the case that produced it.

No figure carries a directory slug. Titles, legends and axis ticks all come
from :mod:`loco_common.case_names`, which is the only place the two namings meet.

    uv run python scripts/report_cases.py                 # every page
    uv run python scripts/report_cases.py --page delta
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from psb_md.plotting import finalize_figure, style_axis

from loco_common.campaign import (
    add_campaign_argument,
    campaign_by_slug,
)
from loco_common.case_names import (
    ALL_PAGES,
    LOCO_OPTICS_CASE,
    LOCO_OPTICS_FITS,
    LOCO_OPTICS_MODE,
    PAGE_BY_SLUG,
    PAGES,
    PER_MAGNET_PAGE,
    Page,
    case_heading,
)
from loco_common.fit_mode import (
    add_fit_mode_argument,
    fit_mode_by_slug,
    result_is_valid,
)
from loco_common.model import (
    DEFAULT_SEQUENCE_FILE,
    build_model,
    model_element_positions,
)
from scripts.plot_knobs import (
    NOMINAL_BEND_ANGLE,
    NOMINAL_K1L,
    OTHER_COLOUR,
    OVERLAY_COLOURS,
    QDE_COLOUR,
    QFO_COLOUR,
    bar_width,
    element_colour,
    mark_bpms,
    read_knobs,
)

logger = logging.getLogger(__name__)

#: Wong palette; one colour per case, in page order. Four cases, four colours,
#: and the pairing is fixed across every figure on a page so a reader learns it
#: once.
CASE_COLOURS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")

#: Knob family -> (axis label, scale from raw units to the plotted ones).
FAMILY_AXIS = {
    ".dk1l": ("gradient error $\\Delta k_1 L / k_1 L$ [%]", 100 / NOMINAL_K1L),
    ".dk0l": ("bend error $\\Delta k_0 L / \\theta$ [%]", 100 / NOMINAL_BEND_ANGLE),
    ".dy": ("quadrupole offset $dy$ [mm]", 1e3),
    ".tilt": ("quadrupole roll [mrad]", 1e3),
}

#: The measured quantities every case is scored against, as (file, axis label).
#: ``delta`` is the corrector response; ``absolute`` is the machine's own closed
#: orbit at each RF setting, which only an absolute-plane fit sees.
RESIDUAL_TARGETS = {
    "delta": "delta-orbit residual [mm]",
    "absolute": "closed-orbit residual [mm]",
}

#: The BPM zero-offset systematic, in metres -- ``run_method2``'s
#: ``--absolute-error-floor`` default. The statistical bar on a measured orbit
#: is a standard error of the mean and comes out around a micron; what actually
#: limits how well an absolute orbit is known is this, two orders of magnitude
#: larger, so it is the line a closed-orbit residual should be read against.
BPM_ZERO_OFFSET = 1e-4


def _legend_handles(elements) -> list[Patch]:
    """Only the element kinds actually drawn.

    A page with no free bends must not carry a "bend" swatch: a legend entry for
    something absent reads as something that was there and came out at zero.
    """
    kinds = {element_colour(element) for element in elements}
    handles = [
        (QFO_COLOUR, "QFO (focusing)"),
        (QDE_COLOUR, "QDE (defocusing)"),
        (OTHER_COLOUR, "bend"),
    ]
    return [Patch(facecolor=colour, label=label) for colour, label in handles
            if colour in kinds]


def figure_family_by_s(
    page: Page, suffix: str, matrix: Path, positions: dict[str, float], output: Path
) -> None:
    """Every magnet's fitted strength against ``s``, one panel per case.

    The panels share both axes, which is the whole point: the lumped case's bars
    sit at the same heights as the per-magnet case's wherever the lumping cost
    nothing, and visibly do not wherever it did. A lumped family shows as
    neighbouring bars at identical height -- worth being able to see rather than
    take on trust.

    Error bars are the fit's own. For a lumped fit they are the bars of the
    *group*, from the reduced normal matrix, so each magnet in a group carries
    the uncertainty of the quantity that was actually determined.
    """
    blocks = {}
    for slug in page.cases:
        path = matrix / slug / "knobs.csv"
        if not path.exists():
            continue
        block = read_knobs(path, positions)
        block = block[block["suffix"] == suffix].sort_values("s")
        if not block.empty:
            blocks[slug] = block
    if not blocks:
        logger.info("%s: no %s knobs on this page", page.slug, suffix)
        return

    label, scale = FAMILY_AXIS[suffix]
    figure, axes = plt.subplots(
        len(blocks), 1, sharex=True, sharey=True, constrained_layout=True,
        figsize=(14, max(2.6 * len(blocks), 5.0)), squeeze=False,
    )
    for axis, (slug, block) in zip(axes[:, 0], blocks.items(), strict=True):
        s = block["s"].to_numpy()
        mark_bpms(axis, positions)
        axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
        axis.bar(s, scale * block["value"].to_numpy(), width=bar_width(s),
                 color=[element_colour(e) for e in block["element"]], alpha=0.85)
        axis.errorbar(s, scale * block["value"].to_numpy(),
                      yerr=scale * block["uncertainty"].to_numpy(),
                      fmt="none", ecolor="black", elinewidth=0.9, capsize=2.0)
        axis.set_ylabel(label, fontsize=8)
        axis.set_title(page.label(slug), fontsize=9, loc="left")
        style_axis(axis)
    axes[-1, 0].set_xlabel("s [m]")
    axes[0, 0].legend(
        handles=[
            *_legend_handles(pd.concat(blocks.values())["element"]),
            Line2D([], [], color="0.55", linestyle="--", linewidth=0.7, label="BPM"),
        ],
        fontsize=8, ncols=4, loc="upper left",
    )
    figure.suptitle(
        f"{label.split(' [')[0]} per magnet — {page.title.lower()}", fontsize=12
    )
    finalize_figure(figure, output / f"{page.slug}_{suffix.lstrip('.')}_by_s.png")


def figure_family_significance(
    page: Page, suffix: str, matrix: Path, positions: dict[str, float], output: Path
) -> None:
    """The same family again, as ``|value| / sigma``: is the number a measurement?

    A fit always produces a number. This says whether the data produced it. Below
    1 the typical fitted value is smaller than its own error bar, which is the
    fit decorating rather than measuring, and no residual improvement rescues it.
    """
    blocks = {}
    for slug in page.cases:
        path = matrix / slug / "knobs.csv"
        if not path.exists():
            continue
        block = read_knobs(path, positions)
        block = block[block["suffix"] == suffix].sort_values("s")
        # Method 1 comes off MAD.match, which reports no covariance, so its
        # knobs carry a zero uncertainty rather than a small one. There is no
        # significance to plot for it, and a legend entry with no curve under it
        # would read as a fit whose knobs all came out at zero.
        if not block.empty and (block["uncertainty"].to_numpy() > 0).any():
            blocks[slug] = block
    if not blocks:
        return

    label, _ = FAMILY_AXIS[suffix]
    figure, axis = plt.subplots(figsize=(14, 5.0), constrained_layout=True)
    mark_bpms(axis, positions, label=True)
    for (slug, block), colour in zip(blocks.items(), CASE_COLOURS, strict=False):
        significance = np.abs(block["value"].to_numpy()) / np.where(
            block["uncertainty"].to_numpy() > 0, block["uncertainty"].to_numpy(), np.nan
        )
        axis.step(block["s"], significance, where="mid", color=colour,
                  linewidth=1.9, alpha=0.9, label=page.label(slug))
    axis.axhline(1.0, color="k", linestyle="--", linewidth=1.0,
                 label="value equals its own error bar")
    axis.set_yscale("log")
    axis.set_xlabel("s [m]")
    axis.set_ylabel(f"|{label.split(' [')[0]}| / $\\sigma$")
    axis.set_title(
        f"How well each magnet's {label.split(' [')[0].lower()} is determined",
        fontsize=11,
    )
    style_axis(axis)
    axis.legend(fontsize=7, ncols=2)
    finalize_figure(figure, output / f"{page.slug}_{suffix.lstrip('.')}_significance.png")


def _rereferenced(frame: pd.DataFrame, start: pd.DataFrame,
                  model: pd.DataFrame) -> pd.DataFrame:
    """One case's cached optics, differenced against *model* instead of *start*.

    The cache holds the fitted beta outright and the phase only as
    ``mu_fit - mu_start``, so the fitted phase is put back together before the
    new reference is subtracted. Both twisses are the same 499-element list off
    the same sequence, so this is element-by-element with no interpolation.

    Dispersion and coupling are the fitted lattice's own and do not move; only
    the reference curves drawn under them do.
    """
    aligned = frame.set_index("element")
    reference = model.reindex(aligned.index)
    origin = start.reindex(aligned.index)
    out = aligned.copy()
    for plane, beta, mu in (("x", "beta11", "mu1"), ("y", "beta22", "mu2")):
        out[f"beta_beating_{plane}"] = (
            aligned[f"beta_{plane}"].to_numpy() / reference[beta].to_numpy() - 1.0
        )
        fitted_mu = aligned[f"phase_error_{plane}"].to_numpy() + origin[mu].to_numpy()
        out[f"phase_error_{plane}"] = fitted_mu - reference[mu].to_numpy()
        out[f"dispersion_{plane}_start"] = reference[f"d{plane}"].to_numpy()
    for rdt in ("f1001", "f1010"):
        if f"coupling_{rdt}_start" in out.columns and rdt in reference.columns:
            out[f"coupling_{rdt}_start"] = reference[rdt].to_numpy()
    return out.reset_index()


#: The two reference models a page's lattice figure puts the measured points
#: against, as (summary key, file-name suffix). Same pair as
#: :data:`MEASURED_REFERENCES`, named for the page figures rather than the
#: measured-optics ones.
PAGE_OPTICS_REFERENCES = (("loco_model", ""), ("matched_model", "_matched"))


def figure_optics(page: Page, optics_dir: Path, predictions_dir: Path,
                  positions: dict[str, float], output: Path, campaign=None) -> None:
    """What each fit did to the lattice: beta-beating, phase and dispersion.

    Everything is against the start model, element by element off the same twiss
    element list. The phase panel keeps the ring-wide slope: a fit that moves the
    tune moves every downstream phase with it, and flattening that out would hide
    the tune change it represents.

    Dispersion is plotted as the fitted lattice's own ``dx``/``dy``, with the
    start model's underneath. The last two panels are the coupling RDTs the
    same way: ``|f1001|`` and ``|f1010|`` of the fitted lattice, the reference
    lattice's underneath, and omc3's measured amplitudes on top. Only a fit
    given tilts can move them, which is the point of drawing them beside a fit
    that was not. MAD-NG is ``pt``-based throughout, so these columns
    are ``dx/dpt`` already and nothing is rescaled.

    The **measured** beta-beating rides on the two beating panels, at the BPMs,
    from phase (filled) and from amplitude (open). The measured dispersion rides
    on the two dispersion panels. It is not taken from a twiss convention: it is
    the slope of each BPM's five measured untrimmed closed orbits against the
    reconstructed ``pt``, cached by :mod:`scripts.predict_loco`. A fit that has
    found the machine's gradient error should run through the points.

    Two figures, one per reference model, because every panel here is a
    difference and has to be against something. ``_optics.png`` differences
    everything -- curves and measured points alike -- against the lattice on the
    ``k1`` sent to the magnets, which is the lattice the fits started from.
    ``_optics_matched.png`` differences the same fitted lattices against the
    same sequence with ``kbrqf``/``kbrqd`` matched to the measured tune, so the
    phase panels carry only the tune each *fit* moved and not the 0.07 / 0.11
    the un-matched start model is away from the machine.

    The re-referencing is arithmetic on the cached twisses, not a new fit: the
    fitted beta and phase are recovered from the cache, and the matched
    lattice's own twiss comes from ``matched-model.twiss.parquet``, which
    :mod:`scripts.case_optics` writes beside the start model's.
    """
    frames = {}
    for slug in page.cases:
        path = optics_dir / f"{slug}.optics.parquet"
        if path.exists():
            frames[slug] = pd.read_parquet(path)
    if not frames:
        logger.warning("%s: no cached optics; run scripts/case_optics.py", page.slug)
        return

    rows = (
        ("beta_beating_x", "horizontal beta-beating [%]", 100.0),
        ("beta_beating_y", "vertical beta-beating [%]", 100.0),
        ("phase_error_x", "horizontal phase error [$2\\pi$]", 1.0),
        ("phase_error_y", "vertical phase error [$2\\pi$]", 1.0),
        ("dispersion_x", "$D_x$ [m]", 1.0),
        ("dispersion_y", "$D_y$ [m]", 1.0),
        ("coupling_f1001", "$|f_{1001}|$", 1.0),
        ("coupling_f1010", "$|f_{1010}|$", 1.0),
    )
    measured = measured_optics_frame(campaign, positions) if campaign else None
    measured_dispersion = measured_dispersion_frame(predictions_dir, positions)
    summary = optics_summary(campaign) if campaign else {}
    models = {
        name: pd.read_parquet(optics_dir / f"{name}.twiss.parquet")
        for name in ("start-model", "matched-model")
        if (optics_dir / f"{name}.twiss.parquet").exists()
    }

    for reference, suffix in PAGE_OPTICS_REFERENCES:
        if measured is not None and f"beat_x_{reference}" not in measured.columns:
            continue
        drawn = frames
        prefit = None
        if reference == "matched_model":
            if not {"start-model", "matched-model"} <= set(models):
                logger.warning(
                    "%s: no matched-model twiss; run "
                    "`scripts/case_optics.py --models-only`", page.slug
                )
                continue
            drawn = {
                slug: _rereferenced(frame, models["start-model"],
                                    models["matched-model"])
                for slug, frame in frames.items()
            }
            prefit = _prefit_vs_matched(models["start-model"], models["matched-model"])
        start_frame = next(iter(drawn.values()))
        figure, axes = plt.subplots(
            len(rows), 1, sharex=True, constrained_layout=True,
            figsize=(14, 2.5 * len(rows))
        )
        for axis, (column, label, scale) in zip(axes, rows, strict=True):
            mark_bpms(axis, positions, label=column == rows[0][0])
            axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
            # Every panel's own rms convention: beta-beating and dispersion are
            # relative (Delta over the reference the curve is against), phase
            # error is absolute -- there is no natural quantity to divide it by.
            # Beta-beating and dispersion are relative to the reference they
            # are drawn against; phase and the coupling RDTs have nothing
            # natural to divide by, so their rms stays in its own units.
            relative = column.startswith(("beta_beating", "dispersion"))
            plane = column[-1] if column[-1] in "xy" else ""
            measured_beat = (
                measured[f"beat_{plane}_{reference}"]
                if measured is not None and f"beat_{plane}_{reference}" in measured.columns
                else None
            )
            if measured is not None and column.startswith("beta_beating"):
                for beat, beta, marker, style, name in (
                    (f"beat_{plane}_{reference}", f"beta_{plane}", "o", {},
                     "measured, from phase"),
                    (f"beat_{plane}_amp_{reference}", f"beta_{plane}_amp", "^",
                     {"markerfacecolor": "none"}, "measured, from amplitude"),
                ):
                    if beat in measured.columns:
                        label_rms = 100 * _rms(measured[beat].to_numpy())
                        axis.errorbar(
                            measured["s"], 100 * measured[beat],
                            yerr=_beat_error(measured, beta,
                                             f"beta_{plane}_{reference}"),
                            fmt=marker, color="k", markersize=6, zorder=4,
                            elinewidth=0.9, capsize=2.0,
                            label=f"{name} (AC dipole), rms {label_rms:.1f}%",
                            **style,
                        )
            if column.startswith("coupling"):
                rdt = column.removeprefix("coupling_")
                start = f"{column}_start"
                ref_label = "matched model" if reference == "matched_model" else "start model"
                if start in start_frame.columns:
                    axis.plot(start_frame["s"], start_frame[start], color="0.35",
                              linewidth=2.4, linestyle="--", label=ref_label, zorder=1)
                # The measured RDT is omc3's own, amplitude only: the sign
                # convention of the phase is not shared with MAD-NG's and a
                # comparison of the two would be a comparison of conventions.
                if measured is not None and rdt in measured.columns:
                    axis.errorbar(
                        measured["s"], measured[rdt],
                        yerr=measured.get(f"{rdt}_err"), fmt="o", color="k",
                        markersize=5, zorder=4, elinewidth=0.9, capsize=2.0,
                        label=f"measured (AC dipole), rms {_rms(measured[rdt]):.2e}",
                    )
            if column.startswith("dispersion"):
                start = f"{column}_start"
                ref_label = "matched model" if reference == "matched_model" else "start model"
                axis.plot(start_frame["s"], start_frame[start], color="0.35",
                          linewidth=2.4, linestyle="--", label=ref_label, zorder=1)
                points = measured_dispersion[
                    measured_dispersion["plane"] == plane
                ]
                if not points.empty:
                    prefit_rms = _rms_vs_measured_dispersion(
                        start_frame["element"].to_numpy(), start_frame[start].to_numpy(),
                        measured_dispersion, plane,
                    )
                    suffix_rms = f", pre-fit rms {prefit_rms:.1f}%" if prefit_rms is not None else ""
                    axis.errorbar(
                        points["s"], points["measured"],
                        yerr=points.get("uncertainty"), fmt="o", color="k",
                        markersize=5, zorder=4, elinewidth=0.9, capsize=2.0,
                        label=f"measured, from momentum closed orbits{suffix_rms}",
                    )
            if prefit is not None and column in prefit:
                pre_s, pre_values = prefit[column]
                pre_elements = prefit["_elements"][1]
                if column.startswith("dispersion"):
                    pre_rms = _rms_vs_measured_dispersion(
                        pre_elements, pre_values, measured_dispersion, plane
                    )
                    pre_text = f"{pre_rms:.1f}%" if pre_rms is not None else "n/a"
                elif column.startswith("coupling"):
                    pre_rms = _rms_vs_measured(
                        pre_elements, pre_values, _measured_rdt(measured, column),
                        relative=False,
                    )
                    pre_text = f"{pre_rms:.2e}" if pre_rms is not None else "n/a"
                elif column.startswith("beta_beating"):
                    pre_rms = _rms_vs_measured(pre_elements, pre_values, measured_beat, relative=relative)
                    pre_text = f"{pre_rms:.1f}%" if pre_rms is not None else "n/a"
                else:
                    pre_rms = 100 * _rms(pre_values) if relative else _rms(pre_values)
                    pre_text = f"{pre_rms:.1f}%" if relative else f"{pre_rms:.4f}"
                axis.plot(pre_s, scale * pre_values, color="0.6", linewidth=2.0,
                          linestyle=":", label=f"pre-fit model, rms {pre_text}", zorder=2)
            for (slug, frame), colour in zip(drawn.items(), CASE_COLOURS, strict=False):
                values = frame[column].to_numpy()
                if column.startswith("dispersion"):
                    case_rms = _rms_vs_measured_dispersion(
                        frame["element"].to_numpy(), values, measured_dispersion, plane
                    )
                    case_text = f"{case_rms:.1f}%" if case_rms is not None else "n/a"
                elif column.startswith("coupling"):
                    case_rms = _rms_vs_measured(
                        frame["element"].to_numpy(), values,
                        _measured_rdt(measured, column), relative=False,
                    )
                    case_text = f"{case_rms:.2e}" if case_rms is not None else "n/a"
                elif column.startswith("beta_beating"):
                    case_rms = _rms_vs_measured(frame["element"].to_numpy(), values, measured_beat, relative=relative)
                    case_text = f"{case_rms:.1f}%" if case_rms is not None else "n/a"
                else:
                    case_rms = 100 * _rms(values) if relative else _rms(values)
                    case_text = f"{case_rms:.1f}%" if relative else f"{case_rms:.4f}"
                axis.plot(frame["s"], scale * values, color=colour,
                          linewidth=1.5, alpha=0.9,
                          label=f"{page.label(slug)}, rms {case_text}")
            axis.set_ylabel(label, fontsize=9)
            style_axis(axis)
        axes[-1].set_xlabel("s [m]")
        axes[0].legend(fontsize=7, ncols=2, loc="upper left")
        axes[-2].legend(fontsize=7, ncols=2, loc="upper left")
        caption = _tune_caption(summary, reference) if campaign else ""
        against = (
            "the tune-matched model" if reference == "matched_model"
            else "the start model the fits began from"
        )
        figure.suptitle(
            f"What each fit did to the lattice, against {against} — "
            f"{page.title.lower()}" + (f"\n{caption}" if caption else ""),
            fontsize=12,
        )
        finalize_figure(figure, output / f"{page.slug}_optics{suffix}.png")


def _dispersion_uncertainty(predictions_dir: Path) -> pd.Series:
    """One-sigma bar on each BPM's measured dispersion, indexed by ``(plane, bpm)``.

    The dispersion cache keeps the slope only, so the bar is refitted here from
    the orbits it came from: the standard error of the slope of the same
    straight line against ``pt``, from the scatter of the points about it. Taken
    from the residuals rather than from each orbit's own standard error of the
    mean, because that one is a micron and the reproducibility between momentum
    settings is not -- a bar the points visibly do not honour is worse than
    none. With two momentum points the line has no degrees of freedom left and
    the bar is ``NaN``, which draws as no bar.
    """
    path = predictions_dir / "start-model.absolute.parquet"
    if not path.exists():
        return pd.Series(dtype=float, index=pd.MultiIndex.from_tuples([], names=["plane", "bpm"]))
    frame = pd.read_parquet(path).dropna(subset=["pt", "measured"])
    bars = {}
    for key, group in frame.groupby(["plane", "bpm"], sort=False):
        pt, orbit = group["pt"].to_numpy(), group["measured"].to_numpy()
        spread = float(np.sum((pt - pt.mean()) ** 2))
        if len(group) < 3 or spread == 0.0:
            bars[key] = np.nan
            continue
        slope, intercept = np.polyfit(pt, orbit, 1)
        residual = orbit - (slope * pt + intercept)
        variance = float(np.sum(residual**2)) / (len(group) - 2)
        bars[key] = float(np.sqrt(variance / spread))
    return pd.Series(bars, name="uncertainty").rename_axis(["plane", "bpm"])


def measured_dispersion_frame(predictions_dir: Path,
                              positions: dict[str, float]) -> pd.DataFrame:
    """Measured ``d orbit / dpt`` at each BPM, with model ``s`` positions.

    Every prediction cache contains the same measured column. The start-model
    cache is used because it exists independently of which fitted cases are
    valid and makes that invariance explicit.
    """
    path = predictions_dir / "start-model.dispersion.parquet"
    if not path.exists():
        logger.warning("No measured dispersion cache; run scripts/predict_loco.py")
        return pd.DataFrame(columns=["plane", "bpm", "measured", "uncertainty", "s"])
    frame = pd.read_parquet(path)
    by_name = {name.upper(): s for name, s in positions.items()}
    frame = frame.copy()
    frame["uncertainty"] = _dispersion_uncertainty(predictions_dir).reindex(
        pd.MultiIndex.from_frame(frame[["plane", "bpm"]])
    ).to_numpy()
    frame["s"] = frame["bpm"].astype(str).str.upper().map(by_name)
    missing = frame["s"].isna()
    if missing.any():
        logger.warning(
            "No model position for %d measured-dispersion BPM rows",
            int(missing.sum()),
        )
    return frame.loc[~missing, ["plane", "bpm", "measured", "uncertainty", "s"]]


def measured_optics_frame(campaign, positions: dict[str, float]) -> pd.DataFrame | None:
    """The measured-optics table, with each BPM's ``s`` from the model sequence.

    The measured frame is keyed by BPM name as omc3 writes it; the model's
    element positions come off the MAD sequence. Both are ``BR3.BPM1L3`` today,
    but only one of them is under this repository's control, so match on case
    rather than assume.
    """
    path = campaign.optics_dir / "measured.parquet"
    if not path.exists():
        logger.warning("%s: no measured optics; run scripts/measured_optics.py", campaign.slug)
        return None
    frame = pd.read_parquet(path)
    by_name = {name.upper(): s for name, s in positions.items()}
    frame = frame.assign(s=[by_name.get(str(name).upper(), np.nan) for name in frame.index])
    return frame.sort_values("s")


def optics_summary(campaign) -> dict:
    """``results/optics/<slug>/summary.json``, or an empty dict if not made yet."""
    path = campaign.optics_dir / "summary.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _tune_caption(summary: dict, reference: str) -> str:
    """The one line every optics figure carries: whose tune is whose.

    A beta-beat is meaningless without knowing what it is against, and on the
    inverted configuration the two candidate references are a tenth of a tune
    apart. So the numbers go in the figure, not only in the page around it.
    """
    measured = summary.get("measured", {}).get("natural_tunes")
    model = summary.get(reference, {}).get("tunes")
    if not (measured and model):
        return ""
    how = (
        "matched to the measurement"
        if reference == "matched_model"
        else "un-matched, the machine's own circuit currents"
    )
    return (
        f"machine $Q$ = {measured[0]:.4f} / {measured[1]:.4f}  ·  "
        f"model $Q$ = {model[0]:.4f} / {model[1]:.4f} ({how})"
    )


#: The model each measured-optics figure is drawn against: summary key, file
#: name, legend label, and what the figure is called.
MEASURED_REFERENCES = (
    ("loco_model", "measured_optics.png", "LOCO start model (un-matched)",
     "the model the fits start from"),
    ("matched_model", "measured_optics_matched.png",
     "same lattice, tunes matched to the measurement",
     "the same lattice with its tunes matched"),
)


#: Legend label per reference model, so the two figures name the same lattice
#: the same way whichever of them it is the subject of.
REFERENCE_LABELS = {key: label for key, _, label, _ in MEASURED_REFERENCES}


def _measured_rdt(measured: pd.DataFrame | None, column: str) -> pd.Series | None:
    """The measured RDT amplitude a ``coupling_*`` panel is scored against."""
    rdt = column.removeprefix("coupling_")
    if measured is None or rdt not in measured.columns:
        return None
    return measured[rdt].dropna()


def _beat_error(frame: pd.DataFrame, beta: str, reference: str):
    """Bar on ``beta/reference - 1`` in per cent, or ``None`` if beta has none."""
    if f"{beta}_err" not in frame.columns:
        return None
    return 100 * frame[f"{beta}_err"] / frame[reference]


def figure_measured_optics(campaign, positions: dict[str, float], output: Path) -> None:
    """Measured beta against a model, per plane, once per reference model.

    Two figures, and the pair is the argument. The first is against the lattice
    the fits actually start from: the machine's own circuit currents, no
    matching, so its tune is wrong by whatever the ring's gradient error is worth
    -- a tenth of a tune on the inverted configuration. The second moves
    ``kbrqf``/``kbrqd`` until the model sits on the measured tune and asks the
    same question again. What survives the match is beta-beating the two main
    circuits cannot explain; what disappears was tune, and LOCO must not be given
    those circuits to absorb it with.

    Measured points carry their own error bars and are the same points in both.
    The last panels are the measured coupling RDT amplitudes against the same
    reference lattice, where the ring's quadrupole rolls show.
    """
    frame = measured_optics_frame(campaign, positions)
    if frame is None:
        return
    summary = optics_summary(campaign)

    for reference, filename, label, description in MEASURED_REFERENCES:
        if f"beta_x_{reference}" not in frame.columns:
            continue
        rdts = [rdt for rdt in ("f1001", "f1010") if rdt in frame.columns]
        figure, axes = plt.subplots(
            4 + len(rdts), 1, sharex=True, constrained_layout=True,
            figsize=(14, 2.75 * (4 + len(rdts))),
        )
        for row, plane in enumerate(("x", "y")):
            beta_axis, beat_axis = axes[2 * row], axes[2 * row + 1]
            mark_bpms(beta_axis, positions, label=row == 0)
            beta_axis.errorbar(
                frame["s"], frame[f"beta_{plane}"], yerr=frame.get(f"beta_{plane}_err"),
                fmt="o", color=CASE_COLOURS[0], markersize=5, linewidth=1.2,
                label="measured, from phase", zorder=3,
            )
            # Amplitude beta needs the BPM gains that phase beta does not, so it
            # is drawn open: same measurement, weaker claim.
            if f"beta_{plane}_amp" in frame.columns:
                beta_axis.errorbar(
                    frame["s"], frame[f"beta_{plane}_amp"],
                    yerr=frame.get(f"beta_{plane}_amp_err"),
                    fmt="^", color=CASE_COLOURS[1], markersize=6, linewidth=1.2,
                    markerfacecolor="none", label="measured, from amplitude", zorder=3,
                )
            beta_axis.plot(
                frame["s"], frame[f"beta_{plane}_{reference}"], color="0.20",
                linewidth=2.0, linestyle="--", label=label,
            )
            other = "loco_model" if reference != "loco_model" else "matched_model"
            if f"beta_{plane}_{other}" in frame.columns:
                beta_axis.plot(
                    frame["s"], frame[f"beta_{plane}_{other}"], color="0.60",
                    linewidth=1.2, linestyle=":", alpha=0.9,
                    label=REFERENCE_LABELS[other],
                )
            beta_axis.set_ylabel(f"$\\beta_{plane}$ [m]", fontsize=9)
            style_axis(beta_axis)

            mark_bpms(beat_axis, positions, label=False)
            beat_axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
            # The reference is a model, so the beating's bar is the measured
            # beta's divided by that model -- the same fraction, moved.
            beat_axis.errorbar(
                frame["s"], 100 * frame[f"beat_{plane}_{reference}"],
                yerr=_beat_error(frame, f"beta_{plane}", f"beta_{plane}_{reference}"),
                fmt="o-", color="0.20", markersize=5, linewidth=1.6, zorder=3,
                elinewidth=0.9, capsize=2.0, label=f"against {label}",
            )
            # Drawn underneath and dashed: on the matched figure the two lie on
            # top of each other, which is the result, and a solid line hiding a
            # solid line would read as one curve having been dropped.
            if f"beat_{plane}_amp_{reference}" in frame.columns:
                beat_axis.errorbar(
                    frame["s"], 100 * frame[f"beat_{plane}_amp_{reference}"],
                    yerr=_beat_error(frame, f"beta_{plane}_amp",
                                     f"beta_{plane}_{reference}"),
                    fmt="^-", color=CASE_COLOURS[1], markersize=6,
                    markerfacecolor="none", linewidth=1.3, alpha=0.9, zorder=3,
                    elinewidth=0.9, capsize=2.0,
                    label="the same, from amplitude beta",
                )
            if f"beat_{plane}_omc3_model" in frame.columns:
                beat_axis.plot(
                    frame["s"], 100 * frame[f"beat_{plane}_omc3_model"], "s--",
                    color=CASE_COLOURS[2], markersize=7, markerfacecolor="none",
                    linewidth=1.6, alpha=0.9, zorder=2,
                    label="against the omc3 analysis model (matched)",
                )
            beat_axis.set_ylabel(f"$\\Delta\\beta_{plane}/\\beta_{plane}$ [%]", fontsize=9)
            style_axis(beat_axis)
        # Coupling is amplitude only, measured against the same reference
        # lattice: omc3's phase convention is not MAD-NG's, and comparing the
        # two would compare conventions rather than machines.
        for rdt, axis in zip(rdts, axes[4:], strict=True):
            mark_bpms(axis, positions, label=False)
            axis.errorbar(
                frame["s"], frame[rdt], yerr=frame.get(f"{rdt}_err"), fmt="o",
                color=CASE_COLOURS[0], markersize=5, elinewidth=0.9, capsize=2.0,
                zorder=3, label=f"measured, rms {_rms(frame[rdt]):.2e}",
            )
            for model, style in ((reference, "--"), ("omc3_model", ":")):
                column = f"{rdt}_{model}"
                if column in frame.columns:
                    axis.plot(
                        frame["s"], frame[column], style,
                        color="0.20" if style == "--" else CASE_COLOURS[2],
                        linewidth=1.8,
                        label=f"{REFERENCE_LABELS.get(model, 'omc3 model')}, "
                              f"rms {_rms(frame[column]):.2e}",
                    )
            axis.set_ylabel(f"$|f_{{{rdt[1:]}}}|$", fontsize=9)
            axis.set_ylim(bottom=0.0)
            axis.legend(fontsize=7, loc="upper left", ncols=3)
            style_axis(axis)
        axes[0].legend(fontsize=7, loc="upper left", ncols=3)
        axes[1].legend(fontsize=7, loc="upper left", ncols=2)
        axes[-1].set_xlabel("s [m]")
        figure.suptitle(
            f"Measured optics against {description} — {campaign.label.lower()}\n"
            f"{_tune_caption(summary, reference)}",
            fontsize=12,
        )
        finalize_figure(figure, output / filename)


def figure_residuals(page: Page, predictions: Path, output: Path) -> None:
    """What each case failed to explain, per BPM, against the measurement's own bar.

    The residual belongs beside the case that produced it rather than in a table
    three sections away: the question a reader has at the end of a section is
    always "and how well did that work". A fit's own loss cannot answer it --
    each case fits a different target -- but the residual against a common
    measurement can, which is what these are.

    Two reference bands ride underneath, and the gap between them is the point.
    The narrow one is the statistical bar: the standard error of the mean over
    turns and bunches, propagated through the reference subtraction, which is
    what ``measured_response.closed_orbit`` returns and is of order a micron.
    The wide one is :data:`BPM_ZERO_OFFSET`, the systematic the fits actually
    weight the absolute planes by. A residual inside the wide band is explained
    to the precision the machine is *known* to; one inside the narrow band and
    outside nothing would mean the model had beaten the BPM calibration, which
    it cannot.
    """
    frames = {
        target: {
            slug: pd.read_parquet(predictions / f"{slug}.{target}.parquet")
            for slug in page.cases
            if (predictions / f"{slug}.{target}.parquet").exists()
        }
        for target in RESIDUAL_TARGETS
    }
    panels = [
        (target, plane) for target in RESIDUAL_TARGETS for plane in ("x", "y")
        if frames[target]
    ]
    if not panels:
        logger.warning("%s: no prediction parquets to plot residuals from", page.slug)
        return

    figure, axes = plt.subplots(
        len(panels), 1, sharex=True, constrained_layout=True,
        figsize=(14, 2.9 * len(panels)), squeeze=False,
    )
    bpms: list[str] = []
    for axis, (target, plane) in zip(axes[:, 0], panels, strict=True):
        for (slug, frame), colour in zip(frames[target].items(), CASE_COLOURS, strict=False):
            block = frame[frame["plane"] == plane]
            if block.empty:
                continue
            residual = block.assign(residual=1e3 * (block["measured"] - block["model"]))
            per_bpm = residual.groupby("bpm", sort=False)["residual"].apply(
                lambda values: float(np.sqrt(np.mean(np.square(values))))
            )
            bpms = list(per_bpm.index)
            axis.plot(range(len(per_bpm)), per_bpm.to_numpy(), marker="o", markersize=4,
                      linewidth=1.6, color=colour, label=page.label(slug))
        if bpms and "error" in next(iter(frames[target].values())).columns:
            reference = next(iter(frames[target].values()))
            reference = reference[reference["plane"] == plane]
            statistical = 1e3 * reference.groupby("bpm", sort=False)["error"].mean()
            axis.fill_between(range(len(statistical)), 0.0, statistical.to_numpy(),
                              color="0.55", alpha=0.35, zorder=0,
                              label="measurement standard error of the mean")
            axis.axhline(1e3 * BPM_ZERO_OFFSET, color="0.35", linestyle=":",
                         linewidth=1.3, zorder=0, label="BPM zero-offset systematic")
        axis.set_ylabel(
            f"{'horizontal' if plane == 'x' else 'vertical'}\n{RESIDUAL_TARGETS[target]}",
            fontsize=8,
        )
        axis.set_ylim(bottom=0.0)
        style_axis(axis)
    if bpms:
        axes[-1, 0].set_xticks(range(len(bpms)), bpms, rotation=90, fontsize=7)
    axes[0, 0].legend(fontsize=7, ncols=2)
    figure.suptitle(
        f"Residual rms per BPM, measured minus model — {page.title.lower()}",
        fontsize=12,
    )
    finalize_figure(figure, output / f"{page.slug}_residuals.png")


def _wrap(text: str, width: int = 22) -> str:
    """Break a case heading over lines so it fits an axis tick."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    lines.append(current)
    return "\n".join(lines)



#: Bars over tables, per instruction: a tune is one number per lattice per
#: plane, and a reader comparing five of them wants the ordering at a glance,
#: not five rows to subtract in their head. Every bar chart below is drawn
#: against a baseline -- the measured value -- so the bar *is* the error and a
#: bar of zero length is agreement.
MEASURED_COLOUR = "#000000"
MODEL_COLOURS = {"loco_model": "#0072B2", "matched_model": "#009E73"}
MODEL_NAMES = {
    "loco_model": "model, $k_1$ as sent",
    "matched_model": "model, matched to the tune",
}


def _rms(values) -> float:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    return float(np.sqrt(np.mean(values**2))) if values.size else float("nan")


def _rms_vs_measured(
    elements: np.ndarray, values: np.ndarray, measured: pd.Series | None, *, relative: bool
) -> float | None:
    """Rms of one curve against the measured beta-beating at the same BPMs.

    Matched by element name, case-insensitive, same convention as
    :func:`_rms_vs_measured_dispersion`. Every quoted rms is against the measurement,
    not the curve's own magnitude -- a fit that agrees with a small measured
    beat should print a small number even if it moved the lattice a lot getting
    there.
    """
    if measured is None or measured.empty:
        return None
    at_bpm = pd.Series(values, index=pd.Index(elements).astype(str).str.upper())
    at_bpm = at_bpm[~at_bpm.index.duplicated()].reindex(measured.index.str.upper())
    valid = at_bpm.notna().to_numpy()
    if not valid.any():
        return None
    diff = at_bpm.to_numpy()[valid] - measured.to_numpy()[valid]
    return 100 * _rms(diff) if relative else _rms(diff)


def _prefit_vs_matched(start: pd.DataFrame, matched: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """The un-fitted start model's own beat/phase/dispersion against the matched model.

    Iteration zero: no fit has touched anything, so this is the ring's gradient
    error once the tune the matched model was matched to is taken back out of
    it -- the same baseline every case on the matched-model page is judged
    against, drawn once rather than once per case.
    """
    common = start.index.intersection(matched.index)
    start, matched = start.loc[common], matched.loc[common]
    s = start["s"].to_numpy()
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for plane, beta, mu in (("x", "beta11", "mu1"), ("y", "beta22", "mu2")):
        out[f"beta_beating_{plane}"] = (s, start[beta].to_numpy() / matched[beta].to_numpy() - 1.0)
        out[f"phase_error_{plane}"] = (s, start[mu].to_numpy() - matched[mu].to_numpy())
    for plane in ("x", "y"):
        column = f"d{plane}"
        values = start[column].to_numpy() if column in start.columns else np.zeros(len(start))
        out[f"dispersion_{plane}"] = (s, values)
    for rdt in ("f1001", "f1010"):
        # The start model's own coupling, not a difference: an RDT amplitude
        # against a reference amplitude is not a meaningful subtraction.
        if rdt in start.columns:
            out[f"coupling_{rdt}"] = (s, start[rdt].to_numpy())
    out["_elements"] = (s, common.to_numpy())
    return out


def _rms_vs_measured_dispersion(
    elements: np.ndarray, values: np.ndarray, measured_dispersion: pd.DataFrame, plane: str
) -> float | None:
    """Rms between one dispersion curve and the measured points, as a % of the measured rms.

    Matched by BPM element name, case-insensitive. Used for the pre-fit model,
    the start model, and every fitted case alike, so every dispersion panel's
    printed number is against the same measurement.
    """
    points = measured_dispersion[measured_dispersion["plane"] == plane]
    if points.empty:
        return None
    curve = pd.Series(values, index=pd.Index(elements).astype(str).str.upper())
    curve = curve[~curve.index.duplicated()]
    model_at_bpm = points["bpm"].astype(str).str.upper().map(curve)
    valid = model_at_bpm.notna()
    if not valid.any():
        return None
    measured_values = points.loc[valid, "measured"].to_numpy()
    diff = measured_values - model_at_bpm[valid].to_numpy()
    denom = _rms(measured_values)
    return 100 * _rms(diff) / denom if denom else None


def _bar_labels(axis, bars, values, fmt: str) -> None:
    """Print each bar's own value at its end, inside or outside as it fits."""
    for bar, value in zip(bars, values, strict=True):
        axis.annotate(
            fmt.format(value),
            (bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height()),
            textcoords="offset points",
            xytext=(0, 3 if bar.get_height() >= 0 else -11),
            ha="center", fontsize=8,
        )


def figure_case_tunes(page: Page, campaign, optics_dir: Path, output: Path) -> None:
    """Where every fit on the page put the tune, one panel per plane.

    The optics figure shows the phase error along ``s`` but not the number that
    summarises it. A fit is free to move the tune -- nothing constrains it to the
    measurement -- so what it did with that freedom is drawn next to the figure,
    as a bar per lattice against the measured tune. Bar length is the error;
    the absolute tune is printed on the bar.

    The fitted tune comes from the cached optics: ``phase_error`` keeps the
    ring-wide slope, so its value at the end of the sequence *is* the tune change
    from the start model, whose own tune ``measured_optics.py`` recorded.
    """
    summary = optics_summary(campaign)
    if not summary:
        return
    start = summary["loco_model"]["tunes"]
    measured = summary["measured"]["natural_tunes"]
    spread = summary["measured"].get("natural_tune_spread", [0.0, 0.0])

    # Both model lattices lead the chart: the one the fits start from and the
    # one matched to the measurement, so the reference a reader might have in
    # mind is on the same axis as the fits rather than in a tab elsewhere.
    labels = ["model\n$k_1$ as sent"]
    tunes = [list(start)]
    colours = ["0.45"]
    matched = summary.get("matched_model", {}).get("tunes")
    if matched:
        labels.append("model\nmatched")
        tunes.append(list(matched))
        colours.append("0.70")
    for index, slug in enumerate(page.cases):
        path = optics_dir / f"{slug}.optics.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        labels.append(_wrap(page.label(slug), 18))
        tunes.append([
            start[plane] + float(frame[f"phase_error_{axis}"].iloc[-1])
            for plane, axis in ((0, "x"), (1, "y"))
        ])
        colours.append(CASE_COLOURS[index % len(CASE_COLOURS)])
    if len(tunes) < 3:
        return

    figure, axes = plt.subplots(1, 2, constrained_layout=True, figsize=(12, 4.6))
    for plane, (axis, name) in enumerate(zip(axes, ("x", "y"), strict=True)):
        values = [tune[plane] - measured[plane] for tune in tunes]
        bars = axis.bar(range(len(values)), values, color=colours, width=0.62)
        _bar_labels(axis, bars, [tune[plane] for tune in tunes], "{:.4f}")
        axis.axhline(0.0, color=MEASURED_COLOUR, linewidth=1.4)
        axis.axhspan(-spread[plane], spread[plane], color="0.5", alpha=0.25, zorder=0)
        axis.set_xticks(range(len(values)))
        axis.set_xticklabels(labels, fontsize=8)
        axis.set_ylabel(f"$Q_{name}$ - measured", fontsize=10)
        axis.set_title(
            f"$Q_{name}$, measured {measured[plane]:.4f}", fontsize=11
        )
        style_axis(axis)
    figure.suptitle(
        f"Fitted tune per case — {page.title.lower()}, {campaign.label.lower()}\n"
        "bar length is the error against the measured tune; the band is its "
        "spread across the flat bottom",
        fontsize=12,
    )
    finalize_figure(figure, output / f"{page.slug}_case_tunes.png")


#: The two Dp/p calibrations a case's fitted chromaticity is scored against:
#: the RF-derived chroma export, and the closed-orbit projection. A case's own
#: fitted dq1/dq2 does not depend on either -- only which measurement it is
#: compared to does -- so the two calibrations move the "measured" reference,
#: not the case bars, and are drawn as paired bars rather than separate figures.
CHROMATICITY_CALIBRATIONS = (
    ("dq_dpt", "dq_dpt_error", "chroma, XImeter Dp/p", ""),
    ("dq_dpt_closed_orbit", "dq_dpt_closed_orbit_error", "chroma, closed-orbit Dp/p", "//"),
)


def figure_case_chromaticity(page: Page, campaign, optics_dir: Path, output: Path) -> None:
    """Measured, start-model and fitted-lattice ``dq1``/``dq2`` per page.

    Each case is fitted once, so its dq1/dq2 is one number regardless of which
    Dp/p calibration is used to judge it -- only the measurement it is judged
    against moves. Both calibrations are drawn side by side per case, hatch
    marking the calibration, so the two do not have to be read off separate
    figures to see how much of a case's apparent error is the calibration.
    """
    summary = optics_summary(campaign)
    if not summary:
        return
    measured = {
        key: summary["measured"][key] for key, _, _, _ in CHROMATICITY_CALIBRATIONS
    }
    error = {
        key: summary["measured"][error_key]
        for key, error_key, _, _ in CHROMATICITY_CALIBRATIONS
    }
    model = summary["loco_model"]["dq_dpt"]

    cases = []
    for index, slug in enumerate(page.cases):
        path = optics_dir / f"{slug}.optics.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        if not {"dq_dpt_x", "dq_dpt_y"} <= set(frame.columns):
            continue
        cases.append((
            _wrap(page.label(slug), 18),
            [float(frame["dq_dpt_x"].iloc[0]), float(frame["dq_dpt_y"].iloc[0])],
            CASE_COLOURS[index % len(CASE_COLOURS)],
        ))
    if not cases:
        return

    labels = ["measured", "model\n$k_1$ as sent", *(label for label, _, _ in cases)]
    group_width = 0.82
    bar_width = group_width / len(CHROMATICITY_CALIBRATIONS)

    figure, axes = plt.subplots(1, 2, constrained_layout=True, figsize=(12, 4.6))
    for plane, (axis, name) in enumerate(zip(axes, ("1", "2"), strict=True)):
        for cal_index, (key, _, cal_label, hatch) in enumerate(CHROMATICITY_CALIBRATIONS):
            offset = (cal_index - (len(CHROMATICITY_CALIBRATIONS) - 1) / 2) * bar_width
            values = [measured[key][plane], model[plane], *(dq[plane] for _, dq, _ in cases)]
            heights = [value - measured[key][plane] for value in values]
            colours = [MEASURED_COLOUR, "0.45", *(colour for _, _, colour in cases)]
            positions = [x + offset for x in range(len(heights))]
            bars = axis.bar(
                positions, heights, width=bar_width, color=colours,
                hatch=hatch, edgecolor="white", linewidth=0.5,
                label=cal_label,
            )
            _bar_labels(axis, bars, heights, "{:+.3f}")
        axis.axhline(0.0, color=MEASURED_COLOUR, linewidth=1.2)
        for key, _, _, _ in CHROMATICITY_CALIBRATIONS:
            axis.axhspan(-error[key][plane], error[key][plane], color=MEASURED_COLOUR,
                         alpha=0.08, zorder=0)
        axis.set_xticks(range(len(labels)))
        axis.set_xticklabels(labels, fontsize=8)
        axis.set_ylabel(f"$dq_{name} - dq_{{{name},\\,measured}}$", fontsize=10)
        axis.set_title(f"$dq_{name}$", fontsize=11)
        style_axis(axis)
    handles = [
        Patch(facecolor="0.7", hatch=hatch, edgecolor="white", label=cal_label)
        for _, _, cal_label, hatch in CHROMATICITY_CALIBRATIONS
    ]
    axes[0].legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.9)
    figure.suptitle(
        f"$dQ/dp_t$ error against measurement per case — {page.title.lower()}, "
        f"{campaign.label.lower()}\nhatch marks the Dp/p calibration the "
        "measurement was scored against; a case's own fit is one number",
        fontsize=12,
    )
    finalize_figure(figure, output / f"{page.slug}_case_chromaticity.png")


def figure_case_scores(page: Page, predictions: Path, output: Path) -> None:
    """Residual against each scored measurement, per case, as grouped bars.

    Residual rms as a percentage of the measured amplitude, so 100 % -- drawn --
    is a model carrying no information about that measurement.
    """
    scoreboard = predictions / "scoreboard.csv"
    if not scoreboard.exists():
        return
    frame = pd.read_csv(scoreboard).set_index("option")
    rows = [slug for slug in ("start-model", *page.cases) if slug in frame.index]
    if not rows:
        return
    targets = [
        ("delta_x", "delta x"), ("delta_y", "delta y"),
        ("static_x", "static x"), ("static_y", "static y"),
        ("dispersion_x", "disp x"), ("dispersion_y", "disp y"),
    ]
    figure, axis = plt.subplots(constrained_layout=True, figsize=(12, 4.6))
    width = 0.8 / len(rows)
    for index, slug in enumerate(rows):
        values = [
            100 * frame.loc[slug, f"{column}_rel"] for column, _ in targets
        ]
        offsets = np.arange(len(targets)) + (index - (len(rows) - 1) / 2) * width
        colour = "0.45" if slug == "start-model" else CASE_COLOURS[
            (index - 1) % len(CASE_COLOURS)
        ]
        label = "start model — no fit" if slug == "start-model" else page.label(slug)
        axis.bar(offsets, values, width=width * 0.92, color=colour, label=label)
    axis.axhline(100.0, color="k", linewidth=1.2, linestyle="--")
    axis.annotate("no information about the measurement", (-0.45, 100), fontsize=8,
                  textcoords="offset points", xytext=(2, 4), ha="left")
    axis.set_xticks(range(len(targets)))
    axis.set_xticklabels([name for _, name in targets])
    axis.set_ylabel("residual rms [% of the measured amplitude]")
    axis.legend(fontsize=8, ncols=2)
    style_axis(axis)
    figure.suptitle(f"Residual per scored measurement — {page.title.lower()}", fontsize=12)
    finalize_figure(figure, output / f"{page.slug}_scores.png")


def _machine_bars(axis, values: dict[str, float], measured: float, error: float,
                  fmt: str, ylabel: str, title: str) -> None:
    names = ["measured", *(MODEL_NAMES[key] for key in values)]
    heights = [measured, *values.values()]
    colours = [MEASURED_COLOUR, *(MODEL_COLOURS[key] for key in values)]
    bars = axis.bar(range(len(heights)), heights, color=colours, width=0.6)
    axis.errorbar([0], [measured], yerr=[error], fmt="none", ecolor="0.4",
                  capsize=4, linewidth=1.4)
    _bar_labels(axis, bars, heights, fmt)
    axis.set_xticks(range(len(heights)))
    axis.set_xticklabels([_wrap(name, 14) for name in names], fontsize=8)
    axis.set_ylabel(ylabel, fontsize=10)
    axis.set_title(title, fontsize=11)
    style_axis(axis)


def figure_beta_beat_summary(
    summaries: list[tuple[object, dict]], beats: pd.DataFrame,
    positions: dict[str, float], output: Path,
) -> None:
    """Measured beta-beating along ``s`` against every reference, every campaign.

    One row per campaign, one column per plane; within a panel, one curve per
    reference model, filled markers for beta from phase and open ones for beta
    from amplitude -- same measurement, weaker claim, the way the per-campaign
    optics figure draws the pair. Drawn once for the whole page rather than
    once per tab: nothing here depends on which model tab is open, and a figure
    repeated in four tabs reads as four different figures.

    Along ``s`` rather than an rms bar per reference: the rms hides whether two
    references disagree everywhere or at one magnet. Each rms is kept in its
    curve's legend entry.

    ``summaries`` is ``[(campaign, optics_summary(campaign)), ...]`` and
    ``beats`` is :func:`optics_beat_along_s` for every campaign concatenated;
    both are persisted by ``scripts/analyse_cross_campaign.py``.
    """
    if not summaries or beats.empty:
        return
    sources = [
        ("from phase", "beta_beat", "o", "full"),
        ("from amplitude", "beta_beat_amplitude", "^", "none"),
    ]
    # Widest first, thinnest last. On a well-matched lattice all three
    # references land on top of each other, which is the result; drawn at one
    # width the last one plotted would hide the other two and read as a curve
    # having been dropped.
    references = [
        ("omc3_model", "omc3's own matched model", "#D55E00", 3.4),
        ("matched_model", MODEL_NAMES["matched_model"], "#009E73", 2.0),
        ("loco_model", MODEL_NAMES["loco_model"], "#0072B2", 1.0),
    ]
    figure, axes = plt.subplots(
        len(summaries), 2, sharex=True, constrained_layout=True, sharey="col",
        figsize=(15, 3.6 * len(summaries)), squeeze=False,
    )
    for row, (campaign, summary) in enumerate(summaries):
        for plane, name in enumerate(("x", "y")):
            axis = axes[row][plane]
            mark_bpms(axis, positions, label=False)
            axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
            for reference, label, colour, linewidth in references:
                for source, quantity, marker, fill in sources:
                    block = beats[
                        (beats["campaign"] == campaign.slug)
                        & (beats["quantity"] == quantity)
                        & (beats["reference"] == reference)
                        & (beats["plane"] == name)
                    ]
                    if block.empty:
                        continue
                    rms = summary.get(quantity, {}).get(name, {}).get(
                        f"vs_{reference}", {}).get("rms", np.nan)
                    entry = f"{label}, {source}"
                    if not np.isnan(rms):
                        entry += f" (rms {100 * rms:.1f}%)"
                    axis.errorbar(
                        block["s"], 100 * block["value"],
                        yerr=100 * block["uncertainty"], marker=marker,
                        linestyle="-" if fill == "full" else "--",
                        color=colour, markersize=5, linewidth=linewidth,
                        markerfacecolor=colour if fill == "full" else "none",
                        elinewidth=0.8, capsize=1.5, alpha=0.85, label=entry,
                    )
            axis.set_ylabel(f"$\\Delta\\beta_{name}/\\beta_{name}$ [%]", fontsize=10)
            axis.set_title(f"{campaign.label}, plane {name}", fontsize=11)
            axis.legend(fontsize=6, loc="upper left", ncols=2)
            style_axis(axis)
    # Once per column, not once per panel: the columns share a y axis, so a
    # per-panel call would compound the headroom row by row.
    for axis in axes[0]:
        _legend_headroom(axis, 0.26)
    for axis in axes[-1]:
        axis.set_xlabel("s [m]")
    figure.suptitle(
        "Measured beta-beating along $s$ against each reference model", fontsize=12
    )
    finalize_figure(figure, output / "comparison_beta_beat.png")


def figure_configuration_comparison(summaries: list[tuple[object, dict]], output: Path) -> None:
    """Both machine configurations on one pair of axes, tune and ``dQ/dpt``.

    The page tabs between configurations, so nothing inside a tab can compare
    them; this is the figure that replaces the side-by-side table.

    ``summaries`` is ``[(campaign, optics_summary(campaign)), ...]``, already
    filtered to campaigns with a summary -- see
    ``scripts/analyse_cross_campaign.py``, which persists it.
    """
    if len(summaries) < 2:
        return
    series = [
        ("measured", MEASURED_COLOUR,
         lambda s, key, plane: s["measured"][key][plane]),
        (MODEL_NAMES["loco_model"], MODEL_COLOURS["loco_model"],
         lambda s, key, plane: s["loco_model"][
             "tunes" if key == "natural_tunes" else "dq_dpt"][plane]),
        (MODEL_NAMES["matched_model"], MODEL_COLOURS["matched_model"],
         lambda s, key, plane: s.get("matched_model", {}).get(
             "tunes" if key == "natural_tunes" else "dq_dpt", [np.nan, np.nan])[plane]),
    ]
    for key, filename, titles, ylabel, fmt, relative in (
        ("natural_tunes", "comparison_tunes.png", ("$Q_x$", "$Q_y$"),
         "tune - measured", "{:.4f}", True),
        ("dq_dpt", "comparison_chromaticity.png", ("$dq1$", "$dq2$"),
         "model - measured $dQ/dp_t$", "{:+.3f}", True),
    ):
        figure, axes = plt.subplots(1, 2, constrained_layout=True, figsize=(11, 4.4))
        step = 0.8 / (len(series) - 1 if relative else len(series))
        for plane, (axis, title) in enumerate(zip(axes, titles, strict=True)):
            heights: list[float] = []
            # On the tune chart the measurement is the baseline, so a
            # "measured" bar would be a zero-height bar and a legend entry for
            # a line the reader can already see.
            drawn_series = series[1:] if relative else series
            for index, (label, colour, getter) in enumerate(drawn_series):
                values = [getter(s, key, plane) for _, s in summaries]
                # Same reason as the per-campaign chart: against the measurement
                # for the tune, absolute for $Q'$, where zero is meaningful.
                drawn = (
                    [
                        value - s["measured"][key][plane]
                        for value, (_, s) in zip(values, summaries, strict=True)
                    ]
                    if relative
                    else values
                )
                heights += [v for v in drawn if not np.isnan(v)]
                offsets = (
                    np.arange(len(values))
                    + (index - (len(drawn_series) - 1) / 2) * step
                )
                bars = axis.bar(offsets, drawn, width=step * 0.92, color=colour,
                                label=label if plane == 0 else None)
                _bar_labels(axis, bars, values, fmt)
            axis.set_xticks(range(len(summaries)))
            axis.set_xticklabels(
                [
                    f"{c.label}\nmeasured {s['measured'][key][plane]:.5f}"
                    if relative else c.label
                    for c, s in summaries
                ],
                fontsize=9,
            )
            axis.set_ylabel(ylabel, fontsize=10)
            axis.set_title(title, fontsize=11)
            if relative:
                axis.axhline(0.0, color=MEASURED_COLOUR, linewidth=1.4)
            if heights:
                # Room past both ends of the bars for the legend and for the
                # values printed at their tips, which otherwise land on the
                # tick labels.
                low, high = min(0.0, *heights), max(0.0, *heights)
                span = max(high - low, 1e-9)
                axis.set_ylim(low - 0.16 * span, high + 0.34 * span)
            style_axis(axis)
        axes[0].legend(fontsize=8)
        figure.suptitle("Both machine configurations, measured against both models",
                        fontsize=12)
        finalize_figure(figure, output / filename)


def scenario_dispersion_beat(campaign) -> dict[str, float]:
    """This campaign's own measured dispersion against its own un-matched
    (nominal, no injected error) model, ``{"x": ..., "y": ...}`` rms fractions.

    Read straight from ``scripts/predict_loco.py``'s scoreboard start-model
    row (``dispersion_{x,y}_rel``) rather than re-derived here -- that
    scoreboard is where the RF-offset-orbit dispersion fit and its
    against-the-model residual already live, from a wholly different
    measurement (the corrector scan) than the AC-dipole beta and phase. Read
    from the single-momentum matrix: the start-model row does not depend on
    the momentum-fit mode. Reads every ``scoreboard*.csv`` shard rather than
    requiring ``--merge`` to have been run: the start-model row is written by
    shard 1 regardless of how many shards there are.
    """
    predictions = fit_mode_by_slug("single").results_root(campaign) / "predictions"
    shards = sorted(predictions.glob("scoreboard*.csv"))
    if not shards:
        return {}
    scoreboard = pd.concat([pd.read_csv(shard) for shard in shards], ignore_index=True)
    row = scoreboard[scoreboard["option"] == "start-model"]
    if row.empty:
        return {}
    row = row.iloc[0]
    return {
        plane: float(row[key])
        for plane, key in (("x", "dispersion_x_rel"), ("y", "dispersion_y_rel"))
        if key in row and not pd.isna(row[key])
    }


#: The stored units of every :func:`optics_beat_along_s` quantity, as
#: ``quantity -> (axis label, scale from stored units to plotted ones)``.
#: Beta and dispersion beating are stored as fractions, phase in units of 2pi.
BEAT_AXIS = {
    "beta_beat": ("$\\Delta\\beta/\\beta$ [%]", 100.0),
    "beta_beat_amplitude": ("$\\Delta\\beta/\\beta$ [%]", 100.0),
    "phase_beat": ("$\\Delta\\mu$ [$2\\pi$]", 1.0),
    "dispersion_beat": ("$\\Delta D$ [m]", 1.0),
}


def _legend_headroom(axis, fraction: float) -> None:
    """Grow the axis upward so an in-axes legend does not sit on the curves.

    An along-s beating panel is full width and its legend carries an entry per
    campaign or per reference model, so ``loc="best"`` has nowhere to go: the
    room has to be made rather than found.
    """
    low, high = axis.get_ylim()
    axis.set_ylim(low, high + fraction * (high - low))


def optics_beat_along_s(campaign, positions: dict[str, float]) -> pd.DataFrame:
    """This campaign's measured beating per BPM, tidy, with model ``s``.

    The per-BPM counterpart of the rms in ``summary.json`` and of
    :func:`scenario_dispersion_beat`: same measurements, same references,
    before the rms is taken, so a comparison figure can show where around the
    ring a scenario's error sits rather than only how large it is. Columns are
    ``campaign, quantity, reference, plane, name, s, value, uncertainty``; beta and phase
    beating carry one row per reference model, dispersion only the un-matched
    one the scoreboard fits. A phase advance belongs to a BPM pair, not a BPM,
    and sits at the downstream one -- ``NAME2``, the same key ``summary.json``
    takes its phase rms over.

    Empty if the campaign has no measured optics yet.
    """
    blocks: list[pd.DataFrame] = []
    by_name = {name.upper(): s for name, s in positions.items()}

    frame = measured_optics_frame(campaign, positions)
    if frame is not None:
        for plane in ("x", "y"):
            for reference in ("loco_model", "matched_model", "omc3_model"):
                for quantity, column, beta in (
                    ("beta_beat", f"beat_{plane}_{reference}", f"beta_{plane}"),
                    ("beta_beat_amplitude", f"beat_{plane}_amp_{reference}",
                     f"beta_{plane}_amp"),
                ):
                    if column not in frame.columns:
                        continue
                    # The reference is a model, so the beating's bar is the
                    # measured beta's over that model.
                    bar = frame.get(f"{beta}_err")
                    blocks.append(pd.DataFrame({
                        "quantity": quantity, "reference": reference, "plane": plane,
                        "name": frame.index.astype(str), "s": frame["s"].to_numpy(),
                        "value": frame[column].to_numpy(float),
                        "uncertainty": np.nan if bar is None
                        else (bar / frame[f"beta_{plane}_{reference}"]).to_numpy(float),
                    }))

    phase_path = campaign.optics_dir / "measured_phase.parquet"
    if phase_path.exists():
        phase = pd.read_parquet(phase_path)
        for plane in ("x", "y"):
            if f"phase_{plane}" not in phase.columns:
                continue
            for reference in ("loco_model", "matched_model", "omc3_model"):
                column = f"phase_{plane}_{reference}"
                if column not in phase.columns:
                    continue
                # Wrapped the same way phase_beat_statistics wraps before its
                # rms: an advance is modulo one turn.
                difference = phase[f"phase_{plane}"] - phase[column]
                blocks.append(pd.DataFrame({
                    "quantity": "phase_beat", "reference": reference, "plane": plane,
                    "name": phase.index.astype(str),
                    "s": [by_name.get(str(n).upper(), np.nan) for n in phase.index],
                    "value": ((difference.astype(float) + 0.5) % 1.0 - 0.5).to_numpy(),
                    "uncertainty": phase.get(
                        f"phase_{plane}_err", pd.Series(np.nan, index=phase.index)
                    ).to_numpy(float),
                }))

    predictions = fit_mode_by_slug("single").results_root(campaign) / "predictions"
    dispersion = measured_dispersion_frame(predictions, positions)
    if not dispersion.empty:
        model = pd.read_parquet(predictions / "start-model.dispersion.parquet")
        merged = dispersion.merge(model[["plane", "bpm", "model"]], on=["plane", "bpm"])
        # Absolute, not relative: the model's vertical dispersion is ~0, so a
        # D_y beating divided by it is a number about the divisor. Same choice
        # as the phase beating, which is also stored as a difference.
        blocks.append(pd.DataFrame({
            "quantity": "dispersion_beat", "reference": "loco_model",
            "plane": merged["plane"].to_numpy(), "name": merged["bpm"].to_numpy(),
            "s": merged["s"].to_numpy(),
            "value": (merged["measured"] - merged["model"]).to_numpy(),
            "uncertainty": merged["uncertainty"].to_numpy(float),
        }))

    if not blocks:
        return pd.DataFrame(
            columns=["campaign", "quantity", "reference", "plane", "name", "s",
                     "value", "uncertainty"]
        )
    result = pd.concat(blocks, ignore_index=True).assign(campaign=campaign.slug)
    return result.dropna(subset=["s"]).sort_values(["quantity", "plane", "s"])


#: What the perturbation-effect figure draws, as ``quantity -> (column label,
#: whether the scenario-minus-baseline difference is taken relative to the
#: baseline)``. Beta is relative because a beta difference means nothing
#: without the beta it is a fraction of; phase and dispersion are absolute.
PERTURBATION_AXIS = {
    "beta": ("$\\Delta\\beta/\\beta$ [%]", True),
    "phase": ("$\\Delta\\mu$ [$2\\pi$]", False),
    "dispersion": ("$\\Delta D$ [m]", False),
    "coupling": ("$\\Delta|f|$", False),
}

#: What a quantity's two rows are. Coupling has no planes: its two rows are the
#: difference and the sum resonance, which is the same slot in the table.
PERTURBATION_PLANES = {
    "beta": ("x", "y"), "phase": ("x", "y"), "dispersion": ("x", "y"),
    "coupling": ("f1001", "f1010"),
}


def optics_values_along_s(
    campaign, positions: dict[str, float], model_bpms: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """This campaign's measured optics and its tune-matched model's, per BPM.

    Values, not beatings: the perturbation-effect figure subtracts one
    campaign's measurement from another's, which only means anything if both
    sides are the raw quantity. Columns are
    ``campaign, source, quantity, plane, name, s, value, uncertainty``, the
    last being the measurement's own one-sigma bar and ``NaN`` for a model,
    with ``source`` one
    of ``measured``/``model`` and ``quantity`` one of ``beta`` (m), ``phase``
    (BPM-to-BPM advance, units of 2pi, at the downstream BPM) and
    ``dispersion`` (m). Beta has a second measured source, ``measured_amp``:
    the same quantity from the BPM amplitudes rather than the phase, which
    needs the BPM gains and is the reason it is kept as its own column
    everywhere rather than averaged in.

    ``model_bpms`` is the tune-matched model's BPM twiss -- the model's beta
    and phase advance are already stored beside the measurement, but its
    dispersion is not, so that one column has to be twissed by the caller
    (:mod:`scripts.analyse_cross_campaign`) and handed in. Without it the
    model's dispersion rows are simply absent.
    """
    blocks: list[pd.DataFrame] = []
    by_name = {name.upper(): s for name, s in positions.items()}

    def block(source: str, quantity: str, plane: str, names, values,
              uncertainty=None) -> None:
        names = [str(name) for name in names]
        if uncertainty is None:
            uncertainty = np.full(len(names), np.nan)
        blocks.append(pd.DataFrame({
            "source": source, "quantity": quantity, "plane": plane,
            "name": names, "s": [by_name.get(n.upper(), np.nan) for n in names],
            "value": np.asarray(values, dtype=float),
            "uncertainty": np.asarray(uncertainty, dtype=float),
        }))

    frame = measured_optics_frame(campaign, positions)
    if frame is not None:
        for plane in ("x", "y"):
            for source, column in (
                ("measured", f"beta_{plane}"),
                ("measured_amp", f"beta_{plane}_amp"),
                ("model", f"beta_{plane}_matched_model"),
            ):
                if column in frame.columns:
                    block(source, "beta", plane, frame.index, frame[column],
                          frame.get(f"{column}_err"))
        # The coupling RDTs ride in the same table, one "plane" per resonance:
        # they are per BPM and per campaign like everything else here, and the
        # figures index them the same way.
        for rdt in ("f1001", "f1010"):
            for source, column in (
                ("measured", rdt),
                ("model", f"{rdt}_matched_model"),
            ):
                if column in frame.columns:
                    block(source, "coupling", rdt, frame.index, frame[column],
                          frame.get(f"{rdt}_err"))

    phase_path = campaign.optics_dir / "measured_phase.parquet"
    if phase_path.exists():
        phase = pd.read_parquet(phase_path)
        for plane in ("x", "y"):
            for source, column in (
                ("measured", f"phase_{plane}"),
                ("model", f"phase_{plane}_matched_model"),
            ):
                if column in phase.columns:
                    block(source, "phase", plane, phase.index, phase[column],
                          phase.get(f"{column}_err"))

    predictions = fit_mode_by_slug("single").results_root(campaign) / "predictions"
    measured_dispersion = measured_dispersion_frame(predictions, positions)
    for plane in ("x", "y"):
        rows = measured_dispersion[measured_dispersion["plane"] == plane]
        if not rows.empty:
            block("measured", "dispersion", plane, rows["bpm"], rows["measured"],
                  rows["uncertainty"])
        if model_bpms is not None and f"d{plane}" in model_bpms.columns:
            # Restricted to the BPMs the measurement has: the model twiss also
            # carries BR3.BPMT3L1, which no orbit came from, and a model row
            # with a point the measured row above it cannot have is a
            # difference the reader has no way to check.
            measured_names = {str(name).upper() for name in rows["bpm"]}
            model = model_bpms[
                [str(name).upper() in measured_names for name in model_bpms.index]
            ] if measured_names else model_bpms
            block("model", "dispersion", plane, model.index, model[f"d{plane}"])

    if not blocks:
        return pd.DataFrame(
            columns=["campaign", "source", "quantity", "plane", "name", "s",
                     "value", "uncertainty"]
        )
    result = pd.concat(blocks, ignore_index=True).assign(campaign=campaign.slug)
    return result.dropna(subset=["s"]).sort_values(["source", "quantity", "plane", "s"])


def loco_optics_values_along_s(
    campaign, measured_names: set[str] | None = None,
    mode_slug: str = LOCO_OPTICS_MODE, case_slug: str = LOCO_OPTICS_CASE,
    source: str = "loco",
) -> pd.DataFrame:
    """The LOCO-fitted lattice's optics at the BPMs, in the same tidy form as
    :func:`optics_values_along_s`, with ``source`` set to ``loco``.

    The cache holds the fitted beta and dispersion outright but the phase only
    as ``mu_fit - mu_start``. That is enough: the start model is the ``k1`` sent
    to the magnets, which is the same lattice for every campaign of a direction,
    so a campaign-minus-baseline difference of this column is the difference of
    the fitted phase itself. It is turned into the BPM-to-BPM advance the
    measurement reports before being stored, so the two halves of the figure are
    the same quantity.
    """
    path = fit_mode_by_slug(mode_slug).results_root(campaign) / "optics" / f"{case_slug}.optics.parquet"
    if not path.exists():
        logger.warning("%s: no %s fitted optics at %s", campaign.slug, case_slug, path)
        return pd.DataFrame(
            columns=["campaign", "source", "quantity", "plane", "name", "s",
                     "value", "uncertainty"]
        )
    frame = pd.read_parquet(path)
    names = frame["element"].astype(str)
    keep = names.str.upper().str.contains("BPM")
    if measured_names:
        # The twiss carries BR3.BPMT3L1, which no orbit came from. Dropping it
        # keeps the fitted BPM pairs the same pairs the measured advance uses.
        keep &= names.str.upper().isin({n.upper() for n in measured_names})
    bpms = frame[keep].sort_values("s")
    blocks: list[pd.DataFrame] = []

    def block(quantity: str, plane: str, rows: pd.DataFrame, values) -> None:
        blocks.append(pd.DataFrame({
            "source": source, "quantity": quantity, "plane": plane,
            "name": rows["element"].astype(str).to_numpy(), "s": rows["s"].to_numpy(),
            "value": np.asarray(values, dtype=float),
            # A fitted lattice has no measurement bar; the column exists so the
            # two halves of the figure concatenate.
            "uncertainty": np.nan,
        }))

    for plane in ("x", "y"):
        block("beta", plane, bpms, bpms[f"beta_{plane}"])
        block("dispersion", plane, bpms, bpms[f"dispersion_{plane}"])
        advance = bpms[f"phase_error_{plane}"].diff()
        block("phase", plane, bpms[1:], advance[1:])
    for rdt in ("f1001", "f1010"):
        if f"coupling_{rdt}" in bpms.columns:
            block("coupling", rdt, bpms, bpms[f"coupling_{rdt}"])
    return pd.concat(blocks, ignore_index=True).assign(campaign=campaign.slug)


#: One entry per perturbation figure, as
#: ``(file-name stem, quantity, measured source, what the figure is called)``.
#: Beta is two figures rather than one three-column figure: it is measured two
#: ways, the amplitude one carries the BPM gains so neither stands in for the
#: other, and side by side the panels are too small to read a BPM off.
PERTURBATION_FIGURES = (
    ("beta", "beta", "measured", "beta, measured from the phase"),
    ("beta_amp", "beta", "measured_amp", "beta, measured from the amplitude"),
    ("phase", "phase", "measured", "phase advance"),
    ("dispersion", "dispersion", "measured", "dispersion"),
    ("coupling", "coupling", "measured", "coupling RDT amplitudes"),
)


def figure_perturbation_effect(
    summaries: list[tuple[object, dict]], values: pd.DataFrame,
    positions: dict[str, float], output: Path,
    fit: tuple[str, str, str] = LOCO_OPTICS_FITS[0],
) -> None:
    """What each perturbation did, measurement against measurement, and the
    same difference in the fitted lattice underneath.

    One figure per entry in :data:`PERTURBATION_FIGURES`, each two rows (the
    planes) by two columns (measured, then the LOCO fit), so a panel is large
    enough to read a BPM-by-BPM feature off. Every curve is one campaign minus the unperturbed
    baseline of its own direction, at the same BPM: no model enters the left
    column at all, so a feature there is something the machine did, not
    something a reference lattice disagrees about. The right column asks the
    same question of the fitted lattices and is the comparison the figure
    exists for -- if LOCO found the perturbation, the two columns look alike.

    Measured points carry the two campaigns' bars added in quadrature, so a
    difference smaller than its own bar reads as one. The fitted column has no
    bar to carry: it is a lattice, not a measurement.

    ``values`` is :func:`optics_values_along_s` and
    :func:`loco_optics_values_along_s` for every campaign, concatenated and
    persisted by ``scripts/analyse_cross_campaign.py``. ``fit`` is the entry of
    :data:`LOCO_OPTICS_FITS` the fitted column is taken from; it names the
    source column to read and goes in the title, so the two pages cannot be
    told apart only by their file path.
    """
    if len(summaries) < 2 or values.empty:
        return
    (baseline, _), *scenarios = summaries
    for stem, quantity, measured_source, description in PERTURBATION_FIGURES:
        ylabel, relative = PERTURBATION_AXIS[quantity]
        fit_slug, _, fit_label = fit
        sources = (
            (measured_source, "measured"),
            (f"loco_{fit_slug}", f"fitted model, {fit_label}"),
        )
        # sharey="row": the measurement and the fit are the same quantity in the
        # same plane, and the point of the figure is how far apart they are.
        # Separate scales made a fit six times too small look identical to one
        # that had found the perturbation.
        figure, axes = plt.subplots(
            2, len(sources), sharex=True, sharey="row", constrained_layout=True,
            figsize=(9.0 * len(sources), 9.0), squeeze=False,
        )
        any_drawn = False
        for row, plane in enumerate(PERTURBATION_PLANES[quantity]):
            for column, (source, source_label) in enumerate(sources):
                axis = axes[row][column]
                selection = (
                    (values["source"] == source)
                    & (values["quantity"] == quantity)
                    & (values["plane"] == plane)
                )
                base = values[selection & (values["campaign"] == baseline.slug)]
                mark_bpms(axis, positions, label=False)
                axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
                drawn = False
                for index, (campaign, _) in enumerate(scenarios):
                    block = values[selection & (values["campaign"] == campaign.slug)]
                    if block.empty or base.empty:
                        continue
                    # Matched on BPM name, not on row order: a campaign whose
                    # analysis dropped a BPM would otherwise be subtracted from
                    # the wrong one and every point after it would shift.
                    pair = block.merge(
                        base[["name", "value", "uncertainty"]], on="name",
                        suffixes=("", "_base"),
                    ).sort_values("s")
                    if pair.empty:
                        continue
                    difference = pair["value"] - pair["value_base"]
                    # Two independent measurements, so the bars add in
                    # quadrature; the relative form carries the baseline's own
                    # bar through the division as well.
                    error = np.hypot(pair["uncertainty"], pair["uncertainty_base"])
                    if relative:
                        error = 100 * np.hypot(
                            error / pair["value_base"],
                            difference * pair["uncertainty_base"]
                            / pair["value_base"] ** 2,
                        )
                        difference = 100 * difference / pair["value_base"]
                    axis.errorbar(
                        pair["s"], difference, yerr=error, fmt="o-", markersize=4,
                        linewidth=1.4, elinewidth=0.9, capsize=2.0,
                        color=OVERLAY_COLOURS[index % len(OVERLAY_COLOURS)],
                        label=f"{campaign.label} (rms {_rms(difference):.3g})",
                    )
                    drawn = True
                    any_drawn = True
                axis.set_ylabel(ylabel, fontsize=11)
                where = f"plane {plane}" if plane in ("x", "y") else f"$|{plane}|$"
                axis.set_title(f"{source_label}, {where}", fontsize=12)
                if drawn:
                    axis.legend(fontsize=8, loc="upper left")
                style_axis(axis)
            # Once per row, not once per panel: the row shares its y axis, so
            # applying it per panel would compound the headroom.
            _legend_headroom(axes[row][0], 0.30)
        for axis in axes[-1]:
            axis.set_xlabel("s [m]")
        figure.suptitle(
            f"Effect of each perturbation on the {description}, against "
            f"{baseline.label}: the measurement on the left, the lattice "
            f"fitted with {fit_label} on the right",
            fontsize=13,
        )
        if any_drawn:
            finalize_figure(figure, output / f"scenario_perturbation_{stem}.png")
        else:
            plt.close(figure)


def figure_perturbation_tunes(summaries: list[tuple[object, dict]], output: Path) -> None:
    """The same difference for tune and chromaticity, as bars.

    Measured only: where each fit put the tune is already a figure of its own
    on every case page, against this same measurement.

    ``summaries`` is persisted by ``scripts/analyse_cross_campaign.py``.
    """
    if len(summaries) < 2:
        return
    (baseline, base_summary), *scenarios = summaries
    panels = [
        ("natural_tunes", 0, "$\\Delta Q_x$", "{:+.4f}"),
        ("natural_tunes", 1, "$\\Delta Q_y$", "{:+.4f}"),
        ("dq_dpt", 0, "$\\Delta dq1$", "{:+.3f}"),
        ("dq_dpt", 1, "$\\Delta dq2$", "{:+.3f}"),
    ]
    figure, axes = plt.subplots(2, 2, constrained_layout=True, figsize=(13, 8))
    for axis, (key, plane, title, fmt) in zip(axes.flat, panels, strict=True):
        values = [
            summary["measured"][key][plane] - base_summary["measured"][key][plane]
            for _, summary in scenarios
        ]
        offsets = np.arange(len(scenarios))
        bars = axis.bar(
            offsets, values, width=0.6,
            color=[OVERLAY_COLOURS[i % len(OVERLAY_COLOURS)] for i in range(len(scenarios))],
        )
        _bar_labels(axis, bars, values, fmt)
        axis.axhline(0.0, color=MEASURED_COLOUR, linewidth=1.4)
        axis.set_xticks(offsets)
        axis.set_xticklabels([_wrap(c.label, 14) for c, _ in scenarios], fontsize=8)
        axis.set_title(title, fontsize=11)
        finite = [v for v in values if not np.isnan(v)]
        if finite:
            low, high = min(0.0, *finite), max(0.0, *finite)
            span = max(high - low, 1e-9)
            axis.set_ylim(low - 0.2 * span, high + 0.3 * span)
        style_axis(axis)
    figure.suptitle(
        f"Effect of each perturbation on the measured tune and chromaticity, "
        f"against {baseline.label}",
        fontsize=12,
    )
    finalize_figure(figure, output / "scenario_perturbation_tunes.png")


def figure_scenario_tunes_chromas(summaries: list[tuple[object, dict]], output: Path) -> None:
    """Absolute measured tune and chromaticity, one group of bars per scenario
    campaign, four panels: $Q_x$, $Q_y$, $dq1$, $dq2$.

    ``summaries`` is persisted by ``scripts/analyse_cross_campaign.py``.
    """
    if not summaries:
        return
    series = [
        ("measured", MEASURED_COLOUR, lambda s, key, plane: s["measured"][key][plane]),
    ]
    panels = [
        ("natural_tunes", 0, "$Q_x$", "{:.4f}"),
        ("natural_tunes", 1, "$Q_y$", "{:.4f}"),
        ("dq_dpt", 0, "$dq1$", "{:+.3f}"),
        ("dq_dpt", 1, "$dq2$", "{:+.3f}"),
    ]
    figure, axes = plt.subplots(2, 2, constrained_layout=True, figsize=(13, 9))
    width = 0.8 / len(series)
    for axis, (key, plane, title, fmt) in zip(axes.flat, panels, strict=True):
        heights: list[float] = []
        for index, (label, colour, getter) in enumerate(series):
            values = [getter(s, key, plane) for _, s in summaries]
            heights += [v for v in values if not np.isnan(v)]
            offsets = np.arange(len(summaries)) + (index - (len(series) - 1) / 2) * width
            bars = axis.bar(offsets, values, width=width * 0.92, color=colour,
                            label=label if axis is axes.flat[0] else None)
            _bar_labels(axis, bars, values, fmt)
        axis.set_xticks(range(len(summaries)))
        axis.set_xticklabels([_wrap(c.label, 14) for c, _ in summaries], fontsize=8)
        axis.set_title(title, fontsize=11)
        if heights:
            low, high = min(0.0, *heights), max(0.0, *heights)
            span = max(high - low, 1e-9)
            axis.set_ylim(low - 0.1 * span, high + 0.3 * span)
        style_axis(axis)
    figure.suptitle("Measured tune and chromaticity, absolute, every scenario", fontsize=12)
    finalize_figure(figure, output / "scenario_tunes_chromas.png")


def figure_scenario_knob_diffs(
    mode, case_slug: str, baseline, base: pd.DataFrame,
    blocks: list[tuple[object, pd.DataFrame]], output: Path,
) -> None:
    """Each scenario's fitted knobs minus the baseline's, per magnet, per family.

    The baseline campaign carries no injected error; a scenario's diff against
    it is the fit's estimate of that scenario's error, magnet by magnet.

    ``base`` (the baseline campaign's own ``read_knobs`` frame) and
    ``blocks`` (``[(scenario, read_knobs(...)), ...]``) are the raw per-magnet
    fits persisted by ``scripts/analyse_cross_campaign.py``, which is also
    where a missing baseline/scenario file is logged and skipped.
    """
    if not blocks:
        return
    for suffix, (label, scale) in FAMILY_AXIS.items():
        if not (base["suffix"] == suffix).any():
            continue
        base_block = base[base["suffix"] == suffix].set_index("element")
        figure, axis = plt.subplots(figsize=(14, 5.0), constrained_layout=True)
        elements = base_block.sort_values("s").index.to_list()
        positions_x = np.arange(len(elements))
        width = 0.8 / max(len(blocks), 1)
        drawn = 0
        for index, (scenario, block) in enumerate(blocks):
            scenario_block = block[block["suffix"] == suffix].set_index("element")
            common = [e for e in elements if e in scenario_block.index]
            if not common:
                continue
            diff = scale * (
                scenario_block.loc[common, "value"] - base_block.loc[common, "value"]
            )
            offsets = [elements.index(e) for e in common]
            offsets = np.array(offsets) + (index - (len(blocks) - 1) / 2) * width
            axis.bar(offsets, diff, width=width * 0.92,
                     color=OVERLAY_COLOURS[index % len(OVERLAY_COLOURS)],
                     label=scenario.label)
            drawn += 1
        if not drawn:
            plt.close(figure)
            continue
        axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
        axis.set_xticks(positions_x)
        axis.set_xticklabels(elements, rotation=90, fontsize=6)
        axis.set_ylabel(f"{label}, scenario − baseline")
        axis.set_title(
            f"{label} error against {baseline.label} — {mode.label.lower()}, "
            f"{case_heading(case_slug).lower()}", fontsize=11,
        )
        axis.legend(fontsize=8, ncols=len(blocks))
        style_axis(axis)
        finalize_figure(figure, output / f"knob_diffs_{suffix.lstrip('.')}.png")


#: One colour per method, fixed across both benchmark figures.
METHOD_COLOURS = {"method1": "#0072B2", "method2": "#D55E00"}
METHOD_NAMES = {"method1": "Method 1", "method2": "Method 2"}


def benchmark_records(root: Path, campaigns) -> list[dict]:
    """Each configuration's benchmark record, for the configurations that have one."""
    records = []
    for campaign in campaigns:
        path = root / f"{campaign.slug}.json"
        if path.exists():
            records.append(json.loads(path.read_text()))
    return records


def figure_benchmark_speed(records: list[dict], output: Path) -> None:
    """What each method cost to reach its answer, wall clock and CPU.

    Both numbers, because the two methods spend time differently: Method 1 is
    one MAD-NG process and its wall clock *is* its CPU, while Method 2 fans the
    same fit over one worker per corrector setting, so wall clock alone would
    report the hardware it was given rather than the work it did.
    """
    if not records:
        return
    figure, axes = plt.subplots(
        1, len(records), figsize=(4.6 * len(records) + 1.6, 4.4),
        sharey=True, constrained_layout=True, squeeze=False,
    )
    for axis, record in zip(axes[0], records, strict=True):
        positions = np.arange(2)
        width = 0.38
        for offset, (key, label) in zip(
            (-width / 2, width / 2), (("wall_s", "wall clock"), ("cpu_s", "CPU, whole tree")),
            strict=True,
        ):
            values = [record[method][key] for method in ("method1", "method2")]
            bars = axis.bar(
                positions + offset, values, width, label=label,
                color=[METHOD_COLOURS[m] for m in ("method1", "method2")],
                alpha=1.0 if key == "wall_s" else 0.55,
                edgecolor="white", linewidth=0.6,
            )
            _bar_labels(axis, bars, values, "{:.1f} s")
        axis.set_xticks(
            positions,
            [f"{METHOD_NAMES['method1']}\n1 process",
             f"{METHOD_NAMES['method2']}\n{record['method2']['processes']} processes"],
            fontsize=9,
        )
        axis.set_title(record["label"], fontsize=10, loc="left")
        style_axis(axis)
    axes[0][0].set_ylabel("seconds")
    axes[0][0].legend(fontsize=8)
    figure.suptitle(
        "What each method cost for the same fit — 32 cell-grouped knobs, delta orbits",
        fontsize=12,
    )
    finalize_figure(figure, output / "benchmark_speed.png")


def figure_benchmark_agreement(records: list[dict], output: Path) -> None:
    """The two answers against each other, one point per magnet.

    On the diagonal the methods asked for the same gradient. The correlation and
    the rms difference are printed rather than left to the eye, and the axes are
    shared and square so a point's distance from the line is the disagreement in
    the units the rest of the study uses.
    """
    if not records:
        return
    figure, axes = plt.subplots(
        1, len(records), figsize=(4.6 * len(records) + 1.2, 4.6),
        constrained_layout=True, squeeze=False,
    )
    scale = 100 / NOMINAL_K1L
    for axis, record in zip(axes[0], records, strict=True):
        directory = Path(record["method1"]["log"]).parent
        first = pd.read_csv(directory / "method1" / "knobs.csv").set_index("knob")["value"]
        second = pd.read_csv(directory / "method2" / "knobs.csv").set_index("knob")["value"]
        common = first.index.intersection(second.index)
        x = scale * first.loc[common].to_numpy(dtype=float)
        y = scale * second.loc[common].to_numpy(dtype=float)
        limit = 1.1 * max(np.abs(np.concatenate([x, y])).max(), 1e-9)
        axis.plot([-limit, limit], [-limit, limit], color="0.6", linewidth=1.0,
                  linestyle="--", label="the same answer")
        axis.scatter(x, y, s=26, color=METHOD_COLOURS["method1"], alpha=0.85,
                     edgecolor="white", linewidth=0.5)
        agreement = record["agreement"]
        axis.annotate(
            f"correlation {agreement['correlation']:+.4f}\n"
            f"rms difference {agreement['rms_difference_pct']:.2f} %\n"
            f"largest {agreement['max_difference_pct']:.2f} %",
            (0.04, 0.96), xycoords="axes fraction", va="top", fontsize=8,
        )
        axis.set_xlim(-limit, limit)
        axis.set_ylim(-limit, limit)
        axis.set_aspect("equal")
        axis.set_xlabel("Method 1, $\\Delta k_1 L / k_1 L$ [%]")
        axis.set_title(record["label"], fontsize=10, loc="left")
        style_axis(axis)
    axes[0][0].set_ylabel("Method 2, $\\Delta k_1 L / k_1 L$ [%]")
    axes[0][-1].legend(fontsize=8, loc="lower right")
    figure.suptitle("Do the two methods ask the same magnets for the same thing?",
                    fontsize=12)
    finalize_figure(figure, output / "benchmark_agreement.png")


def build_page(page: Page, args, positions: dict[str, float]) -> None:
    output = args.output / page.slug
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob(f"{page.slug}_*.png"):
        stale.unlink()
    valid_cases = tuple(
        slug for slug in page.cases
        if slug == "method1" or result_is_valid(args.matrix / slug)
    )
    page = replace(page, cases=valid_cases)
    families = {
        suffix
        for slug in page.cases
        for suffix in FAMILY_AXIS
        if (args.matrix / slug / "knobs.csv").exists()
        and (read_knobs(args.matrix / slug / "knobs.csv", positions)["suffix"] == suffix).any()
    }
    for suffix in FAMILY_AXIS:
        if suffix in families:
            figure_family_by_s(page, suffix, args.matrix, positions, output)
    if ".tilt" in families:
        figure_family_significance(page, ".tilt", args.matrix, positions, output)
    figure_family_significance(page, ".dk1l", args.matrix, positions, output)
    figure_optics(
        page, args.optics, args.predictions, positions, output,
        campaign=args.campaign_object,
    )
    figure_case_tunes(page, args.campaign_object, args.optics, output)
    figure_case_chromaticity(page, args.campaign_object, args.optics, output)
    figure_residuals(page, args.predictions, output)
    figure_case_scores(page, args.predictions, output)
    logger.info("%s: figures written to %s", page.slug, output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=None)
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--optics", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    add_campaign_argument(parser)
    add_fit_mode_argument(parser)
    parser.add_argument("--sequence-file", type=Path,
                        default=DEFAULT_SEQUENCE_FILE)
    parser.add_argument("--page", nargs="+", default=None,
                        choices=sorted(PAGE_BY_SLUG), help="Pages to build.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    campaign = campaign_by_slug(args.campaign)
    mode = fit_mode_by_slug(args.momentum_mode)
    args.campaign_object = campaign
    root = mode.results_root(campaign)
    args.matrix = args.matrix or root
    args.predictions = args.predictions or root / "predictions"
    args.optics = args.optics or root / "optics"
    # Figures are namespaced by campaign so two tabs of the same page cannot
    # overwrite each other's images.
    args.output = args.output or mode.figures_dir(campaign, Path("docs/assets/figures"))
    positions = model_element_positions(
        build_model(sequence_file=args.sequence_file, campaign=campaign)
    )
    args.output.mkdir(parents=True, exist_ok=True)
    figure_measured_optics(campaign, positions, args.output)
    # Cross-campaign comparison figures (configuration/beta-beat/benchmark/
    # scenario) are no longer drawn from here -- they read persisted,
    # combined data written once by scripts/analyse_cross_campaign.py and are
    # drawn by scripts/plot_cross_campaign.py, so this call only ever does
    # this one campaign's own figures and is safe to run in parallel with
    # every other (campaign, mode) call.
    default_pages = ALL_PAGES if mode.slug == "single" else (*PAGES, PER_MAGNET_PAGE)
    pages = [PAGE_BY_SLUG[slug] for slug in args.page] if args.page else list(default_pages)
    for page in pages:
        build_page(page, args, positions)


if __name__ == "__main__":
    main()
