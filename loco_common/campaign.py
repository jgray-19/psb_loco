"""The two machine states the 2026-08-21 MD scanned, as data.

The MD ran the same LOCO corrector scan twice, at two quadrupole powerings whose
tunes sit either side of each other -- ``Qx = 4.171, Qy = 4.229`` and, with QFO
raised and QDE lowered, ``Qx = 4.233, Qy = 4.128``. Everything published before
this module existed was the first of those, and nothing said so.

A campaign is therefore the whole of what differs between the two: which
acquisitions, which scan log, which corrector step, which quadrupole circuits,
where the cache and the results go, and what the machine's optics were measured
to be. One object rather than a module-level constant per item, because the
alternative -- four constants in ``measured_response`` and one dict in ``model``,
each defaulting to the normal-tunes value -- is how a fit ends up reading the
inverted acquisitions against the normal-tunes model.

The measured optics carried here are *pinned numbers*, not a file read: the
acquisition mount is often absent (HANDOVER.md section 2), and a campaign has
to be describable without it. :mod:`scripts.measured_optics` re-derives them from
the MD's own files and fails if they have moved, so the pinning is checked rather
than trusted.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

from psb_md.acd_config import read_strengths_file
from psb_md.defaults import MachineConfig
from psb_md.defaults import campaign as psb_md_campaign


def _from_machine_config(machine_config: MachineConfig) -> tuple[dict[str, float], Path, float]:
    """quad_settings' base, chroma file and driven-tune offset, from psb_md's own campaign."""
    config = psb_md_campaign(machine_config)
    quad_settings = read_strengths_file(config.strengths_files[0])
    offset = config.chroma.driven_tune_offset.offsets(0.0, 0.0)[0]
    return quad_settings, config.chroma.file, offset

#: Root of the acquisition mount. Read-only; write nothing under it.
MOUNT_PATH = Path("/home/jmgray/mnt")
#: Some hosts have /user/psbop mounted directly; others only have it via
#: MOUNT_PATH's sshfs mount. Prefer the direct mount when it's there.
USE_MOUNT = not Path("/user/psbop").is_dir()
FIRST_PATH = (
    MOUNT_PATH if USE_MOUNT else Path("/")
) / "user/psbop/MultiTurn/2026_08_21_Multiturn"
SECOND_PATH = (
    (MOUNT_PATH if USE_MOUNT else Path("/")) / "user/psbop/MultiTurn/2026_08_28_Multiturn"
)
#: The 29 Aug 2026 repeat, at the new P17/P23 tune point -- the normal-tunes
#: counterpart to SECOND_PATH's inverted-tunes scan.
THIRD_PATH = (
    (MOUNT_PATH if USE_MOUNT else Path("/")) / "user/psbop/MultiTurn/2026_08_29_Multiturn"
)
#: The 30 Aug 2026 day, which carries only the normal-tunes sextupoles-on
#: campaign: the 29th ran out of time before it, so its ``normal_tunes_sext_on``
#: folders were left empty and the scan was retaken here the next morning.
FOURTH_PATH = (
    (MOUNT_PATH if USE_MOUNT else Path("/")) / "user/psbop/MultiTurn/2026_08_30_Multiturn"
)
SCAN_PATH = FIRST_PATH / "psb_loco_scan"
CHROMA_PATH = FIRST_PATH / "chroma"

#: Where derived products live, beside the repository rather than on the mount.
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = REPO_ROOT / "data"


@dataclass(frozen=True)
class MeasuredOptics:
    """What the machine's optics were measured to be, outside any model.

    Natural tune and Q' are fitted live from ``chroma_file``, not stored here.
    """

    acd_dirs: dict[str, Path]
    chroma_file: Path
    #: AC-dipole drive offset from the live natural tune (``qxd = qx - offset``).
    driven_tune_offset: float | None = None
    #: Per-folder configured drive, for campaigns predating the offset convention.
    legacy_driven: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class Campaign:
    """One machine state, and every input keyed to it."""

    slug: str
    label: str
    #: One sentence for the tab that opens with this campaign.
    summary: str
    measurements_path: Path
    scan_log: Path
    #: The corrector step the scan stepped by, in LSA ``/K``.
    delta_k: float
    #: The quadrupole circuits the machine sat at, as MAD ``k1``. Read from LSA,
    #: never matched -- see :data:`loco_common.model.SCAN_QUAD_SETTINGS`.
    quad_settings: dict[str, float]
    optics: MeasuredOptics
    #: Whose measured optics these are. The large-step inverted scan is the same
    #: machine as the inverted scan, so it shares its optics analysis rather than
    #: paying for a second harpy run of the same acquisitions.
    optics_slug: str | None = None
    #: Extra scan logs whose RF condition was set by which directory they were
    #: written to rather than by an ``rf_offset_mm`` field on each entry, keyed
    #: by that offset in mm. Merged with :attr:`scan_log` in
    #: :func:`loco_common.measured_response.load_scan`. All acquisitions they
    #: reference still have to live under :attr:`measurements_path` -- one
    #: directory of SDDS files, several scan logs pointed at it.
    rf_scan_logs: dict[float, Path] = field(default_factory=dict)
    #: The ``psb_md.defaults.MachineConfig`` this campaign corresponds to, for
    #: :func:`loco_common.model.build_model`'s diagnostic comparison against
    #: psb_md's own matched-tune/corrector values. ``None`` falls back to that
    #: function's default rather than mislabelling a campaign psb_md has no
    #: matching entry for.
    machine_config: MachineConfig | None = None

    @property
    def results_root(self) -> Path:
        """Where this campaign's fits live: ``results/matrix`` for the first."""
        return (
            REPO_ROOT
            / "results"
            / ("matrix" if self.slug == "normal" else f"matrix_{self.slug}")
        )

    @property
    def method1_dir(self) -> Path:
        """Where this campaign's Method-1 fit is written by ``run_method1``.

        Method 1 writes the same native cell-grouped ``.dk1l`` knobs as Method 2,
        so the scoring, optics cache and figures read this directory directly.
        """
        return self.results_root / "method1"

    @property
    def optics_dir(self) -> Path:
        """Where the measured-optics products of this campaign are written."""
        return REPO_ROOT / "results" / "optics" / (self.optics_slug or self.slug)

    def cache_file(self, name: str) -> Path:
        """A parquet cache path, namespaced by campaign.

        The normal-tunes files keep the names they already have on disk, so the
        ten-minute cold read of the first scan is not repeated for the sake of a
        prefix.
        """
        prefix = "" if self.slug == "normal" else f"{self.slug}_"
        return CACHE_PATH / f"{prefix}{name}"

    def figures_dir(self, root: Path) -> Path:
        """Figure directory under *root*, one per campaign."""
        return root / self.slug


