"""Evidence for docs/studies/quadrupole-roll.md, reproducible today.

Nothing here needs the knob family the spec asks for: every case is applied by
writing element attributes directly, so this runs against the current
``aba_optimiser``. It answers three questions in order.

1. Can *any* magnet roll produce the measured vertical dispersion, and at what
   cost to the vertical closed orbit the fits already reproduce to 0.2 %?
2. Do the three PSB skew-quadrupole circuits explain it? (They are at zero on
   the machine, but the model's sensitivity is worth having on record.)
3. Is ``dpsi`` through MAD-NG's deferred misalignment table the same thing as
   rolling the element -- the assumption the whole spec rests on?

    uv run python scripts/check_quad_roll.py
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
from aba_optimiser.mad import GenericMadInterface

from loco_common.model import build_model

logger = logging.getLogger(__name__)

#: The 2026-08-21 scan, reduced the same way the option matrix reduced it:
#: dispersion is the slope of the untrimmed orbit against pt over the five
#: RF-steering settings, and the closed orbit is the untrimmed orbit itself.
MEASURED = {"dy": 0.1639, "y_co": 1.416e-3, "dx": 2.8958, "x_co": 1.017e-3}

#: One dipole's bending angle: 2*pi over 32 main bends.
BEND_ANGLE = 0.19634954084936207

#: Extends the deferred misalignment table with ``dpsi``. This is exactly the
#: change section 4.3 of the spec asks ``aba_optimiser`` to make; applying it by
#: hand here is what lets the claim be checked before the change exists.
ATTACH_DPSI = r"""
for i, e in loaded_sequence:siter() do
  if e.kind == 'quadrupole' and string.match(e.name, '^BR%.Q[FD][OE]%d+$') then
    e.dx = e.dx or 0
    e.dy = e.dy or 0
    e.dpsi = e.dpsi or 0
    e.misalign = MAD.typeid.deferred{dx =\->e.dx, dy =\->e.dy, dpsi =\->e.dpsi}
  end
