"""Momentum of each RF-steering setting, for Method 2's optional multi-``pt`` mode.

The scan repeated the whole corrector sweep at five RF-steering offsets, so the
same delta-response is available at five momenta and the off-momentum Jacobians
are genuinely independent. The LOCO log records a radial-steering setting in
millimetres, not a ``dp/p``. The accompanying chromaticity scan visited the same
orbit plateaus, however, and supplies an RF-derived ``Dp/p`` calibration that is
independent of the model dispersion. This module keeps that calibration
separate from the older orbit-projection estimate so they can be compared.

Every calibration is relative to the 0 mm orbit: that plateau is the reference
particle and is always passed to MAD-NG as exactly ``pt=0``.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from tmom_recon import estimate_pt_from_orbit

logger = logging.getLogger(__name__)


def _chroma_bands(chroma_file, rf_offsets) -> tuple[tuple[float, ...], dict]:
    """The chroma scan's momentum band of each LOCO plateau, 0 mm required.

    XImeter does not write radial-orbit labels. ``psb_md`` recovers them by
    grouping repeated rows into momentum bands and numbering the bands outwards
    from the one nearest zero. This acquisition used 1 mm steps, so a band index
    is also its LOCO ``rf_offset_mm``.
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

    # Dp/p in the chroma export is an absolute machine readback, whereas this
    # fit uses the 0 mm orbit as its reference particle. Rebase momentum first:
    # if p_i = p_machine*(1+dpp_i) and p_0 = p_machine*(1+dpp_0), then the
    # relative deviation seen by the fit is p_i/p_0 - 1. Only that relative
    # Dp/p may be converted to the fit's canonical pt. Subtracting two canonical
    # pt values is not a coordinate transformation and is wrong once dp2pt is
    # nonlinear.
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

    ``psb_md``'s per-band ``dpp_std`` is propagated through the same rebasing
    arithmetic (both the numerator and the shared reference contribute, since
    every band is rebased against the same 0 mm plateau) and then through
    ``dp2pt``'s local slope, taken by central finite difference since
    ``dp2pt`` is not assumed linear.
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


def compare_momentum_calibrations(
    reference: dict[float, float], alternative: dict[float, float]
) -> dict[float, float]:
    """Return ``alternative - reference`` for matching RF offsets.

    Both mappings must already be expressed relative to the same nominal-RF
    point. Keeping this operation explicit prevents a calibration comparison
    from accidentally mixing absolute ``pt`` with reference-relative ``pt``.
    """
    if set(reference) != set(alternative):
        raise ValueError("Momentum calibrations must contain the same RF offsets")
    if 0.0 in reference and (
        not np.isclose(reference[0.0], 0.0)
        or not np.isclose(alternative[0.0], 0.0)
    ):
        raise ValueError("Momentum calibrations must be zero at the nominal-RF reference")
    return {
        offset: float(alternative[offset] - reference[offset])
        for offset in sorted(reference)
    }


def frame_from_orbit(orbit: pd.DataFrame, twiss: pd.DataFrame) -> pd.DataFrame:
    """Build the orbit-zero reference from the *measured* nominal-RF closed orbit.

    The origin has to be a measured orbit. A dipole error is exactly degenerate
    with the dispersive orbit at a single momentum, so a modelled origin biases
    ``pt`` by tens of percent while looking perfectly reasonable; the
    RF-offset-0 acquisition is the only admissible reference here.

    *twiss* is accepted for a stable call signature across callers but is
    unused: tmom_recon's ``closed_orbit_at_zero`` is a plain x/y DataFrame,
    not a frame object carrying its own reference twiss.
    """
    orbit_zero = pd.DataFrame({"x": orbit["X"].astype(float)}, index=orbit.index)
    orbit_zero["y"] = orbit["Y"].astype(float) if "Y" in orbit else 0.0
    orbit_zero.index = orbit_zero.index.astype(str)
    # normalize_closed_orbit requires a "name" column, or an index named "name"
    # (case-insensitive); pin the latter rather than depend on orbit's own index name.
    orbit_zero.index.name = "name"
    return orbit_zero


def estimate_pt(
    orbit: pd.DataFrame,
    twiss: pd.DataFrame,
    frame: pd.DataFrame,
) -> float:
    """Estimate this orbit's MAD-NG ``pt`` offset from *frame*'s origin.

    *orbit* is one RF setting's measured closed orbit (``X`` in metres, indexed by
    BPM); *twiss* is the model twiss indexed by BPM, carrying ``dx`` (and ``ddx``
    where available, which makes the estimator solve the second-order relation
    instead of projecting linearly).
    """
    # ``.intersection()`` drops the index name when the two sides disagree on
    # its case ("NAME" vs "name"), which then propagates into ``twiss.loc[common]``
    # and trips tmom_recon's index-name check; pin it explicitly instead.
    common = orbit.index.intersection(twiss.index).rename("name")
    measured = pd.DataFrame({"x": orbit.loc[common, "X"].to_numpy(dtype=float)}, index=common)
    return float(
        estimate_pt_from_orbit(measured, twiss.loc[common], closed_orbit_at_zero=frame, info=False)
    )


def estimate_pt_by_rf_offset(
    orbits: dict[float, pd.DataFrame],
    twiss: pd.DataFrame,
) -> dict[float, float]:
    """Estimate ``pt`` for each RF-steering offset, keyed by that offset.

    *orbits* maps RF offset in mm to the measured closed orbit at that setting;
    the ``0.0`` entry is required and becomes the frame origin, so the returned
    ``pt`` values are offsets from nominal RF, which is what a worker pins.
    """
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
