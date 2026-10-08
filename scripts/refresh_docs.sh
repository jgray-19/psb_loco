#!/bin/sh
# Full LOCO report pipeline for one direction's campaigns.
#
#     sh scripts/refresh_docs.sh inverted
#     sh scripts/refresh_docs.sh normal
#
# Each stage's
# stdout/stderr goes to its own file under .logs/, named with the $TAG prefix so
# a normal-tunes refresh cannot overwrite an inverted one. Independent
# (campaign, mode) work runs in parallel within a stage -- see the comment above
# each loop for why that stage in particular is safe to parallelise.
set -eu
cd "$(dirname "$0")/.."

mkdir -p .logs

DIRECTION="${1:?usage: $0 <inverted|normal>}"
TAG="$DIRECTION"

# One interpreter for every stage. A bare `python` resolves to whatever venv the
# shell has active, and sgd-magnet-tuner's .venv has no psb_md. Override with
# PYTHON=... if needed.
PYTHON="${PYTHON:-$(cd .. && pwd)/accpy/bin/python}"
[ -x "$PYTHON" ] || { echo "no interpreter at $PYTHON" >&2; exit 1; }

run() {
    name="$1"
    shift
    echo "==> ${name}"
    "$@" > ".logs/${TAG}_${name}.log" 2>&1
}

# Waits for every background job started since the last call, failing if any
# of them did. $1.. are the names to report on failure.
wait_all() {
    status=0
    for pid in $pids; do
        wait "$pid" || status=1
    done
    pids=""
    [ "$status" -eq 0 ] || { echo "one or more of: $* failed; see .logs/" >&2; exit 1; }
}

# The campaigns this direction's pages tab between, from the registry rather
# than a second hand-maintained list.
CAMPAIGNS=$("$PYTHON" -c "
from loco_common.campaign import INVERTED_PAGE_CAMPAIGNS, NORMAL_PAGE_CAMPAIGNS
groups = {'inverted': INVERTED_PAGE_CAMPAIGNS, 'normal': NORMAL_PAGE_CAMPAIGNS}
print(' '.join(c.slug for c in groups['$DIRECTION']))
")

# Clear cached artifacts so every stage is forced to regenerate from scratch.
# Comment this block out to reuse whatever is already on disk.
for campaign in $CAMPAIGNS; do
    rm -f "data/${campaign}_scan_points.parquet" "data/${campaign}_scan_orbits.parquet"
    rm -rf "results/optics/${campaign}"
    rm -rf "docs/assets/figures/${campaign}"
    for mode in single multi; do
        suffix="_${mode}"
        [ "$mode" = single ] && suffix=""
        rm -rf "results/matrix_${campaign}${suffix}"
    done
done
rm -rf "docs/assets/figures/scenarios/${DIRECTION}" "results/cross_campaign/${DIRECTION}"

# Stage 1: measured optics, first, one independent process per campaign -- each
# writes only under results/optics/<campaign>/, so these can run at once. Every
# RF folder gets the full cleaned harpy/omc3 chain (--optics-folders all, about
# an hour per folder), because stage 2b's phase constraint reads the optics at
# every offset. This is also where each campaign's scan cache
# (data/<campaign>_scan_*.parquet) is rebuilt, before any later stage reads it
# concurrently.
pids=""
for campaign in $CAMPAIGNS; do
    run "measured_optics_${campaign}" "$PYTHON" scripts/measured_optics.py --campaign "$campaign" --optics-folders all &
    pids="$pids $!"
done
wait_all measured_optics

# Stage 2: the fit pipeline, one chain per campaign, every campaign at once.
# Only the multi-momentum fits are reported; run_campaign_fits fits the
# single-momentum warm start of each absolute case itself.
# predict_loco writes scoreboard.shard1of1.csv and only --merge turns that into
# the scoreboard.csv that loco_report's scores figure reads, so the merge is
# part of the chain, not optional.
for mode in multi; do
    pids=""
    for campaign in $CAMPAIGNS; do
        (
            run "run_campaign_fits_${campaign}_${mode}" "$PYTHON" scripts/run_campaign_fits.py --campaign "$campaign" --momentum-mode "$mode"
            run "predict_loco_${campaign}_${mode}"      "$PYTHON" scripts/predict_loco.py --campaign "$campaign" --momentum-mode "$mode"
            run "predict_merge_${campaign}_${mode}"     "$PYTHON" scripts/predict_loco.py --campaign "$campaign" --momentum-mode "$mode" --merge
            run "case_optics_${campaign}_${mode}"       "$PYTHON" scripts/case_optics.py --campaign "$campaign" --momentum-mode "$mode"
        ) &
        pids="$pids $!"
    done
    wait_all "run_campaign_fits/predict_loco/case_optics (${mode})"
done

# Stage 2b: the phase-advance-constrained multi-momentum case matrix
# (docs/studies/phase-advance-constraint.md, implementation in
# phase_advance_constraint/): every multi-momentum case, with one extra
# plain-twiss, no-corrector series per RF offset whose residual is only
# BPM-to-BPM phase advance, added alongside the existing orbit-only
# corrector-trim settings. The phase is stage 1's cleaned optics under
# results/optics/<campaign>/<folder>/free; the closed orbits are the LOCO scan.
# Only the two baseline campaigns run here. Writes to
# results/matrix_<campaign>_multi_phase/, alongside (not over) the non-phase
# multi results.
pids=""
for campaign in $CAMPAIGNS; do
    case "$campaign" in
        p17_p23_final|p23_p13_final)
            rm -rf "results/matrix_${campaign}_multi_phase"
            run "run_campaign_fits_${campaign}_multi_phase" "$PYTHON" scripts/run_campaign_fits.py \
                --campaign "$campaign" --momentum-mode multi --phase-constraint &
            pids="$pids $!"
            ;;
    esac
done
[ -n "$pids" ] && wait_all run_campaign_fits_multi_phase

# Stage 3: combine this direction's cross-campaign comparison once (analysis),
# then draw it once (plotting). --direction keeps the run off the other
# direction's results, which this script has not refreshed.
run analyse_cross_campaign "$PYTHON" scripts/analyse_cross_campaign.py --direction "$DIRECTION"
run plot_cross_campaign "$PYTHON" scripts/plot_cross_campaign.py --direction "$DIRECTION"

# Stage 4: every figure and every page for this direction, in one call.
run report "$PYTHON" -m loco_report --direction "$DIRECTION"
