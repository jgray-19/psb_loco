"""Measured optics per campaign, against the LOCO start model and a tune-matched copy of it.

Per campaign:

1. driven tunes, re-measured from the AC-dipole acquisitions;
2. natural tunes and chromaticity, from the tune/chroma scan;
3. measured optics (beta from phase and amplitude, BPM-to-BPM phase advance,
   coupling RDTs) through ``psb_md``'s omc3 pipeline on
   :data:`PRODUCTION_PREPROCESSING`, equation-compensated to the free machine;
4. the same quantities from the un-matched LOCO start model and from that lattice
   matched to the measured tune.

Beta-beats are taken against the start model, the tune-matched lattice and omc3's model.

    uv run python scripts/measured_optics.py --campaign normal inverted

Products, per campaign, under ``results/optics/<slug>/``:

``<folder>/omc3_model/``   the matched analysis model omc3 needs
``<folder>/driven/``       harpy lin files and the uncompensated optics
``<folder>/free/``         the equation-compensated optics: the free machine
``measured.parquet``       per-BPM measured beta, all three model betas, all three beatings
``measured_phase.parquet`` per-BPM-pair measured phase advance, all three model advances, all three beatings
``summary.json``           every number the report pages quote
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tfs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loco_common.campaign import Campaign, add_campaign_argument, campaign_by_slug
from loco_common.chromaticity import chromaticity_from_dq_dpt
from loco_common.measured_response import (
    average_orbit_frames,
    cached_scan,
    measured_orbits,
)
from loco_common.model import DEFAULT_SEQUENCE_FILE, build_model, model_twiss
from loco_common.momentum import estimate_pt_by_rf_offset
from loco_common.optics_reproducibility import REPLICAS, apply_bootstrap_errors

logger = logging.getLogger(__name__)

from psb_md.acd_config import (  # noqa: E402
    orbit_driven_tune_and_dpp,
    orbit_natural_tunes,
)
from psb_md.defaults import (  # noqa: E402
    default_blank_acd_measurement_dir,
    folder_to_orbit_map,
)
from psb_md.preprocessing import TbtPreprocessing  # noqa: E402

#: Production chain from psb_md's ``ACD_PREPROCESSING_ORDER_REPORT.md`` section 1
#: (not the SSA-only ``TbtPreprocessing()`` default, which fails the AC-dipole consistency guard).
#: Blank-derived removals skip without AC-dipole-off blanks; the summary records which stages ran.
PRODUCTION_PREPROCESSING = TbtPreprocessing(
    demodulate=True,
    remove_energy_motion=True,
    remove_interference=True,
    cleaning_method="svd",
)

#: Turn window handed to harpy.
DEFAULT_START_TURN = 2500
DEFAULT_WINDOW = 7500


def build_accelerator(sequence_file: Path):
    """The MAD-NG accelerator ``read_chroma_summary`` needs for its ``dp2pt``/``beta``."""
    from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: PLC0415, N811

    return OptimiserPSB(ring=3, sequence_file=str(sequence_file), kinetic_energy=0.16)


def campaign_natural_tune(
    campaign: Campaign, sequence_file: Path = DEFAULT_SEQUENCE_FILE
) -> tuple[float, float]:
    """The campaign's natural tune, fitted live from its chroma export."""
    chroma = read_chroma_summary(campaign.chroma_file, build_accelerator(sequence_file))
    return (chroma["QH"], chroma["QV"])


