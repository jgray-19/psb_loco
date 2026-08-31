"""The one place a result directory's name is turned into English.

A fit lives in ``results/matrix/<planes>__<families>__<lump>`` -- ``none__k1__none``,
``xy__k1+b+dy+t__bpm-family``. That slug is an address, not a description: it
says nothing to a reader about what the fit was allowed to move, and a report
built out of it asks the reader to hold a three-part code in their head while
comparing rows.

So the slug never reaches a page. Every heading, table row, figure title, axis
tick and legend entry goes through :func:`case_sentence` or one of the shorter
forms here. Keeping it in one module rather than a dict per renderer is the
point: the reports, the figures and the correlation axes have to agree on what a
case is called, and three copies of the mapping is how two of them go stale.
"""

from __future__ import annotations

from dataclasses import dataclass

#: What each free-family letter lets the fit move, as the word the reports use.
FAMILY_WORD = {"k1": "gradients", "b": "bends", "dy": "offsets", "t": "rolls"}

#: The magnet quantity behind each family, for captions that need to be precise.
FAMILY_QUANTITY = {
    "k1": "quadrupole k1",
    "b": "dipole k0",
    "dy": "quadrupole dy",
    "t": "quadrupole tilt",
}

#: The orbit-matching mode, in words. ``none`` subtracts a reference orbit from
#: both planes; the others keep the machine's own closed orbit in the named
#: plane, which is the only thing a bend or a quadrupole offset can be fitted
#: against.
PLANES_PHRASE = {
    "none": "both planes as delta orbits",
    "x": "horizontal absolute, vertical delta",
    "y": "vertical absolute, horizontal delta",
    "xy": "both planes absolute",
}

#: Short form of the same, for a figure title that has no room for the long one.
PLANES_SHORT = {
    "none": "delta orbit",
    "x": "mixed orbit",
    "y": "vertical-absolute orbit",
    "xy": "absolute orbit",
}

#: How the per-magnet families were parametrised. ``none`` is one knob per
#: magnet; ``bpm-family`` ties them by lattice cell and QFO/QDE family, and
#: ``bpm`` by cell alone. The counts are for the 48 ring quadrupoles: 16 cells,
#: each one QDE between two QFO, one BPM per cell.
LUMP_PHRASE = {
    "none": "one knob per magnet",
    "bpm-family": "lumped to 32 knobs by cell",
    "bpm": "lumped to 16 knobs by cell",
    "k1only": "gradients lumped to 32, everything else per magnet",
    "dy32-t32-k1free": "offsets and rolls lumped to 32, gradients per magnet",
}

