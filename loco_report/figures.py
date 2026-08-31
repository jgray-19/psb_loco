"""Figure builders. Each writes at most a two-panel, page-width PNG."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from psb_md.plotting import finalize_figure, style_axis

from loco_common.case_names import Page
from loco_report import metrics
from loco_report.data import RESIDUAL_TARGETS, REFERENCES, Results, knob_statistics
from loco_report.style import (
    BPM_ZERO_OFFSET,
    CASE_COLOURS,
    FAMILIES,
    PREFIT_COLOUR,
    START_COLOUR,
    bar_width,
    element_colour,
    legend_handles,
    legend_headroom,
    log_axis,
    mark_bpms,
    panels,
    quantity_of,
)

logger = logging.getLogger(__name__)

PLANE_WORD = {"x": "horizontal", "y": "vertical"}

#: One figure per optics quantity, as (file stem, title, columns).
OPTICS_FIGURES = (
    ("beta_beating", "Beta-beating", ("beta_beating_x", "beta_beating_y")),
    ("phase_error", "Phase error", ("phase_error_x", "phase_error_y")),
    ("dispersion", "Dispersion", ("dispersion_x", "dispersion_y")),
    ("coupling", "Coupling", ("coupling_f1001", "coupling_f1010")),
)

AXIS_LABEL = {
    "beta_beating_x": "horizontal beta-beating [%]",
    "beta_beating_y": "vertical beta-beating [%]",
    "phase_error_x": "horizontal phase error [$2\\pi$]",
    "phase_error_y": "vertical phase error [$2\\pi$]",
    "dispersion_x": "$D_x$ [m]",
    "dispersion_y": "$D_y$ [m]",
    "coupling_f1001": "$|f_{1001}|$",
    "coupling_f1010": "$|f_{1010}|$",
}


def _save(figure, path: Path) -> Path:
    finalize_figure(figure, path)
    return path


def family_by_s(results: Results, page: Page, suffix: str, output: Path) -> list[Path]:
    """Every magnet's fitted strength against s, one panel per case."""
    blocks = {}
    for slug in results.valid(page.cases):
        block = results.knobs(slug)
        block = block[block["suffix"] == suffix].sort_values("s")
        if not block.empty:
            blocks[slug] = block
    if not blocks:
        return []

    family = FAMILIES[suffix]
    figure, axes = panels(len(blocks), sharey=True)
    for axis, (slug, block) in zip(axes, blocks.items(), strict=True):
        s = block["s"].to_numpy()
        values = family.scale * block["value"].to_numpy()
        mark_bpms(axis, results.positions)
        axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
        axis.bar(s, values, width=bar_width(s),
                 color=[element_colour(e) for e in block["element"]], alpha=0.85)
        axis.errorbar(s, values, yerr=family.scale * block["uncertainty"].to_numpy(),
                      fmt="none", ecolor="black", elinewidth=0.9, capsize=2.0)
        axis.set_ylabel(family.axis_label, fontsize=8)
        axis.set_title(page.label(slug), fontsize=9, loc="left")
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(
        handles=[
            *legend_handles(pd.concat(blocks.values())["element"]),
            Line2D([], [], color="0.55", linestyle="--", linewidth=0.7, label="BPM"),
        ],
        fontsize=7, ncols=4, loc="upper left",
    )
    legend_headroom(axes[0])
    name = f"{page.slug}_{suffix.lstrip('.')}_by_s.png"
    return [_save(figure, output / name)]


