"""Render the report pages from ``knobs.csv`` and scored predictions.

    uv run python reports/loco_option_matrix/make_pages.py
    uv run python reports/loco_option_matrix/make_pages.py --page delta
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from loco_common.campaign import (
    PAGE_CAMPAIGNS,
    Campaign,
    campaign_by_slug,
)
from loco_common.case_names import (
    ALL_PAGES,
    DELTA_PAGE,
    LOCO_OPTICS_FITS,
    METHOD1_OPTION,
    METHOD1_PAGE,
    PAGE_BY_SLUG,
    PAGES,
    PER_MAGNET_PAGE,
    Page,
    case_heading,
    parse_case,
)
from loco_common.fit_mode import (
    add_fit_mode_argument,
    fit_mode_by_slug,
    result_is_valid,
)

logger = logging.getLogger(__name__)

#: Nominal integrated strengths, matching ``report_cases`` and ``plot_knobs``.
NOMINAL_K1L = 0.36705
NOMINAL_BEND_ANGLE = 0.19635

#: Knob suffix -> (column heading, unit label, scale from raw units).
FAMILY_UNITS = {
    ".dk1l": ("gradients", "% of nominal $k_1L$", 100 / NOMINAL_K1L),
    ".dk0l": ("bends", "% of nominal bend angle", 100 / NOMINAL_BEND_ANGLE),
    ".dy": ("offsets", "mm", 1e3),
    ".tilt": ("rolls", "mrad", 1e3),
}

def knob_statistics(path: Path, suffix: str) -> dict[str, float] | None:
    """One family's fitted magnitudes and |value| / sigma, per group as fitted."""
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    frame = frame[frame["knob"].str.endswith(suffix)]
    if frame.empty:
        return None
    sigma = frame["uncertainty"].abs()
    ratio = (frame["value"].abs() / sigma).replace([np.inf, -np.inf], np.nan).dropna()
    # Method 1 reports no covariance, so significance is empty rather than infinite.
    if ratio.empty:
        ratio = pd.Series([float("nan")])
    return {
        "knobs": float(frame["value"].round(12).nunique()),
        "magnets": float(len(frame)),
        "rms": float((frame["value"] ** 2).mean() ** 0.5),
        "max": float(frame["value"].abs().max()),
        "sigma": float("nan") if (sigma == 0).all() else float(sigma.median()),
        "median_significance": float(ratio.median()),
        "determined": (
            float("nan") if ratio.isna().all() else float((ratio > 1.0).sum())
        ),
    }


def _number(value: float, digits: int = 2) -> str:
    """A table cell that is a number, or an em dash where the fit reports none."""
    return "—" if math.isnan(value) else f"{value:.{digits}f}"


def knob_table(page: Page, matrix: Path) -> str:
    """One row per case and family: knob count, rms, max, sigma, significance."""
    families = [
        suffix for suffix in FAMILY_UNITS
        if any(
            (slug == METHOD1_OPTION or result_is_valid(matrix / slug))
            and knob_statistics(matrix / slug / "knobs.csv", suffix)
            for slug in page.cases
        )
    ]
    if not families:
        return "_No fitted knobs found for this page._"

    lines = [
        # \lvert/\rvert, not a bare pipe: a literal | breaks the Markdown table parser.
        "| case | family | knobs | rms | max | median $\\sigma$ | "
        "median $\\lvert v\\rvert/\\sigma$ | above 1 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for slug in page.cases:
        if slug != METHOD1_OPTION and not result_is_valid(matrix / slug):
            continue
        heading = page.label(slug)
        for suffix in families:
            statistics = knob_statistics(matrix / slug / "knobs.csv", suffix)
            if statistics is None:
                continue
            name, unit, scale = FAMILY_UNITS[suffix]
            lines.append(
                "| {case} | {family} | {knobs:.0f} of {magnets:.0f} | {rms:.2f} | "
                "{max:.2f} | {sigma} | {significance} | {determined} |".format(
                    case=heading,
                    # Escaped: an unescaped "[mm]" in a cell is a shortcut link
                    # reference to a definition that does not exist.
                    family=f"{name} \\[{unit}]",
                    knobs=statistics["knobs"],
                    magnets=statistics["magnets"],
                    rms=scale * statistics["rms"],
                    max=scale * statistics["max"],
                    sigma=_number(scale * statistics["sigma"]),
                    significance=_number(statistics["median_significance"]),
                    determined=(
                        "—" if math.isnan(statistics["determined"])
                        else f"{statistics['determined']:.0f} of {statistics['magnets']:.0f}"
                    ),
                )
            )
            heading = ""
    return "\n".join(lines)


def _figure(path: str, caption: str, prefix: str) -> str:
    return (
        "<figure markdown>\n"
        f"![{caption}]({prefix}/{path})\n"
        f"<figcaption>{caption}</figcaption>\n"
        "</figure>"
    )


def _prefix(figures: Path, page: Path) -> str:
    """Where ``figures`` sits from a page written at ``page`` (a file or a dir).

    Computed, never hardcoded: the same renderer writes into docs/method.md,
    docs/<direction>_tunes/reports/ and .../reports/multi/, three depths.
    """
    directory = page if page.suffix == "" else page.parent
    return os.path.relpath(figures, directory)


def _direction(args) -> str:
    """Which tune direction this run's campaigns belong to."""
    return "normal" if campaign_by_slug(args.campaign[0]).slug.startswith("normal") else "inverted"


def _scenario_figures(args) -> Path:
    """Where the direction's cross-campaign figures are.

    Not ``figures/<direction>``: ``normal`` and ``inverted`` are campaign slugs,
    and ``Campaign.figures_dir`` already owns those folders.
    """
    return args.figures / "scenarios" / _direction(args)


def _exists(figures: Path, page: Page, name: str) -> bool:
    return (figures / page.slug / f"{page.slug}_{name}.png").exists()


def _indent(text: str, spaces: int = 4) -> str:
    """Indent a block for a content tab, leaving blank lines blank."""
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else "" for line in text.split("\n"))


def _tabbed(blocks: dict[str, str]) -> str:
    """One content-tab group, ``{tab label: markdown}``, in the order given."""
    parts = []
    for label, body in blocks.items():
        parts += [f'=== "{label}"', "", _indent(body), ""]
    return "\n".join(parts)


def _case_figures(page: Page, campaign: Campaign, args, names: list[tuple[str, str]]) -> str:
    """Figure blocks that exist for this campaign, as one markdown chunk."""
    figures = args.fit_mode.figures_dir(campaign, args.figures)
    relative_root = _prefix(args.figures, args.output)
    mode_part = "multi/" if args.fit_mode.slug == "multi" else ""
    blocks = [
        _figure(
            f"{campaign.slug}/{mode_part}{page.slug}/{page.slug}_{name}.png",
            caption,
            prefix=relative_root,
        )
        for name, caption in names
        if _exists(figures, page, name)
    ]
    return "\n\n".join(blocks)