#: The four ring quadrupole trim circuits, off in both configurations. Pinned
#: rather than left to the sequence's defaults so a sequence that happens to
#: define them non-zero cannot silently move the start model.
TRIMS_OFF: dict[str, float] = {
    "kbrqfcorr": 0.0,
    "kbrqdcorr": 0.0,
    "kbrqd3corr": 0.0,
    "kbrqd14corr": 0.0,
}


#: Retired 2026-08-21 scans; see :mod:`loco_common.retired_campaigns`.
from loco_common.retired_campaigns import INVERTED, NORMAL  # noqa: E402

#: quad_settings' kbrqf/kbrqd, chroma_file and driven_tune_offset all come from
#: psb_md's own P23_P13_FINAL campaign entry, not a separate hand-typed copy.
_P23_P13_QUADS, _P23_P13_CHROMA_FILE, _P23_P13_DRIVEN_OFFSET = _from_machine_config(
    MachineConfig.P23_P13_FINAL
)

INVERTED_SECOND = replace(
    INVERTED,
    slug="inverted_second",
    label="Inverted tunes, 28th",
    measurements_path=SECOND_PATH / "inverted_tunes" / "loco" / "0mm",
    machine_config=MachineConfig.P23_P13_FINAL,
    quad_settings={**_P23_P13_QUADS, **TRIMS_OFF},
    optics =MeasuredOptics(
        driven_tune_offset=_P23_P13_DRIVEN_OFFSET,
        acd_dirs={
            "0mm": SECOND_PATH / "inverted_tunes" / "0mm",
            "m2mm": SECOND_PATH / "inverted_tunes" / "m2mm",
            "2mm": SECOND_PATH / "inverted_tunes" / "2mm",
        },
        chroma_file=_P23_P13_CHROMA_FILE,
    ),
    delta_k=7.5e-5,
    scan_log=SECOND_PATH / "inverted_tunes" / "loco" / "0mm" / "scan_20260828T093232.jsonl",
    # The RF-offset condition for the 28th's scan was set by which directory was
    # run, not by an ``rf_offset_mm`` field on each entry (those are absent), so
    # the -2 mm and +2 mm runs are named here rather than left for
    # ``entry.get("rf_offset_mm")`` to find. The save directory was never
    # switched off ``0mm`` for either of them, so all three logs' acquisitions
    # live under this campaign's single ``measurements_path`` above.
    rf_scan_logs={
        -2.0: SECOND_PATH / "inverted_tunes" / "loco" / "m2mm" / "scan_20260828T101536.jsonl",
        2.0: SECOND_PATH / "inverted_tunes" / "loco" / "2mm" / "scan_20260828T095625.jsonl",
    },
)