def family_significance(results: Results, page: Page, suffix: str,
                        output: Path) -> list[Path]:
    """The same family as |value| / sigma: whether the data produced the number."""
    blocks = {}
    for slug in results.valid(page.cases):
        block = results.knobs(slug)
        block = block[block["suffix"] == suffix].sort_values("s")
        # Method 1 comes off MAD.match and reports no covariance, so it has no
        # significance to draw and a legend entry would read as an all-zero fit.
        if not block.empty and (block["uncertainty"].to_numpy() > 0).any():
            blocks[slug] = block
    if not blocks:
        return []

    family = FAMILIES[suffix]
    figure, axes = panels(1)
    axis = axes[0]
    mark_bpms(axis, results.positions, label=True)
    for (slug, block), colour in zip(blocks.items(), CASE_COLOURS, strict=False):
        sigma = block["uncertainty"].to_numpy()
        significance = np.abs(block["value"].to_numpy()) / np.where(sigma > 0, sigma, np.nan)
        axis.step(block["s"], significance, where="mid", color=colour,
                  linewidth=1.9, alpha=0.9, label=page.label(slug))
    axis.axhline(1.0, color="k", linestyle="--", linewidth=1.0,
                 label="value equals its own error bar")
    axis.set_yscale("log")
    axis.set_xlabel("s [m]")
    axis.set_ylabel(f"|{family.word[:-1]}| / $\\sigma$")
    style_axis(axis)
    axis.legend(fontsize=7, ncols=2)
    legend_headroom(axis)
    name = f"{page.slug}_{suffix.lstrip('.')}_significance.png"
    return [_save(figure, output / name)]


def rereferenced(frame: pd.DataFrame, start: pd.DataFrame,
                 model: pd.DataFrame) -> pd.DataFrame:
    """One case's cached optics, differenced against *model* instead of *start*."""
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


def prefit_vs_matched(start: pd.DataFrame,
                      matched: pd.DataFrame) -> dict[str, tuple]:
    """The un-fitted start model against the matched model: iteration zero."""
    common = start.index.intersection(matched.index)
    start, matched = start.loc[common], matched.loc[common]
    s = start["s"].to_numpy()
    out: dict[str, tuple] = {}
    for plane, beta, mu in (("x", "beta11", "mu1"), ("y", "beta22", "mu2")):
        out[f"beta_beating_{plane}"] = (s, start[beta].to_numpy() / matched[beta].to_numpy() - 1.0)
        out[f"phase_error_{plane}"] = (s, start[mu].to_numpy() - matched[mu].to_numpy())
    for plane in ("x", "y"):
        column = f"d{plane}"
        values = start[column].to_numpy() if column in start.columns else np.zeros(len(start))
        out[f"dispersion_{plane}"] = (s, values)
    for rdt in ("f1001", "f1010"):
        # The start model's own coupling: an RDT amplitude minus another is not
        # a meaningful subtraction.
        if rdt in start.columns:
            out[f"coupling_{rdt}"] = (s, start[rdt].to_numpy())
    out["_elements"] = (s, common.to_numpy())
    return out


def _curve_rms(results: Results, column: str, elements, values,
               measured_beat: pd.Series | None) -> str:
    """One curve's rms, in the convention its quantity uses."""
    quantity = quantity_of(column)
    plane = column[-1] if column[-1] in "xy" else ""
    if column.startswith("dispersion"):
        value = metrics.rms_vs_measured_dispersion(
            elements, values, results.measured_dispersion, plane
        )
    elif column.startswith("coupling"):
        value = metrics.rms_vs_measured(
            elements, values, _measured_rdt(results.measured_optics, column),
            relative=False,
        )
    elif column.startswith("beta_beating"):
        value = metrics.rms_vs_measured(
            elements, values, measured_beat, relative=quantity.relative
        )
    else:
        value = metrics.rms(values)
    return "n/a" if value is None else quantity.fmt.format(value)


def _measured_rdt(measured: pd.DataFrame, column: str) -> pd.Series | None:
    rdt = column.removeprefix("coupling_")
    if measured.empty or rdt not in measured.columns:
        return None
    return measured[rdt]


def _beat_error(frame: pd.DataFrame, beta: str, reference: str):
    if f"{beta}_err" not in frame.columns or reference not in frame.columns:
        return None
    return 100 * frame[f"{beta}_err"] / frame[reference]


