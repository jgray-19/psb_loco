"""Docs-style figures for phase_advance_constraint/experiment.py's fitted cases.

Per campaign: beta_beating / phase_error / dispersion / coupling PNGs against the un-fitted
machine-knob model; phase_advance (BPM-to-BPM mu1/mu2 against the measured file, at 0Hz); and
orbit (model X/Y at the fitted knobs against the measured closed orbit).

Usage:
    python -m phase_advance_constraint.plot_experiment --campaign p17_p23_final \
        --labels orbit_only orbit_plus_phase orbit_plus_phase_10x
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# psb_md's regular `scripts` package would shadow this repo's namespace `scripts` (PEP 420);
# import scripts.case_optics first so sys.modules caches the right one.
from scripts.case_optics import _twiss, case_optics  # noqa: E402

sys.path.insert(0, "/afs/cern.ch/work/j/jmgray/private/psb_md")

import numpy as np
import pandas as pd
from psb_md.plots import save_figure, style_axis

from loco_common.campaign import campaign_by_slug
from loco_common.measured_response import (
    cached_scan,
    global_reference_orbit,
)
from loco_common.model import build_model
from loco_report.style import (
    CASE_COLOURS,
    MEASURED_BPM_RE,
    legend_headroom,
    mark_bpms,
    panels,
    quantity_of,
)

SEQUENCE_FILE = "/afs/cern.ch/work/j/jmgray/private/psb_loco/models/model_qx0.165000_qy0.227500/psb3_saved.seq"
RESULTS_DIR = Path("/afs/cern.ch/work/j/jmgray/private/psb_loco/results/phase_advance_experiment")
OUT_ROOT = Path("/afs/cern.ch/work/j/jmgray/private/psb_loco/plots/phase_advance_experiment")

CACHE_HIO_DIR_BY_CAMPAIGN = {
    "p17_p23_final": (
        "/afs/cern.ch/work/j/jmgray/private/psb_md/"
        ".psb_cache_p17_p23_final_dynamic_demodulated_no_interference_comb_notch_no_ripple/hio"
    ),
    "p23_p13_final": (
        "/afs/cern.ch/work/j/jmgray/private/psb_md/"
        ".psb_cache_p23_p13_final_dynamic_demodulated_no_interference_comb_notch_no_ripple/hio"
    ),
}

OPTICS_FIGURES = (
    ("beta_beating", "beta_beating_x", "beta_beating_y", "beta-beating [%]"),
    ("phase_error", "phase_error_x", "phase_error_y", "phase error [$2\\pi$]"),
    ("dispersion", "dispersion_x", "dispersion_y", "$D$ [m]"),
    ("coupling", "coupling_f1001", "coupling_f1010", "$|f|$"),
)


def read_tfs(path: Path) -> pd.DataFrame:
    header = None
    rows = []
    with open(path) as handle:
        for line in handle:
            if line.startswith("*"):
                header = line[1:].split()
            elif line.startswith("$") or line.startswith("@"):
                continue
            else:
                rows.append(line.split())
    frame = pd.DataFrame(rows, columns=header)
    for col in frame.columns:
        if col in ("NAME", "NAME2"):
            frame[col] = frame[col].str.strip('"')
        else:
            frame[col] = frame[col].astype(float)
    return frame


def load_knobs_series(label: str) -> pd.Series:
    payload = json.loads((RESULTS_DIR / f"{label}.json").read_text())
    return pd.Series(payload["knobs"], name="value")


def plot_optics_family(model, campaign_slug: str, labels: list[str], output: Path) -> None:
    start = _twiss(model, None)
    positions = start["s"].to_dict()

    frames = {}
    for label in labels:
        knobs = load_knobs_series(label)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            knobs.rename_axis("knob").reset_index().to_csv(handle, index=False)
            csv_path = Path(handle.name)
        frames[label] = case_optics(model, csv_path, start)
        csv_path.unlink()

    for stem, col_x, col_y, ylabel in OPTICS_FIGURES:
        figure, axes = panels(2)
        for axis, column, plane in zip(axes, (col_x, col_y), ("x", "y"), strict=True):
            if not all(column in frame.columns for frame in frames.values()):
                continue
            quantity = quantity_of(column)
            mark_bpms(axis, positions, label=plane == "x")
            axis.axhline(0.0, color="k", linewidth=0.8, alpha=0.5)
            for (label, frame), colour in zip(frames.items(), CASE_COLOURS, strict=False):
                axis.plot(frame["s"], quantity.scale * frame[column], color=colour,
                          linewidth=1.5, alpha=0.9, label=label)
            axis.set_ylabel(f"{plane}\n{ylabel}", fontsize=8)
            style_axis(axis)
        axes[-1].set_xlabel("s [m]")
        axes[0].legend(fontsize=7, ncols=2, loc="upper left")
        legend_headroom(axes[0])
        save_figure(figure, output / f"{campaign_slug}_{stem}.png")
    print(f"wrote {campaign_slug} beta_beating/phase_error/dispersion/coupling to {output}")


def _phase_advance_from_mu(mu: pd.Series, s: pd.Series):
    bpms = [name for name in mu.index if MEASURED_BPM_RE.match(str(name).upper())]
    ordered = sorted(bpms, key=lambda name: s.loc[name])
    values = mu.loc[ordered].to_numpy()
    positions = s.loc[ordered].to_numpy()
    return positions[1:], np.diff(values)


def plot_phase_advance(model, campaign_slug: str, labels: list[str], output: Path) -> None:
    cache_hio_dir = CACHE_HIO_DIR_BY_CAMPAIGN[campaign_slug]
    figure, axes = panels(2)
    for index, (axis, plane, mu_col, tfs_name) in enumerate(
        zip(axes, ("x", "y"), ("mu1", "mu2"), ("phase_x.tfs", "phase_y.tfs"), strict=True)
    ):
        measured = read_tfs(Path(cache_hio_dir) / "0Hz_undriven" / tfs_name)
        col = "PHASEX" if plane == "x" else "PHASEY"
        err = "ERRPHASEX" if plane == "x" else "ERRPHASEY"
        axis.errorbar(measured["S2"], measured[col], yerr=measured[err], fmt="o",
                      color="k", markersize=5, zorder=4, elinewidth=0.9,
                      capsize=2.0, label="measured")
        for (label, _), colour in zip(
            ((label, None) for label in labels), CASE_COLOURS, strict=False
        ):
            knobs = load_knobs_series(label)
            twiss = _twiss(model, knobs)
            s, advance = _phase_advance_from_mu(twiss[mu_col], twiss["s"])
            axis.plot(s, advance, color=colour, linewidth=1.5, alpha=0.9, label=label)
        axis.set_ylabel(f"{plane}\nBPM-to-BPM phase advance [$2\\pi$]", fontsize=8)
        style_axis(axis)
        if index == 0:
            axis.legend(fontsize=7, ncols=2, loc="upper left")
    axes[-1].set_xlabel("s [m]")
    legend_headroom(axes[0])
    path = output / f"{campaign_slug}_phase_advance.png"
    save_figure(figure, path)
    print(f"wrote {path}")


def plot_orbit(model, campaign_slug: str, labels: list[str], output: Path) -> None:
    campaign = campaign_by_slug(campaign_slug)
    points, orbit_by_path = cached_scan(campaign=campaign)
    measured = global_reference_orbit(points, orbit_by_path)

    figure, axes = panels(2)
    for index, (axis, plane, col) in enumerate(
        zip(axes, ("x", "y"), ("X", "Y"), strict=True)
    ):
        err = measured[f"ERR{col}"] if f"ERR{col}" in measured.columns else None
        axis.errorbar(range(len(measured)), measured[col], yerr=err, fmt="o",
                      color="k", markersize=5, zorder=4, elinewidth=0.9,
                      capsize=2.0, label="measured")
        for (label, colour) in zip(labels, CASE_COLOURS, strict=False):
            knobs = load_knobs_series(label)
            twiss = _twiss(model, knobs)
            values = twiss.reindex(measured.index)[col.lower()]
            axis.plot(range(len(measured)), values, color=colour, linewidth=1.5,
                      alpha=0.9, label=label)
        axis.set_ylabel(f"{plane} [m]", fontsize=8)
        style_axis(axis)
        if index == 0:
            axis.legend(fontsize=7, ncols=2, loc="upper left")
    axes[-1].set_xlabel("BPM index")
    legend_headroom(axes[0])
    path = output / f"{campaign_slug}_orbit.png"
    save_figure(figure, path)
    print(f"wrote {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, choices=sorted(CACHE_HIO_DIR_BY_CAMPAIGN))
    parser.add_argument("--labels", nargs="+", required=True)
    args = parser.parse_args()

    campaign = campaign_by_slug(args.campaign)
    model = build_model(sequence_file=SEQUENCE_FILE, campaign=campaign)

    output = OUT_ROOT / args.campaign
    output.mkdir(parents=True, exist_ok=True)
    plot_optics_family(model, args.campaign, args.labels, output)
    plot_phase_advance(model, args.campaign, args.labels, output)
    plot_orbit(model, args.campaign, args.labels, output)


if __name__ == "__main__":
    main()