def read_chroma_summary(path: Path, accelerator) -> dict[str, object]:
    """Fit natural tune and ``Q'`` directly from a full XImeter export.

    Each plane has one tune and one ``Dp/p`` column per ctime. ``Dp/p`` is first
    converted point-by-point with ``accelerator.dp2pt``; a line is then fitted
    with one shared slope and one intercept per ctime, producing measured
    MAD-NG-native ``dq1`` and ``dq2`` without allowing tune drift between ctimes
    to bias the slope. The slope's one-sigma error comes from the full
    least-squares covariance. The file's ``Xi`` summary is deliberately ignored.
    """
    lines = path.read_text().splitlines()
    result: dict[str, object] = {"source": str(path)}
    for word, tune_key, suffix in (("horizontal", "QH", "H"), ("vertical", "QV", "V")):
        start = lines.index(f"Details of used points for {word} plane:") + 1
        end = next(
            (i for i in range(start, len(lines)) if lines[i].startswith("Details of ")),
            len(lines),
        )
        rows = {tune_key: [], "Dp/p": []}
        for line in lines[start:end]:
            cells = [cell.strip() for cell in line.split(",")]
            if cells[0] in rows:
                values = [float(cell) for cell in cells[2:] if cell]
                if values:  # a fully blank point index (all ctimes empty) contributes nothing
                    rows[cells[0]].append(values)
        tunes = np.asarray(rows[tune_key])
        momentum = np.asarray(rows["Dp/p"])
        if tunes.shape != momentum.shape or tunes.ndim != 2:
            raise ValueError(f"Malformed {word} tune/Dp-p block in {path}")
        pt = np.vectorize(accelerator.dp2pt, otypes=[float])(momentum)
        slope, slope_error, intercepts = fit_chromaticity_all_ctimes(tunes, pt)
        result[f"DQ{suffix}_DPT"] = slope
        result[f"DQ{suffix}_DPT_error"] = slope_error
        result[f"QP{suffix}"] = accelerator.beta * slope
        result[f"QP{suffix}_error"] = accelerator.beta * slope_error
        result[tune_key] = float(intercepts.mean())
        result[f"{tune_key}_spread"] = float(np.ptp(intercepts))
        result[f"QP{suffix}_points"] = int(tunes.shape[1])
    return result


def fit_chromaticity_all_ctimes(tunes: np.ndarray,
                                pt: np.ndarray) -> tuple[float, float, np.ndarray]:
    """Common ``dQ/dpt`` plus one free natural-tune intercept per ctime."""
    rows, ctimes = tunes.shape
    design = np.zeros((rows * ctimes, ctimes + 1))
    design[np.arange(rows * ctimes), np.tile(np.arange(ctimes), rows)] = 1.0
    design[:, -1] = pt.reshape(-1)
    target = tunes.reshape(-1)
    parameters, _, _, _ = np.linalg.lstsq(design, target, rcond=None)
    residual = target - design @ parameters
    dof = target.size - parameters.size
    variance = float(residual @ residual / dof)
    covariance = variance * np.linalg.inv(design.T @ design)
    return float(parameters[-1]), float(np.sqrt(covariance[-1, -1])), parameters[:-1]


def closed_orbit_calibrated_chromaticity(
    campaign: Campaign, model
) -> tuple[list[float], list[float]]:
    """Fit the chroma tune points against ``pt`` inferred from closed orbits."""
    from psb_md.defaults import DPP_PER_MM
    from psb_md.tune_measurements import load_orbit_tune_table

    campaign_offsets = campaign.rf_offsets
    points, orbit_by_path = cached_scan(campaign=campaign)
    absolute = {}
    for offset in campaign_offsets:
        untrimmed = {
            key: frame
            for key, frame in measured_orbits(
                offset, points=points, orbit_by_path=orbit_by_path, delta=False
            ).items()
            if key[1] == 0.0
        }
        absolute[offset] = average_orbit_frames(list(untrimmed.values()))
    pt = estimate_pt_by_rf_offset(absolute, model_twiss(model, chrom=True))
    table = load_orbit_tune_table(
        campaign.chroma_file, dpp_per_index=DPP_PER_MM
    )
    offsets = np.asarray(campaign_offsets)
    momentum = np.asarray([pt[offset] for offset in offsets])[:, None]
    slopes = []
    errors = []
    for field in ("qx", "qy"):
        tunes = np.asarray([getattr(table[int(offset)], field) for offset in offsets])[:, None]
        slope, error, _ = fit_chromaticity_all_ctimes(tunes, momentum)
        slopes.append(slope)
        errors.append(error)
    return slopes, errors