def optics(results: Results, page: Page, output: Path) -> list[Path]:
    """What each fit did to the lattice: one figure per quantity, two panels each."""
    frames = {
        slug: results.optics(slug)
        for slug in results.valid(page.cases)
        if not results.optics(slug).empty
    }
    if not frames:
        logger.warning("%s: no cached optics; run scripts/case_optics.py", page.slug)
        return []

    measured = results.measured_optics
    models = {
        name: results.twiss(name)
        for name in ("start-model", "matched-model")
        if not results.twiss(name).empty
    }

    written: list[Path] = []
    for reference, file_suffix in REFERENCES:
        if not measured.empty and f"beat_x_{reference}" not in measured.columns:
            continue
        drawn, prefit = frames, None
        if reference == "matched_model":
            if not {"start-model", "matched-model"} <= set(models):
                logger.warning("%s: no matched-model twiss", page.slug)
                continue
            drawn = {
                slug: rereferenced(frame, models["start-model"], models["matched-model"])
                for slug, frame in frames.items()
            }
            prefit = prefit_vs_matched(models["start-model"], models["matched-model"])
        start_frame = next(iter(drawn.values()))
        for stem, title, columns in OPTICS_FIGURES:
            written.append(_optics_figure(
                results, page, drawn, start_frame, prefit, measured, reference,
                stem, title, columns, output / f"{page.slug}_{stem}{file_suffix}.png",
            ))
    return written


def _optics_figure(results, page, drawn, start_frame, prefit, measured, reference,
                   stem, title, columns, path) -> Path:
    figure, axes = panels(2)
    reference_label = "matched model" if reference == "matched_model" else "start model"
    for index, (axis, column) in enumerate(zip(axes, columns, strict=True)):
        quantity = quantity_of(column)
        plane = column[-1] if column[-1] in "xy" else ""
        mark_bpms(axis, results.positions, label=index == 0)
        axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
        measured_beat = (
            measured[f"beat_{plane}_{reference}"]
            if not measured.empty and f"beat_{plane}_{reference}" in measured.columns
            else None
        )
        if stem == "beta_beating" and not measured.empty:
            _draw_measured_beat(axis, measured, plane, reference)
        if stem in ("coupling", "dispersion"):
            start_column = f"{column}_start"
            if start_column in start_frame.columns:
                axis.plot(start_frame["s"], start_frame[start_column],
                          color=START_COLOUR, linewidth=2.0, linestyle="--",
                          label=reference_label, zorder=1)
        if stem == "dispersion":
            _draw_measured_dispersion(axis, results, plane)
        if stem == "coupling":
            _draw_measured_rdt(axis, measured, column)
        if prefit is not None and column in prefit:
            pre_s, pre_values = prefit[column]
            text = _curve_rms(results, column, prefit["_elements"][1], pre_values,
                              measured_beat)
            axis.plot(pre_s, quantity.scale * pre_values, color=PREFIT_COLOUR,
                      linewidth=1.8, linestyle=":", zorder=2,
                      label=f"pre-fit model, rms {text}")
        for (slug, frame), colour in zip(drawn.items(), CASE_COLOURS, strict=False):
            values = frame[column].to_numpy()
            text = _curve_rms(results, column, frame["element"].to_numpy(), values,
                              measured_beat)
            axis.plot(frame["s"], quantity.scale * values, color=colour,
                      linewidth=1.5, alpha=0.9,
                      label=f"{page.label(slug)}, rms {text}")
        axis.set_ylabel(AXIS_LABEL[column], fontsize=8)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)


def _draw_measured_beat(axis, measured, plane, reference) -> None:
    for beat, beta, marker, style, name in (
        (f"beat_{plane}_{reference}", f"beta_{plane}", "o", {}, "from phase"),
        (f"beat_{plane}_amp_{reference}", f"beta_{plane}_amp", "^",
         {"markerfacecolor": "none"}, "from amplitude"),
    ):
        if beat not in measured.columns:
            continue
        value = 100 * metrics.rms(measured[beat].to_numpy())
        axis.errorbar(
            measured["s"], 100 * measured[beat],
            yerr=_beat_error(measured, beta, f"beta_{plane}_{reference}"),
            fmt=marker, color="k", markersize=5, zorder=4, elinewidth=0.9,
            capsize=2.0, label=f"measured, {name}, rms {value:.1f}%", **style,
        )


