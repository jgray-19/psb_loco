# Spec: quadrupole roll (`dpsi`) as a knob family in `aba_optimiser`

**For:** whoever implements this in `aba_optimiser`.
**Written from:** `psb_loco`, which cannot edit `aba_optimiser` itself.
**Status:** **implemented upstream, 2026-08-23.** Kept as the record of why the
family exists and what was checked before it did.

Two things landed differently from the request below, and the differences are
worth knowing when reading the rest of this document:

* The knob is the element's **`tilt`**, not a `dpsi` misalignment, and the
  switch is **`optimise_quad_tilt`**. §3 of this document is what justifies the
  substitution: it measured that rolling the element and applying `dpsi` through
  the deferred misalignment table are the same thing.
* The knob is seeded at `tilt = 1e-9` rather than exactly zero, because MAD-NG
  drops a zero-angle rotation entirely and the Jacobian column would come back
  identically zero.

Pinned upstream by `tests/mad/test_psb_quad_tilt.py` and
`test_quadrupole_tilts_recovered_from_vertical_dispersion`; reachable from here
as `run_method2.py --optimise-quad-tilt`, and fitted as the `t` family on the
report pages.

**First result on the real data** (`xy · k1+b+dy+t`, offsets and rolls lumped to
32): the argument in §2 holds on magnitude and fails on shape. Modelled vertical
dispersion goes from 0.043 m (start model) to **0.137 m** against a measured
0.164 m — the first time any fitted model has produced vertical dispersion of
the right size, where the best of the previous 57 managed 0.013 m. But the
residual does not improve (0.175 m -> 0.199 m) and the correlation with the
measured shape only moves from -0.15 to +0.12. Rolls supply the amplitude the
other families cannot; they do not yet put it in the right place around the
ring.

**Size:** small. The mechanism already existed for `dx`/`dy`.

---

## 1. What is being asked for

A new optimisable knob family: **rotation of a quadrupole about the beam axis**,
`dpsi`, alongside the existing `dx` and `dy` misalignment knobs. One knob per
energised quadrupole, named `<element>.dpsi`, in radians, with exact TPSA
gradients like every other knob.

The accelerator-level switch is `optimise_quad_dpsi`, matching
`optimise_quad_dx` / `optimise_quad_dy`.

---

## 2. Why — the measurement that needs it

PSB ring 3, 2026-08-21. A sweep of all 60 LOCO option combinations in `psb_loco`
produced 57 fitted models, and **every one of them fails on vertical dispersion**:

| quantity | measured | best of 57 fitted models | start model |
|---|---|---|---|
| vertical dispersion, rms | **0.164 m** | 0.013 m | 0.043 m |
| vertical closed orbit, rms | 1.42e-3 m | 1.415e-3 m (0.2 % residual) | 1.16e-3 m |
| horizontal dispersion, rms | 2.90 m | 2.89 m | 2.89 m |

The best models reproduce the vertical *orbit* to 0.2 % and simultaneously get
the vertical *dispersion* three times **smaller** than the start model, i.e. they
move away from the measurement while fitting it.

The reason is that every knob family currently available — quadrupole `dy`,
dipole `k0`, the orbit correctors — is a **vertical bending** source. Such a
source generates vertical dispersion only through the vertical orbit it also
generates, so matching a 1.4 mm orbit caps the dispersion it can produce. The
measurement needs `Dy/Dx = 0.164/2.90 = 5.7 %` of **coupling**, which is a skew
quadrupole, and there is no skew degree of freedom in the fit.

Two cheaper explanations were tested and eliminated:

- **Dipole roll.** At a realistic 1 mrad it gives `Dy` = 0.117 m, but drags the
  vertical orbit to 2.9e-3 m — already 2.1× the measured value, and the orbit
  grows faster than the dispersion does. It cannot reach 0.164 m without putting
  the vertical orbit far outside what was measured.
- **The three PSB skew-quadrupole circuits** (`kbr3qskh0`, `kbr3qsk210l3`,
  `kbr3qsk614l3`). Right magnitude, wrong shape — and the machine's power
  converters read 0.01 A, 0.00 A and −0.00 A against a 1200 A range, so they
  were genuinely off. The model's zero is correct.

