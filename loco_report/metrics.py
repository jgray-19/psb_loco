"""Rms conventions. Every quoted number on a page comes from here."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rms(values) -> float:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    return float(np.sqrt(np.mean(values**2))) if values.size else float("nan")


def at_elements(elements, values) -> pd.Series:
    """A curve indexed by upper-case element name, duplicates dropped."""
    series = pd.Series(values, index=pd.Index(elements).astype(str).str.upper())
    return series[~series.index.duplicated()]


def rms_vs_measured(elements, values, measured: pd.Series | None,
                    *, relative: bool) -> float | None:
    """One curve against the measured beta-beating at the same BPMs."""
    if measured is None or measured.empty:
        return None
    curve = at_elements(elements, values).reindex(measured.index.str.upper())
    valid = curve.notna().to_numpy()
    if not valid.any():
        return None
    diff = curve.to_numpy()[valid] - measured.to_numpy()[valid]
    return 100 * rms(diff) if relative else rms(diff)


def rms_vs_measured_dispersion(elements, values, measured: pd.DataFrame,
                               plane: str) -> float | None:
    """One dispersion curve against the measured points, as % of the measured rms."""
    points = measured[measured["plane"] == plane]
    if points.empty:
        return None
    curve = at_elements(elements, values)
    at_bpm = points["bpm"].astype(str).str.upper().map(curve)
    valid = at_bpm.notna()
    if not valid.any():
        return None
    measured_values = points.loc[valid, "measured"].to_numpy()
    denominator = rms(measured_values)
    diff = measured_values - at_bpm[valid].to_numpy()
    return 100 * rms(diff) / denominator if denominator else None


def per_bpm_rms(frame: pd.DataFrame, plane: str) -> pd.Series:
    """Residual rms per BPM, in mm, for one plane of one prediction frame."""
    block = frame[frame["plane"] == plane]
    if block.empty:
        return pd.Series(dtype=float)
    residual = 1e3 * (block["measured"] - block["model"])
    return residual.groupby(block["bpm"], sort=False).apply(
        lambda values: float(np.sqrt(np.mean(np.square(values))))
    )
