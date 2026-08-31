"""Chromaticity convention shared by measurement and fitted-lattice reports."""

from __future__ import annotations

import math

PROTON_MASS_GEV = 0.93827208816


def chromaticity_from_dq_dpt(headers: dict) -> tuple[float, float]:
    """Convert MAD-NG ``dQ/dpt`` to conventional ``Q' = dQ/d(delta)``."""
    gamma = float(headers["energy"]) / PROTON_MASS_GEV
    beta = math.sqrt(1.0 - 1.0 / gamma**2)
    return tuple(beta * float(headers[f"dq{plane}"]) for plane in (1, 2))