def _draw_measured_dispersion(axis, results: Results, plane: str) -> None:
    points = results.measured_dispersion
    points = points[points["plane"] == plane]
    if points.empty:
        return
    axis.errorbar(points["s"], points["measured"], yerr=points.get("uncertainty"),
                  fmt="o", color="k", markersize=5, zorder=4, elinewidth=0.9,
                  capsize=2.0, label="measured, from momentum closed orbits")


def _draw_measured_rdt(axis, measured, column) -> None:
    series = _measured_rdt(measured, column)
    if series is None:
        return
    rdt = column.removeprefix("coupling_")
    axis.errorbar(measured["s"], series, yerr=measured.get(f"{rdt}_err"), fmt="o",
                  color="k", markersize=5, zorder=4, elinewidth=0.9, capsize=2.0,
                  label=f"measured (AC dipole), rms {metrics.rms(series):.2e}")


def residuals(results: Results, page: Page, output: Path) -> list[Path]:
    """What each case failed to explain per BPM: one figure per scored kind."""
    written: list[Path] = []
    for target, axis_label in RESIDUAL_TARGETS.items():
        frames = {
            slug: results.predictions / f"{slug}.{target}.parquet"
            for slug in results.valid(page.cases)
        }
        frames = {
            slug: pd.read_parquet(path) for slug, path in frames.items() if path.exists()
        }
        if not frames:
            continue
        written.append(_residual_figure(
            results, page, frames, target, axis_label,
            output / f"{page.slug}_residuals_{target}.png",
        ))
    if not written:
        logger.warning("%s: no prediction parquets for residuals", page.slug)
    return written


def _residual_figure(results, page, frames, target, axis_label, path) -> Path:
    figure, axes = panels(2)
    bpms: list[str] = []
    for axis, plane in zip(axes, ("x", "y"), strict=True):
        for (slug, frame), colour in zip(frames.items(), CASE_COLOURS, strict=False):
            per_bpm = metrics.per_bpm_rms(frame, plane)
            if per_bpm.empty:
                continue
            bpms = list(per_bpm.index)
            axis.plot(range(len(per_bpm)), per_bpm.to_numpy(), marker="o",
                      markersize=4, linewidth=1.6, color=colour, label=page.label(slug))
        reference = next(iter(frames.values()))
        if bpms and "error" in reference.columns:
            block = reference[reference["plane"] == plane]
            statistical = 1e3 * block.groupby("bpm", sort=False)["error"].mean()
            axis.fill_between(range(len(statistical)), 0.0, statistical.to_numpy(),
                              color="0.55", alpha=0.35, zorder=0,
                              label="measurement standard error of the mean")
            axis.axhline(1e3 * BPM_ZERO_OFFSET, color="0.35", linestyle=":",
                         linewidth=1.3, zorder=0, label="BPM zero-offset systematic")
        axis.set_ylabel(f"{PLANE_WORD[plane]}\n{axis_label}", fontsize=8)
        style_axis(axis)
    if bpms:
        axes[-1].set_xticks(range(len(bpms)), bpms, rotation=90, fontsize=6)
    axes[0].legend(fontsize=6, ncols=2)
    legend_headroom(axes[0])
    return _save(figure, path)


#: The scored measurements, as (scoreboard column stem, tick label).
SCORE_TARGETS = (
    ("delta_x", "delta x"), ("delta_y", "delta y"),
    ("static_x", "static x"), ("static_y", "static y"),
    ("dispersion_x", "disp x"), ("dispersion_y", "disp y"),
)


