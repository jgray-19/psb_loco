"""Figure builders. Each writes at most a two-panel, page-width PNG."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from psb_md.plots import save_figure, style_axis

from loco_common.case_names import Page
from loco_report import metrics
from loco_report.data import RESIDUAL_TARGETS, Results
from loco_report.style import (
    CASE_COLOURS,
    FAMILIES,
    MAX_PANELS,
    MEASURED_BPM_RE,
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
    save_figure(figure, path)
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
    # Cases beyond the panel cap spill into numbered figures.
    items = list(blocks.items())
    chunks = [items[i:i + MAX_PANELS] for i in range(0, len(items), MAX_PANELS)]
    written = []
    for index, chunk in enumerate(chunks):
        part = "" if len(chunks) == 1 else f"_{index + 1}"
        written.append(_family_panel(
            results, page, family, chunk,
            output / f"{page.slug}_{suffix.lstrip('.')}_by_s{part}.png",
        ))
    return written


def _family_panel(results, page, family, blocks, path) -> Path:
    figure, axes = panels(len(blocks), sharey=True)
    for axis, (slug, block) in zip(axes, blocks, strict=True):
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
            *legend_handles(pd.concat([b for _, b in blocks])["element"]),
            Line2D([], [], color="0.55", linestyle="--", linewidth=0.7, label="BPM"),
        ],
        fontsize=7, ncols=4, loc="upper left",
    )
    legend_headroom(axes[0])
    return _save(figure, path)


def gains(results: Results, page: Page, output: Path) -> list[Path]:
    """Corrector gains by corrector, and BPM gains against s, for the cases that fitted them."""
    fitted = {slug: results.gains(slug) for slug in results.valid(page.cases)}
    fitted = {slug: gain for slug, gain in fitted.items() if not gain.empty}
    if not fitted:
        return []
    figure, axes = panels(2, sharex=False)
    correctors = sorted(
        {name for gain in fitted.values() for name in gain.index if name.startswith("corrgain.")},
        key=lambda name: (name.split(".")[1][:3] != "DHZ", name),
    )
    positions = np.arange(len(correctors))
    width = 0.8 / len(fitted)
    for index, ((slug, gain), colour) in enumerate(zip(fitted.items(), CASE_COLOURS, strict=False)):
        axes[0].bar(positions + (index - (len(fitted) - 1) / 2) * width,
                    [gain.get(name, np.nan) for name in correctors],
                    width=width, color=colour, alpha=0.85, label=page.label(slug))
    axes[0].axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
    axes[0].set_xticks(positions, [name.split(".")[1] for name in correctors], rotation=45, fontsize=7)
    axes[0].set_ylabel("corrector kick gain $g$", fontsize=8)
    axes[0].legend(fontsize=7)
    legend_headroom(axes[0])
    style_axis(axes[0])
    for (slug, gain), colour in zip(fitted.items(), CASE_COLOURS, strict=False):
        for plane, marker in (("x", "o"), ("y", "s")):
            names = [n for n in gain.index if n.startswith(f"bpmgain.{plane}.")]
            s = [results.positions.get(n.split(".", 2)[2], np.nan) for n in names]
            axes[1].plot(s, gain[names].to_numpy(), marker, color=colour, alpha=0.85,
                         label=f"{PLANE_WORD[plane]}")
    axes[1].axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
    axes[1].set_xlabel("s [m]")
    axes[1].set_ylabel("BPM gain $b$", fontsize=8)
    axes[1].legend(fontsize=7, ncols=2)
    legend_headroom(axes[1])
    style_axis(axes[1])
    return [_save(figure, output / f"{page.slug}_gains.png")]


def family_significance(results: Results, page: Page, suffix: str,
                        output: Path) -> list[Path]:
    """The same family as |value| / sigma: whether the data produced the number."""
    blocks = {}
    for slug in results.valid(page.cases):
        block = results.knobs(slug)
        block = block[block["suffix"] == suffix].sort_values("s")
        # A fit with no covariance (NaN sigma) has no significance to draw.
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
    """The un-fitted machine-knob model against the matched model: iteration zero."""
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
        # An RDT amplitude minus another is not meaningful, so draw the model's own coupling.
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


def _fitted_optics(results: Results, page: Page):
    """Each fitted case's cached optics with the start and matched model twiss, or None."""
    frames = {}
    for slug in results.valid(page.cases):
        frame = results.optics(slug)
        if not frame.empty:
            frames[slug] = frame
    if not frames:
        logger.warning("%s: no cached optics; run scripts/case_optics.py", page.slug)
        return None
    start, matched = results.twiss("start-model"), results.twiss("matched-model")
    if start.empty or matched.empty:
        logger.warning("%s: no matched-model twiss", page.slug)
        return None
    return frames, start, matched


