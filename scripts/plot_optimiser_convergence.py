"""Plot both LOCO fitters' convergence trace: loss vs. call/iteration.

Method 2 (Levenberg-Marquardt, ``aba_optimiser.training_closed_twiss.fitter``)
logs ``GN iter N: loss=..., |g|=..., lam=...`` at INFO level. Method 1
(MAD-NG's own ``match``, ``method1_madng_da/response_da.mad``) prints
``ncall=N [Ts], fval=..., fstp=..., ccnt=...`` to MAD's own stdout, which
passes straight through the Python process. Neither needs a code change to
plot -- just redirect the run's stdout/stderr to a file and pass it here.
Several logs (any mix of the two methods) can be overlaid to compare runs
(different campaigns, priors, or ``--initial-knobs`` starting points).

    python -m method2_delta_orbit.run_method2 ... > run_a.log 2>&1
    python -m method1_madng_da.run_method1 ... > run_b.log 2>&1
    python scripts/plot_optimiser_convergence.py \
        --log run_a.log "method2, normal, default prior" \
        --log run_b.log "method1, normal" \
        --output convergence.png
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt

METHOD2_ITER_RE = re.compile(
    r"GN iter (?P<iter>\d+): loss=(?P<loss>[\d.eE+-]+), "
    r"\|g\|=(?P<grad>[\d.eE+-]+), lam=(?P<lam>[\d.eE+-]+)"
)
METHOD2_PRIOR_RE = re.compile(
    r"Knob prior for (?P<family>\S+): \d+ knobs, alpha=(?P<alpha>[\d.eE+-]+) "
    r"\(strength=(?P<strength>[\d.eE+-]+) x median diag H=(?P<diagh>[\d.eE+-]+)\)"
)
#: MAD-NG's own match trace (Method 1): "ncall=N [Ts], fval=X, fstp=Y, ccnt=Z."
METHOD1_CALL_RE = re.compile(
    r"ncall=(?P<call>\d+) \[(?P<t>[\d.]+)s\], fval=(?P<fval>[\d.eE+-]+), "
    r"fstp=(?P<fstp>-?inf|[\d.eE+-]+)"
)

COLOURBLIND_PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")


def parse_method2_log(path: Path) -> dict[str, list[float]] | None:
    """One Method 2 run's per-GN-iteration trace, or None if this isn't one."""
    iters: list[int] = []
    losses: list[float] = []
    grads: list[float] = []
    lams: list[float] = []
    priors: list[str] = []
    for line in path.read_text().splitlines():
        m = METHOD2_ITER_RE.search(line)
        if m:
            iters.append(int(m["iter"]))
            losses.append(float(m["loss"]))
            grads.append(float(m["grad"]))
            lams.append(float(m["lam"]))
            continue
        m = METHOD2_PRIOR_RE.search(line)
        if m:
            priors.append(
                f"{m['family']}: alpha={float(m['alpha']):.3e} "
                f"(strength={float(m['strength']):.1e} x diagH={float(m['diagh']):.3e})"
            )
    if not iters:
        return None
    return {"x": iters, "loss": losses, "grad": grads, "lam": lams, "priors": priors,
            "method": "method2", "xlabel": "GN iteration"}


def parse_method1_log(path: Path) -> dict[str, list[float]] | None:
    """One Method 1 (MAD-NG match) run's per-call objective trace, or None.

    ``run_method1`` calls MAD's ``match`` twice -- a small preliminary one
    (``ccnt=2``, tune/setup bookkeeping) and the real 384-constraint response
    fit. ``ncall`` restarts at 1 for each, so blocks are split wherever it
    drops, and only the longest block (the real fit) is kept.
    """
    blocks: list[tuple[list[int], list[float]]] = []
    calls: list[int] = []
    fvals: list[float] = []
    for line in path.read_text().splitlines():
        m = METHOD1_CALL_RE.search(line)
        if not m:
            continue
        call = int(m["call"])
        if calls and call <= calls[-1]:
            blocks.append((calls, fvals))
            calls, fvals = [], []
        calls.append(call)
        fvals.append(float(m["fval"]))
    if calls:
        blocks.append((calls, fvals))
    if not blocks:
        return None
    calls, fvals = max(blocks, key=lambda block: len(block[0]))
    return {"x": calls, "loss": fvals, "grad": [], "lam": [], "priors": [],
            "method": "method1", "xlabel": "match call"}


def parse_log(path: Path) -> dict[str, list[float]]:
    """Detect which fitter wrote this log and parse its convergence trace."""
    trace = parse_method2_log(path) or parse_method1_log(path)
    if trace is None:
        raise ValueError(
            f"{path}: no 'GN iter' (method2) or 'ncall=' (method1) lines found"
        )
    return trace


def plot_runs(runs: list[tuple[str, dict]], output: Path) -> None:
    """Loss always plots (both methods have it); |gradient|/damping are method2-only.

    Method 1's x-axis is match *calls*, method 2's is GN *iterations* -- not the
    same unit, so mixing them on one x-axis is a rough visual comparison of
    convergence shape/speed, not a call-for-call one.
    """
    has_method2 = any(trace["method"] == "method2" for _, trace in runs)
    n_panels = 3 if has_method2 else 1
    figure, axes = plt.subplots(n_panels, 1, figsize=(8, 10 if has_method2 else 4), sharex=False)
    axes = [axes] if n_panels == 1 else list(axes)
    for (label, trace), colour in zip(runs, COLOURBLIND_PALETTE * 4, strict=False):
        marker = "o-" if trace["method"] == "method2" else "s--"
        axes[0].plot(trace["x"], trace["loss"], marker, color=colour, label=label)
        if trace["method"] == "method2":
            axes[1].plot(trace["x"], trace["grad"], marker, color=colour, label=label)
            axes[2].plot(trace["x"], trace["lam"], marker, color=colour, label=label)
    labels = ("loss / objective", "|gradient|", "damping (lam)")
    for ax, ylabel in zip(axes, labels[:n_panels], strict=True):
        ax.set_yscale("log")
        ax.set_ylabel(ylabel)
        ax.grid(True, which="both", alpha=0.3)
    axes[0].legend(fontsize="small", loc="best")
    axes[-1].set_xlabel("iteration (method2: GN iter; method1: match call)")
    figure.suptitle("LOCO fitter convergence (method2: LM; method1: MAD-NG match)")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    print(f"Wrote {output}")
    for label, trace in runs:
        print(f"\n{label} ({trace['method']}):")
        for line in trace["priors"]:
            print(f"  {line}")
        tail = f"  final: x={trace['x'][-1]} loss={trace['loss'][-1]:.3e}"
        if trace["method"] == "method2":
            tail += f" |g|={trace['grad'][-1]:.3e} lam={trace['lam'][-1]:.3e}"
        print(tail)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log", nargs=2, action="append", metavar=("LOGFILE", "LABEL"), required=True,
        dest="logs", help="A captured run_method2 log and the label to plot it under. Repeatable.",
    )
    parser.add_argument("--output", type=Path, default=Path("plots/convergence.png"))
    args = parser.parse_args()

    runs = [(label, parse_log(Path(path))) for path, label in args.logs]
    plot_runs(runs, args.output)


if __name__ == "__main__":
    main()