def scores(results: Results, page: Page, output: Path) -> list[Path]:
    """Residual against each scored measurement, per case, log scale."""
    frame = results.scoreboard
    if frame.empty:
        return []
    rows = [slug for slug in ("start-model", *page.cases) if slug in frame.index]
    if not rows:
        return []

    figure, axes = panels(1)
    axis = axes[0]
    width = 0.8 / len(rows)
    drawn: list[float] = []
    for index, slug in enumerate(rows):
        values = [100 * frame.loc[slug, f"{column}_rel"] for column, _ in SCORE_TARGETS]
        drawn.extend(values)
        offsets = np.arange(len(SCORE_TARGETS)) + (index - (len(rows) - 1) / 2) * width
        colour = "0.45" if slug == "start-model" else CASE_COLOURS[
            (index - 1) % len(CASE_COLOURS)
        ]
        label = "start model — no fit" if slug == "start-model" else page.label(slug)
        axis.bar(offsets, values, width=width * 0.92, color=colour, label=label)
    # Log y: one 3700% bar would otherwise flatten the 0-100% band entirely.
    log_axis(axis, drawn, floor=0.1)
    axis.axhline(100.0, color="k", linewidth=1.2, linestyle="--",
                 label="no information about the measurement")
    axis.set_xticks(range(len(SCORE_TARGETS)))
    axis.set_xticklabels([name for _, name in SCORE_TARGETS])
    axis.set_ylabel("residual rms\n[% of measured amplitude]", fontsize=8)
    axis.legend(fontsize=6, ncols=2)
    legend_headroom(axis, 0.6)
    style_axis(axis)
    return [_save(figure, output / f"{page.slug}_scores.png")]


def _wrap(text: str, width: int = 18) -> str:
    """Break a case label over lines so it fits an axis tick."""
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


def _bar_labels(axis, bars, values, fmt: str) -> None:
    """Print each bar's own value at its end."""
    for bar, value in zip(bars, values, strict=True):
        axis.annotate(
            fmt.format(value),
            (bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height()),
            textcoords="offset points",
            xytext=(0, 3 if bar.get_height() >= 0 else -11),
            ha="center", fontsize=7,
        )


def case_tunes(results: Results, page: Page, output: Path) -> list[Path]:
    """Where every fit on the page put the tune, one panel per plane."""
    summary = results.optics_summary
    if not summary:
        return []
    start = summary["loco_model"]["tunes"]
    measured = summary["measured"]["natural_tunes"]
    spread = summary["measured"].get("natural_tune_spread", [0.0, 0.0])

    labels = ["model\n$k_1$ as sent"]
    tunes = [list(start)]
    colours = ["0.45"]
    matched = summary.get("matched_model", {}).get("tunes")
    if matched:
        labels.append("model\nmatched")
        tunes.append(list(matched))
        colours.append("0.70")
    for index, slug in enumerate(page.cases):
        frame = results.optics(slug)
        if frame.empty:
            continue
        labels.append(_wrap(page.label(slug)))
        tunes.append([
            start[plane] + float(frame[f"phase_error_{axis}"].iloc[-1])
            for plane, axis in ((0, "x"), (1, "y"))
        ])
        colours.append(CASE_COLOURS[index % len(CASE_COLOURS)])
    if len(tunes) < 3:
        return []

    figure, axes = panels(2, sharex=True)
    for plane, (axis, name) in enumerate(zip(axes, ("x", "y"), strict=True)):
        values = [tune[plane] - measured[plane] for tune in tunes]
        bars = axis.bar(range(len(values)), values, color=colours, width=0.62)
        _bar_labels(axis, bars, [tune[plane] for tune in tunes], "{:.4f}")
        axis.axhline(0.0, color="k", linewidth=1.4)
        axis.axhspan(-spread[plane], spread[plane], color="0.5", alpha=0.25, zorder=0)
        axis.set_ylabel(f"$Q_{name}$ - measured\n({measured[plane]:.4f})", fontsize=8)
        style_axis(axis)
    axes[-1].set_xticks(range(len(labels)))
    axes[-1].set_xticklabels(labels, fontsize=7)
    return [_save(figure, output / f"{page.slug}_case_tunes.png")]


#: The two Dp/p calibrations the measured chromaticity is scored against. A
#: case's own fit is one number; only the reference it is judged against moves.
CALIBRATIONS = (
    ("dq_dpt", "dq_dpt_error", "XImeter Dp/p", ""),
    ("dq_dpt_closed_orbit", "dq_dpt_closed_orbit_error", "closed-orbit Dp/p", "//"),
)


