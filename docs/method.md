# Method

Statements only. What was measured, what was modelled, what was fitted. The conventions the axes are drawn in are on the [conventions page](reference/conventions.md).

## Configurations

### Inverted tunes

| configuration | measured $Q_x$ / $Q_y$ | QFO / QDE circuit, MAD $k_1$ | what it is |
|---|---|---|---|
| Inverted tunes, 28th | 4.2340 / 4.1276 | 0.7395238 / -0.7377587 | QFO raised and QDE lowered until the tunes swap sides: Qx = 4.233 above Qy = 4.128. The correctors were left where they were, so this is the same measurement of a different lattice. |
| Inverted tunes, QDE14 error | 4.2331 / 4.1277 | 0.7395238 / -0.7377587 | The 28th's inverted lattice again, with QDE14 (kbrqd14corr = +0.0073775865) deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics were all retaken, and the model starts from its unperturbed circuits so LOCO has to find the error. |
| Inverted tunes, QDE14+QDE3 error | 4.2329 / 4.1276 | 0.7395238 / -0.7377587 | The 28th's inverted lattice with both QDE14 and QDE3 deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics were all retaken, and the model starts from its unperturbed circuits so LOCO has to find both errors. |
| Inverted tunes, sextupoles on | 4.2333 / 4.1283 | 0.7395238 / -0.7377587 | The 28th's inverted lattice with the ring sextupoles powered instead of off. The LOCO scan (all three RF offsets), the chroma and the AC-dipole optics were all retaken, and the model starts from its unperturbed circuits. |

### Normal tunes

| configuration | measured $Q_x$ / $Q_y$ | QFO / QDE circuit, MAD $k_1$ | what it is |
|---|---|---|---|
| Normal tunes, 29th | 4.1730 / 4.2293 | 0.7289003 / -0.7442766 | The 29th's repeat of the normal-tunes lattice, at the new P17/P23 tune point and orbit-corrector set. The LOCO scan (all three RF offsets) and chroma were retaken from scratch, same layout as the 28th's inverted-tunes campaign. |
| Normal tunes, QDE14 error | 4.1731 / 4.2299 | 0.7289003 / -0.7442766 | The 29th's normal lattice again, with QDE14 deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets) and this campaign's own driven-tune optics were retaken, same as INVERTED_QDE14_ERR. |
| Normal tunes, QDE14+QDE3 error | 4.1731 / 4.2288 | 0.7289003 / -0.7442766 | The 29th's normal lattice with both QDE14 and QDE3 deliberately mis-trimmed in LSA. The LOCO scan (all three RF offsets) and this campaign's own driven-tune optics were retaken, same as INVERTED_QDE14_QDE3_ERR. |
| Normal tunes, sextupoles on | 4.1735 / 4.2294 | 0.7289003 / -0.7442766 | The normal lattice with the ring sextupoles powered instead of off, taken on the 30th after the 29th ran out of time. The LOCO scan (all three RF offsets), the chroma and this campaign's own driven-tune optics were all retaken; unlike every other campaign here it also has AC-dipole-off blanks, so the dispersive-ripple and per-BPM interference removals do run. |

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
