# Conventions

Definitions needed to read the axes and tables on the results pages. Each is
pinned by a test; where a test and this page disagree, the test is right.

## Sign of the LSA corrector setting

`LSA_K_SIGN = {"x": -1.0, "y": 1.0}`, in `loco_common/naming.py`.

A horizontal corrector's LSA `/K` step produces the opposite kick to MAD's
`hkick` of the same sign. All six DHZ correlate at -0.998 against the model, all
six DVT at +0.999.

The response matrix alone cannot establish this: "LSA `/K` is inverted" and "the
BPM X reading is inverted" predict identical response matrices, because both
flip the same product. The dispersion orbit separates them, since no corrector
touches it. The measured horizontal dispersion tracks the model's with the
correct sign, so the BPM is right and the corrector setting is what is inverted.

Pinned by `tests/test_naming.py`.

## Chromaticity

`Q'H` and `Q'V` are `beta * dq / Q`, with `beta` from the beam energy. Every
chromaticity axis on this site is in that convention.

Pinned by `tests/test_chromaticity_convention.py`.

## Dispersion

MAD-NG twiss `dx` is `dx/dpt`. Measured dispersion on these pages is the slope
of each BPM's untrimmed closed orbits against the reconstructed momentum, over
the RF settings the campaign scanned.

## Reference orbit

Every acquisition — every corrector step, every RF setting — has the same orbit
subtracted: untrimmed, nominal RF. Not each RF setting referred to its own zero.
The model side therefore takes its reference at `pt = 0` rather than at the
worker's own momentum.

## Prior

`prior_strength` is 1e-4, per family rather than one global scalar. It is the
measured knee at 244 settings, not a tuning parameter.

## Absolute-orbit error floor

`--absolute-error-floor` is 1e-4 m, the BPM zero-offset systematic. It is the
line a closed-orbit residual is read against; the statistical bar on a measured
orbit is a standard error of the mean and is two orders of magnitude smaller.

## Machine-knob model

The machine-knob model is built on the machine's own circuit currents, as
extracted, and its tune is not matched to the measurement. Matching moves
`kbrqf` and `kbrqd`, which is the same lever a distributed gradient error pulls.
It is where every fit starts, and it is the dotted un-fitted curve on the
lattice figures. The "matched model" those figures are referred to is a separate
lattice with those two circuits matched to the measured tune. On disk and in the
scoreboard the machine-knob model is still keyed `start-model`.

## Corrector convention in xsuite

`knl[0] = -hkick`, `ksl[0] = +vkick`. Pinned by `tests/test_naming.py`.

## Method 1

Method 1 is a first-order response-matrix fit: one parametric twiss builds the
full `(2*N_BPM) x N_corrector` matrix, and every cell is one weighted
`MAD.match` equality against the same 32 cell-grouped `dk1l` knobs Method 2
lumps to. It reports no covariance, so its knobs carry no error bar and it does
not appear on any significance figure.
