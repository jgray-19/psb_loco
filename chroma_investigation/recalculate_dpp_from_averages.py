"""Recalculate XImeter Dp/p sample-by-sample, then aggregate by plateau."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from psb_md.defaults import DPP_PER_MM
from psb_md.tune_measurements import (
    DEFAULT_JUMP_THRESHOLD,
    DEFAULT_ZERO_THRESHOLD,
    _collect_section_boundaries,
    _infer_row_orbit_map,
)

HERE = Path(__file__).parent
MASS_GEV = 0.93827208816
RHO_M = 8.23885807424
KINETIC_ENERGY_GEV = 0.160
GAMMA = 1 + KINETIC_ENERGY_GEV / MASS_GEV
INV_GAMMA2 = 1 / GAMMA**2
INV_GAMMA2_ERROR = 2 * (0.01 * KINETIC_ENERGY_GEV / MASS_GEV) / GAMMA**3
FILES = {
    "normal": Path("/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_21_Multiturn/chroma/normal_tunes.txt"),
    "inverted": Path("/home/jmgray/mnt/user/psbop/MultiTurn/2026_08_21_Multiturn/chroma/inverted_tunes.txt"),
}


def parse_section(lines, start, end):
    section = lines[start:end]
    times = [int(value.strip()) for value in section[0].split(",")[2:]]
    rows = {name: {} for name in ("Dp/p", "Frev", "BfC", "QH", "QV")}
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


def rebase(mean, std, reference_mean, reference_std):
    value = (1 + mean) / (1 + reference_mean) - 1
    error = np.hypot(
        std / (1 + reference_mean),
        (1 + mean) * reference_std / (1 + reference_mean) ** 2,
    )
    return value, error


def reconstruct_plateaus(path, model_alphap):
    """Calculate every raw Dp/p first, then take each plateau mean and spread."""
    lines = path.read_text(encoding="utf-8").splitlines()
    first, vertical_marker, second = _collect_section_boundaries(lines)
    h_times, horizontal = parse_section(lines, first, vertical_marker)
    v_times, vertical = parse_section(lines, second, None)
    lower, upper = min(h_times + v_times), max(h_times + v_times)
    row_map, orbits = _infer_row_orbit_map(
        h_times, horizontal["Dp/p"], v_times, vertical["Dp/p"],
        ctime_min=lower, ctime_max=upper, dpp_per_index=DPP_PER_MM,
        jump_threshold=DEFAULT_JUMP_THRESHOLD,
        zero_threshold=DEFAULT_ZERO_THRESHOLD,
    )
    samples = {
        orbit: {"logged": [], "recalculated": [], "frev": [], "qx": [], "qy": []}
        for orbit in orbits
    }
    for rows, tune_name, output_name in (
        (horizontal, "QH", "qx"), (vertical, "QV", "qy")
    ):
        reference_frequencies = rows["Frev"][0]
        for row, frequencies in rows["Frev"].items():
            if row not in row_map or row not in rows["BfC"] or row not in rows["Dp/p"]:
                continue
            orbit = row_map[row]
            for frequency, field, logged, reference_frequency in zip(
                frequencies, rows["BfC"][row], rows["Dp/p"][row], reference_frequencies
            ):
                if None in (frequency, field, logged, reference_frequency):
                    continue
                momentum = (field / 1e4) * RHO_M / 3.3356
                eta = MASS_GEV**2 / (MASS_GEV**2 + momentum**2) - model_alphap
                recalculated = ((frequency - reference_frequency) / reference_frequency) / eta
                samples[orbit]["logged"].append(logged)
                samples[orbit]["recalculated"].append(recalculated)
                samples[orbit]["frev"].append(frequency)
            for tune in rows[tune_name].get(row, []):
                if tune is not None:
                    samples[orbit][output_name].append(tune)

    absolute = {}
    for orbit, values in samples.items():
        absolute[orbit] = {}
        for name, raw in values.items():
            array = np.asarray(raw, dtype=float)
            absolute[orbit][name] = (array.mean(), array.std(ddof=1), array.size)

    result = []
    for orbit in orbits:
        logged, logged_std = rebase(
            absolute[orbit]["logged"][0], absolute[orbit]["logged"][1],
            absolute[0]["logged"][0], absolute[0]["logged"][1],
        )
        recalculated, recalculated_std = rebase(
            absolute[orbit]["recalculated"][0], absolute[orbit]["recalculated"][1],
            absolute[0]["recalculated"][0], absolute[0]["recalculated"][1],
        )
        logged_sem = rebase(
            absolute[orbit]["logged"][0],
            absolute[orbit]["logged"][1] / np.sqrt(absolute[orbit]["logged"][2]),
            absolute[0]["logged"][0],
            absolute[0]["logged"][1] / np.sqrt(absolute[0]["logged"][2]),
        )[1]
        recalculated_sem = rebase(
            absolute[orbit]["recalculated"][0],
            absolute[orbit]["recalculated"][1] / np.sqrt(absolute[orbit]["recalculated"][2]),
            absolute[0]["recalculated"][0],
            absolute[0]["recalculated"][1] / np.sqrt(absolute[0]["recalculated"][2]),
        )[1]
        if orbit == 0:
            # The nominal plateau defines the relative-momentum origin.
            logged = recalculated = logged_std = recalculated_std = 0.0
            logged_sem = recalculated_sem = 0.0
        frev_mean, frev_std, count = absolute[orbit]["frev"]
        qx_count = absolute[orbit]["qx"][2]
        qy_count = absolute[orbit]["qy"][2]
        result.append({
            "orbit": orbit, "samples": count,
            "Frev_mean_Hz": frev_mean, "Frev_std_Hz": frev_std,
            "Frev_sem_Hz": frev_std / np.sqrt(count),
            "Dp_p_logged": logged, "Dp_p_logged_std": logged_std,
            "Dp_p_logged_sem": logged_sem,
            "Dp_p_recalculated_from_model": recalculated,
            "Dp_p_recalculated_from_model_std": recalculated_std,
            "Dp_p_recalculated_from_model_sem": recalculated_sem,
            "Qx_samples": qx_count, "Qy_samples": qy_count,
            "Qx_sem": absolute[orbit]["qx"][1] / np.sqrt(qx_count),
            "Qy_sem": absolute[orbit]["qy"][1] / np.sqrt(qy_count),
        })
    return pd.DataFrame(result)


def fit_with_xy_errors(x, y, x_error, y_error):
    slope = np.polyfit(x, y, 1)[0]
    for _ in range(5):
        sigma = np.hypot(y_error, slope * x_error)
        design = np.column_stack([np.ones(len(x)), x])
        weights = np.diag(1 / sigma**2)
        covariance = np.linalg.inv(design.T @ weights @ design)
        intercept, slope = covariance @ design.T @ weights @ y
    return intercept, slope, np.sqrt(covariance[1, 1])


def main():
    input_data = pd.read_csv(HERE / "input_uncleaned.csv")
    plateaus = []
    for campaign, path in FILES.items():
        model_alphap = float(input_data.loc[input_data.campaign == campaign, "model_alphap"].iloc[0])
        table = reconstruct_plateaus(path, model_alphap)
        table.insert(0, "campaign", campaign)
        plateaus.append(table)
    result = pd.concat(plateaus, ignore_index=True)
    result.to_csv(HERE / "dpp_recalculated_by_plateau.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    alpha_rows = []
    for axis, (campaign, frame) in zip(axes, result.groupby("campaign", sort=False)):
        frame = frame[frame.orbit.isin((-2, -1, 0, 1, 2))].sort_values("orbit")
        f0 = float(frame.loc[frame.orbit == 0, "Frev_mean_Hz"].iloc[0])
        sf0 = float(frame.loc[frame.orbit == 0, "Frev_std_Hz"].iloc[0])
        frequency = frame.Frev_mean_Hz.to_numpy()
        fractional_f = (frequency - f0) / f0
        fractional_f_error = np.hypot(
            frame.Frev_std_Hz.to_numpy(), (frequency - f0) * sf0 / f0
        ) / f0
        dpp = frame.Dp_p_recalculated_from_model.to_numpy()
        dpp_error = frame.Dp_p_recalculated_from_model_std.to_numpy()
        intercept, eta, eta_error = fit_with_xy_errors(dpp, fractional_f, dpp_error, fractional_f_error)
        alphap = INV_GAMMA2 - eta
        alphap_error = np.hypot(eta_error, INV_GAMMA2_ERROR)
        alpha_rows.append({
            "campaign": campaign, "eta_fit": eta, "eta_fit_error": eta_error,
            "alphap": alphap, "alphap_error": alphap_error,
        })
        axis.errorbar(
            fractional_f * 1e3, dpp * 1e3,
            xerr=fractional_f_error * 1e3, yerr=dpp_error * 1e3,
            fmt="o", color="C2", capsize=3,
            label=fr"recalculated from model: $\alpha_p={alphap:.5f}\pm{alphap_error:.5f}$",
        )
        grid = np.linspace(dpp.min(), dpp.max(), 100)
        axis.plot((intercept + eta * grid) * 1e3, grid * 1e3, color="C2")
        model_alpha = float(input_data.loc[input_data.campaign == campaign, "model_alphap"].iloc[0])
        model_eta = INV_GAMMA2 - model_alpha
        axis.plot(model_eta * grid * 1e3, grid * 1e3, "k--",
                  label=fr"model: $\alpha_p={model_alpha:.5f}$")
        tunes = input_data[input_data.campaign == campaign].iloc[0]
        axis.set_title(fr"$(Q_x,Q_y)=({tunes.match_Qx:.6f},{tunes.match_Qy:.6f})$")
        axis.set_xlabel(r"$[(f_{rev}-f_0)/f_0]/(10^{-3})$")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    axes[0].set_ylabel(r"$(\Delta p/p)/(10^{-3})$")
    fig.suptitle("Dp/p calculated for every XImeter sample, then averaged by plateau", fontsize=11)
    fig.tight_layout()
    fig.savefig(HERE / "frev_fits_recalculated.png", dpi=180)
    plt.close(fig)
    pd.DataFrame(alpha_rows).to_csv(HERE / "recalculated_alphap.csv", index=False)
    print(result[result.orbit.isin((-2, -1, 0, 1, 2))].to_string(index=False))


if __name__ == "__main__":
    main()