Quadrupole roll at ψ_rms ≈ 1–3 mrad reproduces **both** numbers at once, the
exact figure depending on the pattern. Over six random roll patterns at 3 mrad:
`Dy` = 0.16–0.40 m, vertical orbit 0.9–1.4e-3 m, horizontal dispersion and both
tunes unchanged. The per-BPM shape
is reachable too — correlation against the measured `Dy` pattern ran from −0.81
to +0.89 across those seeds by chance alone.

That is a hypothesis, not a result. Confirming or killing it requires **fitting**
the rolls, which is what this spec is for.

---

## 3. Feasibility, already verified

Run on the ring-3 lattice with `GenericMadInterface`, 48 quadrupoles, ψ_rms =
3 mrad, one random pattern. These are section 3 of
`psb_loco/scripts/check_quad_roll.py` and are what it prints.

| what was done | `Dy` rms | vertical orbit rms | ΔQ2 |
|---|---|---|---|
| baseline | 0.0428 | 1.157e-3 | — |
| set `e.dpsi`, **no misalign table** | 0.0428 | 1.157e-3 | 0.0000 |
| set `e.dpsi`, misalign table carrying `dpsi` | **0.3514** | **1.234e-3** | −0.0001 |
| set `element.tilt` (reference) | **0.3514** | **1.234e-3** | −0.0001 |

Two things follow, and they are the whole basis of this spec:

1. **`dpsi` through the deferred misalignment table is bit-identical to rolling
   the element.** Not approximately — the per-BPM dispersion vectors correlate at
   **+1.0000** and every scalar agrees to the printed digits. So `dpsi` needs no
   new physics in MAD-NG; it needs to be routed the way `dx`/`dy` already are.
2. **Setting `e.dpsi` without the misalignment table is a silent no-op.** No
   error, no warning, no effect. This is the same trap `dy` already has, and it
   is why §7 asks for a test that would catch it.

A skew-multipole approximation (`ksl[2] = k1·sin(2ψ)·L`) was tried separately and
is **not** equivalent, though it reaches a similar `Dy`: on the same pattern it
gave a different vertical closed orbit (9.8e-4 against 1.389e-3 m) and a
dispersion pattern anticorrelated with the true roll (−0.95), because it carries
the skew gradient but not the rolled normal gradient's feed-down of the
horizontal orbit. Do not implement the roll as a skew multipole. (This one case
is not in the script; the two `dpsi`/`tilt` rows above are.)

---

## 4. Implementation

### 4.1 `accelerators/base.py:14` — admit the attribute

```python
_MISALIGNMENT_ATTRIBUTES = frozenset({"dx", "dy", "dpsi"})
```

### 4.2 `accelerators/base.py:198` — `prepare_mad_for_knob_creation`

Currently hard-codes the attribute pair:

```python
grouped.setdefault(kind, {"dx": [], "dy": []})[attr].append(pattern)
```

and then calls `_prepare_misalignments_for_kind(..., dx_patterns=…, dy_patterns=…)`.
Generalise both to an attribute → patterns mapping so a fourth attribute is a
one-line change rather than another edit here:

```python
grouped.setdefault(kind, {}).setdefault(attr, []).append(pattern)
...
for element_kind, patterns in grouped.items():
    self._prepare_misalignments_for_kind(
        mad_iface,
        element_kind,
        {attr: tuple(values) for attr, values in patterns.items()},
    )
```

### 4.3 `accelerators/base.py:218` — `_prepare_misalignments_for_kind`

The Lua block must seed every requested attribute and put all of them in the
deferred table. An element matched for `dpsi` only must still get `dx`/`dy`
seeded, because `MAD.typeid.deferred` replaces the whole table:

```python
def _prepare_misalignments_for_kind(
    self,
    mad_iface: GradientDescentMadInterface,
    element_kind: str,
    patterns_by_attr: dict[str, tuple[str, ...]],
) -> None:
    """Attach MAD-NG deferred misalignment tables to one kind of element.

    Every misalignment attribute is seeded and deferred, not only the ones with
    knobs: ``MAD.typeid.deferred`` replaces the element's misalignment table
    wholesale, so an attribute left out of it is silently pinned at zero for the
    rest of the run.
    """
    patterns = tuple(dict.fromkeys(p for ps in patterns_by_attr.values() for p in ps))
    if not patterns:
        return

    attrs = sorted(_MISALIGNMENT_ATTRIBUTES)
    seed = "\n".join(f"                        e.{a} = e.{a} or 0" for a in attrs)
    deferred = ", ".join(f"{a} =\\\\->e.{a}" for a in attrs)

    mad_iface.mad.send(f"""
    local element_kind = {mad_iface.py_name}:recv()
    local patterns = {mad_iface.py_name}:recv()
    for i, e in loaded_sequence:siter(magnet_range) do
        if e.kind == element_kind then
            for _, pattern in ipairs(patterns) do
                if string.match(e.name, pattern) then
{seed}
                    e.misalign = MAD.typeid.deferred{{{deferred}}}
                    break
                end
            end
        end
    end
    """)
    mad_iface.mad.send(element_kind).send(patterns)
```

The `tblcat` import and the two-list `recv` go away with the generalisation.

**Ordering matters and is already correct:** `_make_adj_knobs`
(`mad/optimising_mad_interface.py:658`) calls `prepare_mad_for_knob_creation`
*before* building the attribute block, so `e.dpsi` exists and is zero by the time
`_build_attr_block`'s direct-attribute branch (`:637-641`) seeds the knob with
`loaded_sequence[k_str_name] = e.dpsi`. Do not reorder these.

### 4.4 `accelerators/psb.py` — the switch and the spec

`__init__` (`:32`), `copy_with` (`:73`) and the base `Accelerator.__init__` all
gain `optimise_quad_dpsi: bool = False`, threaded exactly as `optimise_quad_dy`
is at `:41`, `:61`, `:88`.

`get_supported_knob_specs` (`:99`) gains one line beside the `dy` spec at `:111`:

```python
KnobSpec("quadrupole", "dpsi", self.PATTERN_QUADRUPOLE, "k1", self.optimise_quad_dpsi, "quadrupole rolls"),
```

`nonzero_attr="k1"` is deliberate and matches `dy`: rolling an unpowered
quadrupole does nothing, so it should not consume a knob.

`quadrupole_misalignment_patterns` (`:119`) gains `"dpsi": (self.PATTERN_QUADRUPOLE,)`.

### 4.5 `accelerators/lhc.py:164` — do not break the LHC

LHC builds its misalignment specs by looping over
`quadrupole_misalignment_patterns` and calling
`getattr(self, f"optimise_quad_{attr}")`, against a `label_map` with two entries.
Adding `dpsi` to the LHC's pattern dict without also adding the flag and the
label raises `AttributeError` / `KeyError` at construction.

Either add `optimise_quad_dpsi` and `"dpsi": "quadrupole rolls"` to LHC as well,
or leave `dpsi` out of the LHC's `quadrupole_misalignment_patterns`. **Pick one
deliberately** — the failure is at import-time construction, so it will be
obvious, but it will be obvious to an LHC user rather than to you.

### 4.6 Nothing else should need touching

`_build_attr_block`'s direct-attribute branch already handles an attribute with
no multipole mapping; `format_result_knob_names` passes `<element>.dpsi` through
unchanged; `update_knob_values` / `receive_knob_values` are name-based.

---

## 5. Conventions to fix and document

- **`dpsi` is in radians**, positive in the same sense as MAD's `tilt` — verified
  bit-identical in §3. Say so in the docstring; a reader has no other way to know.
- **`dpsi` is a rotation, `dx`/`dy` are lengths.** Anything that scales knobs as
  a group — an isotropic prior, a trust region, a step limit — is now mixing
  radians with metres. `psb_loco` already solves this with a per-family prior
  (`method2_delta_orbit.run_method2.PRIOR_SUFFIXES`) and will
  add a `.dpsi` family there; if `aba_optimiser`'s own isotropic
  `prior_strength` is used with mixed families, it is wrong for the same reason.
  Worth a warning at minimum.
