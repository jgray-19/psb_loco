"""The pages that are not per-case: measured optics, benchmark, scenarios."""

from __future__ import annotations

from pathlib import Path

from loco_common.campaign import Campaign
from loco_report import render
from loco_report.data import Results, benchmark, read_json
from loco_report.style import FAMILIES

#: The two reference lattices, as (summary key, file suffix, tab word, how).
MODELS = (
    ("loco_model", "", "nominal",
     "stood up on the currents the machine ran at, read from LSA and applied "
     "unchanged"),
    ("matched_model", "_matched", "matched",
     "those same currents, then `kbrqf` and `kbrqd` moved until the model sits "
     "on the measured tune"),
)

#: Figures the measured-optics page shows per (configuration, model) tab.
OPTICS_FIGURES = (
    ("measured_beta", "measured beta against the model",
     "Measured beta from phase and from amplitude, with the reference lattice."),
    ("measured_beat", "measured beta-beating against the model",
     "Measured beta-beating against the reference lattice, both planes."),
    ("measured_coupling", "measured coupling amplitudes",
     "Measured |f1001| and |f1010| against the reference lattice."),
)

#: Cross-campaign figures, drawn once for a whole direction.
COMPARISON_FIGURES = (
    ("comparison_tunes.png", "model tune against measurement",
     "Each model's tune against the measured tune, every configuration."),
    ("comparison_chromaticity.png", "model chromaticity against measurement",
     "Model Q'H / Q'V error against the measurement, every configuration."),
    ("comparison_beta_beat.png", "measured beta-beating against each model",
     "Measured beta-beating along s against each reference model, from phase "
     "(filled) and from amplitude (open)."),
)


def qprime(summary: dict) -> tuple[list[float], list[float]]:
    """Measured Q'H / Q'V and its bar, from the summary's own conversion."""
    measured = summary["measured"]
    model = summary["loco_model"]
    ratios = [q / dq for q, dq in zip(model["qprime"], model["dq_dpt"]) if dq]
    beta = sum(ratios) / len(ratios) if ratios else 1.0
    return (
        [beta * value for value in measured["dq_dpt"]],
        [beta * value for value in measured["dq_dpt_error"]],
    )


def machine_table(campaign: Campaign) -> str:
    """What the machine was measured to be, for one configuration."""
    summary = read_json(campaign.optics_dir / "summary.json")
    if not summary:
        return f"_Not analysed: run `scripts/measured_optics.py --campaign {campaign.slug}`._"
    measured = summary["measured"]
    values, error = qprime(summary)
    return render.table(
        ["quantity", "value", "spread across the flat bottom"],
        [
            ["natural tune $Q_x$ / $Q_y$",
             f"{measured['natural_tunes'][0]:.5f} / {measured['natural_tunes'][1]:.5f}",
             f"{measured['natural_tune_spread'][0]:.1e} / "
             f"{measured['natural_tune_spread'][1]:.1e}"],
            ["$Q'_H$ / $Q'_V$",
             f"{values[0]:+.3f} / {values[1]:+.3f}",
             f"{error[0]:.3f} / {error[1]:.3f} (fit $1\\sigma$)"],
            ["QFO / QDE circuit, MAD $k_1$",
             f"{summary['quad_settings']['kbrqf']:.10f} / "
             f"{summary['quad_settings']['kbrqd']:.10f}",
             "sent to the magnets"],
        ],
    )


def drive_table(campaign: Campaign) -> str:
    """What the AC dipole was driven at, per turn-by-turn folder."""
    summary = read_json(campaign.optics_dir / "summary.json")
    if not summary:
        return "_Not analysed._"
    rows = []
    for name, folder in summary["folders"].items():
        drive = folder["drive"]
        rows.append([
            f"`{name}`",
            f"{drive['measured_qxd']:.6f} / {drive['measured_qyd']:.6f}",
            f"{drive['configured_qxd']:.4f} / {drive['configured_qyd']:.4f}",
            f"{drive['spread_qxd']:.1e} / {drive['spread_qyd']:.1e}",
            str(drive["files"]),
        ])
    table = render.table(
        ["folder", "measured $q_{xd}$ / $q_{yd}$", "set", "spread", "acquisitions"],
        rows,
    )
    return f"{table}\n\nOptics from `{summary['reference_folder']}`."


