"""One-off: build blank_acquisitions for p23_p13_final_sexts_on from the LOCO scan.

The campaign has no AC-dipole-off blanks, but every reset/offset_k=0 point in the scan logs is the
untrimmed machine (see loco_common.measured_response.read_scan_log). Those files live under loco/0mm
(loco_common.campaign.Campaign.measurements_path); this symlinks them into
blank_acquisitions/<orbit> so psb_md.defaults.default_blank_acd_measurement_dir resolves them.
"""

from __future__ import annotations

from pathlib import Path

from loco_common.campaign import Campaign
from loco_common.measured_response import find_scan_measurements, load_measurements, read_scan_log
from psb_md.defaults import (
    CERN_USER_MOUNT_ROOT,
    FINAL_ACD_ORBIT_FOLDERS,
    MachineConfig,
    campaign as psb_md_campaign,
)


def _mounted(path: Path) -> Path:
    if path.exists():
        return path
    return CERN_USER_MOUNT_ROOT / path.relative_to("/")


#: The mount is read-only, so the derived blank set lives here (psb_md.defaults overrides get_blank_dir to it).
LOCAL_BLANK_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    / "psb_md"
    / "data"
    / "p23_p13_final_sexts_on_blanks"
)

CAMPAIGN = Campaign(
    slug="p23_p13_final_sexts_on",
    label="Inverted tunes, sextupoles on",
    summary="",
    machine_config=MachineConfig.P23_P13_FINAL_SEXTS_ON,
)


def main() -> None:
    acd_root = psb_md_campaign(CAMPAIGN.machine_config).acd_root
    measurements = load_measurements(CAMPAIGN.measurements_path)
    print(f"{len(measurements)} acquisitions under {CAMPAIGN.measurements_path}")

    for orbit, folder in FINAL_ACD_ORBIT_FOLDERS.items():
        rf_offset = float(orbit)
        log_path = CAMPAIGN.scan_logs[rf_offset]
        entries = read_scan_log(log_path)
        points = find_scan_measurements(entries, measurements, rf_offset)
        blank_paths = sorted({p.path for p in points if p.offset_k == 0.0})
        print(f"{folder}: {len(blank_paths)} offset_k==0 acquisitions of {len(points)} total")

        blank_dir = LOCAL_BLANK_ROOT / folder
        blank_dir.mkdir(parents=True, exist_ok=True)
        existing = list(blank_dir.glob("*"))
        if existing:
            raise RuntimeError(f"{blank_dir} is not empty ({len(existing)} entries) -- aborting")

        for path in blank_paths:
            link = blank_dir / path.name
            # Target the canonical /user path; the sshfs mount path would dangle on the pipeline server.
            if path.is_relative_to(CERN_USER_MOUNT_ROOT):
                path = Path("/") / path.relative_to(CERN_USER_MOUNT_ROOT)
            link.symlink_to(path)
        print(f"  -> symlinked into {blank_dir}")


if __name__ == "__main__":
    main()
