"""Plot the POCO fitter's convergence trace: loss, gradient and damping per iteration.

POCO logs ``GN iter N: loss=..., |g|=..., lam=...``. Redirect a run's output to a file and pass it
here; several logs can be overlaid.

    python -m poco.run_poco ... > run_a.log 2>&1
    python scripts/plot_optimiser_convergence.py \
        --log run_a.log "poco, normal, default prior" \
        --output convergence.png
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt

ITER_RE = re.compile(
    r"GN iter (?P<iter>\d+): loss=(?P<loss>[\d.eE+-]+), "
    r"\|g\|=(?P<grad>[\d.eE+-]+), lam=(?P<lam>[\d.eE+-]+)"
)
PRIOR_RE = re.compile(
    r"Knob prior for (?P<family>\S+): \d+ knobs, alpha=(?P<alpha>[\d.eE+-]+) "
    r"\(strength=(?P<strength>[\d.eE+-]+) x median diag H=(?P<diagh>[\d.eE+-]+)\)"
)

COLOURBLIND_PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")


def parse_log(path: Path) -> dict[str, list[float]]:
    """One POCO run's per-GN-iteration trace."""
    iters: list[int] = []
    losses: list[float] = []
    grads: list[float] = []
    lams: list[float] = []
    priors: list[str] = []
    for line in path.read_text().splitlines():
        m = ITER_RE.search(line)
        if m:
            iters.append(int(m["iter"]))
            losses.append(float(m["loss"]))
            grads.append(float(m["grad"]))
            lams.append(float(m["lam"]))
            continue
        m = PRIOR_RE.search(line)
        if m:
            priors.append(
                f"{m['family']}: alpha={float(m['alpha']):.3e} "
                f"(strength={float(m['strength']):.1e} x diagH={float(m['diagh']):.3e})"
            )
    if not iters:
        raise ValueError(f"{path}: no 'GN iter' lines found")
    return {"x": iters, "loss": losses, "grad": grads, "lam": lams, "priors": priors}


def plot_runs(runs: list[tuple[str, dict]], output: Path) -> None:
    figure, axes = plt.subplots(3, 1, figsize=(8, 10), sharex=False)
    for (label, trace), colour in zip(runs, COLOURBLIND_PALETTE * 4, strict=False):
        for axis, key in zip(axes, ("loss", "grad", "lam"), strict=True):
            axis.plot(trace["x"], trace[key], "o-", color=colour, label=label)
    for ax, ylabel in zip(axes, ("loss", "|gradient|", "damping (lam)"), strict=True):
        ax.set_yscale("log")
        ax.set_ylabel(ylabel)
        ax.grid(True, which="both", alpha=0.3)
    axes[0].legend(fontsize="small", loc="best")
    axes[-1].set_xlabel("GN iteration")
    figure.suptitle("POCO convergence (Levenberg-Marquardt)")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    print(f"Wrote {output}")
    for label, trace in runs:
        print(f"\n{label}:")
        for line in trace["priors"]:
            print(f"  {line}")
        print(
            f"  final: x={trace['x'][-1]} loss={trace['loss'][-1]:.3e} "
            f"|g|={trace['grad'][-1]:.3e} lam={trace['lam'][-1]:.3e}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log", nargs=2, action="append", metavar=("LOGFILE", "LABEL"), required=True,
        dest="logs", help="A captured run_poco log and the label to plot it under. Repeatable.",
    )
    parser.add_argument("--output", type=Path, default=Path("plots/convergence.png"))
    args = parser.parse_args()

    runs = [(label, parse_log(Path(path))) for path, label in args.logs]
    plot_runs(runs, args.output)


if __name__ == "__main__":
    main()
