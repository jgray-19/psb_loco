"""Turns a result directory slug (``<planes>__<families>__<lump>``) into English.

Every heading, table row, figure title, axis tick and legend entry goes through
:func:`case_sentence` or one of the shorter forms here.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Word the reports use for each free-family letter.
FAMILY_WORD = {
    "k1": "gradients",
    "b": "bends",
    "dy": "offsets",
    "t": "rolls",
    "k0s": "skew dipole errors",
    "k1s": "skew gradient errors",
}

#: Orbit-matching mode in words: ``none`` subtracts a reference orbit, ``xy`` keeps the closed orbit.
PLANES_PHRASE = {
    "none": "both planes as delta orbits",
    "xy": "both planes absolute",
}

#: Short form for figure titles.
PLANES_SHORT = {
    "none": "delta orbit",
    "xy": "absolute orbit",
}

#: Parametrisation: ``none`` is one knob per magnet, ``bpm-family`` ties them by cell and QFO/QDE family (48 quadrupoles, 16 cells).
LUMP_PHRASE = {
    "none": "one knob per magnet",
    "bpm-family": "lumped to 32 knobs by cell",
}

#: Knob count per lump, for narrow table columns.
LUMP_COUNT = {
    "none": "48",
    "bpm-family": "32",
}


@dataclass(frozen=True)
class Case:
    """One fitted option, with every name a report might need."""

    slug: str
    planes: str
    families: str
    lump: str

    @property
    def family_list(self) -> list[str]:
        return [part for part in self.families.split("+") if part]

    @property
    def families_phrase(self) -> str:
        """``k1+t`` -> ``gradients and rolls``."""
        words = [FAMILY_WORD.get(part, part) for part in self.family_list]
        if not words:
            return "nothing free"
        if len(words) == 1:
            return words[0]
        return ", ".join(words[:-1]) + " and " + words[-1]

    @property
    def lump_phrase(self) -> str:
        return LUMP_PHRASE.get(self.lump, self.lump)

    @property
    def planes_phrase(self) -> str:
        return PLANES_PHRASE.get(self.planes, self.planes)

    @property
    def heading(self) -> str:
        """The section heading: ``Gradients and rolls, one knob per magnet``."""
        return f"{self.families_phrase}, {self.lump_phrase}".capitalize()

    @property
    def short(self) -> str:
        """A figure tick label: short enough for an axis, still English."""
        return f"{self.families_phrase}, {LUMP_COUNT.get(self.lump, self.lump)}"

    @property
    def sentence(self) -> str:
        """The full description, including the orbit-matching mode."""
        return (
            f"{self.families_phrase} free, {self.lump_phrase}, "
            f"fitted with {self.planes_phrase}"
        )


def parse_case(slug: str) -> Case:
    """``xy__k1+b+dy__bpm-family`` -> the :class:`Case`; a non-three-part slug (start model) gets empty fields."""
    parts = slug.split("__")
    if len(parts) != 3:
        return Case(slug=slug, planes="", families="", lump="")
    return Case(slug=slug, planes=parts[0], families=parts[1], lump=parts[2])


#: Options that are not a Method-2 case slug, and their names.
OTHER_OPTIONS = {
    "method1": "Method 1, lumped to 32 knobs by cell",
    "start-model": "start model",
}

#: The Method-1 option's on-disk name; not a case slug.
METHOD1_OPTION = "method1"


def display_name(slug: str) -> str:
    """Any option name as something a reader can read, start model included."""
    case = parse_case(slug)
    if not case.families:
        return OTHER_OPTIONS.get(slug, slug)
    return case.short


def case_heading(slug: str) -> str:
    """The section heading for a case, as a plain-English sentence."""
    case = parse_case(slug)
    return case.heading if case.families else display_name(slug)


def case_sentence(slug: str) -> str:
    """The full one-line description of a case, orbit-matching mode included."""
    case = parse_case(slug)
    return case.sentence if case.families else display_name(slug)


@dataclass(frozen=True)
class Page:
    """One report page: the options it compares, and how they are named."""

    slug: str
    planes: str
    title: str
    lede: str
    cases: tuple[str, ...]

    @property
    def case_objects(self) -> list[Case]:
        return [parse_case(slug) for slug in self.cases]

    @property
    def mixed_planes(self) -> bool:
        """Whether the page's options were fitted with different orbit modes (then labels name the mode)."""
        return len({case.planes for case in self.case_objects if case.planes}) > 1

    def label(self, slug: str) -> str:
        """What this page calls one of its options, in a heading or on an axis."""
        case = parse_case(slug)
        if not case.families:
            return display_name(slug)
        if not self.mixed_planes:
            return case.heading
        return f"{case.heading}, {PLANES_SHORT.get(case.planes, case.planes)}s"