end
"""


def measured_vertical_dispersion(predictions: Path) -> pd.Series | None:
    """Per-BPM measured vertical dispersion, for comparing *shape* not just rms."""
    path = predictions / "start-model.dispersion.parquet"
    if not path.exists():
        return None
    frame = pd.read_parquet(path)
    return frame[frame["plane"] == "y"].set_index("bpm")["measured"]


class Lattice:
    """The ring-3 model, with whatever element attributes a case wants written."""

    def __init__(self, sequence_file: Path, reference: pd.Series | None):
        self.sequence_file = sequence_file
        self.model = build_model(sequence_file=sequence_file)
        self.reference = reference

    def run(self, lines: list[str], *, attach_dpsi: bool = False) -> dict:
        accelerator = OptimiserPSB(
            ring=3, sequence_file=str(self.sequence_file), kinetic_energy=0.16
        )
        interface = GenericMadInterface(
            accelerator=accelerator,
            tune_knobs=self.model.tune_knobs or None,
            corrector_knobs=self.model.corrector_knobs or None,
        )
        try:
            if attach_dpsi:
                interface.mad.send(ATTACH_DPSI)
            for line in lines:
                interface.mad.send(line)
            twiss = interface.run_twiss(observe=1, method=6)
            vertical = pd.Series(
                twiss["dy"].astype(float).to_numpy(), index=twiss.index
            )
            result = {
                "y_co": rms(twiss["y"]),
                "x_co": rms(twiss["x"]),
                "dy": rms(vertical),
                "dx": rms(twiss["dx"]),
                "q1": float(twiss.headers["q1"]),
                "q2": float(twiss.headers["q2"]),
                "dy_vector": vertical,
            }
        finally:
            interface.close()
        if self.reference is not None:
            common = self.reference.index.intersection(vertical.index)
            result["shape"] = float(
                np.corrcoef(vertical.loc[common], self.reference.loc[common])[0, 1]
            )
        return result

    def elements(self) -> tuple[list[str], list[str]]:
        """Quadrupole and bend names, in s-order."""
        accelerator = OptimiserPSB(
            ring=3, sequence_file=str(self.sequence_file), kinetic_energy=0.16
        )
        interface = GenericMadInterface(accelerator=accelerator)
        try:
            table = interface.run_twiss(observe=0, method=6)
        finally:
            interface.close()
        quadrupoles = [
            name for name in table.index if name.upper().startswith(("BR.QFO", "BR.QDE"))
        ]
        bends = [name for name in table.index if name.upper().startswith("BR.BHZ")]
        return quadrupoles, bends


def rms(values) -> float:
    return float(np.sqrt(np.mean(np.square(np.asarray(values, dtype=float)))))


def unit_pattern(rng, size: int) -> np.ndarray:
    """A random pattern normalised to unit rms, so the scan variable is the rms."""
    pattern = rng.normal(size=size)
    return pattern / np.sqrt(np.mean(pattern**2))


def line(label: str, result: dict, baseline: dict) -> str:
    shape = result.get("shape")
    return (
        f"{label:38} {result['dy']:8.4f} {result['y_co']:10.3e} {result['dx']:8.4f} "
        f"{result['q2'] - baseline['q2']:+8.4f}"
        + (f" {shape:+8.3f}" if shape is not None else "")
    )


def header(columns: bool = True) -> str:
    head = f"{'case':38} {'Dy':>8} {'y_co':>10} {'Dx':>8} {'dQ2':>8}"
    return head + (f" {'shape':>8}" if columns else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sequence-file",
        type=Path,
        default=Path("models/model_qx0.165000_qy0.227500/psb3_saved.seq"),
    )
    parser.add_argument(
        "--predictions", type=Path, default=Path("results/matrix/predictions")
    )
    parser.add_argument("--seeds", type=int, default=6)
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR)

    reference = measured_vertical_dispersion(args.predictions)
    lattice = Lattice(args.sequence_file, reference)
    quadrupoles, bends = lattice.elements()
    base = lattice.run([])

    print(f"\n{len(quadrupoles)} quadrupoles, {len(bends)} bends")
    print(
        f"{'MEASURED':38} {MEASURED['dy']:8.4f} {MEASURED['y_co']:10.3e} "
        f"{MEASURED['dx']:8.4f}"
    )
    print(header(reference is not None))
    print(line("baseline (start model)", base, base))

    rng = np.random.default_rng(20260822)
    quad_pattern = unit_pattern(rng, len(quadrupoles))
    bend_pattern = unit_pattern(rng, len(bends))

    print("\n-- 1. Which magnet roll can reach the measured vertical dispersion?")
    print("   A dipole 'tilt' rotates the reference frame with the magnet, so it")
    print("   makes dispersion with no closed orbit at all. A real roll error is a")
    print("   skew dipole component and brings orbit with it.")
    for psi in (1e-3, 3e-3, 1e-2):
        result = lattice.run(
            [
                f"loaded_sequence['{name}'].tilt = {psi * value:.12e}"
                for name, value in zip(bends, bend_pattern, strict=True)
            ]
        )
        print(line(f"dipole design tilt, psi={psi:.0e}", result, base))
    for psi in (3e-4, 1e-3):
        result = lattice.run(
            [
                f"loaded_sequence['{name}'].ksl = {{{BEND_ANGLE * psi * value:.12e}}}"
                for name, value in zip(bends, bend_pattern, strict=True)
            ]
        )
        print(line(f"dipole roll error, psi={psi:.0e}", result, base))
    for psi in (1e-3, 3e-3):
        result = lattice.run(
            [
                f"loaded_sequence['{name}'].tilt = {psi * value:.12e}"
                for name, value in zip(quadrupoles, quad_pattern, strict=True)
            ]
        )
        print(line(f"quadrupole roll, psi={psi:.0e}", result, base))

    print("\n-- 2. The three skew-quadrupole circuits (machine reads 0 A on all)")
    for knob in ("kbr3qskh0", "kbr3qsk210l3", "kbr3qsk614l3"):
        for strength in (3e-3, 1e-2):
            result = lattice.run([f"MADX['{knob}'] = {strength:.15e}"])
            print(line(f"{knob} = {strength:.0e}", result, base))

    print("\n-- 3. Is dpsi through the misalignment table the same as a roll?")
    setter = [
        f"loaded_sequence['{name}'].dpsi = {3e-3 * value:.12e}"
        for name, value in zip(quadrupoles, quad_pattern, strict=True)
    ]
    no_table = lattice.run(setter)
    with_table = lattice.run(setter, attach_dpsi=True)
    rolled = lattice.run(
        [
            f"loaded_sequence['{name}'].tilt = {3e-3 * value:.12e}"
            for name, value in zip(quadrupoles, quad_pattern, strict=True)
        ]
    )
    print(line("dpsi set, no misalign table", no_table, base))
    print(line("dpsi set, misalign table carries it", with_table, base))
    print(line("element tilt (reference)", rolled, base))
    agreement = float(
        np.corrcoef(with_table["dy_vector"], rolled["dy_vector"])[0, 1]
    )
    print(f"\n   dispersion-pattern correlation, dpsi vs tilt: {agreement:+.6f}")
    print(
        "   dpsi with no table is a silent no-op: "
        f"{'CONFIRMED' if abs(no_table['dy'] - base['dy']) < 1e-12 else 'changed'}"
    )

    print("\n-- 4. Does a quadrupole roll pattern reach the measured shape?")
    print(f"{'seed':>5} {'Dy':>8} {'y_co':>10} {'Dx':>8} {'dQ2':>8} {'shape':>8}")
    for seed in range(args.seeds):
        pattern = unit_pattern(np.random.default_rng(seed), len(quadrupoles))
        result = lattice.run(
            [
                f"loaded_sequence['{name}'].tilt = {3e-3 * value:.12e}"
                for name, value in zip(quadrupoles, pattern, strict=True)
            ]
        )
        shape = result.get("shape", float("nan"))
        print(
            f"{seed:5d} {result['dy']:8.4f} {result['y_co']:10.3e} {result['dx']:8.4f} "
            f"{result['q2'] - base['q2']:+8.4f} {shape:+8.3f}"
        )


if __name__ == "__main__":
    main()