#: Knob count per per-magnet family, as a bare number for a narrow table column.
LUMP_COUNT = {
    "none": "48",
    "bpm-family": "32",
    "bpm": "16",
    "k1only": "32 gradients, 48 offsets and rolls",
    "dy32-t32-k1free": "32 offsets and rolls, 48 gradients",
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
    """``xy__k1+b+dy__bpm-family`` -> the :class:`Case` describing it.

    A slug that is not three parts is not a fitted option -- the start model is
    the one that reaches here -- and comes back with empty fields so callers can
    fall back to :func:`display_name` without a special case of their own.
    """
    parts = slug.split("__")
    if len(parts) != 3:
        return Case(slug=slug, planes="", families="", lump="")
    return Case(slug=slug, planes=parts[0], families=parts[1], lump=parts[2])


#: Options that are not a Method-2 case slug, and what they are called instead.
#: ``method1`` is the MAD-NG parametric-twiss fit. It writes the same
#: cell-grouped ``.dk1l`` knobs into the same results root, so every figure and
#: table reads it exactly as it reads a case -- only its name comes from here.
OTHER_OPTIONS = {
    "method1": "Method 1, lumped to 32 knobs by cell",
    "start": "start model",
    "start_model": "start model",
    "start model": "start model",
    "start-model": "start model",
}

#: The one Method-1 option, as it is named on disk under a campaign's results
#: root. It is not produced by ``run_method2`` and is not a case slug.
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
        """Whether the page's options were fitted with different orbit modes.

        Three pages hold one mode each and never say so in a case name; the
        per-magnet page holds one option from each mode, where the mode is the
        thing that distinguishes them and has to be in the label.
        """
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
    """The two cases of a page: gradients lumped to 32, then rolls beside them.

    The lumping arm is ``bpm-family`` throughout, which ties *every* free
    per-magnet family to 32 -- so a page's rolls are always lumped to whatever
    its gradients are, which is the comparison the study is set up to make.

    Neither arm frees a per-magnet knob. Rolls per magnet were never a case;
    gradients per magnet were, and have been moved off these pages onto
    :data:`PER_MAGNET_PAGE`, which is where 48 gradients against 16 BPMs per
    plane is shown for what it is rather than compared as an equal.
    """
    return tuple(f"{planes}__{family}__bpm-family" for family in families)


#: The delta-orbit page. A reference orbit is subtracted from both planes, so
#: the fit sees a pure response and a constant kick is invisible to it -- which
#: is why neither bends nor quadrupole ``dy`` appear here. Rolls do not cancel:
#: a rolled quadrupole's skew kick goes as the beam position at the magnet, the
#: very thing the correctors move, so ``tilt`` belongs with ``k1``.
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

#: The absolute-orbit page. Both planes keep the machine's own closed orbit, so
#: bends and quadrupole offsets are constrained and have to be free: the static
#: orbit is the measurement they exist to explain, and freezing either leaves
#: the gradients absorbing it.
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

#: The per-magnet page: the option every other page used to carry as its first
#: case, one per retained orbit mode, collected where the comparison is between them and
#: not with the lumped fits. 48 gradients against 16 BPMs per plane is the
#: parametrisation the study is set up to reject, so it is shown once, together,
#: rather than three times beside the answer.
PER_MAGNET_PAGE = Page(
    slug="per-magnet",
    planes="",
    title="One knob per magnet",
    lede=(
        "Every gradient free, one knob per quadrupole: 48 parameters against 16 "
        "BPMs per plane. The three options here are the same parametrisation in "
        "the two orbit-matching modes, kept off the results pages and shown "
        "together instead."
    ),
    cases=("none__k1__none", "xy__k1+b+dy__none"),
)

#: The Method-1 page. Method 1 fits the measured response matrix directly, with
#: MAD-NG's parametric twiss and the same 32 cell-grouped knobs Method 2 lumps
#: to, so it is a delta-orbit fit by construction and has no absolute-plane form
#: -- it appears on this page and nowhere else. Its neighbour is the Method-2
#: delta-orbit fit at that same parametrisation, which is the comparison the page
#: exists for: two solvers, two objectives, one set of knobs. The per-magnet fit
#: is not on it, because it is not the same parametrisation and the page is not
#: where that argument is made.
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

#: The three orbit-matching modes, in nav order. Method 2 throughout, two cases
#: each: these are the pages ``run_campaign_fits`` fits.
PAGES = (DELTA_PAGE, ABSOLUTE_PAGE)

#: Every page that gets rendered, including the two that only re-show options
#: fitted for the pages above.
ALL_PAGES = (*PAGES, PER_MAGNET_PAGE, METHOD1_PAGE)
PAGE_BY_SLUG = {page.slug: page for page in ALL_PAGES}


def every_page_case() -> list[str]:
    """Every Method-2 case any page shows, deduplicated, in page order.

    Method 1 is not in it: it is not produced by ``run_method2`` and has no
    case slug, so a driver that turns a slug into fitter flags must not see it.
    """
    return list(
        dict.fromkeys(
            slug
            for page in ALL_PAGES
            for slug in page.cases
            if slug not in OTHER_OPTIONS
        )
    )


def every_option() -> list[str]:
    """Every fitted option a page shows, Method 1 included.

    What the scoring and the optics cache work over: both read a directory of
    knobs under a campaign's results root and neither cares which fitter wrote
    it.
    """
    return list(dict.fromkeys(slug for page in ALL_PAGES for slug in page.cases))


#: Which fit mode the scenario-comparison perturbation figures' fitted half is
#: drawn from. Named once here rather than argued in each script: that page is
#: not per-mode, so the choice has to be the same for every campaign or the
#: difference between two of them is a difference of fits.
LOCO_OPTICS_MODE = "multi"

#: The fits that half is drawn from, as ``(slug, case, what the fit could
#: move)``. Two of them, on two pages rather than two curves on one: whether
#: the fit was allowed quadrupole rolls decides whether it can put anything in
#: the coupling panels at all, and a page mixing the two answers neither
#: question. The slug names both the figure folder and the page.
LOCO_OPTICS_FITS = (
    ("gradients", "none__k1__bpm-family", "gradients only"),
    ("rolls", "none__k1+t__bpm-family", "gradients and rolls"),
)

#: The default of the two, for a caller that wants one.
LOCO_OPTICS_CASE = LOCO_OPTICS_FITS[0][1]