def optics(results: Results, page: Page, output: Path) -> list[Path]:
    """What each fit did to the lattice: one figure per quantity, two panels each."""
    fitted = _fitted_optics(results, page)
    if fitted is None:
        return []
    frames, start, matched = fitted
    # Only the tune-matched reference; the machine-knob model is already the dotted curve.
    measured = results.measured_optics
    if not measured.empty and f"beat_x_{MEASURED_REFERENCE}" not in measured.columns:
        return []

    drawn = {slug: rereferenced(frame, start, matched) for slug, frame in frames.items()}
    prefit = prefit_vs_matched(start, matched)
    start_frame = next(iter(drawn.values()))
    return [
        _optics_figure(
            results, page, drawn, start_frame, prefit, measured, MEASURED_REFERENCE,
            stem, columns, output / f"{page.slug}_{stem}_matched.png",
        )
        for stem, _title, columns in OPTICS_FIGURES
    ]


def _phase_advance_from_mu(mu: pd.Series, s: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """The BPM-to-BPM phase advance of the 16 measured BPMs, at the downstream BPM's ``s``."""
    bpms = [name for name in mu.index if MEASURED_BPM_RE.match(str(name).upper())]
    ordered = sorted(bpms, key=lambda name: s.loc[name])
    values = mu.loc[ordered].to_numpy()
    positions = s.loc[ordered].to_numpy()
    return positions[1:], np.diff(values)


def phase_advance(results: Results, page: Page, output: Path) -> list[Path]:
    """BPM-to-BPM phase advance, computed from each case's fitted lattice."""
    fitted = _fitted_optics(results, page)
    if fitted is None:
        return []
    frames, start, matched = fitted
    measured = results.measured_phase

    figure, axes = panels(2)
    for index, (axis, plane, mu) in enumerate(
        zip(axes, ("x", "y"), ("mu1", "mu2"), strict=True)
    ):
        mark_bpms(axis, results.positions, label=index == 0)
        ref_s, ref_advance = _phase_advance_from_mu(matched[mu], matched["s"])
        axis.plot(ref_s, ref_advance, color=START_COLOUR, linewidth=2.0,
                  linestyle="--", zorder=1, label="matched model")
        pre_s, pre_advance = _phase_advance_from_mu(start[mu], start["s"])
        axis.plot(pre_s, pre_advance, color=PREFIT_COLOUR, linewidth=1.8,
                  linestyle=":", zorder=2, label="machine-knob model, un-fitted")
        if not measured.empty and f"phase_{plane}" in measured.columns:
            axis.errorbar(measured["s"], measured[f"phase_{plane}"],
                          yerr=measured.get(f"phase_{plane}_err"), fmt="o",
                          color="k", markersize=5, zorder=4, elinewidth=0.9,
                          capsize=2.0, label="measured")
        for (slug, frame), colour in zip(frames.items(), CASE_COLOURS, strict=False):
            aligned = frame.set_index("element")
            fitted_mu = aligned[f"phase_error_{plane}"] + start[mu].reindex(aligned.index)
            case_s, case_advance = _phase_advance_from_mu(fitted_mu, start["s"])
            axis.plot(case_s, case_advance, color=colour, linewidth=1.5, alpha=0.9,
                      zorder=3, label=page.label(slug))
        axis.set_ylabel(f"{PLANE_WORD[plane]}\nphase advance [$2\\pi$]", fontsize=8)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return [_save(figure, output / f"{page.slug}_phase_advance_matched.png")]


def _optics_figure(results, page, drawn, start_frame, prefit, measured, reference,
                   stem, columns, path) -> Path:
    figure, axes = panels(2)
    reference_label = "matched model"
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
        if column in prefit:
            pre_s, pre_values = prefit[column]
            text = _curve_rms(results, column, prefit["_elements"][1], pre_values,
                              measured_beat)
            axis.plot(pre_s, quantity.scale * pre_values, color=PREFIT_COLOUR,
                      linewidth=1.8, linestyle=":", zorder=2,
                      label=f"machine-knob model, un-fitted, rms {text}")
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
            page, frames, axis_label,
            output / f"{page.slug}_residuals_{target}.png",
        ))
    if not written:
        logger.warning("%s: no prediction parquets for residuals", page.slug)
    return written


def _residual_figure(page, frames, axis_label, path) -> Path:
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
        label = "machine-knob model — no fit" if slug == "start-model" else page.label(slug)
        axis.bar(offsets, values, width=width * 0.92, color=colour, label=label)
    # Log y: one 3700% bar would otherwise flatten the 0-100% band entirely.
    log_axis(axis, drawn, floor=0.1)
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
        # ``annotate`` does not autoscale: include the measurement band and leave room for labels at both ends.
        low = min(0.0, -spread[plane], *values)
        high = max(0.0, spread[plane], *values)
        span = max(high - low, 1e-9)
        axis.set_ylim(low - 0.18 * span, high + 0.20 * span)
        style_axis(axis)
    axes[-1].set_xticks(range(len(labels)))
    axes[-1].set_xticklabels(labels, fontsize=7)
    return [_save(figure, output / f"{page.slug}_case_tunes.png")]


#: The two Dp/p calibrations the measured chromaticity is scored against.
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
    """Measured, machine-knob and fitted-lattice Q'H / Q'V per page."""
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


#: The reference lattice the measured optics is drawn against (tunes matched).
MEASURED_REFERENCE = "matched_model"
MEASURED_REFERENCE_LABEL = "model, tunes matched to the measurement"