def render_optics_page(campaigns, figure_root: Path, scenario_root: Path,
                       destination: Path) -> str:
    """Measured optics: each configuration against each reference lattice."""
    prefix = render.prefix(figure_root, destination)
    scenario_prefix = render.prefix(scenario_root, destination)
    variants = [
        (f"{campaign.label}, {word}", campaign, key, how)
        for campaign in campaigns for key, _, word, how in MODELS
    ]
    suffix = {key: file_suffix for key, file_suffix, _, _ in MODELS}

    def tabs(builder) -> str:
        return render.tabbed({
            label: builder(campaign, key, how) for label, campaign, key, how in variants
        })

    blocks = [
        render.heading("The machine"),
        tabs(lambda campaign, key, how: machine_table(campaign)),
        render.heading("AC-dipole drive"),
        tabs(lambda campaign, key, how: drive_table(campaign)),
    ]

    comparison = [
        render.figure(name, alt, caption, scenario_prefix)
        for name, alt, caption in COMPARISON_FIGURES
        if (scenario_root / name).exists()
    ]
    if comparison:
        blocks += [render.heading("Across configurations"), "\n\n".join(comparison)]

    def model_figures(campaign: Campaign, key: str, how: str) -> str:
        directory = campaign.figures_dir(figure_root)
        found = [
            render.figure(
                str((directory / f"{stem}{suffix[key]}.png").relative_to(figure_root)),
                alt, caption, prefix,
            )
            for stem, alt, caption in OPTICS_FIGURES
            if (directory / f"{stem}{suffix[key]}.png").exists()
        ]
        return "\n\n".join([f"This tab's model is {how}.", *found])

    blocks += [render.heading("Measured against the model"), tabs(model_figures)]
    statement = (
        "PSB ring 3 · AC-dipole turn-by-turn and the tune/chroma scan · "
        f"{len(campaigns)} machine configurations, each against two reference "
        "lattices. Every beta bar is omc3's propagated error added in quadrature "
        "to a bootstrap over the folder's AC-dipole kicks."
    )
    return render.page("Measured optics", statement, blocks)


BENCHMARK_FIGURES = (
    ("benchmark_speed.png", "wall clock and CPU per method",
     "Wall clock and whole-tree CPU for each method, every benchmarked "
     "configuration."),
    ("benchmark_agreement.png", "Method 1 against Method 2 per magnet",
     "Each magnet's fitted gradient, Method 1 against Method 2."),
)


def benchmark_table(record: dict) -> str:
    """One configuration's two runs, side by side."""
    rows = []
    for key, name in (("method1", "Method 1"), ("method2", "Method 2")):
        run = record.get(key)
        if not run:
            continue
        rows.append([
            name,
            f"{run.get('wall_s', float('nan')):.1f}",
            f"{run.get('cpu_s', float('nan')):.1f}",
            f"{run.get('max_rss_mb', float('nan')):.0f}",
            str(run.get("processes", "—")),
        ])
    return render.table(
        ["method", "wall [s]", "CPU [s]", "peak RSS [MB]", "processes"], rows
    )


def agreement_table(records: list[dict]) -> str:
    """How closely the two methods' gradients agree, per configuration."""
    rows = []
    for record in records:
        agreement = record.get("agreement")
        if not agreement:
            continue
        rows.append([
            record["campaign_object"].label,
            str(agreement["magnets"]),
            f"{agreement['correlation']:+.4f}",
            f"{agreement['rms_difference_pct']:.2f}",
            f"{agreement['max_difference_pct']:.2f}",
        ])
    return render.table(
        ["configuration", "magnets", "correlation", "rms difference [%]",
         "max difference [%]"],
        rows,
    )


