"""Cross-campaign analysis and figures, for one direction at a time.

Per-page figures live in :mod:`loco_report`. This module compares whole
campaigns rather than the cases within one: the tidy-frame builders :mod:`scripts.analyse_cross_campaign`
persists, and the figures :mod:`scripts.plot_cross_campaign` draws from them.
Neither has a CLI here; both are driven by those two scripts.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from psb_md.plotting import finalize_figure, style_axis

from loco_common.case_names import (
    LOCO_OPTICS_CASE,
    LOCO_OPTICS_FITS,
    LOCO_OPTICS_MODE,
    case_heading,
)
from loco_common.fit_mode import (
    fit_mode_by_slug,
)
from scripts.plot_knobs import (
    NOMINAL_BEND_ANGLE,
    NOMINAL_K1L,
    OVERLAY_COLOURS,
    mark_bpms,
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










#: The two reference models a page's lattice figure puts the measured points
#: against, as (summary key, file-name suffix). Same pair as
#: :data:`MEASURED_REFERENCES`, named for the page figures rather than the
#: measured-optics ones.
PAGE_OPTICS_REFERENCES = (("loco_model", ""), ("matched_model", "_matched"))




def measured_dispersion_frame(predictions_dir: Path,
                              positions: dict[str, float]) -> pd.DataFrame:
    """Measured ``d orbit / dpt`` at each BPM, with model ``s`` positions.

    Every prediction cache contains the same measured column. The start-model
    cache is used because it exists independently of which fitted cases are
    valid and makes that invariance explicit. The uncertainty comes straight
    from ``measured_error`` in the cache -- written by
    ``scripts/predict_loco.py`` from
    ``tmom_recon.physics.closed_orbit.measure_dispersion``, propagating the
    repeat-acquisition orbit scatter and the chroma pt uncertainty -- rather
    than refitted here from the handful of RF-steering points, which leaves
    too few degrees of freedom to be a meaningful residual estimate.
    """
    path = predictions_dir / "start-model.dispersion.parquet"
    if not path.exists():
        logger.warning("No measured dispersion cache; run scripts/predict_loco.py")
        return pd.DataFrame(columns=["plane", "bpm", "measured", "uncertainty", "s"])
    frame = pd.read_parquet(path)
    by_name = {name.upper(): s for name, s in positions.items()}
    frame = frame.rename(columns={"measured_error": "uncertainty"}).copy()
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













#: Bars over tables, per instruction: a tune is one number per lattice per
#: plane, and a reader comparing five of them wants the ordering at a glance,
#: not five rows to subtract in their head. Every bar chart below is drawn
#: against a baseline -- the measured value -- so the bar *is* the error and a
#: bar of zero length is agreement.
MEASURED_COLOUR = "#000000"
MODEL_NAMES = {
    "loco_model": "model, $k_1$ as sent",
    "matched_model": "model, matched to the tune",
}


def _rms(values) -> float:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    return float(np.sqrt(np.mean(values**2))) if values.size else float("nan")





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




#: The two Dp/p calibrations a case's fitted chromaticity is scored against:
#: the RF-derived chroma export, and the closed-orbit projection. A case's own
#: fitted dq1/dq2 does not depend on either -- only which measurement it is
#: compared to does -- so the two calibrations move the "measured" reference,
#: not the case bars, and are drawn as paired bars rather than separate figures.
CHROMATICITY_CALIBRATIONS = (
    ("dq_dpt", "dq_dpt_error", "chroma, XImeter Dp/p", ""),
    ("dq_dpt_closed_orbit", "dq_dpt_closed_orbit_error", "chroma, closed-orbit Dp/p", "//"),
)








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
        ("natural_tunes", "natural_tune_spread", 0, "$\\Delta Q_x$", "{:+.4f}"),
        ("natural_tunes", "natural_tune_spread", 1, "$\\Delta Q_y$", "{:+.4f}"),
        ("dq_dpt", "dq_dpt_error", 0, "$\\Delta dq1$", "{:+.3f}"),
        ("dq_dpt", "dq_dpt_error", 1, "$\\Delta dq2$", "{:+.3f}"),
    ]
    figure, axes = plt.subplots(2, 2, constrained_layout=True, figsize=(13, 8))
    for axis, (key, error_key, plane, title, fmt) in zip(axes.flat, panels, strict=True):
        values = [
            summary["measured"][key][plane] - base_summary["measured"][key][plane]
            for _, summary in scenarios
        ]
        # Scenario and baseline are independent measurements, so their errors
        # add in quadrature.
        errors = [
            float(np.hypot(summary["measured"][error_key][plane],
                            base_summary["measured"][error_key][plane]))
            for _, summary in scenarios
        ]
        offsets = np.arange(len(scenarios))
        bars = axis.bar(
            offsets, values, width=0.6, yerr=errors, capsize=3,
            error_kw=dict(elinewidth=1.0),
            color=[OVERLAY_COLOURS[i % len(OVERLAY_COLOURS)] for i in range(len(scenarios))],
        )
        _bar_labels(axis, bars, values, fmt)
        axis.axhline(0.0, color=MEASURED_COLOUR, linewidth=1.4)
        axis.set_xticks(offsets)
        axis.set_xticklabels([_wrap(c.label, 14) for c, _ in scenarios], fontsize=8)
        axis.set_title(title, fontsize=11)
        finite = [
            v + sign * e for v, e in zip(values, errors, strict=True)
            if not np.isnan(v) for sign in (-1, 1)
        ]
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
        ("natural_tunes", "natural_tune_spread", 0, "$Q_x$", "{:.4f}"),
        ("natural_tunes", "natural_tune_spread", 1, "$Q_y$", "{:.4f}"),
        ("dq_dpt", "dq_dpt_error", 0, "$dq1$", "{:+.3f}"),
        ("dq_dpt", "dq_dpt_error", 1, "$dq2$", "{:+.3f}"),
    ]
    figure, axes = plt.subplots(2, 2, constrained_layout=True, figsize=(13, 9))
    width = 0.8 / len(series)
    for axis, (key, error_key, plane, title, fmt) in zip(axes.flat, panels, strict=True):
        heights: list[float] = []
        for index, (label, colour, getter) in enumerate(series):
            values = [getter(s, key, plane) for _, s in summaries]
            errors = [s["measured"][error_key][plane] for _, s in summaries]
            heights += [
                v + sign * e for v, e in zip(values, errors, strict=True)
                if not np.isnan(v) for sign in (-1, 1)
            ]
            offsets = np.arange(len(summaries)) + (index - (len(series) - 1) / 2) * width
            bars = axis.bar(offsets, values, width=width * 0.92, color=colour,
                            yerr=errors, capsize=3, error_kw=dict(elinewidth=1.0),
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