def _qprime_factor(summary: dict) -> float:
    """beta, from the summary's own Q' and dq pair: Q' = beta * dq / Q."""
    model = summary["loco_model"]
    ratios = [q / dq for q, dq in zip(model["qprime"], model["dq_dpt"]) if dq]
    return float(np.mean(ratios)) if ratios else 1.0


def case_chromaticity(results: Results, page: Page, output: Path) -> list[Path]:
    """Measured, start-model and fitted-lattice Q'H / Q'V per page."""
    from matplotlib.patches import Patch

    summary = results.optics_summary
    if not summary:
        return []
    beta = _qprime_factor(summary)
    measured = {key: [beta * v for v in summary["measured"][key]]
                for key, _, _, _ in CALIBRATIONS}
    error = {key: [beta * v for v in summary["measured"][error_key]]
             for key, error_key, _, _ in CALIBRATIONS}
    model = [beta * v for v in summary["loco_model"]["dq_dpt"]]

    cases = []
    for index, slug in enumerate(page.cases):
        frame = results.optics(slug)
        if frame.empty or not {"dq_dpt_x", "dq_dpt_y"} <= set(frame.columns):
            continue
        cases.append((
            _wrap(page.label(slug)),
            [beta * float(frame["dq_dpt_x"].iloc[0]),
             beta * float(frame["dq_dpt_y"].iloc[0])],
            CASE_COLOURS[index % len(CASE_COLOURS)],
        ))
    if not cases:
        return []

    labels = ["measured", "model\n$k_1$ as sent", *(label for label, _, _ in cases)]
    width = 0.82 / len(CALIBRATIONS)

    figure, axes = panels(2, sharex=True)
    for plane, (axis, name) in enumerate(zip(axes, ("H", "V"), strict=True)):
        for index, (key, _, _, hatch) in enumerate(CALIBRATIONS):
            offset = (index - (len(CALIBRATIONS) - 1) / 2) * width
            values = [measured[key][plane], model[plane],
                      *(q[plane] for _, q, _ in cases)]
            heights = [value - measured[key][plane] for value in values]
            colours = ["k", "0.45", *(colour for _, _, colour in cases)]
            bars = axis.bar([x + offset for x in range(len(heights))], heights,
                            width=width, color=colours, hatch=hatch,
                            edgecolor="white", linewidth=0.5)
            _bar_labels(axis, bars, heights, "{:+.3f}")
        axis.axhline(0.0, color="k", linewidth=1.2)
        for key, _, _, _ in CALIBRATIONS:
            axis.axhspan(-error[key][plane], error[key][plane], color="k",
                         alpha=0.08, zorder=0)
        axis.set_ylabel(f"$Q'_{name}$ - measured", fontsize=9)
        style_axis(axis)
    axes[-1].set_xticks(range(len(labels)))
    axes[-1].set_xticklabels(labels, fontsize=7)
    axes[0].legend(
        handles=[Patch(facecolor="0.7", hatch=hatch, edgecolor="white", label=label)
                 for _, _, label, hatch in CALIBRATIONS],
        loc="upper left", fontsize=7, framealpha=0.9,
    )
    legend_headroom(axes[0])
    return [_save(figure, output / f"{page.slug}_case_chromaticity.png")]


#: The two reference lattices the measured optics is drawn against.
MEASURED_REFERENCES = (
    ("loco_model", "", "LOCO start model (un-matched)"),
    ("matched_model", "_matched", "same lattice, tunes matched to the measurement"),
)
REFERENCE_LABELS = {key: label for key, _, label in MEASURED_REFERENCES}


def measured_optics(results: Results, output: Path) -> list[Path]:
    """Measured beta, beta-beating and coupling against each reference lattice."""
    frame = results.measured_optics
    if frame.empty:
        return []
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for reference, file_suffix, label in MEASURED_REFERENCES:
        if f"beta_x_{reference}" not in frame.columns:
            continue
        written.append(_measured_beta(results, frame, reference, label,
                                      output / f"measured_beta{file_suffix}.png"))
        written.append(_measured_beat(results, frame, reference, label,
                                      output / f"measured_beat{file_suffix}.png"))
        coupling = _measured_coupling(results, frame, reference,
                                     output / f"measured_coupling{file_suffix}.png")
        if coupling is not None:
            written.append(coupling)
    return written


