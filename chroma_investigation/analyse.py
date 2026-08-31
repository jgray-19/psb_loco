"""Compare the two momentum calibrations used by the chroma measurement."""

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
MASS_GEV = 0.93827208816
KINETIC_ENERGY_GEV = 0.160
KINETIC_ENERGY_ERROR_GEV = 1e-2 * KINETIC_ENERGY_GEV
GAMMA = 1 + KINETIC_ENERGY_GEV / MASS_GEV
GAMMA_ERROR = KINETIC_ENERGY_ERROR_GEV / MASS_GEV
INV_GAMMA2 = 1 / GAMMA**2
INV_GAMMA2_ERROR = 2 * GAMMA_ERROR / GAMMA**3
MODEL_DISPERSION_REL_ERROR = 0.10


def line_fit(x, y):
    """Return intercept, slope, and one-sigma slope error."""
    (slope, intercept), cov = np.polyfit(x, y, 1, cov=True)
    return intercept, slope, np.sqrt(cov[0, 0])


def weighted_line_fit(x, y, sigma):
    """Straight-line fit using known one-sigma errors on y."""
    design = np.column_stack([np.ones(len(x)), x])
    weight = np.diag(1 / np.asarray(sigma) ** 2)
    covariance = np.linalg.inv(design.T @ weight @ design)
    intercept, slope = covariance @ design.T @ weight @ y
    return intercept, slope, np.sqrt(covariance[1, 1])


def uncertain_line_fit(x, y, x_error, y_error):
    """Line fit with both-axis errors, iterating their projected y uncertainty."""
    slope = line_fit(x, y)[1]
    for _ in range(5):
        effective_error = np.hypot(y_error, slope * x_error)
        intercept, slope, slope_error = weighted_line_fit(x, y, effective_error)
    return intercept, slope, slope_error


def prepare_campaign(frame):
    """Collect offsets, matched-model checks, and the two momentum calibrations."""
    offsets = frame.drop_duplicates("rf_offset_mm").sort_values("rf_offset_mm")
    zero = frame[frame.rf_offset_mm == 0].set_index("bpm")
    tune_label = (
        fr"$(Q_x, Q_y)=({offsets.match_Qx.iloc[0]:.6f}, "
        fr"{offsets.match_Qy.iloc[0]:.6f})$"
    )
    # Every model curve below must come from the lattice matched to this scan's
    # nominal measured tune. Refuse to make plausible-looking unmatched plots.
    for plane in ("x", "y"):
        measured_q0 = float(offsets[f"match_Q{plane}"].iloc[0])
        model_q0 = float(offsets[f"model_Q{plane}"].iloc[0])
        if not np.isclose(model_q0, measured_q0, atol=5e-4):
            raise ValueError(f"{campaign} model Q{plane}={model_q0} is not matched to {measured_q0}")

    orbit_dpp = {}
    orbit_dpp_error = {}
    for offset, orbit in frame.groupby("rf_offset_mm"):
        orbit = orbit.set_index("bpm").loc[zero.index]
        dx = orbit.orbit_x_m - zero.orbit_x_m
        D = orbit.model_Dx_m
        orbit_dpp[offset] = np.dot(D, dx) / np.dot(D, D)
        dx_error = np.hypot(orbit.orbit_x_std_m, zero.orbit_x_std_m)
        projection_error = np.sqrt(np.sum((D * dx_error) ** 2)) / np.dot(D, D)
        dispersion_error = MODEL_DISPERSION_REL_ERROR * np.abs(D)
        sensitivity = dx / np.dot(D, D) - 2 * np.dot(D, dx) * D / np.dot(D, D) ** 2
        model_error = np.sqrt(np.sum((sensitivity * dispersion_error) ** 2))
        orbit_dpp_error[offset] = np.hypot(projection_error, model_error)
    orbit_dpp_error[0] = 0.0  # nominal momentum is the defining reference

    momenta = {
        "orbit/model D": np.array([orbit_dpp[o] for o in offsets.rf_offset_mm]),
        "chroma": offsets.chroma_dpp.to_numpy(),
    }
    momentum_errors = {
        "orbit/model D": np.array([orbit_dpp_error[o] for o in offsets.rf_offset_mm]),
        "chroma": offsets.chroma_dpp_std.to_numpy(),
    }
    return offsets, zero, momenta, momentum_errors, tune_label