def missing_cases_note(page: Page, campaign: Campaign) -> str:
    """Which of the page's cases produced no fit here."""
    absent = [
        slug for slug in page.cases
        if not (CURRENT_FIT_MODE.results_root(campaign) / slug / "knobs.csv").exists()
        or (slug != METHOD1_OPTION and not result_is_valid(CURRENT_FIT_MODE.results_root(campaign) / slug))
    ]
    if not absent:
        return ""
    names = ", ".join(f"*{page.label(slug).lower()}*" for slug in absent)
    return f"No valid fit on this lattice for {names}: off-momentum closed twiss did not converge."


def machine_and_models_table(campaign: Campaign) -> str:
    """One configuration: measured values against both model lattices."""
    summary = _summary(campaign)
    if summary is None:
        return f"_No measured optics; run `scripts/measured_optics.py --campaign {campaign.slug}`._"
    measured = summary["measured"]
    matched = summary.get("matched_model")
    quads = summary["quad_settings"]
    beat, amplitude = summary["beta_beat"], summary.get("beta_beat_amplitude", {})

    def cells(*values: str) -> str:
        return "| " + " | ".join(values) + " |"

    rows = [
        cells("", "measured", "model, $k_1$ as sent", "model, matched to the tune"),
        "|---|---|---|---|",
        # Tune and Q' are plotted elsewhere; not repeated here as a table.
        cells(
            "QFO / QDE, MAD $k_1$",
            f"{quads['kbrqf']:.6f} / {quads['kbrqd']:.6f}, from LSA",
            "the same",
            f"{matched['quad_settings']['kbrqf']:.6f} / "
            f"{matched['quad_settings']['kbrqd']:.6f} "
            f"({_circuit_shift(summary)[0]:+.2f} % / {_circuit_shift(summary)[1]:+.2f} %)"
            if matched else "—",
        ),
    ]
    for source, table in (("phase", beat), ("amplitude", amplitude)):
        for plane in ("x", "y"):
            if plane not in table:
                continue
            rows.append(
                cells(
                    f"beta-beating from {source}, {plane}",
                    "—",
                    f"{100 * table[plane]['vs_loco_model']['rms']:.1f} % rms, "
                    f"{100 * table[plane]['vs_loco_model']['max']:.1f} % peak",
                    f"{100 * table[plane]['vs_matched_model']['rms']:.1f} % rms, "
                    f"{100 * table[plane]['vs_matched_model']['max']:.1f} % peak"
                    if "vs_matched_model" in table[plane] else "—",
                )
            )
    for name, folder in summary["folders"].items():
        drive = folder["drive"]
        rows.append(
            cells(
                f"AC-dipole drive, {name.replace('_', ' ')}",
                f"{drive['measured_qxd']:.6f} / {drive['measured_qyd']:.6f} "
                f"(set {drive['configured_qxd']:.4f} / {drive['configured_qyd']:.4f})",
                "—",
                "—",
            )
        )
    rows.append(
        cells(
            "measurement variation / fit error",
            f"tune {measured['natural_tune_spread'][0]:.1e} / "
            f"{measured['natural_tune_spread'][1]:.1e}, "
            f"$dq1/dq2$ fit $1\\sigma$ {measured['dq_dpt_error'][0]:.3f} / "
            f"{measured['dq_dpt_error'][1]:.3f}",
            "—",
            "—",
        )
    )
    return "\n".join(rows)


def _subtitle(page: Page, args) -> str:
    """The one line under a page title: which method, which orbit mode."""
    if page is METHOD1_PAGE:
        modes = "both planes as delta orbits"
        methods = "methods 1 and 2"
    else:
        modes = page.case_objects[0].planes_phrase
        methods = "method 2"
    method_link = os.path.relpath(args.method_page, args.output)
    return (
        f"PSB ring 3 · {methods} · {args.fit_mode.label.lower()} · "
        f"2026-08-21 corrector scans · {modes} · [method]({method_link})"
    )


def fit_scope(page: Page, mode) -> str:
    """State exactly which measured states entered this page's fits."""
    if page is METHOD1_PAGE:
        return "**Single momentum fit.** Nominal RF only."
    if mode.slug == "single":
        if page is PER_MAGNET_PAGE:
            return (
                "**Single momentum fit.** 12 correctors, 4 non-zero `dkick` values "
                "(±0.75, ±1.5), nominal RF (`dpt = 0`). Absolute options also fit the "
                "averaged static orbit. Non-zero-RF residuals are held-out validation."
            )
        return (
            "**Single momentum fit.** Nominal RF (`dpt = 0`) only: 12 correctors, "
            "4 non-zero `dkick` values (±0.75, ±1.5). "
            "Non-zero-RF residuals are held-out validation."
        )
    if page is PER_MAGNET_PAGE:
        return (
            "**Multi momentum fit.** 12 correctors, 4 non-zero `dkick` values "
            "(±0.75, ±1.5), at all measured RF offsets. Delta option: 4 dispersion "
            "targets. Absolute option: absolute correctors and orbits, starting "
            "from its nominal-momentum fit. All RF residuals are in-sample."
        )
    return (
        "**Multi momentum fit.** All measured RF offsets, 12 correctors, "
        "4 non-zero `dkick` values per momentum. "
        + (
            "Warm-started from the matching nominal-momentum absolute fit; "
            "prior centred on zero. "
            if page.planes
            else ""
        )
        + "All RF residuals are in-sample."
    )


def validate_fit_scope(page: Page, campaign: Campaign, mode) -> None:
    """Refuse to publish a result under the wrong momentum heading."""
    expected = list(mode.rf_offsets_for(campaign))
    for slug in page.cases:
        summary_path = mode.results_root(campaign) / slug / "summary.json"
        if not summary_path.exists() or slug == METHOD1_OPTION:
            continue
        summary = json.loads(summary_path.read_text())
        offsets = [float(value) for value in summary.get("rf_offsets", [])]
        if offsets != expected or bool(summary.get("batch_momenta")) != mode.batch_momenta:
            raise ValueError(
                f"{summary_path} is {offsets=}, batch={summary.get('batch_momenta')}; "
                f"cannot render it as {mode.slug} momentum"
            )
        case = parse_case(slug)
        if (
            mode.slug == "multi"
            and case.planes != "none"
            and not summary.get("initial_knobs")
        ):
            raise ValueError(f"{summary_path} is not a staged absolute-orbit fit")


# Set by main/render for the small helper whose public signature is used throughout
# this generator. Keeping the mode here avoids pretending it is a property of the
# machine campaign itself.
CURRENT_FIT_MODE = fit_mode_by_slug("single")


def method1_note(campaign: Campaign) -> str:
    """What Method 1's own solver stopped at, minimising the response matrix."""
    path = campaign.method1_dir / "summary.json"
    if not path.exists():
        return (
            "_No Method 1 fit on this lattice: run "
            f"`python -m method1_madng_da.run_method1 --campaign {campaign.slug}`._"
        )
    summary = json.loads(path.read_text())
    before, after = summary["residual_rms_before"], summary["residual_rms_after"]
    change = 100 * (after - before) / before if before else float("nan")
    return (
        f"Method 1 freed {summary['n_quadrupole_knobs']} cell-grouped quadrupole $dk_1L$ knobs against "
        f"{len(summary['correctors'])} correctors and stopped at "
        f"`{summary['status']}` after {summary['ncall']} calls. Weighted response "
        f"residual rms {before:.1f} → {after:.1f} ({change:+.0f} %)."
    )


