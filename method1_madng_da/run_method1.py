"""Method 1 driver: fit quadrupole ``k1`` to the measured orbit-response matrix.

Everything numerical happens in ``response_da.mad``; this module's job is to
stand the ring-3 model up, hand MAD-NG the measured response as two matrices,
run the match and write the result out in the same format as every other psb_md
optimisation stage.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
from aba_optimiser.mad import GradientDescentMadInterface
from psb_md.optimisation import write_optimisation_results

from loco_common.campaign import add_campaign_argument, campaign_by_slug
from loco_common.measured_response import cached_response
from loco_common.model import LocoModel, build_model
from loco_common.naming import lsa_k_to_rad, lsa_to_element

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

SCRIPT = Path(__file__).with_name("response_da.mad")


@dataclass
class Method1Result:
    """What one Method-1 fit produced."""

    knobs: dict[str, float]
    n_fit_parameters: int
    bpm_names: list[str]
    correctors: list[str]
    response_before: np.ndarray
    response_after: np.ndarray
    target: np.ndarray
    weight: np.ndarray
    status: str
    fmin: float
    ncall: int

    def residual_rms(self, response: np.ndarray) -> float:
        """Weighted RMS of ``response - target`` over the measured points."""
        residual = self.weight * (response - self.target)
        points = int(np.count_nonzero(self.weight))
        return float(np.sqrt(np.sum(residual**2) / max(points, 1)))


def _matrices(
    response: pd.DataFrame, bpm_names: list[str], correctors: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Lay slopes out on the model's ``(2*BPM, corrector)`` grid.

    The slopes are measured per LSA ``/K`` step, so they are converted to m/rad
    by :func:`lsa_k_to_rad` before meeting a model that works in kick angles --
    signed, and negative for the horizontal correctors. The weight takes the
    magnitude, since a sign does not change the size of an error bar. A
    BPM/corrector pair the scan does not carry gets weight zero, which removes it
    rather than pulling it to zero.
    """
    target = np.zeros((2 * len(bpm_names), len(correctors)))
    weight = np.zeros_like(target)
    indexed = response.set_index(["NAME", "PLANE", "CORRECTOR"])
    for p, plane in enumerate(("x", "y")):
        for b, bpm in enumerate(bpm_names):
            matrix_row = p * len(bpm_names) + b
            for i, corrector in enumerate(correctors):
                factor = lsa_k_to_rad(corrector)
                try:
                    row = indexed.loc[(bpm, plane, corrector)]
                except KeyError:
                    continue
                slope, error = float(row["SLOPE"]), float(row["ERRSLOPE"])
                if not np.isfinite(slope) or not np.isfinite(error) or error <= 0.0:
                    continue
                target[matrix_row, i] = slope / factor
                weight[matrix_row, i] = abs(factor) / error
    logger.info(
        "Response grid: %d BPM channels x %d correctors, %d usable points",
        2 * len(bpm_names),
        len(correctors),
        int(np.count_nonzero(weight)),
    )
    return target, weight