#: The inverted lattice again, stepped once at 1.5e-4 instead of four times at
#: 5e-5. Three times the kick per step buys signal against the BPM noise; one step
#: per corrector means the response's linearity is assumed rather than measured.
#: It is the same machine as :data:`INVERTED` -- same quads, same correctors -- so
#: it is a cross-check of the step size, not a third configuration.
INVERTED_DOUBLE = Campaign(
    slug="inverted_double",
    label="Inverted tunes, large step",
    summary=(
        "The inverted lattice stepped once at 1.5e-4 rather than four times at "
        "5e-5: more orbit per point, and no measurement of the response's own "
        "linearity."
    ),
    measurements_path=SCAN_PATH / "CO_measurements_inverted_tunes_double",
    scan_log=SCAN_PATH / "scan_20260821T150756.jsonl",
    delta_k=1.5e-4,
    quad_settings=INVERTED.quad_settings,
    optics=INVERTED.optics,
    optics_slug=INVERTED.slug,
)


#: chroma_file comes from psb_md's own P23_P13_FINAL_QDE14 campaign entry, same
#: as INVERTED_SECOND's -- quad_settings deliberately stays INVERTED_SECOND's
#: unperturbed circuits, since LOCO must recover the QDE14 error, not be handed it.
_, _P23_P13_QDE14_CHROMA_FILE, _ = _from_machine_config(MachineConfig.P23_P13_FINAL_QDE14)

INVERTED_QDE14_ERR = replace(
    INVERTED_SECOND,
    slug="inverted_qde14_err",
    label="Inverted tunes, QDE14 error",
    machine_config=MachineConfig.P23_P13_FINAL_QDE14,
    summary=(
        "The 28th's inverted lattice again, with QDE14 (kbrqd14corr = "
        "+0.0073775865) deliberately mis-trimmed in LSA. The LOCO scan (all "
        "three RF offsets), the chroma and the AC-dipole optics were all "
        "retaken, and the model starts from its unperturbed circuits so LOCO "
        "has to find the error."
    ),
    measurements_path=SECOND_PATH / "inverted_tunes_qde14_err" / "loco" / "0mm",
    scan_log=SECOND_PATH / "inverted_tunes_qde14_err" / "loco" / "0mm" / "scan_20260828T124746.jsonl",
    rf_scan_logs={
        -2.0: SECOND_PATH / "inverted_tunes_qde14_err" / "loco" / "m2mm" / "scan_20260828T131330.jsonl",
        2.0: SECOND_PATH / "inverted_tunes_qde14_err" / "loco" / "2mm" / "scan_20260828T133119.jsonl",
    },
    optics=MeasuredOptics(
        driven_tune_offset=INVERTED_SECOND.optics.driven_tune_offset,
        # Its own AC-dipole kicks, on the mis-trimmed machine. These read
        # INVERTED_SECOND's folders until 2026-08-30, which silently analysed
        # the unperturbed acquisitions under this campaign's name and made its
        # measured optics a copy of the baseline's.
        acd_dirs={
            "0mm": SECOND_PATH / "inverted_tunes_qde14_err" / "0mm",
            "m2mm": SECOND_PATH / "inverted_tunes_qde14_err" / "m2mm",
            "2mm": SECOND_PATH / "inverted_tunes_qde14_err" / "2mm",
        },
        chroma_file=_P23_P13_QDE14_CHROMA_FILE,
    ),
    # Not optics_slug=INVERTED_SECOND.slug: separate acquisitions, separate
    # omc3 model at this campaign's own measured natural tune (QDE14 shifts
    # it), and a campaign-specific summary -- sharing the directory would make
    # each run overwrite the other's summary.json.
)