def render(page: Page, args) -> str:
    """One results page: tables and figures, numbers only; definitions are on the method page."""
    campaigns = [campaign_by_slug(slug) for slug in args.campaign]
    global CURRENT_FIT_MODE
    CURRENT_FIT_MODE = args.fit_mode
    for campaign in campaigns:
        validate_fit_scope(page, campaign, args.fit_mode)
    labels = [campaign.label for campaign in campaigns]

    def tabs(builder) -> str:
        return _tabbed({label: builder(c) for label, c in zip(labels, campaigns, strict=True)})

    parts = [
        f"# {page.title} — {args.fit_mode.label.lower()}",
        "",
        _subtitle(page, args),
        "",
        fit_scope(page, args.fit_mode),
        "",
        "## Machine and start models",
        "",
        tabs(lambda c: "\n\n".join(
            filter(
                None,
                [
                    machine_and_models_table(c),
                    method1_note(c) if page is METHOD1_PAGE else "",
                    missing_cases_note(page, c),
                ],
            )
        )),
        "## Fitted knobs",
        "",
        tabs(lambda c: knob_table(page, args.fit_mode.results_root(c))),
        "### Gradients",
        "",
        tabs(
            lambda c: _case_figures(
                page, c, args,
                [
                    ("dk1l_by_s", "Fitted gradient error per magnet, one panel per case."),
                    ("dk1l_significance", "The same gradients as |value| / σ."),
                ],
            )
        ),
    ]

    for suffix, name in ((".dk0l", "Bends"), (".dy", "Quadrupole offsets")):
        key = f"{suffix.lstrip('.')}_by_s"
        if any(_exists(args.fit_mode.figures_dir(c, args.figures), page, key) for c in campaigns):
            parts += [
                f"### {name}", "",
                tabs(
                    lambda c, key=key, name=name: _case_figures(
                        page, c, args,
                        [(key, f"Fitted {name.lower()} per magnet, one panel per case.")],
                    )
                ),
            ]

    if any(_exists(args.fit_mode.figures_dir(c, args.figures), page, "tilt_by_s") for c in campaigns):
        parts += [
            "### Rolls", "",
            tabs(
                lambda c: _case_figures(
                    page, c, args,
                    [
                        ("tilt_by_s", "Fitted quadrupole roll per magnet, for the "
                                      "cases that free it."),
                        ("tilt_significance", "The rolls as |value| / σ."),
                    ],
                )
            ),
        ]

    if any(_exists(args.fit_mode.figures_dir(c, args.figures), page, "optics") for c in campaigns):
        # Four tabs here and only here: this is the one figure on the page whose
        # measured points are a difference against a model, so it exists twice
        # per configuration -- once against the lattice on the k1 sent to the
        # magnets, once against the same lattice matched to the measured tune.
        parts += [
            "## Fitted lattice", "",
            _tabbed(
                {
                    f"{campaign.label}, {word}": _case_figures(
                        page, campaign, args,
                        [(f"optics{suffix}",
                          "Beta-beating, phase error and dispersion along s, per "
                          "case, with the measured beta-beating at the BPMs "
                          f"taken against the model {word_long}.")],
                    )
                    for campaign in campaigns
                    for word, suffix, word_long in (
                        ("nominal", "", "on the $k_1$ sent to the magnets"),
                        ("matched", "_matched", "matched to the measured tune"),
                    )
                }
            ),
            "### Tunes", "",
            tabs(
                lambda c: _case_figures(
                    page, c, args,
                    [("case_tunes", "Where each fit put the tune, against the "
                                    "measured tune, with both model lattices for "
                                    "scale.")],
                )
            ),
            "### Chromaticity", "",
            tabs(
                lambda c: _case_figures(
                    page, c, args,
                    [
                        ("case_chromaticity", "$dq1$ / $dq2$ error against the "
                         "measurement, paired bars per case for the two `Dp/p` "
                         "calibrations (RF-derived chroma, hatched closed-orbit); "
                         "zero is measured and the band is each calibration's fit "
                         "$1\\sigma$. A case's own fit is one number -- only which "
                         "measurement it is judged against moves."),
                    ],
                )
            ),
        ]

    parts += [
        "## Residuals", "",
        tabs(
            lambda c: "\n\n".join(
                filter(
                    None,
                    [
                        _case_figures(
                            page, c, args,
                            [
                                ("scores", "Residual rms against each scored "
                                           "measurement, per case, as a percentage "
                                           "of the measured amplitude."),
                                ("residuals", "Residual rms per BPM, with the "
                                              "measurement's statistical bar and "
                                              "the 0.1 mm BPM zero-offset "
                                              "systematic."),
                            ],
                        ),
                    ]
                )
            )
        ),
        "---",
        "",
        "## Rerunning this page",
        "",
        tabs(lambda c: _reproducing(page, c, args.fit_mode)),
    ]
    return "\n".join(parts)


def _reproducing(page: Page, campaign: Campaign, mode) -> str:
    """The commands behind this page's tab, in the order they have to run."""
    joined = " \\\n    ".join
    cases = [slug for slug in page.cases if slug != METHOD1_OPTION]
    mode_arg = " --momentum-mode multi" if mode.slug == "multi" else ""
    lines = [
        "```bash",
        f"uv run python scripts/measured_optics.py --campaign {campaign.slug}",
    ]
    if METHOD1_OPTION in page.cases:
        lines += [
            f"uv run python -m method1_madng_da.run_method1 --campaign {campaign.slug} \\",
            "    --sequence-file models/model_qx0.165000_qy0.227500/psb3_saved.seq \\",
            "    --max-call 400",
        ]
    if cases:
        lines += [
            f"uv run python scripts/run_campaign_fits.py --campaign {campaign.slug}{mode_arg} --cases \\",
            f"    {joined(cases)}",
        ]
    lines += [
        f"uv run python scripts/predict_loco.py --campaign {campaign.slug}{mode_arg} --options \\",
        f"    {joined(page.cases)}",
        f"uv run python scripts/predict_loco.py --campaign {campaign.slug}{mode_arg} --merge",
        f"uv run python scripts/case_optics.py --campaign {campaign.slug}{mode_arg} --options \\",
        f"    {joined(page.cases)}",
        f"uv run python scripts/report_cases.py --campaign {campaign.slug}{mode_arg} --page {page.slug}",
        f"uv run python reports/loco_option_matrix/make_pages.py{mode_arg} --page {page.slug}",
        "```",
    ]
    return "\n".join(lines)


def _summary(campaign: Campaign) -> dict | None:
    path = campaign.optics_dir / "summary.json"
    return json.loads(path.read_text()) if path.exists() else None