def run(
    response: pd.DataFrame,
    model: LocoModel,
    *,
    max_call: int = 50,
    fmin: float = 1e-12,
    var_tol: float = 0.0,
    var_rtol: float = 3e-3,
    info_level: int = 2,
) -> Method1Result:
    """Run the parametric-twiss match and return the fitted ``dk1l`` knobs."""
    correctors = sorted(response["CORRECTOR"].unique())
    accelerator = OptimiserPSB(
        ring=model.ring,
        sequence_file=model.sequence_file,
        kinetic_energy=model.kinetic_energy,
        optimise_quadrupoles=True,
        group_quadrupoles_by_cell=True,
    )
    interface = GradientDescentMadInterface(
        accelerator=accelerator,
        tune_knobs=model.tune_knobs or None,
        corrector_knobs=model.corrector_knobs or None,
    )
    try:
        mad = interface.mad
        quad_knobs = list(interface.knob_names)
        logger.info("Freeing %d cell-grouped quadrupole dk1l knobs", len(quad_knobs))

        mad["corr_elements"] = [lsa_to_element(name) for name in correctors]
        mad["quad_knobs"] = quad_knobs
        # The BPM grid has to be the model's, so send placeholder matrices, run
        # one twiss to learn the observed BPM ordering, then send the real
        # targets on that ordering.
        mad["target_mat"] = np.zeros((1, len(correctors)))
        mad["weight_mat"] = np.zeros((1, len(correctors)))
        # The script writes back through ``pyi``; bind it to whatever this
        # interface named its Python channel rather than assuming a name.
        mad.send(f"pyi = {interface.py_name}")
        mad.send(SCRIPT.read_text())
        mad.send("compute_response(); send_response()")
        bpm_names = [str(name) for name in mad.recv()]
        response_before = np.asarray(mad.recv(), dtype=float)

        target, weight = _matrices(response, bpm_names, correctors)
        mad["target_mat"] = target
        mad["weight_mat"] = weight
        mad.send(
            f"py:send({{run_match({int(max_call)}, {fmin:.15e}, {var_tol:.15e}, "
            f"{var_rtol:.15e}, {int(info_level)})}}, true)"
        )
        status, final_objective, ncall = mad.recv()

        mad.send("compute_response(); send_response()")
        mad.recv()
        response_after = np.asarray(mad.recv(), dtype=float)
        mad.send("send_quad_knobs()")
        knob_values = np.asarray(mad.recv(), dtype=float).ravel()
    finally:
        interface.close()

    return Method1Result(
        knobs=accelerator.format_result_knobs(
            dict(zip(quad_knobs, (float(v) for v in knob_values), strict=True))
        ),
        n_fit_parameters=len(quad_knobs),
        bpm_names=bpm_names,
        correctors=correctors,
        response_before=response_before,
        response_after=response_after,
        target=target,
        weight=weight,
        status=str(status),
        fmin=float(final_objective),
        ncall=int(ncall),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-offset", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--max-call", type=int, default=4000,
        help="Hard cap on MAD.match calls. A backstop, not the stopping rule: "
             "the fit is meant to end on XTOL (see --var-rtol), and a MAXCALL in "
             "the summary means it did not.",
    )
    parser.add_argument(
        "--fmin", type=float, default=1e-12,
        help="Objective value that counts as solved. On measured data it is "
             "never reached -- the response residual is thousands of sigma -- so "
             "it is the tolerances below that stop the match.",
    )
    parser.add_argument(
        "--var-tol", type=float, default=0.0,
        help="Absolute tolerance on each knob's step (MAD-NG variables[i].tol). "
             "0 disables it.",
    )
    parser.add_argument(
        "--var-rtol", type=float, default=3e-3,
        help="Relative tolerance on the knob steps (MAD-NG variables.rtol): stop "
             "with status XTOL once no knob moves by this much of itself. This is "
             "the criterion that stops the fit -- the objective tolerances are "
             "only tested at a feasible point, and measured data never is.",
    )
    parser.add_argument("--sequence-file", type=Path, default=None)
    add_campaign_argument(parser)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    campaign = campaign_by_slug(args.campaign)
    result = run(
        cached_response(args.rf_offset, campaign=campaign),
        build_model(
            sequence_file=args.sequence_file, campaign=campaign
        ),
        max_call=args.max_call,
        fmin=args.fmin,
        var_tol=args.var_tol,
        var_rtol=args.var_rtol,
    )

    output = args.output or campaign.method1_dir
    output.mkdir(parents=True, exist_ok=True)
    physical_knobs = result.knobs
    write_optimisation_results(
        output / "knobs.csv",
        physical_knobs,
        dict.fromkeys(physical_knobs, 0.0),
        stage_name="loco_method1",
    )
    summary = {
        "method": "madng_da",
        "rf_offset": args.rf_offset,
        "correctors": result.correctors,
        "bpms": result.bpm_names,
        "n_quadrupole_knobs": result.n_fit_parameters,
        "n_output_knobs": len(physical_knobs),
        "status": result.status,
        "fmin": result.fmin,
        "ncall": result.ncall,
        "max_call": args.max_call,
        "objective_fmin": args.fmin,
        "variable_tol": args.var_tol,
        "variable_rtol": args.var_rtol,
        "residual_rms_before": result.residual_rms(result.response_before),
        "residual_rms_after": result.residual_rms(result.response_after),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    logger.info(
        "Method 1 done: weighted response RMS %.4e -> %.4e (%s, %d calls)",
        summary["residual_rms_before"],
        summary["residual_rms_after"],
        result.status,
        result.ncall,
    )


if __name__ == "__main__":
    main()
