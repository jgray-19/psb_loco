"""The PSB machine states the LOCO scans were taken on: exactly ``psb_md``'s campaigns.

Inputs come from ``psb_md.defaults``; this module names each state and says where its derived products live.
The LOCO scan sits in ``<acd_root>/loco`` (one ``scan_*.jsonl`` per RF offset); all three runs' acquisitions are under ``loco/0mm``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from psb_md.acd_config import read_strengths_file
from psb_md.defaults import (
    FINAL_ACD_ORBIT_FOLDERS,
    MachineConfig,
    default_acd_measurement_dir,
)
from psb_md.defaults import campaign as psb_md_campaign

#: Where derived products live, beside the repository rather than on the mount.
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = REPO_ROOT / "data"

#: The four ring quadrupole trim circuits, off in every campaign; pinned so the sequence defaults cannot move the start model.
TRIMS_OFF: dict[str, float] = {
    "kbrqfcorr": 0.0,
    "kbrqdcorr": 0.0,
    "kbrqd3corr": 0.0,
    "kbrqd14corr": 0.0,
}


@dataclass(frozen=True)
class Campaign:
    """One machine state, named for the report; everything else from ``psb_md``."""

    slug: str
    label: str
    #: One sentence for the tab that opens with this campaign.
    summary: str
    machine_config: MachineConfig

    @property
    def acd_dirs(self) -> dict[str, Path]:
        """The AC-dipole acquisition folder of each orbit, keyed by folder name."""
        return {
            folder: default_acd_measurement_dir(orbit, self.machine_config)
            for orbit, folder in FINAL_ACD_ORBIT_FOLDERS.items()
        }

    @property
    def rf_offsets(self) -> tuple[float, ...]:
        """The RF-steering offsets the scan was run at, in mm."""
        return tuple(float(orbit) for orbit in sorted(FINAL_ACD_ORBIT_FOLDERS))

    @property
    def loco_dir(self) -> Path:
        return default_acd_measurement_dir(0, self.machine_config).parent / "loco"

    @property
    def measurements_path(self) -> Path:
        """The one folder every scan acquisition was saved to, whatever its RF offset."""
        return self.loco_dir / FINAL_ACD_ORBIT_FOLDERS[0]

    @property
    def scan_logs(self) -> dict[float, Path]:
        """The scan log of each RF offset: the single ``scan_*.jsonl`` in its folder."""
        logs = {}
        for orbit, folder in FINAL_ACD_ORBIT_FOLDERS.items():
            found = sorted((self.loco_dir / folder).glob("scan_*.jsonl"))
            if len(found) != 1:
                raise FileNotFoundError(
                    f"{self.slug}: expected one scan log in {self.loco_dir / folder}, "
                    f"found {len(found)}"
                )
            logs[float(orbit)] = found[0]
        return logs

    @property
    def chroma_file(self) -> Path:
        return psb_md_campaign(self.machine_config).chroma.file

    @property
    def quad_settings(self) -> dict[str, float]:
        """The quadrupole circuits the machine sat at, as MAD ``k1``, trims off."""
        strengths = psb_md_campaign(self.machine_config).strengths_files[0]
        return {**read_strengths_file(strengths), **TRIMS_OFF}

    @property
    def results_root(self) -> Path:
        """Where this campaign's single-momentum fits live."""
        return REPO_ROOT / "results" / f"matrix_{self.slug}"

    @property
    def optics_dir(self) -> Path:
        """Where the measured-optics products of this campaign are written."""
        return REPO_ROOT / "results" / "optics" / self.slug

    def cache_file(self, name: str) -> Path:
        """A parquet cache path, namespaced by campaign."""
        return CACHE_PATH / f"{self.slug}_{name}"

    def figures_dir(self, root: Path) -> Path:
        """Figure directory under *root*, one per campaign."""
        return root / self.slug


P23_P13_FINAL = Campaign(
    slug="p23_p13_final",
    label="Inverted tunes, 28th",
    summary=(
        "The 28th's inverted-tunes lattice, Qx above Qy, with nothing mis-trimmed: "
        "the baseline the other inverted-tunes configurations are compared against. "
        "The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics."
    ),
    machine_config=MachineConfig.P23_P13_FINAL,
)

P23_P13_FINAL_QDE14 = Campaign(
    slug="p23_p13_final_qde14",
    label="Inverted tunes, QDE14 error",
    summary=(
        "The 28th's inverted lattice again, with QDE14 (kbrqd14corr = "
        "+0.0073775865) deliberately mis-trimmed in LSA. The LOCO scan (all "
        "three RF offsets), the chroma and the AC-dipole optics were all "
        "retaken, and the model starts from its unperturbed circuits so LOCO "
        "has to find the error."
    ),
    machine_config=MachineConfig.P23_P13_FINAL_QDE14,
)