def _machine_table(campaign: Campaign) -> str:
    """What the machine was measured to be, for one configuration."""
    summary = _summary(campaign)
    if summary is None:
        return (
            "_Not analysed: run "
            f"`uv run python scripts/measured_optics.py --campaign {campaign.slug}`._"
        )
    measured = summary["measured"]
    return "\n".join(
        [
            "| quantity | value | spread across the flat bottom |",
            "|---|---|---|",
            "| natural tune $Q_x$ / $Q_y$ | "
            f"{measured['natural_tunes'][0]:.5f} / {measured['natural_tunes'][1]:.5f} | "
            f"{measured['natural_tune_spread'][0]:.1e} / "
            f"{measured['natural_tune_spread'][1]:.1e} |",
            "| $dq1=dQ_x/dp_t$ / $dq2=dQ_y/dp_t$ | "
            f"{measured['dq_dpt'][0]:+.3f} / {measured['dq_dpt'][1]:+.3f} | "
            f"{measured['dq_dpt_error'][0]:.3f} / "
            f"{measured['dq_dpt_error'][1]:.3f} (fit $1\\sigma$) |",
            "| QFO / QDE circuit, MAD $k_1$ | "
            f"{summary['quad_settings']['kbrqf']:.10f} / "
            f"{summary['quad_settings']['kbrqd']:.10f} | sent to the magnets |",
        ]
    )


def _drive_table(campaign: Campaign) -> str:
    """What the AC dipole was driven at, per turn-by-turn folder."""
    summary = _summary(campaign)
    if summary is None:
        return "_Not analysed._"
    lines = [
        "| folder | measured $q_{xd}$ / $q_{yd}$ | set | spread | acquisitions |",
        "|---|---|---|---|---|",
    ]
    for name, folder in summary["folders"].items():
        drive = folder["drive"]
        lines.append(
            f"| `{name}` | {drive['measured_qxd']:.6f} / {drive['measured_qyd']:.6f} | "
            f"{drive['configured_qxd']:.4f} / {drive['configured_qyd']:.4f} | "
            f"{drive['spread_qxd']:.1e} / {drive['spread_qyd']:.1e} | {drive['files']} |"
        )
    reference = summary["folders"][summary["reference_folder"]]
    lines += [
        "",
        f"Optics from `{summary['reference_folder']}`. Preprocessing: "
        f"`{reference.get('preprocessing', 'unrecorded')}`"
        + (
            ". No AC-dipole-off blanks in this MD, so the dispersive-ripple and "
            "per-BPM interference removals did not run."
            if reference.get("blank_acquisitions") is None
            else f", blanks from `{reference['blank_acquisitions']}`."
        ),
    ]
    return "\n".join(lines)


#: The two model lattices every configuration is measured against, as
#: (summary key, tab word, figure file, how the circuits got there).
MODEL_VARIANTS = (
    (
        "loco_model",
        "nominal",
        "measured_optics.png",
        "stood up on the currents the machine ran at, read from LSA and applied "
        "unchanged",
    ),
    (
        "matched_model",
        "matched",
        "measured_optics_matched.png",
        "stood up on those same currents, then `kbrqf` and `kbrqd` moved until it "
        "sits on the measured tune",
    ),
)


def _model_comparison(campaign: Campaign, figures: Path, reference: str, prefix: str) -> str:
    """The measured optics against one model lattice, as figures."""
    summary = _summary(campaign)
    if summary is None:
        return "_Not analysed yet._"
    model = summary.get(reference)
    if model is None:
        return "_Not analysed yet._"
    measured = summary["measured"]
    matched = reference == "matched_model"
    _, _, figure_name, how = next(v for v in MODEL_VARIANTS if v[0] == reference)
    directory = campaign.figures_dir(figures)

    lines = [f"This tab's model is {how}.", ""]
    if matched:
        shift = _circuit_shift(summary)
        lines += [
            f"QFO / QDE move {shift[0]:+.2f} % / {shift[1]:+.2f} % in magnitude "
            f"to get there, to {model['quad_settings']['kbrqf']:.6f} / "
            f"{model['quad_settings']['kbrqd']:.6f}.",
            "",
        ]
    lines += [
        "Closed-orbit response scaling of this model's tune error, "
        "$\\sin(\\pi Q_\\text{machine}) / \\sin(\\pi Q_\\text{model})$: "
        + ", ".join(
            f"{plane} **{_amplification(measured['natural_tunes'][index], model['tunes'][index]):.2f}x**"
            for plane, index in (("x", 0), ("y", 1))
        )
        + ".",
        "",
    ]
    if (directory / figure_name).exists():
        lines += [
            _figure(
                f"{campaign.slug}/{figure_name}",
                "Measured beta against this model, with the beating below each "
                "plane; the other model is drawn underneath for scale.",
                prefix=prefix,
            ),
            "",
        ]

    advances = [
        (name, plane, folder[f"phase_advance_rms_{plane}"])
        for name, folder in summary["folders"].items()
        for plane in ("x", "y")
        if f"phase_advance_rms_{plane}" in folder
    ]
    if advances:
        lines += [
            "BPM-to-BPM phase advance against the matched model, rms in units of "
            "$2\\pi$: "
            + ", ".join(f"`{name}` {plane} {value:.4f}" for name, plane, value in advances)
            + ".",
            "",
        ]
    return "\n".join(lines)


def _circuit_shift(summary: dict) -> list[float]:
    """Percent shift of each main circuit to reach the measured tune, by magnitude."""
    matched = summary["matched_model"]["quad_settings"]
    machine = summary["quad_settings"]
    return [
        100 * (abs(matched[knob]) - abs(machine[knob])) / abs(machine[knob])
        for knob in ("kbrqf", "kbrqd")
    ]


def _amplification(measured: float, model: float) -> float:
    """``sin(pi Q_machine) / sin(pi Q_model)``."""
    modelled = abs(math.sin(math.pi * (model % 1.0)))
    if modelled == 0.0:
        return float("inf")
    return abs(math.sin(math.pi * (measured % 1.0))) / modelled


