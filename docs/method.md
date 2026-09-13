# Method

Statements only. What was measured, what was modelled, what was fitted. The conventions the axes are drawn in are on the [conventions page](reference/conventions.md).

## Configurations

### Inverted tunes

| configuration | measured $Q_x$ / $Q_y$ | QFO / QDE circuit, MAD $k_1$ | what it is |
|---|---|---|---|
| Inverted tunes, 28th | — | — | The 28th's inverted-tunes lattice, Qx above Qy, with nothing mis-trimmed: the baseline the other inverted-tunes configurations are compared against. The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics. |
| Inverted tunes, QDE14 error | — | — | The 28th's inverted lattice again, with QDE14 (kbrqd14corr = +0.0073775865) deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics were all retaken, and the model starts from its unperturbed circuits so LOCO has to find the error. |
| Inverted tunes, QDE14+QDE3 error | — | — | The 28th's inverted lattice with both QDE14 and QDE3 deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics were all retaken, and the model starts from its unperturbed circuits so LOCO has to find both errors. |
| Inverted tunes, sextupoles on | — | — | The 28th's inverted lattice with the ring sextupoles powered instead of off. The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics were all retaken, and the model starts from its unperturbed circuits. |

### Normal tunes

| configuration | measured $Q_x$ / $Q_y$ | QFO / QDE circuit, MAD $k_1$ | what it is |
|---|---|---|---|
| Normal tunes, 29th | 4.1730 / 4.2293 | 0.7289003 / -0.7442766 | The 29th's normal-tunes lattice, at the P17/P23 tune point and orbit-corrector set. The LOCO scan (all three RF offsets) and chroma were taken with the same layout as the 28th's inverted-tunes campaign. |
| Normal tunes, QDE14 error | 4.1731 / 4.2299 | 0.7289003 / -0.7442766 | The 29th's normal lattice again, with QDE14 deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets) and this campaign's own driven-tune optics were retaken, as for the inverted-tunes QDE14 error. |
| Normal tunes, QDE14+QDE3 error | 4.1731 / 4.2288 | 0.7289003 / -0.7442766 | The 29th's normal lattice with both QDE14 and QDE3 deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets) and this campaign's own driven-tune optics were retaken, as for the inverted-tunes QDE14+QDE3 error. |
| Normal tunes, sextupoles on | 4.1735 / 4.2294 | 0.7289003 / -0.7442766 | The normal lattice with the ring sextupoles powered instead of off, taken on the 30th after the 29th ran out of time. The LOCO scan (all three RF offsets), the chroma and this campaign's own driven-tune optics were all retaken. |

## Vocabulary

**working point**
: One of the two quadrupole powerings the MD ran: normal tunes or inverted tunes. A nav section each.

**configuration**
: One machine state within a working point: the unperturbed baseline, or one of the three with an error injected. Four per working point, shown as the tabs on every results page. Called a *scenario* on the scenario-comparison page, where the baseline is subtracted from the other three.

**case**
: One fitted option within a page: which knob families the fit was allowed to move, and how they were grouped. Two per page.

**orbit-matching mode**
: What the fit was scored against. *Delta orbits* subtract a reference orbit from both planes, so a constant kick is invisible and quadrupole offsets are not fitted. *Absolute orbits* keep the machine's own closed orbit in both planes, so bends and offsets are constrained and free.

**momentum mode**
: *Single momentum* fits the nominal-RF acquisitions only, and the other RF settings are held-out validation. *Multi momentum* fits every RF setting together.

**lumping**
: How per-magnet families were grouped. *Lumped to 32 knobs by cell* ties the two QFO flanking a QDE and leaves the QDE free. *One knob per magnet* frees all 48 against 16 BPMs per plane.

**Method 1**
: The MAD-NG parametric-twiss fit of the measured response matrix, on the delta orbits, over the same 32 cell-grouped knobs.

**Method 2**
: The closed-orbit fit: one MAD-NG worker per corrector setting, Levenberg-Marquardt over the same knobs.