def model_optics(
    campaign: Campaign,
    sequence_file: Path,
    *,
    match_to: tuple[float, float] | None = None,
) -> dict[str, object]:
    """One model lattice: beta at the BPMs, plus its tune and chromaticity.

    ``match_to=None`` is the fit start model; a measured tune moves ``kbrqf``/``kbrqd`` onto it.
    """
    from scripts.predict_loco import open_full_interface  # noqa: PLC0415

    model = build_model(sequence_file=sequence_file, campaign=campaign)
    interface = open_full_interface(model)
    try:
        # Create and zero every fitted family, as ``case_optics`` does.
        interface.update_knob_values(dict.fromkeys(interface.knob_names, 0.0))
        matched: dict[str, float] = {}
        if match_to is not None:
            matched = {
                str(name).lower(): float(value)
                for name, value in interface.match_tunes(*match_to).items()
            }
        # coupling=True adds the f1001/f1010 columns; chrom=True is unneeded (dq1/dq2 are exact).
        table = interface.run_twiss(observe=0, method=6, coupling=True)
    finally:
        interface.close()

    headers = dict(table.headers)
    frame = table.copy()
    frame.index = [str(name) for name in table.index]
    bpms = frame[frame.index.str.contains("BPM", case=False)]
    return {
        "bpms": bpms,
        "tunes": (float(headers["q1"]), float(headers["q2"])),
        "chromaticity": chromaticity_from_dq_dpt(headers),
        "dq_dpt": (float(headers["dq1"]), float(headers["dq2"])),
        "matched_knobs": matched,
    }


#: The betas omc3 writes and the column suffix of each; phase is primary, amplitude a BPM-gain check.
BETA_SOURCES = {"": "beta_phase", "_amp": "beta_amplitude"}


def measured_frame(free_dir: Path) -> pd.DataFrame:
    """Measured beta per BPM, both planes, from phase and from amplitude (missing files are skipped)."""
    frames = []
    for suffix, stem in BETA_SOURCES.items():
        for plane in ("x", "y"):
            path = free_dir / f"{stem}_{plane}.tfs"
            if not path.exists():
                logger.warning("%s missing; skipping that beta", path)
                continue
            table = tfs.read(path, index="NAME")
            upper = plane.upper()
            columns = {f"BET{upper}": f"beta_{plane}{suffix}"}
            for candidate in (f"ERRBET{upper}", f"STDBET{upper}"):
                if candidate in table.columns:
                    columns[candidate] = f"beta_{plane}{suffix}_err"
                    break
            # The model column is identical in both files; keep the phase one.
            if not suffix and f"BET{upper}MDL" in table.columns:
                columns[f"BET{upper}MDL"] = f"beta_{plane}_omc3_model"
            frames.append(table.rename(columns=columns)[list(columns.values())])
    merged = pd.concat(frames, axis=1)
    merged.index.name = "NAME"
    return merged


#: Coupling RDTs omc3 writes: ``f1001`` (difference, driven by quadrupole roll), ``f1010`` (sum, control).
COUPLING_RDTS = {"f1001": "f1001", "f1010": "f1010"}


def coupling_frame(free_dir: Path) -> pd.DataFrame | None:
    """Measured coupling RDT amplitudes per BPM, indexed like :func:`measured_frame`; ``None`` if absent."""
    blocks = []
    for stem, name in COUPLING_RDTS.items():
        path = free_dir / f"{stem}.tfs"
        if not path.exists():
            logger.warning("%s missing; skipping that coupling RDT", path)
            continue
        table = tfs.read(path, index="NAME")
        columns = {"AMP": name, "ERRAMP": f"{name}_err", "AMPMDL": f"{name}_omc3_model"}
        present = {k: v for k, v in columns.items() if k in table.columns}
        blocks.append(table.rename(columns=present)[list(present.values())])
    if not blocks:
        return None
    merged = pd.concat(blocks, axis=1)
    merged.index.name = "NAME"
    return merged


def measured_optics_frame(free_dir: Path) -> pd.DataFrame:
    """Beta and the coupling RDTs; what the kick bootstrap resamples (omc3's ``ERRAMP`` is zero)."""
    frame = measured_frame(free_dir)
    coupling = coupling_frame(free_dir)
    return frame if coupling is None else frame.join(coupling, how="left")


