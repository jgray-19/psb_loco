"""What each page shows, declared. Adding a page is adding an entry."""

from __future__ import annotations

from dataclasses import dataclass

from loco_common.case_names import ALL_PAGES, Page


@dataclass(frozen=True)
class FigureSpec:
    """One figure: its file stem after the page slug, its alt text and caption."""

    stem: str
    alt: str
    caption: str


@dataclass(frozen=True)
class SectionSpec:
    heading: str
    figures: tuple[FigureSpec, ...] = ()
    #: Name of a table builder in render, or None for a figure-only section.
    table: str | None = None


@dataclass(frozen=True)
class PageSpec:
    """One rendered page, bound to the case_names Page whose fits it shows."""

    page: Page
    sections: tuple[SectionSpec, ...]

    @property
    def slug(self) -> str:
        return self.page.slug

    @property
    def title(self) -> str:
        return self.page.title


def _figure(stem: str, alt: str, caption: str) -> FigureSpec:
    return FigureSpec(stem, alt, caption)


KNOB_TABLE = SectionSpec("Fitted knobs, per family", (), table="knob_table")

KNOBS = SectionSpec("Fitted knobs", (
    _figure("dk1l_by_s", "gradient error per magnet against s",
            "Fitted gradient error per magnet, one panel per case."),
    _figure("dk1l_significance", "gradient error over its own error bar",
            "The same gradients as |value| / sigma, log scale."),
    _figure("dk0l_by_s", "bend error per magnet against s",
            "Fitted bend error per magnet, where bends were free."),
    _figure("dy_by_s", "quadrupole offset per magnet against s",
            "Fitted quadrupole offset per magnet, where offsets were free."),
    _figure("tilt_by_s", "quadrupole roll per magnet against s",
            "Fitted quadrupole roll per magnet, where rolls were free."),
    _figure("tilt_significance", "roll over its own error bar",
            "The same rolls as |value| / sigma, log scale."),
))

LATTICE = SectionSpec("Fitted lattice, against the tune-matched model", (
    _figure("beta_beating_matched", "beta-beating against the matched model",
            "Beta-beating against the tune-matched model, with the measured "
            "points; the machine-knob model is the dotted curve."),
    _figure("phase_error_matched", "phase error against the matched model",
            "Phase error, referred to the lattice matched to the measured tune."),
    _figure("dispersion_matched", "dispersion against the matched model",
            "Dispersion, referred to the lattice matched to the measured tune."),
    _figure("coupling_matched", "coupling against the matched model",
            "Coupling amplitudes, referred to the tune-matched lattice."),
))

TUNE = SectionSpec("Tune and chromaticity", (
    _figure("case_tunes", "fitted tune per case",
            "Fitted tune per case against the measured tune, bar length is the error."),
    _figure("case_chromaticity", "fitted chromaticity per case",
            "Fitted Q'H and Q'V against the measurement, under both Dp/p calibrations."),
))

RESIDUALS = SectionSpec("Residuals", (
    _figure("residuals_delta", "delta-orbit residual per BPM",
            "Delta-orbit residual rms per BPM, measured minus model."),
    _figure("residuals_absolute", "closed-orbit residual per BPM",
            "Closed-orbit residual rms per BPM, measured minus model."),
    _figure("scores", "residual per scored measurement",
            "Residual rms per scored measurement, as a percentage of the measured "
            "amplitude, log scale."),
))

SECTIONS = (KNOB_TABLE, KNOBS, LATTICE, TUNE, RESIDUALS)

#: Every rendered page, one per case_names Page.
PAGE_SPECS = tuple(PageSpec(page=page, sections=SECTIONS) for page in ALL_PAGES)
PAGE_SPEC_BY_SLUG = {spec.slug: spec for spec in PAGE_SPECS}


def every_figure_stem() -> list[str]:
    """Every figure stem any page declares, deduplicated."""
    return list(dict.fromkeys(
        figure.stem for spec in PAGE_SPECS
        for section in spec.sections for figure in section.figures
    ))
