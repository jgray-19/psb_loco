"""The acceptance comparison: two fitted response matrices against each other.

The model is stood up exactly as the drivers stand it up -- ``build_model`` plus
``GenericMadInterface`` with the campaign's tune and corrector knobs. Comparing
fitted knobs on a bare sequence instead silently evaluates them on a different
lattice.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
from aba_optimiser.accelerators import PSB as OptimiserPSB  # noqa: N811
from aba_optimiser.mad import GenericMadInterface

from loco_common.campaign import add_campaign_argument, campaign_by_slug
from loco_common.measured_response import cached_response
from loco_common.model import build_model
from loco_common.naming import lsa_to_element
from method1_madng_da.run_method1 import _matrices
from tests.madng_helpers import read_response, setup_response_da

#: build_model()'s default model directory does not currently exist, so the
#: sequence has to be named explicitly. See the handover notes.
SEQ = "/afs/cern.ch/work/j/jmgray/private/psb_md/models/reference/model_qx0.234255_qy0.127202_driven_qx0.230300_qy0.131200_dpp-3.850735e-06_state_tunematch/psb3_saved.seq"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sequence-file", default=SEQ)
add_campaign_argument(parser)
parser.add_argument(
    "--fits", nargs="+", default=None,
    help="LABEL=results/<dir>/knobs.csv pairs; defaults to every results/ dir found.",
)
parser.add_argument(
    "--bounds", type=float, nargs="+", default=[0.05],
    help=(
        "Relative k1 change(s) to count knobs against, as a diagnostic. Method 2 "
        "does not constrain the knobs at all, so this is a reading of the answer "
        "and not a bound either fit respected."
    ),
)
args = parser.parse_args()
campaign = campaign_by_slug(args.campaign)
model = build_model(sequence_file=args.sequence_file, campaign=campaign)
resp = cached_response(0.0, campaign=campaign)
corr = sorted(resp["CORRECTOR"].unique())
elements = [lsa_to_element(c) for c in corr]


def quad_elements(mad):
    mad.send("""
local names = {}
for _, element in loaded_sequence:iter() do
    if element.kind == 'quadrupole' then table.insert(names, element.name) end
end
py:send(names, true)
""")
    return [name for name in mad.recv() if name.upper().startswith(("BR.QFO", "BR.QDE"))]


def interface():
    """The drivers' model: campaign tune knobs and corrector settings applied."""
    acc = OptimiserPSB(ring=model.ring, sequence_file=model.sequence_file,
                       kinetic_energy=model.kinetic_energy)
    return GenericMadInterface(accelerator=acc,
                               tune_knobs=model.tune_knobs or None,
                               corrector_knobs=model.corrector_knobs or None)


iface = interface()
try:
    quads = quad_elements(iface.mad)
    nominal, lengths = {}, {}
    for name in quads:
        iface.mad.send(
            f"py:send({{loaded_sequence['{name}'].k1, loaded_sequence['{name}'].l}}, true)"
        )
        nominal[name], lengths[name] = map(float, iface.mad.recv())
    names, R_before = setup_response_da(iface, elements, [])
finally:
    iface.close()
R_before = np.asarray(R_before, float)


def response_with(knobs):
    ifc = interface()
    try:
        setup_response_da(ifc, elements, [])
        for name, value in knobs.items():
            base = name.removesuffix(".dk1l")
            targets = (
                [f"BR.QFO{name.split('CELL', 1)[1].split('.', 1)[0]}1",
                 f"BR.QFO{name.split('CELL', 1)[1].split('.', 1)[0]}2"]
                if ".QFOCELL" in name else [base]
            )
            for element in targets:
                k1 = nominal[element] + float(value) / lengths[element]
                ifc.mad.send(f"loaded_sequence['{element}'].k1 = {k1:.15e}")
        _, matrix = read_response(ifc)
    finally:
        ifc.close()
    return np.asarray(matrix, float)


def discover():
    """Every results/<dir>/knobs.csv, Method 1 first, labelled by directory."""
    found = []
    for d in sorted(pathlib.Path("results").glob("*/knobs.csv")):
        found.append((d.parent.name, str(d)))
    return sorted(found, key=lambda lp: lp[0] != "method1")


pairs = [tuple(f.split("=", 1)) for f in args.fits] if args.fits else discover()

fits = {}
for label, path in pairs:
    try:
        k = pd.read_csv(path).set_index("knob")["value"]
    except FileNotFoundError:
        continue
    fits[label] = {name: float(value) for name, value in k.items() if name.endswith(".dk1l")}

R = {label: response_with(k) for label, k in fits.items()}
T, W = _matrices(resp, names, corr)
m = W > 0


def rms(a):
    return float(np.sqrt((a[m] ** 2).mean()))


print("\nweighted residual RMS (sigma):")
print(f"  {'start model':28s} {rms(W * (R_before - T)):9.1f}")
for label, r in R.items():
    print(f"  {label:28s} {rms(W * (r - T)):9.1f}")

print(f"\nunweighted response error, |measured| rms = {rms(T):.3e} m/rad:")
print(f"  {'start model':28s} {rms(R_before - T) / rms(T) * 100:6.2f} %")
for label, r in R.items():
    print(f"  {label:28s} {rms(r - T) / rms(T) * 100:6.2f} %")

labels = list(R)
print("\nagreement between fits (correlation of the response change each made):")
for i, a in enumerate(labels):
    for b in labels[i + 1:]:
        da, db = (R[a] - R_before)[m], (R[b] - R_before)[m]
        print(f"  {a} vs {b}: corr {np.corrcoef(da, db)[0, 1]:+.4f}, "
              f"|dA-dB|/|dA| {rms(R[a] - R[b]) / rms(R[a] - R_before):.3f}")

nom = np.array([nominal[n] for n in quads])
print("\nfitted k1 changes, relative to nominal:")
deltas = {}
for label, k in fits.items():
    d = np.array([k.get(n, nominal[n]) - nominal[n] for n in quads])
    deltas[label] = d
    counts = " ".join(
        f"past {bound:.0%}: {(np.abs(d / nom) > bound * 0.98).sum():2d}/{len(d)}"
        for bound in args.bounds
    )
    print(f"  {label:28s} rms {np.sqrt(((d / nom) ** 2).mean()) * 100:5.2f} %, "
          f"max {np.abs(d / nom).max():6.2%}, {counts}")
for i, a in enumerate(labels):
    for b in labels[i + 1:]:
        print(f"  corr(dk1 {a}, dk1 {b}) = {np.corrcoef(deltas[a], deltas[b])[0, 1]:+.4f}")

print("\nper-corrector gain (lsq ratio measured/model):")
header = "  " + f"{'corrector':24s} {'start':>7s}" + "".join(f" {lab[:9]:>9s}" for lab in labels)
print(header)
for i, c in enumerate(corr):
    mi = m[:, i]
    if mi.sum() < 2:
        continue
    def g(r):
        return np.sum(T[mi, i] * r[mi, i]) / np.sum(r[mi, i] ** 2)
    print(f"  {c:24s} {g(R_before):7.3f}" + "".join(f" {g(R[lab]):9.3f}" for lab in labels))