def render_benchmark_page(campaigns, benchmark_root: Path, scenario_root: Path,
                          destination: Path) -> str:
    """Both methods on the same data, run back to back."""
    records = benchmark(benchmark_root, campaigns)
    if not records:
        return render.page(
            "Method 1 against Method 2",
            "_Not measured: run `python -m scripts.benchmark_methods --campaign "
            + " ".join(campaign.slug for campaign in campaigns) + "`._",
            [],
        )
    prefix = render.prefix(scenario_root, destination)
    blocks = [
        render.heading("The two runs"),
        render.tabbed({
            record["campaign_object"].label: benchmark_table(record) for record in records
        }),
    ]
    blocks += [render.heading("Agreement"), agreement_table(records)]
    figures = [
        render.figure(name, alt, caption, prefix)
        for name, alt, caption in BENCHMARK_FIGURES
        if (scenario_root / name).exists()
    ]
    if figures:
        blocks += [render.heading("Speed and agreement"), "\n\n".join(figures)]
    statement = (
        "PSB ring 3 · both methods, same 32 cell-grouped knobs, same delta "
        "orbits. Wall clock is one run on one machine, not a mean over repeats; "
        "the CPU column is the whole process tree, which for Method 2 is one "
        "worker per corrector setting."
    )
    return render.page("Method 1 against Method 2", statement, blocks)


#: The two fits the scenario perturbation figures are drawn from.
SCENARIO_FITS = (
    ("gradients", "none__k1__bpm-family", "gradients only"),
    ("rolls", "none__k1+t__bpm-family", "gradients and rolls"),
)

#: What each scenario figure shows, per fit.
PERTURBATION_FIGURES = (
    ("scenario_perturbation_beta", "beta-beating difference from baseline",
     "Relative beta-beating from the measured phase, each scenario minus the "
     "unperturbed baseline at the same BPM."),
    ("scenario_perturbation_beta_amp", "amplitude beta difference from baseline",
     "The same quantity from the measured amplitude, which needs the BPM gains."),
    ("scenario_perturbation_phase", "phase advance difference from baseline",
     "Phase advance, BPM to BPM, each scenario minus the baseline."),
    ("scenario_perturbation_dispersion", "dispersion difference from baseline",
     "Dispersion, each scenario minus the baseline, in metres."),
    ("scenario_perturbation_coupling", "coupling difference from baseline",
     "Coupling RDT amplitudes, each scenario minus the baseline."),
)

TOP_SCENARIO_FIGURES = (
    ("scenario_tunes_chromas.png", "measured tune and chromaticity per scenario",
     "Measured tune and Q'H / Q'V, one group of bars per scenario."),
    ("scenario_perturbation_tunes.png", "tune and chromaticity shift per scenario",
     "Measured tune and chromaticity, each scenario minus the unperturbed baseline."),
)


def render_scenario_page(campaigns, scenario_root: Path, modes,
                         destination: Path) -> str:
    """The error-injection configurations against the unperturbed baseline."""
    prefix = render.prefix(scenario_root, destination)
    blocks = []
    top = [
        render.figure(name, alt, caption, prefix)
        for name, alt, caption in TOP_SCENARIO_FIGURES
        if (scenario_root / name).exists()
    ]
    if top:
        blocks += [render.heading("Tune and chromaticity"), "\n\n".join(top)]

    tabs = {}
    for folder, case, word in SCENARIO_FITS:
        found = [
            render.figure(f"{folder}/{stem}.png", alt, caption, prefix)
            for stem, alt, caption in PERTURBATION_FIGURES
            if (scenario_root / folder / f"{stem}.png").exists()
        ]
        if found:
            tabs[f"Fitted with {word}"] = "\n\n".join(found)
    if tabs:
        blocks += [render.heading("Effect of the perturbations"), render.tabbed(tabs)]

    knob_tabs = {}
    for mode in modes:
        for _, case, word in SCENARIO_FITS:
            directory = scenario_root / "scenario-comparison" / mode.slug / case
            found = [
                render.figure(
                    str((directory / f"knob_diffs_{suffix.lstrip('.')}.png")
                        .relative_to(scenario_root)),
                    f"fitted {family.word[:-1]} difference from baseline",
                    f"Fitted {family.word[:-1]} per magnet, each scenario minus "
                    "the unperturbed baseline.",
                    prefix,
                )
                for suffix, family in FAMILIES.items()
                if (directory / f"knob_diffs_{suffix.lstrip('.')}.png").exists()
            ]
            if found:
                knob_tabs[f"{mode.label}, {word}"] = "\n\n".join(found)
    if knob_tabs:
        blocks += [render.heading("Fitted gradients against the baseline"),
                   render.tabbed(knob_tabs)]

    baseline, *rest = campaigns
    statement = (
        f"PSB ring 3 · {baseline.label} as the unperturbed baseline, against "
        + ", ".join(campaign.label for campaign in rest)
        + ". The left column of each perturbation figure is measurement against "
        "measurement; the right is the same difference taken between the "
        "LOCO-fitted lattices."
    )
    return render.page("Scenario comparison", statement, blocks)