def phase_advance_frame(free_dir: Path) -> dict[str, float]:
    """RMS disagreement in BPM-to-BPM phase advance, measurement against omc3's model."""
    result = {}
    for plane in ("x", "y"):
        table = tfs.read(free_dir / f"phase_{plane}.tfs")
        upper = plane.upper()
        if f"PHASE{upper}" not in table.columns or f"PHASE{upper}MDL" not in table.columns:
            continue
        difference = table[f"PHASE{upper}"] - table[f"PHASE{upper}MDL"]
        # Advance is modulo one turn.
        wrapped = (difference + 0.5) % 1.0 - 0.5
        result[f"phase_advance_rms_{plane}"] = float(np.sqrt(np.mean(wrapped**2)))
    return result


def measured_tunes(free_dir: Path) -> dict[str, float]:
    """Harpy's own tune headers, as a cross-check on the chroma scan."""
    tunes = {}
    for plane, key in (("x", "Q1"), ("y", "Q2")):
        table = tfs.read(free_dir / f"beta_phase_{plane}.tfs")
        for header, name in ((key, f"driven_q{plane}"), (f"NAT{key}", f"natural_q{plane}")):
            if header in table.headers:
                tunes[name] = float(table.headers[header])
    return tunes


def preprocessing_for(args: argparse.Namespace) -> TbtPreprocessing:
    """The production chain, with any stage the caller switched off removed."""
    from dataclasses import replace  # noqa: PLC0415

    return replace(
        PRODUCTION_PREPROCESSING,
        demodulate=not args.no_demodulate,
        remove_energy_motion=not args.no_energy_motion,
        remove_interference=not args.no_interference,
        cleaning_method=args.tbt_cleaning,
    )


#: Turns averaged for the folder-placement check (a wrong folder is a ~1.2e-3 dp/p step).
MOMENTUM_CHECK_TURNS = 1000
MOMENTUM_CHECK_TOLERANCE = 3e-4


def check_acd_folder_momenta(campaign: Campaign, model, *, limit: int | None = None) -> None:
    """Each AC-dipole folder's closed orbit must match its scan point's dp/p (relative to the measured 0 mm orbit)."""
    from psb_md.measurements import compute_closed_orbit_dataframe  # noqa: PLC0415

    orbits: dict[float, pd.DataFrame] = {}
    expected_dpp: dict[float, float] = {}
    for name, folder in campaign.acd_dirs.items():
        orbit_mm = float(folder_to_orbit_map()[name])
        _, expected_dpp[orbit_mm] = orbit_driven_tune_and_dpp(
            int(orbit_mm), campaign.machine_config
        )
        files = sorted(folder.glob("*.sdds"))[: limit or None]
        frame = compute_closed_orbit_dataframe(files, max_turns=MOMENTUM_CHECK_TURNS)
        orbits[orbit_mm] = pd.DataFrame(
            {"X": frame["mean_x"].to_numpy(float), "Y": frame["mean_y"].to_numpy(float)},
            index=pd.Index(frame["name"].astype(str), name="name"),
        )
    if 0.0 not in orbits:
        logger.warning(
            "%s: no 0 mm AC-dipole folder, so the momentum reference is missing "
            "and the folder-placement check is skipped",
            campaign.slug,
        )
        return

    accelerator = build_accelerator(model.sequence_file)
    estimated = estimate_pt_by_rf_offset(orbits, model_twiss(model, chrom=True))
    reference = expected_dpp[0.0]
    wrong = []
    for orbit_mm in sorted(orbits):
        # Rebase to the 0 mm plateau before converting.
        relative = (1.0 + expected_dpp[orbit_mm]) / (1.0 + reference) - 1.0
        expected_pt = float(accelerator.dp2pt(relative))
        difference = estimated[orbit_mm] - expected_pt
        logger.info(
            "%s: %+g mm orbit -> pt %+.3e measured, %+.3e expected (%+.3e apart)",
            campaign.slug, orbit_mm, estimated[orbit_mm], expected_pt, difference,
        )
        if abs(difference) > MOMENTUM_CHECK_TOLERANCE:
            wrong.append(
                f"{orbit_mm:+g} mm: expected dp/p {expected_pt:+.3e}, "
                f"closed orbit gives {estimated[orbit_mm]:+.3e}"
            )
    if wrong:
        raise ValueError(
            f"{campaign.slug}: AC-dipole folders disagree with the momentum their "
            "scan point claims, which is what a folder saved to the wrong place "
            "looks like -- " + "; ".join(wrong)
        )


