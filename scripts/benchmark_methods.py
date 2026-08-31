"""Both methods on the same data, timed: what each costs and where they agree.

The two methods share no solver and no objective. Method 1 hands MAD-NG the
measured response matrix and matches it in one process; Method 2 fits delta
closed orbits with a Levenberg-Marquardt Gauss-Newton solve spread over one
MAD-NG worker per corrector setting. They free the *same* 32 cell-grouped
``dk1l`` knobs, so their answers are directly comparable, which makes the two
questions on this page well posed: do they land in the same place, and what does
each cost to get there.

Both are run here rather than timed from the report directories, because a
runtime is only meaningful if the two runs happen on the same machine, in the
same state, back to back. The results go to ``results/benchmark/<campaign>.json``
and nothing else reads the fits this script writes -- the pages keep using the
campaign's own results root.

Timing is wall clock plus the CPU time of the whole process tree
(``RUSAGE_CHILDREN``), because the two methods spend it differently: Method 2's
wall time is a parallel sum over workers, and reporting only wall clock would
credit it with hardware rather than efficiency.

    uv run python -m scripts.benchmark_methods --campaign normal inverted
"""

from __future__ import annotations

import argparse
import json
import logging
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from loco_common.campaign import add_campaign_argument, campaign_by_slug
from loco_common.model import DEFAULT_SEQUENCE_FILE

logger = logging.getLogger(__name__)

#: The nominal integrated gradient every report scales a ``dk1l`` by.
NOMINAL_K1L = 0.36705

#: The Method-2 case this benchmark is against: delta orbits, gradients only,
#: lumped to the same 32 knobs Method 1 fits. Any other case would be comparing
#: two different questions and calling the difference a benchmark.
METHOD2_CASE = "none__k1__bpm-family"


def _run(argv: list[str], log: Path) -> dict:
    """Run one fit, timed, and return what it cost."""
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    with log.open("w") as handle:
        result = subprocess.run(argv, stdout=handle, stderr=subprocess.STDOUT, check=False)
    wall = time.monotonic() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "command": " ".join(argv[1:]),
        "returncode": result.returncode,
        "wall_s": wall,
        "cpu_s": (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime),
        "max_rss_mb": after.ru_maxrss / 1024,
        "log": str(log),
    }


def _knobs(directory: Path) -> pd.Series:
    frame = pd.read_csv(directory / "knobs.csv").set_index("knob")["value"]
    return frame[frame.index.str.endswith(".dk1l")].sort_index()


def _agreement(first: pd.Series, second: pd.Series) -> dict:
    """How close the two answers are, on the knobs both of them fitted."""
    common = first.index.intersection(second.index)
    a = first.loc[common].to_numpy(dtype=float)
    b = second.loc[common].to_numpy(dtype=float)
    scale = 100 / NOMINAL_K1L
    difference = scale * (a - b)
    return {
        "magnets": int(len(common)),
        "distinct_method1": int(pd.Series(first.loc[common]).round(12).nunique()),
        "distinct_method2": int(pd.Series(second.loc[common]).round(12).nunique()),
        "correlation": float(np.corrcoef(a, b)[0, 1]),
        "rms_difference_pct": float(np.sqrt(np.mean(difference**2))),
        "max_difference_pct": float(np.max(np.abs(difference))),
        "rms_method1_pct": float(scale * np.sqrt(np.mean(a**2))),
        "rms_method2_pct": float(scale * np.sqrt(np.mean(b**2))),
    }


def benchmark(campaign, sequence: Path, output: Path, max_call: int) -> dict:
    """One configuration: both fits, back to back, timed and compared."""
    output.mkdir(parents=True, exist_ok=True)
    method1_dir, method2_dir = output / "method1", output / "method2"

    method1 = _run(
        [sys.executable, "-m", "method1_madng_da.run_method1",
         "--campaign", campaign.slug, "--sequence-file", str(sequence),
         "--max-call", str(max_call), "--output", str(method1_dir)],
        output / "method1.log",
    )
    method2 = _run(
        [sys.executable, "-m", "method2_delta_orbit.run_method2",
         "--campaign", campaign.slug, "--sequence-file", str(sequence),
         "--group-quadrupoles-by-cell", "--output", str(method2_dir)],
        output / "method2.log",
    )
    for name, run in (("Method 1", method1), ("Method 2", method2)):
        if run["returncode"]:
            raise SystemExit(f"{name} failed on {campaign.slug}; see {run['log']}")
        logger.info(
            "%s on %s: %.1f s wall, %.1f s CPU", name, campaign.slug,
            run["wall_s"], run["cpu_s"],
        )

    method1["summary"] = json.loads((method1_dir / "summary.json").read_text())
    method2["summary"] = json.loads((method2_dir / "summary.json").read_text())
    method1["processes"] = 1
    method2["processes"] = int(method2["summary"].get("n_settings", 0))

    return {
        "campaign": campaign.slug,
        "label": campaign.label,
        "case": METHOD2_CASE,
        "method1": method1,
        "method2": method2,
        "agreement": _agreement(_knobs(method1_dir), _knobs(method2_dir)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_campaign_argument(parser, multiple=True)
    parser.add_argument("--sequence-file", type=Path, default=DEFAULT_SEQUENCE_FILE)
    parser.add_argument("--max-call", type=int, default=4000,
                        help="Method 1's MAD.match call cap. A backstop only: the fit "
                             "stops on XTOL, when its knob steps go below "
                             "``--var-rtol``.")
    parser.add_argument("--output", type=Path, default=Path("results/benchmark"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    args.output.mkdir(parents=True, exist_ok=True)
    for slug in args.campaign:
        campaign = campaign_by_slug(slug)
        record = benchmark(campaign, args.sequence_file, args.output / slug, args.max_call)
        destination = args.output / f"{slug}.json"
        destination.write_text(json.dumps(record, indent=2))
        agreement = record["agreement"]
        logger.info(
            "%s: correlation %+.4f, rms difference %.3f %% of nominal k1L -> %s",
            slug, agreement["correlation"], agreement["rms_difference_pct"], destination,
        )


if __name__ == "__main__":
    main()