def render_optics_page(args) -> str:
    """The measured-optics results: two machine states, each against two models."""
    campaigns = [campaign_by_slug(slug) for slug in args.campaign]
    prefix = _prefix(args.figures, args.optics_page)
    scenario_figures = _scenario_figures(args)
    scenario_prefix = _prefix(scenario_figures, args.optics_page)
    variants = [
        (f"{campaign.label}, {word}", campaign, reference)
        for campaign in campaigns
        for reference, word, _, _ in MODEL_VARIANTS
    ]

    def tabs(builder) -> str:
        """One tab group over the four (configuration, model) pairs."""
        return _tabbed(
            {label: builder(campaign, reference) for label, campaign, reference in variants}
        )  # sections that ignore the model still repeat per model, keeping tab labels linked

    parts = [
        "# Measured optics",
        "",
        "PSB ring 3 · 2026-08-21 · AC-dipole turn-by-turn and the tune/chroma "
        f"scan · [method]({os.path.relpath(args.method_page, args.optics_page.parent)})",
        "",
        "!!! note \"What the beta error bars mean\"",
        "",
        "    Every bar on this page is omc3's propagated error added in "
        "quadrature to a bootstrap over the folder's AC-dipole kicks: the kicks "
        "are resampled with replacement and the optics stage rerun on each "
        "replica. omc3's bar alone comes from one pooled analysis and contains "
        "no repeat of the machine, so it misses the shot-to-shot spread "
        "entirely; on its own it is 3-5 times too small for the phase beta. The "
        "bootstrap in turn cannot see anything common to the whole folder -- "
        "the kick normalisation and BPM calibration the amplitude beta leans on "
        "-- which is why the two are added rather than one replacing the other.",
        "",
        "## The machine",
        "",
        tabs(lambda c, _: _machine_table(c)),
        "## AC-dipole drive",
        "",
        tabs(lambda c, _: _drive_table(c)),
    ]

    # Outside every tab group on purpose: none of these three depends on which
    # model tab is open, and both configurations are on each of them, so a tab
    # could only show half the figure and would show the same half four times.
    comparison = [
        _figure(name, caption, prefix=scenario_prefix)
        for name, caption in (
            ("comparison_tunes.png",
             "Each model's tune against the measured tune, every campaign on "
             "this page."),
            ("comparison_chromaticity.png",
             "$dq1$ / $dq2$ model error against measurement, every campaign on "
             "this page."),
            ("comparison_beta_beat.png",
             "Measured beta-beating along $s$ against each reference model, from "
             "phase beta (filled) and from amplitude beta (open); each curve's "
             "rms is in the legend."),
        )
        if (scenario_figures / name).exists()
    ]
    if comparison:
        parts += ["## Tune, chromaticity and beta-beating", "", *comparison, ""]

    parts += [
        "## Measured against the model",
        "",
        tabs(lambda c, reference: _model_comparison(c, args.figures, reference, prefix)),
    ]

    parts += [
        "---",
        "",
        "## Rerunning this page",
        "",
        "```bash",
        "uv run python scripts/measured_optics.py --campaign "
        + " ".join(c.slug for c in campaigns),
        "uv run python scripts/report_cases.py --campaign <slug>",
        "uv run python reports/loco_option_matrix/make_pages.py",
        "```",
        "",
    ]
    return "\n".join(parts)


def _benchmark_records(root: Path, campaigns) -> list[dict]:
    """Each configuration's benchmark record, for those that have one."""
    records = []
    for campaign in campaigns:
        path = root / f"{campaign.slug}.json"
        if path.exists():
            records.append(json.loads(path.read_text()))
    return records


def _benchmark_table(record: dict) -> str:
    """The two runs side by side: knobs, parallelism, own stopping point."""
    first, second = record["method1"], record["method2"]
    one, two = first["summary"], second["summary"]
    agreement = record["agreement"]
    # Free-knob counts come from the written knobs, not the summary field, which
    # double-counts cell-grouped magnets.
    rows = [
        "| | Method 1 | Method 2 |",
        "|---|---|---|",
        f"| free knobs | {agreement['distinct_method1']} cell-grouped "
        f"$\\Delta k_1 L$ over {one['n_output_knobs']} magnets | "
        f"{agreement['distinct_method2']} cell-grouped $\\Delta k_1 L$ over "
        f"{two['n_output_knobs']} magnets |",
        f"| what it fits | the measured response matrix | "
        f"{two['n_settings']} delta closed orbits |",
        f"| processes | 1 | {second['processes']} |",
        f"| wall clock | {first['wall_s']:.1f} s | {second['wall_s']:.1f} s |",
        f"| CPU, whole tree | {first['cpu_s']:.1f} s | {second['cpu_s']:.1f} s |",
        f"| peak RSS | {first['max_rss_mb']:.0f} MB | {second['max_rss_mb']:.0f} MB |",
        f"| stopped at | `{one['status']}` after {one['ncall']} calls | "
        f"its own convergence test |",
        f"| its own residual | weighted response rms "
        f"{one['residual_rms_before']:.1f} → {one['residual_rms_after']:.1f} | "
        "not comparable: a different objective |",
    ]
    return "\n".join(rows)


def _benchmark_sentences(record: dict) -> str:
    """The two answers against each other."""
    agreement = record["agreement"]
    first, second = record["method1"], record["method2"]
    speed = second["wall_s"] and first["wall_s"] / second["wall_s"]
    cpu = second["cpu_s"] and first["cpu_s"] / second["cpu_s"]
    return "\n\n".join(
        [
            f"The two fits correlate at **{agreement['correlation']:+.4f}** over "
            f"{agreement['magnets']} magnets "
            f"({agreement['distinct_method1']} distinct knobs each). Their gradients "
            f"differ by {agreement['rms_difference_pct']:.2f} % of nominal $k_1L$ rms, "
            f"{agreement['max_difference_pct']:.2f} % at the worst magnet, against "
            f"fitted magnitudes of {agreement['rms_method1_pct']:.2f} % and "
            f"{agreement['rms_method2_pct']:.2f} % rms.",
            f"Method 2 finishes **{speed:.1f}x** faster in wall clock and "
            f"**{cpu:.1f}x** in CPU, while holding "
            f"{second['processes']} MAD-NG workers to Method 1's one.",
        ]
    )


def _method1_stopping(records: list[dict]) -> str:
    """What Method 1 stopped at here, and the stopping rule."""
    stops = ", ".join(
        f"{record['label'].lower()} `{record['method1']['summary']['status']}` at "
        f"{record['method1']['summary']['ncall']} calls"
        for record in records
    )
    return (
        "Method 1 stops on **XTOL** (`--var-rtol 3e-3`: no knob moves by more than "
        "0.3 % of itself), not on `FMIN`/`FTOL`, since measured BPM bars keep all "
        "384 response cells infeasible by thousands of sigma. Here: "
        f"{stops}. Tightening to 1e-8 costs 4000–6000 extra calls and changes no "
        "gradient by more than 2.2e-4 % of nominal $k_1L$, against fitted "
        "magnitudes of about 3 %."
    )