def _cases(planes: str, families: tuple[str, ...]) -> tuple[str, ...]:
    """The cases of a page, all lumped ``bpm-family``; per-magnet fits live on :data:`PER_MAGNET_PAGE`."""
    return tuple(f"{planes}__{family}__bpm-family" for family in families)


#: Delta-orbit page: a constant kick cancels, so no bends or ``dy``; rolls do not cancel.
DELTA_PAGE = Page(
    slug="delta",
    planes="none",
    title="Delta orbits",
    lede=(
        "A reference orbit is subtracted from both planes, so this is a pure "
        "response measurement. Its defining property is what it cannot see: a "
        "constant kick. A quadrupole offset is exactly that, so it cancels out "
        "of a delta orbit to linear order and is not fitted here. A roll does "
        "not cancel -- its skew kick goes as the beam position at the magnet, "
        "which is what the correctors change -- so the rolls are fitted "
        "alongside the gradients."
    ),
    cases=_cases("none", ("k1", "k1+t")),
)

#: Absolute-orbit page: bends and offsets are constrained by the static orbit and must be free.
ABSOLUTE_PAGE = Page(
    slug="absolute",
    planes="xy",
    title="Absolute orbits",
    lede=(
        "Both planes keep the machine's own closed orbit rather than a "
        "difference, so the untrimmed orbit is itself a constraint. That is the "
        "only measurement a dipole error or a quadrupole offset can be fitted "
        "against, so bends and offsets are free in every case here -- freezing "
        "either leaves the gradients absorbing an orbit they did not make. It "
        "is also the mode with the most parameters for the least data, which is "
        "what the error bars in each section are for."
    ),
    cases=_cases("xy", ("k1+b+dy", "k1+b+dy+t")),
)

#: Per-magnet page: one option per orbit mode.
PER_MAGNET_PAGE = Page(
    slug="per-magnet",
    planes="",
    title="One knob per magnet",
    lede=(
        "Every gradient free, one knob per quadrupole: 48 parameters against 16 "
        "BPMs per plane. The two options here are the same parametrisation in "
        "the two orbit-matching modes, kept off the results pages and shown "
        "together instead."
    ),
    cases=("none__k1__none", "xy__k1+b+dy__none"),
)

#: Method-1 page: delta-orbit only, beside the Method-2 fit at the same 32 knobs.
METHOD1_PAGE = Page(
    slug="method1",
    planes="none",
    title="Method 1",
    lede=(
        "The MAD-NG parametric-twiss fit of the measured response matrix, on "
        "the delta orbits, beside the two Method-2 delta-orbit fits of the same "
        "data."
    ),
    cases=(METHOD1_OPTION, "none__k1__bpm-family"),
)

#: The pages ``run_campaign_fits`` fits, in nav order.
PAGES = (DELTA_PAGE, ABSOLUTE_PAGE)

#: Every rendered page, including those that re-show options fitted for the above.
ALL_PAGES = (*PAGES, PER_MAGNET_PAGE, METHOD1_PAGE)


def every_page_case() -> list[str]:
    """Every Method-2 case any page shows, deduplicated, in page order (Method 1 excluded)."""
    return list(
        dict.fromkeys(
            slug
            for page in ALL_PAGES
            for slug in page.cases
            if slug not in OTHER_OPTIONS
        )
    )


def every_option() -> list[str]:
    """Every fitted option a page shows, Method 1 included."""
    return list(dict.fromkeys(slug for page in ALL_PAGES for slug in page.cases))


#: Fit mode the perturbation figures' fitted half is drawn from; fixed across campaigns.
LOCO_OPTICS_MODE = "multi"

#: ``(slug, case, what the fit could move)``; the slug names the figure folder and page.
LOCO_OPTICS_FITS = (
    ("gradients", "none__k1__bpm-family", "gradients only"),
    ("rolls", "none__k1+t__bpm-family", "gradients and rolls"),
)

#: Default fit.
LOCO_OPTICS_CASE = LOCO_OPTICS_FITS[0][1]
