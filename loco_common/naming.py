"""Names and units shared by both LOCO methods.

Maps LSA parameter names (``logical.BR3.DHZ8L1/K``) to MAD-X knob variables
(``kbr3dhz8l1``) and sequence elements (``BR3.DHZ8L1``).
"""

from __future__ import annotations

import re

from psb_md.names import normalise_element_name

#: Magnitude of an LSA ``/K`` step as a MAD kick, in rad; pinned against xsuite in ``tests/test_naming.py``.
LSA_K_TO_RAD = 1.0

#: Sign of an LSA ``/K`` step relative to MAD's ``kick``, per plane.
#: Horizontal correctors are inverted (2026-08-21 scan: DHZ response correlation -0.998, DVT +0.999).
#: The dispersion orbit rules out a flipped BPM reading; ``tests/test_naming.py`` reproduces that check.
LSA_K_SIGN: dict[str, float] = {"x": -1.0, "y": 1.0}

#: ``logical.BR<ring>.<magnet>/<property>``.
_LSA_PATTERN = re.compile(r"^(?:logical\.)?(?P<element>[A-Za-z0-9._]+?)(?:/(?P<property>\w+))?$")


def lsa_to_element(parameter: str) -> str:
    """``logical.BR3.DHZ8L1/K`` -> ``BR3.DHZ8L1`` (the MAD-NG element name)."""
    match = _LSA_PATTERN.match(parameter.strip())
    if match is None:
        raise ValueError(f"Unrecognised LSA parameter name: {parameter!r}")
    return normalise_element_name(match.group("element"))


def element_to_knob(element: str) -> str:
    """``BR3.DHZ8L1`` -> ``kbr3dhz8l1``, the MAD-X variable the element defers to."""
    return "k" + normalise_element_name(element).replace(".", "").lower()


def lsa_to_knob(parameter: str) -> str:
    """``logical.BR3.DHZ8L1/K`` -> ``kbr3dhz8l1``."""
    return element_to_knob(lsa_to_element(parameter))


def plane_of(parameter: str) -> str:
    """``"x"`` for a DHZ corrector, ``"y"`` for a DVT one."""
    element = lsa_to_element(parameter)
    if ".DHZ" in element:
        return "x"
    if ".DVT" in element:
        return "y"
    raise ValueError(f"Cannot infer a plane from {parameter!r}")


def lsa_k_to_rad(parameter: str) -> float:
    """Signed conversion from this corrector's LSA ``/K`` to a MAD kick, in rad.

    Negative for the horizontal correctors: see :data:`LSA_K_SIGN`. Use this
    rather than :data:`LSA_K_TO_RAD` anywhere a measured step or slope crosses
    into the model, since the two planes do not share a sign.
    """
    return LSA_K_SIGN[plane_of(parameter)] * LSA_K_TO_RAD