#: chroma_file comes from psb_md's own P23_P13_FINAL_QDE14_QDE3 campaign entry --
#: quad_settings stays INVERTED_SECOND's unperturbed circuits, same reasoning as
#: INVERTED_QDE14_ERR: LOCO has to recover both errors, not be handed them.
_, _P23_P13_QDE14_QDE3_CHROMA_FILE, _ = _from_machine_config(
    MachineConfig.P23_P13_FINAL_QDE14_QDE3
)

INVERTED_QDE14_QDE3_ERR = replace(
    INVERTED_SECOND,
    slug="inverted_qde14_qde3_err",
    label="Inverted tunes, QDE14+QDE3 error",
    machine_config=MachineConfig.P23_P13_FINAL_QDE14_QDE3,
    summary=(
        "The 28th's inverted lattice with both QDE14 and QDE3 deliberately "
        "mis-trimmed in LSA. The LOCO scan (all three RF offsets), the chroma "
        "and the AC-dipole optics were all retaken, and the model starts from "
        "its unperturbed circuits so LOCO has to find both errors."
    ),
    measurements_path=SECOND_PATH / "inverted_tunes_qde14_qde3_err" / "loco" / "0mm",
    scan_log=SECOND_PATH / "inverted_tunes_qde14_qde3_err" / "loco" / "0mm" / "scan_20260828T153631.jsonl",
    rf_scan_logs={
        -2.0: SECOND_PATH / "inverted_tunes_qde14_qde3_err" / "loco" / "m2mm" / "scan_20260828T161135.jsonl",
        2.0: SECOND_PATH / "inverted_tunes_qde14_qde3_err" / "loco" / "2mm" / "scan_20260828T155404.jsonl",
    },
    optics=MeasuredOptics(
        driven_tune_offset=INVERTED_SECOND.optics.driven_tune_offset,
        # Own AC-dipole kicks, not INVERTED_SECOND's; measured_optics.py fails
        # loudly on an empty folder rather than silently reusing another
        # campaign's driven-tune data.
        acd_dirs={
            "0mm": SECOND_PATH / "inverted_tunes_qde14_qde3_err" / "0mm",
            "m2mm": SECOND_PATH / "inverted_tunes_qde14_qde3_err" / "m2mm",
            "2mm": SECOND_PATH / "inverted_tunes_qde14_qde3_err" / "2mm",
        },
        chroma_file=_P23_P13_QDE14_QDE3_CHROMA_FILE,
    ),
    # Not optics_slug=INVERTED_SECOND.slug -- see INVERTED_QDE14_ERR's comment.
)


#: chroma_file comes from psb_md's own P23_P13_FINAL_SEXTS_ON campaign entry --
#: quad_settings stays INVERTED_SECOND's unperturbed circuits; unlike the QDE
#: campaigns nothing is mis-trimmed here, the sextupoles are simply powered.
_, _P23_P13_SEXTS_ON_CHROMA_FILE, _ = _from_machine_config(
    MachineConfig.P23_P13_FINAL_SEXTS_ON
)