#: The vocabulary the pages use, defined once. Four words were previously used
#: across the site for three concepts, with no glossary anywhere.
GLOSSARY = (
    ("working point", "One of the two quadrupole powerings the MD ran: normal "
     "tunes or inverted tunes. A nav section each."),
    ("configuration", "One machine state within a working point: the "
     "unperturbed baseline, or one of the three with an error injected. Four "
     "per working point, shown as the tabs on every results page. Called a "
     "*scenario* on the scenario-comparison page, where the baseline is "
     "subtracted from the other three."),
    ("case", "One fitted option within a page: which knob families the fit was "
     "allowed to move, and how they were grouped. Two per page."),
    ("orbit-matching mode", "What the fit was scored against. *Delta orbits* "
     "subtract a reference orbit from both planes, so a constant kick is "
     "invisible and quadrupole offsets are not fitted. *Absolute orbits* keep "
     "the machine's own closed orbit in both planes, so bends and offsets are "
     "constrained and free."),
    ("momentum mode", "*Single momentum* fits the nominal-RF acquisitions only, "
     "and the other RF settings are held-out validation. *Multi momentum* fits "
     "every RF setting together."),
    ("lumping", "How per-magnet families were grouped. *Lumped to 32 knobs by "
     "cell* ties the two QFO flanking a QDE and leaves the QDE free. *One knob "
     "per magnet* frees all 48 against 16 BPMs per plane."),
    ("Method 1", "The MAD-NG parametric-twiss fit of the measured response "
     "matrix, on the delta orbits, over the same 32 cell-grouped knobs."),
    ("Method 2", "The closed-orbit fit: one MAD-NG worker per corrector "
     "setting, Levenberg-Marquardt over the same knobs."),
)


def render_method_page(directions, destination: Path) -> str:
    """What was measured and fitted, as statements, plus the vocabulary."""
    blocks = []
    for label, campaigns in directions:
        rows = []
        for campaign in campaigns:
            summary = read_json(campaign.optics_dir / "summary.json")
            measured = summary.get("measured", {})
            tunes = measured.get("natural_tunes")
            quads = summary.get("quad_settings", {})
            rows.append([
                campaign.label,
                f"{tunes[0]:.4f} / {tunes[1]:.4f}" if tunes else "—",
                f"{quads.get('kbrqf', float('nan')):.7f} / "
                f"{quads.get('kbrqd', float('nan')):.7f}" if quads else "—",
                campaign.summary,
            ])
        blocks += [
            render.heading(label, 3),
            render.table(
                ["configuration", "measured $Q_x$ / $Q_y$",
                 "QFO / QDE circuit, MAD $k_1$", "what it is"],
                rows,
            ),
        ]
    blocks.insert(0, render.heading("Configurations"))
    blocks += [
        render.heading("Vocabulary"),
        "\n\n".join(f"**{term}**\n: {text}" for term, text in GLOSSARY),
    ]
    statement = (
        "Statements only. What was measured, what was modelled, what was "
        "fitted. The conventions the axes are drawn in are on the "
        "[conventions page](reference/conventions.md)."
    )
    return render.page("Method", statement, blocks)
