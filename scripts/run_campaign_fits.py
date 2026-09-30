"""Run the nine cases the report pages show, for one campaign.

The cases are declared in :mod:`loco_common.case_names`; the slug ``<planes>__<families>__<lump>``
maps to the fitter's flags one-for-one. Serial by construction: each fit spawns one MAD-NG process
per corrector setting.

    uv run python scripts/run_campaign_fits.py --campaign inverted
    uv run python scripts/run_campaign_fits.py --campaign inverted --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loco_common.campaign import add_campaign_argument, campaign_by_slug
from loco_common.case_names import PAGES, PER_MAGNET_PAGE, every_page_case, parse_case
from loco_common.fit_mode import (
    MULTI,
    SINGLE,
    THREE,
    add_fit_mode_argument,
    fit_mode_by_slug,
    result_is_valid,
)

logger = logging.getLogger(__name__)

#: Both staged modes warm-start from ``single``: every campaign scanned -2/0/+2 mm, so ``three`` has no intermediate offsets.
PREVIOUS_MODE = {THREE.slug: SINGLE, MULTI.slug: SINGLE}

#: Which case family letter frees which ``--errors`` token.
ERROR_TOKENS = {"k1": "quad:k1", "b": "bend:k0", "k0s": "quad:k0s", "k1s": "quad:k1s"}
#: Which case family letter frees which ``--misalign`` token.
MISALIGN_TOKENS = {"dy": "quad:dy", "t": "quad:tilt"}

def command(
    slug: str,
    campaign: str,
    sequence_file: Path,
    output_root: Path,
    momentum_mode: str = "single",
    *,
    phase_constraint: bool = False,
    phase_weight: float = 1.0,
) -> list[str]:
    case = parse_case(slug)
    mode = fit_mode_by_slug(momentum_mode)
    campaign_object = campaign_by_slug(campaign)
    rf_offsets = mode.rf_offsets_for(campaign_object)
    if phase_constraint and mode.slug != "multi":
        raise ValueError("--phase-constraint requires --momentum-mode multi")
    argv = [
        sys.executable, "-m", "method2_delta_orbit.run_method2",
        "--campaign", campaign,
        "--sequence-file", str(sequence_file),
        "--output", str(output_root / slug),
    ]
    if case.planes != "none":
        argv += ["--absolute-planes", *list(case.planes)]
    errors = [ERROR_TOKENS[f] for f in case.family_list if f in ERROR_TOKENS]
    misalign = [MISALIGN_TOKENS[f] for f in case.family_list if f in MISALIGN_TOKENS]
    argv += ["--errors", *(errors or ["none"])]
    if misalign:
        argv += ["--misalign", *misalign]
    if case.lump != "none":
        argv += ["--group-quadrupoles-by-cell"]
    if rf_offsets != (0.0,):
        argv += ["--rf-offsets", *(f"{offset:g}" for offset in rf_offsets)]
    if mode.batch_momenta:
        argv += ["--batch-momenta"]
    if mode.slug != "single" and case.planes != "none":
        previous = PREVIOUS_MODE[mode.slug]
        initial = previous.results_root(campaign_by_slug(campaign)) / slug / "knobs.csv"
        argv += ["--initial-knobs", str(initial)]
    if phase_constraint:
        argv += ["--phase-constraint"]
        if phase_weight != 1.0:
            argv += ["--phase-weight", f"{phase_weight:g}"]
    return argv


def staged_result_is_valid(
    directory: Path,
    *,
    require_warm_start: bool,
    expected_initial: Path | None = None,
) -> bool:
    if not result_is_valid(directory):
        return False
    if not require_warm_start:
        return True
    summary = json.loads((directory / "summary.json").read_text())
    recorded = summary.get("initial_knobs")
    if not recorded:
        return False
    if expected_initial is None:
        return True
    return Path(recorded).resolve() == expected_initial.resolve()


def run_case(
    argv: list[str], destination: Path, log: Path, *, require_warm_start: bool
) -> bool:
    """Run into a sibling staging directory and publish only a valid fit."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    staged = staging_root / destination.name
    staged_argv = argv.copy()
    staged_argv[staged_argv.index("--output") + 1] = str(staged)
    with log.open("w") as handle:
        result = subprocess.run(staged_argv, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if result.returncode or not staged_result_is_valid(
        staged, require_warm_start=require_warm_start
    ):
        shutil.rmtree(staging_root)
        return False

    backup = destination.with_name(f".{destination.name}.previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        destination.replace(backup)
    staged.replace(destination)
    shutil.rmtree(staging_root)
    if backup.exists():
        shutil.rmtree(backup)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_campaign_argument(parser, default="p23_p13_final")
    add_fit_mode_argument(parser)
    parser.add_argument("--sequence-file", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--log-dir", type=Path, default=Path("/tmp/campaign_fits"))
    parser.add_argument("--cases", nargs="+", default=None, help="Case slugs; default is every page case.")
    parser.add_argument(
        "--phase-constraint",
        action="store_true",
        help=(
            "Add the phase-advance constraint (docs/studies/phase-advance-constraint.md) "
            "to every case. Requires --momentum-mode multi and the campaign's "
            "optics at every RF offset (scripts/measured_optics.py --optics-folders "
            "all). Writes to a separate '_phase'-suffixed results root unless "
            "--output overrides it."
        ),
    )
    parser.add_argument(
        "--phase-weight",
        type=float,
        default=1.0,
        help="Passed through to run_method2.py's --phase-weight; see its help.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.phase_constraint and args.momentum_mode != "multi":
        raise SystemExit("--phase-constraint requires --momentum-mode multi")

    from loco_common.model import DEFAULT_SEQUENCE_FILE

    campaign = campaign_by_slug(args.campaign)
    mode = fit_mode_by_slug(args.momentum_mode)
    sequence_file = args.sequence_file or DEFAULT_SEQUENCE_FILE
    default_root = mode.results_root(campaign)
    if args.phase_constraint and args.output is None:
        default_root = default_root.with_name(f"{default_root.name}_phase")
    output_root = args.output or default_root
    args.log_dir.mkdir(parents=True, exist_ok=True)

    multi_cases = list(
        dict.fromkeys(slug for page in (*PAGES, PER_MAGNET_PAGE) for slug in page.cases)
    )
    cases = args.cases or (multi_cases if mode.slug == "multi" else every_page_case())
    for slug in cases:
        case = parse_case(slug)
        warm_start = mode.slug != "single" and case.planes != "none"
        argv = command(
            slug, campaign.slug, sequence_file, output_root, mode.slug,
            phase_constraint=args.phase_constraint, phase_weight=args.phase_weight,
        )
        if args.dry_run:
            print(" ".join(argv))
            continue
        if warm_start:
            # Only the mode the warm start is read from.
            prerequisite = PREVIOUS_MODE[mode.slug]
            prerequisite_destination = prerequisite.results_root(campaign) / slug
            if not staged_result_is_valid(prerequisite_destination, require_warm_start=False):
                prerequisite_argv = command(
                    slug,
                    campaign.slug,
                    sequence_file,
                    prerequisite.results_root(campaign),
                    prerequisite.slug,
                )
                prerequisite_log = (
                    args.log_dir / f"{campaign.slug}__{prerequisite.slug}__{slug}.log"
                )
                logger.info(
                    "=== %s warm start %s -> %s", prerequisite.label, slug, prerequisite_log
                )
                if not run_case(
                    prerequisite_argv,
                    prerequisite_destination,
                    prerequisite_log,
                    require_warm_start=False,
                ):
                    logger.error(
                        "FAILED %s warm start %s (see %s)",
                        prerequisite.label,
                        slug,
                        prerequisite_log,
                    )
                    continue
        destination = output_root / slug
        expected_initial = (
            Path(argv[argv.index("--initial-knobs") + 1]) if warm_start else None
        )
        if staged_result_is_valid(
            destination,
            require_warm_start=warm_start,
            expected_initial=expected_initial,
        ):
            logger.info("skip %s (already fitted)", slug)
            continue
        log = args.log_dir / f"{campaign.slug}__{mode.slug}__{slug}.log"
        logger.info("=== %s -> %s", slug, log)
        started = time.monotonic()
        succeeded = run_case(argv, destination, log, require_warm_start=warm_start)
        elapsed = time.monotonic() - started
        if not succeeded:
            logger.error("FAILED %s after %.0f s (see %s)", slug, elapsed, log)
        else:
            logger.info("done %s in %.0f s", slug, elapsed)


if __name__ == "__main__":
    main()