def plot_dispersion(axis, campaign, frame, offsets, zero, momenta, momentum_errors, full_model, tune_label, plane, column, row):
    """Plot measured BPM dispersion, full-ring model, and uncertainties."""
    for color, (label, delta) in zip(("C0", "C1"), momenta.items()):
        measured, measured_error = [], []
        for bpm, bpm_rows in frame.groupby("bpm", sort=False):
            bpm_rows = bpm_rows.set_index("rf_offset_mm").loc[offsets.rf_offset_mm]
            _, slope, error = uncertain_line_fit(
                delta,
                bpm_rows[f"orbit_{plane}_m"].to_numpy(),
                momentum_errors[label],
                bpm_rows[f"orbit_{plane}_std_m"].to_numpy(),
            )
            measured.append(slope)
            measured_error.append(error)
        axis.errorbar(
            zero.s_m, measured, yerr=measured_error, fmt="o--", color=color,
            ms=3, lw=1, capsize=2, label=label,
        )

    ring = full_model[full_model.campaign == campaign]
    model_values = ring[f"model_D{plane}_m"].to_numpy()
    axis.plot(ring.s_m, model_values, "k--", lw=1, label="model, full ring")
    axis.fill_between(
        ring.s_m,
        model_values - MODEL_DISPERSION_REL_ERROR * np.abs(model_values),
        model_values + MODEL_DISPERSION_REL_ERROR * np.abs(model_values),
        color="k", alpha=0.10, linewidth=0, label="model ±10%",
    )
    bpm_model = zero[f"model_D{plane}_m"]
    axis.errorbar(
        zero.s_m, bpm_model, yerr=MODEL_DISPERSION_REL_ERROR * np.abs(bpm_model),
        fmt="kx", ms=6, mew=1.2, capsize=2, label="model at BPMs",
    )
    axis.axhline(0, color="0.8", lw=0.7)
    axis.set(title=tune_label if row == 0 else None,
             ylabel=rf"$D_{{{plane}}}$ [m]" if column == 0 else None)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)


def plot_tunes(axis, campaign, offsets, momenta, momentum_errors, tune_label, plane, column, row, summary):
    """Plot tune points and chromaticity fits for one plane."""
    tune = offsets[f"Q{plane}"].to_numpy()
    tune_error = offsets[f"Q{plane}_std"].to_numpy()
    q0 = tune[offsets.rf_offset_mm.to_numpy() == 0][0]
    for color, (label, delta) in zip(("C0", "C1"), momenta.items()):
        intercept, slope, error = uncertain_line_fit(delta, tune, momentum_errors[label], tune_error)
        grid = np.linspace(delta.min(), delta.max(), 100)
        axis.errorbar(
            delta * 1e3, tune, xerr=momentum_errors[label] * 1e3, yerr=tune_error,
            fmt="o", color=color, ms=4, capsize=2,
            label=fr"{label}: $Q_{plane}'$={slope:.3f}±{error:.3f}",
        )
        axis.plot(grid * 1e3, intercept + slope * grid, color=color, lw=1)
        summary.append([campaign, f"Q{plane}", label, slope, error, 0.0, error])

    model_slope = float(offsets[f"model_Qp{plane}"].iloc[0])
    grid = np.linspace(min(map(np.min, momenta.values())), max(map(np.max, momenta.values())), 100)
    axis.plot(grid * 1e3, q0 + model_slope * grid, "k--",
              label=fr"model: $Q_{plane}'$={model_slope:.3f}")
    axis.set(title=tune_label if row == 0 else None,
             xlabel=r"$(\Delta p/p)/(10^{-3})$" if row == 1 else None,
             ylabel=fr"$Q_{plane}$")
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7)


