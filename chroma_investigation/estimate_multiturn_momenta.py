"""Estimate Dp/p at each blank-acquisition RF offset from multiturn closed orbits.

The 2026-08-16 MD took "blank" (no AC-dipole, no LOCO corrector kick) multiturn
acquisitions at three RF-steering settings -- ``0mm``, ``2mm``, ``m2mm`` -- under
``blank_acquisitions/``. This mirrors the LOCO scan's RF-offset convention, but
there is no per-orbit orbit-acquisition average for these files, only raw
turn-by-turn BPM positions. This script turns each file's turn-mean into a
closed orbit exactly as ``loco_common.measured_response.closed_orbit`` already
does for the LOCO scan, averages repeat visits within a folder, and projects
the 2mm/m2mm orbits onto the model dispersion relative to the 0mm orbit with
``tmom_recon``'s own model-based estimator (``loco_common.momentum.estimate_pt``
/ ``frame_from_orbit``) -- the same machinery ``loco_common/momentum.py`` uses
for Method 2's multi-``pt`` mode, not a re-derived projection.

The model is matched to the machine's own measured tune for this configuration,
``MachineConfig.QDE_ERRORS_ASYM_P23_P13`` -- the "asym QDE" lattice the sibling
``tune_and_chroma/asym_qde_errors.txt`` XImeter export was also taken on -- with
no scanned correctors, matching these unkicked blanks.

``asym_qde_errors.txt`` gives an independent, RF-derived Dp/p for the same three
settings via ``psb_md.tune_measurements.load_orbit_tune_table``, banded on the
same integer-mm convention the LOCO scan's chroma files use
(``loco_common.momentum.chroma_pt_by_rf_offset``). The two Dp/p estimates --
orbit/model dispersion, and RF/XImeter -- are written side by side so they can
be compared, exactly as ``analyse.py`` compares its own two calibrations.

    MPLCONFIGDIR=/tmp .venv/bin/python chroma_investigation/estimate_multiturn_momenta.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loco_common.measured_response import closed_orbit
from loco_common.model import build_model, model_twiss
from loco_common.momentum import estimate_pt, frame_from_orbit

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
MULTITURN_ROOT = Path("/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_16_Multiturn")
BLANK_DIR = MULTITURN_ROOT / "blank_acquisitions"
CHROMA_FILE = MULTITURN_ROOT / "tune_and_chroma" / "asym_qde_errors.txt"

#: Folder name -> RF-steering offset in mm, the LOCO scan's own convention.
OFFSETS_MM: dict[str, float] = {"0mm": 0.0, "2mm": 2.0, "m2mm": -2.0}

MASS_GEV = 0.93827208816
KINETIC_ENERGY_GEV = 0.160
GAMMA = 1.0 + KINETIC_ENERGY_GEV / MASS_GEV
INV_GAMMA2 = 1.0 / GAMMA**2


def average_closed_orbit(folder: Path) -> pd.DataFrame:
    """Average the closed orbit over every repeat acquisition in *folder*.

    Each file's own turn-mean (``closed_orbit``) is one repeat visit to this
    RF-offset setting; the spread across repeats -- not a single file's
    turn-to-turn SEM -- is what sets the point-to-point reproducibility, so the
    reported uncertainty here is the standard error of the file means, the same
    repeat-plateau convention ``chroma_investigation/analyse.py`` already uses.
    """
    files = sorted(folder.glob("MULTITURN_ACQ__*.sdds"))
    if not files:
        raise FileNotFoundError(f"No multiturn acquisitions found in {folder}")
    per_plane_files = {"X": [], "Y": []}
    for path in files:
        orbit = closed_orbit(path)
        for plane in ("X", "Y"):
            per_plane_files[plane].append(orbit[plane][0])  # per-file turn-mean
    columns = {}
    for plane in ("X", "Y"):
        stacked = pd.concat(per_plane_files[plane], axis=1)
        columns[plane] = stacked.mean(axis=1)
        columns[f"{plane}_sem"] = stacked.std(axis=1, ddof=1) / np.sqrt(stacked.shape[1])
    frame = pd.DataFrame(columns)
    frame.index.name = "bpm"
    frame.attrs["n_files"] = len(files)
    return frame


def reference_dpp_by_offset() -> dict[float, float]:
    """RF/XImeter Dp/p for each offset, from ``asym_qde_errors.txt``.

    Rebased to the 0 mm plateau the same way as
    ``loco_common.momentum.chroma_pt_by_rf_offset``: the export carries an
    absolute machine readback, and only the relative deviation from the 0 mm
    band is the quantity comparable to the orbit-based estimate below.
    """
    from psb_md.defaults import DPP_PER_MM
    from psb_md.tune_measurements import load_orbit_tune_table

    table = load_orbit_tune_table(CHROMA_FILE, dpp_per_index=DPP_PER_MM)
    missing = sorted(int(mm) for mm in OFFSETS_MM.values() if int(mm) not in table)
    if missing:
        raise KeyError(f"No chroma Dp/p bands for orbit offsets {missing} mm in {CHROMA_FILE}")
    reference = float(table[0].dpp)
    return {
        mm: (1.0 + float(table[int(mm)].dpp)) / (1.0 + reference) - 1.0
        for mm in OFFSETS_MM.values()
    }


def frev_by_offset() -> pd.DataFrame:
    """Revolution frequency at each RF offset, from ``asym_qde_errors.txt``.

    ``OrbitTunePoint`` (``load_orbit_tune_table``'s return type) does not carry
    ``Frev``, so this bands the raw ``Frev`` rows itself, reusing the same
    orbit-inference and section-boundary helpers ``load_orbit_tune_table`` and
    ``recalculate_dpp_from_averages.py`` are already built on -- not a
    re-derived banding rule.
    """
    from psb_md.defaults import DPP_PER_MM
    from psb_md.tune_measurements import (
        DEFAULT_JUMP_THRESHOLD,
        DEFAULT_ZERO_THRESHOLD,
        _collect_section_boundaries,
        _infer_row_orbit_map,
    )

    lines = CHROMA_FILE.read_text(encoding="utf-8").splitlines()
    first, vertical_marker, second = _collect_section_boundaries(lines)

    def parse(start: int, end: int | None) -> tuple[list[int], dict[str, dict[int, list[float | None]]]]:
        section = lines[start:end]
        times = [int(value.strip()) for value in section[0].split(",")[2:]]
        rows: dict[str, dict[int, list[float | None]]] = {"Dp/p": {}, "Frev": {}}
        for line in section[1:]:
            fields = [field.strip() for field in line.split(",")]
            if fields[0] not in rows:
                continue
            values = fields[2 : 2 + len(times)]
            values += [""] * (len(times) - len(values))
            rows[fields[0]][int(fields[1])] = [
                None if value == "" else float(value) for value in values
            ]
        return times, rows

    h_times, horizontal = parse(first, vertical_marker)
    v_times, vertical = parse(second, None)
    row_map, orbits = _infer_row_orbit_map(
        h_times, horizontal["Dp/p"], v_times, vertical["Dp/p"],
        ctime_min=min(h_times + v_times), ctime_max=max(h_times + v_times),
        dpp_per_index=DPP_PER_MM,
        jump_threshold=DEFAULT_JUMP_THRESHOLD,
        zero_threshold=DEFAULT_ZERO_THRESHOLD,
    )

    frev_by_orbit: dict[int, list[float]] = {orbit: [] for orbit in orbits}
    for row, values in horizontal["Frev"].items():
        orbit = row_map.get(row)
        if orbit is None:
            continue
        frev_by_orbit[orbit].extend(value for value in values if value is not None)

    wanted = {int(mm) for mm in OFFSETS_MM.values()}
    missing = sorted(wanted - frev_by_orbit.keys())
    if missing:
        raise KeyError(f"No Frev band for orbit offsets {missing} mm in {CHROMA_FILE}")
    rows = [
        {
            "rf_offset_mm": float(orbit),
            "frev_mean_hz": float(np.mean(frev_by_orbit[orbit])),
            "frev_std_hz": float(np.std(frev_by_orbit[orbit], ddof=1)),
            "n_samples": len(frev_by_orbit[orbit]),
        }
        for orbit in sorted(wanted)
    ]
    return pd.DataFrame(rows)


def plot_frev(
    result: pd.DataFrame, frev_reference: pd.DataFrame, frev0: float, alphap: float
) -> None:
    """Frev vs. Dp/p, in ``chroma_investigation/analyse.py``'s ``frev_fits.png`` style.

    Both axes are fractional and both sources share the same ``x``: the
    chroma-export Dp/p reference and this script's own orbit-based Dp/p,
    against the *same* measured ``(Frev - Frev0)/Frev0`` from the chroma
    export -- the two sources being compared are the two Dp/p calibrations,
    exactly as ``analyse.py`` compares ``orbit/model D`` against ``chroma``
    on one frequency axis, with the model line from this model's own
    ``alfap``.
    """
    merged = result.merge(frev_reference, on="rf_offset_mm", validate="one_to_one")
    fractional_f = (merged.frev_mean_hz - frev0) / frev0
    fractional_f_error = merged.frev_std_hz / frev0

    fig, axis = plt.subplots(figsize=(5.5, 4.2))
    for color, (label, dpp) in zip(
        ("C0", "C1"),
        (("chroma (XImeter/RF)", merged.dpp_xicorr_reference), ("orbit/model D", merged.dpp_from_orbit)),
    ):
        axis.errorbar(
            fractional_f * 1e3, dpp * 1e3, xerr=fractional_f_error * 1e3,
            fmt="o", color=color, ms=5, capsize=3, label=label,
        )

    eta = INV_GAMMA2 - alphap
    grid = np.linspace(merged.dpp_xicorr_reference.min(), merged.dpp_xicorr_reference.max(), 100)
    axis.plot((eta * grid) * 1e3, grid * 1e3, "k--", label=fr"model: $\alpha_p$={alphap:.5f}")

    axis.set(
        xlabel=r"$[(f_{rev}-f_0)/f_0](10^{-3})$", ylabel=r"$(\Delta p/p)(10^{-3})$",
        title="Asym QDE: multiturn blanks vs. chroma export",
    )
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "multiturn_frev.png", dpi=180)
    plt.close(fig)


def main() -> None:
    from aba_optimiser.accelerators import PSB as OptimiserPSB
    from psb_md.acd_config import MachineConfig

    # No scanned correctors and no tune match to the campaign circuits: these
    # are unkicked blanks, taken on the "asym QDE" lattice the reference
    # chroma file was also measured on.
    model = build_model(
        MachineConfig.QDE_ERRORS_ASYM_P23_P13,
        orbit=0,
        scan_correctors=False,
        scan_quads=False,
        sequence_file=REPO_ROOT / "models/model_qx0.165000_qy0.227500/psb3_saved.seq",
    )
    twiss = model_twiss(model, chrom=True)
    accelerator = OptimiserPSB(
        ring=model.ring, sequence_file=model.sequence_file, kinetic_energy=model.kinetic_energy,
    )

    orbits = {
        offset: average_closed_orbit(BLANK_DIR / folder)
        for folder, offset in OFFSETS_MM.items()
    }
    frame = frame_from_orbit(orbits[0.0], twiss)

    reference = reference_dpp_by_offset()
    rows = []
    for offset in sorted(orbits):
        pt = 0.0 if offset == 0.0 else estimate_pt(orbits[offset], twiss, frame)
        dpp_from_orbit = 0.0 if offset == 0.0 else float(accelerator.pt2dp(pt))
        rows.append(
            {
                "rf_offset_mm": offset,
                "n_files": orbits[offset].attrs["n_files"],
                "pt_from_orbit": pt,
                "dpp_from_orbit": dpp_from_orbit,
                "dpp_xicorr_reference": reference[offset],
                "difference": dpp_from_orbit - reference[offset],
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(HERE / "multiturn_momenta.csv", index=False)
    print(result.to_string(index=False))

    frev_reference = frev_by_offset()
    frev0 = float(frev_reference.loc[frev_reference.rf_offset_mm == 0.0, "frev_mean_hz"].iloc[0])
    alphap = float(twiss.headers["alfap"])
    frev_reference.to_csv(HERE / "multiturn_frev_reference.csv", index=False)
    plot_frev(result, frev_reference, frev0, alphap)
    print(frev_reference.to_string(index=False))


if __name__ == "__main__":
    main()