INVERTED_SEXTS_ON = replace(
    INVERTED_SECOND,
    slug="inverted_sexts_on",
    label="Inverted tunes, sextupoles on",
    machine_config=MachineConfig.P23_P13_FINAL_SEXTS_ON,
    summary=(
        "The 28th's inverted lattice with the ring sextupoles powered instead "
        "of off. The LOCO scan (all three RF offsets), the chroma and the "
        "AC-dipole optics were all retaken, and the model starts from its "
        "unperturbed circuits."
    ),
    measurements_path=SECOND_PATH / "inverted_tunes_sexts_on" / "loco" / "0mm",
    scan_log=SECOND_PATH / "inverted_tunes_sexts_on" / "loco" / "0mm" / "scan_20260828T165943.jsonl",
    rf_scan_logs={
        -2.0: SECOND_PATH / "inverted_tunes_sexts_on" / "loco" / "m2mm" / "scan_20260828T172322.jsonl",
        2.0: SECOND_PATH / "inverted_tunes_sexts_on" / "loco" / "2mm" / "scan_20260828T174041.jsonl",
    },
    optics=MeasuredOptics(
        driven_tune_offset=INVERTED_SECOND.optics.driven_tune_offset,
        # Own AC-dipole kicks -- see INVERTED_QDE14_QDE3_ERR.
        acd_dirs={
            "0mm": SECOND_PATH / "inverted_tunes_sexts_on" / "0mm",
            "m2mm": SECOND_PATH / "inverted_tunes_sexts_on" / "m2mm",
            "2mm": SECOND_PATH / "inverted_tunes_sexts_on" / "2mm",
        },
        chroma_file=_P23_P13_SEXTS_ON_CHROMA_FILE,
    ),
    # Not optics_slug=INVERTED_SECOND.slug -- see INVERTED_QDE14_ERR's comment.
)


#: quad_settings' kbrqf/kbrqd, chroma_file and driven_tune_offset all come from
#: psb_md's own P17_P23_FINAL campaign entry -- the normal-tunes counterpart of
#: _P23_P13_QUADS above, taken 29 Aug 2026 rather than the 28th.
_P17_P23_QUADS, _P17_P23_CHROMA_FILE, _P17_P23_DRIVEN_OFFSET = _from_machine_config(
    MachineConfig.P17_P23_FINAL
)

NORMAL_SECOND = replace(
    NORMAL,
    slug="normal_second",
    label="Normal tunes, 29th",
    summary=(
        "The 29th's repeat of the normal-tunes lattice, at the new P17/P23 tune "
        "point and orbit-corrector set. The LOCO scan (all three RF offsets) and "
        "chroma were retaken from scratch, same layout as the 28th's "
        "inverted-tunes campaign."
    ),
    measurements_path=THIRD_PATH / "normal_tunes" / "loco" / "0mm",
    machine_config=MachineConfig.P17_P23_FINAL,
    quad_settings={**_P17_P23_QUADS, **TRIMS_OFF},
    optics=MeasuredOptics(
        driven_tune_offset=_P17_P23_DRIVEN_OFFSET,
        acd_dirs={
            "0mm": THIRD_PATH / "normal_tunes" / "0mm",
            "m2mm": THIRD_PATH / "normal_tunes" / "m2mm",
            "2mm": THIRD_PATH / "normal_tunes" / "2mm",
        },
        chroma_file=_P17_P23_CHROMA_FILE,
    ),
    delta_k=7.5e-5,
    scan_log=THIRD_PATH / "normal_tunes" / "loco" / "0mm" / "scan_20260829T095805.jsonl",
    rf_scan_logs={
        -2.0: THIRD_PATH / "normal_tunes" / "loco" / "m2mm" / "scan_20260829T103356.jsonl",
        2.0: THIRD_PATH / "normal_tunes" / "loco" / "2mm" / "scan_20260829T101646.jsonl",
    },
)


#: chroma_file comes from psb_md's own P17_P23_FINAL_QDE14 campaign entry, same
#: as NORMAL_SECOND's -- quad_settings deliberately stays NORMAL_SECOND's
#: unperturbed circuits, since LOCO must recover the QDE14 error, not be handed it.
_, _P17_P23_QDE14_CHROMA_FILE, _ = _from_machine_config(MachineConfig.P17_P23_FINAL_QDE14)