def plot_frev(axis, campaign, offsets, momenta, momentum_errors, tune_label, row, summary):
    """Plot revolution frequency against both momentum calibrations."""
    frev = offsets.frev_Hz.to_numpy()
    f0 = frev[offsets.rf_offset_mm.to_numpy() == 0][0]
    fractional_f = (frev - f0) / f0
    fractional_f_error = offsets.frev_std_Hz.to_numpy() / f0
    for color, (label, delta) in zip(("C0", "C1", "C2"), momenta.items()):
        intercept, slope, error = uncertain_line_fit(
            delta, fractional_f, momentum_errors[label], fractional_f_error
        )
        fitted = -slope
        alphap = INV_GAMMA2 + fitted
        alphap_error = math.hypot(error, INV_GAMMA2_ERROR)
        grid = np.linspace(delta.min(), delta.max(), 100)
        axis.errorbar(
            fractional_f * 1e3, delta * 1e3,
            xerr=fractional_f_error * 1e3, yerr=momentum_errors[label] * 1e3,
            fmt="o", color=color, ms=4, capsize=3, elinewidth=1.1,
            label=(fr"{label}: "#$\alpha_p-1/\gamma^2$={fitted:+.5f}±{error:.1e}; "
                   fr"$\alpha_p$={alphap:.5f}±{alphap_error:.1e}"),
        )
        axis.plot((intercept + slope * grid) * 1e3, grid * 1e3, color=color, lw=1)
        summary.append([campaign, "alphap", label, alphap, error, INV_GAMMA2_ERROR, alphap_error])

    model_alphap = float(offsets.model_alphap.iloc[0])
    model_slope = INV_GAMMA2 - model_alphap
    grid = np.linspace(min(map(np.min, momenta.values())), max(map(np.max, momenta.values())), 100)
    axis.plot(model_slope * grid * 1e3, grid * 1e3, "k--",
              label=fr"model: $\alpha_p$={model_alphap:.5f}")
    axis.set(title=tune_label, xlabel=r"$[(f_{rev}-f_0)/f_0](10^{-3})$",
             ylabel=r"$(\Delta p/p)(10^{-3})$" if row == 0 else None)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7)


def main():
    """Read the snapshot, make all figures, and write the fit summary."""
    data = pd.read_csv(HERE / "input_uncleaned.csv")
    # The raw untrimmed scan has 24 acquisitions off momentum and 47 at the
    # nominal setting. Recover their standard deviations from the stored SEMs.
    orbit_samples = data.rf_offset_mm.map(lambda offset: 47 if offset == 0 else 24)
    for plane in ("x", "y"):
        data[f"orbit_{plane}_std_m"] = data[f"orbit_{plane}_sem_m"] * np.sqrt(orbit_samples)
    full_model = pd.read_csv(HERE / "model_full_ring.csv")
    recalculated = pd.read_csv(HERE / "dpp_recalculated_by_plateau.csv")
    spread_columns = recalculated[["campaign", "orbit", "Frev_std_Hz"]].rename(
        columns={"orbit": "rf_offset_mm", "Frev_std_Hz": "frev_std_Hz"}
    )
    data = data.merge(
        spread_columns, on=["campaign", "rf_offset_mm"], how="left", validate="many_to_one"
    )
    summary = []
    fig_d, ax_d = plt.subplots(2, 2, figsize=(11, 7), sharex="col", sharey="row")
    fig_q, ax_q = plt.subplots(2, 2, figsize=(11, 7))
    fig_f, ax_f = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)

    for column, (campaign, frame) in enumerate(data.groupby("campaign", sort=False)):
        offsets, zero, momenta, momentum_errors, tune_label = prepare_campaign(frame)
        for row, plane in enumerate(("x", "y")):
            plot_dispersion(ax_d[row, column], campaign, frame, offsets, zero, momenta,
                            momentum_errors, full_model, tune_label, plane, column, row)
            plot_tunes(ax_q[row, column], campaign, offsets, momenta, momentum_errors,
                       tune_label, plane, column, row, summary)
        recalc = recalculated[
            (recalculated.campaign == campaign)
            & recalculated.orbit.isin(offsets.rf_offset_mm)
        ].set_index("orbit").loc[offsets.rf_offset_mm]
        frev_momenta = dict(momenta)
        frev_momentum_errors = dict(momentum_errors)
        frev_momenta["recalculated"] = recalc.Dp_p_recalculated_from_model.to_numpy()
        frev_momentum_errors["recalculated"] = recalc.Dp_p_recalculated_from_model_std.to_numpy()
        plot_frev(ax_f[column], campaign, offsets, frev_momenta, frev_momentum_errors,
                  tune_label, column, summary)

    fig_f.suptitle(
        fr"160 MeV protons: $1/\gamma^2={INV_GAMMA2:.6f}\pm{INV_GAMMA2_ERROR:.1e}$ "
        r"(from guessed $10^{-2}$ relative energy uncertainty)", fontsize=10,
    )
    for axis in ax_d[-1]:
        axis.set_xlabel("s [m]")
    for fig, name in ((fig_d, "dispersion.png"), (fig_q, "tune_fits.png"), (fig_f, "frev_fits.png")):
        fig.tight_layout()
        fig.savefig(HERE / name, dpi=180)
    result = pd.DataFrame(summary, columns=["campaign", "quantity", "momentum", "value", "fit_error", "energy_error", "total_error"])
    result.to_csv(HERE / "summary.csv", index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