def analyse_folder(
    campaign: Campaign,
    name: str,
    folder: Path,
    args: argparse.Namespace,
    *,
    optics: bool,
) -> dict[str, object]:
    """One driven-tune setting: the drive always, the (hour-long) optics chain only if *optics*."""
    from psb_md.driven_tune_measurement import (
        measure_folder_driven_tunes,  # noqa: PLC0415
    )
    from psb_md.hio_analysis import (  # noqa: PLC0415
        create_omc3_model,
        infer_ac_dipole_window,
        run_acd_phase_analysis,
        run_driven_compensated_optics_from_lin_files,
    )

    root = campaign.optics_dir / name
    model_dir, driven_dir, free_dir = root / "omc3_model", root / "driven", root / "free"
    root.mkdir(parents=True, exist_ok=True)

    # Both tunes come from the same per-orbit scan point (natural tune moves ~2e-3 per mm).
    orbit = folder_to_orbit_map()[name]
    natural = orbit_natural_tunes(orbit, campaign.machine_config)
    configured, _ = orbit_driven_tune_and_dpp(orbit, campaign.machine_config)
    # Configured tunes only locate the AC-dipole BPM window; rebuilt on the measured drive below.
    create_omc3_model(model_dir, nat_tunes=natural, drv_tunes=configured, force=args.force)
    _, first_bpm_after_acd = infer_ac_dipole_window(model_dir, "BR3.DES3L1")
    drive = measure_folder_driven_tunes(
        folder, configured,
        machine_config=campaign.machine_config,
        orbit=orbit,
        first_bpm_after_acd=first_bpm_after_acd,
        preprocessing=preprocessing_for(args),
        limit=args.limit,
    )
    measured_drive = (drive["measured_qxd"], drive["measured_qyd"])
    logger.info(
        "%s/%s: drive measured at %.6f / %.6f (spread %.6f / %.6f) "
        "(configured %.4f / %.4f) over %d files",
        campaign.slug, name,
        *measured_drive, drive["spread_qxd"], drive["spread_qyd"], *configured, drive["files"],
    )

    if not optics:
        logger.info("%s/%s: drive only, no optics chain", campaign.slug, name)
    elif args.force or not (free_dir / "beta_phase_x.tfs").exists():
        create_omc3_model(model_dir, nat_tunes=natural, drv_tunes=measured_drive, force=args.force)
        files = sorted(folder.glob("*.sdds"))[: args.limit or None]
        run_acd_phase_analysis(
            files,
            model_dir,
            driven_dir,
            machine_config=campaign.machine_config,
            orbit=orbit,
            nat_tunes=natural,
            drv_tunes=measured_drive,
            start_turn=args.start_turn,
            window=args.window,
            preprocessing=preprocessing_for(args),
        )
        run_driven_compensated_optics_from_lin_files(
            driven_dir / "lin_files", model_dir, free_dir, compensation="equation"
        )
    else:
        logger.info("%s/%s: compensated optics already present, reusing", campaign.slug, name)

    blanks = default_blank_acd_measurement_dir(campaign.machine_config, orbit)
    analysed = (free_dir / "beta_phase_x.tfs").exists()
    return {
        "folder": str(folder),
        "drive": drive,
        "optics": analysed,
        "preprocessing": preprocessing_for(args).describe(),
        "blank_acquisitions": str(blanks),
        **({"harpy_tunes": measured_tunes(free_dir)} if analysed else {}),
        **(phase_advance_frame(free_dir) if analysed else {}),
        "free_dir": str(free_dir),
    }