NORMAL_QDE14_ERR = replace(
    NORMAL_SECOND,
    slug="normal_qde14_err",
    label="Normal tunes, QDE14 error",
    machine_config=MachineConfig.P17_P23_FINAL_QDE14,
    summary=(
        "The 29th's normal lattice again, with QDE14 deliberately mis-trimmed "
        "in LSA. The LOCO scan (all three RF offsets) and this campaign's own "
        "driven-tune optics were retaken, same as INVERTED_QDE14_ERR."
    ),
    measurements_path=THIRD_PATH / "normal_tunes_qde14_err" / "loco" / "0mm",
    scan_log=THIRD_PATH / "normal_tunes_qde14_err" / "loco" / "0mm" / "scan_20260829T125640.jsonl",
    rf_scan_logs={
        -2.0: THIRD_PATH / "normal_tunes_qde14_err" / "loco" / "m2mm" / "scan_20260829T133305.jsonl",
        2.0: THIRD_PATH / "normal_tunes_qde14_err" / "loco" / "2mm" / "scan_20260829T131321.jsonl",
    },
    optics=MeasuredOptics(
        driven_tune_offset=NORMAL_SECOND.optics.driven_tune_offset,
        acd_dirs={
            "0mm": THIRD_PATH / "normal_tunes_qde14_err" / "0mm",
            "m2mm": THIRD_PATH / "normal_tunes_qde14_err" / "m2mm",
            "2mm": THIRD_PATH / "normal_tunes_qde14_err" / "2mm",
        },
        chroma_file=_P17_P23_QDE14_CHROMA_FILE,
    ),
    # Not optics_slug=NORMAL_SECOND.slug -- see INVERTED_QDE14_ERR's comment.
)


#: chroma_file comes from psb_md's own P17_P23_FINAL_QDE14_QDE3 campaign entry.
#: As of 2026-08-29 the LOCO scan (all three RF offsets) and this campaign's
#: own driven-tune optics (acd_dirs) are complete.
_, _P17_P23_QDE14_QDE3_CHROMA_FILE, _ = _from_machine_config(
    MachineConfig.P17_P23_FINAL_QDE14_QDE3
)

NORMAL_QDE14_QDE3_ERR = replace(
    NORMAL_SECOND,
    slug="normal_qde14_qde3_err",
    label="Normal tunes, QDE14+QDE3 error",
    machine_config=MachineConfig.P17_P23_FINAL_QDE14_QDE3,
    summary=(
        "The 29th's normal lattice with both QDE14 and QDE3 deliberately "
        "mis-trimmed in LSA. The LOCO scan (all three RF offsets) and this "
        "campaign's own driven-tune optics were retaken, same as "
        "INVERTED_QDE14_QDE3_ERR."
    ),
    measurements_path=THIRD_PATH / "normal_tunes_qde14_qde3_err" / "loco" / "0mm",
    scan_log=(
        THIRD_PATH / "normal_tunes_qde14_qde3_err" / "loco" / "0mm"
        / "scan_20260829T163906.jsonl"
    ),
    rf_scan_logs={
        -2.0: THIRD_PATH / "normal_tunes_qde14_qde3_err" / "loco" / "m2mm" / "scan_20260829T171234.jsonl",
        2.0: THIRD_PATH / "normal_tunes_qde14_qde3_err" / "loco" / "2mm" / "scan_20260829T165542.jsonl",
    },
    optics=MeasuredOptics(
        driven_tune_offset=NORMAL_SECOND.optics.driven_tune_offset,
        acd_dirs={
            "0mm": THIRD_PATH / "normal_tunes_qde14_qde3_err" / "0mm",
            "m2mm": THIRD_PATH / "normal_tunes_qde14_qde3_err" / "m2mm",
            "2mm": THIRD_PATH / "normal_tunes_qde14_qde3_err" / "2mm",
        },
        chroma_file=_P17_P23_QDE14_QDE3_CHROMA_FILE,
    ),
)


#: chroma_file and driven_tune_offset come from psb_md's own
#: P17_P23_FINAL_SEXTS_ON campaign entry -- quad_settings stays NORMAL_SECOND's
#: unperturbed circuits; as on INVERTED_SEXTS_ON nothing is mis-trimmed here,
#: the ring sextupoles are simply powered.
_, _P17_P23_SEXTS_ON_CHROMA_FILE, _P17_P23_SEXTS_ON_DRIVEN_OFFSET = _from_machine_config(
    MachineConfig.P17_P23_FINAL_SEXTS_ON
)

