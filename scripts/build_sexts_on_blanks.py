"""One-off: build blank_acquisitions for p23_p13_final_sexts_on from the LOCO scan.

This campaign never took a dedicated AC-dipole-off blank set. Its
blank_acquisitions/{m2mm,0mm,2mm} folders exist but are empty. The LOCO scan
recorded three RF-offset runs, and every reset/offset_k=0 point in each run's
scan log is, by construction, the untrimmed machine (see
loco_common.measured_response.read_scan_log) -- exactly what a blank
acquisition is. Those acquisitions all live physically under loco/0mm
(loco_common.campaign.Campaign.measurements_path), tagged by timestamp against
each RF offset's own scan_*.jsonl.

This symlinks the qualifying files into blank_acquisitions/<orbit> so
psb_md.defaults.default_blank_acd_measurement_dir resolves them normally, with
no change to psb_md itself and no copy of the real data.
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


#: The real-data mount is read-only for us, so the derived blank set lives here
#: instead of under blank_acquisitions/ on the mount. psb_md.defaults overrides
#: this campaign's get_blank_dir to point at it (see CampaignConfig.blank_dir_override).
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
            # Always target the canonical /user path: the pipeline runs on a
            # server that has /user but not the sshfs mount, so a mount-path
            # target would be a dangling link there.
            if path.is_relative_to(CERN_USER_MOUNT_ROOT):
                path = Path("/") / path.relative_to(CERN_USER_MOUNT_ROOT)
            link.symlink_to(path)
        print(f"  -> symlinked into {blank_dir}")


if __name__ == "__main__":
    main()