def render_benchmark_page(args) -> str:
    """Both methods on the same data, run back to back: agreement and cost."""
    campaigns = [campaign_by_slug(slug) for slug in args.campaign]
    records = _benchmark_records(args.benchmark, campaigns)
    method_link = os.path.relpath(args.method_page, args.benchmark_page.parent)
    if not records:
        return "\n".join(
            [
                "# Method 1 against Method 2",
                "",
                "_Not measured: run `uv run python -m scripts.benchmark_methods "
                f"--campaign {' '.join(c.slug for c in campaigns)}`._",
                "",
            ]
        )

    parts = [
        "# Method 1 against Method 2",
        "",
        "PSB ring 3 · both methods, same 32 cell-grouped knobs, same delta "
        f"orbits · [method]({method_link})",
        "",
        "## The two runs",
        "",
        _tabbed({record["label"]: _benchmark_table(record) for record in records}),
        "## What each answer and each run cost",
        "",
        _tabbed({record["label"]: _benchmark_sentences(record) for record in records}),
    ]

    scenario_figures = _scenario_figures(args)
    figures = [
        _figure(name, caption, prefix=_prefix(scenario_figures, args.benchmark_page))
        for name, caption in (
            ("benchmark_speed.png",
             "Wall clock and whole-tree CPU for each method, every benchmarked "
             "campaign on this page."),
            ("benchmark_agreement.png",
             "Each magnet's fitted gradient, Method 1 against Method 2."),
        )
        if (scenario_figures / name).exists()
    ]
    if figures:
        parts += ["## Speed and agreement", "", *figures, ""]

    parts += [
        "Wall clock is one run on one machine, not a mean over repeats, and the "
        "CPU column is the whole process tree as the operating system reports "
        "it — for Method 2 that is one worker per corrector setting, started and "
        "terminated by the fitter.",
        "",
        _method1_stopping(records),
        "",
        "---",
        "",
        "## Rerunning this page",
        "",
        "```bash",
        "uv run python -m scripts.benchmark_methods --campaign "
        + " ".join(record["campaign"] for record in records),
        "uv run python scripts/analyse_cross_campaign.py --direction "
        + _direction(args),
        "uv run python scripts/plot_cross_campaign.py --direction " + _direction(args),
        "uv run python reports/loco_option_matrix/make_pages.py",
        "```",
        "",
    ]
    return "\n".join(parts)


def render_method_page(args) -> str:
    """What was done, in order, as statements."""
    campaigns = [campaign_by_slug(slug) for slug in args.campaign]
    summaries = {c.slug: _summary(c) for c in campaigns}
    report_prefix = os.path.relpath(args.output, args.method_page.parent)
    reproducing = os.path.relpath(args.reproducing_page, args.method_page.parent)

    rows = ["| | " + " | ".join(c.label for c in campaigns) + " |",
            "|---|" + "---|" * len(campaigns)]
    rows.append("| acquisitions | " + " | ".join(
        f"`{c.measurements_path.name}`" for c in campaigns) + " |")
    rows.append("| scan log | " + " | ".join(f"`{c.scan_log.name}`" for c in campaigns) + " |")
    rows.append("| corrector step, LSA `/K` | " + " | ".join(
        f"0, ±{c.delta_k:g}, ±{2 * c.delta_k:g}" for c in campaigns) + " |")
    rows.append("| QFO / QDE, MAD $k_1$ | " + " | ".join(
        f"{c.quad_settings['kbrqf']:.10f} / {c.quad_settings['kbrqd']:.10f}"
        for c in campaigns) + " |")
    rows.append("| trim circuits | " + " | ".join("all four at zero" for _ in campaigns) + " |")
    rows.append("| AC-dipole folders | " + " | ".join(
        ", ".join(f"`{name}`" for name in c.optics.acd_dirs) for c in campaigns) + " |")
    rows.append("| model tune, $k_1$ as sent | " + " | ".join(
        f"{summaries[c.slug]['loco_model']['tunes'][0]:.4f} / "
        f"{summaries[c.slug]['loco_model']['tunes'][1]:.4f}"
        if summaries[c.slug] else "—" for c in campaigns) + " |")
    rows.append("| model tune, matched | " + " | ".join(
        f"{summaries[c.slug]['matched_model']['tunes'][0]:.4f} / "
        f"{summaries[c.slug]['matched_model']['tunes'][1]:.4f}"
        if summaries[c.slug] and "matched_model" in summaries[c.slug] else "—"
        for c in campaigns) + " |")

    cases = ["| case | free families | knobs |", "|---|---|---|"]
    for case in PAGES[0].case_objects:
        cases.append(
            f"| {case.heading} | {case.families_phrase} | {case.lump_phrase} |"
        )

    pages = ["| page | planes keeping the closed orbit |", "|---|---|"]
    for page in PAGES:
        pages.append(f"| [{page.title}]({report_prefix}/{page.slug}.md) | "
                     f"{page.case_objects[0].planes_phrase} |")
    pages.append(
        f"| [{PER_MAGNET_PAGE.title}]({report_prefix}/{PER_MAGNET_PAGE.slug}.md) | "
        "one option from each of the three |"
    )
    pages.append(
        f"| [{METHOD1_PAGE.title}]({report_prefix}/{METHOD1_PAGE.slug}.md) | "
        "both planes as delta orbits |"
    )
    # One row per fitted lattice the scenarios are read against: the two pages
    # carry the same measurement and differ only in what the fit could move.
    for slug, _, fit_label in LOCO_OPTICS_FITS:
        stem = "scenario-comparison" + ("" if slug == LOCO_OPTICS_FITS[0][0] else f"-{slug}")
        pages.append(
            f"| [Scenario comparison, {fit_label}]({report_prefix}/{stem}.md) | "
            "delta orbits, error-injection scenarios against the baseline |"
        )

    return "\n".join(
        [
            "# Method",
            "",
            "PSB ring 3, flat bottom, kinetic energy 0.16 GeV. 16 BPMs per plane, "
            "48 ring quadrupoles, 12 orbit correctors (6 DHZ, 6 DVT).",
            "",
            "## Configurations",
            "",
            "The corrector scan was run twice on 2026-08-21, at two quadrupole "
            "powerings. The correctors were not changed between them.",
            "",
            *rows,
            "",
            "A third scan, `CO_measurements_inverted_tunes_double` / "
            "`scan_20260821T150756.jsonl`, repeats the inverted lattice with a "
            "single ±1.5e-4 step. It is fitted (`--campaign inverted_double`) and "
            "not shown on the pages.",
            "",
            "## Orbit measurement",
            "",
            "1. Each corrector is trimmed to each step in the table above, at five "
            "RF-steering offsets; one acquisition per setting.",
            "2. A closed orbit is the mean over turns and bunches; its bar is the "
            "standard error of that mean.",
            "3. One reference orbit — the untrimmed machine at nominal RF — is "
            "subtracted from every orbit in the scan.",
            "4. LSA `/K` is taken as the kick in rad; the six DHZ carry a sign "
            "inversion, the six DVT do not.",
            "",
            "## Tune and chromaticity",
            "",
            "Full XImeter tune/chroma export. Every measured `Dp/p` is converted "
            "to $p_t$ with the PSB accelerator class, then all ctimes are fitted "
            "together with one shared slope and a separate tune intercept per "
            "ctime. The plots show MAD-NG-native $dq1=dQ_x/dp_t$ and "
            "$dq2=dQ_y/dp_t$; their bars carry the common fit's $1\\sigma$ slope "
            "errors. The file's `Xi` summary is not used.",
            "",
            "## Optics measurement",
            "",
            "1. AC-dipole turn-by-turn, two drive settings per configuration, "
            "10 000 turns per acquisition, flat top from turn 2 000.",
            "2. The drive is re-measured per acquisition: ring-summed `|FFT|` peak "
            "within 0.006 of the set tune, refined by sub-bin projection "
            "maximisation on the loudest BPM; the folder value is the median.",
            "3. Preprocessing: demodulate, remove energy motion, remove "
            "interference, SSA clean per BPM (window 200, rank 4). The two "
            "removals need AC-dipole-off blanks; this MD took none, so they did "
            "not run.",
            "4. An omc3 model is built at the measured natural and driven tunes.",
            "5. Harpy over turns 2 500-9 500, then driven optics, then "
            "equation-compensated free optics.",
            "6. Beta is taken from phase and from amplitude, both reported.",
            "",
            "## Models",
            "",
            "One sequence, `models/model_qx0.165000_qy0.227500/psb3_saved.seq`, "
            "twissed in MAD-NG (integrator method 6, DA/normal-form chromaticity), correctors at "
            "their scan settings. Two lattices per configuration:",
            "",
            "- **$k_1$ as sent** — `kbrqf`/`kbrqd` at the LSA currents above, the "
            "four trims at zero, no matching. The fits start here.",
            "- **matched** — the same, then `kbrqf`/`kbrqd` matched to the measured "
            "natural tune (`MAD.match`, `fmin = 1e-8`).",
            "",
            "## Fits",
            "",
            "**Method 2**, on every page but one: delta closed orbits, "
            "Levenberg-Marquardt Gauss-Newton "
            "(`aba_optimiser.ClosedTwissFitter`), one MAD-NG worker per corrector "
            "setting, isotropic Tikhonov prior at strength 1e-4. The reference "
            "orbit and its Jacobian are recomputed every iteration.",
            "",
            "The **single-momentum** result pages fit nominal RF only: 48 "
            "non-zero corrector settings, plus one averaged static-orbit target "
            "when either plane is absolute. Their non-zero-RF scores are held-out "
            "validation.",
            "",
            "The **multi-momentum** result pages fit all five RF offsets "
            "(`-2, -1, 0, +1, +2 mm`): 240 non-zero corrector settings plus four "
            "dispersion targets for a pure-delta fit, or five averaged untrimmed "
            "orbit targets when a plane is absolute. The 244/245 targets are "
            "batched into 50 MAD-NG workers without changing the objective. "
            "Absolute-orbit fits first solve the matching nominal-momentum case, "
            "then use that lattice to initialise the joint five-momentum solve; "
            "the Tikhonov prior remains centred on zero error knobs.",
            "",
            "**Method 1**, on its own page: the measured response matrix is the "
            "target and a first-order MAD-NG parametric twiss the model. Every "
            "matrix cell is one weighted `MAD.match` equality, fitted directly "
            "with the 32 native cell-grouped $\\Delta k_1 L$ knobs used by "
            "grouped Method 2. It stops on `XTOL`, when no knob moves by more "
            "than 0.3 % of itself; the objective tests are only made at a "
            "feasible point, which measured data never is.",
            "",
            *pages,
            "",
            "Two cases per Method-2 page:",
            "",
            *cases,
            "",
            "Lumping to 32 ties the two QFO flanking a QDE and leaves the QDE "
            "free, by magnet name. Rolls are parametrised as the gradients are. "
            "Neither arm of a page frees a per-magnet knob: rolls per magnet are "
            "not run at all, and gradients per magnet — 48 against 16 BPMs per "
            f"plane — are on the [one knob per magnet]({report_prefix}/per-magnet.md) page "
            "rather than beside the lumped fits.",
            "",
            "## Scoring",
            "",
            "Every fit is stood up again and asked the same six questions; the "
            "number reported is residual rms as a percentage of the measured "
            "amplitude:",
            "",
            "| target | what is compared |",
            "|---|---|",
            "| delta x, delta y | corrector delta orbits |",
            "| static x, static y | the machine's closed orbit at each RF setting |",
            "| disp x, disp y | dispersion from the RF-offset orbits |",
            "",
            "Absolute planes are weighted with a 1e-4 m BPM zero-offset floor.",
            "",
            "## Figures",
            "",
            "| figure | contents |",
            "|---|---|",
            "| gradients, bends, offsets, rolls by `s` | fitted value per magnet, "
            "one panel per case, fit's own error bars |",
            "| significance | fitted value over its own error bar per magnet, "
            "log scale |",
            "| lattice | beta-beating, phase error and dispersion along `s` "
            "against the start model, per case, with measured beta-beating and "
            "measured dispersion at the BPMs; dispersion is the slope of the five "
            "untrimmed closed orbits versus reconstructed `pt` |",
            "| case tunes | each fit's tune against the measured tune, one bar "
            "per case, one panel per plane |",
            "| residuals | residual rms per BPM, with the statistical bar and the "
            "0.1 mm systematic |",
            "| scores | residual rms against each scored measurement, one bar per "
            "case |",
            "| tune, chromaticity | measured against both model lattices, "
            "one bar per model |",
            "| beta-beating | measured beta-beating along $s$ against each "
            "reference model, from phase beta and from amplitude beta |",
            "| measured optics | measured beta and beta-beating against one model, "
            "one figure per model |",
            "",
            f"[Reproducing any of it]({reproducing})",
            "",
        ]
    )


