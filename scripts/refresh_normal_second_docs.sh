#!/bin/sh
# Full LOCO report pipeline for every campaign the normal-tunes report pages
# tab between (loco_common.campaign.NORMAL_PAGE_CAMPAIGNS). normal_sexts_on was
# taken on the 30th rather than the 29th and is now complete, so unlike earlier
# revisions of this script nothing is excluded. Each stage's stdout/stderr
# goes to its own file under .logs/, named with the $TAG prefix so an
# inverted-tunes refresh cannot overwrite a normal one. Independent
# (campaign, mode) work runs in parallel within a stage -- see the comment above
# each loop for why that stage in particular is safe to parallelise. Mirrors
# refresh_inverted_second_docs.sh but writes under docs/normal_tunes/ with its
# own method/benchmark/scenario pages, since those hardcode report links for
# whichever campaign set is passed in.
set -eu
cd "$(dirname "$0")/.."

mkdir -p .logs

TAG=normal
DIRECTION=normal

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

CAMPAIGNS="normal_second normal_qde14_err normal_qde14_qde3_err normal_sexts_on"

# Every page this script writes lives under docs/normal_tunes/, so its method
# page and its [method] links have to as well -- the default docs/method.md is
# the inverted-tunes one.
PAGE_ARGS="--optics-page docs/normal_tunes/studies/measured-optics.md \
    --method-page docs/normal_tunes/method.md \
    --benchmark-page docs/normal_tunes/reports/benchmark.md \
    --scenario-page docs/normal_tunes/reports/scenario-comparison.md"

# Clear cached artifacts so every stage is forced to regenerate from scratch.
# Comment this block out to reuse whatever is already on disk.
for campaign in $CAMPAIGNS; do
    rm -f "data/${campaign}_scan_points.parquet" "data/${campaign}_scan_orbits.parquet" "data/${campaign}_orbits_rfp0.parquet"
    rm -rf "results/optics/${campaign}"
    rm -rf "docs/assets/figures/${campaign}"
    for mode in single multi; do
        suffix="_${mode}"
        [ "$mode" = single ] && suffix=""
        rm -rf "results/matrix_${campaign}${suffix}"
    done
done
rm -rf "docs/assets/figures/scenarios/${DIRECTION}" "results/cross_campaign/${DIRECTION}"

# Stage 1: measured optics, one independent process per campaign -- each
# writes only under results/optics/<campaign>/, so these can run at once.
pids=""
for campaign in $CAMPAIGNS; do
    run "measured_optics_${campaign}" python scripts/measured_optics.py --campaign "$campaign" &
    pids="$pids $!"
done
wait_all measured_optics

# Stage 2: the fit pipeline, one independent chain per (campaign, mode) --
# each chain writes only under results/matrix_<campaign>[_multi]/, so the
# chains can run at once; each stage inside a chain still waits on the last.
# predict_loco writes scoreboard.shard1of1.csv and only --merge turns that into
# the scoreboard.csv that report_cases' scores figure reads, so the merge is
# part of the chain, not optional.
pids=""
for campaign in $CAMPAIGNS; do
    for mode in single multi; do
        (
            run "run_campaign_fits_${campaign}_${mode}" python scripts/run_campaign_fits.py --campaign "$campaign" --momentum-mode "$mode"
            run "predict_loco_${campaign}_${mode}"      python scripts/predict_loco.py --campaign "$campaign" --momentum-mode "$mode"
            run "predict_merge_${campaign}_${mode}"     python scripts/predict_loco.py --campaign "$campaign" --momentum-mode "$mode" --merge
            run "case_optics_${campaign}_${mode}"       python scripts/case_optics.py --campaign "$campaign" --momentum-mode "$mode"
        ) &
        pids="$pids $!"
    done
done
wait_all run_campaign_fits/predict_loco/case_optics

# Stage 3: Method 1, one process per campaign. Its fit lives in
# results/matrix_<campaign>/method1, which the clear block above removed, so
# without this the Method 1 page renders as "no fit on this lattice". Single
# momentum only -- Method 1 fits the nominal-RF response matrix.
pids=""
for campaign in $CAMPAIGNS; do
    run "run_method1_${campaign}" python -m method1_madng_da.run_method1 \
        --campaign "$campaign" \
        --sequence-file models/model_qx0.165000_qy0.227500/psb3_saved.seq &
    pids="$pids $!"
done
wait_all run_method1

# Stage 4: the method-against-method benchmark. It runs both methods itself
# into results/benchmark/<campaign>/ and writes the record the benchmark page
# and its two figures are drawn from. Serial: the point of the record is a
# wall-clock and CPU comparison, which parallel campaigns would corrupt.
for campaign in $CAMPAIGNS; do
    run "benchmark_${campaign}" python -m scripts.benchmark_methods --campaign "$campaign"
done

# Stage 5: report_cases.py only draws each (campaign, mode)'s own figures --
# the cross-campaign comparison figures are stage 6 -- so every call here is
# independent and can run at once.
pids=""
for campaign in $CAMPAIGNS; do
    for mode in single multi; do
        run "report_cases_${campaign}_${mode}" python scripts/report_cases.py --campaign "$campaign" --momentum-mode "$mode" &
        pids="$pids $!"
    done
done
wait_all report_cases

# Stage 6: combine this direction's cross-campaign comparison once (analysis),
# then draw it once (plotting). --direction keeps the run off the other
# direction's results, which this script has not refreshed.
run analyse_cross_campaign python scripts/analyse_cross_campaign.py --direction "$DIRECTION"
run plot_cross_campaign python scripts/plot_cross_campaign.py --direction "$DIRECTION"

# shellcheck disable=SC2086  # PAGE_ARGS and CAMPAIGNS are word lists on purpose
run make_pages python reports/loco_option_matrix/make_pages.py \
    --campaign $CAMPAIGNS $PAGE_ARGS \
    --output docs/normal_tunes/reports

# shellcheck disable=SC2086
run make_pages_multi python reports/loco_option_matrix/make_pages.py \
    --momentum-mode multi \
    --campaign $CAMPAIGNS $PAGE_ARGS \
    --output docs/normal_tunes/reports/multi