P23_P13_FINAL_QDE14_QDE3 = Campaign(
    slug="p23_p13_final_qde14_qde3",
    label="Inverted tunes, QDE14+QDE3 error",
    summary=(
        "The 28th's inverted lattice with both QDE14 and QDE3 deliberately "
        "mis-trimmed in LSA. The LOCO scan (all three RF offsets), the chroma "
        "and the AC-dipole optics were all retaken, and the model starts from "
        "its unperturbed circuits so LOCO has to find both errors."
    ),
    machine_config=MachineConfig.P23_P13_FINAL_QDE14_QDE3,
)

P23_P13_FINAL_SEXTS_ON = Campaign(
    slug="p23_p13_final_sexts_on",
    label="Inverted tunes, sextupoles on",
    summary=(
        "The 28th's inverted lattice with the ring sextupoles powered instead "
        "of off. The LOCO scan (all three RF offsets), the chroma and the "
        "AC-dipole optics were all retaken, and the model starts from its "
        "unperturbed circuits."
    ),
    machine_config=MachineConfig.P23_P13_FINAL_SEXTS_ON,
)

P17_P23_FINAL = Campaign(
    slug="p17_p23_final",
    label="Normal tunes, 29th",
    summary=(
        "The 29th's normal-tunes lattice, at the P17/P23 tune point and "
        "orbit-corrector set. The LOCO scan (all three RF offsets) and chroma "
        "were taken with the same layout as the 28th's inverted-tunes campaign."
    ),
    machine_config=MachineConfig.P17_P23_FINAL,
)

P17_P23_FINAL_QDE14 = Campaign(
    slug="p17_p23_final_qde14",
    label="Normal tunes, QDE14 error",
    summary=(
        "The 29th's normal lattice again, with QDE14 deliberately mis-trimmed "
        "in LSA. The LOCO scan (all three RF offsets) and this campaign's own "
        "driven-tune optics were retaken, as for the inverted-tunes QDE14 error."
    ),
    machine_config=MachineConfig.P17_P23_FINAL_QDE14,
)

P17_P23_FINAL_QDE14_QDE3 = Campaign(
    slug="p17_p23_final_qde14_qde3",
    label="Normal tunes, QDE14+QDE3 error",
    summary=(
        "The 29th's normal lattice with both QDE14 and QDE3 deliberately "
        "mis-trimmed in LSA. The LOCO scan (all three RF offsets) and this "
        "campaign's own driven-tune optics were retaken, as for the "
        "inverted-tunes QDE14+QDE3 error."
    ),
    machine_config=MachineConfig.P17_P23_FINAL_QDE14_QDE3,
)

P17_P23_FINAL_SEXTS_ON = Campaign(
    slug="p17_p23_final_sexts_on",
    label="Normal tunes, sextupoles on",
    summary=(
        "The normal lattice with the ring sextupoles powered instead of off, "
        "taken on the 30th after the 29th ran out of time. The LOCO scan (all "
        "three RF offsets), the chroma and this campaign's own driven-tune "
        "optics were all retaken."
    ),
    machine_config=MachineConfig.P17_P23_FINAL_SEXTS_ON,
)

#: The campaigns the inverted-tunes report pages tab between, in tab order.
INVERTED_PAGE_CAMPAIGNS: tuple[Campaign, ...] = (
    P23_P13_FINAL,
    P23_P13_FINAL_QDE14,
    P23_P13_FINAL_QDE14_QDE3,
    P23_P13_FINAL_SEXTS_ON,
)

#: The normal-tunes counterpart of INVERTED_PAGE_CAMPAIGNS.
NORMAL_PAGE_CAMPAIGNS: tuple[Campaign, ...] = (
    P17_P23_FINAL,
    P17_P23_FINAL_QDE14,
    P17_P23_FINAL_QDE14_QDE3,
    P17_P23_FINAL_SEXTS_ON,
)

CAMPAIGNS: dict[str, Campaign] = {
    campaign.slug: campaign
    for campaign in (*NORMAL_PAGE_CAMPAIGNS, *INVERTED_PAGE_CAMPAIGNS)
}


def campaign_by_slug(slug: str) -> Campaign:
    """Look a campaign up by slug, accepting the hyphenated CLI spelling."""
    key = slug.replace("-", "_")
    if key not in CAMPAIGNS:
        raise ValueError(
            f"Unknown campaign {slug!r}; expected one of {sorted(CAMPAIGNS)}"
        )
    return CAMPAIGNS[key]


def add_campaign_argument(
    parser, *, default: str = "p23_p13_final", multiple: bool = False
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