def measured_optics(results: Results, output: Path) -> list[Path]:
    """Measured beta, beta-beating and coupling, against the matched model."""
    frame = results.measured_optics
    if frame.empty:
        return []
    output.mkdir(parents=True, exist_ok=True)
    written = [
        _measured_beta(results, frame, output / "measured_beta.png"),
        _measured_beat(results, frame, output / "measured_beat.png"),
    ]
    coupling = _measured_coupling(results, frame, output / "measured_coupling.png")
    if coupling is not None:
        written.append(coupling)
    phase = _measured_phase(results, output / "measured_phase.png")
    if phase is not None:
        written.append(phase)
    return written


def _measured_beta(results, frame, path) -> Path:
    figure, axes = panels(2)
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
        column = f"beta_{plane}_{MEASURED_REFERENCE}"
        if column in frame.columns:
            axis.plot(frame["s"], frame[column], color="0.20",
                      linewidth=2.0, linestyle="--", label=MEASURED_REFERENCE_LABEL)
        axis.set_ylabel(f"$\\beta_{plane}$ [m]", fontsize=9)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)


def _measured_beat(results, frame, path) -> Path:
    figure, axes = panels(2)
    for index, (axis, plane) in enumerate(zip(axes, ("x", "y"), strict=True)):
        mark_bpms(axis, results.positions, label=index == 0)
        axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
        # Bar is the measured beta's error over the model beta.
        beat = f"beat_{plane}_{MEASURED_REFERENCE}"
        if beat in frame.columns:
            axis.errorbar(frame["s"], 100 * frame[beat],
                          yerr=_beat_error(frame, f"beta_{plane}",
                                           f"beta_{plane}_{MEASURED_REFERENCE}"),
                          fmt="o--", color="0.20", markersize=5, linewidth=2.0,
                          zorder=3, elinewidth=0.9, capsize=2.0,
                          label=f"from phase, against {MEASURED_REFERENCE_LABEL}")
            amplitude = f"beat_{plane}_amp_{MEASURED_REFERENCE}"
            if amplitude in frame.columns:
                axis.errorbar(frame["s"], 100 * frame[amplitude],
                              yerr=_beat_error(frame, f"beta_{plane}_amp",
                                               f"beta_{plane}_{MEASURED_REFERENCE}"),
                              fmt="^--", color="0.20", markersize=6,
                              linewidth=1.4, markerfacecolor="none",
                              zorder=2, elinewidth=0.9, capsize=2.0,
                              label=f"from amplitude, against {MEASURED_REFERENCE_LABEL}")
        axis.set_ylabel(f"{PLANE_WORD[plane]}\nbeta-beating [%]", fontsize=8)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)


def _measured_coupling(results, frame, path) -> Path | None:
    rdts = [rdt for rdt in ("f1001", "f1010") if rdt in frame.columns]
    if not rdts:
        return None
    figure, axes = panels(len(rdts))
    for index, (axis, rdt) in enumerate(zip(axes, rdts, strict=True)):
        mark_bpms(axis, results.positions, label=index == 0)
        axis.errorbar(frame["s"], frame[rdt], yerr=frame.get(f"{rdt}_err"),
                      fmt="o", color="k", markersize=5, zorder=3, elinewidth=0.9,
                      capsize=2.0, label=f"measured, rms {metrics.rms(frame[rdt]):.2e}")
        column = f"{rdt}_{MEASURED_REFERENCE}"
        if column in frame.columns:
            axis.plot(frame["s"], frame[column], color="0.20", linewidth=2.0,
                      linestyle="--", label=MEASURED_REFERENCE_LABEL)
        axis.set_ylabel(f"$|f_{{{rdt[1:]}}}|$", fontsize=9)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)


def _measured_phase(results, path) -> Path | None:
    """Measured phase advance between adjacent BPMs, against the matched model."""
    frame = results.measured_phase
    if frame.empty:
        return None
    figure, axes = panels(2)
    for index, (axis, plane) in enumerate(zip(axes, ("x", "y"), strict=True)):
        mark_bpms(axis, results.positions, label=index == 0)
        axis.errorbar(frame["s"], frame[f"phase_{plane}"],
                      yerr=frame.get(f"phase_{plane}_err"), fmt="o",
                      color=CASE_COLOURS[0], markersize=5, linewidth=1.2,
                      zorder=3, elinewidth=0.9, capsize=2.0, label="measured")
        column = f"phase_{plane}_{MEASURED_REFERENCE}"
        if column in frame.columns:
            axis.plot(frame["s"], frame[column], color="0.20",
                      linewidth=2.0, linestyle="--", label=MEASURED_REFERENCE_LABEL)
        axis.set_ylabel(f"{PLANE_WORD[plane]}\nphase advance [$2\\pi$]", fontsize=8)
        style_axis(axis)
    axes[-1].set_xlabel("s [m]")
    axes[0].legend(fontsize=6, ncols=2, loc="upper left")
    legend_headroom(axes[0])
    return _save(figure, path)
