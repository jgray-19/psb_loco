"""Momentum of each RF-steering setting, for POCO's multi-``pt`` mode.

The chromaticity scan visited the same orbit plateaus as the LOCO scan and gives an
RF-derived ``Dp/p`` calibration, kept separate from the orbit-projection estimate for comparison.
Every calibration is relative to the 0 mm orbit, which is always ``pt=0``.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from tmom_recon import estimate_pt_from_orbit

logger = logging.getLogger(__name__)


def _chroma_bands(chroma_file, rf_offsets) -> tuple[tuple[float, ...], dict]:
    """The chroma scan's momentum band of each LOCO plateau, 0 mm required.

    ``psb_md`` numbers the bands outwards from the one nearest zero; with 1 mm steps a band index is its ``rf_offset_mm``.
    """
    from psb_md.defaults import DPP_PER_MM
    from psb_md.tune_measurements import load_orbit_tune_table

    offsets = tuple(float(offset) for offset in rf_offsets)
    if 0.0 not in offsets:
        raise ValueError("The 0 mm orbit is required as the momentum reference")
    if any(not offset.is_integer() for offset in offsets):
        raise ValueError("The chroma calibration is defined on integer-mm plateaus")
    table = load_orbit_tune_table(chroma_file, dpp_per_index=DPP_PER_MM)
    missing = sorted(int(offset) for offset in offsets if int(offset) not in table)
    if missing:
        raise KeyError(f"No chroma Dp/p bands for orbit offsets {missing} mm")
    return offsets, table


def chroma_pt_by_rf_offset(
    chroma_file,
    rf_offsets: tuple[float, ...] | list[float],
    accelerator,
) -> dict[float, float]:
    """Return RF-derived ``pt`` for the LOCO plateaus, relative to 0 mm."""
    offsets, table = _chroma_bands(chroma_file, rf_offsets)

    # Rebase to the 0 mm plateau before converting: subtracting two canonical pt values is wrong once dp2pt is nonlinear.
    reference_dpp = float(table[0].dpp)
    relative_dpp = {
        offset: (1.0 + float(table[int(offset)].dpp)) / (1.0 + reference_dpp) - 1.0
        for offset in offsets
    }
    momenta = {
        offset: float(accelerator.dp2pt(dpp)) for offset, dpp in relative_dpp.items()
    }
    # This is the defining reference, not another measured off-momentum point.
    momenta[0.0] = 0.0
    for offset in sorted(momenta):
        logger.info(
            "RF offset %+g mm -> absolute chroma Dp/p %+.4e -> pt-pt(0 mm) %+.4e",
            offset,
            table[int(offset)].dpp,
            momenta[offset],
        )
    _warn_if_not_monotonic(momenta)
    return momenta


def chroma_pt_error_by_rf_offset(
    chroma_file,
    rf_offsets: tuple[float, ...] | list[float],
    accelerator,
) -> dict[float, float]:
    """One-sigma uncertainty on :func:`chroma_pt_by_rf_offset`'s ``pt``.

    ``dpp_std`` is propagated through the rebasing (numerator and shared reference) and ``dp2pt``'s
    local slope, by central finite difference.
    """
    offsets, table = _chroma_bands(chroma_file, rf_offsets)
    reference_dpp = float(table[0].dpp)
    reference_dpp_std = float(table[0].dpp_std)

    errors = {}
    for offset in offsets:
        if offset == 0.0:
            errors[0.0] = 0.0
            continue
        dpp = float(table[int(offset)].dpp)
        dpp_std = float(table[int(offset)].dpp_std)
        relative_dpp = (1.0 + dpp) / (1.0 + reference_dpp) - 1.0

        d_relative_d_dpp = 1.0 / (1.0 + reference_dpp)
        d_relative_d_reference = -(1.0 + dpp) / (1.0 + reference_dpp) ** 2
        relative_dpp_sigma = np.hypot(
            d_relative_d_dpp * dpp_std, d_relative_d_reference * reference_dpp_std
        )

        step = max(abs(relative_dpp), 1.0) * 1e-6
        d_pt_d_relative = (
            accelerator.dp2pt(relative_dpp + step) - accelerator.dp2pt(relative_dpp - step)
        ) / (2.0 * step)
        errors[offset] = float(abs(d_pt_d_relative) * relative_dpp_sigma)

    for offset in sorted(errors):
        logger.info("RF offset %+g mm -> chroma pt one-sigma %.4e", offset, errors[offset])
    return errors


def frame_from_orbit(orbit: pd.DataFrame, twiss: pd.DataFrame) -> pd.DataFrame:
    """Build the orbit-zero reference from the *measured* nominal-RF closed orbit.

    Must be measured: a dipole error is degenerate with the dispersive orbit at a single momentum.
    *twiss* is unused; kept for a stable call signature.
    """
    orbit_zero = pd.DataFrame({"x": orbit["X"].astype(float)}, index=orbit.index)
    orbit_zero["y"] = orbit["Y"].astype(float) if "Y" in orbit else 0.0
    orbit_zero.index = orbit_zero.index.astype(str)
    # normalize_closed_orbit needs a "name" column or index; pin the index.
    orbit_zero.index.name = "name"
    return orbit_zero


def estimate_pt(
    orbit: pd.DataFrame,
    twiss: pd.DataFrame,
    frame: pd.DataFrame,
) -> float:
    """Estimate this orbit's MAD-NG ``pt`` offset from *frame*'s origin.

    *orbit* is one RF setting's measured closed orbit (``X`` in metres, indexed by BPM);
    *twiss* carries ``dx`` (and ``ddx`` for the second-order estimator).
    """
    # ``.intersection()`` drops the index name on a case mismatch, which trips tmom_recon; pin it.
    common = orbit.index.intersection(twiss.index).rename("name")
    measured = pd.DataFrame({"x": orbit.loc[common, "X"].to_numpy(dtype=float)}, index=common)
    return float(
        estimate_pt_from_orbit(measured, twiss.loc[common], closed_orbit_at_zero=frame, info=False)
    )


def estimate_pt_by_rf_offset(
    orbits: dict[float, pd.DataFrame],
    twiss: pd.DataFrame,
) -> dict[float, float]:
    """Estimate ``pt`` for each RF offset in mm; the required ``0.0`` entry is the frame origin."""
    if 0.0 not in orbits:
        raise ValueError(
            "The RF-offset-0 orbit is required as the momentum reference: pt is "
            "estimated as an offset from it, not absolutely."
        )
    frame = frame_from_orbit(orbits[0.0], twiss)
    estimates = {offset: estimate_pt(orbit, twiss, frame) for offset, orbit in orbits.items()}
    for offset, pt in sorted(estimates.items()):
        logger.info("RF offset %+g mm -> pt %+.4e (relative to nominal RF)", offset, pt)
    _warn_if_not_monotonic(estimates)
    return estimates


def _warn_if_not_monotonic(estimates: dict[float, float]) -> None:
    offsets = np.array(sorted(estimates))
    values = np.array([estimates[offset] for offset in offsets])
    differences = np.diff(values)
    if differences.size and not (np.all(differences > 0) or np.all(differences < 0)):
        logger.warning(
            "Estimated pt is not monotonic in RF offset (%s). The estimate is "
            "dispersion-projected, so a non-monotonic result means the reference "
            "orbit or the model dispersion is wrong, not that the machine was.",
            ", ".join(f"{o:+g}:{v:+.3e}" for o, v in zip(offsets, values, strict=True)),
        )