def _measured_beta(results, frame, reference, label, path) -> Path:
    figure, axes = panels(2)
    other = "loco_model" if reference != "loco_model" else "matched_model"
    for index, (axis, plane) in enumerate(zip(axes, ("x", "y"), strict=True)):
        mark_bpms(axis, results.positions, label=index == 0)
        axis.errorbar(frame["s"], frame[f"beta_{plane}"],
                      yerr=frame.get(f"beta_{plane}_err"), fmt="o",
                      color=CASE_COLOURS[0], markersize=5, linewidth=1.2,
                      label="measured, from phase", zorder=3)
        # Amplitude beta needs the BPM gains phase beta does not: drawn open.
        if f"beta_{plane}_amp" in frame.columns:
            axis.errorbar(frame["s"], frame[f"beta_{plane}_amp"],
                          yerr=frame.get(f"beta_{plane}_amp_err"), fmt="^",
                          color=CASE_COLOURS[1], markersize=6, linewidth=1.2,
                          markerfacecolor="none", zorder=3,
                          label="measured, from amplitude")
        axis.plot(frame["s"], frame[f"beta_{plane}_{reference}"], color="0.20",
                  linewidth=2.0, linestyle="--", label=label)
        if f"beta_{plane}_{other}" in frame.columns:
            axis.plot(frame["s"], frame[f"beta_{plane}_{other}"], color="0.60",
                      linewidth=1.2, linestyle=":", alpha=0.9,
                      label=REFERENCE_LABELS[other])
        axis.set_ylabel(f"$\\beta_{plane}$ [m]", fontsize=9)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)


def _measured_beat(results, frame, reference, label, path) -> Path:
    figure, axes = panels(2)
    for index, (axis, plane) in enumerate(zip(axes, ("x", "y"), strict=True)):
        mark_bpms(axis, results.positions, label=index == 0)
        axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
        # The reference is a model, so the beating's bar is the measured beta's
        # divided by that model: the same fraction, moved.
        axis.errorbar(frame["s"], 100 * frame[f"beat_{plane}_{reference}"],
                      yerr=_beat_error(frame, f"beta_{plane}",
                                       f"beta_{plane}_{reference}"),
                      fmt="o-", color="0.20", markersize=5, linewidth=1.6,
                      zorder=3, elinewidth=0.9, capsize=2.0,
                      label=f"from phase, against {label}")
        amplitude = f"beat_{plane}_amp_{reference}"
        if amplitude in frame.columns:
            axis.errorbar(frame["s"], 100 * frame[amplitude],
                          yerr=_beat_error(frame, f"beta_{plane}_amp",
                                           f"beta_{plane}_{reference}"),
                          fmt="^--", color="0.45", markersize=6, linewidth=1.2,
                          markerfacecolor="none", zorder=2, elinewidth=0.9,
                          capsize=2.0, label="from amplitude")
        axis.set_ylabel(f"{PLANE_WORD[plane]}\nbeta-beating [%]", fontsize=8)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)


def _measured_coupling(results, frame, reference, path) -> Path | None:
    rdts = [rdt for rdt in ("f1001", "f1010") if rdt in frame.columns]
    if not rdts:
        return None
    figure, axes = panels(len(rdts))
    for index, (axis, rdt) in enumerate(zip(axes, rdts, strict=True)):
        mark_bpms(axis, results.positions, label=index == 0)
        axis.errorbar(frame["s"], frame[rdt], yerr=frame.get(f"{rdt}_err"),
                      fmt="o", color="k", markersize=5, zorder=3, elinewidth=0.9,
                      capsize=2.0, label=f"measured, rms {metrics.rms(frame[rdt]):.2e}")
        model = f"{rdt}_{reference}"
        if model in frame.columns:
            axis.plot(frame["s"], frame[model], color="0.35", linewidth=2.0,
                      linestyle="--", label=REFERENCE_LABELS[reference])
        axis.set_ylabel(f"$|f_{{{rdt[1:]}}}|$", fontsize=9)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)
