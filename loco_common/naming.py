"""Names and units shared by both LOCO methods.

The scan log records correctors as LSA parameter names (``logical.BR3.DHZ8L1/K``);
the model knows them as MAD-X global knob variables (``kbr3dhz8l1``) attached to
sequence elements (``BR3.DHZ8L1``) through the deferred expression
``kick := kbr3dhz8l1`` in the ring-3 sequence. Both methods need the round trip,
so it lives here rather than being re-derived in each.
"""

from __future__ import annotations

import re

from psb_md.names import normalise_element_name

#: Magnitude of the conversion from an LSA ``/K`` step to a MAD kick, in rad.
#:
#: LSA's ``/K`` for a PSB DHZ/DVT trim *is* the kick angle in rad, so this is
#: exactly one. It is kept as a named constant rather than left implicit because
#: it is an assumption about the control system, not a fact about the model: if it
#: is wrong every fitted gradient is wrong by the same factor and nothing else
#: would show it. ``tests/test_naming.py`` pins it against xsuite by applying the
#: same step through both codes.
LSA_K_TO_RAD = 1.0

#: Sign of an LSA ``/K`` step relative to MAD's ``kick``, per plane.
#:
#: The horizontal correctors are inverted; the vertical ones are not. This is not
#: a guess and it is not fitted -- it is what the 2026-08-21 scan says. Against
#: the ring-3 model the measured response of all six DHZ correctors comes back at
#: correlation -0.998 and all six DVT at +0.999.
#:
#: Two things could produce that: this sign, or a flipped BPM horizontal reading.
#: They predict identical response matrices, so the response cannot separate them
#: -- the dispersion orbit can, since no corrector touches it. The measured
#: horizontal dispersion tracks the model's with the *correct* sign (implied
#: dp/p of -4.90, -2.47, +2.34, +4.65 e-4 at RF offsets -2, -1, +1, +2 mm:
#: right sign, linear and symmetric), so the BPM reading is right and the
#: corrector convention is what is inverted. ``tests/test_naming.py`` reproduces
#: that argument from the cached measurement.
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
