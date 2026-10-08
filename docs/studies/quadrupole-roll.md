# Quadrupole roll

Quadrupole rolls are a knob family: `<element>.tilt`, switched on with `--misalign quad:tilt`, shown as `t` in case names.

## Why

A delta orbit cannot see a quadrupole offset (a constant kick) but does see a roll: its skew kick goes as the beam position at the magnet, which the correctors change. In the absolute orbit, rolls feed vertical dispersion, which the other families cannot supply.

## Convention

- The knob is the element's `tilt` in rad, positive as in MAD's `tilt`. Through the deferred misalignment table, `dpsi` is bit-identical to rolling the element (`Dy` rms 0.3514 for both; dispersion vectors correlate at +1.0000).
- Setting `element.dpsi` without that table is a silent no-op.
- It is seeded at `tilt = 1e-9`: MAD-NG drops a zero-angle rotation, so its Jacobian column would be identically zero.
- It is not a skew multipole. `ksl[2] = k1·sin(2ψ)·L` gives a different vertical orbit (9.8e-4 against 1.389e-3 m) and a dispersion pattern anticorrelated with the true roll (-0.95).
- A rotation is not a length: priors are per family (`FAMILIES` in `poco/run_poco.py`, tilt 1e-2).
- Realistic scale 1e-4 to 3e-3 rad rms; above about 5 mrad Q2 moves by more than 0.02.

Pinned upstream by `tests/mad/test_psb_quad_tilt.py`; evidence in `scripts/check_quad_roll.py`.

## First result (`xy · k1+b+dy+t`, lumped)

Modelled vertical dispersion goes from 0.043 m to 0.137 m against 0.164 m measured, the first fitted model with vertical dispersion of the right size (the best of 57 earlier fits reached 0.013 m). The residual does not improve (0.175 → 0.199 m) and the correlation with the measured shape moves only from -0.15 to +0.12: rolls supply the amplitude, not yet its position around the ring.