def beat_statistics(measured: pd.Series, model: pd.Series) -> dict[str, float]:
    """``beta/beta_model - 1`` as rms and peak, over the BPMs both frames carry."""
    common = measured.index.intersection(model.index)
    beat = (measured.loc[common] / model.loc[common] - 1.0).astype(float)
    return {
        "rms": float(np.sqrt(np.mean(beat**2))),
        "max": float(np.max(np.abs(beat))),
        "bpms": int(len(common)),
    }


def phase_beat_statistics(measured: pd.Series, model: pd.Series) -> dict[str, float]:
    """``measured - model`` phase advance as rms and peak, in units of 2π (wrapped)."""
    common = measured.index.intersection(model.index)
    difference = (measured.loc[common] - model.loc[common]).astype(float)
    wrapped = (difference + 0.5) % 1.0 - 0.5
    return {
        "rms": float(np.sqrt(np.mean(wrapped**2))),
        "max": float(np.max(np.abs(wrapped))),
        "bpms": int(len(common)),
    }


def phase_beat_frame(free_dir: Path, bpms_by_model: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    """BPM-to-BPM phase advance, measured against every reference model, indexed by ``NAME2``.

    omc3's model advance is its ``PHASE{X,Y}MDL`` column; the others come from each model's ``mu1``/``mu2``.
    """
    blocks = []
    for plane, mu_column in (("x", "mu1"), ("y", "mu2")):
        upper = plane.upper()
        path = free_dir / f"phase_{plane}.tfs"
        if not path.exists():
            continue
        table = tfs.read(path, index="NAME2")
        if f"PHASE{upper}" not in table.columns:
            continue
        name1 = table["NAME"]
        block = pd.DataFrame(
            {
                f"phase_{plane}": table[f"PHASE{upper}"],
                f"phase_{plane}_err": table.get(f"ERRPHASE{upper}"),
                f"phase_{plane}_omc3_model": table.get(f"PHASE{upper}MDL"),
            }
        )
        for reference_model, bpms in bpms_by_model.items():
            if mu_column not in bpms.columns:
                continue
            mu = bpms[mu_column]
            advance = (mu.reindex(table.index).to_numpy() - mu.reindex(name1).to_numpy()) % 1.0
            block[f"phase_{plane}_{reference_model}"] = advance
        blocks.append(block)
    if not blocks:
        return None
    return pd.concat(blocks, axis=1)


def analyse_campaign(campaign: Campaign, args: argparse.Namespace) -> dict[str, object]:
    accelerator = build_accelerator(args.sequence_file)
    chroma = read_chroma_summary(campaign.chroma_file, accelerator)
    measured_natural = (chroma["QH"], chroma["QV"])
    measured_chroma = (chroma["QPH"], chroma["QPV"])

    # Reference folder: named, or the one with the most acquisitions.
    files_per_folder = {
        name: len(sorted(folder.glob("*.sdds")))
        for name, folder in campaign.acd_dirs.items()
    }
    reference = args.reference or max(files_per_folder, key=files_per_folder.get)
    if reference not in campaign.acd_dirs:
        raise SystemExit(
            f"--reference {reference!r} is not a folder of the {campaign.slug} campaign; "
            f"expected one of {sorted(campaign.acd_dirs)}"
        )
    loco_model = build_model(sequence_file=args.sequence_file, campaign=campaign)
    check_acd_folder_momenta(campaign, loco_model, limit=args.limit)
    folders = {
        name: analyse_folder(
            campaign, name, folder, args,
            optics=args.optics_folders == "all" or name == reference,
        )
        for name, folder in campaign.acd_dirs.items()
    }

    # Fit start model, and the same lattice tune-matched.
    start = model_optics(campaign, args.sequence_file)
    matched = model_optics(campaign, args.sequence_file, match_to=measured_natural)
    measured_chroma_error = (chroma["QPH_error"], chroma["QPV_error"])
    orbit_dq_dpt, orbit_dq_dpt_error = closed_orbit_calibrated_chromaticity(
        campaign, loco_model
    )
    free_dir = Path(folders[reference]["free_dir"])
    measured = measured_optics_frame(free_dir)
    # omc3's bar is too small on beta and zero on the RDTs; add the kick bootstrap (0 replicas keeps omc3's).
    if args.bootstrap_replicas:
        measured = apply_bootstrap_errors(
            measured,
            campaign.optics_dir / reference,
            measured_optics_frame,
            replicas=args.bootstrap_replicas,
        )

    model_beta = pd.DataFrame(
        {
            "beta_x_loco_model": start["bpms"]["beta11"].astype(float),
            "beta_y_loco_model": start["bpms"]["beta22"].astype(float),
            "beta_x_matched_model": matched["bpms"]["beta11"].astype(float),
            "beta_y_matched_model": matched["bpms"]["beta22"].astype(float),
        }
    )
    model_coupling = pd.DataFrame({
        f"{name}_{reference_model}": np.abs(bpms[name].to_numpy())
        for name in COUPLING_RDTS.values()
        for reference_model, bpms in (
            ("loco_model", start["bpms"]), ("matched_model", matched["bpms"])
        )
        if name in bpms.columns
    }, index=start["bpms"].index)
    frame = measured.join(model_beta, how="left").join(model_coupling, how="left")
    for suffix in BETA_SOURCES:
        for plane in ("x", "y"):
            if f"beta_{plane}{suffix}" not in frame.columns:
                continue
            for reference_model in ("loco_model", "matched_model", "omc3_model"):
                column = f"beta_{plane}_{reference_model}"
                if column in frame.columns:
                    frame[f"beat_{plane}{suffix}_{reference_model}"] = (
                        frame[f"beta_{plane}{suffix}"] / frame[column] - 1.0
                    )
    campaign.optics_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(campaign.optics_dir / "measured.parquet")

    phase_frame = phase_beat_frame(
        free_dir, {"loco_model": start["bpms"], "matched_model": matched["bpms"]}
    )
    if phase_frame is not None:
        phase_frame.to_parquet(campaign.optics_dir / "measured_phase.parquet")

    summary: dict[str, object] = {
        "campaign": campaign.slug,
        "label": campaign.label,
        "quad_settings": campaign.quad_settings,
        "measured": {
            "natural_tunes": list(measured_natural),
            "natural_tune_spread": [chroma["QH_spread"], chroma["QV_spread"]],
            "dq_dpt": [chroma["DQH_DPT"], chroma["DQV_DPT"]],
            "dq_dpt_error": [chroma["DQH_DPT_error"], chroma["DQV_DPT_error"]],
            "dq_dpt_closed_orbit": orbit_dq_dpt,
            "dq_dpt_closed_orbit_error": orbit_dq_dpt_error,
            "qprime": list(measured_chroma),
            "qprime_error": list(measured_chroma_error),
            "chroma_file": chroma["source"],
        },
        "loco_model": {
            "tunes": list(start["tunes"]),
            "sequence_file": str(args.sequence_file),
            "matched": False,
            "tune_error": [
                start["tunes"][0] - measured_natural[0],
                start["tunes"][1] - measured_natural[1],
            ],
            "qprime": list(start["chromaticity"]),
            "dq_dpt": list(start["dq_dpt"]),
        },
        "matched_model": {
            "tunes": list(matched["tunes"]),
            "matched": True,
            "matched_to": list(measured_natural),
            "quad_settings": matched["matched_knobs"],
            "qprime": list(matched["chromaticity"]),
            "dq_dpt": list(matched["dq_dpt"]),
        },
        "folders": folders,
        "reference_folder": reference,
        "beta_beat": {
            plane: {
                f"vs_{reference_model}": beat_statistics(
                    frame[f"beta_{plane}"], frame[f"beta_{plane}_{reference_model}"]
                )
                for reference_model in ("loco_model", "matched_model", "omc3_model")
                if f"beta_{plane}_{reference_model}" in frame.columns
            }
            for plane in ("x", "y")
        },
        # Kept separate from ``beta_beat``: amplitude and phase beta are not interchangeable.
        "beta_beat_amplitude": {
            plane: {
                f"vs_{reference_model}": beat_statistics(
                    frame[f"beta_{plane}_amp"], frame[f"beta_{plane}_{reference_model}"]
                )
                for reference_model in ("loco_model", "matched_model", "omc3_model")
                if f"beta_{plane}_{reference_model}" in frame.columns
            }
            for plane in ("x", "y")
            if f"beta_{plane}_amp" in frame.columns
        },
        # BPM-gain check: a calibration error moves only the amplitude beta.
        "phase_vs_amplitude": {
            plane: beat_statistics(frame[f"beta_{plane}_amp"], frame[f"beta_{plane}"])
            for plane in ("x", "y")
            if f"beta_{plane}_amp" in frame.columns
        },
        "phase_beat": (
            {
                plane: {
                    f"vs_{reference_model}": phase_beat_statistics(
                        phase_frame[f"phase_{plane}"],
                        phase_frame[f"phase_{plane}_{reference_model}"],
                    )
                    for reference_model in ("loco_model", "matched_model", "omc3_model")
                    if f"phase_{plane}_{reference_model}" in phase_frame.columns
                }
                for plane in ("x", "y")
                if f"phase_{plane}" in phase_frame.columns
            }
            if phase_frame is not None
            else {}
        ),
    }
    (campaign.optics_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    logger.info(
        "%s: model tune %.4f / %.4f against a machine measured at %.4f / %.4f "
        "(%+.4f / %+.4f); beta-beat vs the LOCO model %.1f%% / %.1f%% rms, vs the "
        "same lattice matched to the measured tune %.1f%% / %.1f%% rms",
        campaign.slug,
        *start["tunes"],
        *measured_natural,
        *summary["loco_model"]["tune_error"],
        100 * summary["beta_beat"]["x"]["vs_loco_model"]["rms"],
        100 * summary["beta_beat"]["y"]["vs_loco_model"]["rms"],
        100 * summary["beta_beat"]["x"]["vs_matched_model"]["rms"],
        100 * summary["beta_beat"]["y"]["vs_matched_model"]["rms"],
    )
    logger.info(
        "%s: dq1/dq2 = dQ/dpt measured %.3f / %.3f, model %.3f / %.3f",
        campaign.slug,
        chroma["DQH_DPT"],
        chroma["DQV_DPT"],
        *start["dq_dpt"],
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_campaign_argument(parser, multiple=True)
    parser.add_argument("--sequence-file", type=Path, default=DEFAULT_SEQUENCE_FILE)
    parser.add_argument("--start-turn", type=int, default=DEFAULT_START_TURN)
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Use only the first N acquisitions of each folder; 0 (the default) uses all.",
    )
    parser.add_argument(
        "--reference", default=None,
        help="Which driven-tune folder the published optics come from; default is "
             "whichever has the most acquisitions.",
    )
    parser.add_argument("--no-demodulate", action="store_true",
                        help="Skip dividing out the drive's amplitude envelope.")
    parser.add_argument("--no-energy-motion", action="store_true",
                        help="Skip the dispersive-ripple removal.")
    parser.add_argument("--no-interference", action="store_true",
                        help="Skip the per-BPM hardware-line removal.")
    parser.add_argument(
        "--tbt-cleaning", default=PRODUCTION_PREPROCESSING.cleaning_method,
        choices=("ssa", "svd", "intra-average", "none"),
        help="Denoising axis; the production chain's is SSA, per BPM.",
    )
    parser.add_argument(
        "--optics-folders", choices=("reference", "all"), default="reference",
        help="Run the harpy/omc3 chain on the reference folder only (the default, "
             "about an hour) or on every driven-tune folder.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Rebuild the omc3 model and rerun harpy even if the optics are already there.",
    )
    parser.add_argument(
        "--bootstrap-replicas", type=int, default=REPLICAS,
        help="Kick resamples behind the measured optics error bars; 0 keeps omc3's own.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    for slug in args.campaign:
        analyse_campaign(campaign_by_slug(slug), args)


if __name__ == "__main__":
    main()