#: The one campaign not on THIRD_PATH: the 29th ran out of time, so this was
#: taken on the morning of the 30th instead, under FOURTH_PATH. Its 29th folders
#: still exist and are still empty -- do not point at them.
_SEXTS_ON_ROOT = FOURTH_PATH / "normal_tunes_sext_on"

NORMAL_SEXTS_ON = replace(
    NORMAL_SECOND,
    slug="normal_sexts_on",
    label="Normal tunes, sextupoles on",
    machine_config=MachineConfig.P17_P23_FINAL_SEXTS_ON,
    summary=(
        "The normal lattice with the ring sextupoles powered instead of off, "
        "taken on the 30th after the 29th ran out of time. The LOCO scan (all "
        "three RF offsets), the chroma and this campaign's own driven-tune "
        "optics were all retaken; unlike every other campaign here it also has "
        "AC-dipole-off blanks, so the dispersive-ripple and per-BPM "
        "interference removals do run."
    ),
    measurements_path=_SEXTS_ON_ROOT / "loco" / "0mm",
    scan_log=_SEXTS_ON_ROOT / "loco" / "0mm" / "scan_20260830T093624.jsonl",
    rf_scan_logs={
        -2.0: _SEXTS_ON_ROOT / "loco" / "m2mm" / "scan_20260830T101045.jsonl",
        2.0: _SEXTS_ON_ROOT / "loco" / "2mm" / "scan_20260830T095303.jsonl",
    },
    optics=MeasuredOptics(
        driven_tune_offset=_P17_P23_SEXTS_ON_DRIVEN_OFFSET,
        acd_dirs={
            "0mm": _SEXTS_ON_ROOT / "0mm",
            "m2mm": _SEXTS_ON_ROOT / "m2mm",
            "2mm": _SEXTS_ON_ROOT / "2mm",
        },
        chroma_file=_P17_P23_SEXTS_ON_CHROMA_FILE,
    ),
)


CAMPAIGNS: dict[str, Campaign] = {
    campaign.slug: campaign
    for campaign in (
        INVERTED_DOUBLE,
        NORMAL_SECOND,
        NORMAL_QDE14_ERR,
        NORMAL_QDE14_QDE3_ERR,
        NORMAL_SEXTS_ON,
        INVERTED_SECOND,
        INVERTED_QDE14_ERR,
        INVERTED_QDE14_QDE3_ERR,
        INVERTED_SEXTS_ON,
    )
}

#: The campaigns the inverted-tunes report pages tab between, in tab order.
INVERTED_PAGE_CAMPAIGNS: tuple[Campaign, ...] = (
    INVERTED_SECOND,
    INVERTED_QDE14_ERR,
    INVERTED_QDE14_QDE3_ERR,
    INVERTED_SEXTS_ON,
)

#: The normal-tunes counterpart of INVERTED_PAGE_CAMPAIGNS.
NORMAL_PAGE_CAMPAIGNS: tuple[Campaign, ...] = (
    NORMAL_SECOND,
    NORMAL_QDE14_ERR,
    NORMAL_QDE14_QDE3_ERR,
    NORMAL_SEXTS_ON,
)

#: Backward-compatible alias -- most of the current report machinery still
#: imports PAGE_CAMPAIGNS meaning "the inverted-tunes tab set".
PAGE_CAMPAIGNS = INVERTED_PAGE_CAMPAIGNS


def campaign_by_slug(slug: str) -> Campaign:
    """Look a campaign up by slug, accepting the hyphenated CLI spelling."""
    key = slug.replace("-", "_")
    if key not in CAMPAIGNS:
        raise ValueError(
            f"Unknown campaign {slug!r}; expected one of {sorted(CAMPAIGNS)}"
        )
    return CAMPAIGNS[key]


def add_campaign_argument(
    parser, *, default: str = "inverted_second", multiple: bool = False
) -> None:
    """Add ``--campaign`` to an argparse parser, spelled the same way everywhere."""
    choices = sorted(CAMPAIGNS)
    if multiple:
        parser.add_argument(
            "--campaign",
            nargs="+",
            default=[default],
            choices=choices,
            help="Machine configuration(s) to work on.",
        )
        return
    parser.add_argument(
        "--campaign",
        default=default,
        choices=choices,
        help="Machine configuration to work on (default: the 28th's inverted-tunes scan).",
    )