- **Realistic scale** for acceptance and for any default bound: 1e-4 to 3e-3 rad
  rms. Above ~5 mrad the coupling resonance starts moving Q2 by more than 0.02
  and the lattice stops being the machine.

---

## 6. Risks

1. **TPSA differentiability is the one real unknown.** `dx`/`dy` enter the map as
   translations; `dpsi` enters as a rotation. MAD-NG evaluates the misalignment
   in the same place either way, so the gradient should come through, but this
   has *not* been verified — §3 only verified the forward model. **Check this
   first**; if it fails, everything else in this spec is wasted work. The test is
   in §7.1.
2. **A deferred table replaces, it does not merge.** An element that gets a
   `dpsi` table without `dx`/`dy` in it loses its `dx`/`dy`. §4.3 handles this by
   always seeding all three; a test should pin it (§7.3).
3. **Silent no-ops.** Both `dy` and now `dpsi` do nothing at all if the table is
   missing, with no error. Whatever else is skipped, do not skip §7.2.

---

## 7. Tests

### 7.1 Gradient correctness — do this first

For a lattice with `optimise_quad_dpsi=True`, compare the analytic Jacobian
column for one `<quad>.dpsi` knob against a central finite difference of the
closed orbit at the BPMs, step 1e-6 rad. They should agree to the finite-difference
floor. This is the test that decides whether the family works at all.

### 7.2 The knob actually moves the machine

With the family enabled, setting `<quad>.dpsi` to 3e-3 must change the twiss.
Assert on a real change, not on the call returning: the failure mode is silence.
Compare against `element.tilt = 3e-3` on a bare interface and require agreement —
§3 shows they are bit-identical, so this doubles as a physics check.

### 7.3 `dpsi` knobs do not destroy `dx`/`dy`

Enable `dpsi` only, then set a `dy` on the same element through the misalignment
table and confirm it still takes effect. This pins risk 2.

### 7.4 The family is off by default

Every existing fit must be byte-identical with `optimise_quad_dpsi=False`. The
knob count and knob names of an existing PSB configuration must not change.

### 7.5 Unpowered quadrupoles get no knob

`nonzero_attr="k1"` — a quadrupole with `k1 == 0` must not produce a `.dpsi`
knob.

### 7.6 Recovery — the acceptance test

Inject a known roll pattern (ψ_rms = 1e-3 rad), generate closed orbits, fit with
`optimise_quad_dpsi=True`, and recover the pattern. Prefer this over any
implementation-pinning test: it is the only one that shows the family is usable
rather than merely present.

---

## 8. Acceptance

Minimum: §7.1 passes, §7.4 passes, and §7.6 recovers an injected roll pattern
with correlation > 0.9 against truth.

The physics goal this exists to serve, which `psb_loco` will evaluate and which
is **not** a requirement on this implementation: a fit with the roll family free
should reach a vertical dispersion near the measured 0.164 m rms while keeping
the vertical closed orbit near 1.42e-3 m, with fitted rolls of order 1e-3 rad.
If the family is implemented correctly and that fit still fails, the hypothesis
in §2 is wrong — which is a useful result and not a bug in this work.

---

## 9. Out of scope, but nearly free afterwards

`dtheta` and `dphi` (the other two misalignment rotations) become one-line
additions to `_MISALIGNMENT_ATTRIBUTES` and the pattern dict once §4.2/§4.3 are
generalised. `dpsi` on bends and sextupoles likewise — a rolled dipole is a
different and physically interesting error (§2), and it needs no further
machinery, only a `KnobSpec` and a switch. None of it is needed for the
measurement that motivates this.

---

## 10. Reproducing the evidence

`psb_loco/scripts/check_quad_roll.py` runs everything in §2 and §3 against the
ring-3 sequence and prints the tables above. It needs only `GenericMadInterface`,
so it runs today, without this change.
