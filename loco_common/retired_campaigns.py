"""The 2026-08-21 normal- and inverted-tunes scans, retired.

Superseded by the 2026-08-28 repeat; kept but out of ``CAMPAIGNS``/``PAGE_CAMPAIGNS``.
"""

from __future__ import annotations

from loco_common.campaign import (
    FIRST_PATH,
    CHROMA_PATH,
    SCAN_PATH,
    TRIMS_OFF,
    Campaign,
    MeasuredOptics,
)

NORMAL = Campaign(
    slug="normal",
    label="Normal tunes",
    summary=(
        "The machine as the MD found it: the horizontal tune below the vertical, "
        "Qx = 4.171 against Qy = 4.229. Every result published before the second "
        "configuration existed is this one."
    ),
    measurements_path=SCAN_PATH / "CO_measurements",
    scan_log=SCAN_PATH / "scan_20260821T091044.jsonl",
    delta_k=5e-5,
    quad_settings={
        "kbrqf": 0.7289003149414066,
        "kbrqd": -0.7442765966796879,
        **TRIMS_OFF,
    },
    optics=MeasuredOptics(
        legacy_driven={
            "init_tunes": (0.169, 0.233),
            "closer_drive": (0.1695, 0.2325),
        },
        acd_dirs={
            # "iniit_tunes" is the folder's real, misspelt name on the mount.
            "init_tunes": FIRST_PATH / "normal_tunes" / "iniit_tunes",
            "closer_drive": FIRST_PATH / "normal_tunes" / "closer_drive",
        },
        chroma_file=CHROMA_PATH / "normal_tunes.txt",
    ),
)

#: The same scan, an hour later, with QFO raised and QDE lowered so the two tunes
#: swap sides. The corrector settings were not touched.
INVERTED = Campaign(
    slug="inverted",
    label="Inverted tunes",
    summary=(
        "QFO raised and QDE lowered until the tunes swap sides: Qx = 4.233 above "
        "Qy = 4.128. The correctors were left where they were, so this is the same "
        "measurement of a different lattice."
    ),
    measurements_path=SCAN_PATH / "CO_measurements_inverted_tunes",
    scan_log=SCAN_PATH / "scan_20260821T115006.jsonl",
    delta_k=5e-5,
    quad_settings={
        "kbrqf": 0.7395237890625004,
        "kbrqd": -0.7377586523437502,
        **TRIMS_OFF,
    },
    optics=MeasuredOptics(
        legacy_driven={
            "init_tunes": (0.2296, 0.132),
            "closer_drive": (0.23, 0.1316),
        },
        acd_dirs={
            "init_tunes": FIRST_PATH / "inverted_tunes_optics" / "init_tunes",
            "closer_drive": FIRST_PATH / "inverted_tunes_optics" / "closer_drive",
        },
        chroma_file=CHROMA_PATH / "inverted_tunes.txt",
    ),
)