def _scenario_diff_figures(mode_slug: str, case_slug: str, figures: Path, prefix: str) -> str:
    """Every knob-family diff figure for one (momentum mode, case) tab.

    ``figures`` is already the direction-specific scenario folder (see
    :func:`render_scenario_comparison_page`), matching where
    ``scripts/plot_cross_campaign.py`` wrote it.
    """
    directory = figures / "scenario-comparison" / mode_slug / case_slug
    blocks = [
        _figure(
            f"scenario-comparison/{mode_slug}/{case_slug}/knob_diffs_{suffix}.png",
            f"Fitted {name} error against the unperturbed baseline, per magnet, "
            "one bar group per scenario.",
            prefix=prefix,
        )
        for suffix, name in (
            ("dk1l", "gradient"), ("dk0l", "bend"), ("dy", "offset"), ("tilt", "roll"),
        )
        if (directory / f"knob_diffs_{suffix}.png").exists()
    ]
    return "\n\n".join(blocks) if blocks else "_No scenario fit here yet._"


def _scenario_page_path(args, fit_slug: str) -> Path:
    """Where one fit's scenario-comparison page goes.

    The first fit keeps ``--scenario-page`` as given, so every existing link to
    it still resolves; the second gets the same name with its slug appended.
    """
    if fit_slug == LOCO_OPTICS_FITS[0][0]:
        return args.scenario_page
    return args.scenario_page.with_name(
        f"{args.scenario_page.stem}-{fit_slug}{args.scenario_page.suffix}"
    )


def render_scenario_comparison_page(args, fit=LOCO_OPTICS_FITS[0]) -> str:
    """Knob errors and optics of the error-injection scenarios against the
    unperturbed baseline: absolute tunes/chromaticities, beta/phase/dispersion
    beating against the nominal model, then per-family knob diffs, tabbed by
    momentum mode and by whether rolls were fitted.

    One page per entry of :data:`~scripts.report_cases.LOCO_OPTICS_FITS`. The
    measured half of every perturbation figure is the same on both -- it is the
    machine -- and only the fitted half differs, which is the comparison: what
    a fit allowed to roll a quadrupole reproduces that one denied rolls cannot,
    the coupling tab most of all."""
    # The campaigns this run was given, not the direction's full set: a refresh
    # can leave one out (normal_sexts_on has no acquisitions), and the prose
    # must not promise a scenario whose figures are not on the page.
    baseline, *scenarios = [campaign_by_slug(slug) for slug in args.campaign]
    names = ", ".join(c.label for c in scenarios)
    fit_slug, _, fit_label = fit
    page = _scenario_page_path(args, fit_slug)
    figures = _scenario_figures(args)
    # The perturbation figures are per fit and live in their own folder; every
    # other figure on the page is the measurement and is shared.
    fit_figures = figures / fit_slug
    prefix = _prefix(figures, page)
    fit_prefix = _prefix(fit_figures, page)
    method_link = os.path.relpath(args.method_page, page.parent)
    parts = [
        f"# Scenario comparison — fitted with {fit_label}",
        "",
        f"PSB ring 3 · {baseline.label} baseline against {names} · "
        f"[method]({method_link})",
        "",
        "## Tune and chromaticity, absolute",
        "",
    ]
    if (figures / "scenario_tunes_chromas.png").exists():
        parts += [
            _figure(
                "scenario_tunes_chromas.png",
                "Measured tune and chromaticity, absolute, one group of bars "
                "per scenario.",
                prefix=prefix,
            ),
            "",
        ]
    parts += ["## Effect of the perturbations", ""]
    perturbation = {
        "beta": (
            "Beta from phase",
            "Relative, $\\Delta\\beta/\\beta$, from the measured phase.",
        ),
        "beta_amp": (
            "Beta from amplitude",
            "The same quantity from the measured amplitude, which needs the BPM "
            "gains -- its own tab rather than standing in for the phase one.",
        ),
        "phase": ("Phase advance", "Absolute, BPM to BPM, in units of $2\\pi$."),
        "dispersion": ("Dispersion", "Absolute, $\\Delta D$ in metres."),
        "coupling": (
            "Coupling",
            "Absolute, $\\Delta|f_{1001}|$ and $\\Delta|f_{1010}|$ from omc3's "
            "RDT amplitudes -- the rows are the two resonances, not the two "
            "planes.",
        ),
    }
    drawn = {
        stem: value for stem, value in perturbation.items()
        if (fit_figures / f"scenario_perturbation_{stem}.png").exists()
    }
    if drawn:
        parts += [
            _figure(
                "scenario_perturbation_tunes.png",
                "Measured tune and chromaticity, each scenario minus the "
                "unperturbed baseline.",
                prefix=prefix,
            ),
            "",
            _tabbed({
                heading: _figure(
                    f"scenario_perturbation_{stem}.png",
                    f"{note} Each scenario minus the unperturbed baseline "
                    "at the same BPM, along $s$. The left column is "
                    "measurement against measurement, no model involved; "
                    "the right is the same difference taken between the "
                    f"LOCO-fitted lattices, multi-momentum, {fit_label}, "
                    "lumped to 32 knobs by cell. Measured points carry the "
                    "two campaigns' bars added in quadrature, and each "
                    "curve's rms is in the legend.",
                    prefix=fit_prefix,
                )
                for stem, (heading, note) in drawn.items()
            }),
            "",
        ]
    else:
        parts += ["_Not analysed yet._", ""]
    parts += ["## Fitted knob errors against the baseline", ""]
    tabs = {
        f"{mode.label}, {case_heading(case_slug).lower()}": _scenario_diff_figures(
            mode.slug, case_slug, figures, prefix,
        )
        for mode in (fit_mode_by_slug("single"), fit_mode_by_slug("multi"))
        for case_slug in DELTA_PAGE.cases
    }
    parts += [_tabbed(tabs), ""]

    benchmark_prefix = os.path.relpath(args.benchmark_page, page.parent)
    parts += [
        "## Method 1 against Method 2",
        "",
        f"How the two fitting methods themselves compare on this baseline is on "
        f"its own page: [Method 1 against Method 2]({benchmark_prefix}).",
        "",
    ]
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures", type=Path, default=Path("docs/assets/figures"))
    add_fit_mode_argument(parser)
    parser.add_argument(
        "--campaign", nargs="+", default=[c.slug for c in PAGE_CAMPAIGNS],
        help="Machine configurations to tab between, in tab order.",
    )
    parser.add_argument("--output", type=Path, default=Path("docs/inverted_tunes/reports"))
    parser.add_argument("--page", nargs="+", default=None, choices=sorted(PAGE_BY_SLUG))
    parser.add_argument(
        "--optics-page", type=Path,
        default=Path("docs/inverted_tunes/studies/measured-optics.md"),
        help="Where the measured-optics study is written; skipped when --page is given.",
    )
    parser.add_argument(
        "--method-page", type=Path, default=Path("docs/method.md"),
        help="Where the method page is written, and what every page's [method] "
             "link points at. Honoured in every mode: only the writing is "
             "skipped outside the single-momentum default run.",
    )
    parser.add_argument(
        "--reproducing-page", type=Path,
        default=Path("docs/reference/reproducing.md"),
        help="What the method page's 'Reproducing any of it' link points at.",
    )
    parser.add_argument(
        "--benchmark", type=Path, default=Path("results/benchmark"),
        help="Where scripts/benchmark_methods.py wrote its records.",
    )
    parser.add_argument(
        "--benchmark-page", type=Path,
        default=Path("docs/inverted_tunes/reports/benchmark.md"),
        help="Where the method-against-method benchmark is written.",
    )
    parser.add_argument(
        "--scenario-page", type=Path,
        default=Path("docs/inverted_tunes/reports/scenario-comparison.md"),
        help="Where the scenario comparison is written; skipped when --page is given.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    args.fit_mode = fit_mode_by_slug(args.momentum_mode)
    if args.output == Path("docs/inverted_tunes/reports") and args.fit_mode.slug == "multi":
        args.output = args.output / "multi"
    args.output.mkdir(parents=True, exist_ok=True)
    default_pages = (
        ALL_PAGES if args.fit_mode.slug == "single" else (*PAGES, PER_MAGNET_PAGE)
    )
    pages = [PAGE_BY_SLUG[slug] for slug in args.page] if args.page else list(default_pages)
    for page in pages:
        destination = args.output / f"{page.slug}.md"
        destination.write_text(render(page, args))
        logger.info("wrote %s", destination)

    if args.page is None and args.fit_mode.slug == "single":
        args.optics_page.parent.mkdir(parents=True, exist_ok=True)
        args.optics_page.write_text(render_optics_page(args))
        logger.info("wrote %s", args.optics_page)
        args.method_page.parent.mkdir(parents=True, exist_ok=True)
        args.method_page.write_text(render_method_page(args))
        logger.info("wrote %s", args.method_page)
        args.benchmark_page.parent.mkdir(parents=True, exist_ok=True)
        args.benchmark_page.write_text(render_benchmark_page(args))
        logger.info("wrote %s", args.benchmark_page)
        for fit in LOCO_OPTICS_FITS:
            destination = _scenario_page_path(args, fit[0])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(render_scenario_comparison_page(args, fit))
            logger.info("wrote %s", destination)


if __name__ == "__main__":
    main()
